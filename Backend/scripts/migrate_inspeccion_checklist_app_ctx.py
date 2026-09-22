"""Migrate test_inspeccion_checklist to conftest app_ctx (JWT strict)."""
from __future__ import annotations

import re
from pathlib import Path


KEEP_APP = {
    "test_rechaza_contrato_v1_ids",
    "test_personas_sin_carnet_negativo_rechazado",
    "test_rechaza_item_sin_respuesta",
    "test_migration_v2_schema",
    "test_migration_tipo_si_no_schema",
}


def _dedent_app_context_block(lines: list[str], start: int) -> tuple[list[str], int]:
    """Remove `with app.app_context():` and dedent its body by 4 spaces."""
    base = lines[start]
    base_indent = len(base) - len(base.lstrip())
    body_indent = base_indent + 4
    out: list[str] = []
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            out.append(line)
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent < body_indent:
            break
        out.append(line[4:] if line.startswith(" " * body_indent) else line)
        i += 1
    return out, i


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "tests" / "test_inspeccion_checklist.py"
    text = path.read_text(encoding="utf-8")

    text = text.replace(
        "@pytest.fixture()\ndef items_catalogo(app):\n    with app.app_context():",
        "@pytest.fixture()\ndef items_catalogo(app_ctx):",
    )

    raw_lines = text.splitlines()
    # Dedent items_catalogo fixture body
    processed: list[str] = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if line.startswith("def items_catalogo(app_ctx):"):
            processed.append(line)
            i += 1
            while i < len(raw_lines) and (
                raw_lines[i].startswith("    ") or raw_lines[i].strip() == ""
            ):
                if raw_lines[i].strip() == "with app.app_context():":
                    body, i = _dedent_app_context_block(raw_lines, i)
                    processed.extend(body)
                    continue
                if raw_lines[i].startswith("        "):
                    processed.append(raw_lines[i][4:])
                else:
                    processed.append(raw_lines[i])
                i += 1
            continue
        processed.append(line)
        i += 1

    # Transform tests
    final: list[str] = []
    i = 0
    while i < len(processed):
        line = processed[i]
        m = re.match(r"def (test_\w+)\(app, items_catalogo\):", line)
        if m and m.group(1) not in KEEP_APP:
            line = line.replace("(app, items_catalogo)", "(app_ctx, items_catalogo)")
        final.append(line)
        if line.strip() == "with app.app_context():":
            body, next_i = _dedent_app_context_block(processed, i)
            final.pop()  # remove with line
            final.extend(body)
            i = next_i
            continue
        i += 1

    path.write_text("\n".join(final) + "\n", encoding="utf-8")
    print(f"Updated {path}")


if __name__ == "__main__":
    main()
