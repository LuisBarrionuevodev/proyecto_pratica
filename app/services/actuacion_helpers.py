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




def parse_fecha_grid(fecha_str: str):
    s = (fecha_str or "").strip()
    if not s:
        raise ValueError("La fecha es obligatoria")

    try:
        if "-" in s:
            fecha_date = datetime.strptime(s, "%Y-%m-%d").date()
        else:
            fecha_date = datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError("Formato inválido. Usá DD/MM/AAAA o YYYY-MM-DD")

    return fecha_date.month, fecha_date.year, fecha_date



# =========================================================
# Catálogos base
# =========================================================

def get_or_create_rubro(nombre: Optional[str]) -> Optional[Rubro]:
    """
    Rubro viene como nombre.
    - Si no viene nombre -> None
    - Si existe -> lo devolvemos
    - Si no existe -> lo creamos
    """
    if not nombre:
        return None

    s = nombre.strip()
    rubro = Rubro.query.filter_by(nombre=s).first()
    if rubro:
        return rubro

    rubro = Rubro(nombre=s)
    db.session.add(rubro)
    return rubro


def get_inspectores_o_falla(nombres: List[str]) -> List[Inspector]:
    """
    En tu negocio: los inspectores SON catálogo.
    Si un nombre no existe, rechazamos duro.
    """
    encontrados: List[Inspector] = []

    for n in nombres:
        ins = Inspector.query.filter_by(nombre=n).first()
        if not ins:
            raise ValueError(f"Inspector no existe en catálogo: {n}")
        encontrados.append(ins)

    return encontrados


# =========================================================
# Contribuyente + Domicilio
# =========================================================

def resolve_contribuyente(data: Optional[Dict[str, Any]]) -> Optional[Contribuyente]:
    """
    Contribuyente se identifica por documento.
    - Si no hay data -> None
    - Si existe -> no tocamos apellido/nombre (tu regla)
    - Si no existe -> creamos uno mínimo
    """
    if not data:
        return None

    doc = data.get("doc_nro")
    if not doc:
        return None  # Pydantic ya evita casos incoherentes

    c = Contribuyente.query.filter_by(documento=doc).first()
    if c:
        return c

    c = Contribuyente(
        documento=doc,
        apellido=data.get("apellido"),
        nombre=data.get("nombre"),
    )
    db.session.add(c)
    return c


def get_or_create_domicilio(
    data: Optional[Dict[str, Any]],
    contribuyente: Optional[Contribuyente],
    rubro: Optional[Rubro],
) -> Optional[Domicilio]:
    """
    Domicilio en tu DB exige:
    calle + numero + contribuyente_id + rubro_id

    Por eso:
    - Si no hay data -> None
    - Si falta contribuyente o rubro -> error claro
    - Si existe -> devolvemos
    - Si no existe -> creamos
    """
    if not data:
        return None

    if not contribuyente or not rubro:
        raise ValueError("Domicilio requiere contribuyente y rubro.")

    calle = data.get("calle")
    numero = data.get("numero")

    dom = Domicilio.query.filter_by(calle=calle, numero=numero).first()
    if dom:
        return dom

    dom = Domicilio(
        calle=calle,
        numero=numero,
        contribuyente_id=contribuyente.id,
        rubro_id=rubro.id,
    )
    db.session.add(dom)
    return dom


# =========================================================
# Orden de Trabajo (base de la actuación)
# =========================================================

def get_or_create_orden_trabajo(numero_ot: str, fecha_str: str) -> OrdenTrabajo:
    """
    En tu modelo:
    - OrdenTrabajo es única por (numero_acta, anio)
    - No hay precargadas, así que se crean si no existen

    Usamos la fecha de la grid para setear mes/año.
    """
    mes, anio, _ = parse_fecha_grid(fecha_str)
    numero = acta_6(numero_ot)

    ot = OrdenTrabajo.query.filter_by(numero_acta=numero, anio=anio).first()
    if ot:
        return ot

    ot = OrdenTrabajo(numero_acta=numero, anio=anio, mes=mes)
    db.session.add(ot)
    return ot


# =========================================================
# Motivos (catálogo simple)
# =========================================================

def get_or_create_motivo(nombre: str) -> Motivo:
    """
    Motivo usado por notificación (M2M).
    Si no existe, lo crea.
    """
    m = Motivo.query.filter_by(nombre=nombre).first()
    if m:
        return m

    m = Motivo(nombre=nombre)
    db.session.add(m)
    return m


# =========================================================
# Reglas de unicidad de actas principales
# =========================================================

