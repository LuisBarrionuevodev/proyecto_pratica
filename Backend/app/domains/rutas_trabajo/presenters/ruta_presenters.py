from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    cargar_domicilio_efectivo_orm,
)
from app.domains.rutas_trabajo.utils.planificacion_prioridad import (
    elegible_urgente_planificacion,
    prioridad_categoria_from_value,
)
from app.models import Domicilio, IniciadorRuta, RutaGrupo, RutaGrupoInspector, RutaItem, RutaTrabajo

_TIPO_INICIADOR_LABELS: dict[str, str] = {
    "RELEVAMIENTO": "Relevamiento",
    "DENUNCIA": "Denuncia",
    "REINSPECCION_NOTIFICACION": "Reinspección por notificación",
    "REINSPECCION_OFICIO": "Reinspección por oficio",
    "VERIFICAR_INFORMAR_OFICIO": "Verificar e informar",
    "RATIFICACION_CLAUSURA_OFICIO": "Ratificación de clausura",
    "RATIFICACION_DECOMISO_OFICIO": "Ratificación de decomiso",
}

_OFICIO_TIPOS_INICIADOR = frozenset(
    {
        "REINSPECCION_OFICIO",
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    }
)

_REF_PREFIX_ESQ = re.compile(r"^ref\.?\s+", re.IGNORECASE)


def _s(value: str | None) -> str:
    return (value or "").strip()


def _same_text(a: str, b: str) -> bool:
    return bool(a) and bool(b) and a.casefold() == b.casefold()


def _esquina_display_interseccion(esquina_norm: str, esquina_raw: str, numero: str) -> str:
    """
    Texto de cruce para intersección formal: prioriza normalizado, evita duplicar ``numero`` si es igual,
    y quita prefijo ``ref.`` / ``ref `` solo en modo esquina (etiqueta UI, no altera persistencia).
    """
    for cand in (_s(esquina_norm), _s(esquina_raw), _s(numero)):
        if not cand:
            continue
        cleaned = _REF_PREFIX_ESQ.sub("", cand).strip() or cand
        return cleaned
    return ""


def _build_domicilio_texto_desde_dom(dom: Domicilio | None) -> str | None:
    """
    Construye un domicilio listo para UI priorizando datos normalizados.

    - ``numero_tipo == ESQUINA``: ``<calle> Y <cruce>`` (sin duplicar número y esquina ni ``(ref: …)``).
    - En caso contrario: ``<calle> <número>`` y, si hay texto en esquina distinto al número, `` ref. …``.
    """
    if not dom:
        return None

    calle = None
    if dom.calle_catalogo and dom.calle_catalogo.nombre_canonico:
        calle = dom.calle_catalogo.nombre_canonico
    elif dom.calle_normalizada:
        calle = dom.calle_normalizada
    elif dom.calle:
        calle = dom.calle
    elif dom.calle_raw:
        calle = dom.calle_raw

    calle_s = _s(calle)
    numero = _s(dom.numero)
    ref_esq = _s(dom.esquina_normalizada) or _s(dom.esquina_raw)
    nt = _s(dom.numero_tipo).upper()

    if nt == "ESQUINA":
        esq = _esquina_display_interseccion(
            dom.esquina_normalizada or "",
            dom.esquina_raw or "",
            numero,
        )
        if calle_s and esq:
            return f"{calle_s} Y {esq}"
        if calle_s:
            return calle_s
        if esq:
            return esq
        return None

    if calle_s and numero:
        if ref_esq and not _same_text(numero, ref_esq):
            return f"{calle_s} {numero} ref. {ref_esq}"
        return f"{calle_s} {numero}"
    if calle_s and ref_esq and not numero:
        return f"{calle_s} ref. {ref_esq}"
    if calle_s:
        return calle_s
    if numero:
        return numero
    if ref_esq:
        return f"Ref. {ref_esq}"
    return None


def _build_domicilio_texto(iniciador: IniciadorRuta) -> str | None:
    """Texto de domicilio usando fuente efectiva (PR5)."""
    dom, _ef = cargar_domicilio_efectivo_orm(
        iniciador,
        apply_backfill=True,
        try_sync=False,
    )
    return _build_domicilio_texto_desde_dom(dom)


