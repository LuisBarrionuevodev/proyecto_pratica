"""Domicilio visible en Establecimientos (PR10.4b.5)."""

from __future__ import annotations

from types import SimpleNamespace

from app.domains.establecimientos.utils.domicilio_display import (
    domicilio_texto_ficha_detalle,
    domicilio_texto_historial_fila,
    domicilio_texto_visible,
)


def _dom(
    *,
    calle: str | None = None,
    calle_raw: str | None = None,
    calle_normalizada: str | None = None,
    numero: str | None = None,
    numero_tipo: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        calle=calle,
        calle_raw=calle_raw,
        calle_normalizada=calle_normalizada,
        numero=numero,
        numero_tipo=numero_tipo or "NUMERO",
        esquina_normalizada=None,
        esquina_raw=None,
        calle_catalogo=None,
    )


def test_domicilio_texto_prioriza_normalizada_sobre_raw() -> None:
    dom = _dom(
        calle="calle raw relevamiento",
        calle_raw="calle raw relevamiento",
        calle_normalizada="San Martín",
        numero="2869",
    )
    assert domicilio_texto_visible(dom) == "San Martín 2869"


def test_domicilio_ficha_detalle_prioriza_ultima_actuacion() -> None:
    dom_ficha = _dom(calle="raw viejo", numero="1")
    dom_act = _dom(calle_normalizada="Corregida Final", numero="100")
    assert domicilio_texto_ficha_detalle(dom_ficha, dom_act) == "Corregida Final 100"


def test_domicilio_historial_fila_usa_domicilio_de_actuacion() -> None:
    act = SimpleNamespace(domicilio=_dom(calle_normalizada="Actuación 50", numero="50"))
    assert domicilio_texto_historial_fila(act) == "Actuación 50 50"


def test_domicilio_historial_fila_fallback_iniciador(monkeypatch) -> None:
    act = SimpleNamespace(domicilio=None)
    iniciador = object()

    def _fake_build(iniciador_arg):
        assert iniciador_arg is iniciador
        return "Iniciador Normalizado 10"

    monkeypatch.setattr(
        "app.domains.establecimientos.utils.domicilio_display._build_domicilio_texto",
        _fake_build,
    )
    assert domicilio_texto_historial_fila(act, iniciador=iniciador) == "Iniciador Normalizado 10"
