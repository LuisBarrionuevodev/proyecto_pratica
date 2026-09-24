from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.database import db
from app.models import CalleCatalogo
from app.domains.geolocalizacion.normalizacion_calles.repos.domicilio_repo import get_domicilio
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
)


def apply_esquina_canon_to_domicilio(dom: Any, esquina_catalogo_id: int) -> CalleCatalogo:
    """
    Aplica esquina de catálogo sobre un domicilio en sesión (sin commit ni geocode).

    Parámetros:
        dom: instancia ``Domicilio``.
        esquina_catalogo_id: FK a ``calle_catalogo``.

    Retorno:
        Instancia ``CalleCatalogo`` aplicada.

    Errores:
        ValueError: si el id de catálogo no existe.
    """
    calle = CalleCatalogo.query.get(esquina_catalogo_id)
    if not calle:
        raise ValueError("Calle de catálogo no encontrada.")

    dom.esquina_catalogo_id = calle.id
    dom.esquina_normalizada = calle.nombre_canonico
    dom.esquina_norm_status = "OK"
    dom.esquina_norm_score = 1.0
    dom.esquina_norm_error = None
    dom.esquina_norm_updated_at = datetime.utcnow()
    return calle


def set_esquina_canon(domicilio_id: int, esquina_catalogo_id: int) -> Dict[str, object]:
    """
    Setea una esquina canónica en un domicilio y marca normalización OK.
    """
    dom = get_domicilio(domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")

    apply_esquina_canon_to_domicilio(dom, esquina_catalogo_id)

    db.session.add(dom)
    db.session.commit()

    try:
        on_domicilio_changed(dom.id)
    except Exception:
        pass

    return {
        "ok": True,
        "domicilio_id": dom.id,
        "esquina_catalogo_id": dom.esquina_catalogo_id,
        "esquina_normalizada": dom.esquina_normalizada,
        "esquina_estado": dom.esquina_norm_status,
        "esquina_score": dom.esquina_norm_score,
    }
