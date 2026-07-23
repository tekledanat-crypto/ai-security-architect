"""Tests covering each tool function and the threat-modeling logic."""
from __future__ import annotations


def test_list_frameworks(tools):
    out = tools.list_frameworks()
    assert len(out["frameworks"]) == 11
    assert all("control_count" in f for f in out["frameworks"])


def test_find_control_found(tools):
    out = tools.find_control("LLM01")
    assert out["found"]
    assert out["matches"][0]["framework_id"] == "owasp-llm-top10"


def test_find_control_not_found(tools):
    out = tools.find_control("DOES-NOT-EXIST")
    assert out["found"] is False
    assert out["matches"] == []


def test_search_controls(tools):
    out = tools.search_controls("private endpoint")
    assert out["count"] > 0


def test_list_best_practices_for_service(tools):
    out = tools.list_best_practices(service="storage-account")
    assert out["count"] > 0
    assert all("guidance" in bp for bp in out["best_practices"])


def test_map_service(tools):
    out = tools.map_service("key-vault")
    assert out["control_count"] > 0
    assert "frameworks" in out
    assert isinstance(out["stride_exposure"], list)


def test_validate_architecture_shape(tools, insecure_arch):
    out = tools.validate_architecture(insecure_arch)
    assert "overall_score" in out
    assert "findings" in out
    assert "frameworks" in out


def test_score_architecture_is_concise(tools, hardened_arch):
    out = tools.score_architecture(hardened_arch)
    assert "findings" not in out  # concise variant omits full findings
    assert out["overall_score"] >= 90


def test_generate_remediation_prioritized(tools, insecure_arch):
    out = tools.generate_remediation(insecure_arch)
    assert out["remediation_count"] > 0
    sevs = [item["severity"] for item in out["remediation_plan"]]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
    assert sevs == sorted(sevs, key=lambda s: order[s])


def test_get_stride_threats(tools, insecure_arch):
    out = tools.get_stride_threats(insecure_arch)
    assert out["total_threats"] > 0
    cats = {c["category"] for c in out["stride"]}
    assert "Information Disclosure" in cats


def test_stride_threats_link_to_controls(tools, insecure_arch):
    out = tools.get_stride_threats(insecure_arch)
    for cat in out["stride"]:
        for threat in cat["threats"]:
            assert threat["source_control"]
            assert threat["mitigation"]


def test_map_threats(tools):
    out = tools.map_threats("storage-account")
    assert out["technique_count"] > 0
    assert all("mitigating_controls" in t for t in out["threats"])


def test_crosswalk_control(tools):
    out = tools.crosswalk_control("cis-azure", "CIS-2.1.1")
    assert out["equivalent_count"] > 0
    fw_ids = {e["framework_id"] for e in out["equivalents"]}
    assert "nist-800-53" in fw_ids


def test_crosswalk_control_none(tools):
    out = tools.crosswalk_control("cis-azure", "CIS-10.1")
    # CIS-10.1 is in a crosswalk group, but a control with no group returns empty
    assert "equivalents" in out


def test_compare_frameworks(tools):
    out = tools.compare_frameworks("cis-azure", "nist-800-53")
    assert out["shared_objective_count"] > 0
    assert out["framework_a"]["name"]
    assert out["framework_b"]["name"]
