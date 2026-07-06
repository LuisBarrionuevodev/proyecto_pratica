"""
PR6A — Diagnóstico de calle_catalogo para patrones Roca / Julio / Septiembre.

Uso:
    cd Backend
    python -m app.scripts.diagnosticar_calle_catalogo_patrones
"""

from __future__ import annotations

import json

from sqlalchemy import func

from app import create_app
from app.models import CalleCatalogo

_PATTERNS = ("%roca%", "%julio%", "%septiembre%")

_EXACT_NAMES = (
    "Roca",
    "Julio Argentino Roca",
    "General Roca",
    "9 de Julio",
    "Nueve de Julio",
    "24 de Septiembre",
    "Veinticuatro de Septiembre",
)


def diagnosticar_calle_catalogo_patrones() -> dict:
    """
    Busca calles oficiales por ILIKE y por nombre exacto.

    Retorno:
        Dict serializable con resultados por patrón y nombres exactos.
    """
    by_pattern: dict[str, list[dict]] = {}
    for pattern in _PATTERNS:
        rows = (
            CalleCatalogo.query.filter(
                CalleCatalogo.activo.is_(True),
                func.upper(CalleCatalogo.nombre_canonico).like(pattern.upper()),
            )
            .order_by(CalleCatalogo.nombre_canonico)
            .all()
        )
        by_pattern[pattern] = [
            {
                "id": r.id,
                "nombre_canonico": r.nombre_canonico,
                "nombre_key": r.nombre_key,
                "canon_base": r.canon_base,
            }
            for r in rows
        ]

    exact_lookup: dict[str, dict | None] = {}
    for name in _EXACT_NAMES:
        row = (
            CalleCatalogo.query.filter(
                CalleCatalogo.activo.is_(True),
                func.upper(CalleCatalogo.nombre_canonico) == name.upper(),
            )
            .first()
        )
        exact_lookup[name] = (
            {
                "id": row.id,
                "nombre_canonico": row.nombre_canonico,
                "nombre_key": row.nombre_key,
                "canon_base": row.canon_base,
            }
            if row
            else None
        )

    return {"by_pattern": by_pattern, "exact_lookup": exact_lookup}


def main() -> int:
    """Imprime diagnóstico JSON."""
    app = create_app()
    with app.app_context():
        report = diagnosticar_calle_catalogo_patrones()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
