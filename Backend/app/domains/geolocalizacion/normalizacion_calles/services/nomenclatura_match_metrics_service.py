"""
Métricas de diagnóstico para matching de nomenclatura local (PR4).

Uso: scripts, tests o endpoints admin/dev. No modifica persistencia.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import (
    match_calle,
)


def analyze_street_match_samples(inputs: list[str]) -> dict[str, Any]:
    """
    Evalúa una lista de textos de calle y resume OK / REVIEW / NO_MATCH.

    Parámetros:
        inputs: textos ``calle_raw`` o similares.

    Retorno:
        Conteos, tasa de éxito, detalle por fila, top no matcheadas y sugerencias.
    """
    details: list[dict[str, Any]] = []
    status_counter: Counter[str] = Counter()

    for raw in inputs:
        text = (raw or "").strip()
        if not text:
            continue
        result = match_calle(text)
        status = str(result.get("status") or "NO_MATCH")
        status_counter[status] += 1
        details.append(
            {
                "input": text,
                "status": status,
                "canon": result.get("canon"),
                "catalogo_id": result.get("catalogo_id"),
                "score": result.get("score"),
                "candidates": result.get("candidates"),
            }
        )

    total = sum(status_counter.values())
    ok = status_counter.get("OK", 0)
    return {
        "total": total,
        "ok": ok,
        "review": status_counter.get("REVIEW", 0),
        "no_match": status_counter.get("NO_MATCH", 0),
        "success_rate": round(ok / total, 4) if total else 0.0,
        "auto_ok_rate": round(ok / total, 4) if total else 0.0,
        "details": details,
        "top_no_match": [d["input"] for d in details if d["status"] == "NO_MATCH"][:20],
        "top_review": [d["input"] for d in details if d["status"] == "REVIEW"][:20],
    }


def estimate_improvement_vs_thresholds(
    inputs: list[str],
    *,
    legacy_ok: float = 0.84,
    legacy_review: float = 0.70,
) -> dict[str, Any]:
    """
    Compara conteos actuales vs umbrales legacy (pre-PR4) sobre la misma muestra.

    Parámetros:
        inputs: textos de calle.
        legacy_ok: umbral OK anterior en fuzzy.
        legacy_review: umbral REVIEW anterior.

    Retorno:
        Dict con conteos ``current`` y simulación ``legacy_fuzzy_only``.
    """
    current = analyze_street_match_samples(inputs)

    legacy_ok_count = 0
    legacy_review_count = 0
    legacy_no_match = 0
    for raw in inputs:
        text = (raw or "").strip()
        if not text:
            continue
        r = match_calle(text)
        score = r.get("score")
        if r["status"] == "OK" and (score is None or float(score) >= legacy_ok or score == 1.0):
            legacy_ok_count += 1
        elif r["status"] == "REVIEW" or (
            isinstance(score, (int, float)) and legacy_review <= float(score) < legacy_ok
        ):
            legacy_review_count += 1
        else:
            legacy_no_match += 1

    total = current["total"]
    return {
        "sample_size": total,
        "current": {
            "ok": current["ok"],
            "review": current["review"],
            "no_match": current["no_match"],
            "success_rate": current["success_rate"],
        },
        "legacy_simulated": {
            "ok": legacy_ok_count,
            "review": legacy_review_count,
            "no_match": legacy_no_match,
            "success_rate": round(legacy_ok_count / total, 4) if total else 0.0,
        },
        "delta_ok": current["ok"] - legacy_ok_count,
    }
