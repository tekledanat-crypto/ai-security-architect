#!/usr/bin/env python3
"""Static validation for the Bicep templates.

`az bicep build` is the authoritative check and runs in CI. This script exists because
it is useful to catch the common structural errors *before* pushing — and because in
some environments (including the one this was authored in) the Azure CLI isn't
available, and shipping unvalidated IaC would be worse than shipping none.

Checks:
  1. Braces/brackets/parens balance in every .bicep file.
  2. Every module referenced by main.bicep exists on disk.
  3. Every parameter a module requires is passed by its caller (and vice versa).
  4. Every output a caller consumes is declared by the module.
  5. No circular references between resources in the same file.

This is not a substitute for `az bicep build`. It is a fast pre-flight.

Run:  python scripts/validate_bicep.py
Exit: 0 = checks pass, 1 = problems found.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"


def check_balance(path: Path) -> list[str]:
    """Braces must balance.

    Bicep string interpolation ('${x}') puts braces inside strings, so a naive count
    is wrong. This walks the source character by character, tracking whether it is
    inside a string, and — importantly — treats the '${' ... '}' interpolation as a
    nested expression context, which is what Bicep actually does.
    """
    src = path.read_text(encoding="utf-8")
    pairs = {"{": "}", "[": "]", "(": ")"}
    closers = {v: k for k, v in pairs.items()}

    stack: list[str] = []
    i = 0
    in_string = False
    in_multiline = False
    interp_depth = 0  # brace depth inside a '${ ... }' interpolation

    while i < len(src):
        ch = src[i]
        nxt2 = src[i : i + 3]

        # Multi-line strings ''' ... '''
        if not in_string and nxt2 == "'''":
            in_multiline = not in_multiline
            i += 3
            continue
        if in_multiline:
            i += 1
            continue

        # Line comments (only outside strings)
        if not in_string and src[i : i + 2] == "//":
            while i < len(src) and src[i] != "\n":
                i += 1
            continue

        # Block comments
        if not in_string and src[i : i + 2] == "/*":
            end = src.find("*/", i)
            i = len(src) if end == -1 else end + 2
            continue

        if in_string:
            if ch == "\\":
                i += 2
                continue
            # Enter interpolation: braces inside it are real expression braces
            if src[i : i + 2] == "${":
                interp_depth += 1
                i += 2
                continue
            if interp_depth and ch == "}":
                interp_depth -= 1
                i += 1
                continue
            if ch == "'" and interp_depth == 0:
                in_string = False
            i += 1
            continue

        if ch == "'":
            in_string = True
            i += 1
            continue

        if ch in pairs:
            stack.append(ch)
        elif ch in closers:
            if not stack:
                line = src[:i].count("\n") + 1
                return [f"{path.name}:{line}: unexpected '{ch}'"]
            opener = stack.pop()
            if pairs[opener] != ch:
                line = src[:i].count("\n") + 1
                return [f"{path.name}:{line}: '{opener}' closed by '{ch}'"]
        i += 1

    if stack:
        return [f"{path.name}: {len(stack)} unclosed '{stack[-1]}'"]
    return []


def parse_params(path: Path) -> tuple[set[str], set[str]]:
    """Return (all params, params without defaults)."""
    src = path.read_text(encoding="utf-8")
    all_params: set[str] = set()
    required: set[str] = set()
    for m in re.finditer(r"^param (\w+) [\w\[\]?]+(\s*=\s*(.+))?$", src, re.M):
        name, has_default = m.group(1), m.group(2)
        all_params.add(name)
        if not has_default:
            required.add(name)
    return all_params, required


def parse_outputs(path: Path) -> set[str]:
    src = path.read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"^output (\w+) ", src, re.M)}


def check_module_wiring() -> list[str]:
    errors: list[str] = []
    main = INFRA / "main.bicep"
    if not main.exists():
        return ["infra/main.bicep not found"]

    src = main.read_text(encoding="utf-8")
    module_blocks = re.finditer(
        r"module (\w+) '([^']+)' = (?:if \([^)]*\) )?\{(.*?)\n\}", src, re.S
    )

    modules_seen = 0
    for block in module_blocks:
        modules_seen += 1
        symbol, rel_path, body = block.group(1), block.group(2), block.group(3)
        mod_path = INFRA / rel_path
        if not mod_path.exists():
            errors.append(f"main.bicep references missing module: {rel_path}")
            continue

        all_params, required = parse_params(mod_path)
        params_block = re.search(r"params:\s*\{(.*?)\n  \}", body, re.S)
        passed = (
            {m.group(1) for m in re.finditer(r"^\s+(\w+):", params_block.group(1), re.M)}
            if params_block
            else set()
        )

        for missing in sorted(required - passed):
            errors.append(f"module '{symbol}' ({rel_path}): required param '{missing}' not passed")
        for unknown in sorted(passed - all_params):
            errors.append(f"module '{symbol}' ({rel_path}): passes unknown param '{unknown}'")

    # Outputs consumed by main must exist on the module.
    for m in re.finditer(r"(\w+)\.outputs\.(\w+)", src):
        symbol, output = m.group(1), m.group(2)
        decl = re.search(rf"module {symbol} '([^']+)'", src)
        if not decl:
            continue
        mod_path = INFRA / decl.group(1)
        if mod_path.exists() and output not in parse_outputs(mod_path):
            errors.append(f"main.bicep reads '{symbol}.outputs.{output}' which the module does not declare")

    print(f"  modules wired:     {modules_seen} checked")
    return errors


def check_cycles(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    decls = [
        (m.group(1), m.start())
        for m in re.finditer(r"^resource (\w+) '[^']+' = (?:if \([^)]*\) )?\{", src, re.M)
    ]
    if not decls:
        return []

    names = [d[0] for d in decls]
    bodies: dict[str, str] = {}
    for i, (name, start) in enumerate(decls):
        end = decls[i + 1][1] if i + 1 < len(decls) else len(src)
        bodies[name] = src[start:end]

    edges: set[tuple[str, str]] = set()
    for name, body in bodies.items():
        for other in names:
            if other == name:
                continue
            if re.search(rf"\b{other}\.(properties|id|name)", body) or re.search(
                rf"dependsOn:\s*\[[^\]]*\b{other}\b", body
            ):
                edges.add((name, other))

    return [
        f"{path.name}: circular reference between '{a}' and '{b}'"
        for (a, b) in sorted(edges)
        if (b, a) in edges and a < b
    ]


def main() -> int:
    if not INFRA.exists():
        print(f"infra directory not found: {INFRA}")
        return 1

    files = sorted(INFRA.rglob("*.bicep"))
    if not files:
        print("no .bicep files found")
        return 1

    print("Static Bicep validation (pre-flight; `az bicep build` is authoritative)")
    print("=" * 68)

    errors: list[str] = []
    for f in files:
        errors += check_balance(f)
        errors += check_cycles(f)
    print(f"  files parsed:      {len(files)} ({sum(len(f.read_text().splitlines()) for f in files)} lines)")
    errors += check_module_wiring()

    print("=" * 68)
    if errors:
        print(f"\n{len(errors)} problem(s):")
        for e in errors:
            print(f"  ! {e}")
        return 1

    print("\nStructure, module wiring, and dependency graph all check out.")
    print("Note: this does not replace `az bicep build` — see .github/workflows/ci.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
