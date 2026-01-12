from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import (
    Actuaciones,
    Inspeccion,
    Notificacion,
    Comprobacion,
    Clausura,
    Decomiso,
    Expediente,
    Oficio,
)

from app.utils.actas import acta_6
from app.services.actuaciones.catalogs.motivo import get_motivo_o_falla
from app.services.actuaciones.attach.uniqueness import (
    asegurar_acta_libre_para_actuacion,
    asegurar_acta_no_usada_en_otra,
)


# =========================================================
# Reglas de unicidad de actas principales
# =========================================================


# =========================================================
# Attach actas
# =========================================================

def attach_inspeccion(actuacion: Actuaciones, acta_num: Optional[Any], crear: bool = True):
    if not acta_num:
        return

    numero = acta_6(acta_num)
    if not numero:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Inspeccion, numero, anio, actuacion.id)
    else:
        asegurar_acta_libre_para_actuacion(Inspeccion, numero, anio, actuacion.id)

    actual = Inspeccion.query.filter_by(actuacion_id=actuacion.id).first()
    if actual:
        actual.numero_acta = numero
        actual.anio = anio
        actual.mes = mes
        db.session.add(actual)
        return

    ins = Inspeccion.query.filter_by(numero_acta=numero, anio=anio).first()
    if ins:
        # si existe pero era de otra actuación, asegurar_* ya lo frenó
        ins.actuacion_id = actuacion.id
        db.session.add(ins)
        return

    ins = Inspeccion(numero_acta=numero, anio=anio, mes=mes, actuacion_id=actuacion.id)
    db.session.add(ins)


def attach_notificacion(actuacion: Actuaciones, data: Optional[Dict[str, Any]]):
    """
    Notificación:
    - Se identifica por numero_acta + anio
    - Motivos vienen como lista y SON catálogo (tabla Motivo)
    """
    if not data:
        return

    acta_num = acta_6(data.get("acta_num"))
    if not acta_num:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    # 1) si ya tiene notificación asociada, actualizamos esa
    if actuacion.notificacion_id:
        noti = Notificacion.query.get(actuacion.notificacion_id)
        if noti:
            existente = Notificacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
            if existente and existente.id != noti.id:
                raise ValueError("Acta de notificación ya asociada a otra actuación.")

            noti.numero_acta = acta_num
            noti.anio = anio
            noti.mes = mes

            # 👇 clave: si viene el campo (aunque sea []), lo reflejamos
            if "motivos" in data:
                motivos = data.get("motivos") or []
                noti.motivos = [get_motivo_o_falla(m) for m in motivos]

            db.session.add(noti)
            return

    # 2) si no tenía, buscamos por acta+anio
    noti = Notificacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
    if not noti:
        noti = Notificacion(numero_acta=acta_num, anio=anio, mes=mes)
        db.session.add(noti)
        db.session.flush()

    if "motivos" in data:
        motivos = data.get("motivos") or []
        noti.motivos = [get_motivo_o_falla(m) for m in motivos]
        db.session.flush()  # 👈 útil para ver inserts antes del commit

    if actuacion.tipo is not None:
        existe_mismo_tipo = (
            Actuaciones.query
            .filter(
            Actuaciones.id != actuacion.id,
            Actuaciones.anio == anio,
            Actuaciones.tipo == actuacion.tipo,
            Actuaciones.notificacion_id == noti.id,
            )
            .first()
    )
    if existe_mismo_tipo:
        raise ValueError(
            f"La Notificación {acta_num}/{anio} ya está asociada a otra actuación del mismo tipo ({actuacion.tipo})."
        )
    actuacion.notificacion_id = noti.id


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


def attach_clausura(actuacion: Actuaciones, data: Optional[Dict[str, Any]], crear: bool = True):
    if not data or not data.get("acta_num"):
        return

    numero = acta_6(data["acta_num"])
    if not numero:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Clausura, numero, anio, actuacion.id)
    else:
        asegurar_acta_libre_para_actuacion(Clausura, numero, anio, actuacion.id)

    actual = Clausura.query.filter_by(actuacion_id=actuacion.id).first()
    if actual:
        actual.numero_acta = numero
        actual.anio = anio
        actual.mes = mes
        db.session.add(actual)
        return

    cl = Clausura.query.filter_by(numero_acta=numero, anio=anio).first()
    if cl:
        cl.actuacion_id = actuacion.id
        db.session.add(cl)
        return

    cl = Clausura(numero_acta=numero, anio=anio, mes=mes, actuacion_id=actuacion.id)
    db.session.add(cl)


def attach_decomiso(actuacion: Actuaciones, data: Optional[Dict[str, Any]], crear: bool = True):
    if not data or not data.get("acta_num"):
        return

    numero = acta_6(data["acta_num"])
    if not numero:
        return

    kilos = data.get("kilos_total")
    if kilos is None:
        raise ValueError("Kilos de decomiso es obligatorio.")
    try:
        kilos = float(kilos)
    except Exception:
        raise ValueError("Kilos de decomiso inválido.")
    if kilos <= 0:
        raise ValueError("Kilos de decomiso debe ser > 0.")

    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Decomiso, numero, anio, actuacion.id)
    else:
        asegurar_acta_libre_para_actuacion(Decomiso, numero, anio, actuacion.id)

    actual = Decomiso.query.filter_by(actuacion_id=actuacion.id).first()
    if actual:
        actual.numero_acta = numero
        actual.anio = anio
        actual.mes = mes
        actual.cantidad = kilos
        db.session.add(actual)
        return

    dec = Decomiso.query.filter_by(numero_acta=numero, anio=anio).first()
    if dec:
        dec.actuacion_id = actuacion.id
        dec.mes = mes
        dec.cantidad = kilos
        db.session.add(dec)
        return

    dec = Decomiso(numero_acta=numero, anio=anio, mes=mes, cantidad=kilos, actuacion_id=actuacion.id)
    db.session.add(dec)


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
