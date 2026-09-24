"""PERF.1-C — índices + EXPLAIN Comprobaciones (solo lectura)."""
from __future__ import annotations

from app import create_app
from app.database import db
from sqlalchemy import text

TABLES = (
    "actuaciones",
    "comprobacion",
    "expediente",
    "oficio",
    "domicilio",
    "contribuyente",
    "iniciador_ruta",
    "orden_trabajo",
)

QUERIES = {
    "comp_base": (
        "SELECT a.id FROM actuaciones a "
        "WHERE a.comprobacion_id IS NOT NULL ORDER BY a.id DESC LIMIT 50"
    ),
    "sin_expediente_envio": (
        "SELECT a.id FROM actuaciones a "
        "WHERE a.comprobacion_id IS NOT NULL "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM expediente e "
        "  WHERE e.comprobacion_id = a.comprobacion_id "
        "  AND e.oficio_id IS NULL AND e.deleted_at IS NULL"
        ") ORDER BY a.id DESC LIMIT 50"
    ),
    "pendiente_oficio": (
        "SELECT a.id FROM actuaciones a "
        "WHERE a.comprobacion_id IS NOT NULL "
        "AND EXISTS ("
        "  SELECT 1 FROM expediente e "
        "  WHERE e.comprobacion_id = a.comprobacion_id "
        "  AND e.oficio_id IS NULL AND e.deleted_at IS NULL"
        ") "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM expediente e2 "
        "  WHERE e2.comprobacion_id = a.comprobacion_id "
        "  AND e2.oficio_id IS NOT NULL AND e2.deleted_at IS NULL"
        ") ORDER BY a.id DESC LIMIT 50"
    ),
    "recorrido_calle_exists": (
        "SELECT a.id FROM actuaciones a "
        "WHERE a.comprobacion_id IS NOT NULL AND EXISTS ("
        "  SELECT 1 FROM domicilio d WHERE d.id = a.domicilio_id "
        "  AND LOWER(d.calle) LIKE '%san martin%'"
        ") LIMIT 50"
    ),
    "recorrido_acta_exists": (
        "SELECT a.id FROM actuaciones a "
        "WHERE a.comprobacion_id IS NOT NULL AND EXISTS ("
        "  SELECT 1 FROM comprobacion c WHERE c.id = a.comprobacion_id "
        "  AND LOWER(c.numero_acta) LIKE '%123%'"
        ") LIMIT 50"
    ),
    "recorrido_oficio_exists": (
        "SELECT a.id FROM actuaciones a "
        "WHERE a.comprobacion_id IS NOT NULL AND EXISTS ("
        "  SELECT 1 FROM oficio o WHERE o.comprobacion_id = a.comprobacion_id "
        "  AND o.deleted_at IS NULL AND LOWER(o.numero_oficio) LIKE '%202%'"
        ") LIMIT 50"
    ),
    "recorrido_expediente_exists": (
        "SELECT a.id FROM actuaciones a "
        "WHERE a.comprobacion_id IS NOT NULL AND EXISTS ("
        "  SELECT 1 FROM expediente e WHERE e.comprobacion_id = a.comprobacion_id "
        "  AND e.deleted_at IS NULL AND LOWER(e.numero_expediente) LIKE '%123%'"
        ") LIMIT 50"
    ),
    "comp_mes_anio_join": (
        "SELECT a.id FROM actuaciones a "
        "INNER JOIN comprobacion c ON c.id = a.comprobacion_id "
        "WHERE c.mes = 3 AND c.anio = 2026 ORDER BY a.id DESC LIMIT 50"
    ),
}


def main() -> None:
    app = create_app({"TESTING": True})
    with app.app_context():
        for table in TABLES:
            print(f"\n-- {table} --")
            rows = db.session.execute(
                text(
                    "SELECT INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX "
                    "FROM information_schema.STATISTICS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                    "ORDER BY INDEX_NAME, SEQ_IN_INDEX"
                ),
                {"t": table},
            ).fetchall()
            if not rows:
                print("  (sin índices o tabla inexistente)")
            for r in rows:
                print(f"  {r[0]}: {r[1]} (seq={r[2]})")

        for label, sql in QUERIES.items():
            print(f"\nEXPLAIN {label}:")
            for r in db.session.execute(text(f"EXPLAIN {sql}")).fetchall():
                print(dict(r._mapping))


if __name__ == "__main__":
    main()
