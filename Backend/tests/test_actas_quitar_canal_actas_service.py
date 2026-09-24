import pytest

from app.domains.actuaciones.services.actas_quitar_canal_actas_service import quitar_acta_canal_actas


def test_quitar_acta_rechaza_tipo_invalido(app) -> None:
    with app.app_context():
        with pytest.raises(ValueError, match="inválido"):
            quitar_acta_canal_actas(1, "NO_EXISTE")
