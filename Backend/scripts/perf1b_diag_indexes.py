"""PERF.1-B — índices + EXPLAIN."""
from app import create_app
from app.database import db
from sqlalchemy import text

app = create_app({"TESTING": True})
with app.app_context():
    for table in ("actuaciones", "notificacion", "domicilio", "orden_trabajo", "iniciador_ruta", "ruta_item"):
        print(f"\n-- {table} --")
        rows = db.session.execute(
            text(
                "SELECT INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX, NON_UNIQUE "
                "FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                "ORDER BY INDEX_NAME, SEQ_IN_INDEX"
            ),
            {"t": table},
        ).fetchall()
        for r in rows:
            print(f"  {r[0]}: {r[1]} (seq={r[2]})")

    print("\nEXPLAIN notif_base:")
    for r in db.session.execute(
        text(
            "EXPLAIN SELECT id FROM actuaciones "
            "WHERE notificacion_id IS NOT NULL ORDER BY id DESC LIMIT 50"
        )
    ).fetchall():
        print(dict(r._mapping))

    print("\nEXPLAIN reinspeccion_core:")
    for r in db.session.execute(
        text(
            "EXPLAIN SELECT a.id FROM actuaciones a "
            "INNER JOIN iniciador_ruta ir ON ir.actuacion_id = a.id "
            "INNER JOIN notificacion n ON n.id = a.notificacion_id "
            "WHERE ir.tipo_iniciador = 'REINSPECCION_NOTIFICACION' "
            "AND ir.deleted_at IS NULL AND n.deleted_at IS NULL "
            "AND n.fecha_vencimiento IS NOT NULL "
            "ORDER BY a.id DESC LIMIT 50"
        )
    ).fetchall():
        print(dict(r._mapping))

    print("\nEXPLAIN calle_exists:")
    for r in db.session.execute(
        text(
            "EXPLAIN SELECT a.id FROM actuaciones a "
            "WHERE a.notificacion_id IS NOT NULL AND EXISTS ("
            "  SELECT 1 FROM domicilio d WHERE d.id = a.domicilio_id "
            "  AND LOWER(d.calle) LIKE '%san martin%'"
            ") LIMIT 50"
        )
    ).fetchall():
        print(dict(r._mapping))

    print("\nEXPLAIN ot_join:")
    for r in db.session.execute(
        text(
            "EXPLAIN SELECT a.id FROM actuaciones a "
            "INNER JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id "
            "WHERE a.notificacion_id IS NOT NULL AND ot.numero_acta = '092834' LIMIT 50"
        )
    ).fetchall():
        print(dict(r._mapping))
