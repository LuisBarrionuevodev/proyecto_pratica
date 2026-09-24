"""Listado Establecimientos: domicilio_texto en fila (PR10.4b.6)."""

from __future__ import annotations

from types import SimpleNamespace

from app.domains.establecimientos.presenters.establecimiento_operativo_presenters import (
    establecimiento_operativo_list_row,
)


def _eo_with_dom(dom: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        domicilio_id=10,
        created_at=None,
        updated_at=None,
        domicilio=dom,
    )


def _dom(
    *,
    calle: str | None = None,
    calle_normalizada: str | None = None,
    numero: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        calle=calle,
        calle_raw=calle,
        calle_normalizada=calle_normalizada,
        numero=numero,
        numero_tipo="NUMERO",
        esquina_normalizada=None,
        esquina_raw=None,
        calle_catalogo=None,
        rubro=None,
        distrito=None,
        distrito_id=None,
        contribuyente=None,
    )


def test_list_row_incluye_domicilio_texto_normalizado() -> None:
    eo = _eo_with_dom(
        _dom(
            calle="calle raw relevamiento",
            calle_normalizada="San Martín",
            numero="2869",
        )
    )
    row = establecimiento_operativo_list_row(eo)
    assert row["domicilio_texto"] == "San Martín 2869"
    assert row["calle"] == "calle raw relevamiento"
