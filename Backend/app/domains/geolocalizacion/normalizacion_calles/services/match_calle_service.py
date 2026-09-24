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
    matching_token_set,
    significant_tokens,
    slug_key,
    street_base,
)

# Umbrales fuzzy (PR4); estrategias estructuradas pueden OK con score menor.
OK_THRESHOLD = 0.92
REVIEW_THRESHOLD = 0.78
AMBIGUITY_DELTA = 0.05

TOKEN_EXACT_SCORE = 0.97
TOKEN_CONTAINMENT_OK_SCORE = 0.88
TOKEN_CONTAINMENT_REVIEW_SCORE = 0.72


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


def _result(
    *,
    status: str,
    canon: str | None,
    catalogo_id: int | None,
    score: float | None,
    candidates: List[dict] | None,
    match_strategy: str | None = None,
    confidence_reason: str | None = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "canon": canon,
        "catalogo_id": catalogo_id,
        "score": score,
        "candidates": candidates,
        "match_strategy": match_strategy,
        "confidence_reason": confidence_reason,
    }


def _ok_result(
    catalogo_id: int,
    canon: str,
    score: float,
    *,
    match_strategy: str,
    confidence_reason: str,
) -> Dict[str, Any]:
    return _result(
        status="OK",
        canon=canon,
        catalogo_id=catalogo_id,
        score=score,
        candidates=None,
        match_strategy=match_strategy,
        confidence_reason=confidence_reason,
    )


def _review_result(
    score: float,
    candidates: List[dict],
    *,
    match_strategy: str = "fuzzy",
    confidence_reason: str = "Coincidencia ambigua",
) -> Dict[str, Any]:
    return _result(
        status="REVIEW",
        canon=None,
        catalogo_id=None,
        score=score,
        candidates=candidates,
        match_strategy=match_strategy,
        confidence_reason=confidence_reason,
    )


def _no_match_result(
    score: float | None,
    candidates: List[dict] | None,
    *,
    match_strategy: str | None = None,
    confidence_reason: str = "Fuzzy bajo",
) -> Dict[str, Any]:
    return _result(
        status="NO_MATCH",
        canon=None,
        catalogo_id=None,
        score=score,
        candidates=candidates,
        match_strategy=match_strategy,
        confidence_reason=confidence_reason,
    )


def _candidate_row(cid: int, cbase: str, ccanon: str, score: float) -> dict:
    return {
        "calle_id": cid,
        "display": ccanon,
        "canon_base": cbase,
        "score": round(float(score), 4),
    }


def _match_alias(nombre_input: str) -> Dict[str, Any] | None:
    """Alias CSV validado → fila existente en ``calle_catalogo``."""
    canon_name = resolve_calle_alias(nombre_input)
    if not canon_name:
        return None
    row = get_by_nombre_canonico(canon_name)
    if row is None:
        return None
    return _ok_result(
        int(row.id),
        row.nombre_canonico,
        1.0,
        match_strategy="alias",
        confidence_reason="Alias validado contra calle_catalogo",
    )


def _find_exact_token_matches(
    active: List[Tuple[int, str, str, str]],
    input_tokens: frozenset[str],
) -> List[Tuple[int, str, str]]:
    """Calles cuyo conjunto de tokens significativos coincide exactamente."""
    if not input_tokens:
        return []
    matches: List[Tuple[int, str, str]] = []
    for cid, cbase, _ckey, ccanon in active:
        if not cbase:
            continue
        if matching_token_set(cbase) == input_tokens:
            matches.append((cid, cbase, ccanon))
    return matches


def _find_token_containment_matches(
    active: List[Tuple[int, str, str, str]],
    input_tokens: frozenset[str],
) -> List[Tuple[int, str, str, float]]:
    """
    Calles donde todos los tokens del input están contenidos en el catálogo.

    Retorno:
        Lista ``(id, canon_base, nombre_canonico, coverage)``.
    """
    if not input_tokens:
        return []
    matches: List[Tuple[int, str, str, float]] = []
    for cid, cbase, _ckey, ccanon in active:
        if not cbase:
            continue
        cat_tokens = matching_token_set(cbase)
        if not cat_tokens or not input_tokens <= cat_tokens:
            continue
        coverage = len(input_tokens) / len(cat_tokens)
        matches.append((cid, cbase, ccanon, coverage))
    matches.sort(key=lambda x: (-x[3], x[2]))
    return matches


