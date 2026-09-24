"""
Seed/plan de calles canónicas desde CSV (CATALOGOS-PREDEPLOY.4).

Qué hace: diff compartido dry-run/apply por nombre_key + fallbacks legacy.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from app.domains.catalogos.seeds.catalog_matchers import (
    CalleIndexes,
    MatchAction,
    build_calle_indexes,
    resolve_calle,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import (
    normalize_display,
    slug_key,
    street_base,
)
from app.models import CalleCatalogo

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def iter_canonical_calles_from_csv(path: Path) -> list[str]:
    """
    Lee nombres canónicos del CSV versionado.

    Parameters:
        path: ruta al CSV con columna ``calles``.

    Returns:
        Lista de nombres canónicos en orden de archivo.
    """
    names: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw = row.get("calles")
            if raw is None and row:
                raw = next(iter(row.values()))
            canon = normalize_display(raw or "")
            if canon:
                names.append(canon)
    return names


def plan_calles_canonicas(session: Session, path: Path) -> tuple[list[str], list[str], CalleIndexes]:
    """
    Planifica CREATE/REUSE para cada calle canónica del CSV.

    Parameters:
        session: sesión SQLAlchemy.
        path: ruta al CSV canónico.

    Returns:
        Tupla (to_create, ambiguous_messages, indexes).

    Raises:
        ValueError: si hay entradas ambiguas.
    """
    indexes = build_calle_indexes(session)
    to_create: list[str] = []
    ambiguous: list[str] = []

    for canon in iter_canonical_calles_from_csv(path):
        result = resolve_calle(canon, indexes)
        if result.action == MatchAction.AMBIGUOUS:
            ambiguous.append(f"{canon}: {result.reason}")
        elif result.action == MatchAction.CREATE:
            to_create.append(canon)

    if ambiguous:
        raise ValueError("Calles canónicas ambiguas: " + "; ".join(ambiguous[:10]))

    return to_create, ambiguous, indexes


def apply_calles_canonicas(
    session: Session,
    path: Path,
    *,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """
    Ejecuta el plan de calles canónicas (mismo algoritmo que dry-run).

    Parameters:
        session: sesión SQLAlchemy.
        path: ruta al CSV canónico.
        dry_run: si True, solo planifica sin mutar sesión.

    Returns:
        Tupla (created, updated, skipped/reused).
    """
    to_create, _, _ = plan_calles_canonicas(session, path)
    created = len(to_create)
    skipped = len(iter_canonical_calles_from_csv(path)) - created

    if dry_run:
        return created, 0, skipped

    for canon in to_create:
        session.add(
            CalleCatalogo(
                nombre_canonico=canon,
                nombre_key=slug_key(canon),
                canon_base=street_base(canon),
                activo=True,
            )
        )

    return created, 0, skipped
