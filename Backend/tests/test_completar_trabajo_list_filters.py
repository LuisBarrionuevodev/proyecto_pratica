from datetime import date

import pytest
from pydantic import ValidationError

from app.domains.actuaciones.schemas.completar_trabajo_list_filters import CompletarTrabajoPendientesListFilters


def test_completar_trabajo_filters_fecha_string() -> None:
    f = CompletarTrabajoPendientesListFilters.model_validate({"fecha": "2025-03-22", "page": 1, "per_page": 20})
    assert f.fecha == date(2025, 3, 22)
    assert f.page == 1
    assert f.per_page == 20


def test_completar_trabajo_filters_per_page_max() -> None:
    with pytest.raises(ValidationError):
        CompletarTrabajoPendientesListFilters.model_validate({"fecha": "2025-01-01", "per_page": 99})
