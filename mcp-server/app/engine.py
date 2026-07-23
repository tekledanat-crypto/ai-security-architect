"""Deterministic architecture validation and scoring.

Given an Architecture and the FrameworkRepository, evaluate every control's
check_hints to produce pass/fail Findings, then roll them up into per-framework
and overall scores. Scoring is severity-weighted and fully deterministic — no LLM
involved — so results are reproducible and defensible (NIST AI RMF: the AI narrates
these results but does not invent them; see docs/ai-governance/, Chunk 9).

A control with no check_hints is treated as "not applicable" to automated
evaluation for scoring purposes (the AI can still surface it as guidance). A
control is "applicable" if it has at least one check_hint whose target service is
present in the architecture, or a global ('architecture') check.
"""
from __future__ import annotations

from typing import Optional

from .models import (
    Architecture, AssessmentResult, CheckHint,
    Control, Finding, FrameworkScore,
)
from .repository import FrameworkRepository

SEVERITY_WEIGHT = {
    "critical": 10,
    "high": 6,
    "medium": 3,
    "low": 1,
    "informational": 0,
}


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _truthy(v) -> bool:
    return v is True or (isinstance(v, str) and v.lower() in {"true", "yes", "1", "enabled"})


def _eval_hint(hint: CheckHint, arch: Architecture) -> Optional[tuple[bool, list[str]]]:
    """Return (passed, affected_node_ids) or None if the hint is not applicable.

    Not applicable = the hint targets a specific service that is absent from the
    architecture (except for service-present/absent checks, which are inherently
    about presence).
    """
    cond = hint.condition
    target = hint.target

    # A completely empty architecture is not assessable: presence/absence checks
    # would otherwise flag every "must include X" control against a blank canvas.
    # Treat all checks as not-applicable until the design has at least one node.
    if not arch.nodes:
        return None

    # ── architecture-level presence checks ──
    if cond in {"service-present", "service-absent"}:
        present = hint.value in arch.services()
        passed = present if cond == "service-present" else not present
        return passed, []

    if cond in {"edge-exists", "edge-absent"}:
        # value = {"source_service": x, "target_service": y}
        val = hint.value or {}
        src, tgt = val.get("source_service"), val.get("target_service")
        id_to_service = {n.id: n.service for n in arch.nodes}
        found = any(
            id_to_service.get(e.source) == src and id_to_service.get(e.target) == tgt
            for e in arch.edges
        )
        passed = found if cond == "edge-exists" else not found
        return passed, []

    # ── global (architecture-scoped) property checks ──
    if target == "architecture":
        # property lives on arch.context or is a synthetic flag; treat missing as pass-through
        prop = hint.property
        current = getattr(arch.context, prop, None) if prop else None
        return _compare(cond, current, hint.value), []

    # ── per-node property checks ──
    nodes = arch.nodes_for(target)
    if not nodes:
        return None  # service not in architecture → control not applicable

    failed_nodes: list[str] = []
    for node in nodes:
        current = node.properties.get(hint.property) if hint.property else None
        if not _compare(cond, current, hint.value):
            failed_nodes.append(node.id)
    return (len(failed_nodes) == 0), failed_nodes


def _compare(cond: str, current, expected) -> bool:
    if cond == "exists":
        return current is not None
    if cond == "not-exists":
        return current is None
    if cond == "equals":
        if isinstance(expected, bool):
            return _truthy(current) == expected if current is not None else False
        return current == expected
    if cond == "not-equals":
        return current != expected
    if cond == "contains":
        try:
            return expected in current
        except TypeError:
            return False
    return False


def evaluate_control(ctrl: Control, arch: Architecture) -> Optional[Finding]:
    """Evaluate one control. Returns a Finding, or None if not applicable."""
    if not ctrl.check_hints:
        return None

    applicable = False
    all_failed_nodes: list[str] = []
    fail_messages: list[str] = []
    passed_all = True

    for hint in ctrl.check_hints:
        res = _eval_hint(hint, arch)
        if res is None:
            continue  # hint not applicable to this architecture
        applicable = True
        ok, nodes = res
        if not ok:
            passed_all = False
            all_failed_nodes.extend(nodes)
            if hint.fail_message:
                fail_messages.append(hint.fail_message)

    if not applicable:
        return None

    status = "pass" if passed_all else "fail"
    message = (
        ctrl.summary if status == "pass"
        else " ".join(dict.fromkeys(fail_messages)) or f"{ctrl.title} check failed."
    )
    return Finding(
        framework_id=ctrl.framework_id,
        control_id=ctrl.control_id,
        title=ctrl.title,
        severity=ctrl.severity,
        status=status,
        message=message,
        remediation=ctrl.remediation if status == "fail" else None,
        affected_nodes=sorted(set(all_failed_nodes)),
        stride=ctrl.stride,
        attack_techniques=ctrl.attack_techniques,
    )


def score_architecture(
    arch: Architecture,
    repo: FrameworkRepository,
    framework_ids: Optional[list[str]] = None,
) -> AssessmentResult:
    target_fw = framework_ids or list(repo.frameworks.keys())
    all_findings: list[Finding] = []
    fw_scores: list[FrameworkScore] = []

    for fid in target_fw:
        fw = repo.get_framework(fid)
        if not fw:
            continue
        earned = 0
        possible = 0
        passed = failed = 0
        failed_controls: list[Finding] = []
        fw_findings: list[Finding] = []

        for ctrl in fw.controls:
            finding = evaluate_control(ctrl, arch)
            if finding is None:
                continue
            weight = SEVERITY_WEIGHT[ctrl.severity]
            possible += weight
            fw_findings.append(finding)
            if finding.status == "pass":
                earned += weight
                passed += 1
            else:
                failed += 1
                failed_controls.append(finding)

        applicable = passed + failed
        if applicable == 0:
            fw_scores.append(FrameworkScore(
                framework_id=fid, name=fw.name, status="NOT-ASSESSED",
                score=0, passed=0, failed=0, applicable=0,
            ))
            continue

        score = round(100 * earned / possible) if possible else 100
        status = "PASS" if failed == 0 else "FAIL"
        fw_scores.append(FrameworkScore(
            framework_id=fid, name=fw.name, status=status, score=score,
            passed=passed, failed=failed, applicable=applicable,
            failed_controls=failed_controls,
        ))
        all_findings.extend(fw_findings)

    # Overall score: severity-weighted across all applicable findings
    total_possible = sum(SEVERITY_WEIGHT[f.severity] for f in all_findings)
    total_earned = sum(SEVERITY_WEIGHT[f.severity] for f in all_findings if f.status == "pass")
    overall = round(100 * total_earned / total_possible) if total_possible else 100

    summary = {
        "critical_failures": sum(1 for f in all_findings if f.status == "fail" and f.severity == "critical"),
        "high_failures": sum(1 for f in all_findings if f.status == "fail" and f.severity == "high"),
        "medium_failures": sum(1 for f in all_findings if f.status == "fail" and f.severity == "medium"),
        "passed_controls": sum(1 for f in all_findings if f.status == "pass"),
        "failed_controls": sum(1 for f in all_findings if f.status == "fail"),
    }

    return AssessmentResult(
        architecture_name=arch.name,
        overall_score=overall,
        grade=_grade(overall),
        frameworks=fw_scores,
        findings=all_findings,
        summary=summary,
    )
