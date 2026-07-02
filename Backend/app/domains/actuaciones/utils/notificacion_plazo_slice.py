"""Filtro operativo ``plazo_slice`` para bandeja NOTIFICACION (alineado al frontend)."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from app.models import Actuaciones, Notificacion
from app.domains.actuaciones.presenters.actuacion_presenters import (
    _dias_restantes_desde_vencimiento,
)

# Mismos umbrales que ``gestionNotificacionPlazo.ts``
DIAS_EN_PLAZO_MIN = 5
POR_VENCER_MIN = 1
POR_VENCER_MAX = 4

PLAZO_SLICE_VALUES = frozenset({"en_plazo", "por_vencer", "total"})


def normalize_plazo_slice_param(value: Optional[str]) -> Optional[str]:
    """
    Normaliza query param ``plazo_slice``.

    Retorna ``None`` si no aplica filtro (total, vacío o inválido ignorado en service).
    """
    if value is None:
        return None
    v = str(value).strip().lower()
    if not v or v == "total":
        return None
    if v in ("en_plazo", "por_vencer"):
        return v
    return None


def dias_restantes_notificacion_act(
    act: Actuaciones,
    venc_map: dict[int, date | None],
) -> int | None:
    """Días hábiles restantes usando la misma regla que el presenter."""
    if act.notificacion_id is None:
        return None
    return _dias_restantes_desde_vencimiento(venc_map.get(int(act.notificacion_id)))


def actuacion_matches_plazo_slice(
    act: Actuaciones,
    plazo_slice: str,
    venc_map: dict[int, date | None],
) -> bool:
    """
    Clasifica una actuación NOTIFICACION según ``dias_restantes`` canónico.

    Parámetros:
        act: actuación con ``notificacion_id``.
        plazo_slice: ``en_plazo`` o ``por_vencer``.
        venc_map: mapa ``notificacion_id`` → ``fecha_vencimiento``.

    Retorno:
        True si la fila pertenece al slice operativo.
    """
    d = dias_restantes_notificacion_act(act, venc_map)
    if d is None:
        return False
    if plazo_slice == "en_plazo":
        return d >= DIAS_EN_PLAZO_MIN
    if plazo_slice == "por_vencer":
        return POR_VENCER_MIN <= d <= POR_VENCER_MAX
    return True


def _build_venc_map_for_acts(acts: List[Actuaciones]) -> dict[int, date | None]:
    """Mapa ``notificacion_id`` → ``fecha_vencimiento`` (incluye prórrogas persistidas)."""
    noti_ids = list({int(a.notificacion_id) for a in acts if a.notificacion_id is not None})
    if not noti_ids:
        return {}
    notis = Notificacion.query.filter(Notificacion.id.in_(noti_ids)).all()
    return {int(n.id): n.fecha_vencimiento for n in notis}


def filter_actuaciones_notificacion_por_plazo_slice(
    acts: List[Actuaciones],
    plazo_slice: Optional[str],
) -> List[Actuaciones]:
    """
    Filtra actuaciones de bandeja NOTIFICACION por slice operativo.

    Solo aplica con ``plazo_slice`` en ``en_plazo`` / ``por_vencer``.
    """
    normalized = normalize_plazo_slice_param(plazo_slice)
    if not normalized or not acts:
        return acts
    venc_map = _build_venc_map_for_acts(acts)
    return [
        act
        for act in acts
        if actuacion_matches_plazo_slice(act, normalized, venc_map)
    ]
