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
    include_telefono: bool,
) -> dict[str, Any] | None:
    """
    Payload anidado ``seguimiento`` para detalle autorizado de una actuación.

    Parámetros:
        act: actuación.
        ini: iniciador de ruta.
        batch: mapas precargados de seguimiento.
        include_telefono: incluir teléfono solo en detalle individual.

    Retorno:
        Dict con campos de carnet o subsanación según contexto, o None si no aplica.
    """
    ui = build_actuacion_gestion_ui_policy(act, ini, actuacion_editable=True)
    if not ui["mostrar_solicitud_carnet_manipulador"] and not ui["mostrar_subsanacion_notificacion"]:
        return None

    grid = _seguimiento_acta_grid_fields(
        act,
        batch,
        expose_telefono_solicitud_carnet=include_telefono,
    )
    out: dict[str, Any] = {}

    if ui["mostrar_solicitud_carnet_manipulador"]:
        out["solicita_carnet_manipulador"] = grid.get("solicita_carnet_manipulador")
        if include_telefono:
            out["telefono_contacto_solicitud_carnet"] = grid.get(
                "telefono_contacto_solicitud_carnet"
            )

    if ui["mostrar_subsanacion_notificacion"]:
        out["faltas_notificacion_subsanadas"] = grid.get("faltas_notificacion_subsanadas")
        noti_map = batch.notificacion_by_id if batch is not None else None
        out["notificacion_origen_numero"] = notificacion_origen_numero_desde_iniciador(
            ini, noti_map
        )

    return out or None


def enrich_actuacion_grid_row_gestion_detalle(
    row: dict[str, Any],
    act: Actuaciones,
    ini: IniciadorRuta | None,
    batch: ActuacionGridBatchMaps | None,
    *,
    include_telefono_en_seguimiento: bool,
) -> dict[str, Any]:
    """
    Añade ``ui_policy`` y ``seguimiento`` a la fila de grilla en modo detalle individual.
    """
    editable = bool(row.get("actuacion_editable", True))
    row["ui_policy"] = build_actuacion_gestion_ui_policy(
        act, ini, actuacion_editable=editable
    )
    seg = build_actuacion_seguimiento_detalle(
        act,
        ini,
        batch,
        include_telefono=include_telefono_en_seguimiento,
    )
    if seg is not None:
        row["seguimiento"] = seg
    return row
