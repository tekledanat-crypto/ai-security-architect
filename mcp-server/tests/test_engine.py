"""Validation and scoring engine tests.

These pin the core security behavior: an insecure design must score poorly and
surface the expected critical findings; a hardened design must score highly; and
scoring must be deterministic.
"""
from __future__ import annotations

from app.engine import score_architecture
from app.models import Architecture


def _score(arch_dict, repo, framework_ids=None):
    return score_architecture(Architecture(**arch_dict), repo, framework_ids)


def test_insecure_scores_low(insecure_arch, repo):
    r = _score(insecure_arch, repo)
    assert r.overall_score < 50
    assert r.grade in {"D", "F"}


def test_hardened_scores_high(hardened_arch, repo):
    r = _score(hardened_arch, repo)
    assert r.overall_score >= 90
    assert r.grade == "A"


def test_hardened_beats_insecure(insecure_arch, hardened_arch, repo):
    assert _score(hardened_arch, repo).overall_score > _score(insecure_arch, repo).overall_score


def test_scoring_is_deterministic(insecure_arch, repo):
    a = _score(insecure_arch, repo)
    b = _score(insecure_arch, repo)
    assert a.overall_score == b.overall_score
    assert a.summary == b.summary


def test_public_blob_is_critical_failure(insecure_arch, repo):
    r = _score(insecure_arch, repo)
    blob = [f for f in r.findings if f.control_id == "CIS-4.1.4"]
    assert blob and blob[0].status == "fail"
    assert blob[0].severity == "critical"


def test_failed_finding_carries_remediation(insecure_arch, repo):
    r = _score(insecure_arch, repo)
    for f in r.findings:
        if f.status == "fail":
            assert f.remediation, f"{f.control_id} missing remediation"


def test_failed_finding_has_affected_nodes_for_node_checks(insecure_arch, repo):
    r = _score(insecure_arch, repo)
    sql_public = [f for f in r.findings if f.control_id == "CIS-5.1.2"]
    assert sql_public
    assert "sql" in sql_public[0].affected_nodes


def test_not_applicable_controls_excluded(repo):
    # An architecture with only a storage account should not be scored against
    # SQL-specific controls.
    arch = {"name": "solo", "nodes": [{"id": "s", "service": "storage-account",
             "properties": {"public_access": False, "allow_blob_public_access": False,
                            "https_only": True, "private_endpoint": True}}], "edges": []}
    r = _score(arch, repo)
    assert not any(f.control_id.startswith("CIS-5.1") for f in r.findings)


def test_framework_filter(insecure_arch, repo):
    r = _score(insecure_arch, repo, framework_ids=["cis-azure"])
    assert all(f.framework_id == "cis-azure" for f in r.findings)
    assert len(r.frameworks) == 1


def test_empty_architecture_does_not_crash(repo):
    r = _score({"name": "empty", "nodes": [], "edges": []}, repo)
    assert r.overall_score == 100  # nothing applicable → vacuously compliant
    assert r.summary["failed_controls"] == 0
