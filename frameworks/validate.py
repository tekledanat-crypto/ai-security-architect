#!/usr/bin/env python3
"""Validate framework data files and the crosswalks index.

Usage:
    python frameworks/validate.py            # validate everything in frameworks/data/
    python frameworks/validate.py file.json  # validate specific file(s)

Checks:
  * Every framework file conforms to framework.schema.json.
  * crosswalks.json conforms to crosswalks.schema.json.
  * No duplicate control_ids within a framework.
  * Every crosswalk reference (inline and in the index) resolves to a real
    (framework_id, control_id) pair. Unresolved references are FAILURES when
    the full data set is validated together; when validating a single file in
    isolation they are reported as warnings (the referent may live elsewhere).

Exit code 0 = all valid; 1 = any failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.exit("Missing dependency: pip install jsonschema")

ROOT = Path(__file__).resolve().parent
SCHEMA_DIR = ROOT / "schemas"
DATA_DIR = ROOT / "data"
CROSSWALKS_FILE = "crosswalks.json"
IGNORE_FILES = {"_manifest.json"}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str]) -> int:
    fw_validator = Draft202012Validator(load_json(SCHEMA_DIR / "framework.schema.json"))
    xw_validator = Draft202012Validator(load_json(SCHEMA_DIR / "crosswalks.schema.json"))

    explicit = bool(argv)
    targets = [Path(a) for a in argv] or [p for p in sorted(DATA_DIR.glob("*.json")) if p.name not in IGNORE_FILES]
    if not targets:
        print("No data files found.")
        return 1
    # When the whole set is validated together we can enforce referential
    # integrity; a single explicit file cannot see the others.
    full_run = not explicit

    failures = 0
    # index of every known control: {framework_id: {control_id, ...}}
    known: dict[str, set[str]] = {}
    fw_docs: dict[Path, dict] = {}
    xw_doc: dict | None = None
    xw_path: Path | None = None

    for path in targets:
        try:
            doc = load_json(path)
        except json.JSONDecodeError as exc:
            print(f"FAIL  {path.name}: invalid JSON — {exc}")
            failures += 1
            continue

        if path.name == CROSSWALKS_FILE:
            errors = sorted(xw_validator.iter_errors(doc), key=lambda e: list(e.path))
            if errors:
                failures += 1
                print(f"FAIL  {path.name}: {len(errors)} schema error(s)")
                for err in errors[:10]:
                    loc = "/".join(str(p) for p in err.path) or "<root>"
                    print(f"      at {loc}: {err.message}")
            else:
                xw_doc, xw_path = doc, path
                print(f"OK    {path.name}: {len(doc['groups'])} crosswalk group(s)")
            continue

        errors = sorted(fw_validator.iter_errors(doc), key=lambda e: list(e.path))
        if errors:
            failures += 1
            print(f"FAIL  {path.name}: {len(errors)} schema error(s)")
            for err in errors[:10]:
                loc = "/".join(str(p) for p in err.path) or "<root>"
                print(f"      at {loc}: {err.message}")
            continue

        fw_docs[path] = doc
        seen: set[str] = set()
        for control in doc["controls"]:
            cid = control["control_id"]
            if cid in seen:
                print(f"FAIL  {path.name}: duplicate control_id '{cid}'")
                failures += 1
            seen.add(cid)
        known[doc["framework_id"]] = seen
        print(f"OK    {path.name}: {len(doc['controls'])} control(s)")

    def check_ref(where: str, fid: str, cid: str) -> None:
        nonlocal failures
        if fid not in known:
            msg = f"{where}: reference to unknown framework '{fid}'"
        elif cid not in known[fid]:
            msg = f"{where}: reference to unknown control '{fid}:{cid}'"
        else:
            return
        if full_run:
            print(f"FAIL  {msg}")
            failures += 1
        else:
            print(f"WARN  {msg} (cannot resolve in single-file mode)")

    # Inline crosswalk integrity
    for path, doc in fw_docs.items():
        for control in doc["controls"]:
            for xw in control.get("crosswalk", []):
                check_ref(f"{path.name} {control['control_id']}", xw["framework_id"], xw["control_id"])

    # Crosswalk index integrity
    if xw_doc is not None:
        for i, group in enumerate(xw_doc["groups"]):
            for ref in group["controls"]:
                check_ref(f"{xw_path.name} group[{i}] '{group['objective'][:32]}'",
                          ref["framework_id"], ref["control_id"])

    total = len(fw_docs) + (1 if xw_doc is not None else 0)
    print(f"\n{total} file(s) valid, {failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
