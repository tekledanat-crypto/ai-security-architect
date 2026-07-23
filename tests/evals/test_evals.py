"""Golden-architecture evals as pytest cases (also runnable via run_evals.py).

Wired into CI in Chunk 10. These are the regression suite for the deterministic
scoring engine — the component the product's credibility depends on.
"""
from __future__ import annotations

import pytest

from run_evals import _load_engine, evaluate_case, load_cases

CASES = load_cases()


@pytest.fixture(scope="module")
def tools():
    return _load_engine()


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden_architecture(tools, case):
    result = evaluate_case(tools, case)
    assert result["passed"], "\n".join(result["failures"])


def test_scoring_is_deterministic(tools):
    """The same architecture must always produce the same score — the basis of the
    claim that findings are reproducible rather than model-generated."""
    case = CASES[0]
    scores = {tools.validate_architecture(case["architecture"])["overall_score"] for _ in range(5)}
    assert len(scores) == 1, f"non-deterministic scoring: {scores}"


def test_hardening_strictly_improves_score(tools):
    """Remediation must measurably improve the score — otherwise remediation advice
    is unfalsifiable."""
    insecure = next(c for c in CASES if c["id"] == "insecure-ecommerce")
    hardened = next(c for c in CASES if c["id"] == "hardened-ecommerce")
    s_bad = tools.validate_architecture(insecure["architecture"])["overall_score"]
    s_good = tools.validate_architecture(hardened["architecture"])["overall_score"]
    assert s_good > s_bad
