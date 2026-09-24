from __future__ import annotations

from typing import Dict, Optional

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.repos.domicilio_repo import get_domicilio
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
)


def set_numero_esquina(
    domicilio_id: int, numero: str, numero_tipo: Optional[str] = None
) -> Dict[str, object]:
    """
    Actualiza el número/esquina de un domicilio y re-normaliza.

    Args:
        domicilio_id: id del domicilio.
        numero: valor ingresado (número o calle para esquina).
        numero_tipo: "NUMERO" | "ESQUINA" (opcional).

    Returns:
        Dict con resumen de normalización.
    """
    dom = get_domicilio(domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")
    if not numero:
        raise ValueError("numero es obligatorio.")

    dom.numero = str(numero).strip()
    override = str(numero_tipo).strip().upper() if numero_tipo else None
    result = normalizar_domicilio_en_sesion(dom, override_numero_tipo=override)
    db.session.add(dom)
    db.session.commit()
    try:
        on_domicilio_changed(dom.id)
    except Exception:
        pass
    return {
        "ok": True,
        "domicilio_id": dom.id,
        "numero": dom.numero,
        "numero_tipo": dom.numero_tipo,
        "calle_normalizada": dom.calle_normalizada,
        "calle_catalogo_id": dom.calle_catalogo_id,
        "calle_estado": dom.calle_norm_status,
        "esquina_normalizada": dom.esquina_normalizada,
        "esquina_catalogo_id": dom.esquina_catalogo_id,
        "esquina_status": dom.esquina_norm_status,
        "result": result,
    }
