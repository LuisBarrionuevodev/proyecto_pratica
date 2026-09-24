"""
PREDEPLOY-CLEANUP.3A.3 — reconciliación universo EO seguro FASE 2A (solo SELECT).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE, TEST_ACTUACIONES_SQL
from app.domains.predeploy_cleanup.manifest_io import file_sha256, load_manifest, manifest_sha256
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import _chunk_ids, _fetch_ids, load_user_fk_columns

OUTPUT_TABLES_FORBIDDEN = frozenset(
    {"domicilio", "contribuyente", "actuaciones", "users", "rubro"}
)


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _scalar(conn: Connection, sql: str, params: dict | None = None) -> Any:
    row = conn.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


def load_eo_sets(
    blockers_diag: Path,
    indeterminate_diag: Path,
    structured_acts_diag: Path,
) -> dict[str, Any]:
    """Carga SET_A, SET_B, SET_C desde diagnósticos congelados."""
    p1 = json.loads(blockers_diag.read_text(encoding="utf-8"))
    p2 = json.loads(indeterminate_diag.read_text(encoding="utf-8"))
    p3 = json.loads(structured_acts_diag.read_text(encoding="utf-8"))

    set_a = sorted(e["id"] for e in p1["establecimientos"]["buckets"]["CONFIRMADO_TEST_SEGURO"])
    set_b = sorted(p2["safe_candidates"]["fase2a_eo_only"])
    set_c = sorted(
        {
            a["establecimiento_operativo_id"]
            for a in p3["acts"]
            if a.get("establecimiento_operativo_id")
        }
    )
    acts_274 = sorted(a["actuacion_id"] for a in p3["acts"])

    a_set, b_set, c_set = set(set_a), set(set_b), set(set_c)
    intersections = {
        "A_cap_B": sorted(a_set & b_set),
        "A_cap_C": sorted(a_set & c_set),
        "B_cap_C": sorted(b_set & c_set),
        "A_cap_B_cap_C": sorted(a_set & b_set & c_set),
    }
    safe_final = sorted(a_set | b_set | c_set)

    return {
        "SET_A": set_a,
        "SET_B": set_b,
        "SET_C": set_c,
        "ACTS_274": acts_274,
        "intersections": intersections,
        "intersection_counts": {k: len(v) for k, v in intersections.items()},
        "SAFE_EO_FINAL": safe_final,
        "SAFE_EO_FINAL_count": len(safe_final),
        "arithmetic_check": {
            "A": len(set_a),
            "B": len(set_b),
            "C": len(set_c),
            "sum_if_disjoint": len(set_a) + len(set_b) + len(set_c),
            "union": len(safe_final),
            "disjoint": len(safe_final) == len(set_a) + len(set_b) + len(set_c),
        },
        "source_hashes": {
            "blockers_diag": file_sha256(blockers_diag),
            "indeterminate_diag": file_sha256(indeterminate_diag),
            "structured_acts_diag": file_sha256(structured_acts_diag),
        },
        "prior_incorrect_union_323_note": (
            "323 = 62(B) + 261(C) omitió SET_A (77). SAFE_EO_FINAL correcto = 400."
        ),
    }


def _classify_act_direct(
    act_id: int,
    prot_acts: set[int],
    test_acts_sql: set[int],
    acts_274: set[int],
) -> str:
    if act_id in prot_acts:
        return "PROTECTED_REAL"
    if act_id in acts_274 or act_id in test_acts_sql:
        return "CONFIRMADO_TEST"
    return "INDETERMINADO"


def revalidate_safe_eo_final(
    conn: Connection,
    safe_eo_ids: list[int],
    set_labels: dict[int, str],
    acts_274: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    """Revalida todos los EO del universo seguro contra DB actual."""
    test_user_ids = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    test_acts_sql = _fetch_ids(conn, TEST_ACTUACIONES_SQL)
    prot_acts = prot.get("actuaciones", set())

    missing: list[int] = []
    degraded: list[dict[str, Any]] = []
    valid: list[int] = []
    set_null_impact: list[dict[str, Any]] = []
    set_null_by_cls = {"CONFIRMADO_TEST": 0, "PROTECTED_REAL": 0, "INDETERMINADO": 0}

    existing = set()
    for chunk in _chunk_ids(set(safe_eo_ids), 400):
        ph = ",".join(str(i) for i in chunk)
        existing.update(_fetch_ids(conn, f"SELECT id FROM establecimiento_operativo WHERE id IN ({ph})"))
    missing = sorted(set(safe_eo_ids) - existing)

    for eid in safe_eo_ids:
        if eid not in existing:
            continue
        row = _rows(
            conn,
            """
            SELECT eo.id, eo.created_by_user_id, eo.domicilio_id,
                   u.username, u.email
            FROM establecimiento_operativo eo
            JOIN users u ON u.id = eo.created_by_user_id
            WHERE eo.id = :id
            """,
            {"id": eid},
        )
        if not row:
            missing.append(eid)
            continue
        eo = row[0]
        issues: list[str] = []
        if eo["created_by_user_id"] not in test_user_ids:
            issues.append("created_by_not_test_user")

        direct_acts = _rows(
            conn,
            """
            SELECT a.id, a.tipo, a.notificacion_id, a.comprobacion_id
            FROM actuaciones a
            WHERE a.establecimiento_operativo_id = :eid
            """,
            {"eid": eid},
        )
        act_classes = []
        for act in direct_acts:
            cls = _classify_act_direct(act["id"], prot_acts, test_acts_sql, acts_274)
            act_classes.append({"actuacion_id": act["id"], "classification": cls})
            set_null_impact.append(
                {
                    "actuacion_id": act["id"],
                    "establecimiento_operativo_id": eid,
                    "set_label": set_labels.get(eid, "?"),
                    "classification": cls,
                }
            )
            set_null_by_cls[cls] += 1
            if cls == "PROTECTED_REAL":
                issues.append(f"direct_act_protected_{act['id']}")
            elif cls == "INDETERMINADO":
                issues.append(f"direct_act_indeterminate_{act['id']}")

        label = set_labels.get(eid, "?")
        if label in ("A", "B") and direct_acts:
            issues.append("set_A_B_unexpected_direct_actuaciones")

        if issues:
            degraded.append(
                {
                    "eo_id": eid,
                    "set": label,
                    "issues": issues,
                    "direct_actuaciones": act_classes,
                }
            )
        else:
            valid.append(eid)

    return {
        "valid_count": len(valid),
        "degraded": degraded,
        "degraded_count": len(degraded),
        "missing_ids": missing,
        "set_null_total": len(set_null_impact),
        "set_null_by_classification": set_null_by_cls,
        "set_null_detail_sample": set_null_impact[:30],
        "set_null_all_act_ids": sorted({x["actuacion_id"] for x in set_null_impact}),
        "phase2a_set_null_allowed": (
            set_null_by_cls["PROTECTED_REAL"] == 0 and set_null_by_cls["INDETERMINADO"] == 0
        ),
    }


def protected_closure_check(
    conn: Connection,
    safe_eo_ids: set[int],
    set_null_act_ids: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    """Cruza EO y actuaciones SET NULL vs manifest protegido."""
    conflicts: list[dict[str, Any]] = []
    prot_acts = prot.get("actuaciones", set())
    inter_acts = set_null_act_ids & prot_acts
    if inter_acts:
        conflicts.append(
            {
                "entity": "actuaciones_set_null",
                "intersection": sorted(inter_acts)[:20],
                "count": len(inter_acts),
            }
        )
    for eid in safe_eo_ids:
        if eid in prot.get("establecimiento_operativo", set()):
            conflicts.append({"entity": "establecimiento_operativo", "id": eid})

    return {
        "valid": len(conflicts) == 0,
        "conflicts": conflicts,
        "protected_actuaciones_in_set_null": len(inter_acts),
    }


def simulate_users_unlocked_by_eo_only(
    conn: Connection,
    safe_eo_ids: set[int],
) -> dict[str, Any]:
    """Simula users liberables si solo se borran EO seguros."""
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    unlocked: set[int] = set()
    still_blocked: set[int] = set()

    for uid in test_users:
        refs: list[tuple[str, int]] = []
        for table, col in fk_columns:
            rows = conn.execute(
                text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}
            ).fetchall()
            refs.extend((table, r[0]) for r in rows)
        non_eo = [
            (t, rid)
            for t, rid in refs
            if not (t == "establecimiento_operativo" and rid in safe_eo_ids)
        ]
        eo_only = [
            (t, rid) for t, rid in refs if t == "establecimiento_operativo" and rid in safe_eo_ids
        ]
        if eo_only and not non_eo:
            unlocked.add(uid)
        elif refs:
            still_blocked.add(uid)

    return {
        "test_users_total": len(test_users),
        "users_unlocked_by_eo_only": len(unlocked),
        "users_still_blocked": len(still_blocked),
        "users_without_any_fk": len(test_users) - len(unlocked) - len(still_blocked),
        "unlocked_sample": sorted(unlocked)[:40],
    }


def build_phase2a_manifest_proposal(
    conn: Connection,
    safe_eo_ids: list[int],
    sets_info: dict[str, Any],
    protected_path: Path,
    revalidation: dict[str, Any],
    protected_check: dict[str, Any],
    user_sim: dict[str, Any],
    baseline: dict[str, int],
) -> dict[str, Any]:
    """Propuesta de manifest FASE 2A (sin ejecutar)."""
    if revalidation["degraded_count"] > 0 or revalidation["missing_ids"]:
        raise ValueError("No se puede generar manifest: EO degradados o ausentes")
    if not protected_check["valid"]:
        raise ValueError("No se puede generar manifest: conflictos protected")
    if not revalidation["phase2a_set_null_allowed"]:
        raise ValueError("No se puede generar manifest: SET NULL sobre no-test")

    protected_hash = file_sha256(protected_path)
    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2A",
        "phase_name": "establecimiento_operativo_only",
        "mode": "EXECUTION_MANIFEST_PROPOSAL",
        "writes_executed": False,
        "database": _scalar(conn, "SELECT DATABASE()"),
        "alembic_revision": _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1"),
        "source_diag_hashes": sets_info["source_hashes"],
        "protected_manifest_hash": protected_hash,
        "sets": {
            "SET_A_count": len(sets_info["SET_A"]),
            "SET_B_count": len(sets_info["SET_B"]),
            "SET_C_count": len(sets_info["SET_C"]),
            "SAFE_EO_FINAL_count": len(safe_eo_ids),
            "intersection_counts": sets_info["intersection_counts"],
        },
        "baseline_counts": baseline,
        "post_estimated": {
            "establecimiento_operativo": baseline.get("establecimiento_operativo", 0) - len(safe_eo_ids),
            "actuaciones_physical_count_unchanged": True,
            "actuaciones_set_null_count": revalidation["set_null_total"],
            "users_physical_count_unchanged": True,
            "users_unlocked_after_eo_delete": user_sim["users_unlocked_by_eo_only"],
        },
        "validation": {
            "revalidation": {
                "valid_count": revalidation["valid_count"],
                "degraded_count": revalidation["degraded_count"],
            },
            "protected_closure": protected_check,
            "set_null_by_classification": revalidation["set_null_by_classification"],
            "forbidden_deletes": {
                "domicilio": 0,
                "contribuyente": 0,
                "actuaciones": 0,
                "users": 0,
            },
        },
        "delete_order": ["establecimiento_operativo"],
        "entities": {
            "establecimiento_operativo": [{"id": i} for i in sorted(safe_eo_ids)],
        },
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def run_phase2a_reconcile(
    conn: Connection,
    blockers_diag: Path,
    indeterminate_diag: Path,
    structured_acts_diag: Path,
    protected_path: Path,
) -> dict[str, Any]:
    """Ejecuta reconciliación completa 3A.3."""
    sets_info = load_eo_sets(blockers_diag, indeterminate_diag, structured_acts_diag)
    safe_eo = sets_info["SAFE_EO_FINAL"]

    set_labels: dict[int, str] = {}
    for i in sets_info["SET_A"]:
        set_labels[i] = "A"
    for i in sets_info["SET_B"]:
        set_labels[i] = "B"
    for i in sets_info["SET_C"]:
        set_labels[i] = "C"

    acts_274 = set(sets_info["ACTS_274"])
    prot_manifest = load_manifest(protected_path)
    prot = expand_protected_indirect(conn, load_protected_sets(prot_manifest))

    baseline_tables = [
        "establecimiento_operativo",
        "users",
        "actuaciones",
        "domicilio",
        "contribuyente",
        "iniciador_ruta",
    ]
    baseline = {}
    for tbl in baseline_tables:
        baseline[tbl] = _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}`") or 0

    revalidation = revalidate_safe_eo_final(
        conn, safe_eo, set_labels, acts_274, prot
    )
    set_null_ids = set(revalidation["set_null_all_act_ids"])
    protected_check = protected_closure_check(conn, set(safe_eo), set_null_ids, prot)
    user_sim = simulate_users_unlocked_by_eo_only(conn, set(safe_eo))

    acts_274_still_test = _rows(
        conn,
        f"""
        SELECT id FROM actuaciones WHERE id IN ({",".join(str(i) for i in sorted(acts_274)) or "0"})
        """,
    )
    acts_274_confirmed = all(
        _classify_act_direct(r["id"], prot.get("actuaciones", set()), _fetch_ids(conn, TEST_ACTUACIONES_SQL), acts_274)
        == "CONFIRMADO_TEST"
        for r in acts_274_still_test
    )
    set_c_null_subset = set_null_ids <= acts_274

    manifest_proposal = None
    manifest_error = None
    try:
        if (
            revalidation["degraded_count"] == 0
            and not revalidation["missing_ids"]
            and protected_check["valid"]
            and revalidation["phase2a_set_null_allowed"]
        ):
            manifest_proposal = build_phase2a_manifest_proposal(
                conn,
                safe_eo,
                sets_info,
                protected_path,
                revalidation,
                protected_check,
                user_sim,
                baseline,
            )
    except ValueError as exc:
        manifest_error = str(exc)

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3A.3",
        "mode": "READ_ONLY_RECONCILE",
        "writes_executed": False,
        "sets": sets_info,
        "baseline": baseline,
        "revalidation": revalidation,
        "acts_274": {
            "count": len(acts_274),
            "all_still_confirmed_test": acts_274_confirmed,
            "set_null_subset_of_274": set_c_null_subset,
            "set_null_from_set_c_only_count": len(
                set_null_ids & acts_274
            ),
        },
        "protected_closure": protected_check,
        "user_unlock_simulation": user_sim,
        "manifest_proposal": manifest_proposal,
        "manifest_proposal_error": manifest_error,
    }


def write_json(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path
