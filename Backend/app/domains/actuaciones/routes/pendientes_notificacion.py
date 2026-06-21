from __future__ import annotations

from flask import jsonify

from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
    materializacion_notificacion_vencida_on_read_enabled,
    sync_iniciadores_reinspeccion_notificacion,
)
from app.models import IniciadorRuta

from . import actuacion


def _iniciador_id_por_actuacion_base(act_ids: list[int]) -> dict[int, int]:
    """
    Mapa ``actuacion_base_id`` → ``iniciador_id`` para filas PENDIENTE de reinspección por notificación.

    Parámetros:
        act_ids: ids de actuaciones INSPECCION devueltas por la cola operativa.

    Retorno:
        Dict actuacion_id → iniciador_ruta.id.
    """
    if not act_ids:
        return {}
    rows = (
        IniciadorRuta.query.filter(IniciadorRuta.actuacion_id.in_(act_ids))
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
        .filter(IniciadorRuta.estado_iniciador == "PENDIENTE")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .all()
    )
    out: dict[int, int] = {}
    for ini in rows:
        if ini.actuacion_id is not None:
            out[int(ini.actuacion_id)] = int(ini.id)
    return out


@actuacion.get("/pendientes-notificacion")
def get_pendientes_notificacion():
    """
    Lista operativa de reinspecciones por notificación vencida.

    Fase C: no ejecuta materialización salvo `SYNC_NOTIFICACIONES_VENCIDAS_ON_READ=1` (transitorio).
    En producción, el sync debe correr vía CLI / scheduler.
    """
    if materializacion_notificacion_vencida_on_read_enabled():
        sync_iniciadores_reinspeccion_notificacion()
    acts = list_reinspeccion_notificacion_operativas()
    counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
    ini_by_act = _iniciador_id_por_actuacion_base([int(a.id) for a in acts])
    payload = []
    for act in acts:
        row = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
        ini_id = ini_by_act.get(int(act.id))
        if ini_id is not None:
            row["iniciador_id"] = ini_id
            row["bandeja_row_key"] = f"{int(act.id)}-{ini_id}"
        row.setdefault("source_type", "NOTIFICACION")
        payload.append(row)
    return jsonify(payload), 200

