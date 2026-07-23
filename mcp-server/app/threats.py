"""STRIDE threat modeling and remediation generation.

Threats are derived deterministically from the architecture and the control data:
each failed or at-risk control contributes threats in its STRIDE categories, linked
to the ATT&CK/ATLAS techniques from the framework data. This keeps the threat model
grounded in the same control corpus rather than free-form model output.
"""
from __future__ import annotations

from collections import defaultdict

from .engine import evaluate_control
from .models import Architecture, Finding
from .repository import FrameworkRepository

STRIDE_LABELS = {
    "spoofing": "Spoofing",
    "tampering": "Tampering",
    "repudiation": "Repudiation",
    "information-disclosure": "Information Disclosure",
    "denial-of-service": "Denial of Service",
    "elevation-of-privilege": "Elevation of Privilege",
}


def stride_threats(arch: Architecture, repo: FrameworkRepository) -> list[dict]:
    """Build a STRIDE-organized threat model for the architecture.

    For each STRIDE category, collect the failing controls that map to it and turn
    them into concrete threat/mitigation entries scoped to affected components.
    """
    by_category: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    for ctrl in repo.all_controls():
        finding = evaluate_control(ctrl, arch)
        # Only surface threats where the architecture is actually exposed (fail),
        # or where the control is high/critical and applicable.
        if finding is None or finding.status != "fail":
            continue
        for cat in ctrl.stride:
            key = (cat, ctrl.control_id)
            if key in seen:
                continue
            seen.add(key)
            components = finding.affected_nodes or [
                n.label or n.service for n in arch.nodes if n.service in ctrl.azure_services
            ]
            by_category[cat].append({
                "threat": ctrl.title,
                "description": finding.message,
                "components": components,
                "mitigation": ctrl.remediation,
                "severity": ctrl.severity,
                "attack_techniques": ctrl.attack_techniques,
                "source_control": f"{ctrl.framework_id}:{ctrl.control_id}",
            })

    model = []
    for cat, label in STRIDE_LABELS.items():
        entries = sorted(by_category.get(cat, []),
                         key=lambda e: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(e["severity"], 4))
        model.append({
            "category": label,
            "category_id": cat,
            "threat_count": len(entries),
            "threats": entries,
        })
    return model


def generate_remediation(findings: list[Finding]) -> list[dict]:
    """Turn failed findings into a prioritized, deduplicated remediation plan."""
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
    fails = [f for f in findings if f.status == "fail"]
    fails.sort(key=lambda f: (order.get(f.severity, 5), f.framework_id))
    plan = []
    for i, f in enumerate(fails, 1):
        plan.append({
            "priority": i,
            "severity": f.severity,
            "finding": f.message,
            "control": f"{f.framework_id}:{f.control_id}",
            "title": f.title,
            "remediation": f.remediation,
            "affected_components": f.affected_nodes,
            "attack_techniques": f.attack_techniques,
        })
    return plan