def _numeric_to_float(value: Decimal | float | int | None) -> float | None:
    """Convierte un valor numérico de DB a float para JSON; None si falta."""
    if value is None:
        return None
    return float(value)


def domicilio_geocode_campos(dom: Domicilio | None) -> dict[str, float | str | None]:
    """
    Extrae lat/lng/geo_status desde domicilio → geocode.

    Misma regla operativa que M4 e ítems de ruta: ambos coords deben existir en geocode.
    """
    lat: float | None = None
    lng: float | None = None
    geo_status: str | None = None
    if dom:
        gc = dom.geocode
        if gc:
            geo_status = str(gc.geo_status) if gc.geo_status is not None else None
            la = _numeric_to_float(gc.lat)
            ln = _numeric_to_float(gc.lng)
            if la is not None and ln is not None:
                lat = la
                lng = ln
    return {"lat": lat, "lng": lng, "geo_status": geo_status}


def _rubro_nombre_para_iniciador(
    iniciador: IniciadorRuta | None,
    dom: Domicilio | None,
) -> str | None:
    """
    Resuelve el rubro mostrado en Ruta de Trabajo (planificación / documentos).

    Para ``tipo_iniciador == RELEVAMIENTO`` la fuente canónica es ``relevamiento.rubro``.
    Denuncias y otros tipos usan ``domicilio.rubro`` (pool de iniciadores pendientes).
    """
    if iniciador and iniciador.tipo_iniciador == "RELEVAMIENTO":
        rel = iniciador.relevamiento
        if rel and rel.rubro:
            nombre = _s(rel.rubro.nombre)
            if nombre:
                return nombre

    rubro_nombre = dom.rubro.nombre if dom and dom.rubro else None
    if not rubro_nombre and iniciador and iniciador.relevamiento and iniciador.relevamiento.rubro:
        rubro_nombre = iniciador.relevamiento.rubro.nombre
    return rubro_nombre or None


def _establecimiento_campos_relevamiento(iniciador: IniciadorRuta | None) -> dict[str, str | None]:
    """
    Discriminadores operativos del relevamiento origen (no persistidos en iniciador).

    Retorna ``nombre_fantasia`` y ``angulo_esquina`` como null si faltan o están vacíos.
    """
    out: dict[str, str | None] = {"nombre_fantasia": None, "angulo_esquina": None}
    if not iniciador or iniciador.tipo_iniciador != "RELEVAMIENTO":
        return out
    rel = iniciador.relevamiento
    if not rel:
        return out
    nf = _s(rel.nombre_fantasia) or None
    ae = _s(rel.angulo_esquina) or None
    out["nombre_fantasia"] = nf
    out["angulo_esquina"] = ae
    return out


def _ruta_item_ubicacion_y_geo(item: RutaItem) -> dict:
    """
    Extrae domicilio, texto UI, distrito, rubro y coordenadas desde iniciador → domicilio → geocode.

    lat/lng solo se exponen cuando existen ambos en `domicilio_geocode` (fuente operativa de coords).
    """
    ini = item.iniciador_ruta
    dom = None
    domicilio_texto = None
    if ini:
        dom, _ef = cargar_domicilio_efectivo_orm(ini, apply_backfill=True, try_sync=False)
        domicilio_texto = _build_domicilio_texto_desde_dom(dom)

    lat: float | None = None
    lng: float | None = None
    geo_status: str | None = None
    domicilio_id: int | None = None
    distrito_id: int | None = None
    distrito_nombre: str | None = None
    rubro_nombre: str | None = None

    if dom:
        domicilio_id = dom.id
        distrito_id = dom.distrito_id
        distrito_nombre = dom.distrito.nombre if dom.distrito else None
        rubro_nombre = _rubro_nombre_para_iniciador(ini, dom)

        geo = domicilio_geocode_campos(dom)
        lat = geo["lat"]
        lng = geo["lng"]
        geo_status = geo["geo_status"]

    establecimiento = _establecimiento_campos_relevamiento(ini)
    return {
        "domicilio_id": domicilio_id,
        "domicilio_texto": domicilio_texto,
        "lat": lat,
        "lng": lng,
        "geo_status": geo_status,
        "distrito_id": distrito_id,
        "distrito_nombre": distrito_nombre,
        "rubro_nombre": rubro_nombre,
        "nombre_fantasia": establecimiento["nombre_fantasia"],
        "angulo_esquina": establecimiento["angulo_esquina"],
    }


