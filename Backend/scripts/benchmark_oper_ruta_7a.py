"""OPER-RUTA.7A — Benchmark M3/M4 planificación (solo medición, no modifica datos)."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("PLANIFICACION_DEBUG", "1")


def main() -> int:
    from app import create_app
    from app.database import db
    from app.domains.rutas_trabajo.services.planificacion_service import (
        get_planificacion_pendientes_contexto,
        get_planificacion_urgentes,
    )
    from app.models import Distrito, RutaTrabajo

    app = create_app()
    with app.app_context():
        ruta = (
            RutaTrabajo.query.filter(RutaTrabajo.estado_ruta == "BORRADOR")
            .order_by(RutaTrabajo.id.desc())
            .first()
        )
        if not ruta:
            print("No hay ruta BORRADOR para benchmark.")
            return 1

        distrito = Distrito.query.order_by(Distrito.id.asc()).first()
        if not distrito:
            print("No hay distritos en BD.")
            return 1

        print(f"Benchmark ruta_id={ruta.id} distrito_id={distrito.id} fecha={ruta.fecha}")
        print("--- URGENTES (M3) ---")
        items_u, total_u = get_planificacion_urgentes(
            int(ruta.id), page=1, per_page=25
        )
        print(f"urgentes page1 items={len(items_u)} total={total_u}")

        print("--- M4 pendientes-contexto (1 página 500) ---")
        items_m4, total_m4 = get_planificacion_pendientes_contexto(
            int(ruta.id),
            distrito_id=int(distrito.id),
            tipo=None,
            prioridad=None,
            prioridad_categoria=None,
            q=None,
            turno_sugerido=None,
            calle_catalogo_id=None,
            page=1,
            per_page=500,
            orden="prioridad",
        )
        print(f"m4 page1 items={len(items_m4)} total={total_m4}")

        db.session.rollback()
    return 0


if __name__ == "__main__":
    sys.exit(main())
