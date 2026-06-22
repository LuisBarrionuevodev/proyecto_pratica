"""
Dry-run: REINSPECCION huérfanas (notificacion_id NULL) vinculables vía RutaItem + IniciadorRuta.

Uso:
    cd Backend
    PYTHONPATH=. python scripts/backfill_reinspeccion_notificacion_id_dry_run.py

    # Aplicar (solo tras revisar dry-run):
    PYTHONPATH=. python scripts/backfill_reinspeccion_notificacion_id_dry_run.py --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy.orm import aliased

from app import create_app
from app.database import db
from app.models import Actuaciones, IniciadorRuta, RutaItem


def find_orphan_reinspeccion_rows() -> list[dict]:
    """
    REINSPECCION con notificacion_id NULL enlazada a iniciador REINSPECCION_NOTIFICACION con notificacion_id.
    """
    Ini = aliased(IniciadorRuta)
    rows = (
        db.session.query(
            Actuaciones.id.label("reinspeccion_id"),
            Actuaciones.notificacion_id.label("act_notificacion_id"),
            RutaItem.id.label("ruta_item_id"),
            Ini.id.label("iniciador_id"),
            Ini.notificacion_id.label("iniciador_notificacion_id"),
        )
        .join(RutaItem, RutaItem.actuacion_id == Actuaciones.id)
        .join(Ini, Ini.id == RutaItem.iniciador_ruta_id)
        .filter(Actuaciones.tipo == "REINSPECCION")
        .filter(Actuaciones.notificacion_id.is_(None))
        .filter(Ini.tipo_iniciador == "REINSPECCION_NOTIFICACION")
        .filter(Ini.notificacion_id.isnot(None))
        .filter(RutaItem.deleted_at.is_(None))
        .filter(Ini.deleted_at.is_(None))
        .order_by(Actuaciones.id.asc())
        .all()
    )
    return [
        {
            "reinspeccion_id": int(r.reinspeccion_id),
            "act_notificacion_id": r.act_notificacion_id,
            "ruta_item_id": int(r.ruta_item_id),
            "iniciador_id": int(r.iniciador_id),
            "iniciador_notificacion_id": int(r.iniciador_notificacion_id),
        }
        for r in rows
    ]


def apply_backfill(candidates: list[dict]) -> int:
    """Setea ``actuaciones.notificacion_id`` desde iniciador; retorna filas actualizadas."""
    updated = 0
    for row in candidates:
        act = db.session.get(Actuaciones, row["reinspeccion_id"])
        if act is None or act.tipo != "REINSPECCION" or act.notificacion_id is not None:
            continue
        nid = row["iniciador_notificacion_id"]
        act.notificacion_id = nid
        db.session.add(act)
        updated += 1
    if updated:
        db.session.commit()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill notificacion_id en REINSPECCION huérfanas")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar cambios (default: solo dry-run)",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        candidates = find_orphan_reinspeccion_rows()
        print(f"Candidatos encontrados: {len(candidates)}")
        for row in candidates:
            print(row)
        if args.apply:
            n = apply_backfill(candidates)
            print(f"Actualizadas: {n}")
        else:
            print("Dry-run: no se modificó la base. Usar --apply para persistir.")


if __name__ == "__main__":
    main()
