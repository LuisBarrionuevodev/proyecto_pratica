"""Mapper: payload validado → valores propuestos (sin tocar DB)."""

from __future__ import annotations

from typing import Any

from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
    ContribuyenteCorreccionIn,
    CorreccionEstablecimientoIn,
    DomicilioCorreccionIn,
)
from app.models import Contribuyente, Domicilio


def contribuyente_actual_dict(contrib: Contribuyente | None) -> dict[str, Any] | None:
    """Serializa datos actuales del contribuyente ancla."""
    if contrib is None:
        return None
    return {
        "id": int(contrib.id),
        "documento": contrib.documento,
        "apellido": contrib.apellido,
        "nombre": contrib.nombre,
        "razon_social": contrib.razon_social,
    }


def _coord(v: object) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def domicilio_actual_dict(dom: Domicilio) -> dict[str, Any]:
    """Serializa dirección operativa actual (sin recalcular geo)."""
    geo = getattr(dom, "geocode", None)
    return {
        "id": int(dom.id),
        "calle": dom.calle,
        "numero": dom.numero,
        "numero_tipo": dom.numero_tipo,
        "esquina_raw": getattr(dom, "esquina_raw", None),
        "calle_key": getattr(dom, "calle_key", None),
        "calle_normalizada": getattr(dom, "calle_normalizada", None),
        "distrito_id": dom.distrito_id,
        "barrio_id": dom.barrio_id,
        "lat": _coord(getattr(geo, "lat", None) if geo is not None else None),
        "lng": _coord(getattr(geo, "lng", None) if geo is not None else None),
    }


def proposicion_contribuyente(
    contrib: Contribuyente,
    patch: ContribuyenteCorreccionIn | None,
) -> dict[str, Any]:
    """
    Combina valores actuales con el parche (campos omitidos se conservan).

    Parámetros:
        contrib: contribuyente ancla (mismo id).
        patch: bloque de corrección o None.

    Retorno:
        dict con documento/apellido/nombre/razon_social propuestos.
    """
    base = {
        "documento": contrib.documento,
        "apellido": contrib.apellido,
        "nombre": contrib.nombre,
        "razon_social": contrib.razon_social,
    }
    if patch is None:
        return base
    if patch.documento is not None:
        base["documento"] = patch.documento
    if patch.apellido is not None:
        base["apellido"] = patch.apellido
    if patch.nombre is not None:
        base["nombre"] = patch.nombre
    if patch.razon_social is not None:
        base["razon_social"] = patch.razon_social
    return base


def proposicion_domicilio(
    dom: Domicilio,
    patch: DomicilioCorreccionIn | None,
) -> dict[str, Any]:
    """
    Combina dirección actual con el parche.

    Si ``numero_tipo`` es ESQUINA y viene ``esquina``, se usa como número/intersección.
    """
    base = {
        "calle": dom.calle,
        "numero": dom.numero,
        "numero_tipo": dom.numero_tipo,
        "esquina": getattr(dom, "esquina_raw", None) or (
            dom.numero if (dom.numero_tipo or "").upper() == "ESQUINA" else None
        ),
    }
    if patch is None:
        return base
    if patch.calle is not None:
        base["calle"] = patch.calle
    if patch.numero is not None:
        base["numero"] = patch.numero
    if patch.numero_tipo is not None:
        base["numero_tipo"] = patch.numero_tipo
    if patch.esquina is not None:
        base["esquina"] = patch.esquina
        if (base["numero_tipo"] or "").upper() == "ESQUINA" and patch.numero is None:
            base["numero"] = patch.esquina
    return base


def hay_cambio_contribuyente(actual: dict[str, Any], propuesto: dict[str, Any]) -> bool:
    """True si algún campo de identidad del contribuyente cambia (trim-insensitive)."""
    keys = ("documento", "apellido", "nombre", "razon_social")
    for k in keys:
        a = (str(actual.get(k) or "")).strip()
        b = (str(propuesto.get(k) or "")).strip()
        if a != b:
            return True
    return False


def hay_cambio_domicilio(actual: dict[str, Any], propuesto: dict[str, Any]) -> bool:
    """True si calle/número/tipo cambian."""

    def _n(v: object) -> str:
        return str(v or "").strip()

    if _n(actual.get("calle")) != _n(propuesto.get("calle")):
        return True
    if _n(actual.get("numero")) != _n(propuesto.get("numero")):
        return True
    if _n(actual.get("numero_tipo")).upper() != _n(propuesto.get("numero_tipo")).upper():
        return True
    return False


def payload_tiene_contribuyente(body: CorreccionEstablecimientoIn) -> bool:
    return body.contribuyente is not None


def payload_tiene_domicilio(body: CorreccionEstablecimientoIn) -> bool:
    return body.domicilio is not None
