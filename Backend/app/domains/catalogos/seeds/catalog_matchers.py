"""
Matchers compartidos entre seed y validación canónica (CATALOGOS-PREDEPLOY.4).

Qué hace: resuelve identidad de rubros (ai_ci) y calles (nombre_key + fallbacks).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domains.catalogos.canonical.normalize import (
    normalize_ai_ci_identity,
    normalize_catalog_display,
    normalize_catalog_key,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import (
    normalize_display,
    slug_key,
)
from app.models import CalleCatalogo, Rubro

T = TypeVar("T")


class MatchAction(str, Enum):
    """Resultado de reconciliación por entrada canónica."""

    REUSE = "reuse"
    CREATE = "create"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class MatchResult:
    """Plan de acción para una entrada canónica."""

    action: MatchAction
    entity: object | None = None
    reason: str = ""


def build_rubro_identity_index(session: Session) -> dict[str, list[Rubro]]:
    """
    Índice ``identity_key`` → filas rubro (precarga única).

    Parameters:
        session: sesión SQLAlchemy.

    Returns:
        Mapa identity → lista de rubros.
    """
    index: dict[str, list[Rubro]] = defaultdict(list)
    for row in session.query(Rubro).all():
        index[normalize_ai_ci_identity(row.nombre)].append(row)
    return index


def resolve_rubro(
    session: Session,
    nombre_canonico: str,
    *,
    index: dict[str, list[Rubro]] | None = None,
) -> MatchResult:
    """
    Resuelve un rubro canónico contra DB con semántica ai_ci.

    Parameters:
        session: sesión SQLAlchemy.
        nombre_canonico: nombre canónico a reconciliar.
        index: índice precargado opcional.

    Returns:
        MatchResult con REUSE, CREATE o AMBIGUOUS.

    Raises:
        ValueError: si hay ambigüedad o error de guard SQL.
    """
    display = normalize_catalog_display(nombre_canonico)
    identity = normalize_ai_ci_identity(display)
    idx = index if index is not None else build_rubro_identity_index(session)

    candidates = idx.get(identity, [])
    if len(candidates) > 1:
        ids = [r.id for r in candidates]
        return MatchResult(
            MatchAction.AMBIGUOUS,
            reason=f"múltiples rubros para identity={identity!r}: ids={ids}",
        )
    if len(candidates) == 1:
        return MatchResult(MatchAction.REUSE, candidates[0])

    sql_rows = session.execute(
        text(
            """
            SELECT id, nombre
            FROM rubro
            WHERE nombre = :nombre COLLATE utf8mb4_0900_ai_ci
            """
        ),
        {"nombre": display},
    ).fetchall()
    if len(sql_rows) > 1:
        ids = [int(r[0]) for r in sql_rows]
        return MatchResult(
            MatchAction.AMBIGUOUS,
            reason=f"colisión UNIQUE ai_ci para rubro {display!r}: ids={ids}",
        )
    if len(sql_rows) == 1:
        row_id = int(sql_rows[0][0])
        entity = session.get(Rubro, row_id)
        return MatchResult(MatchAction.REUSE, entity)

    return MatchResult(MatchAction.CREATE)


@dataclass(frozen=True)
class CalleIndexes:
    """Índices precargados para resolver calles canónicas."""

    by_key: dict[str, CalleCatalogo]
    by_key_fold: dict[str, list[CalleCatalogo]]
    by_canon_identity: dict[str, list[CalleCatalogo]]
    by_slug_of_key: dict[str, list[CalleCatalogo]]
    all_rows: tuple[CalleCatalogo, ...]


def build_calle_indexes(session: Session) -> CalleIndexes:
    """
    Precarga calle_catalogo en índices de búsqueda.

    Parameters:
        session: sesión SQLAlchemy.

    Returns:
        CalleIndexes con mapas por key y nombre canónico.
    """
    rows = tuple(session.query(CalleCatalogo).all())
    by_key: dict[str, CalleCatalogo] = {}
    by_key_fold: dict[str, list[CalleCatalogo]] = defaultdict(list)
    by_canon_identity: dict[str, list[CalleCatalogo]] = defaultdict(list)
    by_slug_of_key: dict[str, list[CalleCatalogo]] = defaultdict(list)

    for row in rows:
        by_key[row.nombre_key] = row
        by_key_fold[row.nombre_key.casefold()].append(row)
        by_canon_identity[normalize_ai_ci_identity(row.nombre_canonico)].append(row)
        by_slug_of_key[slug_key(row.nombre_key)].append(row)

    return CalleIndexes(
        by_key=by_key,
        by_key_fold=dict(by_key_fold),
        by_canon_identity=dict(by_canon_identity),
        by_slug_of_key=dict(by_slug_of_key),
        all_rows=rows,
    )


def resolve_calle(
    nombre_canonico: str,
    indexes: CalleIndexes,
) -> MatchResult:
    """
    Resuelve una calle canónica sin colapsar por ``canon_base``.

    Orden: ``nombre_key`` (slug) → key legacy casefold → identidad del
    ``nombre_canonico`` → slug de ``nombre_key`` legacy.

    Parameters:
        nombre_canonico: nombre canónico del CSV/fuente.
        indexes: índices precargados.

    Returns:
        MatchResult REUSE, CREATE o AMBIGUOUS.
    """
    canon = normalize_display(nombre_canonico)
    if not canon:
        return MatchResult(MatchAction.CREATE, reason="nombre vacío")

    key = slug_key(canon)

    if key in indexes.by_key:
        return MatchResult(MatchAction.REUSE, indexes.by_key[key])

    folded_matches = indexes.by_key_fold.get(key.casefold(), [])
    if len(folded_matches) == 1:
        return MatchResult(MatchAction.REUSE, folded_matches[0])
    if len(folded_matches) > 1:
        ids = [r.id for r in folded_matches]
        return MatchResult(
            MatchAction.AMBIGUOUS,
            reason=f"múltiples calles para key casefold {key!r}: ids={ids}",
        )

    canon_identity = normalize_ai_ci_identity(canon)
    canon_matches = indexes.by_canon_identity.get(canon_identity, [])
    if len(canon_matches) == 1:
        return MatchResult(MatchAction.REUSE, canon_matches[0])
    if len(canon_matches) > 1:
        ids = [r.id for r in canon_matches]
        return MatchResult(
            MatchAction.AMBIGUOUS,
            reason=f"múltiples calles para nombre {canon!r}: ids={ids}",
        )

    slug_key_matches = indexes.by_slug_of_key.get(key, [])
    if len(slug_key_matches) == 1:
        return MatchResult(MatchAction.REUSE, slug_key_matches[0])
    if len(slug_key_matches) > 1:
        ids = [r.id for r in slug_key_matches]
        return MatchResult(
            MatchAction.AMBIGUOUS,
            reason=f"múltiples calles slug legacy para {key!r}: ids={ids}",
        )

    for row in indexes.all_rows:
        if row.nombre_key.casefold() == canon.casefold():
            return MatchResult(MatchAction.REUSE, row)

    return MatchResult(MatchAction.CREATE)


def exists_rubro(session: Session, nombre: str, *, index: dict[str, list[Rubro]] | None = None) -> bool:
    """True si el rubro canónico resuelve en DB."""
    return resolve_rubro(session, nombre, index=index).action == MatchAction.REUSE


def exists_calle(nombre_canonico: str, indexes: CalleIndexes) -> bool:
    """True si la calle canónica resuelve en DB."""
    return resolve_calle(nombre_canonico, indexes).action == MatchAction.REUSE


def exists_nombre_catalog(session: Session, model, nombre: str) -> bool:
    """Presencia por clave normalize_catalog_key (catálogos simples por nombre)."""
    key = normalize_catalog_key(nombre)
    return any(normalize_catalog_key(r.nombre) == key for r in session.query(model).all())