def asegurar_acta_no_usada_en_otra(model_cls, numero_acta: str, anio: int, actuacion_id: int):
    """
    Regla para INSPECCION / CLAUSURA / DECOMISO:
    - En creación, si esa acta ya pertenece a otra actuación -> rechazo duro.
    """
    existente = model_cls.query.filter_by(numero_acta=numero_acta, anio=anio).first()
    if existente and existente.actuacion_id != actuacion_id:
        raise ValueError(f"El acta {numero_acta}/{anio} ya está cargada en otra actuación.")


# =========================================================
# Attach de actas (pensados para ser fáciles de leer)
# =========================================================

def attach_inspeccion(actuacion: Actuaciones, acta_num: Optional[str], fecha_str: str, crear: bool):
    """
    Crea/relaciona acta de inspección.
    - Acta única global
    - Usa mes/año de la actuación (para no repetir lógica rara)
    """
    if not acta_num:
        return

    numero = acta_6(acta_num)
    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Inspeccion, numero, anio, actuacion.id)

    ins = Inspeccion.query.filter_by(numero_acta=numero, anio=anio).first()
    if ins:
        # Si ya era de esta actuación, perfecto.
        if ins.actuacion_id != actuacion.id:
            raise ValueError("Acta de inspección ya asociada a otra actuación.")
        return

    ins = Inspeccion(
        numero_acta=numero,
        anio=anio,
        mes=mes,
        actuacion_id=actuacion.id,
    )
    db.session.add(ins)


def attach_notificacion(actuacion: Actuaciones, data: Optional[Dict[str, Any]]):
    """
    Notificación:
    - Se crea por numero_acta + anio
    - Motivos se guardan en relación M2M
    """
    if not data:
        return

    acta_num = acta_6(data.get("acta_num"))
    if not acta_num:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    noti = Notificacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
    if not noti:
        noti = Notificacion(numero_acta=acta_num, anio=anio, mes=mes)
        db.session.add(noti)
        db.session.flush()

    # link en actuación
    actuacion.notificacion_id = noti.id

    # motivos
    motivos = data.get("motivos") or []
    if motivos:
        noti.motivos = [get_or_create_motivo(m) for m in motivos]


def attach_comprobacion(actuacion: Actuaciones, data: Optional[Dict[str, Any]]):
    """
    Comprobación:
    - Se crea por numero_acta + anio
    - Motivo es obligatorio (Pydantic ya lo garantiza)
    """
    if not data:
        return

    acta_num = acta_6(data.get("acta_num"))
    motivo = data.get("motivo")

    if not acta_num:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    comp = Comprobacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
    if not comp:
        comp = Comprobacion(
            numero_acta=acta_num,
            anio=anio,
            mes=mes,
            motivo=motivo,
        )
        db.session.add(comp)
        db.session.flush()

    actuacion.comprobacion_id = comp.id


def attach_clausura(actuacion: Actuaciones, data: Optional[Dict[str, Any]], crear: bool):
    """
    Clausura:
    - Acta única global
    """
    if not data or not data.get("acta_num"):
        return

    numero = acta_6(data["acta_num"])
    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Clausura, numero, anio, actuacion.id)

    cl = Clausura.query.filter_by(numero_acta=numero, anio=anio).first()
    if cl:
        if cl.actuacion_id != actuacion.id:
            raise ValueError("Acta de clausura ya asociada a otra actuación.")
        return

    cl = Clausura(
        numero_acta=numero,
        anio=anio,
        mes=mes,
        actuacion_id=actuacion.id,
    )
    db.session.add(cl)


def attach_decomiso(actuacion: Actuaciones, data: Optional[Dict[str, Any]], crear: bool):
    """
    Decomiso:
    - Acta única global
    - cantidad (kilos) obligatoria
    """
    if not data or not data.get("acta_num"):
        return

    numero = acta_6(data["acta_num"])
    kilos = data.get("kilos_total")

    if kilos is None:
        raise ValueError("Si cargás decomiso, kilos_total es obligatorio.")

    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Decomiso, numero, anio, actuacion.id)

    dec = Decomiso.query.filter_by(numero_acta=numero, anio=anio).first()
    if dec:
        if dec.actuacion_id != actuacion.id:
            raise ValueError("Acta de decomiso ya asociada a otra actuación.")
        # update simple
        dec.cantidad = kilos
        return

    dec = Decomiso(
        numero_acta=numero,
        anio=anio,
        mes=mes,
        cantidad=kilos,
        actuacion_id=actuacion.id,
    )
    db.session.add(dec)


# =========================================================
# Expediente / Oficio (simple)
# =========================================================

def attach_oficio(data: Optional[Dict[str, Any]]) -> Optional[Oficio]:
    """
    Oficio:
    - Se identifica por numero + anio.
    - causa la dejás nullable en DB, así que no la exigimos acá.
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
    - Se identifica por numero + anio.
    - Tu DB lo modela con anio varchar, por eso lo casteamos.
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
    return ex
