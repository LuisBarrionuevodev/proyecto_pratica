"""PERF.1-B — EXPLAIN diagnóstico (solo lectura)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import exists, and_, text

from app import create_app
from app.database import db
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    _ESTADOS_INICIADOR_BANDEJA_REINSPECCION_NOTIF,
    _subq_reinsp_exitosa_misma_notificacion,
    _subq_reinsp_via_ruta_item_bloqueante_iniciador,
)
from app.models import Actuaciones, IniciadorRuta, Notificacion, RutaItem, Domicilio, OrdenTrabajo
from app.domains.actuaciones.services.notificacion_iniciador_service import filtro_sql_actuacion_base_workflow_documental


def explain_sql(label: str, sql: str, params: dict | None = None) -> None:
    dialect = db.engine.dialect.name
    print(f"\n=== {label} ({dialect}) ===")
    if dialect == "mysql":
        rows = db.session.execute(text(f"EXPLAIN {sql}"), params or {}).fetchall()
        for r in rows:
            print(dict(r._mapping))
    elif dialect == "sqlite":
        plan = db.session.execute(text(f"EXPLAIN QUERY PLAN {sql}"), params or {}).fetchall()
        for r in plan:
            print(r)
    else:
        print("dialect not supported for EXPLAIN:", dialect)


def main() -> None:
    app = create_app({"TESTING": True})
    with app.app_context():
        dialect = db.engine.dialect.name
        print("dialect:", dialect)

        # Base notificacion bandeja
        q_base = (
            Actuaciones.query.filter(Actuaciones.notificacion_id.isnot(None))
            .order_by(Actuaciones.id.desc())
            .limit(50)
        )
        explain_sql("notif_base", str(q_base.statement.compile(dialect=db.engine.dialect)))

        # Reinspeccion core
        today = date.today()
        subq_reinsp = _subq_reinsp_exitosa_misma_notificacion()
        subq_item_realizado = exists().where(
            and_(
                RutaItem.iniciador_ruta_id == IniciadorRuta.id,
                RutaItem.deleted_at.is_(None),
                RutaItem.estado_ruta_item == "FINALIZADO",
                RutaItem.estado_ejecucion == "REALIZADO",
            )
        )
        subq_reinsp_via_item = _subq_reinsp_via_ruta_item_bloqueante_iniciador()
        q_rein = (
            Actuaciones.query.join(IniciadorRuta, IniciadorRuta.actuacion_id == Actuaciones.id)
            .join(Notificacion, Notificacion.id == Actuaciones.notificacion_id)
            .filter(filtro_sql_actuacion_base_workflow_documental())
            .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
            .filter(IniciadorRuta.estado_iniciador.in_(_ESTADOS_INICIADOR_BANDEJA_REINSPECCION_NOTIF))
            .filter(IniciadorRuta.deleted_at.is_(None))
            .filter(Notificacion.deleted_at.is_(None))
            .filter(Notificacion.fecha_vencimiento.isnot(None))
            .filter(Notificacion.fecha_vencimiento <= today)
            .filter(~subq_reinsp)
            .filter(~subq_item_realizado)
            .filter(~subq_reinsp_via_item)
            .order_by(Actuaciones.id.desc())
            .limit(50)
        )
        explain_sql("reinspeccion", str(q_rein.statement.compile(dialect=db.engine.dialect)))

        # Spike calle EXISTS
        from sqlalchemy import func

        q_calle = (
            Actuaciones.query.filter(Actuaciones.notificacion_id.isnot(None))
            .filter(
                exists().where(
                    and_(
                        Domicilio.id == Actuaciones.domicilio_id,
                        func.lower(Domicilio.calle).contains("san martin"),
                    )
                )
            )
            .limit(50)
        )
        explain_sql("calle_exists", str(q_calle.statement.compile(dialect=db.engine.dialect)))

        # Spike OT exact
        q_ot = (
            Actuaciones.query.join(OrdenTrabajo, Actuaciones.orden_trabajo_id == OrdenTrabajo.id)
            .filter(Actuaciones.notificacion_id.isnot(None))
            .filter(OrdenTrabajo.numero_acta == "092834")
            .limit(50)
        )
        explain_sql("ot_exact", str(q_ot.statement.compile(dialect=db.engine.dialect)))

        # Indexes inventory
        if dialect == "mysql":
            for table in ("actuaciones", "notificacion", "domicilio", "orden_trabajo", "iniciador_ruta", "ruta_item"):
                print(f"\n-- indexes {table} --")
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
                    print(dict(r._mapping))


if __name__ == "__main__":
    main()
