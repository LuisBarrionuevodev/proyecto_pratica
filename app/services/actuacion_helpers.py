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

    Reglas:
    - Si no viene nombre -> None
    - Normalizamos espacios
    - Si existe -> devolvemos
    - Si no existe -> creamos
    """
    if nombre is None:
        return None

    s = str(nombre).strip()
    if not s:
        return None

    # normalización mínima
    s = " ".join(s.split())

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

    Reglas nuevas:
    - Si no hay data -> None
    - Si no hay doc -> None
    - Si existe -> SI actualizamos apellido/nombre si el payload los trae
    - Si no existe -> creamos
    """
    if not data:
        return None

    doc = data.get("doc_nro")
    if not doc:
        return None

    apellido = data.get("apellido")
    nombre = data.get("nombre")

    c = Contribuyente.query.filter_by(documento=doc).first()
    if c:
        # ✅ Update suave: solo si llega algo válido
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

    # ✅ Si no existe, creamos
    c = Contribuyente(
        documento=doc,
        apellido=apellido,
        nombre=nombre,
    )
    db.session.add(c)
    return c


def get_or_create_domicilio(
    data: Optional[Dict[str, Any]],
    contribuyente: Optional[Contribuyente],
    rubro: Optional[Rubro],
) -> Optional[Domicilio]:
    """
    Domicilio se identifica por calle + numero.

    Reglas nuevas:
    - Si no hay data -> None
    - Si falta contribuyente o rubro -> error claro
    - Si existe por calle+numero -> ACTUALIZAMOS contribuyente_id y rubro_id si cambian
    - Si no existe -> creamos con contribuyente + rubro
    """
    if not data:
        return None

    if not contribuyente or not rubro:
        raise ValueError("Domicilio requiere contribuyente y rubro.")

    calle = data.get("calle")
    numero = data.get("numero")

    if not calle or not numero:
        return None  # coherencia con tu esquema: domicilio se arma solo si vienen ambos

    dom = Domicilio.query.filter_by(calle=calle, numero=numero).first()
    if dom:
        changed = False

        # ✅ re-asociar contribuyente si cambió
        if dom.contribuyente_id != contribuyente.id:
            dom.contribuyente_id = contribuyente.id
            changed = True

        # ✅ re-asociar rubro si cambió
        if dom.rubro_id != rubro.id:
            dom.rubro_id = rubro.id
            changed = True

        if changed:
            db.session.add(dom)

        return dom

    # ✅ Si no existe, creamos
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

def asegurar_acta_libre_para_actuacion(model_cls, numero_acta: str, anio: int, actuacion_id: int):
    """
    Para UPDATE:
    - Permite usar el número si:
        a) no existe
        b) existe pero ya pertenece a esta misma actuación
    - Rechaza si pertenece a otra.
    """
    existente = model_cls.query.filter_by(numero_acta=numero_acta, anio=anio).first()
    if existente and existente.actuacion_id != actuacion_id:
        raise ValueError(f"El acta {numero_acta}/{anio} ya está cargada en otra actuación.")


def attach_inspeccion(actuacion: Actuaciones, acta_num: Optional[str], fecha_str: str, crear: bool):
    if not acta_num:
        return

    numero = acta_6(acta_num)
    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Inspeccion, numero, anio, actuacion.id)
    else:
        asegurar_acta_libre_para_actuacion(Inspeccion, numero, anio, actuacion.id)

    # ✅ BUSCAMOS LA INSPECCIÓN YA ASOCIADA A ESTA ACTUACIÓN
    actual = Inspeccion.query.filter_by(actuacion_id=actuacion.id).first()

    if actual:
        # ✅ UPDATE IN-PLACE
        actual.numero_acta = numero
        actual.anio = anio
        actual.mes = mes
        db.session.add(actual)
        return

    # Si no existía una inspección para esta actuación,
    # caemos al comportamiento clásico
    ins = Inspeccion.query.filter_by(numero_acta=numero, anio=anio).first()
    if ins:
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
    if not data:
        return

    acta_num = acta_6(data.get("acta_num"))
    if not acta_num:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    motivos = data.get("motivos") or []

    # ✅ si la actuación ya tiene notificación, actualizamos ESA
    if actuacion.notificacion_id:
        noti = Notificacion.query.get(actuacion.notificacion_id)
        if noti:
            # check unicidad global
            existente = Notificacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
            if existente and existente.id != noti.id:
                raise ValueError("Acta de notificación ya asociada a otra actuación.")

            noti.numero_acta = acta_num
            noti.anio = anio
            noti.mes = mes

            if motivos:
                noti.motivos = [get_or_create_motivo(m) for m in motivos]

            db.session.add(noti)
            return

    # ✅ si no había una notificación asociada, usamos comportamiento clásico
    noti = Notificacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
    if not noti:
        noti = Notificacion(numero_acta=acta_num, anio=anio, mes=mes)
        db.session.add(noti)
        db.session.flush()

    actuacion.notificacion_id = noti.id

    if motivos:
        noti.motivos = [get_or_create_motivo(m) for m in motivos]


def attach_comprobacion(actuacion: Actuaciones, data: Optional[Dict[str, Any]]):
    if not data:
        return

    acta_num = acta_6(data.get("acta_num"))
    motivo = data.get("motivo")

    if not acta_num:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    # ✅ si la actuación ya tiene comprobación, actualizamos ESA
    if actuacion.comprobacion_id:
        comp = Comprobacion.query.get(actuacion.comprobacion_id)
        if comp:
            existente = Comprobacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
            if existente and existente.id != comp.id:
                raise ValueError("Acta de comprobación ya asociada a otra actuación.")

            comp.numero_acta = acta_num
            comp.anio = anio
            comp.mes = mes
            if motivo:
                comp.motivo = motivo

            db.session.add(comp)
            return

    # ✅ si no había una comprobación asociada, usamos comportamiento clásico
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
    if not data or not data.get("acta_num"):
        return

    numero = acta_6(data["acta_num"])
    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Clausura, numero, anio, actuacion.id)
    else:
        asegurar_acta_libre_para_actuacion(Clausura, numero, anio, actuacion.id)

    # ✅ clausura actual de la actuación
    actual = Clausura.query.filter_by(actuacion_id=actuacion.id).first()
    if actual:
        actual.numero_acta = numero
        actual.anio = anio
        actual.mes = mes
        db.session.add(actual)
        return

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
    else:
        asegurar_acta_libre_para_actuacion(Decomiso, numero, anio, actuacion.id)

    # ✅ decomiso actual de la actuación
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
        if dec.actuacion_id != actuacion.id:
            raise ValueError("Acta de decomiso ya asociada a otra actuación.")
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
