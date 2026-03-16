from __future__ import annotations

from app.models import IniciadorRuta, RutaGrupo, RutaGrupoInspector, RutaItem, RutaTrabajo


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
    items_activos = [
        ruta_item_to_min_dict(item)
        for item in grupo.items
        if item.deleted_at is None
    ]
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

    return {
        "id": iniciador.id,
        "tipo_iniciador": iniciador.tipo_iniciador,
        "estado_iniciador": iniciador.estado_iniciador,
        "fecha_origen": iniciador.fecha_origen.isoformat() if iniciador.fecha_origen else None,
        "prioridad": iniciador.prioridad,
        "turno_sugerido": iniciador.turno_sugerido,
        "domicilio": {
            "id": dom.id if dom else None,
            "calle": dom.calle if dom else None,
            "numero": dom.numero if dom else None,
            "distrito_id": dom.distrito_id if dom else None,
            "barrio_id": dom.barrio_id if dom else None,
        },
        "origen": {
            "tipo": origen,
            "denuncia_id": iniciador.denuncia_id,
            "relevamiento_id": iniciador.relevamiento_id,
            "notificacion_id": iniciador.notificacion_id,
            "oficio_id": iniciador.oficio_id,
            "actuacion_id": iniciador.actuacion_id,
        },
        "observaciones": iniciador.observaciones,
        "badges": {
            "tipo_label": (iniciador.tipo_iniciador or "").replace("_", " "),
            "estado_label": (iniciador.estado_iniciador or "").replace("_", " "),
            "origen_label": origen or "SIN_ORIGEN",
            "prioridad_label": f"P{iniciador.prioridad}" if iniciador.prioridad else "S/P",
        },
    }


def ruta_item_to_min_dict(item: RutaItem) -> dict:
    """
    Serializa un item de ruta para operaciones de asignación/movimiento.
    """
    orden_trabajo = item.orden_trabajo
    return {
        "id": item.id,
        "ruta_trabajo_id": item.ruta_trabajo_id,
        "ruta_grupo_id": item.ruta_grupo_id,
        "iniciador_ruta_id": item.iniciador_ruta_id,
        "orden_trabajo_id": item.orden_trabajo_id,
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
