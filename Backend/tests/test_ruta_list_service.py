"""Tests mínimos para el listado de rutas en BORRADOR."""

import pytest

from app.domains.rutas_trabajo.services.ruta_list_service import list_rutas_borrador


def test_list_rutas_borrador_rejects_invalid_page() -> None:
    """page debe ser >= 1."""
    with pytest.raises(ValueError, match="page"):
        list_rutas_borrador(page=0)
