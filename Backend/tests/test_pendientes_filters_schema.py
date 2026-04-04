"""Defaults de ActuacionesPendientesFilters (rango mes actual sin query params)."""

from datetime import timedelta

from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters


def test_filters_solo_source_type_aplica_rango_mes_actual() -> None:
    """Sin desde/hasta el schema completa el mes corriente (regresión: no día 0 inválido)."""
    f = ActuacionesPendientesFilters.model_validate({"source_type": "notificacion"})
    assert f.source_type == "notificacion"
    assert f.desde is not None and f.hasta is not None
    assert f.desde.day == 1
    assert f.desde.month == f.hasta.month
    assert f.desde <= f.hasta
    assert (f.hasta + timedelta(days=1)).day == 1
