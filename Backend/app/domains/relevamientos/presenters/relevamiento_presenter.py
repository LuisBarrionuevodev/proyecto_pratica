from __future__ import annotations

from typing import Any, Dict, Optional

from app.models import Relevamiento
from app.utils.iniciador_estado import normalize_estado_iniciador


def relevamiento_to_row(rel: Relevamiento) -> Dict[str, Any]:
    """
    Convierte un Relevamiento a formato plano consumible por la UI.

    Retorna:
    - id
    - fecha (YYYY-MM-DD)
    - inspector (nombre)
    - calle
    - numero
    - rubro (nombre)
    """
    fecha_iso: Optional[str] = rel.fecha.isoformat() if rel.fecha else None
    inspector_nombre = rel.inspector.nombre if rel.inspector else None
    dom = rel.domicilio
    rub = rel.rubro
    calle = getattr(dom, "calle", None)
    calle_raw = getattr(dom, "calle_raw", None)
    numero = getattr(dom, "numero", None)
    calle_normalizada = getattr(dom, "calle_normalizada", None)
    calle_estado = getattr(dom, "calle_norm_status", None)
    calle_score = getattr(dom, "calle_norm_score", None)
    calle_catalogo_id = getattr(dom, "calle_catalogo_id", None)
    numero_tipo = getattr(dom, "numero_tipo", None)
    esquina_raw = getattr(dom, "esquina_raw", None)
    esquina_normalizada = getattr(dom, "esquina_normalizada", None)
    esquina_catalogo_id = getattr(dom, "esquina_catalogo_id", None)
    esquina_status = getattr(dom, "esquina_norm_status", None)
    esquina_score = getattr(dom, "esquina_norm_score", None)
    domicilio_id = getattr(dom, "id", None)

    calle_mostrar = calle_normalizada if calle_estado == "OK" and calle_normalizada else calle
    calle_sugerida = calle_normalizada if calle_normalizada else None
    numero_mostrar = (
        f"ESQ: {esquina_normalizada}"
        if numero_tipo == "ESQUINA" and esquina_status == "OK" and esquina_normalizada
        else numero
    )

    return {
        "id": rel.id,
        "fecha": fecha_iso,
        "inspector": inspector_nombre,
        "calle": calle,
        "calle_raw": calle_raw,
        "calle_cargada": calle_raw or calle,
        "numero": numero,
        "numero_tipo": numero_tipo,
        "numero_esquina": (
            esquina_normalizada or esquina_raw if numero_tipo == "ESQUINA" else None
        ),
        "numero_mostrar": numero_mostrar,
        "esquina_raw": esquina_raw,
        "esquina_normalizada": esquina_normalizada,
        "esquina_catalogo_id": esquina_catalogo_id,
        "esquina_status": esquina_status,
        "esquina_score": esquina_score,
        "domicilio_id": domicilio_id,
        "calle_normalizada": calle_normalizada,
        "calle_estado": calle_estado,
        "calle_score": calle_score,
        "calle_catalogo_id": calle_catalogo_id,
        "calle_sugerida": calle_sugerida,
        "calle_mostrar": calle_mostrar,
        "rubro": getattr(rub, "nombre", None),
        "nombre_fantasia": rel.nombre_fantasia,
        "angulo_esquina": rel.angulo_esquina,
        "turno": rel.turno_carga,
        "esta_abierto": rel.esta_abierto,
    }


def relevamiento_operativo_to_row(rel: Relevamiento, iniciador_id: int, iniciador_estado: object) -> Dict[str, Any]:
    """
    Convierte un Relevamiento de gestión operativa a formato UI.
    """
    data = relevamiento_to_row(rel)
    data["iniciador_ruta_id"] = iniciador_id
    data["iniciador_estado"] = normalize_estado_iniciador(iniciador_estado)
    # Bandeja gestión operativa solo lista iniciadores PENDIENTE; la grilla debe permitir editar siempre.
    data["editable"] = True
    return data


def relevamiento_to_pendiente_domicilio_row(rel: Relevamiento) -> Dict[str, Any]:
    """
    Convierte un Relevamiento a un formato mínimo para pendientes de domicilio.
    """
    fecha_iso: Optional[str] = rel.fecha.isoformat() if rel.fecha else None
    rub = rel.rubro
    dom = rel.domicilio

    calle = getattr(dom, "calle", None)
    numero = getattr(dom, "numero", None)
    calle_normalizada = getattr(dom, "calle_normalizada", None)
    calle_catalogo_id = getattr(dom, "calle_catalogo_id", None)
    numero_tipo = getattr(dom, "numero_tipo", None)
    esquina_normalizada = getattr(dom, "esquina_normalizada", None)
    esquina_catalogo_id = getattr(dom, "esquina_catalogo_id", None)
    esquina_status = getattr(dom, "esquina_norm_status", None)
    domicilio_id = getattr(dom, "id", None)

    return {
        "id": rel.id,
        "fecha": fecha_iso,
        "rubro": getattr(rub, "nombre", None),
        "calle_ingresada": calle,
        "calle": calle,
        "calle_normalizada": calle_normalizada,
        "calle_catalogo_id": calle_catalogo_id,
        "numero": numero,
        "numero_tipo": numero_tipo,
        "esquina_normalizada": esquina_normalizada,
        "esquina_catalogo_id": esquina_catalogo_id,
        "esquina_status": esquina_status,
        "domicilio_id": domicilio_id,
    }
