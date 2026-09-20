"""Sincronización N:N Relevamiento ↔ Relevador."""

from __future__ import annotations

from typing import Iterable, List

from app.database import db
from app.models import Relevador, Relevamiento
from app.domains.relevamientos.catalogs.relevador import get_relevadores_o_falla


def sync_relevamiento_relevadores(
    relevamiento: Relevamiento,
    relevador_ids: Iterable[int],
    *,
    requiere_activos: bool = True,
) -> List[Relevador]:
    """
    Reemplaza las asociaciones de relevadores de un relevamiento.

    Parámetros:
        relevamiento: entidad persistida (con id).
        relevador_ids: exactamente un id único.
        requiere_activos: valida activos para nuevas asignaciones.

    Retorno:
        Lista de relevadores asociados (longitud 1).

    Errores:
        ValueError: validación de catálogo o cardinalidad distinta de 1.
    """
    ids_list = list(relevador_ids)
    if len(ids_list) != 1:
        raise ValueError("Debe indicar exactamente un relevador.")
    relevadores = get_relevadores_o_falla(ids_list, requiere_activos=requiere_activos)
    relevamiento.relevadores = relevadores
    db.session.flush()
    return relevadores
