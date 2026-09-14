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
        relevador_ids: ids únicos (mínimo 1).
        requiere_activos: valida activos para nuevas asignaciones.

    Retorno:
        Lista de relevadores asociados.

    Errores:
        ValueError: validación de catálogo.
    """
    relevadores = get_relevadores_o_falla(list(relevador_ids), requiere_activos=requiere_activos)
    relevamiento.relevadores = relevadores
    db.session.flush()
    return relevadores
