"""Dry-run read-only: clasificación oficios para backfill ACT-HIST.5 en sandbox."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TIPOS_INI_OFICIO = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)


def _classify_oficios(engine) -> dict[str, int]:
    counts = {"MATERIALIZADO": 0, "PENDIENTE_DOMICILIO": 0, "PENDIENTE_MATERIALIZACION": 0}
    tipos_sql = ", ".join(f"'{t}'" for t in TIPOS_INI_OFICIO)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT o.id AS oficio_id, o.comprobacion_id
                FROM oficio o
                WHERE o.deleted_at IS NULL
                """
            )
        ).fetchall()
        for row in rows:
            oficio_id = int(row.oficio_id)
            comprobacion_id = row.comprobacion_id
            has_ini = conn.execute(
                text(
                    f"""
                    SELECT 1 FROM iniciador_ruta i
                    WHERE i.oficio_id = :oid
                      AND i.deleted_at IS NULL
                      AND i.tipo_iniciador IN ({tipos_sql})
                    LIMIT 1
                    """
                ),
                {"oid": oficio_id},
            ).first()
            if has_ini:
                estado = "MATERIALIZADO"
            else:
                act_row = conn.execute(
                    text(
                        """
                        SELECT a.domicilio_id
                        FROM actuaciones a
                        WHERE a.comprobacion_id = :cid
                        ORDER BY a.id DESC
                        LIMIT 1
                        """
                    ),
                    {"cid": comprobacion_id},
                ).first()
                domicilio_id = act_row.domicilio_id if act_row else None
                estado = "PENDIENTE_DOMICILIO" if domicilio_id is None else "PENDIENTE_MATERIALIZACION"
            counts[estado] += 1
    return counts


def main() -> int:
    load_dotenv(BACKEND_ROOT / ".env")
    sandbox_url = (os.getenv("SANDBOX_DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if "sandbox" not in sandbox_url.lower():
        print("SANDBOX_DATABASE_URL no apunta a sandbox; abortando dry-run.")
        return 1
    engine = create_engine(sandbox_url)
    counts = _classify_oficios(engine)
    comprobaciones_sin_exp = 0
    with engine.connect() as conn:
        comprobaciones_sin_exp = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM comprobacion c
                WHERE c.deleted_at IS NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM expediente e
                    WHERE e.comprobacion_id = c.id
                      AND e.oficio_id IS NULL
                      AND e.deleted_at IS NULL
                  )
                """
            )
        ).scalar()
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": sandbox_url.split("/")[-1],
        "oficios_classification_dry_run": counts,
        "comprobaciones_sin_expediente_envio": int(comprobaciones_sin_exp or 0),
        "note": "Dry-run only; no writes.",
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
