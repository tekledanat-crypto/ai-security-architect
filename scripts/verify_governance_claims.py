#!/usr/bin/env python3
"""Verify that the AI governance documents' claims remain verifiable.

Chunk 9's governance docs cite specific files and tests as evidence. Documentation
rots: a file gets renamed, a test gets deleted, and the citation silently becomes a
lie. Since this project's argument is that governance claims should be checkable,
that failure mode is the one thing it cannot tolerate.

This script checks:
  1. Every source file cited in docs/ai-governance/ exists.
  2. Every test name cited exists in a test file.
  3. Numeric claims (control counts) match the corpus.

Run:  python scripts/verify_governance_claims.py
Exit: 0 = all claims verifiable, 1 = at least one broken claim.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOV_DIR = ROOT / "docs" / "ai-governance"

# Paths in docs look like `backend/app/guardrails/input_filter.py:inspect_input`
FILE_PATTERN = re.compile(
    r"`((?:backend|frontend|mcp-server|frameworks|tests|docs|infra|scripts)/[\w./-]+\.\w+)"
)
TEST_PATTERN = re.compile(r"(test_[a-z0-9_]+)")
TEST_GLOBS = ("backend/tests/*.py", "mcp-server/tests/*.py", "tests/evals/*.py")


def check_file_citations() -> list[str]:
    errors: list[str] = []
    cited: set[str] = set()
    for doc in sorted(GOV_DIR.glob("*.md")):
        for match in FILE_PATTERN.finditer(doc.read_text(encoding="utf-8")):
            cited.add(match.group(1))
    for path in sorted(cited):
        if not (ROOT / path).exists():
            errors.append(f"cited file does not exist: {path}")
    print(f"  file citations:    {len(cited)} checked, {len(errors)} broken")
    return errors


def check_test_citations() -> list[str]:
    actual: set[str] = set()
    for glob in TEST_GLOBS:
        for test_file in ROOT.glob(glob):
            actual.add(test_file.stem)
            for match in re.finditer(r"def (test_[a-z0-9_]+)", test_file.read_text(encoding="utf-8")):
                actual.add(match.group(1))

    cited: set[str] = set()
    for doc in sorted(GOV_DIR.glob("*.md")):
        for match in TEST_PATTERN.finditer(doc.read_text(encoding="utf-8")):
            name = match.group(1)
            # Docs use `test_rbac_*` as a wildcard in prose; skip trailing-underscore stubs.
            if not name.endswith("_"):
                cited.add(name)

    errors = [f"cited test does not exist: {name}" for name in sorted(cited) if name not in actual]
    print(f"  test citations:    {len(cited)} checked, {len(errors)} broken")
    return errors


def check_control_count() -> list[str]:
    """The docs and UI both claim a specific control count. Keep them honest."""
    total = 0
    for path in (ROOT / "frameworks" / "data").glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return [f"corpus file is not valid JSON: {path.name} ({exc})"]
        if isinstance(data, dict) and "controls" in data:
            total += len(data["controls"])

    errors: list[str] = []
    claimed_counts: set[str] = set()
    for doc in sorted(GOV_DIR.glob("*.md")):
        for match in re.finditer(r"(\d+)\s+controls", doc.read_text(encoding="utf-8")):
            claimed_counts.add(match.group(1))

    for claimed in claimed_counts:
        if int(claimed) != total:
            errors.append(f"docs claim {claimed} controls; corpus contains {total}")
    print(f"  control count:     corpus has {total}, docs claim {sorted(claimed_counts) or ['—']}")
    return errors


def main() -> int:
    if not GOV_DIR.exists():
        print(f"governance directory not found: {GOV_DIR}")
        return 1

    print("Verifying AI governance claims are checkable\n" + "=" * 52)
    errors = check_file_citations() + check_test_citations() + check_control_count()
    print("=" * 52)

    if errors:
        print(f"\n{len(errors)} broken claim(s):")
        for err in errors:
            print(f"  ! {err}")
        print("\nA governance doc citing evidence that does not exist is worse than no doc.")
        return 1

    print("\nAll governance claims resolve to real files, tests, and counts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
