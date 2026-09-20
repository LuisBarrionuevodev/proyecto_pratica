from __future__ import annotations

import argparse
import csv
from typing import TYPE_CHECKING, Tuple

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import (
    normalize_display,
    slug_key,
    street_base,
)
from app.models import CalleCatalogo

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def importar_csv(
    path: str,
    *,
    session: Session | None = None,
    commit: bool = True,
) -> Tuple[int, int, int]:
    """
    Importa catálogo de calles desde CSV.

    Parameters:
        path: ruta al CSV.
        session: sesión SQLAlchemy opcional.
        commit: si True, hace commit al finalizar.

    Returns:
        Tupla (created, updated, skipped).
    """
    sess = session or db.session
    created = 0
    updated = 0
    skipped = 0

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canon_raw = row.get("calles")
            if canon_raw is None:
                if len(row) == 1:
                    canon_raw = next(iter(row.values()))
                else:
                    canon_raw = ""
            canon = normalize_display(canon_raw)
            if not canon:
                skipped += 1
                continue
            key = slug_key(canon)
            base = street_base(canon)
            existing = sess.query(CalleCatalogo).filter_by(nombre_key=key).first()
            if existing:
                if existing.nombre_canonico != canon:
                    existing.nombre_canonico = canon
                    existing.canon_base = base
                    sess.add(existing)
                    updated += 1
                else:
                    skipped += 1
                continue
            sess.add(
                CalleCatalogo(
                    nombre_canonico=canon,
                    nombre_key=key,
                    canon_base=base,
                    activo=True,
                )
            )
            created += 1

    if commit:
        sess.commit()
    return created, updated, skipped


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="Ruta al CSV de calles normalizadas")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    from app.main import create_app

    app = create_app()
    with app.app_context():
        created, updated, skipped = importar_csv(args.path)
        print(f"Import OK. created={created} updated={updated} skipped={skipped}")


if __name__ == "__main__":
    main()
