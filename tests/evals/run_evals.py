#!/usr/bin/env python3
"""Evaluation harness for the deterministic scoring engine.

Runs the golden architectures in cases/golden_architectures.json against the real
MCP tool logic and asserts the expected outcomes. This is the evidence behind the
NIST AI RMF "Measure" function (docs/ai-governance/nist-ai-rmf.md): the system's
core claim — that findings are grounded and reproducible — is continuously tested,
not asserted.

Usage:
    python tests/evals/run_evals.py            # human-readable, exit 1 on failure
    python tests/evals/run_evals.py --json     # machine-readable results
    pytest tests/evals/                        # same cases as pytest tests

Exit code 0 = all cases pass; 1 = any failure. Wired into CI in Chunk 10.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_FILE = Path(__file__).parent / "cases" / "golden_architectures.json"


def _load_engine():
    """Load the MCP server's tool logic under an isolated package name.

    Both backend/ and mcp-server/ define a top-level `app` package, so we import via
    importlib rather than sys.path to avoid collision (same approach as the backend's
    in-process MCP client).
    """
    mcp_root = REPO_ROOT / "mcp-server"
    pkg_name = "eval_mcp_app"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(mcp_root / "app")]
        sys.modules[pkg_name] = pkg

    def _load(mod: str):
        full = f"{pkg_name}.{mod}"
        if full in sys.modules:
            return sys.modules[full]
        spec = importlib.util.spec_from_file_location(full, mcp_root / "app" / f"{mod}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[full] = module
        spec.loader.exec_module(module)
        return module

    for m in ("models", "engine", "threats", "repository"):
        _load(m)
    tools = _load("tools")
    repository = sys.modules[f"{pkg_name}.repository"]
    return tools.Tools(repository.FrameworkRepository())


def load_cases() -> list[dict]:
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]


def evaluate_case(tools, case: dict) -> dict[str, Any]:
    """Run one case; return a result dict with pass/fail and per-assertion detail."""
    result = tools.validate_architecture(case["architecture"])
    expect = case["expect"]
    failures: list[str] = []

    findings = result["findings"]
    by_key = {f"{f['framework_id']}:{f['control_id']}": f for f in findings}
    failed_keys = {k for k, f in by_key.items() if f["status"] == "fail"}
    passed_keys = {k for k, f in by_key.items() if f["status"] == "pass"}
    score = result["overall_score"]
    summary = result["summary"]

    # ── score bounds ──
    if "score_min" in expect and score < expect["score_min"]:
        failures.append(f"score {score} < expected min {expect['score_min']}")
    if "score_max" in expect and score > expect["score_max"]:
        failures.append(f"score {score} > expected max {expect['score_max']}")
    if "grade_in" in expect and result["grade"] not in expect["grade_in"]:
        failures.append(f"grade {result['grade']} not in {expect['grade_in']}")

    # ── severity bounds ──
    crit = summary.get("critical_failures", 0)
    if "min_critical_failures" in expect and crit < expect["min_critical_failures"]:
        failures.append(f"critical failures {crit} < expected min {expect['min_critical_failures']}")
    if "max_critical_failures" in expect and crit > expect["max_critical_failures"]:
        failures.append(f"critical failures {crit} > expected max {expect['max_critical_failures']}")
    if "max_total_findings" in expect and len(findings) > expect["max_total_findings"]:
        failures.append(f"{len(findings)} findings > expected max {expect['max_total_findings']}")

    # ── specific controls ──
    for key in expect.get("must_fail", []):
        if key not in failed_keys:
            state = "passed" if key in passed_keys else "not assessed"
            failures.append(f"{key} expected to FAIL but {state}")
    for key in expect.get("must_pass", []):
        if key not in passed_keys:
            state = "failed" if key in failed_keys else "not assessed"
            failures.append(f"{key} expected to PASS but {state}")

    # ── applicability scoping ──
    for prefix in expect.get("must_not_assess_prefixes", []):
        hit = [k for k in by_key if k.startswith(prefix)]
        if hit:
            failures.append(f"controls matching '{prefix}' should not be assessed, got {hit}")

    # ── affected-node attribution ──
    all_failed_nodes = {n for f in findings if f["status"] == "fail" for n in f.get("affected_nodes", [])}
    for node in expect.get("failed_nodes_include", []):
        if node not in all_failed_nodes:
            failures.append(f"node '{node}' expected among failing nodes, got {sorted(all_failed_nodes)}")

    return {
        "id": case["id"],
        "description": case["description"],
        "passed": not failures,
        "failures": failures,
        "observed": {
            "score": score,
            "grade": result["grade"],
            "findings": len(findings),
            "failed_controls": summary.get("failed_controls", 0),
            "critical_failures": crit,
        },
    }


def run_all() -> dict[str, Any]:
    tools = _load_engine()
    results = [evaluate_case(tools, c) for c in load_cases()]
    passed = sum(1 for r in results if r["passed"])
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(100 * passed / len(results)) if results else 0,
        "cases": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run scoring-engine evaluations")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    report = run_all()

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["failed"] == 0 else 1

    print("Scoring engine evaluation\n" + "=" * 60)
    for r in report["cases"]:
        mark = "PASS" if r["passed"] else "FAIL"
        o = r["observed"]
        print(f"[{mark}] {r['id']:<26} score={o['score']:>3} {o['grade']}  "
              f"findings={o['findings']:>2}  failed={o['failed_controls']:>2}  crit={o['critical_failures']}")
        for f in r["failures"]:
            print(f"         ! {f}")
    print("=" * 60)
    print(f"{report['passed']}/{report['total']} cases passed ({report['pass_rate']}%)")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
