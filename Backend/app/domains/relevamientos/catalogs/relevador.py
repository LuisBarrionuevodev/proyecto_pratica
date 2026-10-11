"""Catálogo de relevadores para el dominio Relevamientos."""

from __future__ import annotations

from typing import Any, Iterable, List, Sequence

from app.domains.relevamientos.utils.relevador_display import (
    relevador_etiqueta_catalogo,
    relevador_sort_key,
)
from app.domains.relevamientos.utils.relevador_resolve import (
    resolve_relevador_nombres_o_falla,
    resolve_relevador_unico_por_nombre_celda,
)
from app.models import Relevador


def _dedupe_preserve_order(ids: Iterable[int]) -> List[int]:
    seen: set[int] = set()
    out: List[int] = []
    for rid in ids:
        if rid in seen:
            continue
        seen.add(rid)
        out.append(rid)
    return out


def listar_relevadores_catalogo(*, solo_activos: bool = True) -> list[dict[str, Any]]:
    """
    Lista relevadores para dropdowns.

    Parámetros:
        solo_activos: si True, filtra ``activo=True`` (alta de nuevos relevamientos).

    Retorno:
        Lista de dicts ``{id, nombre}`` con ``nombre`` en formato ``Apellido, Nombre``.
    """
    q = Relevador.query
    if solo_activos:
        q = q.filter(Relevador.activo.is_(True))
    rows = q.all()
    rows.sort(key=lambda r: relevador_sort_key(r.nombre))
    return [{"id": int(r.id), "nombre": relevador_etiqueta_catalogo(r.nombre)} for r in rows]


def get_relevador_by_id(relevador_id: int) -> Relevador | None:
    """Obtiene un relevador por id."""
    return Relevador.query.filter(Relevador.id == relevador_id).first()


def get_relevadores_o_falla(
    relevador_ids: Sequence[int],
    *,
    requiere_activos: bool = True,
) -> List[Relevador]:
    """
    Resuelve IDs de relevadores existentes, sin duplicados.

    Parámetros:
        relevador_ids: lista de ids (mínimo 1 para alta).
        requiere_activos: si True, rechaza inactivos (nuevas asignaciones).

    Retorno:
        Lista de ``Relevador`` en el mismo orden de ids únicos.

    Errores:
        ValueError: lista vacía, duplicados implícitos ignorados pero id inexistente o inactivo.
    """
    unique_ids = _dedupe_preserve_order(relevador_ids)
    if not unique_ids:
        raise ValueError("Debe indicar un relevador.")

    rows = Relevador.query.filter(Relevador.id.in_(unique_ids)).all()
    by_id = {int(r.id): r for r in rows}
    missing = [i for i in unique_ids if i not in by_id]
    if missing:
        raise ValueError("Relevador no encontrado. Seleccioná uno del catálogo.")

    if requiere_activos:
        inactivos = [r.nombre for r in rows if not r.activo]
        if inactivos:
            raise ValueError(f"Relevador inactivo: {inactivos[0]}.")

    return [by_id[i] for i in unique_ids]
