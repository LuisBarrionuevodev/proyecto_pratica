from __future__ import annotations

import re
from decimal import Decimal

from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    cargar_domicilio_efectivo_orm,
)
from app.domains.rutas_trabajo.utils.planificacion_prioridad import (
    elegible_urgente_planificacion,
    prioridad_categoria_from_value,
)
from app.models import Domicilio, IniciadorRuta, RutaGrupo, RutaGrupoInspector, RutaItem, RutaTrabajo

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


def _rubro_nombre_para_iniciador(
    iniciador: IniciadorRuta | None,
    dom: Domicilio | None,
) -> str | None:
    """
    Resuelve el rubro mostrado en Ruta de Trabajo.

    Para ``tipo_iniciador == RELEVAMIENTO`` la fuente canónica es ``relevamiento.rubro``
    (PR7.8: evita rubro desactualizado en domicilio compartido ESQUINA multi-rubro).
    Otros tipos usan ``domicilio.rubro`` con fallback legacy a relevamiento.
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

        gc = dom.geocode
        if gc:
            geo_status = str(gc.geo_status) if gc.geo_status is not None else None
            la = _numeric_to_float(gc.lat)
            ln = _numeric_to_float(gc.lng)
            if la is not None and ln is not None:
                lat = la
                lng = ln

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


def _build_identificadores_iniciador(iniciador: IniciadorRuta) -> dict:
    """
    Números operativos para cards de planificación (STAB-10c).

    Usa relaciones ya cargadas en ``planificable_iniciadores_base_query`` (oficio, notificación, comprobación).
    """
    out: dict = {
        "numero_oficio": None,
        "anio_oficio": None,
        "numero_comprobacion": None,
        "anio_comprobacion": None,
        "numero_notificacion": None,
        "anio_notificacion": None,
        "fecha_vencimiento_notificacion": None,
        "numero_denuncia": None,
    }

    ofi = iniciador.oficio
    if ofi is not None:
        nof = _s(ofi.numero_oficio)
        if nof:
            out["numero_oficio"] = nof
        out["anio_oficio"] = ofi.anio
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

    return {
        "id": iniciador.id,
        "tipo_iniciador": iniciador.tipo_iniciador,
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
        "prioridad_categoria": prioridad_categoria_from_value(iniciador.prioridad),
        "elegible_urgente": elegible_urgente_planificacion(
            iniciador.tipo_iniciador, iniciador.prioridad
        ),
        "badges": {
            "tipo_label": (iniciador.tipo_iniciador or "").replace("_", " "),
            "estado_label": (iniciador.estado_iniciador or "").replace("_", " "),
            "origen_label": origen or "SIN_ORIGEN",
            "prioridad_label": f"P{iniciador.prioridad}" if iniciador.prioridad else "S/P",
        },
        "identificadores": _build_identificadores_iniciador(iniciador),
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
    return base
