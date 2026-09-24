"""
PREDEPLOY-CLEANUP.3A.1-DIAG — desambiguación de EO INDETERMINADOS (solo SELECT).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import (
    OT_TEST_PATTERN,
    RUBRO_TEST_PATTERN,
    RUBROS_CANONICOS,
    SQL_TEST_USER_WHERE,
    TEST_ACTUACIONES_SQL,
)
from app.domains.predeploy_cleanup.manifest_io import entity_ids, load_manifest
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    _chunk_ids,
    _fetch_ids,
    load_user_fk_columns,
)

TEST_STREET_PATTERN = re.compile(r"(CalleCat|Main Canon|Esquina Canon)\s+\d+", re.I)
DOMICILIO_UUID_CALLE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.I)
CONTRIB_FIXTURE = re.compile(
    r"(fixture|test|qa_|stab|fix\d|pr\d|uuid|St4_|hotfix)", re.I
)

EO_CODE_ASSIGNMENT = {
    "servicios": [
        "resolve_establecimiento_por_domicilio.py — crea/reutiliza EO 1:1 domicilio",
        "vincular_establecimiento_operativo_actuacion_service.py — try_vincular al crear/editar actuación (grilla)",
        "completar_trabajo_cierre_service.py — resolve EO al cerrar visita realizada",
        "update_service.py — try_vincular tras PUT; desvincula si identidad inválida",
    ],
    "reglas": [
        "EO se crea cuando domicilio tiene contribuyente+rubro+calle+número",
        "Actuación vieja puede recibir EO al editarse o al completar trabajo (backfill)",
        "ON DELETE EO → actuaciones.establecimiento_operativo_id SET NULL",
        "Mismo domicilio puede tener actuaciones sin EO vinculado (históricas)",
    ],
    "tests_relevantes": [
        "test_gestion_fix_6.py — local cerrado vincula EO",
        "test_gestion_fix_10b_1_2.py — completar trabajo crea/vincula EO",
        "test_gestion_fix_10b_1_6.py — EO huérfano / desvinculación",
    ],
}


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _scalar(conn: Connection, sql: str, params: dict | None = None) -> Any:
    row = conn.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


def load_eo_ids_from_prior_diag(path: Path) -> tuple[list[int], list[int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    indet = [e["id"] for e in data["establecimientos"]["buckets"]["INDETERMINADO"]]
    seguro = [e["id"] for e in data["establecimientos"]["buckets"]["CONFIRMADO_TEST_SEGURO"]]
    return indet, seguro


def _classify_act(
    act_id: int,
    act_row: dict[str, Any],
    prot: dict[str, set[int]],
    test_act_ids: set[int],
) -> str:
    if act_id in prot.get("actuaciones", set()):
        return "PROTECTED_REAL"
    if act_id in test_act_ids:
        return "CONFIRMADO_TEST"
    ot_num = (act_row.get("numero_acta") or "").strip()
    calle = (act_row.get("calle") or "").strip()
    if OT_TEST_PATTERN.match(ot_num) or DOMICILIO_UUID_CALLE.match(calle):
        return "CONFIRMADO_TEST"
    if act_row.get("notificacion_id") in prot.get("notificacion", set()):
        return "PROTECTED_REAL"
    if act_row.get("comprobacion_id") in prot.get("comprobacion", set()):
        return "PROTECTED_REAL"
    insp = act_row.get("inspeccion_id")
    if insp and insp in prot.get("inspeccion", set()):
        return "PROTECTED_REAL"
    return "INDETERMINADO"


def _act_evidence(conn: Connection, act_id: int, act_row: dict[str, Any], prot: dict[str, set[int]]) -> dict[str, Any]:
    """Evidencia positiva real vs test para actuación."""
    ot_num = (act_row.get("numero_acta") or "").strip()
    calle = (act_row.get("calle") or "").strip()
    real_signals: list[str] = []
    test_signals: list[str] = []

    if act_row.get("inspeccion_id"):
        real_signals.append("tiene_inspeccion")
    if act_row.get("notificacion_id"):
        if act_row["notificacion_id"] in prot.get("notificacion", set()):
            real_signals.append("notificacion_protegida")
        else:
            real_signals.append("tiene_notificacion")
    if act_row.get("comprobacion_id"):
        if act_row["comprobacion_id"] in prot.get("comprobacion", set()):
            real_signals.append("comprobacion_protegida")
        else:
            real_signals.append("tiene_comprobacion")
    if act_row.get("inspector_count", 0) > 0:
        real_signals.append("tiene_inspectores")
    if act_row.get("expediente_count", 0) > 0:
        real_signals.append("tiene_expediente")
    if act_row.get("oficio_count", 0) > 0:
        real_signals.append("tiene_oficio")
    if act_row.get("fecha") and str(act_row["fecha"]) < "2025-01-01":
        real_signals.append("fecha_anterior_2025")

    if OT_TEST_PATTERN.match(ot_num):
        test_signals.append("ot_fixture_pattern")
    if DOMICILIO_UUID_CALLE.match(calle):
        test_signals.append("calle_uuid_fixture")
    if act_id == 11450:
        test_signals.append("act_id_fixture_literal")
    if RUBRO_TEST_PATTERN.search(act_row.get("rubro_nombre") or ""):
        test_signals.append("rubro_fixture")
    if CONTRIB_FIXTURE.search(act_row.get("contrib_apellido") or ""):
        test_signals.append("contribuyente_fixture")
    if CONTRIB_FIXTURE.search(act_row.get("contrib_nombre") or ""):
        test_signals.append("contribuyente_fixture")

    return {"real_signals": real_signals, "test_signals": test_signals}


def _classify_domicilio(dom_row: dict[str, Any], prot_dom_ids: set[int]) -> str:
    calle = (dom_row.get("calle") or "").strip()
    if DOMICILIO_UUID_CALLE.match(calle) or TEST_STREET_PATTERN.search(calle):
        return "CONFIRMADO_TEST"
    if dom_row.get("id") in prot_dom_ids:
        return "REAL"
    if CONTRIB_FIXTURE.search(calle):
        return "CONFIRMADO_TEST"
    return "INDETERMINADO"


def _chronology_pattern(eo_created_at: Any, direct_acts: list[dict]) -> str:
    if not direct_acts:
        return "sin_actuaciones_directas"
    eo_ts = eo_created_at
    act_ts = [a.get("created_at") for a in direct_acts if a.get("created_at")]
    if not eo_ts or not act_ts:
        return "D_sin_timestamps_suficientes"
    eo_dt = eo_ts if isinstance(eo_ts, datetime) else datetime.fromisoformat(str(eo_ts))
    act_dts = [
        t if isinstance(t, datetime) else datetime.fromisoformat(str(t)) for t in act_ts
    ]
    min_act = min(act_dts)
    max_act = max(act_dts)
    if eo_dt > min_act and (eo_dt - min_act).days > 0:
        return "A_eo_posterior_a_actuaciones_historicas"
    if abs((eo_dt - min_act).total_seconds()) < 120 and abs((eo_dt - max_act).total_seconds()) < 120:
        return "B_eo_y_actuaciones_mismo_momento"
    if eo_dt < min_act:
        return "C_eo_anterior_a_actuaciones"
    return "D_sin_patron_claro"


def _final_classify_eo(
    eo_row: dict[str, Any],
    direct_acts: list[dict[str, Any]],
    same_addr_acts: list[dict[str, Any]],
    domicilio_cls: str,
    chronology: str,
    has_other_child_refs: bool,
) -> tuple[str, str]:
    """Clasificación final única + razón."""
    direct_cls = [a["classification"] for a in direct_acts]

    if any(c == "PROTECTED_REAL" for c in direct_cls):
        if chronology.startswith("A_"):
            return "TEST_WRAPPER_AROUND_REAL", "actuacion_directa_protegida_eo_posterior"
        return "TEST_WRAPPER_AROUND_REAL", "actuacion_directa_protegida"

    if direct_acts and all(c == "CONFIRMADO_TEST" for c in direct_cls):
        return "CONFIRMADO_TEST_SEGURO", "todas_actuaciones_directas_confirmado_test"

    if not direct_acts and not has_other_child_refs:
        # §13: actuaciones indeterminadas solo por domicilio no bloquean
        if domicilio_cls == "CONFIRMADO_TEST":
            return "CONFIRMADO_TEST_SEGURO", "cero_actuaciones_directas_domicilio_test"
        return "CONFIRMADO_TEST_SEGURO", "cero_actuaciones_directas_sin_refs_hijas"

    if direct_acts and any(c == "INDETERMINADO" for c in direct_cls):
        indet = [a for a in direct_acts if a["classification"] == "INDETERMINADO"]
        strong_real = any(len(a["evidence"]["real_signals"]) >= 2 for a in indet)
        strong_test = any(len(a["evidence"]["test_signals"]) >= 2 for a in indet)
        if strong_real and not strong_test:
            return "REAL_OPERATIVO", "evidencia_real_en_actuacion_directa_indeterminada"
        if strong_test and not strong_real:
            return "CONFIRMADO_TEST_SEGURO", "evidencia_test_suficiente_reclasificacion_directa"
        return "INDETERMINADO", "actuaciones_directas_indeterminadas"

    if not direct_acts and same_addr_acts:
        same_cls = {a["classification"] for a in same_addr_acts}
        if same_cls <= {"CONFIRMADO_TEST"}:
            return "CONFIRMADO_TEST_SEGURO", "solo_actuaciones_mismo_domicilio_test"
        if "PROTECTED_REAL" in same_cls:
            return "INDETERMINADO", "mismo_domicilio_con_protected_sin_vinculo_directo"
        return "INDETERMINADO", "mismo_domicilio_actuaciones_indeterminadas_sin_vinculo_directo"

    return "INDETERMINADO", "evidencia_insuficiente"


def _load_act_details_batch(conn: Connection, act_ids: set[int]) -> dict[int, dict[str, Any]]:
    if not act_ids:
        return {}
    result: dict[int, dict[str, Any]] = {}
    for chunk in _chunk_ids(act_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = _rows(
            conn,
            f"""
            SELECT a.id, a.fecha, a.tipo, a.mes, a.anio, a.created_at,
                   a.orden_trabajo_id, a.domicilio_id, a.establecimiento_operativo_id,
                   a.notificacion_id, a.comprobacion_id,
                   ot.numero_acta,
                   d.calle, d.numero, d.contribuyente_id, d.rubro_id,
                   r.nombre AS rubro_nombre,
                   c.apellido AS contrib_apellido, c.nombre AS contrib_nombre,
                   (SELECT COUNT(*) FROM inspeccion i WHERE i.actuacion_id = a.id) AS inspeccion_count,
                   (SELECT i.id FROM inspeccion i WHERE i.actuacion_id = a.id LIMIT 1) AS inspeccion_id,
                   (SELECT COUNT(*) FROM actuaciones_inspector ai WHERE ai.actuaciones_id = a.id) AS inspector_count,
                   (SELECT COUNT(*) FROM expediente e
                    JOIN comprobacion comp ON comp.id = a.comprobacion_id
                    WHERE e.comprobacion_id = comp.id) AS expediente_count,
                   (SELECT COUNT(*) FROM oficio o WHERE o.comprobacion_id = a.comprobacion_id) AS oficio_count
            FROM actuaciones a
            LEFT JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
            LEFT JOIN domicilio d ON d.id = a.domicilio_id
            LEFT JOIN rubro r ON r.id = d.rubro_id
            LEFT JOIN contribuyente c ON c.id = d.contribuyente_id
            WHERE a.id IN ({ph})
            """,
        )
        for r in rows:
            result[r["id"]] = r
    return result


def analyze_eo_universe(
    conn: Connection,
    eo_ids: list[int],
    prot: dict[str, set[int]],
    test_act_ids: set[int],
    blocked_139: set[int],
    label: str,
) -> dict[str, Any]:
    """Analiza un conjunto de EO IDs."""
    if not eo_ids:
        return {"label": label, "count": 0}

    existing = []
    missing = []
    for chunk in _chunk_ids(set(eo_ids), 400):
        ph = ",".join(str(i) for i in chunk)
        found = _fetch_ids(conn, f"SELECT id FROM establecimiento_operativo WHERE id IN ({ph})")
        missing.extend(set(chunk) - found)
        existing.extend(found)

    eo_rows = {}
    for chunk in _chunk_ids(set(existing), 200):
        ph = ",".join(str(i) for i in chunk)
        for r in _rows(
            conn,
            f"""
            SELECT eo.id, eo.domicilio_id, eo.created_by_user_id, eo.created_at,
                   d.calle, d.numero, d.esquina_raw, d.contribuyente_id, d.rubro_id,
                   d.created_at AS domicilio_created_at,
                   r.nombre AS rubro_nombre,
                   c.apellido AS contrib_apellido, c.nombre AS contrib_nombre, c.documento AS contrib_documento,
                   u.username AS created_by_username, u.email AS created_by_email
            FROM establecimiento_operativo eo
            JOIN domicilio d ON d.id = eo.domicilio_id
            LEFT JOIN rubro r ON r.id = d.rubro_id
            LEFT JOIN contribuyente c ON c.id = d.contribuyente_id
            JOIN users u ON u.id = eo.created_by_user_id
            WHERE eo.id IN ({ph})
            """,
        ):
            eo_rows[r["id"]] = r

    dom_ids = {r["domicilio_id"] for r in eo_rows.values()}
    prot_dom_ids: set[int] = set()
    for chunk in _chunk_ids(prot.get("actuaciones", set()), 400):
        ph = ",".join(str(i) for i in chunk)
        rows = _rows(
            conn, f"SELECT DISTINCT domicilio_id FROM actuaciones WHERE id IN ({ph}) AND domicilio_id IS NOT NULL"
        )
        prot_dom_ids.update(r["domicilio_id"] for r in rows)

    # direct acts by eo
    direct_by_eo: dict[int, list[int]] = defaultdict(list)
    for chunk in _chunk_ids(set(existing), 200):
        ph = ",".join(str(i) for i in chunk)
        for r in _rows(
            conn,
            f"SELECT id, establecimiento_operativo_id FROM actuaciones "
            f"WHERE establecimiento_operativo_id IN ({ph})",
        ):
            direct_by_eo[r["establecimiento_operativo_id"]].append(r["id"])

    # same address acts
    same_by_dom: dict[int, list[int]] = defaultdict(list)
    for chunk in _chunk_ids(dom_ids, 200):
        ph = ",".join(str(i) for i in chunk)
        for r in _rows(
            conn,
            f"""
            SELECT id, domicilio_id, establecimiento_operativo_id
            FROM actuaciones WHERE domicilio_id IN ({ph})
            """,
        ):
            same_by_dom[r["domicilio_id"]].append(r["id"])

    all_act_ids: set[int] = set()
    for aids in direct_by_eo.values():
        all_act_ids.update(aids)
    for dom_id, aids in same_by_dom.items():
        all_act_ids.update(aids)
    act_details = _load_act_details_batch(conn, all_act_ids)

    # contribuyente multi-domicilio
    contrib_ids = {r["contribuyente_id"] for r in eo_rows.values() if r.get("contribuyente_id")}
    contrib_dom_count: dict[int, int] = {}
    for chunk in _chunk_ids(contrib_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        for r in _rows(
            conn,
            f"SELECT contribuyente_id, COUNT(*) AS cnt FROM domicilio "
            f"WHERE contribuyente_id IN ({ph}) GROUP BY contribuyente_id",
        ):
            contrib_dom_count[r["contribuyente_id"]] = r["cnt"]

    records: list[dict[str, Any]] = []
    structural = Counter()
    final_cls = Counter()

    for eid in sorted(existing):
        eo = eo_rows[eid]
        dom_id = eo["domicilio_id"]
        direct_ids = direct_by_eo.get(eid, [])
        same_ids = [
            aid
            for aid in same_by_dom.get(dom_id, [])
            if aid not in direct_ids
            and (
                act_details.get(aid, {}).get("establecimiento_operativo_id") is None
                or act_details.get(aid, {}).get("establecimiento_operativo_id") != eid
            )
        ]

        direct_acts = []
        for aid in direct_ids:
            row = act_details.get(aid, {})
            cls = _classify_act(aid, row, prot, test_act_ids)
            ev = _act_evidence(conn, aid, row, prot)
            direct_acts.append(
                {
                    "actuacion_id": aid,
                    "fecha": str(row.get("fecha")),
                    "tipo": row.get("tipo"),
                    "orden_trabajo_id": row.get("orden_trabajo_id"),
                    "numero_acta": row.get("numero_acta"),
                    "domicilio_id": row.get("domicilio_id"),
                    "contribuyente_id": row.get("contribuyente_id"),
                    "rubro": row.get("rubro_nombre"),
                    "created_at": str(row.get("created_at")),
                    "inspeccion_count": row.get("inspeccion_count", 0),
                    "classification": cls,
                    "evidence": ev,
                    "in_blocked_139": aid in blocked_139,
                }
            )

        same_addr_acts = []
        for aid in same_ids:
            row = act_details.get(aid, {})
            cls = _classify_act(aid, row, prot, test_act_ids)
            same_addr_acts.append(
                {
                    "actuacion_id": aid,
                    "classification": cls,
                    "establecimiento_operativo_id": row.get("establecimiento_operativo_id"),
                    "numero_acta": row.get("numero_acta"),
                }
            )

        dom_row = {
            "id": dom_id,
            "calle": eo["calle"],
            "numero": eo["numero"],
        }
        domicilio_cls = _classify_domicilio(dom_row, prot_dom_ids)
        chronology = _chronology_pattern(eo["created_at"], direct_acts)

        ini_cnt = _scalar(
            conn,
            "SELECT COUNT(*) FROM iniciador_ruta WHERE domicilio_id = :d AND deleted_at IS NULL",
            {"d": dom_id},
        )
        has_other = bool(ini_cnt)

        rubro_cls = (
            "canonico"
            if (eo.get("rubro_nombre") or "") in RUBROS_CANONICOS
            else (
                "qa_fixture"
                if RUBRO_TEST_PATTERN.search(eo.get("rubro_nombre") or "")
                else "indeterminado"
            )
        )

        classification, reason = _final_classify_eo(
            eo, direct_acts, same_addr_acts, domicilio_cls, chronology, has_other
        )
        final_cls[classification] += 1

        set_null_on_delete = {
            "total_direct": len(direct_acts),
            "test_direct": sum(1 for a in direct_acts if a["classification"] == "CONFIRMADO_TEST"),
            "protected_direct": sum(1 for a in direct_acts if a["classification"] == "PROTECTED_REAL"),
            "indeterminate_direct": sum(1 for a in direct_acts if a["classification"] == "INDETERMINADO"),
        }

        if len(direct_acts) == 0 and len(same_addr_acts) > 0:
            structural["A_cero_directas_solo_mismo_domicilio"] += 1
        if direct_acts and all(a["classification"] == "CONFIRMADO_TEST" for a in direct_acts):
            structural["B_directas_todas_test"] += 1
        if any(a["classification"] == "PROTECTED_REAL" for a in direct_acts):
            structural["C_directa_protected"] += 1
        if any(a["classification"] == "INDETERMINADO" for a in direct_acts):
            structural["D_directa_indeterminada"] += 1
        if chronology.startswith("A_"):
            structural["E_eo_posterior_historicas"] += 1
        if chronology.startswith("B_"):
            structural["F_eo_mismo_momento_test"] += 1

        fixture_street = bool(TEST_STREET_PATTERN.search(eo.get("calle") or ""))

        records.append(
            {
                "eo_id": eid,
                "created_by_user_id": eo["created_by_user_id"],
                "created_by_username": eo["created_by_username"],
                "eo_created_at": str(eo["created_at"]),
                "domicilio_id": dom_id,
                "domicilio": {
                    "calle": eo["calle"],
                    "numero": eo["numero"],
                    "esquina_raw": eo.get("esquina_raw"),
                    "classification": domicilio_cls,
                },
                "contribuyente": {
                    "id": eo.get("contribuyente_id"),
                    "apellido": eo.get("contrib_apellido"),
                    "nombre": eo.get("contrib_nombre"),
                    "documento": eo.get("contrib_documento"),
                    "domicilios_count": contrib_dom_count.get(eo.get("contribuyente_id"), 0),
                },
                "rubro": {"nombre": eo.get("rubro_nombre"), "classification": rubro_cls},
                "counts": {
                    "direct_actuaciones": len(direct_acts),
                    "same_address_actuaciones": len(same_addr_acts),
                    "iniciadores_domicilio": ini_cnt,
                },
                "direct_actuaciones": direct_acts,
                "same_address_actuaciones": same_addr_acts,
                "chronology": chronology,
                "fixture_street": fixture_street,
                "classification_final": classification,
                "classification_reason": reason,
                "set_null_impact": set_null_on_delete,
                "linked_blocked_139": [a["actuacion_id"] for a in direct_acts if a["in_blocked_139"]],
            }
        )

    safe_candidates = [
        r["eo_id"]
        for r in records
        if r["classification_final"] == "CONFIRMADO_TEST_SEGURO"
        and r["set_null_impact"]["protected_direct"] == 0
        and r["set_null_impact"]["indeterminate_direct"] == 0
        and not any(a["classification"] == "PROTECTED_REAL" for a in r["direct_actuaciones"])
    ]

    phase2a_strict = [
        r["eo_id"]
        for r in records
        if r["eo_id"] in safe_candidates
        and (
            r["set_null_impact"]["total_direct"] == 0
            or r["set_null_impact"]["test_direct"] == r["set_null_impact"]["total_direct"]
        )
    ]

    return {
        "label": label,
        "input_count": len(eo_ids),
        "existing_count": len(existing),
        "missing_ids": sorted(missing),
        "final_classification": dict(final_cls),
        "structural_buckets": dict(structural),
        "records": records,
        "safe_candidates": safe_candidates,
        "fase2a_eo_only_ids": phase2a_strict,
        "summary": {
            "cero_actuaciones_directas": sum(1 for r in records if r["counts"]["direct_actuaciones"] == 0),
            "solo_test_directas": sum(
                1
                for r in records
                if r["counts"]["direct_actuaciones"] > 0
                and all(a["classification"] == "CONFIRMADO_TEST" for a in r["direct_actuaciones"])
            ),
            "con_protected_directas": sum(
                1
                for r in records
                if any(a["classification"] == "PROTECTED_REAL" for a in r["direct_actuaciones"])
            ),
            "con_indeterminadas_directas": sum(
                1
                for r in records
                if any(a["classification"] == "INDETERMINADO" for a in r["direct_actuaciones"])
            ),
            "linked_blocked_139_count": sum(1 for r in records if r["linked_blocked_139"]),
            "fixture_street_count": sum(1 for r in records if r["fixture_street"]),
        },
    }


def simulate_user_unlock(conn: Connection, eo_ids: set[int], test_users: set[int]) -> dict[str, Any]:
    fk_columns = load_user_fk_columns(conn)
    users_only_eo: set[int] = set()
    users_still: set[int] = set()

    for uid in test_users:
        refs: list[tuple[str, int]] = []
        for table, col in fk_columns:
            rows = conn.execute(
                text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}
            ).fetchall()
            for r in rows:
                refs.append((table, r[0]))
        non_eo = [
            (t, rid)
            for t, rid in refs
            if not (t == "establecimiento_operativo" and rid in eo_ids)
        ]
        eo_refs = [(t, rid) for t, rid in refs if t == "establecimiento_operativo" and rid in eo_ids]
        if eo_refs and not non_eo:
            users_only_eo.add(uid)
        elif refs:
            users_still.add(uid)

    return {
        "eo_deletables_simulados": len(eo_ids),
        "users_liberados_inmediatamente": len(users_only_eo),
        "users_todavia_bloqueados": len(users_still),
        "users_sin_ninguna_fk": len(test_users) - len(users_only_eo) - len(users_still),
        "unlocked_sample": sorted(users_only_eo)[:40],
    }


def run_eo_indeterminate_diag(
    conn: Connection,
    prior_diag_path: Path,
    protected_manifest_path: Path,
) -> dict[str, Any]:
    indet_ids, seguro_ids = load_eo_ids_from_prior_diag(prior_diag_path)
    protected_manifest = load_manifest(protected_manifest_path)
    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    test_act_ids = _fetch_ids(conn, TEST_ACTUACIONES_SQL)
    all_test = test_act_ids
    blocked_139 = all_test - prot.get("actuaciones", set())
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")

    eo_783 = analyze_eo_universe(conn, indet_ids, prot, test_act_ids, blocked_139, "INDETERMINADO_783")
    reval_77 = analyze_eo_universe(conn, seguro_ids, prot, test_act_ids, blocked_139, "REVALIDACION_77")

    all_safe = set(eo_783["fase2a_eo_only_ids"]) | set(
        r["eo_id"]
        for r in reval_77["records"]
        if r["classification_final"] == "CONFIRMADO_TEST_SEGURO"
    )
    user_sim = simulate_user_unlock(conn, all_safe, test_users)

    reval_still_safe = sum(
        1 for r in reval_77["records"] if r["classification_final"] == "CONFIRMADO_TEST_SEGURO"
    )
    reval_degraded = len(reval_77["records"]) - reval_still_safe

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3A.1-DIAG",
        "mode": "READ_ONLY_SELECT",
        "writes_executed": False,
        "universe_verification": {
            "indeterminado_ids_from_prior_diag": len(indet_ids),
            "still_existing": eo_783["existing_count"],
            "missing_since_prior_diag": eo_783["missing_ids"],
            "database": _scalar(conn, "SELECT DATABASE()"),
            "alembic_version": _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1"),
        },
        "eo_code_assignment": EO_CODE_ASSIGNMENT,
        "eo_783": eo_783,
        "revalidation_77": {
            "original_count": len(seguro_ids),
            "still_seguro": reval_still_safe,
            "degraded": reval_degraded,
            "degraded_records": [
                {
                    "eo_id": r["eo_id"],
                    "new_classification": r["classification_final"],
                    "reason": r["classification_reason"],
                }
                for r in reval_77["records"]
                if r["classification_final"] != "CONFIRMADO_TEST_SEGURO"
            ],
            "detail": reval_77,
        },
        "direct_vs_same_address_aggregate": {
            "total_direct_act_refs": sum(r["counts"]["direct_actuaciones"] for r in eo_783["records"]),
            "total_same_address_only_refs": sum(
                r["counts"]["same_address_actuaciones"] for r in eo_783["records"]
            ),
            "eo_with_zero_direct": eo_783["summary"]["cero_actuaciones_directas"],
            "eo_with_only_same_address_indeterminate": sum(
                1
                for r in eo_783["records"]
                if r["counts"]["direct_actuaciones"] == 0
                and any(
                    a["classification"] == "INDETERMINADO" for a in r["same_address_actuaciones"]
                )
            ),
        },
        "classification": {
            "CONFIRMADO_TEST_SEGURO": eo_783["final_classification"].get("CONFIRMADO_TEST_SEGURO", 0),
            "TEST_WRAPPER_AROUND_REAL": eo_783["final_classification"].get("TEST_WRAPPER_AROUND_REAL", 0),
            "REAL_OPERATIVO": eo_783["final_classification"].get("REAL_OPERATIVO", 0),
            "INDETERMINADO": eo_783["final_classification"].get("INDETERMINADO", 0),
            "sum_check": sum(eo_783["final_classification"].values()),
        },
        "safe_candidates": {
            "confidente": eo_783["safe_candidates"],
            "fase2a_eo_only": eo_783["fase2a_eo_only_ids"],
            "count_fase2a": len(eo_783["fase2a_eo_only_ids"]),
        },
        "blocked": {
            "protected_eo_ids": [
                r["eo_id"]
                for r in eo_783["records"]
                if r["classification_final"] in ("TEST_WRAPPER_AROUND_REAL", "REAL_OPERATIVO")
            ],
            "indeterminado_eo_ids": [
                r["eo_id"] for r in eo_783["records"] if r["classification_final"] == "INDETERMINADO"
            ],
        },
        "user_unlock_simulation": user_sim,
        "relation_blocked_139": {
            "eo_with_direct_link": eo_783["summary"]["linked_blocked_139_count"],
            "eo_ids": [r["eo_id"] for r in eo_783["records"] if r["linked_blocked_139"]],
            "note": "estos EO pertenecen al grafo FASE2B/C, no 2A independiente",
        },
        "relation_fixture_streets": {
            "count_in_783": eo_783["summary"]["fixture_street_count"],
            "eo_ids": [r["eo_id"] for r in eo_783["records"] if r["fixture_street"]],
        },
        "protected_intersections": [
            r for r in eo_783["records"] if any(
                a["classification"] == "PROTECTED_REAL" for a in r["direct_actuaciones"]
            )
        ],
    }


def write_report(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return path
