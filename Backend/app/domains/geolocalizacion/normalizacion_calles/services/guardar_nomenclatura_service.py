from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.repos.domicilio_repo import get_domicilio
from app.domains.geolocalizacion.normalizacion_calles.schemas.guardar_nomenclatura_in import (
    GuardarNomenclaturaIn,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    clear_esquina_norm_fields,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key
from app.domains.geolocalizacion.normalizacion_calles.services.set_calle_canon_service import (
    apply_calle_canon_to_domicilio,
)
from app.domains.geolocalizacion.normalizacion_calles.services.set_esquina_canon_service import (
    apply_esquina_canon_to_domicilio,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
)


def _apply_calle_manual(dom: Any, calle_texto: str) -> None:
    """
    Persiste calle operativa sin catálogo y sin re-match automático (política manual explícita).

    Estado: ``NO_MATCH``, sin ``OK`` ni ``calle_catalogo_id``.
    """
    dom.calle = calle_texto
    dom.calle_raw = calle_texto
    dom.calle_catalogo_id = None
    dom.calle_normalizada = None
    dom.calle_key = slug_key(calle_texto)
    dom.calle_norm_status = "NO_MATCH"
    dom.calle_norm_score = None
    dom.calle_norm_error = "manual"
    dom.calle_norm_updated_at = datetime.utcnow()


def _apply_esquina_manual(dom: Any) -> None:
    """
    Esquina declarada manual: texto en ``dom.numero``, sin catálogo ni match fuzzy.

    Estado: ``NO_MATCH`` con ``esquina_norm_error == manual``.
    """
    dom.esquina_raw = dom.numero
    dom.esquina_catalogo_id = None
    dom.esquina_normalizada = None
    dom.esquina_norm_status = "NO_MATCH"
    dom.esquina_norm_score = None
    dom.esquina_norm_error = "manual"
    dom.esquina_norm_updated_at = datetime.utcnow()


def guardar_nomenclatura_hibrida(domicilio_id: int, body: GuardarNomenclaturaIn) -> Dict[str, Any]:
    """
    Orquesta guardado de nomenclatura en un solo commit y una sola señal a geocode.

    Orden:
        1. Calle (catálogo o manual, sin re-match en manual).
        2. Número y tipo.
        3. Esquina si ``ESQUINA`` (catálogo o manual sin fuzzy), o limpieza si ``NUMERO``.
        4. commit + ``on_domicilio_changed``.

    Parámetros:
        domicilio_id: id del domicilio.
        body: payload validado (``GuardarNomenclaturaIn``).

    Retorno:
        Dict serializable con resumen de estado.

    Errores:
        ValueError: domicilio inexistente o reglas de negocio.
    """
    dom = get_domicilio(domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")

    # 1. Calle
    if body.calle.mode == "CATALOGO":
        assert body.calle.calle_catalogo_id is not None
        apply_calle_canon_to_domicilio(dom, int(body.calle.calle_catalogo_id))
    else:
        assert body.calle.calle_texto is not None
        _apply_calle_manual(dom, body.calle.calle_texto)

    # 2. Número / tipo
    dom.numero = body.numero
    dom.numero_tipo = body.numero_tipo

    # 3. Esquina
    if body.numero_tipo == "NUMERO":
        clear_esquina_norm_fields(dom)
    else:
        assert body.esquina is not None
        if body.esquina.mode == "CATALOGO":
            assert body.esquina.esquina_catalogo_id is not None
            apply_esquina_canon_to_domicilio(dom, int(body.esquina.esquina_catalogo_id))
        else:
            _apply_esquina_manual(dom)

    db.session.add(dom)
    db.session.commit()

    try:
        on_domicilio_changed(dom.id)
    except Exception:
        pass

    esquina_block: Dict[str, Any] | None = None
    if body.numero_tipo == "ESQUINA" and body.esquina is not None:
        esquina_block = {
            "mode": body.esquina.mode,
            "esquina_catalogo_id": dom.esquina_catalogo_id,
            "esquina_normalizada": dom.esquina_normalizada,
            "esquina_norm_status": dom.esquina_norm_status,
        }

    return {
        "ok": True,
        "domicilio_id": dom.id,
        "calle": {
            "mode": body.calle.mode,
            "calle": dom.calle,
            "calle_catalogo_id": dom.calle_catalogo_id,
            "calle_normalizada": dom.calle_normalizada,
            "calle_norm_status": dom.calle_norm_status,
        },
        "numero": dom.numero,
        "numero_tipo": dom.numero_tipo,
        "esquina": esquina_block,
    }