def ruta_trabajo_to_dict(ruta: RutaTrabajo) -> dict:
    """
    Serializa la ruta de trabajo para responses del módulo.
    """
    return ruta.to_dict()


def grupo_inspector_to_dict(rel: RutaGrupoInspector) -> dict:
    """
    Serializa la relación grupo-inspector para detalle mínimo.
    """
    inspector = rel.inspector
    return {
        "id": rel.id,
        "inspector_id": rel.inspector_id,
        "inspector_nombre": inspector.nombre if inspector else None,
        "inspector_legajo": inspector.legajo if inspector else None,
    }


def ruta_grupo_to_min_dict(grupo: RutaGrupo) -> dict:
    """
    Serializa un grupo no eliminado con su listado de inspectores e items activos.
    """
    inspectores = [
        grupo_inspector_to_dict(rel)
        for rel in grupo.grupo_inspectores
    ]
    # Orden estable por id: el modelo no tiene secuencia de visita; id refleja creación asignación.
    activos = [item for item in grupo.items if item.deleted_at is None]
    activos.sort(key=lambda it: it.id)
    items_activos = [ruta_item_to_min_dict(item) for item in activos]
    return {
        "id": grupo.id,
        "ruta_trabajo_id": grupo.ruta_trabajo_id,
        "nombre": grupo.nombre,
        "estado": grupo.estado,
        "inspectores": inspectores,
        "items": items_activos,
        "created_by_user_id": grupo.created_by_user_id,
        "created_at": grupo.created_at.isoformat() if grupo.created_at else None,
        "updated_at": grupo.updated_at.isoformat() if grupo.updated_at else None,
    }


def _humanizar_codigo_tipo(codigo: str | None) -> str:
    """Etiqueta legible para códigos de tipo no catalogados."""
    key = _s(codigo)
    if not key:
        return "—"
    return " ".join(part.capitalize() for part in key.split("_") if part)


def _tipo_iniciador_label(tipo: str | None) -> str:
    """Etiqueta operativa del tipo de iniciador."""
    key = _s(tipo)
    if not key:
        return "—"
    return _TIPO_INICIADOR_LABELS.get(key, _humanizar_codigo_tipo(key))


def _format_acta_numero(numero: str | None, anio: int | None) -> str | None:
    """Formato `número/año` para actas y documentos."""
    num = _s(numero)
    if not num:
        return None
    if anio is not None:
        return f"{num}/{anio}"
    return num


def _expedientes_activos(exps: object) -> list:
    """Filtra expedientes no eliminados desde relación ORM (lista o único)."""
    if exps is None:
        return []
    rows = exps if isinstance(exps, list) else [exps]
    return [row for row in rows if row is not None and getattr(row, "deleted_at", None) is None]


def _mejor_expediente_por_fecha(exps: list) -> object | None:
    """Selecciona el expediente más reciente por fecha/id."""
    if not exps:
        return None
    return max(
        exps,
        key=lambda row: (
            getattr(row, "fecha_expediente", None) or date.min,
            getattr(row, "id", 0) or 0,
        ),
    )


def _expediente_label(exp) -> str | None:
    """Texto `número/año` de un expediente."""
    if exp is None:
        return None
    num = _s(getattr(exp, "numero_expediente", None))
    if not num:
        return None
    anio = getattr(exp, "anio", None)
    if anio is not None and _s(str(anio)):
        return f"{num}/{anio}"
    return num


def _append_detalle_item(items: list[dict[str, str]], label: str, value: str | None) -> None:
    """Agrega par label/value si el valor no está vacío."""
    val = _s(value)
    if val:
        items.append({"label": label, "value": val})


