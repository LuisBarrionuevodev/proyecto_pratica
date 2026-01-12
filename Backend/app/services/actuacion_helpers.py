from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.database import db
from app.models import (
    Actuaciones,
    OrdenTrabajo,
    Rubro,
    Contribuyente,
    Domicilio,
    Inspector,
    Inspeccion,
    Notificacion,
    Comprobacion,
    Clausura,
    Decomiso,
    Motivo,
    Expediente,
    Oficio,
)


# =========================================================
# Helpers de formato / fecha
# =========================================================

def acta_6(valor: Any) -> Optional[str]:
    """
    Normaliza numeros de acta/OT a 6 dígitos si son numéricos.
    Si viene vacío o None, devuelve None.
    """
    if valor is None:
        return None

    s = str(valor).strip()
    if not s:
        return None

    return s.zfill(6) if s.isdigit() else s


def parse_fecha_grid(fecha_str: Any) -> Tuple[int, int, datetime.date]:
    """
    Acepta:
      - "DD/MM/YYYY"
      - "YYYY-MM-DD"
    Devuelve: (mes, anio, date)
    """
    if fecha_str is None:
        raise ValueError("La fecha es obligatoria")

    s = str(fecha_str).strip()
    if not s:
        raise ValueError("La fecha es obligatoria")

    try:
        if "/" in s:
            dt = datetime.strptime(s, "%d/%m/%Y").date()
        else:
            dt = datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("Formato de fecha inválido. Usá DD/MM/YYYY o YYYY-MM-DD")

    return dt.month, dt.year, dt


# =========================================================
# Catálogos estrictos
# =========================================================

def get_rubro_o_falla(nombre: Optional[str]) -> Optional[Rubro]:
    """
    Rubro es catálogo:
    - si no viene -> None
    - si viene y no existe -> ValueError
    """
    if nombre is None:
        return None

    s = str(nombre).strip()
    if not s:
        return None

    s = " ".join(s.split())
    rubro = Rubro.query.filter_by(nombre=s).first()
    if not rubro:
        raise ValueError(f"Rubro no existe en catálogo: {s}")
    return rubro


def get_motivo_o_falla(nombre: str) -> Motivo:
    """
    Motivo es catálogo:
    - si no existe -> ValueError
    """
    s = (nombre or "").strip()
    if not s:
        raise ValueError("Motivo inválido (vacío).")

    m = Motivo.query.filter_by(nombre=s).first()
    if not m:
        raise ValueError(f"Motivo no existe en catálogo: {s}")
    return m


def get_inspectores_o_falla(nombres: List[str]) -> List[Inspector]:
    """
    Inspectores SON catálogo.
    Si un nombre no existe, rechazamos duro.
    """
    encontrados: List[Inspector] = []

    for n in nombres:
        s = (n or "").strip()
        if not s:
            continue
        ins = Inspector.query.filter_by(nombre=s).first()
        if not ins:
            raise ValueError(f"Inspector no existe en catálogo: {s}")
        encontrados.append(ins)

    return encontrados


# =========================================================
# Contribuyente + Domicilio
# =========================================================

def resolve_contribuyente(data: Optional[Dict[str, Any]]) -> Optional[Contribuyente]:
    """
    Contribuyente se identifica por documento.
    - Si no hay data -> None
    - Si hay apellido/nombre -> documento obligatorio
    - Si existe -> actualiza campos si cambiaron
    - Si no existe -> crea
    """
    if not data:
        return None

    doc = data.get("doc_nro")
    apellido = data.get("apellido")
    nombre = data.get("nombre")

    # coherencia: si hay datos de persona, doc obligatorio
    if (apellido or nombre) and not doc:
        raise ValueError("Documento del contribuyente es obligatorio.")

    if not doc:
        return None

    doc = str(doc).strip()

    c = Contribuyente.query.filter_by(documento=doc).first()
    if c:
        changed = False
        if apellido is not None and apellido != "" and apellido != c.apellido:
            c.apellido = apellido
            changed = True
        if nombre is not None and nombre != "" and nombre != c.nombre:
            c.nombre = nombre
            changed = True
        if changed:
            db.session.add(c)
        return c

    c = Contribuyente(
        documento=doc,
        apellido=apellido,
        nombre=nombre,
    )
    db.session.add(c)
    db.session.flush()
    return c


def get_or_create_domicilio(
    data: Optional[Dict[str, Any]],
    contribuyente: Optional[Contribuyente],
    rubro: Optional[Rubro],
) -> Optional[Domicilio]:
    """
    Domicilio se identifica por calle + numero.

    Reglas:
    - Si no hay data -> None
    - Si viene calle+numero, exige contribuyente y rubro
    - Si existe -> re-asocia contribuyente/rubro si cambian
    - Si no existe -> crea
    """
    if not data:
        return None

    calle = data.get("calle")
    numero = data.get("numero")

    if not calle or not numero:
        return None

    if contribuyente is None:
        raise ValueError("Si cargás domicilio, debés cargar contribuyente.")
    if rubro is None:
        raise ValueError("Si cargás domicilio, debés cargar rubro.")

    calle = str(calle).strip()
    numero = str(numero).strip()

    dom = Domicilio.query.filter_by(calle=calle, numero=numero).first()
    if dom:
        changed = False
        if dom.contribuyente_id != contribuyente.id:
            dom.contribuyente_id = contribuyente.id
            changed = True
        if dom.rubro_id != rubro.id:
            dom.rubro_id = rubro.id
            changed = True
        if changed:
            db.session.add(dom)
        return dom

    dom = Domicilio(
        calle=calle,
        numero=numero,
        contribuyente_id=contribuyente.id,
        rubro_id=rubro.id,
    )
    db.session.add(dom)
    db.session.flush()
    return dom


# =========================================================
# Orden de trabajo
# =========================================================

def get_or_create_orden_trabajo(numero_ot: Any, fecha_str: Any) -> OrdenTrabajo:
    """
    OT:
    - Se identifica por numero_acta + anio
    - mes/anio salen de fecha
    """
    mes, anio, _ = parse_fecha_grid(fecha_str)
    numero = acta_6(numero_ot)
    if not numero:
        raise ValueError("Orden de trabajo es obligatoria.")

    ot = OrdenTrabajo.query.filter_by(numero_acta=numero, anio=anio).first()
    if ot:
        return ot

    ot = OrdenTrabajo(numero_acta=numero, anio=anio, mes=mes)
    db.session.add(ot)
    db.session.flush()
    return ot


# =========================================================
# Reglas de unicidad de actas principales
# =========================================================

def asegurar_acta_no_usada_en_otra(model_cls, numero_acta: str, anio: int, actuacion_id: int):
    """
    Regla para INSPECCION / CLAUSURA / DECOMISO:
    - En creación, si esa acta ya pertenece a otra actuación -> rechazo duro.
    """
    existente = model_cls.query.filter_by(numero_acta=numero_acta, anio=anio).first()
    if existente and getattr(existente, "actuacion_id", None) != actuacion_id:
        raise ValueError("Acta ya asociada a otra actuación.")


def asegurar_acta_libre_para_actuacion(model_cls, numero_acta: str, anio: int, actuacion_id: int):
    """
    En update:
    - Si existe la acta pero está asociada a OTRA actuación -> error
    """
    existente = model_cls.query.filter_by(numero_acta=numero_acta, anio=anio).first()
    if existente and getattr(existente, "actuacion_id", None) not in (None, actuacion_id):
        raise ValueError("Acta ya asociada a otra actuación.")


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
