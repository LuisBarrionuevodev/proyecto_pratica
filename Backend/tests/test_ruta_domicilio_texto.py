"""Etiqueta ``domicilio_texto`` en planificación / ruta (intersección vs referencia)."""

from unittest.mock import MagicMock

from app.domains.rutas_trabajo.presenters.ruta_presenters import _build_domicilio_texto_desde_dom


def _dom(
    *,
    calle_n: str | None = None,
    calle: str | None = None,
    numero: str = "",
    numero_tipo: str | None = None,
    esquina_n: str | None = None,
    esquina_raw: str | None = None,
    nombre_catalogo: str | None = None,
):
    dom = MagicMock()
    dom.calle_catalogo = None
    if nombre_catalogo:
        dom.calle_catalogo = MagicMock()
        dom.calle_catalogo.nombre_canonico = nombre_catalogo
    dom.calle_normalizada = calle_n
    dom.calle = calle
    dom.calle_raw = None
    dom.numero = numero
    dom.numero_tipo = numero_tipo
    dom.esquina_normalizada = esquina_n
    dom.esquina_raw = esquina_raw
    return dom


def test_esquina_formal_sin_duplicar_ref():
    dom = _dom(
        calle_n="Chacabuco",
        numero="ref Piedras",
        numero_tipo="ESQUINA",
        esquina_n="ref Piedras",
    )
    assert _build_domicilio_texto_desde_dom(dom) == "Chacabuco Y Piedras"


def test_esquina_catalogo_y_cruce_normalizado():
    dom = _dom(
        nombre_catalogo="Chacabuco",
        numero="Piedras",
        numero_tipo="ESQUINA",
        esquina_n="Piedras",
    )
    assert _build_domicilio_texto_desde_dom(dom) == "Chacabuco Y Piedras"


def test_numero_con_referencia_esquina_distinta():
    dom = _dom(
        calle_n="San Martín",
        numero="1200",
        numero_tipo="NUMERO",
        esquina_n="frente al hospital",
    )
    assert _build_domicilio_texto_desde_dom(dom) == "San Martín 1200 ref. frente al hospital"


def test_numero_sin_esquina_extra():
    dom = _dom(calle_n="Mitre", numero="500", numero_tipo="NUMERO", esquina_n=None)
    assert _build_domicilio_texto_desde_dom(dom) == "Mitre 500"