def _build_prorroga_notificacion_texto(noti) -> str | None:
    """
    Resume prórroga de notificación: días otorgados y expediente asociado si existe.
    """
    if noti is None:
        return None
    partes: list[str] = []
    dias = int(getattr(noti, "prorroga_dias", 0) or 0)
    if dias > 0:
        partes.append(f"{dias} días")
    exps = [
        row
        for row in _expedientes_activos(getattr(noti, "expedientes", None))
        if getattr(row, "tipo_expediente", None) == "PRORROGA_NOTIFICACION"
    ]
    exp = _mejor_expediente_por_fecha(exps)
    if exp is not None:
        exp_txt = _expediente_label(exp)
        if exp_txt:
            fecha = getattr(exp, "fecha_expediente", None)
            if fecha is not None:
                partes.append(f"Exp. {exp_txt} ({fecha.isoformat()})")
            else:
                partes.append(f"Exp. {exp_txt}")
    return " · ".join(partes) if partes else None


def _build_detalle_operativo_items(iniciador: IniciadorRuta) -> list[dict[str, str]]:
    """
    Ítems estructurados de detalle operativo según tipo de iniciador (asignación / export).
    """
    items: list[dict[str, str]] = []
    tipo = _s(iniciador.tipo_iniciador)

    if tipo == "REINSPECCION_NOTIFICACION":
        noti = iniciador.notificacion
        if noti is not None:
            noti_txt = _format_acta_numero(noti.numero_acta, noti.anio)
            _append_detalle_item(items, "Notif.", noti_txt)
            prorroga_txt = _build_prorroga_notificacion_texto(noti)
            if prorroga_txt:
                _append_detalle_item(items, "Prórroga", prorroga_txt)
            if noti.fecha_vencimiento is not None:
                _append_detalle_item(items, "Vence", noti.fecha_vencimiento.isoformat())

    elif tipo in _OFICIO_TIPOS_INICIADOR:
        ofi = iniciador.oficio
        comp = iniciador.comprobacion
        if comp is None and ofi is not None:
            comp = ofi.comprobacion
        if comp is not None:
            comp_txt = _format_acta_numero(comp.numero_acta, comp.anio)
            _append_detalle_item(items, "Acta comp.", comp_txt)
        if ofi is not None:
            exp = _mejor_expediente_por_fecha(_expedientes_activos(ofi.expediente))
            exp_txt = _expediente_label(exp)
            if exp_txt:
                _append_detalle_item(items, "Exp.", exp_txt)
            ofi_txt = _format_acta_numero(ofi.numero_oficio, ofi.anio)
            _append_detalle_item(items, "Oficio", ofi_txt)
            _append_detalle_item(items, "Causa", ofi.causa)
            juzgado = getattr(ofi, "juzgado", None)
            if juzgado is not None:
                _append_detalle_item(items, "Juzgado", getattr(juzgado, "nombre", None))

    elif tipo == "DENUNCIA":
        den = iniciador.denuncia
        if den is not None:
            _append_detalle_item(items, "Motivo", den.motivo)

    elif tipo == "RELEVAMIENTO":
        rel = iniciador.relevamiento
        if rel is not None:
            rubro = None
            if rel.rubro and rel.rubro.nombre:
                rubro = rel.rubro.nombre
            _append_detalle_item(items, "Rubro", rubro)
            _append_detalle_item(items, "Nombre fantasía", rel.nombre_fantasia)
            _append_detalle_item(items, "Esquina", rel.angulo_esquina)

    return items


def _detalle_operativo_texto_desde_items(items: list[dict[str, str]]) -> str | None:
    """Serializa ítems de detalle a una línea compacta."""
    if not items:
        return None
    return " · ".join(f"{row['label']}: {row['value']}" for row in items)


