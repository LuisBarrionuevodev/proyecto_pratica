from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.repos.domicilio_repo import get_domicilio
from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import match_calle
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key
from app.domains.geolocalizacion.normalizacion_calles.services.numero_esquina_detector import (
    detect_numero_o_esquina,
)


def _normalize_calle(dom) -> Dict[str, object]:
    """
    Normaliza la calle principal de un domicilio.
    """
    if dom.calle_raw is None:
        dom.calle_raw = dom.calle

    key = slug_key(dom.calle)
    result = match_calle(dom.calle)

    dom.calle_key = key
    dom.calle_norm_updated_at = datetime.utcnow()

    if result["status"] == "OK":
        dom.calle_normalizada = result["canon"]
        dom.calle_catalogo_id = result["catalogo_id"]
        dom.calle_norm_status = "OK"
        dom.calle_norm_score = result["score"]
        dom.calle_norm_error = None
    elif result["status"] == "REVIEW":
        dom.calle_normalizada = None
        dom.calle_catalogo_id = None
        dom.calle_norm_status = "REVIEW"
        dom.calle_norm_score = result["score"]
        dom.calle_norm_error = "review"
    else:
        dom.calle_normalizada = None
        dom.calle_catalogo_id = None
        dom.calle_norm_status = "NO_MATCH"
        dom.calle_norm_score = result["score"]
        dom.calle_norm_error = "no match"

    return {
        "status": dom.calle_norm_status,
        "score": dom.calle_norm_score,
        "canon": dom.calle_normalizada,
        "error": dom.calle_norm_error,
        "suggestions": result.get("candidates"),
    }


def _clear_esquina_fields(dom) -> None:
    dom.esquina_raw = None
    dom.esquina_catalogo_id = None
    dom.esquina_normalizada = None
    dom.esquina_norm_status = None
    dom.esquina_norm_score = None
    dom.esquina_norm_error = None
    dom.esquina_norm_updated_at = None


def _normalize_esquina(dom, override_numero_tipo: Optional[str] = None) -> Optional[Dict[str, object]]:
    """
    Normaliza esquina si el número es una calle.
    """
    if not dom.numero:
        dom.numero_tipo = None
        _clear_esquina_fields(dom)
        return None

    if override_numero_tipo:
        override = override_numero_tipo.strip().upper()
        if override == "ESQUINA":
            dom.numero_tipo = "ESQUINA"
            numero_tipo = "ESQUINA"
        else:
            dom.numero_tipo = override
            _clear_esquina_fields(dom)
            return None
    else:
        numero_tipo = detect_numero_o_esquina(dom.numero)
        dom.numero_tipo = numero_tipo

    if numero_tipo != "ESQUINA":
        _clear_esquina_fields(dom)
        return None

    dom.esquina_raw = dom.numero
    result = match_calle(dom.esquina_raw)
    dom.esquina_norm_updated_at = datetime.utcnow()

    if result["status"] == "OK":
        dom.esquina_normalizada = result["canon"]
        dom.esquina_catalogo_id = result["catalogo_id"]
        dom.esquina_norm_status = "OK"
        dom.esquina_norm_score = result["score"]
        dom.esquina_norm_error = None
    elif result["status"] == "REVIEW":
        dom.esquina_normalizada = None
        dom.esquina_catalogo_id = None
        dom.esquina_norm_status = "REVIEW"
        dom.esquina_norm_score = result["score"]
        dom.esquina_norm_error = "review"
    else:
        dom.esquina_normalizada = None
        dom.esquina_catalogo_id = None
        dom.esquina_norm_status = "NO_MATCH"
        dom.esquina_norm_score = result["score"]
        dom.esquina_norm_error = "no match"

    return {
        "status": dom.esquina_norm_status,
        "score": dom.esquina_norm_score,
        "canon": dom.esquina_normalizada,
        "error": dom.esquina_norm_error,
        "suggestions": result.get("candidates"),
    }


def _build_result(dom, calle_result, esquina_result) -> Dict[str, object]:
    return {
        "ok": True,
        "status": dom.calle_norm_status,
        "canon": dom.calle_normalizada,
        "score": dom.calle_norm_score,
        "error": dom.calle_norm_error,
        "suggestions": calle_result.get("suggestions") if calle_result else None,
        "calle": calle_result,
        "esquina": esquina_result,
        "numero_tipo": dom.numero_tipo,
        "domicilio_id": dom.id,
    }


def normalizar_domicilio_en_sesion(dom, override_numero_tipo: Optional[str] = None) -> Dict[str, object]:
    """
    Normaliza la calle/esquina de un domicilio usando la sesión actual.

    Qué hace:
    - Ejecuta normalización de calle y esquina.
    - Actualiza campos de normalización en el modelo.
    - Agrega el domicilio a la sesión (sin commit).

    Parámetros:
    - dom: instancia de Domicilio ya cargada en sesión.

    Retorno:
    - Dict con estado de normalización.
    """
    if not dom:
        raise ValueError("Domicilio no encontrado.")
    if not dom.calle:
        raise ValueError("Domicilio sin calle.")

    calle_result = _normalize_calle(dom)
    esquina_result = _normalize_esquina(dom, override_numero_tipo=override_numero_tipo)
    db.session.add(dom)

    return _build_result(dom, calle_result, esquina_result)


def normalizar_domicilio(domicilio_id: int) -> Dict[str, object]:
    """
    Normaliza la calle de un domicilio y persiste resultado.
    """
    dom = get_domicilio(domicilio_id)
    result = normalizar_domicilio_en_sesion(dom)
    db.session.commit()
    return result
