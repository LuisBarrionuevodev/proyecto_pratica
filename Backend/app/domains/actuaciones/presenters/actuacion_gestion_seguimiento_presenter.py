from __future__ import annotations

from typing import Any

from app.domains.actuaciones.presenters.actuacion_presenters import (
    ActuacionGridBatchMaps,
    _seguimiento_acta_grid_fields,
)
from app.domains.actuaciones.services.acta_seguimiento_gestion_service import (
    notificacion_origen_numero_desde_iniciador,
)
from app.domains.actuaciones.utils.acta_seguimiento_policy import (
    contexto_solicitud_carnet_gestion,
    contexto_subsanacion_gestion,
)
from app.models import Actuaciones, IniciadorRuta


def build_actuacion_gestion_ui_policy(
    act: Actuaciones,
    ini: IniciadorRuta | None,
    *,
    actuacion_editable: bool,
) -> dict[str, Any]:
    """
    Política UI de seguimiento para detalle/PUT de Gestión de Actuaciones.

    Parámetros:
        act: actuación persistida.
        ini: iniciador resuelto por ruta (no inferir desde act.notificacion_id).
        actuacion_editable: flag de bloqueo por intento posterior.

    Retorno:
        Dict con flags ``mostrar_*`` y ``puede_editar_seguimiento``.
    """
    mostrar_carnet = contexto_solicitud_carnet_gestion(ini, act)
    mostrar_subs = contexto_subsanacion_gestion(ini, act)
    puede_editar = bool(actuacion_editable and (mostrar_carnet or mostrar_subs))
    return {
        "mostrar_solicitud_carnet_manipulador": mostrar_carnet,
        "mostrar_subsanacion_notificacion": mostrar_subs,
        "puede_editar_seguimiento": puede_editar,
    }


def build_actuacion_seguimiento_detalle(
    act: Actuaciones,
    ini: IniciadorRuta | None,
    batch: ActuacionGridBatchMaps | None,
    *,
    actuacion_editable: bool,
) -> dict[str, Any] | None:
    """
    Payload anidado ``seguimiento`` para detalle autorizado de una actuación.

    Parámetros:
        act: actuación.
        ini: iniciador de ruta.
        batch: mapas precargados de seguimiento.
        actuacion_editable: si la actuación admite edición (bloqueo por intento posterior).

    Retorno:
        Dict con campos de carnet o subsanación según contexto (valores null si aún no hay registro),
        o None si ningún bloque aplica al origen.
    """
    ui = build_actuacion_gestion_ui_policy(act, ini, actuacion_editable=actuacion_editable)
    if not ui["mostrar_solicitud_carnet_manipulador"] and not ui["mostrar_subsanacion_notificacion"]:
        return None

    grid = _seguimiento_acta_grid_fields(
        act,
        batch,
        expose_telefono_solicitud_carnet=True,
    )
    out: dict[str, Any] = {}

    if ui["mostrar_solicitud_carnet_manipulador"]:
        out["solicita_carnet_manipulador"] = grid.get("solicita_carnet_manipulador")
        out["telefono_contacto_solicitud_carnet"] = grid.get("telefono_contacto_solicitud_carnet")

    if ui["mostrar_subsanacion_notificacion"]:
        out["faltas_notificacion_subsanadas"] = grid.get("faltas_notificacion_subsanadas")
        noti_map = batch.notificacion_by_id if batch is not None else None
        out["notificacion_origen_numero"] = notificacion_origen_numero_desde_iniciador(
            ini, noti_map
        )

    return out


def present_actuacion_gestion_detalle(act: Actuaciones) -> dict[str, Any]:
    """
    Presenta el detalle autorizado de Gestión: grilla sin teléfono plano + ``ui_policy`` + ``seguimiento``.
    """
    from app.domains.actuaciones.presenters.actuacion_presenters import (
        actuacion_to_grid_row,
        build_actuacion_grid_batch_maps,
        build_iniciador_ruta_por_actuacion_id,
    )
    from app.domains.actuaciones.services.actuacion_reencolado_service import (
        build_actuacion_editable_flags_por_actuacion_id,
    )
    from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
        build_counts_by_eo_from_actuaciones,
    )

    act_id = int(act.id)
    iniciador_map = build_iniciador_ruta_por_actuacion_id([act_id])
    ini = iniciador_map.get(act_id)
    batch = build_actuacion_grid_batch_maps([act], iniciador_map)
    counts_by_eo = build_counts_by_eo_from_actuaciones([act])
    editable_map = build_actuacion_editable_flags_por_actuacion_id([act_id])
    editable_override = editable_map.get(act_id)

    row = actuacion_to_grid_row(
        act,
        counts_by_eo=counts_by_eo,
        iniciador_desde_ruta=ini,
        batch=batch,
        editable_override=editable_override,
        expose_telefono_solicitud_carnet=False,
    )
    row.pop("telefono_contacto_solicitud_carnet", None)

    editable = bool(row.get("actuacion_editable", True))
    row["ui_policy"] = build_actuacion_gestion_ui_policy(
        act, ini, actuacion_editable=editable
    )
    seg = build_actuacion_seguimiento_detalle(
        act, ini, batch, actuacion_editable=editable
    )
    if seg is not None:
        row["seguimiento"] = seg
    return row
