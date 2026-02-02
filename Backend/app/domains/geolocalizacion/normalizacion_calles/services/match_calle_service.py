from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from .normalize_string import normalize_street, street_base
from app.domains.geolocalizacion.normalizacion_calles.repos.calle_catalogo_repo import (
    get_by_key,
    get_by_canon_base,
    list_active_keys,
)


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def match_calle(
    nombre_input: str,
    *,
    min_ratio: float = 0.85,
    review_ratio: float = 0.70,
    ok_ratio: float = 0.84,
    ambiguity_delta: float = 0.05,
) -> Dict[str, Any]:
    """
    Resuelve una calle contra el catálogo por etapas:

    1) Normalización:
       - key_full: forma "full" normalizada (incluye prefijos tipo 'calle', 'av', etc según tu normalizador)
       - key_base: forma base para matching difuso (sin prefijos / con limpieza)

    2) Match por canon_base exacto:
       - Si hay 1 coincidencia por canon_base -> OK (score 1.0)
       - Si hay >1 -> REVIEW (ambigüedad)

    3) Match por key_full exacto:
       - Si existe -> OK (score 1.0)

    4) Fuzzy sobre canon_base de catálogo:
       - score >= ok_ratio -> OK directo
       - score >= review_ratio -> REVIEW con sugerencias
       - score >= min_ratio -> OK si NO es ambiguo (gap top1-top2 >= ambiguity_delta), si no REVIEW
       - else -> NO_MATCH con sugerencias

    Retorna:
      {
        "status": "OK" | "REVIEW" | "NO_MATCH",
        "canon": str|None,
        "catalogo_id": int|None,
        "score": float|None,
        "candidates": list|None,
      }
    """
    if not nombre_input or not str(nombre_input).strip():
        return {
            "status": "NO_MATCH",
            "canon": None,
            "catalogo_id": None,
            "score": None,
            "candidates": None,
        }

    key_full = normalize_street(nombre_input)
    key_base = street_base(nombre_input)

    # -------------------------
    # 1) Match por canon_base exacto
    # -------------------------
    if key_base:
        base_matches = get_by_canon_base(key_base)  # lista de rows con mismo canon_base
        if len(base_matches) == 1:
            exact = base_matches[0]
            return {
                "status": "OK",
                "canon": exact.nombre_canonico,
                "catalogo_id": exact.id,
                "score": 1.0,
                "candidates": None,
            }

        if len(base_matches) > 1:
            # Ambigüedad: varias calles comparten base (ej: "araoz" puede ser avenida/calle/pasaje...)
            return {
                "status": "REVIEW",
                "canon": None,
                "catalogo_id": None,
                "score": 0.55,
                "candidates": [
                    {
                        "calle_id": c.id,
                        "display": c.nombre_canonico,
                        "canon_base": c.canon_base,
                        "score": 0.55,
                    }
                    for c in base_matches[:5]
                ],
            }

    # -------------------------
    # 2) Match exacto por key_full
    # -------------------------
    exact_full = get_by_key(key_full)
    if exact_full:
        return {
            "status": "OK",
            "canon": exact_full.nombre_canonico,
            "catalogo_id": exact_full.id,
            "score": 1.0,
            "candidates": None,
        }

    # -------------------------
    # 3) Fuzzy contra todo el catálogo activo (usando canon_base)
    # -------------------------
    if not key_base:
        # Si no pudimos sacar base, no tiene sentido fuzzy por base
        return {
            "status": "NO_MATCH",
            "canon": None,
            "catalogo_id": None,
            "score": None,
            "candidates": None,
        }

    active = list_active_keys()
    scored: List[Tuple[int, str, str, float]] = []
    for cid, cbase, _ckey, ccanon in active:
        if not cbase:
            continue
        ratio = _score(key_base, cbase)
        scored.append((cid, cbase, ccanon, ratio))

    if not scored:
        return {
            "status": "NO_MATCH",
            "canon": None,
            "catalogo_id": None,
            "score": None,
            "candidates": None,
        }

    scored.sort(key=lambda x: x[3], reverse=True)
    top = scored[:5]

    top1 = top[0]
    best_score = top1[3]

    suggestions = [
        {
            "calle_id": t[0],
            "display": t[2],
            "canon_base": t[1],
            "score": t[3],
        }
        for t in top
    ]

    # Helper: medir ambigüedad (si el 2do está muy cerca del 1ro)
    second_score = top[1][3] if len(top) > 1 else 0.0
    is_ambiguous = (best_score - second_score) < ambiguity_delta

    # -------------------------
    # Decisión final
    # -------------------------
    if best_score >= ok_ratio:
        return {
            "status": "OK",
            "canon": top1[2],
            "catalogo_id": top1[0],
            "score": best_score,
            "candidates": None,
        }

    if best_score >= review_ratio:
        return {
            "status": "REVIEW",
            "canon": None,
            "catalogo_id": None,
            "score": best_score,
            "candidates": suggestions,
        }

    # ✅ Tu pedido: aceptar 0.67 como "no es malo"
    if best_score >= min_ratio:
        if is_ambiguous:
            # si está “empatado” con otra calle, forzamos revisión
            return {
                "status": "REVIEW",
                "canon": None,
                "catalogo_id": None,
                "score": best_score,
                "candidates": suggestions,
            }

        # si no es ambiguo, OK directo aunque sea score medio
        return {
            "status": "OK",
            "canon": top1[2],
            "catalogo_id": top1[0],
            "score": best_score,
            "candidates": None,
        }

    return {
        "status": "NO_MATCH",
        "canon": None,
        "catalogo_id": None,
        "score": best_score,
        "candidates": suggestions,
    }

