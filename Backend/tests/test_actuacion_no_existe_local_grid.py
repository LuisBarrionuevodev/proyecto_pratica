"""NO_EXISTE_LOCAL en PUT/validación grid actuaciones (ESTABILIDAD-MÓVIL.1)."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    contraproducencia_es_familia_no_existe_local,
)
from app.domains.actuaciones.utils.circuito_operativo import build_actuacion_grid_validation_context
from app.models import CatalogContraproducencia


def _nombre_no_existe_en_catalogo() -> str | None:
    for (nombre,) in db.session.query(CatalogContraproducencia.nombre).all():
        if nombre and contraproducencia_es_familia_no_existe_local(str(nombre)):
            return str(nombre).strip()
    return None


def test_coerce_contraproducencia_no_existe_local_alias(app_ctx) -> None:
    nombre = _nombre_no_existe_en_catalogo()
    if not nombre:
        pytest.skip("Catálogo sin familia NO EXISTE LOCAL")
    row = ActuacionGridRowIn.model_validate(
        {
            "id": 1,
            "orden_trabajo_numero": "123456",
            "fecha_actuacion": "2026-06-15",
            "tipo_actuacion": "INSPECCION",
            "contraproducencia": "NO_EXISTE_LOCAL",
        },
        context=build_actuacion_grid_validation_context(1),
    )
    assert contraproducencia_es_familia_no_existe_local(row.contraproducencia or "")


def test_grid_no_existe_local_sin_rubro_ni_actas(app_ctx) -> None:
    nombre = _nombre_no_existe_en_catalogo()
    if not nombre:
        pytest.skip("Catálogo sin familia NO EXISTE LOCAL")
    row = ActuacionGridRowIn.model_validate(
        {
            "id": 99,
            "orden_trabajo_numero": "654321",
            "fecha_actuacion": date(2026, 6, 15),
            "tipo_actuacion": "INSPECCION",
            "contraproducencia": nombre,
            "inspectores": [],
        },
        context=build_actuacion_grid_validation_context(99),
    )
    assert row.contraproducencia


def test_grid_no_existe_local_rechaza_acta_inspeccion(app_ctx) -> None:
    nombre = _nombre_no_existe_en_catalogo()
    if not nombre:
        pytest.skip("Catálogo sin familia NO EXISTE LOCAL")
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ActuacionGridRowIn.model_validate(
            {
                "id": 99,
                "orden_trabajo_numero": "654321",
                "fecha_actuacion": "2026-06-15",
                "tipo_actuacion": "INSPECCION",
                "contraproducencia": nombre,
                "acta_inspeccion_num": "100",
            },
            context=build_actuacion_grid_validation_context(99),
        )
