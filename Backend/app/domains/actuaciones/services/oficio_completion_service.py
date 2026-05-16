from __future__ import annotations

from typing import Any, Dict

from app.database import db
from app.domains.actuaciones.attach.oficio import attach_oficio
from app.domains.actuaciones.queries.expediente_vigente import expedientes_vigentes
from app.domains.actuaciones.services.expediente_reactivacion_service import (
    aplicar_reactivacion_respuesta_oficio,
    buscar_expediente_respuesta_oficio_reactivable,
)
from app.domains.actuaciones.presenters.actuacion_presenters import expediente_envio_por_comprobacion
from app.domains.actuaciones.services.oficio_iniciador_service import (
    get_or_create_iniciador_from_oficio,
)
from app.models import Actuaciones, Expediente, JuzgadoCatalogo
from app.utils.actas import acta_6


def complete_oficio_from_actuacion(actuacion_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    **Esperando oficio:** flujo sobre actuación con comprobación.

    - Valida rama COMPROBACION.
    - Exige **expediente de envío** (`oficio_id` NULL) ya creado.
    - Crea o actualiza `Oficio` (misma comprobación) vía `attach_oficio`.
    - Crea **expediente de respuesta de oficio** sin modificar el expediente de envío, o **reactiva** el
      soft-deleted del mismo ``oficio_id``/comprobación si coincide número/año del expediente de respuesta.
    - La fecha del expediente de respuesta se alinea siempre con ``fecha_oficio`` (una sola fecha operativa).
    - Materializa (idempotente) ``IniciadorRuta`` tipo ``REINSPECCION_OFICIO`` vía
      ``get_or_create_iniciador_from_oficio`` para que el caso entre en planificación de rutas
      (mismo criterio de negocio que el servicio dedicado; no duplica si ya existe uno activo).

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

    expediente_original = expediente_envio_por_comprobacion(int(act.comprobacion_id))
    if not expediente_original:
        raise LookupError("No existe expediente original para esta comprobación")

    juzgado = db.session.get(JuzgadoCatalogo, int(data["juzgado_id"]))
    if not juzgado:
        raise LookupError("Juzgado no encontrado")

    ya_respuesta = (
        Expediente.query.filter(
            Expediente.comprobacion_id == act.comprobacion_id,
            Expediente.oficio_id.isnot(None),
            Expediente.deleted_at.is_(None),
        ).first()
    )
    if ya_respuesta:
        raise RuntimeError("Ya existe expediente de respuesta de oficio para esta actuación")

    numero_exp_oficio = acta_6(data.get("numero_expediente_oficio"))
    fecha_oficio = data["fecha_oficio"]
    fecha_expediente_oficio = data.get("fecha_expediente_oficio") or fecha_oficio
    if fecha_expediente_oficio != fecha_oficio:
        fecha_expediente_oficio = fecha_oficio
    if not numero_exp_oficio or fecha_expediente_oficio is None:
        raise ValueError("numero_expediente_oficio y fecha_expediente_oficio son obligatorios")
    anio_exp_oficio = str(fecha_expediente_oficio.year)

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

    reactivable = buscar_expediente_respuesta_oficio_reactivable(
        comprobacion_id=int(act.comprobacion_id),
        oficio_id=int(oficio.id),
        numero_expediente=numero_exp_oficio,
        anio=anio_exp_oficio,
    )
    if reactivable:
        dup_otro = (
            expedientes_vigentes(
                Expediente.query.filter_by(
                    numero_expediente=numero_exp_oficio,
                    anio=anio_exp_oficio,
                ).filter(Expediente.id != reactivable.id)
            ).first()
        )
        if dup_otro:
            raise RuntimeError("Ese expediente de respuesta de oficio ya existe")
        aplicar_reactivacion_respuesta_oficio(
            reactivable,
            fecha_expediente=fecha_expediente_oficio,
            anio_str=anio_exp_oficio,
        )
        db.session.add(reactivable)
        expediente_respuesta = reactivable
    else:
        dup_expediente = (
            expedientes_vigentes(
                Expediente.query.filter_by(
                    numero_expediente=numero_exp_oficio,
                    anio=anio_exp_oficio,
                )
            ).first()
        )
        if dup_expediente:
            raise RuntimeError("Ese expediente de respuesta de oficio ya existe")

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

    iniciador_ruta = get_or_create_iniciador_from_oficio(
        actuacion=act,
        oficio=oficio,
        expediente_respuesta=expediente_respuesta,
    )
    if iniciador_ruta.id is None:
        db.session.add(iniciador_ruta)

    db.session.commit()

    return {
        "actuacion": act,
        "oficio": oficio,
        "expediente_original": expediente_original,
        "expediente_respuesta_oficio": expediente_respuesta,
        "iniciador_ruta": iniciador_ruta,
    }

