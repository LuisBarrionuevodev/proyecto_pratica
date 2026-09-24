"""
Texto de domicilio operativo/normalizado para lectura en Establecimientos (sin geocode).
"""

from __future__ import annotations

from typing import Any

from app.domains.rutas_trabajo.presenters.ruta_presenters import (
    _build_domicilio_texto,
    _build_domicilio_texto_desde_dom,
)
from app.models import Domicilio


def domicilio_texto_visible(dom: Domicilio | None) -> str | None:
    """
    Arma línea de domicilio priorizando catálogo/normalizado sobre calle raw.

    Parámetros:
        dom: instancia ORM con relaciones de domicilio ya cargadas si aplica.

    Retorno:
        Texto listo para UI o None.
    """
    return _build_domicilio_texto_desde_dom(dom)


def domicilio_texto_ficha_detalle(
    dom_ficha: Domicilio | None,
    dom_ultima_actuacion: Domicilio | None = None,
) -> str | None:
    """
    Domicilio visible en card de ficha: actuación más reciente, luego ficha operativa.

    Parámetros:
        dom_ficha: domicilio canónico de la ficha.
        dom_ultima_actuacion: domicilio de la actuación más reciente, si existe.

    Retorno:
        Texto listo para UI o None.
    """
    txt_act = domicilio_texto_visible(dom_ultima_actuacion)
    if txt_act:
        return txt_act
    return domicilio_texto_visible(dom_ficha)


def domicilio_texto_historial_fila(
    act: Any,
    *,
    iniciador: Any = None,
) -> str | None:
    """
    Domicilio visible por fila de historial: actuación final, luego iniciador normalizado.

    Parámetros:
        act: actuación con ``domicilio`` opcionalmente cargado.
        iniciador: iniciador de ruta para fallback sin actuación final.

    Retorno:
        Texto listo para UI o None.
    """
    dom_act = getattr(act, "domicilio", None) if act is not None else None
    txt = domicilio_texto_visible(dom_act)
    if txt:
        return txt
    if iniciador is not None:
        return _build_domicilio_texto(iniciador)
    return None
