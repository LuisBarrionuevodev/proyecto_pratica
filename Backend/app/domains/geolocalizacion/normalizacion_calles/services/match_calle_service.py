from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple

from app.domains.geolocalizacion.normalizacion_calles.repos.calle_catalogo_repo import (
    get_by_canon_base,
    get_by_key,
    get_by_nombre_canonico,
    list_active_keys,
)
from app.domains.geolocalizacion.normalizacion_calles.services.calle_alias_service import (
    resolve_calle_alias,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import (
    normalize_street,
    significant_tokens,
    slug_key,
    street_base,
)

# Umbrales PR4 (conservadores; casos fuertes resueltos por alias/key exacto).
OK_THRESHOLD = 0.92
REVIEW_THRESHOLD = 0.78
AMBIGUITY_DELTA = 0.05


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _token_overlap_score(key_base: str, canon_base: str) -> float:
    """
    Boost cuando todos los tokens significativos del input están en el catálogo.

    Ej.: ``mate luna`` ⊆ ``fernando mate de luna``.
    """
    ta = set(significant_tokens(key_base))
    tb = set(significant_tokens(canon_base))
    if not ta:
        return 0.0
    if ta <= tb:
        coverage = len(ta) / max(len(tb), 1)
        return min(0.98, 0.88 + 0.10 * coverage)
    inter = ta & tb
    if not inter:
        return 0.0
    return (len(inter) / len(ta)) * 0.80


def _combined_score(key_base: str, canon_base: str) -> float:
    if not key_base or not canon_base:
        return 0.0
    if key_base == canon_base:
        return 1.0
    ratio = _ratio(key_base, canon_base)
    overlap = _token_overlap_score(key_base, canon_base)
    substring_boost = 0.0
    if len(key_base) >= 4 and (key_base in canon_base or canon_base in key_base):
        substring_boost = 0.90
    return max(ratio, overlap, substring_boost)


def _ok_result(catalogo_id: int, canon: str, score: float) -> Dict[str, Any]:
    return {
        "status": "OK",
        "canon": canon,
        "catalogo_id": catalogo_id,
        "score": score,
        "candidates": None,
    }


def _review_result(score: float, candidates: List[dict]) -> Dict[str, Any]:
    return {
        "status": "REVIEW",
        "canon": None,
        "catalogo_id": None,
        "score": score,
        "candidates": candidates,
    }


def _no_match_result(score: float | None, candidates: List[dict] | None) -> Dict[str, Any]:
    return {
        "status": "NO_MATCH",
        "canon": None,
        "catalogo_id": None,
        "score": score,
        "candidates": candidates,
    }


def _match_alias(nombre_input: str) -> Dict[str, Any] | None:
    canon_name = resolve_calle_alias(nombre_input)
    if not canon_name:
        return None
    row = get_by_nombre_canonico(canon_name) or get_by_key(slug_key(canon_name))
    if row is None:
        return None
    return _ok_result(int(row.id), row.nombre_canonico, 1.0)


def match_calle(
    nombre_input: str,
    *,
    ok_threshold: float = OK_THRESHOLD,
    review_threshold: float = REVIEW_THRESHOLD,
    ambiguity_delta: float = AMBIGUITY_DELTA,
) -> Dict[str, Any]:
    """
    Resuelve una calle contra el catálogo por etapas (PR4):

    1. Alias CSV (score 1.0 → OK).
    2. ``nombre_key`` exacto.
    3. ``canon_base`` exacto (1 → OK, >1 → REVIEW).
    4. Fuzzy + token overlap con umbrales:
       - ≥ ok_threshold y sin empate → OK
       - ≥ review_threshold → REVIEW
       - else → NO_MATCH

    Parámetros:
        nombre_input: texto de calle ingresado.
        ok_threshold: mínimo para OK automático (default 0.92).
        review_threshold: mínimo para REVIEW con sugerencias (default 0.78).
        ambiguity_delta: gap mínimo top1-top2 para OK fuzzy.

    Retorno:
        Dict con ``status``, ``canon``, ``catalogo_id``, ``score``, ``candidates``.
    """
    if not nombre_input or not str(nombre_input).strip():
        return _no_match_result(None, None)

    alias_hit = _match_alias(nombre_input)
    if alias_hit is not None:
        return alias_hit

    key_full = slug_key(nombre_input)
    key_base = street_base(nombre_input)

    exact_full = get_by_key(key_full)
    if exact_full:
        return _ok_result(int(exact_full.id), exact_full.nombre_canonico, 1.0)

    if key_base:
        base_matches = get_by_canon_base(key_base)
        if len(base_matches) == 1:
            row = base_matches[0]
            return _ok_result(int(row.id), row.nombre_canonico, 1.0)
        if len(base_matches) > 1:
            cands = [
                {
                    "calle_id": c.id,
                    "display": c.nombre_canonico,
                    "canon_base": c.canon_base,
                    "score": 0.55,
                }
                for c in base_matches[:5]
            ]
            return _review_result(0.55, cands)

    if not key_base:
        return _no_match_result(None, None)

    active = list_active_keys()
    scored: List[Tuple[int, str, str, float]] = []
    for cid, cbase, _ckey, ccanon in active:
        if not cbase:
            continue
        score = _combined_score(key_base, cbase)
        if score >= review_threshold - 0.05:
            scored.append((cid, cbase, ccanon, score))

    if not scored:
        return _no_match_result(None, None)

    scored.sort(key=lambda x: x[3], reverse=True)
    top = scored[:5]
    best = top[0]
    best_score = best[3]
    second_score = top[1][3] if len(top) > 1 else 0.0
    is_ambiguous = (best_score - second_score) < ambiguity_delta

    suggestions = [
        {
            "calle_id": t[0],
            "display": t[2],
            "canon_base": t[1],
            "score": t[3],
        }
        for t in top
    ]

    if best_score >= ok_threshold and not is_ambiguous:
        return _ok_result(best[0], best[2], best_score)

    if best_score >= review_threshold or is_ambiguous:
        return _review_result(best_score, suggestions)

    return _no_match_result(best_score, suggestions)
