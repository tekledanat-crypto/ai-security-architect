"""Repository, data-integrity, and search tests."""
from __future__ import annotations

EXPECTED_FRAMEWORKS = {
    "cis-azure", "mcsb", "nist-800-53", "nist-csf", "iso-27001",
    "soc2", "azure-waf", "owasp-web-top10", "owasp-api-top10",
    "owasp-llm-top10", "mitre-attack-azure",
}


def test_all_frameworks_loaded(repo):
    assert set(repo.frameworks) == EXPECTED_FRAMEWORKS


def test_control_count(repo):
    # 137 controls as of Chunk 2; guard against accidental data loss
    assert len(repo.controls) == 137


def test_every_control_knows_its_framework(repo):
    for (fid, cid), ctrl in repo.controls.items():
        assert ctrl.framework_id == fid
        assert ctrl.framework_name


def test_crosswalk_groups_loaded(repo):
    assert len(repo.crosswalks) == 17
    for g in repo.crosswalks:
        assert len(g.members) >= 2


def test_crosswalk_referential_integrity(repo):
    # every crosswalk member must resolve to a real control
    for g in repo.crosswalks:
        for (fid, cid) in g.members:
            assert repo.get_control(fid, cid) is not None, f"dangling {fid}:{cid}"


def test_search_finds_mfa(repo):
    results = repo.search("mfa")
    assert results
    assert any("mfa" in (c.title + c.summary).lower() or "multi-factor" in c.summary.lower()
               for c in results)


def test_search_scoped_to_framework(repo):
    results = repo.search("encryption", framework_id="nist-800-53")
    assert all(c.framework_id == "nist-800-53" for c in results)


def test_search_empty_query_returns_nothing_bad(repo):
    # should not raise
    assert isinstance(repo.search(""), list)


def test_controls_for_service(repo):
    kv = repo.controls_for_service("key-vault")
    assert kv
    assert all("key-vault" in c.azure_services for c in kv)


def test_find_control_specific(repo):
    matches = repo.find_control("CIS-2.1.1", "cis-azure")
    assert len(matches) == 1
    assert matches[0].severity == "critical"
