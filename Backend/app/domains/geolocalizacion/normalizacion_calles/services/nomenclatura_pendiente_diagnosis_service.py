"""
Diagnóstico de nomenclatura pendiente sobre domicilios reales (PR5/PR5b).

Solo lectura salvo ``append_suggested_aliases_to_csv`` explícito.
Fuente oficial: ``calle_catalogo`` en DB. CSV alias solo como apoyo validado.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import func

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.repos.calle_catalogo_repo import (
    get_by_nombre_canonico,
)
from app.domains.geolocalizacion.normalizacion_calles.services.calle_alias_service import (
    audit_calle_aliases,
    reload_calle_aliases_cache,
    resolve_calle_alias,
)
from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import (
    match_calle,
)
from app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_match_metrics_service import (
    analyze_street_match_samples,
)
from app.models import Domicilio

_ALIASES_CSV = (
    Path(__file__).resolve().parents[1] / "data" / "calle_aliases.csv"
)

# Prefijos de calles usadas en tests/fixtures (PR5c). Orden: más específicos primero.
_SYNTHETIC_PREFIXES: tuple[str, ...] = (
    "PresenterPlazo",
    "HotfixNot",
    "CalleProrroga",
    "CalleMotor",
    "CalleSlice",
    "ReencCalle",
    "Presenter",
    "EditPlazo",
    "EditPerm",
    "CSoloEnv",
    "Reactiva",
    "TestCalle",
    "CReinB",
    "ActNew",
    "ActOld",
    "DenPR",
    "RelGeo",
    "Hotfix",
    "Fake",
    "Slice",
    "Stab",
    "St4",
    "Calle Test",
)

# Prefijos cortos: solo sintético si el sufijo parece fixture (dígito, _ o -).
_SYNTHETIC_SHORT_PREFIX = re.compile(
    r"^(?:CEd|UGA|UGB)(?:[\d_\-]|$)",
    re.IGNORECASE,
)

_SYNTHETIC_PR_PREFIX = re.compile(r"^PR\d", re.IGNORECASE)
_SYNTHETIC_PR_TOKEN = re.compile(r"^PR\d+[A-Za-z]+\d+$", re.IGNORECASE)

_SYNTHETIC_LITERALS = frozenset({"calle test", "test calle"})


def is_synthetic_calle_text(text: str) -> bool:
    """
    Heurística para separar calles de tests/fixtures de datos operativos.

    Solo usada en diagnóstico PR5; no afecta ``match_calle`` productivo.

    Parámetros:
        text: valor de ``domicilio.calle``.

    Retorno:
        True si parece dato sintético de pruebas.
    """
    t = (text or "").strip()
    if not t:
        return False
    lower = t.lower()
    if lower in _SYNTHETIC_LITERALS:
        return True
    for prefix in _SYNTHETIC_PREFIXES:
        if lower.startswith(prefix.lower()):
            return True
    if _SYNTHETIC_SHORT_PREFIX.match(t):
        return True
    if _SYNTHETIC_PR_PREFIX.match(t):
        return True
    if _SYNTHETIC_PR_TOKEN.match(t):
        return True
    return False


def count_domicilios_nomenclatura_pendiente() -> dict[str, int]:
    """
    Cuenta domicilios activos por ``calle_norm_status`` no OK.

    Retorno:
        Totales por estado y pendientes agregados.
    """
    rows = (
        db.session.query(Domicilio.calle_norm_status, func.count(Domicilio.id))
        .filter(Domicilio.deleted_at.is_(None))
        .group_by(Domicilio.calle_norm_status)
        .all()
    )
    by_status = {str(s or "NULL"): int(c) for s, c in rows}
    pendiente = sum(c for s, c in by_status.items() if s != "OK")
    return {"by_status": by_status, "pendiente_total": pendiente}


def fetch_pendiente_calle_frecuencias(*, limit: int = 500) -> list[dict[str, Any]]:
    """
    Agrupa textos de calle en domicilios con nomenclatura no OK.

    Parámetros:
        limit: máximo de grupos distintos por frecuencia.

    Retorno:
        Lista ``{text, count, statuses, sample_domicilio_id, is_synthetic}``.
    """
    base = (
        db.session.query(
            Domicilio.calle,
            Domicilio.calle_norm_status,
            func.count(Domicilio.id).label("cnt"),
            func.min(Domicilio.id).label("sample_id"),
        )
        .filter(
            Domicilio.deleted_at.is_(None),
            Domicilio.calle.isnot(None),
            Domicilio.calle != "",
            Domicilio.calle_norm_status != "OK",
        )
        .group_by(Domicilio.calle, Domicilio.calle_norm_status)
    )
    partial: dict[str, dict[str, Any]] = {}
    for calle, status, cnt, sample_id in base.all():
        text = (calle or "").strip()
        if not text:
            continue
        slot = partial.setdefault(
            text,
            {
                "text": text,
                "count": 0,
                "statuses": Counter(),
                "sample_domicilio_id": int(sample_id),
                "is_synthetic": is_synthetic_calle_text(text),
            },
        )
        slot["count"] += int(cnt)
        slot["statuses"][str(status or "NULL")] += int(cnt)

    ranked = sorted(partial.values(), key=lambda x: x["count"], reverse=True)
    for item in ranked:
        item["statuses"] = dict(item["statuses"])
    return ranked[: max(1, int(limit))]


def simulate_rematch_for_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Simula ``match_calle`` sobre textos frecuentes (sin persistir).

    Parámetros:
        samples: salida de ``fetch_pendiente_calle_frecuencias``.

    Retorno:
        Conteos simulados, detalle y domicilios que pasarían a OK.
    """
    simulated_status: Counter[str] = Counter()
    stored_status: Counter[str] = Counter()
    would_ok_domicilios = 0
    details: list[dict[str, Any]] = []

    for row in samples:
        text = row["text"]
        count = int(row["count"])
        result = match_calle(text)
        sim_status = str(result.get("status") or "NO_MATCH")
        simulated_status[sim_status] += count
        for st, n in row.get("statuses", {}).items():
            stored_status[st] += int(n)
        if sim_status == "OK":
            would_ok_domicilios += count
        top_candidate = None
        cands = result.get("candidates") or []
        if cands:
            top_candidate = cands[0]
        details.append(
            {
                "text": text,
                "count": count,
                "is_synthetic": bool(row.get("is_synthetic")),
                "stored_statuses": row.get("statuses"),
                "simulated_status": sim_status,
                "simulated_canon": result.get("canon"),
                "simulated_score": result.get("score"),
                "top_candidate": top_candidate,
            }
        )

    total = sum(int(r["count"]) for r in samples)
    return {
        "sample_groups": len(samples),
        "domicilios_in_sample": total,
        "stored_status_breakdown": dict(stored_status),
        "simulated_status_breakdown": dict(simulated_status),
        "would_become_ok_domicilios": would_ok_domicilios,
        "simulated_ok_rate": round(would_ok_domicilios / total, 4) if total else 0.0,
        "details": details,
    }