def iniciador_operativo_campos(iniciador: IniciadorRuta | None) -> dict:
    """
    Campos operativos compartidos para pool, pendientes y ítems de ruta.

    Parámetros:
        iniciador: instancia ORM con relaciones de documento cargadas si aplica.

    Retorno:
        dict con tipo, prioridad, identificadores y detalle operativo.
    """
    if iniciador is None:
        return {
            "tipo_iniciador": None,
            "tipo_iniciador_label": None,
            "prioridad": None,
            "prioridad_categoria": None,
            "prioridad_label": None,
            "detalle_operativo_items": [],
            "detalle_operativo_texto": None,
            "identificadores": _build_identificadores_iniciador_empty(),
            "nombre_fantasia": None,
            "angulo_esquina": None,
            "motivo_denuncia": None,
            "causa": None,
            "prorroga_texto": None,
        }

    identificadores = _build_identificadores_iniciador(iniciador)
    detalle_items = _build_detalle_operativo_items(iniciador)
    establecimiento = _establecimiento_campos_relevamiento(iniciador)
    prioridad_raw = iniciador.prioridad
    prioridad = prioridad_raw if isinstance(prioridad_raw, int) else None
    prioridad_cat = prioridad_categoria_from_value(prioridad)
    tipo_label = _tipo_iniciador_label(iniciador.tipo_iniciador)

    return {
        "tipo_iniciador": iniciador.tipo_iniciador,
        "tipo_iniciador_label": tipo_label,
        "prioridad": prioridad,
        "prioridad_categoria": prioridad_cat,
        "prioridad_label": f"P{prioridad}" if prioridad is not None else None,
        "detalle_operativo_items": detalle_items,
        "detalle_operativo_texto": _detalle_operativo_texto_desde_items(detalle_items),
        "identificadores": identificadores,
        "nombre_fantasia": establecimiento["nombre_fantasia"],
        "angulo_esquina": establecimiento["angulo_esquina"],
        "motivo_denuncia": identificadores.get("motivo_denuncia"),
        "causa": identificadores.get("causa"),
        "prorroga_texto": identificadores.get("prorroga_texto"),
        "badges": {
            "tipo_label": tipo_label,
            "estado_label": (iniciador.estado_iniciador or "").replace("_", " "),
            "origen_label": identificadores.get("origen_label") or "SIN_ORIGEN",
            "prioridad_label": f"P{prioridad}" if prioridad is not None else "S/P",
        },
    }


def _build_identificadores_iniciador_empty() -> dict:
    """Plantilla vacía de identificadores documentales."""
    return {
        "numero_oficio": None,
        "anio_oficio": None,
        "numero_comprobacion": None,
        "anio_comprobacion": None,
        "numero_notificacion": None,
        "anio_notificacion": None,
        "fecha_vencimiento_notificacion": None,
        "numero_denuncia": None,
        "numero_expediente": None,
        "anio_expediente": None,
        "prorroga_dias": None,
        "prorroga_texto": None,
        "causa": None,
        "juzgado_nombre": None,
        "motivo_denuncia": None,
        "origen_label": None,
    }


