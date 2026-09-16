from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domains.domicilios.utils.domicilio_distrito_display import domicilio_distrito_gestion_fields
from app.models import Relevamiento
from app.utils.iniciador_estado import normalize_estado_iniciador


def _relevadores_dto(rel: Relevamiento) -> List[Dict[str, Any]]:
    rows = sorted(rel.relevadores or [], key=lambda r: (r.nombre or "").lower())
    return [{"id": int(r.id), "nombre": r.nombre} for r in rows]


def _relevadores_label(dtos: List[Dict[str, Any]], rel: Relevamiento) -> Optional[str]:
    if dtos:
        return " · ".join(d["nombre"] for d in dtos)
    if rel.inspector and rel.inspector.nombre:
        return rel.inspector.nombre
    return None


def relevamiento_to_row(rel: Relevamiento) -> Dict[str, Any]:
    """
    Convierte un Relevamiento a formato plano consumible por la UI.

    Retorna:
    - id
    - fecha (YYYY-MM-DD)
    - relevadores [{id, nombre}]
    - relevadores_label (texto plano)
    - calle, numero, rubro, etc.
    """
    fecha_iso: Optional[str] = rel.fecha.isoformat() if rel.fecha else None
    relevadores = _relevadores_dto(rel)
    relevadores_label = _relevadores_label(relevadores, rel)
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

    distrito_fields = domicilio_distrito_gestion_fields(dom)

    return {
        "id": rel.id,
        "fecha": fecha_iso,
        "relevadores": relevadores,
        "relevadores_label": relevadores_label,
        "relevador_ids": [d["id"] for d in relevadores],
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
        **distrito_fields,
    }


def relevamiento_operativo_to_row(rel: Relevamiento, iniciador_id: int, iniciador_estado: object) -> Dict[str, Any]:
    """
    Convierte un Relevamiento de gestión operativa a formato UI.
    """
    data = relevamiento_to_row(rel)
    data["iniciador_ruta_id"] = iniciador_id
    data["iniciador_estado"] = normalize_estado_iniciador(iniciador_estado)
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