def match_calle(
    nombre_input: str,
    *,
    ok_threshold: float = OK_THRESHOLD,
    review_threshold: float = REVIEW_THRESHOLD,
    ambiguity_delta: float = AMBIGUITY_DELTA,
) -> Dict[str, Any]:
    """
    Resuelve una calle contra ``calle_catalogo`` (PR6A):

    1. Normalizar texto cargado.
    2. Exacto por ``nombre_canonico``.
    3. Exacto por ``nombre_key`` / ``canon_base``.
    4. Exacto por conjunto de tokens significativos.
    5. Alias CSV validado.
    6. Contención fuerte de tokens (única → OK; varias → REVIEW).
    7. Fuzzy general.

    Retorno incluye ``match_strategy`` y ``confidence_reason`` opcionales.
    """
    if not nombre_input or not str(nombre_input).strip():
        return _no_match_result(None, None, confidence_reason="Entrada vacía")

    raw = str(nombre_input).strip()
    key_full = slug_key(raw)
    key_base = street_base(raw)
    input_tokens = matching_token_set(raw)
    active = list_active_keys()

    exact_canon = get_by_nombre_canonico(raw)
    if exact_canon:
        return _ok_result(
            int(exact_canon.id),
            exact_canon.nombre_canonico,
            1.0,
            match_strategy="exact_nombre",
            confidence_reason="Coincidencia exacta por nombre canónico",
        )

    exact_full = get_by_key(key_full)
    if exact_full:
        return _ok_result(
            int(exact_full.id),
            exact_full.nombre_canonico,
            1.0,
            match_strategy="exact_key",
            confidence_reason="Coincidencia exacta por nombre_key",
        )

    if key_base:
        base_matches = get_by_canon_base(key_base)
        if len(base_matches) == 1:
            row = base_matches[0]
            return _ok_result(
                int(row.id),
                row.nombre_canonico,
                1.0,
                match_strategy="exact_key",
                confidence_reason="Coincidencia exacta por canon_base",
            )
        if len(base_matches) > 1:
            cands = [_candidate_row(c.id, c.canon_base, c.nombre_canonico, 0.55) for c in base_matches[:5]]
            return _review_result(
                0.55,
                cands,
                match_strategy="exact_key",
                confidence_reason="Coincidencia ambigua",
            )

    token_exact = _find_exact_token_matches(active, input_tokens)
    if len(token_exact) == 1:
        cid, cbase, ccanon = token_exact[0]
        return _ok_result(
            cid,
            ccanon,
            TOKEN_EXACT_SCORE,
            match_strategy="exact_tokens",
            confidence_reason="Coincidencia exacta por tokens",
        )
    if len(token_exact) > 1:
        cands = [_candidate_row(cid, cbase, ccanon, TOKEN_EXACT_SCORE) for cid, cbase, ccanon in token_exact[:5]]
        return _review_result(
            TOKEN_EXACT_SCORE,
            cands,
            match_strategy="exact_tokens",
            confidence_reason="Coincidencia ambigua",
        )

    alias_hit = _match_alias(raw)
    if alias_hit is not None:
        return alias_hit

    containment = _find_token_containment_matches(active, input_tokens)
    if len(containment) == 1:
        cid, cbase, ccanon, coverage = containment[0]
        score = max(TOKEN_CONTAINMENT_OK_SCORE, round(0.80 + 0.15 * coverage, 4))
        return _ok_result(
            cid,
            ccanon,
            score,
            match_strategy="token_containment",
            confidence_reason="Coincidencia por contención de tokens",
        )
    if len(containment) > 1:
        cands = [
            _candidate_row(cid, cbase, ccanon, max(TOKEN_CONTAINMENT_REVIEW_SCORE, 0.70 + 0.20 * cov))
            for cid, cbase, ccanon, cov in containment[:5]
        ]
        return _review_result(
            cands[0]["score"],
            cands,
            match_strategy="token_containment",
            confidence_reason="Coincidencia ambigua",
        )

    if not key_base:
        return _no_match_result(None, None, confidence_reason="Sin base normalizada")

    scored: List[Tuple[int, str, str, float]] = []
    for cid, cbase, _ckey, ccanon in active:
        if not cbase:
            continue
        score = _combined_score(key_base, cbase)
        if score >= review_threshold - 0.05:
            scored.append((cid, cbase, ccanon, score))

    if not scored:
        return _no_match_result(None, None, match_strategy="fuzzy", confidence_reason="Fuzzy bajo")

    scored.sort(key=lambda x: x[3], reverse=True)
    top = scored[:5]
    best = top[0]
    best_score = best[3]
    second_score = top[1][3] if len(top) > 1 else 0.0
    is_ambiguous = (best_score - second_score) < ambiguity_delta

    suggestions = [_candidate_row(t[0], t[1], t[2], t[3]) for t in top]

    if best_score >= ok_threshold and not is_ambiguous:
        return _ok_result(
            best[0],
            best[2],
            best_score,
            match_strategy="fuzzy",
            confidence_reason="Coincidencia fuzzy alta",
        )

    if best_score >= review_threshold or is_ambiguous:
        reason = "Coincidencia ambigua" if is_ambiguous else "Coincidencia fuzzy media"
        return _review_result(
            best_score,
            suggestions,
            match_strategy="fuzzy",
            confidence_reason=reason,
        )

    return _no_match_result(
        best_score,
        suggestions,
        match_strategy="fuzzy",
        confidence_reason="Fuzzy bajo",
    )
