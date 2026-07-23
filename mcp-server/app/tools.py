"""Tool implementations.

Each function here is a plain, synchronous, fully-testable unit. The MCP protocol
layer (server.py) is a thin wrapper that validates inputs and serializes these
outputs. Keeping the logic here means the pytest suite exercises real behavior
without needing an MCP client, and the FastAPI backend (Chunk 4) can import these
directly if it ever needs in-process access.
"""
from __future__ import annotations

from typing import Any, Optional

from .engine import score_architecture
from .models import Architecture
from .repository import FrameworkRepository
from .threats import STRIDE_LABELS, generate_remediation, stride_threats


class Tools:
    def __init__(self, repo: FrameworkRepository):
        self.repo = repo

    # ── discovery ────────────────────────────────────────────────────
    def list_frameworks(self) -> dict[str, Any]:
        return {
            "frameworks": [
                {
                    "framework_id": fw.framework_id,
                    "name": fw.name,
                    "version": fw.version,
                    "category": fw.category,
                    "publisher": fw.publisher,
                    "control_count": len(fw.controls),
                    "reference_url": fw.reference_url,
                }
                for fw in self.repo.list_frameworks()
            ]
        }

    def find_control(self, control_id: str, framework_id: Optional[str] = None) -> dict[str, Any]:
        matches = self.repo.find_control(control_id, framework_id)
        if not matches:
            return {"found": False, "control_id": control_id, "matches": []}
        return {
            "found": True,
            "control_id": control_id,
            "matches": [self._control_dict(c) for c in matches],
        }

    def search_controls(self, query: str, framework_id: Optional[str] = None, limit: int = 20) -> dict[str, Any]:
        results = self.repo.search(query, framework_id, limit)
        return {
            "query": query,
            "count": len(results),
            "results": [self._control_dict(c, brief=True) for c in results],
        }

    def list_best_practices(self, service: Optional[str] = None, framework_id: Optional[str] = None) -> dict[str, Any]:
        controls = list(self.repo.all_controls())
        if service:
            controls = [c for c in controls if service in c.azure_services]
        if framework_id:
            controls = [c for c in controls if c.framework_id == framework_id]
        # highest severity first
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
        controls.sort(key=lambda c: order.get(c.severity, 5))
        return {
            "service": service,
            "count": len(controls),
            "best_practices": [
                {"control": f"{c.framework_id}:{c.control_id}", "title": c.title,
                 "severity": c.severity, "guidance": c.remediation}
                for c in controls
            ],
        }

    def map_service(self, service: str) -> dict[str, Any]:
        controls = self.repo.controls_for_service(service)
        stride = sorted({s for c in controls for s in c.stride})
        techniques = sorted({t for c in controls for t in c.attack_techniques})
        return {
            "service": service,
            "control_count": len(controls),
            "frameworks": sorted({c.framework_id for c in controls}),
            "stride_exposure": [STRIDE_LABELS[s] for s in stride],
            "attack_techniques": techniques,
            "controls": [
                {"control": f"{c.framework_id}:{c.control_id}", "title": c.title, "severity": c.severity}
                for c in controls
            ],
        }

    # ── validation / scoring ─────────────────────────────────────────
    def validate_architecture(self, architecture: dict, framework_ids: Optional[list[str]] = None) -> dict[str, Any]:
        arch = Architecture(**architecture)
        result = score_architecture(arch, self.repo, framework_ids)
        return result.model_dump()

    def score_architecture(self, architecture: dict, framework_ids: Optional[list[str]] = None) -> dict[str, Any]:
        arch = Architecture(**architecture)
        result = score_architecture(arch, self.repo, framework_ids)
        return {
            "architecture_name": result.architecture_name,
            "overall_score": result.overall_score,
            "grade": result.grade,
            "summary": result.summary,
            "frameworks": [
                {"framework_id": f.framework_id, "name": f.name, "status": f.status,
                 "score": f.score, "passed": f.passed, "failed": f.failed, "applicable": f.applicable}
                for f in result.frameworks
            ],
        }

    def generate_remediation(self, architecture: dict, framework_ids: Optional[list[str]] = None) -> dict[str, Any]:
        arch = Architecture(**architecture)
        result = score_architecture(arch, self.repo, framework_ids)
        plan = generate_remediation(result.findings)
        return {"architecture_name": arch.name, "remediation_count": len(plan), "remediation_plan": plan}

    # ── threat modeling ──────────────────────────────────────────────
    def get_stride_threats(self, architecture: dict) -> dict[str, Any]:
        arch = Architecture(**architecture)
        model = stride_threats(arch, self.repo)
        total = sum(cat["threat_count"] for cat in model)
        return {"architecture_name": arch.name, "total_threats": total, "stride": model}

    def map_threats(self, service: str) -> dict[str, Any]:
        controls = self.repo.controls_for_service(service)
        threats: dict[str, dict] = {}
        for c in controls:
            for t in c.attack_techniques:
                threats.setdefault(t, {"technique": t, "controls": [], "stride": set()})
                threats[t]["controls"].append(f"{c.framework_id}:{c.control_id}")
                threats[t]["stride"].update(c.stride)
        out = [
            {"technique": v["technique"], "mitigating_controls": v["controls"],
             "stride": [STRIDE_LABELS[s] for s in sorted(v["stride"])]}
            for v in threats.values()
        ]
        return {"service": service, "technique_count": len(out), "threats": out}

    # ── cross-framework ──────────────────────────────────────────────
    def crosswalk_control(self, framework_id: str, control_id: str) -> dict[str, Any]:
        groups = self.repo.crosswalk_for(framework_id, control_id)
        equivalents = []
        for g in groups:
            for (fid, cid) in g.members:
                if (fid, cid) == (framework_id, control_id):
                    continue
                ctrl = self.repo.get_control(fid, cid)
                equivalents.append({
                    "framework_id": fid, "control_id": cid,
                    "title": ctrl.title if ctrl else None,
                    "objective": g.objective,
                })
        return {
            "source": {"framework_id": framework_id, "control_id": control_id},
            "objectives": [g.objective for g in groups],
            "equivalent_count": len(equivalents),
            "equivalents": equivalents,
        }

    def compare_frameworks(self, framework_a: str, framework_b: str) -> dict[str, Any]:
        shared = []
        for g in self.repo.crosswalks:
            a = [cid for (fid, cid) in g.members if fid == framework_a]
            b = [cid for (fid, cid) in g.members if fid == framework_b]
            if a and b:
                shared.append({"objective": g.objective,
                               f"{framework_a}_controls": a,
                               f"{framework_b}_controls": b})
        fw_a = self.repo.get_framework(framework_a)
        fw_b = self.repo.get_framework(framework_b)
        return {
            "framework_a": {"id": framework_a, "name": fw_a.name if fw_a else None,
                            "controls": len(fw_a.controls) if fw_a else 0},
            "framework_b": {"id": framework_b, "name": fw_b.name if fw_b else None,
                            "controls": len(fw_b.controls) if fw_b else 0},
            "shared_objective_count": len(shared),
            "shared_objectives": shared,
        }

    # ── helpers ──────────────────────────────────────────────────────
    def _control_dict(self, c, brief: bool = False) -> dict[str, Any]:
        base = {
            "framework_id": c.framework_id,
            "framework_name": c.framework_name,
            "control_id": c.control_id,
            "title": c.title,
            "severity": c.severity,
            "domain": c.domain,
            "summary": c.summary,
        }
        if brief:
            return base
        base.update({
            "azure_services": c.azure_services,
            "remediation": c.remediation,
            "stride": [STRIDE_LABELS[s] for s in c.stride],
            "attack_techniques": c.attack_techniques,
            "crosswalk": [{"framework_id": x.framework_id, "control_id": x.control_id} for x in c.crosswalk],
        })
        return base
