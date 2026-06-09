from __future__ import annotations

from typing import Any

from sqlalchemy import or_

from app.database import db
from app.domains.actuaciones.services.oficio_editable_service import evaluar_editable_oficio
from app.models import Expediente, IniciadorRuta, JuzgadoCatalogo, Oficio


def list_oficios_by_comprobacion(comprobacion_id: int) -> list[Oficio]:
    """
    Lista oficios activos asociados a una comprobación.

    Parámetros:
        comprobacion_id: FK de comprobación.

    Retorno:
        Lista ordenada por ``id`` ascendente (estable para UI legacy = primer oficio).

    Errores esperados:
        Ninguno; devuelve lista vacía si no hay oficios.
    """
    return (
        Oficio.query.filter_by(comprobacion_id=int(comprobacion_id))
        .filter(Oficio.deleted_at.is_(None))
        .order_by(Oficio.id.asc())
        .all()
    )


def _expediente_respuesta_activo(oficio_id: int) -> Expediente | None:
    return (
        Expediente.query.filter_by(oficio_id=int(oficio_id))
        .filter(
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            )
        )
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .first()
    )


def _iniciador_reinspeccion_oficio(oficio_id: int) -> IniciadorRuta | None:
    return (
        IniciadorRuta.query.filter_by(oficio_id=int(oficio_id))
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def oficio_comprobacion_item_payload(oficio: Oficio) -> dict[str, Any]:
    """
    Serializa un oficio con expediente de respuesta e iniciador (si existen) para PR4.

    Parámetros:
        oficio: fila ``Oficio`` activa.

    Retorno:
        Dict con campos del oficio más ``expediente_*`` e ``iniciador_*`` opcionales.
    """
    data = oficio.to_dict()
    if oficio.juzgado_id:
        j = db.session.get(JuzgadoCatalogo, int(oficio.juzgado_id))
        if j:
            data["tribunal"] = j.nombre
    ex = _expediente_respuesta_activo(oficio.id)
    if ex:
        data["expediente_id"] = ex.id
        data["expediente_numero"] = ex.numero_expediente
        data["expediente_anio"] = ex.anio
        data["fecha_expediente_respuesta"] = (
            ex.fecha_expediente.isoformat() if ex.fecha_expediente else None
        )
    policy = evaluar_editable_oficio(oficio.id)
    for key in (
        "iniciador_id",
        "iniciador_estado",
        "ruta_item_id",
        "ruta_estado",
        "estado_ejecucion",
        "editable",
        "bloqueado_motivo",
    ):
        if policy.get(key) is not None:
            data[key] = policy[key]
    if "editable" not in data:
        data["editable"] = policy.get("editable", True)
    return data


def oficios_comprobacion_payload(comprobacion_id: int) -> list[dict[str, Any]]:
    """
    Serializa oficios activos de una comprobación para API interna/PR4.

    Parámetros:
        comprobacion_id: FK de comprobación.

    Retorno:
        Lista de dicts con campos del oficio, expediente de respuesta e iniciador (si existen).
    """
    return [oficio_comprobacion_item_payload(oficio) for oficio in list_oficios_by_comprobacion(comprobacion_id)]
