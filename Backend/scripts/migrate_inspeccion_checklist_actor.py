"""One-off: add actor_user_id to test_inspeccion_checklist.py."""
from __future__ import annotations

import re
from pathlib import Path


def add_actor_multiline(s: str) -> str:
    out: list[str] = []
    i = 0
    needle = "crear_actuacion_desde_payload("
    while i < len(s):
        idx = s.find(needle, i)
        if idx == -1:
            out.append(s[i:])
            break
        out.append(s[i:idx])
        j = idx + len(needle)
        depth = 1
        while j < len(s) and depth:
            if s[j] == "(":
                depth += 1
            elif s[j] == ")":
                depth -= 1
            j += 1
        block = s[idx:j]
        if "actor_user_id" not in block:
            block = block[:-1] + ", actor_user_id=actor_user_id)"
        out.append(block)
        i = j
    return "".join(out)


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "tests" / "test_inspeccion_checklist.py"
    text = path.read_text(encoding="utf-8")

    text = text.replace(
        "@pytest.fixture()\ndef items_catalogo(app):\n    with app.app_context():",
        "@pytest.fixture()\ndef items_catalogo(app_ctx):",
    )

    text = text.replace(
        "def _put_actuacion(act, **row_extra) -> None:\n"
        "    row = ActuacionGridRowIn.model_validate(_legacy_put_row_dict(act, **row_extra))\n"
        "    actualizar_actuacion(int(act.id), map_actuacion_row(row))",
        "def _put_actuacion(act, *, actor_user_id: int, **row_extra) -> None:\n"
        "    row = ActuacionGridRowIn.model_validate(_legacy_put_row_dict(act, **row_extra))\n"
        "    actualizar_actuacion(int(act.id), map_actuacion_row(row), actor_user_id=actor_user_id)",
    )

    text = add_actor_multiline(text)
    text = re.sub(
        r"_put_actuacion\(act\)",
        "_put_actuacion(act, actor_user_id=actor_user_id)",
        text,
    )
    text = re.sub(
        r"_put_actuacion\(act,",
        "_put_actuacion(act, actor_user_id=actor_user_id,",
        text,
    )
    text = text.replace(
        "actor_user_id=actor_user_id, actor_user_id=actor_user_id",
        "actor_user_id=actor_user_id",
    )

    keep_app = {
        "test_rechaza_contrato_v1_ids",
        "test_personas_sin_carnet_negativo_rechazado",
        "test_rechaza_item_sin_respuesta",
        "test_migration_v2_schema",
        "test_migration_tipo_si_no_schema",
    }

    lines = text.splitlines()
    new_lines: list[str] = []
    in_ctx = False
    for line in lines:
        m = re.match(r"def (test_\w+)\(app, items_catalogo\):", line)
        if m and m.group(1) not in keep_app:
            line = line.replace("(app, items_catalogo)", "(app_ctx, items_catalogo, actor_user_id)")
        if line.strip() == "with app.app_context():":
            in_ctx = True
            continue
        if in_ctx:
            if line.startswith("        "):
                new_lines.append(line[4:])
            else:
                new_lines.append(line)
                in_ctx = False
            continue
        new_lines.append(line)

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Updated {path}")


if __name__ == "__main__":
    main()
