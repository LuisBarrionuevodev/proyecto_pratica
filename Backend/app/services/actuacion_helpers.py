from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import (
    Actuaciones,
    Comprobacion,
    Expediente,
    Oficio,
)

from app.utils.actas import acta_6


def attach_comprobacion(actuacion: Actuaciones, data: Optional[Dict[str, Any]]):
    if not data:
        return

    acta_num = acta_6(data.get("acta_num"))
    if not acta_num:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    motivo = (data.get("motivo") or "").strip()
    if not motivo:
        raise ValueError("Motivo de comprobación es obligatorio.")

    # 1) Conseguir/crear Comprobacion por (numero_acta, anio)
    comp = Comprobacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
    if not comp:
        comp = Comprobacion(numero_acta=acta_num, anio=anio, mes=mes, motivo=motivo)
        db.session.add(comp)
        db.session.flush()
    else:
        comp.mes = mes
        comp.motivo = motivo
        db.session.add(comp)

    db.session.flush()

    # 2) Regla negocio: misma comprobación NO puede repetirse en (anio,tipo)
    if actuacion.tipo is not None:
        existe_mismo_tipo = (
            Actuaciones.query
            .filter(
                Actuaciones.id != actuacion.id,
                Actuaciones.anio == anio,
                Actuaciones.tipo == actuacion.tipo,
                Actuaciones.comprobacion_id == comp.id,
            )
            .first()
        )
        if existe_mismo_tipo:
            raise ValueError(
                f"La Comprobación {acta_num}/{anio} ya está asociada a otra actuación del mismo tipo ({actuacion.tipo})."
            )

    actuacion.comprobacion_id = comp.id

# =========================================================
# Oficio / Expediente
# =========================================================

def attach_oficio(data: Optional[Dict[str, Any]],comprobacion_id: Optional[int]) -> Optional[Oficio]:
    """
    Oficio:
    - Se identifica por numero + anio
    """
    if not data:
        return None

    numero = data.get("numero")
    anio = data.get("anio")

    if not numero or anio is None:
        raise ValueError("Si cargás oficio, número y año son obligatorios.")

    of = Oficio.query.filter_by(numero_oficio=str(numero).strip(), anio=int(anio)).first()
    if of:
        return of

    of = Oficio(
        numero_oficio=str(numero).strip(),
        anio=int(anio),
        causa=data.get("causa"),
        comprobacion_id=comprobacion_id,
    )
    db.session.add(of)
    db.session.flush()
    return of


def attach_expediente(
    data: Optional[Dict[str, Any]],
    comprobacion_id: Optional[int],
    oficio_id: Optional[int],
) -> Optional[Expediente]:
    """
    Expediente:
    - Se identifica por numero + anio (anio en DB es varchar)
    """
    if not data:
        return None

    numero = acta_6(data.get("numero"))
    anio = data.get("anio")

    if not numero or anio is None:
        raise ValueError("Si cargás expediente, número y año son obligatorios.")

    anio_str = str(anio)

    ex = Expediente.query.filter_by(numero_expediente=numero, anio=anio_str).first()
    if ex:
        return ex

    ex = Expediente(
        numero_expediente=numero,
        anio=anio_str,
        comprobacion_id=comprobacion_id,
        oficio_id=oficio_id,
    )
    db.session.add(ex)
    db.session.flush()
    return ex
