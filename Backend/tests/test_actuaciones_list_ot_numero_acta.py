"""
Filtro `orden_trabajo` del listado: debe resolver OT por `OrdenTrabajo.numero_acta` (no columna inexistente).
"""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.schemas.list_filters import ActuacionesListFilters
from app.domains.actuaciones.services.list_service import listar_actuaciones_con_filtros
from app.models import Actuaciones, OrdenTrabajo


def _unique_ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_ot_y_actuacion(numero_acta: str) -> tuple[OrdenTrabajo, Actuaciones]:
    ot = OrdenTrabajo(numero_acta=numero_acta, anio=2026, mes=5)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 5, 1),
        mes=5,
        anio=2026,
        orden_trabajo_id=ot.id,
    )
    db.session.add(act)
    db.session.flush()
    return ot, act


def test_listar_actuaciones_filtra_por_ot_numero_acta_sin_ceros_a_la_izquierda(app_ctx) -> None:
    """Búsqueda `orden_trabajo=42` debe matchear OT con `numero_acta='000042'`."""
    try:
        num = _unique_ot_num()
        ot, act = _mk_ot_y_actuacion(num)
        raw_int = str(int(num))
        filters = ActuacionesListFilters.model_validate(
            {"orden_trabajo": raw_int, "desde": "2026-05-01", "hasta": "2026-05-31"}
        )
        result = listar_actuaciones_con_filtros(filters)
        assert result["meta"]["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0].id == act.id
        assert result["items"][0].orden_trabajo_id == ot.id
    finally:
        db.session.rollback()


def test_listar_actuaciones_ot_inexistente_valueerror(app_ctx) -> None:
    try:
        existe = _unique_ot_num()
        _mk_ot_y_actuacion(existe)
        ot_busqueda = _unique_ot_num()
        while ot_busqueda == existe:
            ot_busqueda = _unique_ot_num()
        filters = ActuacionesListFilters.model_validate(
            {"orden_trabajo": ot_busqueda, "desde": "2026-05-01", "hasta": "2026-05-31"}
        )
        with pytest.raises(ValueError, match="No existe la orden de trabajo"):
            listar_actuaciones_con_filtros(filters)
    finally:
        db.session.rollback()
