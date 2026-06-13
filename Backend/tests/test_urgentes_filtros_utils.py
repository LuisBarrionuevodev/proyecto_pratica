"""Tests unitarios para filtros de urgentes (M3)."""

from app.domains.rutas_trabajo.utils.urgentes_filtros import TIPOS_OFICIO_URGENTE


def test_tipos_oficio_urgente_incluye_ratificaciones():
    assert "REINSPECCION_OFICIO" in TIPOS_OFICIO_URGENTE
    assert "VERIFICAR_INFORMAR_OFICIO" in TIPOS_OFICIO_URGENTE
    assert len(TIPOS_OFICIO_URGENTE) == 4
