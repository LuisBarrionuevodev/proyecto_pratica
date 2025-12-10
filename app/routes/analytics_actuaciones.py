from __future__ import annotations

from flask import Blueprint, jsonify, request
from sqlalchemy import func, case

from app.database import db
from app.models import Actuaciones, Expediente

# Si tenés estos modelos, mejor importarlos.
# Si todavía no están, dejalos comentados y ajustamos después.
# from app.models import Clausura, Domicilio, Rubro

dashboard = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard.get("/resumen")
def dashboard_resumen():
    # -------------------------
    # 1) total actuaciones
    # -------------------------
    actuaciones_count = Actuaciones.query.count() or 0

    # -------------------------
    # 2) pendientes notificación
    # - cuenta notificacion_id que tenga:
    #   >= 1 INSPECCION
    #   y 0 REINSPECCION
    # -------------------------
    notif_subq = (
        db.session.query(
            Actuaciones.notificacion_id.label("nid"),
            func.sum(
                case((Actuaciones.tipo == "INSPECCION", 1), else_=0)
            ).label("ins"),
            func.sum(
                case((Actuaciones.tipo == "REINSPECCION", 1), else_=0)
            ).label("reins"),
        )
        .filter(Actuaciones.notificacion_id.isnot(None))
        .group_by(Actuaciones.notificacion_id)
        .subquery()
    )

    pendientes_count = (
        db.session.query(func.count())
        .select_from(notif_subq)
        .filter(notif_subq.c.ins >= 1)
        .filter(notif_subq.c.reins == 0)
        .scalar()
    ) or 0

    # -------------------------
    # 3) vinculación acta pendiente
    # - tiene comprobacion_id
    # - NO existe expediente con esa comprobacion_id
    # -------------------------
    exp_exists = (
        db.session.query(Expediente.id)
        .filter(Expediente.comprobacion_id == Actuaciones.comprobacion_id)
        .exists()
    )

    vinculacion_acta_pendiente = (
        db.session.query(func.count(func.distinct(Actuaciones.comprobacion_id)))
        .filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(~exp_exists)
        .scalar()
    ) or 0

    # -------------------------
    # 4) vinculación oficio pendiente
    # - expediente con comprobacion_id
    # - sin oficio_id
    # -------------------------
    vinculacion_oficio_pendiente = (
        db.session.query(func.count(Expediente.id))
        .filter(Expediente.comprobacion_id.isnot(None))
        .filter(Expediente.oficio_id.is_(None))
        .scalar()
    ) or 0

    return jsonify({
        "actuaciones": actuaciones_count,
        "relevamientos": 0,  # por ahora
        "pendientes": pendientes_count,
        "vinculacionActaPendiente": vinculacion_acta_pendiente,
        "vinculacionOficioPendiente": vinculacion_oficio_pendiente,
    }), 200


@dashboard.get("/actuaciones-por-mes")
def dashboard_actuaciones_por_mes():
    anio = request.args.get("anio", type=int)
    if not anio:
        return jsonify({"detail": "anio es obligatorio"}), 400

    rows = (
        db.session.query(
            Actuaciones.mes,
            func.count(Actuaciones.id).label("total")
        )
        .filter(Actuaciones.anio == anio)
        .group_by(Actuaciones.mes)
        .order_by(Actuaciones.mes.asc())
        .all()
    )

    # devolvemos 12 meses completos para que Recharts no se rompa
    mapa = {m: t for m, t in rows}
    data = [{"mes": m, "actu": int(mapa.get(m, 0))} for m in range(1, 13)]

    return jsonify(data), 200


@dashboard.get("/rubros-clausura")
def dashboard_rubros_clausura():
    """
    Pie chart de rubros clausurados.

    Este endpoint asume que:
    - Actuaciones tiene relacion con domicilio
    - domicilio tiene relacion con rubro
    - clausura existe como relacion 1:1 en Actuaciones

    Si tus nombres reales difieren, ajustás los joins.
    """

    anio = request.args.get("anio", type=int)
    if not anio:
        return jsonify({"detail": "anio es obligatorio"}), 400

    # ✅ Opción robusta sin depender de modelos explícitos:
    # usamos joins "por atributo" contra relaciones ya conocidas en Actuaciones.
    try:
        rows = (
            db.session.query(
                func.coalesce(db.text("rubro.nombre"), "Sin rubro").label("rubro"),
                func.count(Actuaciones.id).label("clausuras"),
            )
            .select_from(Actuaciones)
            # join a domicilio y rubro usando los nombres de tablas en texto para evitar crash
            # si SQLAlchemy todavía no tiene las relaciones correctamente declaradas.
            .join(db.text("domicilio"), db.text("domicilio.id = actuaciones.domicilio_id"))
            .join(db.text("rubro"), db.text("rubro.id = domicilio.rubro_id"))
            .join(db.text("clausura"), db.text("clausura.actuaciones_id = actuaciones.id"))
            .filter(Actuaciones.anio == anio)
            .group_by(db.text("rubro.nombre"))
            .order_by(func.count(Actuaciones.id).desc())
            .all()
        )

        data = [{"rubro": r[0], "clausuras": int(r[1])} for r in rows]
        return jsonify(data), 200

    except Exception:
        # fallback simple: si todavía no tenés lista la estructura de clausura/rubro,
        # devolvemos vacío sin romper el dashboard.
        return jsonify([]), 200
