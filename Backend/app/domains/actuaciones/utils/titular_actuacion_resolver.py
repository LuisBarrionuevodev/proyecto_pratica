"""
Resolución unificada de titular para presenters y búsqueda.

Prioridad:
1. domicilio.contribuyente (actuación operativa normal)
2. snapshot histórico (carga_solo_comprobacion)
3. vacío
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.models import Actuaciones


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def resolve_titular_grid_fields(act: Actuaciones) -> Dict[str, Optional[str]]:
    """
    Devuelve campos de titular para grilla/listados/exports.

    Parámetros:
        act: instancia ORM de actuación.

    Retorno:
        Dict con ``contrib_apellido``, ``contrib_nombre``, ``razon_social``,
        ``doc_nro`` y ``titular_source``.
    """
    dom = getattr(act, "domicilio", None)
    if dom is not None:
        contrib = getattr(dom, "contribuyente", None)
        if contrib is not None:
            doc = getattr(contrib, "documento", None) or getattr(contrib, "doc_nro", None)
            return {
                "contrib_apellido": _clean_str(getattr(contrib, "apellido", None)),
                "contrib_nombre": _clean_str(getattr(contrib, "nombre", None)),
                "razon_social": _clean_str(getattr(contrib, "razon_social", None)),
                "doc_nro": _clean_str(doc),
                "titular_source": "domicilio_contribuyente",
            }

    if bool(getattr(act, "carga_solo_comprobacion", False)):
        return {
            "contrib_apellido": _clean_str(getattr(act, "titular_apellido_historico", None)),
            "contrib_nombre": _clean_str(getattr(act, "titular_nombre_historico", None)),
            "razon_social": _clean_str(getattr(act, "titular_razon_social_historica", None)),
            "doc_nro": None,
            "titular_source": "snapshot_historico",
        }

    return {
        "contrib_apellido": None,
        "contrib_nombre": None,
        "razon_social": None,
        "doc_nro": None,
        "titular_source": None,
    }


def titular_label_from_grid_fields(fields: Dict[str, Optional[str]]) -> Optional[str]:
    """Texto legible de titular a partir del dict del resolver."""
    rs = fields.get("razon_social")
    if rs:
        return rs
    ap = fields.get("contrib_apellido")
    no = fields.get("contrib_nombre")
    parts = [p for p in (ap, no) if p]
    return " ".join(parts).strip() or None
