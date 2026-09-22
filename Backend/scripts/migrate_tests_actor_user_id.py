#!/usr/bin/env python
"""
PREDEPLOY-TESTS.1 — migración mecánica actor_user_id en tests.

Solo modifica tests/. No toca app/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TESTS = BACKEND / "tests"

SERVICE_CALLS = (
    "create_ruta_grupo",
    "replace_grupo_inspectores",
    "assign_iniciadores_to_grupo",
    "create_ruta_trabajo",
)

ACTOR_KW = "actor_user_id="


def _inject_actor_into_call(call_text: str, actor_expr: str) -> str:
    if ACTOR_KW in call_text:
        return call_text
    if call_text.rstrip().endswith(")"):
        inner = call_text.rstrip()[:-1]
        if inner.endswith("("):
            return f"{inner}actor_user_id={actor_expr})"
        return f"{inner}, actor_user_id={actor_expr})"
    return call_text


def _process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    actor_var: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m_user = re.match(
            r"^(\s*)(\w+)\s*=\s*_mk_user\(\)\s*$",
            line,
        )
        if m_user:
            actor_var = m_user.group(2)
        m_rel = re.match(
            r"^(\s*)rel\s*=\s*crear_relevamiento_desde_payload\(\s*$",
            line,
        )
        if m_rel and actor_var:
            block = [line]
            j = i + 1
            while j < len(lines) and not re.search(r"^\s*\)\s*$", lines[j]):
                block.append(lines[j])
                j += 1
            if j < len(lines):
                block.append(lines[j])
            joined = "".join(block)
            if ACTOR_KW not in joined:
                block[-1] = block[-1].replace(
                    ")",
                    f", actor_user_id={actor_var})",
                    1,
                )
            out.extend(block)
            i = j + 1
            continue

        for fn in SERVICE_CALLS:
            if f"{fn}(" in line and ACTOR_KW not in line:
                if actor_var:
                    if line.strip().endswith(")") and "(" in line:
                        line = _inject_actor_into_call(line.rstrip("\n"), actor_var) + (
                            "\n" if line.endswith("\n") else ""
                        )
                    else:
                        block = [line]
                        j = i + 1
                        while j < len(lines):
                            block.append(lines[j])
                            if ")" in lines[j]:
                                break
                            j += 1
                        joined = "".join(block)
                        if ACTOR_KW not in joined:
                            block[-1] = block[-1].replace(
                                ")",
                                f", actor_user_id={actor_var})",
                                1,
                            )
                        out.extend(block)
                        i = j + 1
                        break
        else:
            out.append(line)
            i += 1
            continue
        continue

    new_text = "".join(out)
    if new_text != original:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for path in sorted(TESTS.rglob("test_*.py")):
        if _process_file(path):
            changed += 1
            print(f"updated {path.relative_to(BACKEND)}")
    print(f"files_changed={changed}")


if __name__ == "__main__":
    main()
