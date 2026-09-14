"""Catálogo de relevadores para el dominio Relevamientos."""

from __future__ import annotations

from typing import Any, Iterable, List, Sequence

from sqlalchemy import func

from app.database import db
from app.models import Relevador

_SPACE_RE = __import__("re").compile(r"\s+")


def _upper_norm(s: str) -> str:
    s = s.strip().upper()
    s = s.replace("_", " ")
    s = _SPACE_RE.sub(" ", s)
    return s


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
        Lista de dicts ``{id, nombre}``.
    """
    q = Relevador.query
    if solo_activos:
        q = q.filter(Relevador.activo.is_(True))
    rows = q.order_by(Relevador.nombre.asc()).all()
    return [{"id": int(r.id), "nombre": r.nombre} for r in rows]


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
        raise ValueError("Debe indicar al menos un relevador.")

    rows = Relevador.query.filter(Relevador.id.in_(unique_ids)).all()
    by_id = {int(r.id): r for r in rows}
    missing = [i for i in unique_ids if i not in by_id]
    if missing:
        raise ValueError(f"Relevador inexistente: {missing[0]}.")

    if requiere_activos:
        inactivos = [r.nombre for r in rows if not r.activo]
        if inactivos:
            raise ValueError(f"Relevador inactivo: {inactivos[0]}.")

    return [by_id[i] for i in unique_ids]


def resolve_relevador_nombres_o_falla(
    nombres: Sequence[str],
    *,
    requiere_activos: bool = True,
) -> List[Relevador]:
    """
    Resuelve nombres de relevadores contra catálogo (normalización upper/underscore).

    Parámetros:
        nombres: nombres canónicos (sin duplicados lógicos).
        requiere_activos: rechaza inactivos para nuevas asignaciones.

    Retorno:
        Lista de ``Relevador``.

    Errores:
        ValueError: sin nombres, nombre inválido o inactivo.
    """
    cleaned: List[str] = []
    seen_norm: set[str] = set()
    for raw in nombres:
        s = (raw or "").strip()
        if not s:
            continue
        norm = _upper_norm(s)
        if norm in seen_norm:
            continue
        seen_norm.add(norm)
        cleaned.append(s)

    if not cleaned:
        raise ValueError("Debe indicar al menos un relevador.")

    out: List[Relevador] = []
    for nombre in cleaned:
        norm = _upper_norm(nombre)
        row = (
            db.session.query(Relevador)
            .filter(func.replace(func.upper(Relevador.nombre), "_", " ") == norm)
            .limit(1)
            .first()
        )
        if row is None:
            raise ValueError(f"Relevador inválido: {nombre}.")
        if requiere_activos and not row.activo:
            raise ValueError(f"Relevador inactivo: {row.nombre}.")
        out.append(row)
    return out
