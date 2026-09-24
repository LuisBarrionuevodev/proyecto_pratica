"""
Campos de distrito para listados de gestión (solo lectura, sin resolución espacial).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import and_

from app.models import Domicilio, DomicilioGeocode


def domicilio_geocode_valido_para_distrito(geocode: Optional[DomicilioGeocode]) -> bool:
    """
    True si el geocode del domicilio cumple la regla canónica para mostrar distrito.

    Requiere geo_status OK y coordenadas no nulas.
    """
    if geocode is None:
        return False
    if str(geocode.geo_status or "") != "OK":
        return False
    return geocode.lat is not None and geocode.lng is not None


def domicilio_distrito_gestion_fields(domicilio: Optional[Domicilio]) -> Dict[str, Any]:
    """
    Deriva ``distrito_id``, ``distrito_codigo``, ``distrito_nombre`` y ``distrito_mostrar``.

    ``distrito_mostrar`` solo se completa cuando geo_status es OK, hay lat/lng y
    ``domicilio.distrito_id`` no es nulo. No ejecuta ``resolve_distrito_id``.
    """
    if domicilio is None:
        return {
            "distrito_id": None,
            "distrito_codigo": None,
            "distrito_nombre": None,
            "distrito_mostrar": None,
        }

    distrito = getattr(domicilio, "distrito", None)
    geocode = getattr(domicilio, "geocode", None)
    distrito_id_interno = domicilio.distrito_id

    base: Dict[str, Any] = {
        "distrito_id": distrito_id_interno,
        "distrito_codigo": None,
        "distrito_nombre": None,
        "distrito_mostrar": None,
    }

    if not domicilio_geocode_valido_para_distrito(geocode):
        return base

    if distrito_id_interno is None:
        return base

    distrito_codigo = getattr(distrito, "codigo", None) if distrito else None
    distrito_nombre = getattr(distrito, "nombre", None) if distrito else None
    distrito_mostrar = distrito_nombre
    if not distrito_mostrar and distrito_codigo is not None:
        distrito_mostrar = f"Distrito {distrito_codigo}"

    return {
        "distrito_id": int(distrito_id_interno),
        "distrito_codigo": distrito_codigo,
        "distrito_nombre": distrito_nombre,
        "distrito_mostrar": distrito_mostrar,
    }


def domicilio_distrito_listado_sql_predicates(distrito_id: int):
    """
    Predicados SQL para filtrar por distrito de forma consistente con ``distrito_mostrar``.

    Requiere join previo a ``Domicilio`` y ``DomicilioGeocode``.
    """
    return and_(
        Domicilio.distrito_id == int(distrito_id),
        DomicilioGeocode.geo_status == "OK",
        DomicilioGeocode.lat.isnot(None),
        DomicilioGeocode.lng.isnot(None),
    )
