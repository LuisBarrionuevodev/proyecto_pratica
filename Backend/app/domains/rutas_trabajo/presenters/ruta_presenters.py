from __future__ import annotations

from decimal import Decimal

from app.domains.rutas_trabajo.utils.planificacion_prioridad import (
    elegible_urgente_planificacion,
    prioridad_categoria_from_value,
)
from app.models import IniciadorRuta, RutaGrupo, RutaGrupoInspector, RutaItem, RutaTrabajo


def _build_domicilio_texto(iniciador: IniciadorRuta) -> str | None:
    """
    Construye un domicilio listo para UI priorizando datos normalizados.
    """
    dom = iniciador.domicilio
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

    numero = (dom.numero or "").strip()
    ref = (dom.esquina_normalizada or dom.esquina_raw or "").strip()

    if calle and numero and ref:
        return f"{calle} {numero} (ref: {ref})"
    if calle and numero:
        return f"{calle} {numero}"
    if calle:
        return calle
    if ref:
        return f"Ref: {ref}"
    return None


def _numeric_to_float(value: Decimal | float | int | None) -> float | None:
    """Convierte un valor numérico de DB a float para JSON; None si falta."""
    if value is None:
        return None
    return float(value)


def _ruta_item_ubicacion_y_geo(item: RutaItem) -> dict:
    """
    Extrae domicilio, texto UI, distrito, rubro y coordenadas desde iniciador → domicilio → geocode.

    lat/lng solo se exponen cuando existen ambos en `domicilio_geocode` (fuente operativa de coords).
    """
    ini = item.iniciador_ruta
    domicilio_texto = _build_domicilio_texto(ini) if ini else None
    dom = ini.domicilio if ini else None

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
        rubro_nombre = dom.rubro.nombre if dom.rubro else None
        if ini and not rubro_nombre and ini.relevamiento and ini.relevamiento.rubro:
            rubro_nombre = ini.relevamiento.rubro.nombre

        gc = dom.geocode
        if gc:
            geo_status = str(gc.geo_status) if gc.geo_status is not None else None
            la = _numeric_to_float(gc.lat)
            ln = _numeric_to_float(gc.lng)
            if la is not None and ln is not None:
                lat = la
                lng = ln

    return {
        "domicilio_id": domicilio_id,
        "domicilio_texto": domicilio_texto,
        "lat": lat,
        "lng": lng,
        "geo_status": geo_status,
        "distrito_id": distrito_id,
        "distrito_nombre": distrito_nombre,
        "rubro_nombre": rubro_nombre,
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


def iniciador_pendiente_to_row(iniciador: IniciadorRuta) -> dict:
    """
    Serializa un iniciador pendiente para tabla operativa de planificación.
    """
    dom = iniciador.domicilio
    origen = None
    if iniciador.denuncia_id:
        origen = "DENUNCIA"
    elif iniciador.relevamiento_id:
        origen = "RELEVAMIENTO"
    elif iniciador.notificacion_id:
        origen = "NOTIFICACION"
    elif iniciador.oficio_id:
        origen = "OFICIO"

    domicilio_texto = _build_domicilio_texto(iniciador)
    rubro_nombre = dom.rubro.nombre if dom and dom.rubro else None
    if not rubro_nombre and iniciador.relevamiento and iniciador.relevamiento.rubro:
        rubro_nombre = iniciador.relevamiento.rubro.nombre
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
    }


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
