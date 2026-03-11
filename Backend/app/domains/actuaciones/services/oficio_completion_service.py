from __future__ import annotations

from typing import Any, Dict

from app.database import db
from app.domains.actuaciones.attach.oficio import attach_oficio
from app.domains.actuaciones.services.oficio_iniciador_service import get_or_create_iniciador_from_oficio
from app.models import Actuaciones, Expediente, JuzgadoCatalogo
from app.utils.actas import acta_6


def complete_oficio_from_actuacion(actuacion_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Completa el flujo de oficio desde una actuación de comprobación.

    - Valida rama COMPROBACION.
    - Exige expediente original existente.
    - Crea o actualiza Oficio.
    - Crea expediente de respuesta de oficio sin sobrescribir el original.

    Errores:
    - LookupError: 404 (actuación, juzgado o expediente original no encontrados)
    - ValueError: 400 (payload inválido)
    - RuntimeError: 409 (conflictos de consistencia/duplicados)
    """
    act = db.session.get(Actuaciones, actuacion_id)
    if not act:
        raise LookupError("Actuación no encontrada")

    if act.comprobacion_id is None:
        raise RuntimeError("La actuación no pertenece al flujo COMPROBACION")

    expediente_original = (
        Expediente.query
        .filter_by(comprobacion_id=act.comprobacion_id, oficio_id=None)
        .order_by(Expediente.id.asc())
        .first()
    )
    if not expediente_original:
        raise LookupError("No existe expediente original para esta comprobación")

    juzgado = db.session.get(JuzgadoCatalogo, int(data["juzgado_id"]))
    if not juzgado:
        raise LookupError("Juzgado no encontrado")

    ya_respuesta = (
        Expediente.query
        .filter(
            Expediente.comprobacion_id == act.comprobacion_id,
            Expediente.oficio_id.isnot(None),
        )
        .first()
    )
    if ya_respuesta:
        raise RuntimeError("Ya existe expediente de respuesta de oficio para esta actuación")

    numero_exp_oficio = acta_6(data.get("numero_expediente_oficio"))
    fecha_expediente_oficio = data.get("fecha_expediente_oficio")
    if not numero_exp_oficio or fecha_expediente_oficio is None:
        raise ValueError("numero_expediente_oficio y fecha_expediente_oficio son obligatorios")
    anio_exp_oficio = str(fecha_expediente_oficio.year)

    dup_expediente = Expediente.query.filter_by(
        numero_expediente=numero_exp_oficio,
        anio=anio_exp_oficio,
    ).first()
    if dup_expediente:
        raise RuntimeError("Ese expediente de respuesta de oficio ya existe")

    fecha_oficio = data["fecha_oficio"]
    oficio = attach_oficio(
        {
            "numero": data["numero_oficio"],
            "anio": int(fecha_oficio.year),
            "fecha_oficio": fecha_oficio,
            "juzgado_id": int(data["juzgado_id"]),
            "causa": data.get("causa"),
        },
        comprobacion_id=act.comprobacion_id,
    )
    if not oficio:
        raise ValueError("No se pudo crear/actualizar oficio")

    expediente_respuesta = Expediente(
        numero_expediente=numero_exp_oficio,
        fecha_expediente=fecha_expediente_oficio,
        anio=anio_exp_oficio,
        tipo_expediente="RESPUESTA_OFICIO",
        comprobacion_id=act.comprobacion_id,
        oficio_id=oficio.id,
    )
    db.session.add(expediente_respuesta)
    db.session.flush()

    iniciador = get_or_create_iniciador_from_oficio(
        actuacion=act,
        oficio=oficio,
        expediente_respuesta=expediente_respuesta,
    )
    db.session.add(iniciador)
    db.session.commit()

    return {
        "actuacion": act,
        "oficio": oficio,
        "expediente_original": expediente_original,
        "expediente_respuesta_oficio": expediente_respuesta,
        "iniciador_ruta": iniciador,
    }