def _split_simulation_by_origin(simulation: dict[str, Any]) -> dict[str, Any]:
    """Separa conteos simulados entre calles reales y sintéticas."""
    real_groups = 0
    synthetic_groups = 0
    real_domicilios = 0
    synthetic_domicilios = 0
    real_would_ok = 0
    real_status: Counter[str] = Counter()

    for row in simulation.get("details") or []:
        count = int(row.get("count") or 0)
        if row.get("is_synthetic"):
            synthetic_groups += 1
            synthetic_domicilios += count
        else:
            real_groups += 1
            real_domicilios += count
            st = str(row.get("simulated_status") or "NO_MATCH")
            real_status[st] += count
            if st == "OK":
                real_would_ok += count

    return {
        "real_groups": real_groups,
        "synthetic_groups": synthetic_groups,
        "real_domicilios": real_domicilios,
        "synthetic_domicilios": synthetic_domicilios,
        "real_would_become_ok": real_would_ok,
        "real_simulated_ok_rate": round(real_would_ok / real_domicilios, 4)
        if real_domicilios
        else 0.0,
        "real_simulated_status_breakdown": dict(real_status),
    }


def suggest_aliases_from_simulation(
    simulation: dict[str, Any],
    *,
    min_count: int = 2,
    min_score: float = 0.78,
    max_suggestions: int = 30,
    real_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Propone filas para ``calle_aliases.csv`` desde NO_MATCH/REVIEW con candidato fuerte.

    Solo sugiere alias cuyo ``nombre_canonico`` exista en ``calle_catalogo``.

    Parámetros:
        simulation: salida de ``simulate_rematch_for_samples``.
        min_count: frecuencia mínima del texto crudo.
        min_score: score mínimo del candidato top.
        max_suggestions: tope de sugerencias.
        real_only: excluir textos sintéticos de tests.

    Retorno:
        Lista ``{alias, nombre_canonico, count, score, notas}``.
    """
    out: list[dict[str, Any]] = []
    seen_alias: set[str] = set()

    for row in simulation.get("details") or []:
        if row.get("simulated_status") == "OK":
            continue
        if real_only and row.get("is_synthetic"):
            continue
        count = int(row.get("count") or 0)
        if count < min_count:
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        if resolve_calle_alias(text):
            continue

        cand = row.get("top_candidate")
        if not cand:
            continue
        score = cand.get("score")
        if score is None or float(score) < min_score:
            continue
        canon = str(cand.get("display") or "").strip()
        if not canon or get_by_nombre_canonico(canon) is None:
            continue
        alias_key = text.lower()
        if alias_key in seen_alias:
            continue
        seen_alias.add(alias_key)
        out.append(
            {
                "alias": text,
                "nombre_canonico": canon,
                "count": count,
                "score": round(float(score), 4),
                "notas": f"PR5b auto freq={count} score={float(score):.2f}",
            }
        )
        if len(out) >= max_suggestions:
            break

    out.sort(key=lambda x: (-x["count"], -x["score"]))
    return out


def top_real_no_match_candidates(
    simulation: dict[str, Any],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Top NO_MATCH reales que podrían requerir alta en catálogo o alias.

    Parámetros:
        simulation: salida de ``simulate_rematch_for_samples``.
        limit: máximo de filas.

    Retorno:
        Lista ordenada por frecuencia con candidato top si existe.
    """
    rows = [
        r
        for r in simulation.get("details") or []
        if r.get("simulated_status") == "NO_MATCH" and not r.get("is_synthetic")
    ]
    rows.sort(key=lambda x: int(x.get("count") or 0), reverse=True)
    out: list[dict[str, Any]] = []
    for row in rows[:limit]:
        cand = row.get("top_candidate")
        out.append(
            {
                "text": row.get("text"),
                "count": row.get("count"),
                "top_candidate": cand,
                "action_hint": (
                    "revisar alta en calle_catalogo"
                    if not cand
                    else "revisar alias o catálogo"
                ),
            }
        )
    return out


def diagnose_pendiente_nomenclatura(*, limit: int = 500) -> dict[str, Any]:
    """
    Diagnóstico completo sobre domicilios reales con nomenclatura no OK.

    Parámetros:
        limit: grupos de calle distintos a analizar (por frecuencia).

    Retorno:
        Resumen DB, simulación rematch, alias auditados y sugerencias.
    """
    counts = count_domicilios_nomenclatura_pendiente()
    alias_audit = audit_calle_aliases()
    samples = fetch_pendiente_calle_frecuencias(limit=limit)
    simulation = simulate_rematch_for_samples(samples)
    origin_split = _split_simulation_by_origin(simulation)

    real_samples = [s for s in samples if not s.get("is_synthetic")]
    real_texts = [s["text"] for s in real_samples]
    match_report_all = analyze_street_match_samples([s["text"] for s in samples])
    match_report_real = analyze_street_match_samples(real_texts) if real_texts else {
        "total": 0,
        "ok": 0,
        "review": 0,
        "no_match": 0,
        "success_rate": 0.0,
        "auto_ok_rate": 0.0,
        "details": [],
    }

    suggestions = suggest_aliases_from_simulation(simulation)
    would_ok = simulation["would_become_ok_domicilios"]

    return {
        "domicilios_pendientes_total": counts["pendiente_total"],
        "status_breakdown_db": counts["by_status"],
        "fuente_oficial": "calle_catalogo (DB)",
        "alias_csv_rol": "variantes/abreviaturas validadas contra calle_catalogo",
        "alias_audit": alias_audit,
        "unique_calle_groups_analyzed": len(samples),
        "domicilios_in_top_groups": simulation["domicilios_in_sample"],
        "origin_split": origin_split,
        "match_on_unique_texts": match_report_all,
        "match_on_real_texts": match_report_real,
        "simulation": simulation,
        "top_real_no_match": top_real_no_match_candidates(simulation),
        "suggested_aliases": suggestions,
        "impact_estimate": {
            "would_become_ok_in_sample": would_ok,
            "would_become_ok_real_only": origin_split["real_would_become_ok"],
            "sample_ok_rate": simulation["simulated_ok_rate"],
            "real_ok_rate": origin_split["real_simulated_ok_rate"],
            "extrapolated_ok_domicilios_min": origin_split["real_would_become_ok"],
            "note": (
                "Estimación sobre top grupos por frecuencia; fuente oficial calle_catalogo; "
                "no re-normaliza esquina ni persiste."
            ),
        },
    }


def _load_existing_alias_keys() -> set[str]:
    keys: set[str] = set()
    if not _ALIASES_CSV.is_file():
        return keys
    with _ALIASES_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            alias = (row.get("alias") or "").strip().lower()
            if alias:
                keys.add(alias)
    return keys


def append_suggested_aliases_to_csv(
    suggestions: list[dict[str, Any]],
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """
    Agrega alias sugeridos al CSV si no existen y el canon está en catálogo.

    Parámetros:
        suggestions: salida de ``suggest_aliases_from_simulation``.
        dry_run: si True, no escribe disco.

    Retorno:
        ``{added, skipped_existing, skipped_invalid_canon, rows}``.
    """
    existing = _load_existing_alias_keys()
    to_add: list[dict[str, str]] = []
    skipped = 0
    skipped_invalid = 0
    for s in suggestions:
        alias = str(s.get("alias") or "").strip()
        canon = str(s.get("nombre_canonico") or "").strip()
        if not alias or not canon:
            continue
        if get_by_nombre_canonico(canon) is None:
            skipped_invalid += 1
            continue
        if alias.lower() in existing:
            skipped += 1
            continue
        to_add.append(
            {
                "alias": alias,
                "nombre_canonico": canon,
                "notas": str(s.get("notas") or "PR5b sugerido"),
            }
        )
        existing.add(alias.lower())

    if not dry_run and to_add:
        write_header = not _ALIASES_CSV.is_file() or _ALIASES_CSV.stat().st_size == 0
        with _ALIASES_CSV.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["alias", "nombre_canonico", "notas"])
            if write_header:
                writer.writeheader()
            for row in to_add:
                writer.writerow(row)
        reload_calle_aliases_cache()

    return {
        "added": len(to_add),
        "skipped_existing": skipped,
        "skipped_invalid_canon": skipped_invalid,
        "rows": to_add,
    }