def _build_identificadores_iniciador(iniciador: IniciadorRuta) -> dict:
    """
    Números operativos para cards de planificación (STAB-10c).

    Usa relaciones ya cargadas en ``planificable_iniciadores_base_query`` (oficio, notificación, comprobación).
    """
    out: dict = _build_identificadores_iniciador_empty()

    origen = None
    if iniciador.denuncia_id:
        origen = "DENUNCIA"
    elif iniciador.relevamiento_id:
        origen = "RELEVAMIENTO"
    elif iniciador.notificacion_id:
        origen = "NOTIFICACION"
    elif iniciador.oficio_id:
        origen = "OFICIO"
    out["origen_label"] = origen or "SIN_ORIGEN"

    ofi = iniciador.oficio
    if ofi is not None:
        nof = _s(ofi.numero_oficio)
        if nof:
            out["numero_oficio"] = nof
        out["anio_oficio"] = ofi.anio
        causa = _s(ofi.causa)
        if causa:
            out["causa"] = causa
        juzgado = getattr(ofi, "juzgado", None)
        if juzgado is not None:
            jnom = _s(getattr(juzgado, "nombre", None))
            if jnom:
                out["juzgado_nombre"] = jnom
        exp_ofi = _mejor_expediente_por_fecha(_expedientes_activos(ofi.expediente))
        if exp_ofi is not None:
            out["numero_expediente"] = _s(getattr(exp_ofi, "numero_expediente", None)) or None
            out["anio_expediente"] = _s(getattr(exp_ofi, "anio", None)) or None
        comp_ofi = ofi.comprobacion
        if comp_ofi is not None:
            ncomp = _s(comp_ofi.numero_acta)
            if ncomp:
                out["numero_comprobacion"] = ncomp
            out["anio_comprobacion"] = comp_ofi.anio

    comp = iniciador.comprobacion
    if comp is not None:
        if not out["numero_comprobacion"]:
            ncomp = _s(comp.numero_acta)
            if ncomp:
                out["numero_comprobacion"] = ncomp
            out["anio_comprobacion"] = comp.anio
        if not out["numero_oficio"]:
            oficios_rel = getattr(comp, "oficio", None)
            if oficios_rel is not None:
                first_ofi = oficios_rel[0] if isinstance(oficios_rel, list) else oficios_rel
                if first_ofi is not None:
                    nof = _s(getattr(first_ofi, "numero_oficio", None))
                    if nof:
                        out["numero_oficio"] = nof
                    out["anio_oficio"] = getattr(first_ofi, "anio", None)

    noti = iniciador.notificacion
    if noti is not None:
        nnot = _s(noti.numero_acta)
        if nnot:
            out["numero_notificacion"] = nnot
        out["anio_notificacion"] = noti.anio
        if noti.fecha_vencimiento is not None:
            out["fecha_vencimiento_notificacion"] = noti.fecha_vencimiento.isoformat()
        dias_prorroga = int(noti.prorroga_dias or 0)
        if dias_prorroga > 0:
            out["prorroga_dias"] = dias_prorroga
        prorroga_txt = _build_prorroga_notificacion_texto(noti)
        if prorroga_txt:
            out["prorroga_texto"] = prorroga_txt

    den = iniciador.denuncia
    if den is not None:
        motivo = _s(den.motivo)
        if motivo:
            out["motivo_denuncia"] = motivo

    return out


def iniciador_pendiente_to_row(iniciador: IniciadorRuta) -> dict:
    """
    Serializa un iniciador pendiente para tabla operativa de planificación.
    """
    dom, _efectivo = cargar_domicilio_efectivo_orm(
        iniciador,
        apply_backfill=True,
        try_sync=True,
    )
    origen = None
    if iniciador.denuncia_id:
        origen = "DENUNCIA"
    elif iniciador.relevamiento_id:
        origen = "RELEVAMIENTO"
    elif iniciador.notificacion_id:
        origen = "NOTIFICACION"
    elif iniciador.oficio_id:
        origen = "OFICIO"

    domicilio_texto = _build_domicilio_texto_desde_dom(dom)
    rubro_nombre = _rubro_nombre_para_iniciador(iniciador, dom)
    establecimiento = _establecimiento_campos_relevamiento(iniciador)
    distrito_id = dom.distrito_id if dom else None
    distrito_nombre = dom.distrito.nombre if dom and dom.distrito else None

    geo = domicilio_geocode_campos(dom)
    lat = geo["lat"]
    lng = geo["lng"]
    geo_status = geo["geo_status"]

    operativo = iniciador_operativo_campos(iniciador)

    return {
        "id": iniciador.id,
        "tipo_iniciador": iniciador.tipo_iniciador,
        "tipo_iniciador_label": operativo["tipo_iniciador_label"],
        "estado_iniciador": iniciador.estado_iniciador,
        "fecha_origen": iniciador.fecha_origen.isoformat() if iniciador.fecha_origen else None,
        "prioridad": iniciador.prioridad,
        "turno_sugerido": iniciador.turno_sugerido,
        "domicilio": {
            "id": dom.id if dom else None,
            "calle": (
                dom.calle_catalogo.nombre_canonico
                if dom and dom.calle_catalogo and dom.calle_catalogo.nombre_canonico
                else dom.calle_normalizada
                if dom and dom.calle_normalizada
                else dom.calle
                if dom
                else None
            ),
            "numero": dom.numero if dom else None,
            "distrito_id": distrito_id,
            "distrito_nombre": distrito_nombre,
            "barrio_id": dom.barrio_id if dom else None,
            "rubro": rubro_nombre,
        },
        "domicilio_texto": domicilio_texto,
        "distrito_id": distrito_id,
        "distrito_nombre": distrito_nombre,
        "rubro_nombre": rubro_nombre,
        "nombre_fantasia": establecimiento["nombre_fantasia"],
        "angulo_esquina": establecimiento["angulo_esquina"],
        "origen": {
            "tipo": origen,
            "denuncia_id": iniciador.denuncia_id,
            "relevamiento_id": iniciador.relevamiento_id,
            "notificacion_id": iniciador.notificacion_id,
            "oficio_id": iniciador.oficio_id,
            "actuacion_id": iniciador.actuacion_id,
        },
        "observaciones": iniciador.observaciones,
        "lat": lat,
        "lng": lng,
        "geo_status": geo_status,
        "prioridad_categoria": operativo["prioridad_categoria"],
        "prioridad_label": operativo["prioridad_label"],
        "elegible_urgente": elegible_urgente_planificacion(
            iniciador.tipo_iniciador, iniciador.prioridad
        ),
        "badges": operativo["badges"],
        "identificadores": operativo["identificadores"],
        "detalle_operativo_items": operativo["detalle_operativo_items"],
        "detalle_operativo_texto": operativo["detalle_operativo_texto"],
        "motivo_denuncia": operativo["motivo_denuncia"],
        "causa": operativo["causa"],
        "prorroga_texto": operativo["prorroga_texto"],
    }


