from __future__ import annotations

import hashlib
from typing import Dict, Optional

from app.database import db
from app.models import Domicilio
from app.domains.geolocalizacion.geocoding.repos.domicilio_geocode_repo import (
    ensure_geocode_row,
)
from app.domains.geolocalizacion.geocoding.services.geocode_service import (
    geocode_domicilio,
)


def compute_addr_hash(dom: Domicilio) -> str:
    """
    Calcula hash SHA1 del address canonical.

    Args:
        dom: Domicilio a evaluar.

    Returns:
        Hash SHA1 en hex.
    """
    raw = "|".join(
        [
            (dom.calle_normalizada or "").strip(),
            (dom.numero or "").strip(),
            (dom.esquina_normalizada or "").strip(),
            (dom.ciudad or "").strip(),
            (dom.provincia or "").strip(),
            (dom.pais or "").strip(),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def is_ready_for_geocode(dom: Domicilio) -> bool:
    """
    Determina si el domicilio está listo para geocodificar.

    Args:
        dom: Domicilio a evaluar.

    Returns:
        True si está listo, False si falta normalización/datos.
    """
    if dom.calle_norm_status != "OK":
        return False
    if dom.numero_tipo == "ESQUINA":
        return dom.esquina_norm_status == "OK" and dom.esquina_catalogo_id is not None
    return bool(dom.numero)


def mark_geocode_pending(domicilio_id: int, addr_hash: str) -> None:
    """
    Marca el geocode como PENDING limpiando resultados previos.

    Args:
        domicilio_id: id del domicilio.
        addr_hash: hash del address canonical.
    """
    geo = ensure_geocode_row(domicilio_id)
    geo.geo_status = "PENDING"
    geo.lat = None
    geo.lng = None
    geo.score = None
    geo.error_msg = None
    geo.raw_json = None
    geo.checked_at = None
    geo.addr_hash = addr_hash
    geo.source = "AUTO"
    db.session.add(geo)


def run_geocode_if_ready(domicilio_id: int) -> Dict[str, object]:
    """
    Ejecuta geocode si el domicilio está listo, si no deja REVIEW.

    Args:
        domicilio_id: id del domicilio.

    Returns:
        Resultado del geocode o status REVIEW.

    Raises:
        ValueError: si el domicilio no existe.
    """
    dom = db.session.get(Domicilio, domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")
    geo = ensure_geocode_row(domicilio_id)
    if not is_ready_for_geocode(dom):
        geo.geo_status = "REVIEW"
        db.session.add(geo)
        db.session.commit()
        return {"ok": False, "geo_status": "REVIEW", "domicilio_id": domicilio_id}
    return geocode_domicilio(domicilio_id)


def on_domicilio_changed(domicilio_id: int, force: bool = False) -> Dict[str, object]:
    """
    Orquestador principal: detecta cambios y re-geocodifica si corresponde.

    Args:
        domicilio_id: id del domicilio.
        force: si True, recalcula aunque el hash no cambie.

    Returns:
        Resultado del geocode o skip reason.

    Raises:
        ValueError: si el domicilio no existe.
    """
    dom = db.session.get(Domicilio, domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")

    geo = ensure_geocode_row(domicilio_id)
    if geo.source in {"MANUAL", "REVERSE"} and not force:
        return {"ok": True, "skipped": True, "reason": "manual_or_reverse", "domicilio_id": domicilio_id}

    new_hash = compute_addr_hash(dom)
    if not force and geo.addr_hash == new_hash:
        return {"ok": True, "skipped": True, "reason": "hash_unchanged", "domicilio_id": domicilio_id}

    mark_geocode_pending(domicilio_id, new_hash)
    db.session.commit()
    return run_geocode_if_ready(domicilio_id)
