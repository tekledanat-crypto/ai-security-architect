"""Loads framework JSON into memory and a SQLite FTS5 index for search.

The repository is the single source of truth the tools query. It is built once at
startup from frameworks/data/*.json (validated against the schema in Chunk 2) and
holds:
  * an in-memory index of every Control (keyed by framework_id + control_id),
  * a SQLite FTS5 virtual table for full-text search over controls,
  * the crosswalk index for cross-framework equivalence lookups.

SQLite FTS5 is used locally (ADR-0002). The FTS query surface is deliberately
small (`search`) so the production Postgres implementation can swap in behind the
same method without touching the tools.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from .models import Control, Framework

# frameworks/ is mounted at /app/frameworks in the container, or found relative
# to the repo root in local dev.
_CANDIDATES = [
    Path("/app/frameworks/data"),
    Path(__file__).resolve().parents[3] / "frameworks" / "data",
    Path(__file__).resolve().parents[2] / "frameworks" / "data",
]

IGNORE = {"_manifest.json", "crosswalks.json"}


def _data_dir() -> Path:
    for c in _CANDIDATES:
        if c.is_dir():
            return c
    raise FileNotFoundError(
        f"Could not locate frameworks/data in any of: {[str(c) for c in _CANDIDATES]}"
    )


class CrosswalkGroup:
    __slots__ = ("objective", "domain", "members")

    def __init__(self, objective: str, domain: str, members: list[tuple[str, str]]):
        self.objective = objective
        self.domain = domain
        self.members = members  # list of (framework_id, control_id)


class FrameworkRepository:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or _data_dir()
        self.frameworks: dict[str, Framework] = {}
        self.controls: dict[tuple[str, str], Control] = {}
        self.crosswalks: list[CrosswalkGroup] = []
        self._db = sqlite3.connect(":memory:")
        self._db.row_factory = sqlite3.Row
        self._load()
        self._build_fts()

    # ── loading ──────────────────────────────────────────────────────
    def _load(self) -> None:
        for path in sorted(self.data_dir.glob("*.json")):
            if path.name in IGNORE:
                continue
            raw = json.loads(path.read_text(encoding="utf-8"))
            fw = Framework(**raw)
            for ctrl in fw.controls:
                ctrl.framework_id = fw.framework_id
                ctrl.framework_name = fw.name
                self.controls[(fw.framework_id, ctrl.control_id)] = ctrl
            self.frameworks[fw.framework_id] = fw

        xw_path = self.data_dir / "crosswalks.json"
        if xw_path.exists():
            xw = json.loads(xw_path.read_text(encoding="utf-8"))
            for g in xw["groups"]:
                self.crosswalks.append(
                    CrosswalkGroup(
                        objective=g["objective"],
                        domain=g.get("domain", ""),
                        members=[(m["framework_id"], m["control_id"]) for m in g["controls"]],
                    )
                )

    def _build_fts(self) -> None:
        cur = self._db.cursor()
        cur.execute(
            "CREATE VIRTUAL TABLE controls_fts USING fts5("
            "framework_id, control_id, title, summary, remediation, domain, azure_services)"
        )
        cur.executemany(
            "INSERT INTO controls_fts VALUES (?,?,?,?,?,?,?)",
            [
                (
                    c.framework_id, c.control_id, c.title, c.summary,
                    c.remediation, c.domain or "", " ".join(c.azure_services),
                )
                for c in self.controls.values()
            ],
        )
        self._db.commit()

    # ── queries ──────────────────────────────────────────────────────
    def list_frameworks(self) -> list[Framework]:
        return list(self.frameworks.values())

    def get_framework(self, framework_id: str) -> Optional[Framework]:
        return self.frameworks.get(framework_id)

    def get_control(self, framework_id: str, control_id: str) -> Optional[Control]:
        return self.controls.get((framework_id, control_id))

    def all_controls(self) -> Iterable[Control]:
        return self.controls.values()

    def find_control(self, control_id: str, framework_id: Optional[str] = None) -> list[Control]:
        out = []
        for (fid, cid), ctrl in self.controls.items():
            if cid == control_id and (framework_id is None or fid == framework_id):
                out.append(ctrl)
        return out

    def search(self, query: str, framework_id: Optional[str] = None, limit: int = 20) -> list[Control]:
        # FTS5 MATCH; fall back to a LIKE scan if the query has no usable tokens.
        cur = self._db.cursor()
        safe = query.strip()
        results: list[Control] = []
        if safe:
            try:
                sql = (
                    "SELECT framework_id, control_id FROM controls_fts "
                    "WHERE controls_fts MATCH ? "
                )
                params: list = [safe]
                if framework_id:
                    sql += "AND framework_id = ? "
                    params.append(framework_id)
                sql += "ORDER BY rank LIMIT ?"
                params.append(limit)
                for row in cur.execute(sql, params):
                    ctrl = self.controls.get((row["framework_id"], row["control_id"]))
                    if ctrl:
                        results.append(ctrl)
            except sqlite3.OperationalError:
                results = []
        if not results:  # substring fallback
            q = safe.lower()
            for c in self.controls.values():
                if framework_id and c.framework_id != framework_id:
                    continue
                blob = f"{c.title} {c.summary} {c.remediation} {c.domain}".lower()
                if q in blob:
                    results.append(c)
                if len(results) >= limit:
                    break
        return results

    def controls_for_service(self, service: str) -> list[Control]:
        return [c for c in self.controls.values() if service in c.azure_services]

    def crosswalk_for(self, framework_id: str, control_id: str) -> list[CrosswalkGroup]:
        return [g for g in self.crosswalks if (framework_id, control_id) in g.members]
