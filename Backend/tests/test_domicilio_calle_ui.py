"""Tests calle_cargada / esquina_cargada vs claves técnicas en presenters."""

from __future__ import annotations

from app.domains.domicilios.utils.domicilio_calle_ui import (
    calle_cargada_desde_domicilio,
    esquina_cargada_desde_domicilio,
    esquina_key_desde_domicilio,
)
from app.models import Domicilio


def test_calle_cargada_prefiere_calle_raw_sobre_calle_key() -> None:
    dom = Domicilio(
        calle="monteagudo",
        numero="100",
        calle_raw="Monteagudo barrio sur",
        calle_key="monteagudo",
        calle_normalizada="Dr Bernardo Monteagudo",
        calle_norm_status="OK",
    )
    assert calle_cargada_desde_domicilio(dom) == "Monteagudo barrio sur"


def test_calle_cargada_sin_raw_usa_calle() -> None:
    dom = Domicilio(calle="San Martín 450", numero="10", calle_key="san martin 450")
    assert calle_cargada_desde_domicilio(dom) == "San Martín 450"


def test_esquina_cargada_prefiere_normalizada() -> None:
    dom = Domicilio(
        calle="monteagudo",
        numero="santiago del estero",
        numero_tipo="ESQUINA",
        esquina_raw="santiago del estero",
        esquina_normalizada="Santiago del Estero",
        esquina_norm_status="OK",
    )
    assert esquina_key_desde_domicilio(dom) == "santiago del estero"
    assert esquina_cargada_desde_domicilio(dom) == "Santiago del Estero"


def test_esquina_cargada_sin_normalizada_usa_raw() -> None:
    dom = Domicilio(
        calle="monteagudo",
        numero="santiago del estero",
        numero_tipo="ESQUINA",
        esquina_raw="Santiago del Estero cargada",
    )
    assert esquina_cargada_desde_domicilio(dom) == "Santiago del Estero cargada"
