"""
PREDEPLOY-FIX.1 — regresión RELEVAMIENTOS-500 (defaults fecha + ValidationError serializable).
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from pydantic import ValidationError

from app.domains.relevamientos.schemas import list_filters as list_filters_mod
from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters
from app.shared.errors import pydantic_errors_to_cell_map


def _patch_today(monkeypatch: pytest.MonkeyPatch, today: date) -> None:
    """Monkeypatch date.today() en list_filters sin romper el constructor date()."""

    class _DateWithToday(date):
        @classmethod
        def today(cls) -> date:
            return today

    monkeypatch.setattr(list_filters_mod, "date", _DateWithToday)


@pytest.mark.parametrize(
    "today,expected_desde,expected_hasta",
    [
        (date(2026, 1, 15), date(2026, 1, 1), date(2026, 1, 31)),
        (date(2025, 2, 15), date(2025, 2, 1), date(2025, 2, 28)),
        (date(2028, 2, 15), date(2028, 2, 1), date(2028, 2, 29)),
        (date(2026, 4, 10), date(2026, 4, 1), date(2026, 4, 30)),
        (date(2026, 9, 20), date(2026, 9, 1), date(2026, 9, 30)),
        (date(2026, 11, 5), date(2026, 11, 1), date(2026, 11, 30)),
        (date(2026, 12, 15), date(2026, 12, 1), date(2026, 12, 31)),
    ],
)
def test_default_month_range_cases(
    monkeypatch: pytest.MonkeyPatch,
    today: date,
    expected_desde: date,
    expected_hasta: date,
) -> None:
    _patch_today(monkeypatch, today)
    filters = RelevamientosListFilters.model_validate({})
    assert filters.desde == expected_desde
    assert filters.hasta == expected_hasta


@pytest.mark.parametrize(
    "month,last_day",
    [
        (1, 31),
        (2, 28),
        (3, 31),
        (4, 30),
        (5, 31),
        (6, 30),
        (7, 31),
        (8, 31),
        (9, 30),
        (10, 31),
        (11, 30),
        (12, 31),
    ],
)
def test_default_month_range_parametrized_non_leap(
    monkeypatch: pytest.MonkeyPatch, month: int, last_day: int
) -> None:
    year = 2025
    _patch_today(monkeypatch, date(year, month, 15))
    filters = RelevamientosListFilters.model_validate({})
    assert filters.desde == date(year, month, 1)
    assert filters.hasta == date(year, month, last_day)


def test_explicit_range_unchanged() -> None:
    filters = RelevamientosListFilters.model_validate(
        {"desde": "2026-01-01", "hasta": "2026-01-31"}
    )
    assert filters.desde == date(2026, 1, 1)
    assert filters.hasta == date(2026, 1, 31)


def test_desde_gt_hasta_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        RelevamientosListFilters.model_validate(
            {"desde": "2026-05-10", "hasta": "2026-05-01"}
        )


def test_invalid_date_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        RelevamientosListFilters.model_validate({"desde": "2026-02-30"})


def test_pydantic_errors_to_cell_map_serializable_on_value_error() -> None:
    """Regression: ctx.error ValueError debe serializarse (defecto secundario del 500)."""
    try:
        RelevamientosListFilters.model_validate(
            {"desde": "2026-05-10", "hasta": "2026-05-01"}
        )
    except ValidationError as exc:
        mapped = pydantic_errors_to_cell_map(exc)
        json.dumps(mapped)
        assert "_row" in mapped or any(k for k in mapped)
        return
    raise AssertionError("expected ValidationError")


# --- API integration ---


def test_get_relevamientos_sin_params_200(client, auth_headers) -> None:
    resp = client.get("/relevamientos/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "meta" in data


def test_get_relevamientos_explicit_range_200(client, auth_headers) -> None:
    resp = client.get(
        "/relevamientos/?desde=2026-01-01&hasta=2026-01-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "items" in resp.get_json()


def test_get_relevamientos_empty_range_200(client, auth_headers) -> None:
    resp = client.get(
        "/relevamientos/?desde=2099-01-01&hasta=2099-01-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["items"] == []


def test_get_relevamientos_invalid_date_422_not_500(client, auth_headers) -> None:
    resp = client.get("/relevamientos/?desde=2026-02-30", headers=auth_headers)
    assert resp.status_code == 422
    assert resp.status_code != 500
    data = resp.get_json()
    assert data is not None
    json.dumps(data)


def test_get_relevamientos_desde_gt_hasta_422_not_500(client, auth_headers) -> None:
    resp = client.get(
        "/relevamientos/?desde=2026-05-10&hasta=2026-05-01",
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.status_code != 500
    data = resp.get_json()
    assert data is not None
    json.dumps(data)
    assert "errors" in data


def test_get_relevamientos_gestion_operativa_invalid_date_422(client, auth_headers) -> None:
    resp = client.get(
        "/relevamientos/gestion-operativa?desde=2026-02-30",
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.status_code != 500
    json.dumps(resp.get_json())