_MAP_PIN_KEYS: tuple[str, ...] = (
    "id",
    "tipo_iniciador",
    "estado_iniciador",
    "fecha_origen",
    "prioridad",
    "prioridad_categoria",
    "domicilio_texto",
    "distrito_id",
    "distrito_nombre",
    "rubro_nombre",
    "nombre_fantasia",
    "angulo_esquina",
    "domicilio",
    "origen",
    "lat",
    "lng",
    "geo_status",
    "badges",
    "identificadores",
)


def iniciador_pendiente_to_map_pin(iniciador: IniciadorRuta) -> dict:
    """
    Payload mínimo para pins del mapa de planificación (STAB-10b).

    Reutiliza la resolución de domicilio/geocode de `iniciador_pendiente_to_row`
    y recorta campos no usados en mapa/popup/pool.
    """
    full = iniciador_pendiente_to_row(iniciador)
    return {k: full[k] for k in _MAP_PIN_KEYS if k in full}


def iniciador_pendiente_present(iniciador: IniciadorRuta, *, fields: str = "full") -> dict:
    """
    Presenta un iniciador pendiente según el modo solicitado.

    Parámetros:
        fields: ``full`` (lista/tabla) o ``minimal`` (mapa).
    """
    if (fields or "full").strip().lower() == "minimal":
        return iniciador_pendiente_to_map_pin(iniciador)
    return iniciador_pendiente_to_row(iniciador)


def ruta_item_to_min_dict(item: RutaItem) -> dict:
    """
    Serializa un item de ruta para operaciones de asignación/movimiento y detalle/mapa.

    Incluye ubicación y geocodificación cuando el iniciador tiene domicilio (vía iniciador_ruta → domicilio → geocode).
    Incluye tipo_iniciador desde IniciadorRuta para UI (mapa / panel) sin depender del pool de planificación.
    """
    orden_trabajo = item.orden_trabajo
    ini = item.iniciador_ruta
    base = {
        "id": item.id,
        "ruta_trabajo_id": item.ruta_trabajo_id,
        "ruta_grupo_id": item.ruta_grupo_id,
        "iniciador_ruta_id": item.iniciador_ruta_id,
        "tipo_iniciador": ini.tipo_iniciador if ini else None,
        "orden_trabajo_id": item.orden_trabajo_id,
        "actuacion_id": item.actuacion_id,
        "orden_trabajo": {
            "id": orden_trabajo.id,
            "numero_acta": orden_trabajo.numero_acta,
            "anio": orden_trabajo.anio,
            "mes": orden_trabajo.mes,
        }
        if orden_trabajo
        else None,
        "estado_ruta_item": item.estado_ruta_item,
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }
    base.update(_ruta_item_ubicacion_y_geo(item))
    base.update(iniciador_operativo_campos(ini))
    return base
