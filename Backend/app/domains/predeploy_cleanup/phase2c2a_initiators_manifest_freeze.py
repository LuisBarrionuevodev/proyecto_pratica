"""
PREDEPLOY-CLEANUP.3F.2 — congelar execution manifest FASE 2C.2A (155 iniciadores).
Solo lectura / generación de manifest. Sin DELETE/UPDATE/INSERT en DB.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import RELEVAMIENTOS_QA_IDS, SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.execution_validator import load_iniciador_ruta_incoming_fks
from app.domains.predeploy_cleanup.manifest_io import file_sha256, load_manifest, manifest_sha256
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar, audit_otro_relevador_qa
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import (
    PROTECTED_COMP_CLOSURE_8,
    SYNC_REL_OBS_RE,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    load_user_fk_columns,
    protection_closure_check,
)

PHASE2C2A_DELETE_ORDER = ["iniciador_ruta"]

BASELINE_POST_2C1 = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8194,
    "actuaciones": 8222,
    "denuncia": 417,
    "relevamiento": 4592,
    "orden_trabajo": 8958,
    "inspeccion": 915,
    "actuaciones_inspector": 4189,
    "clausura": 69,
    "decomiso": 25,
    "acta_inspeccion_item": 52,
}

EXPECTED_SAFE_TOTAL = 155
EXPECTED_RESIDUAL = 129
EXPECTED_RELEVAMIENTO = 26

POST_INICIADOR = 8039

FORBIDDEN_MANIFEST_ENTITIES = frozenset(
    {
        "notificacion",
        "comprobacion",
        "actuaciones",
        "relevamiento",
        "orden_trabajo",
        "denuncia",
        "domicilio",
        "users",
        "ruta_item",
        "ruta_pool_dia",
        "ruta_grupo",
        "ruta_trabajo",
    }
)


class ManifestFreezeError(Exception):
    """Aborta freeze del manifest FASE 2C.2A."""


def load_safe_initiators_from_diag(diag_path: Path) -> dict[str, Any]:
    """Carga SAFE_INITIATOR_2C2A congelado del diagnóstico 3F.1."""
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    raw = data.get("safe_initiators", {}).get("SAFE_INITIATOR_2C2A", [])
    ids = [int(x) for x in raw]
    if len(ids) != EXPECTED_SAFE_TOTAL:
        raise ManifestFreezeError(f"SAFE_INITIATOR_2C2A: expected {EXPECTED_SAFE_TOTAL}, got {len(ids)}")
    if len(ids) != len(set(ids)):
        raise ManifestFreezeError("SAFE_INITIATOR_2C2A: duplicate ids")
    rel_set = set(data.get("relevamiento_initiators", {}).get("SAFE_TEST_from_relevamiento_universe", []))
    residual = [i for i in ids if i not in rel_set]
    relev = [i for i in ids if i in rel_set]
    if len(residual) != EXPECTED_RESIDUAL:
        raise ManifestFreezeError(f"residual breakdown: expected {EXPECTED_RESIDUAL}, got {len(residual)}")
    if len(relev) != EXPECTED_RELEVAMIENTO:
        raise ManifestFreezeError(f"relevamiento breakdown: expected {EXPECTED_RELEVAMIENTO}, got {len(relev)}")
    return {
        "all_ids": set(ids),
        "residual_ids": set(residual),
        "relevamiento_ids": set(relev),
        "diag": data,
    }


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ManifestFreezeError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ManifestFreezeError(f"alembic={alembic}")
    counts = {}
    for table, expected in BASELINE_POST_2C1.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            raise ManifestFreezeError(f"baseline {table}: {actual} != {expected}")
    return {"database": db, "alembic_revision": alembic, "counts": counts}


def _incoming_fk_blockers(conn: Connection, ini_ids: set[int]) -> list[dict[str, Any]]:
    """Todas las FK entrantes hacia iniciador_ruta para los IDs dados."""
    incoming = load_iniciador_ruta_incoming_fks(conn)
    blockers: list[dict[str, Any]] = []
    for edge in incoming:
        child_table = edge["child_table"]
        child_col = edge["child_column"]
        for chunk in _chunk_ids(ini_ids, 300):
            ph = ",".join(str(i) for i in chunk)
            rows = conn.execute(
                text(f"SELECT `{child_col}` FROM `{child_table}` WHERE `{child_col}` IN ({ph})")
            ).fetchall()
            for r in rows:
                blockers.append(
                    {
                        "child_table": child_table,
                        "child_column": child_col,
                        "iniciador_id": r[0],
                        "delete_rule": edge.get("delete_rule"),
                    }
                )
    return blockers


def _validate_residual_classification(diag: dict[str, Any], residual_ids: set[int]) -> dict[str, Any]:
    items = {it["iniciador_id"]: it for it in diag["initiators_167"]["items"]}
    violations: list[dict[str, Any]] = []
    for iid in sorted(residual_ids):
        it = items.get(iid)
        if not it:
            violations.append({"iniciador_id": iid, "reason": "not_in_167_universe"})
            continue
        if it.get("final_classification") != "SAFE_TEST_INITIATOR":
            violations.append(
                {"iniciador_id": iid, "classification": it.get("final_classification")}
            )
        allowed_tipos = {"REINSPECCION_NOTIFICACION", "VERIFICAR_INFORMAR_OFICIO"}
        if it.get("tipo") not in allowed_tipos:
            violations.append({"iniciador_id": iid, "tipo": it.get("tipo")})
    if violations:
        raise ManifestFreezeError(f"residual classification violations: {violations[:5]}")
    return {"validated": len(residual_ids), "all_SAFE_TEST_INITIATOR": True}


def _validate_relevamiento_initiators(
    conn: Connection,
    diag: dict[str, Any],
    rel_ini_ids: set[int],
    rel_26: set[int],
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    rel_items = {it["iniciador_id"]: it for it in diag.get("relevamiento_26", {}).get("items", [])}
    for iid in sorted(rel_ini_ids):
        row = conn.execute(
            text(
                """
                SELECT ir.id, ir.tipo_iniciador, ir.relevamiento_id, ir.observaciones,
                       r.created_by_user_id, u.username
                FROM iniciador_ruta ir
                JOIN relevamiento r ON r.id = ir.relevamiento_id
                LEFT JOIN users u ON u.id = r.created_by_user_id
                WHERE ir.id = :id
                """
            ),
            {"id": iid},
        ).fetchone()
        if not row:
            violations.append({"iniciador_id": iid, "reason": "missing"})
            continue
        rid = row[2]
        if rid not in rel_26:
            violations.append({"iniciador_id": iid, "relevamiento_id": rid, "reason": "not_in_26"})
        if row[1] != "RELEVAMIENTO":
            violations.append({"iniciador_id": iid, "tipo": row[1]})
        obs = row[3] or ""
        sync_rel = bool(SYNC_REL_OBS_RE.search(obs))
        if not sync_rel:
            violations.append({"iniciador_id": iid, "observaciones": obs[:80]})
        username = row[5] or ""
        rel_creator_id = row[4]
        user_test = bool(
            rel_creator_id
            and _scalar(
                conn,
                f"SELECT COUNT(*) FROM users u WHERE u.id = :id AND ({SQL_TEST_USER_WHERE})",
                {"id": rel_creator_id},
            )
        )
        # Alineado con 3F.1: sync observaciones basta; relhot_* o test user en relevamiento es evidencia adicional.
        if not (sync_rel or user_test or str(username).startswith("relhot_")):
            violations.append({"iniciador_id": iid, "creator": username, "sync_rel": sync_rel})
    if violations:
        raise ManifestFreezeError(f"relevamiento initiator violations: {violations[:5]}")
    return {"validated": len(rel_ini_ids), "all_linked_to_26_relevamientos": True}


def _residual_tipo_breakdown(diag: dict[str, Any], residual_ids: set[int]) -> dict[str, int]:
    """Cuenta tipos de iniciador en el subconjunto residual (excl. relevamiento)."""
    items = {it["iniciador_id"]: it for it in diag["initiators_167"]["items"]}
    counts: dict[str, int] = {}
    for iid in residual_ids:
        tipo = items.get(iid, {}).get("tipo", "UNKNOWN")
        counts[tipo] = counts.get(tipo, 0) + 1
    return counts


def _excluded_indeterminate_initiators(diag: dict[str, Any]) -> set[int]:
    excluded: set[int] = set()
    for it in diag["initiators_167"]["items"]:
        if it.get("final_classification") in ("KEEP_INDETERMINATE_SOURCE", "OTHER_INDETERMINATE"):
            excluded.add(it["iniciador_id"])
    return excluded


def _simulate_unlock(
    conn: Connection,
    blocked_148: set[int],
    rel_26: set[int],
    safe_ini: set[int],
) -> dict[str, Any]:
    unlocked_acts: list[int] = []
    still_acts: list[int] = []
    for aid in sorted(blocked_148):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}")
        if not (inis - safe_ini) and not ri and not rp:
            unlocked_acts.append(aid)
        else:
            still_acts.append(aid)

    unlocked_rel: list[int] = []
    still_rel: list[int] = []
    for rid in sorted(rel_26):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}")
        if not (inis - safe_ini):
            unlocked_rel.append(rid)
        else:
            still_rel.append(rid)

    return {
        "actuaciones": {
            "unlocked": unlocked_acts,
            "blocked": still_acts,
            "unlocked_count": len(unlocked_acts),
            "blocked_count": len(still_acts),
        },
        "relevamientos": {
            "unlocked": unlocked_rel,
            "blocked": still_rel,
            "unlocked_count": len(unlocked_rel),
            "blocked_count": len(still_rel),
        },
    }


def _users_simulation(conn: Connection, baseline_free: int, safe_ini: set[int]) -> dict[str, Any]:
    """Simula FK users tras eliminar iniciadores (solo iniciador_ruta.created_by_user_id)."""
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    newly_free: list[int] = []
    still_blocked: list[int] = []
    for uid in test_users:
        refs = 0
        for table, col in fk_columns:
            if table == "iniciador_ruta" and col == "created_by_user_id":
                n = _scalar(
                    conn,
                    f"SELECT COUNT(*) FROM iniciador_ruta WHERE created_by_user_id = :uid "
                    f"AND id NOT IN ({','.join(str(i) for i in sorted(safe_ini)) or '0'})",
                    {"uid": uid},
                )
            else:
                n = _scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` = :uid", {"uid": uid})
            refs += int(n or 0)
        if refs == 0:
            newly_free.append(uid)
        else:
            still_blocked.append(uid)
    after_free = len(newly_free)
    return {
        "users_test_fk_free_baseline": baseline_free,
        "users_test_fk_free_after_2c2a_sim": after_free,
        "users_additionally_unlocked_by_2c2a_sim": max(0, after_free - baseline_free),
        "users_test_still_blocked_sim": len(still_blocked),
    }


def _protected_comp_regression(conn: Connection, prot: dict[str, set[int]]) -> dict[str, Any]:
    found: dict[str, bool] = {}
    in_prot: dict[str, bool] = {}
    for cid in PROTECTED_COMP_CLOSURE_8:
        found[str(cid)] = bool(
            _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid})
        )
        in_prot[str(cid)] = cid in prot.get("comprobacion", set())
    return {
        "closure_8_ids": sorted(PROTECTED_COMP_CLOSURE_8),
        "exist_in_db": found,
        "in_expanded_protected": in_prot,
        "all_protected": all(in_prot.values()) and all(found.values()),
    }


def _notif_sources_for_residual(conn: Connection, residual_ids: set[int]) -> dict[str, Any]:
    sources: dict[int, list[int]] = {}
    classifications: dict[int, str] = {}
    for iid in sorted(residual_ids):
        row = conn.execute(
            text("SELECT notificacion_id FROM iniciador_ruta WHERE id = :id"), {"id": iid}
        ).fetchone()
        if row and row[0]:
            nid = row[0]
            sources.setdefault(nid, []).append(iid)
    diag_details = {}
    return {
        "notificacion_ids": sorted(sources.keys()),
        "count": len(sources),
        "policy": "NO_DELETE_NO_UPDATE_IN_2C2A",
        "by_notificacion": {str(k): v for k, v in sources.items()},
    }


def run_phase2c2a_manifest_freeze(
    conn: Connection,
    *,
    source_diag_path: Path,
    protected_path: Path,
    phase2c1_manifest_path: Path,
) -> dict[str, Any]:
    """Orquestador freeze manifest FASE 2C.2A."""
    baseline = _baseline_check(conn)
    safe = load_safe_initiators_from_diag(source_diag_path)
    diag = safe["diag"]
    safe_ids = safe["all_ids"]

    stale = [
        iid
        for iid in safe_ids
        if not _scalar(conn, "SELECT COUNT(*) FROM iniciador_ruta WHERE id = :id", {"id": iid})
    ]
    if stale:
        raise ManifestFreezeError(f"missing iniciadores: {stale[:10]}")

    excluded_ini = _excluded_indeterminate_initiators(diag)
    inter_excl = safe_ids & excluded_ini
    if inter_excl:
        raise ManifestFreezeError(f"excluded initiators in safe set: {sorted(inter_excl)[:10]}")

    _validate_residual_classification(diag, safe["residual_ids"])

    phase2c1 = load_manifest(phase2c1_manifest_path)
    rel_26 = {int(x) for x in phase2c1.get("excluded", {}).get("relevamientos_26", [])}
    acts_148 = {int(x) for x in phase2c1.get("excluded", {}).get("blocked_acts_148", [])}
    if len(acts_148) != 148:
        raise ManifestFreezeError(f"blocked_acts_148: {len(acts_148)}")
    if len(rel_26) != 26:
        raise ManifestFreezeError(f"relevamientos_26: {len(rel_26)}")

    for rid in RELEVAMIENTOS_QA_IDS:
        if rid not in rel_26:
            raise ManifestFreezeError(f"QA relevamiento {rid} missing from excluded set")

    _validate_relevamiento_initiators(conn, diag, safe["relevamiento_ids"], rel_26)

    fk_blockers = _incoming_fk_blockers(conn, safe_ids)
    if fk_blockers:
        raise ManifestFreezeError(f"incoming FK blockers: {fk_blockers[:10]}")

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    virtual = VirtualDeleteState()
    virtual.add_explicit("iniciador_ruta", safe_ids)
    closure = protection_closure_check(virtual, prot)
    if not closure.get("valid"):
        raise ManifestFreezeError(f"protected closure: {closure.get('conflicts', [])[:3]}")

    unlock = _simulate_unlock(conn, acts_148, rel_26, safe_ids)
    if unlock["actuaciones"]["unlocked_count"] != 110:
        raise ManifestFreezeError(
            f"acts unlock: {unlock['actuaciones']['unlocked_count']} != 110"
        )
    if unlock["actuaciones"]["blocked_count"] != 38:
        raise ManifestFreezeError(
            f"acts blocked: {unlock['actuaciones']['blocked_count']} != 38"
        )
    if unlock["relevamientos"]["unlocked_count"] != 26:
        raise ManifestFreezeError(
            f"relev unlock: {unlock['relevamientos']['unlocked_count']} != 26"
        )

    comp_reg = _protected_comp_regression(conn, prot)

    users_base = diag.get("users_simulation", {}).get("baseline_post_2c1", {}).get(
        "users_test_fk_free", 802
    )
    users_sim = _users_simulation(conn, users_base, safe_ids)

    ot_ids: set[int] = set()
    for aid in unlock["actuaciones"]["unlocked"]:
        ot = _scalar(conn, "SELECT orden_trabajo_id FROM actuaciones WHERE id = :id", {"id": aid})
        if ot:
            ot_ids.add(ot)

    orphan_notif = diag.get("orphan_docs_reserved", {}).get("notificaciones_36_ORPHAN_CONFIRMED_TEST", [])
    notif_sources = _notif_sources_for_residual(conn, safe["residual_ids"])

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2C2A",
        "phase_name": "safe_test_initiators_residual",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(source_diag_path.resolve()),
        "source_diag_sha256": file_sha256(source_diag_path),
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "safe_set_counts": {
            "iniciador_ruta": EXPECTED_SAFE_TOTAL,
            "residual_acts": EXPECTED_RESIDUAL,
            "relevamientos": EXPECTED_RELEVAMIENTO,
        },
        "breakdown": {
            "residual_acts": sorted(safe["residual_ids"]),
            "residual_acts_by_tipo": _residual_tipo_breakdown(diag, safe["residual_ids"]),
            "relevamiento_RELEVAMIENTO": sorted(safe["relevamiento_ids"]),
        },
        "entities": {
            "iniciador_ruta": [{"id": i} for i in sorted(safe_ids)],
        },
        "delete_order": PHASE2C2A_DELETE_ORDER,
        "forbidden_deletes": {
            "notificacion": 0,
            "comprobacion": 0,
            "actuaciones": 0,
            "relevamiento": 0,
            "orden_trabajo": 0,
        },
        "notificacion_sources_preserved": notif_sources,
        "expected_counts_before": {"iniciador_ruta": BASELINE_POST_2C1["iniciador_ruta"]},
        "expected_counts_after": {"iniciador_ruta": POST_INICIADOR},
        "unchanged_counts": {
            k: v
            for k, v in BASELINE_POST_2C1.items()
            if k != "iniciador_ruta"
        },
        "unlock_expected": {
            "actuaciones": {
                "unlocked": 110,
                "blocked": 38,
                "unlocked_ids": unlock["actuaciones"]["unlocked"],
                "blocked_ids": unlock["actuaciones"]["blocked"],
            },
            "relevamientos": {
                "unlocked": 26,
                "blocked": 0,
                "unlocked_ids": unlock["relevamientos"]["unlocked"],
            },
        },
        "ot_exclusive_future_2c2b": {
            "count": len(ot_ids),
            "orden_trabajo_ids": sorted(ot_ids),
        },
        "excluded": {
            "blocked_initiators_indeterminate": sorted(excluded_ini),
            "blocked_initiators_count": len(excluded_ini),
            "acts_148": sorted(acts_148),
            "relevamientos_26": sorted(rel_26),
            "orphan_notificaciones_36": orphan_notif,
            "orphan_comprobaciones_20": "reserved per 3F.1 for 2C.2C",
        },
        "protected_intersection": 0,
        "protected_closure_detail": closure,
        "protected_closure_valid": closure.get("valid"),
        "protected_comprobacion_regression": comp_reg,
        "users_unlock_simulation": users_sim,
        "otro_relevador_qa": {
            **diag.get("relevamiento_26", {}).get("otro_relevador_qa", {}),
            "current_refs": audit_otro_relevador_qa(conn),
            "future_after_2c2b_relevamiento_delete": {
                "relevador_id": 2,
                "expected_refs": 0,
                "verdict": "FUTURE_CATALOG_DELETE",
                "note": "en 2C.2A los 26 relevamientos permanecen; relevador mantiene refs",
            },
        },
        "validation": {
            "ids_exist": {"iniciador_ruta": {"expected": 155, "found": 155, "missing": 0}},
            "incoming_fk_blockers": [],
            "route_refs": {"ruta_item": 0, "ruta_pool_dia": 0},
            "excluded_intersection": 0,
            "unlock_simulation": unlock,
        },
    }

    manifest["manifest_sha256"] = manifest_sha256(manifest)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3F.2",
        "writes_executed": False,
        "baseline": baseline,
        "manifest": manifest,
        "manifest_sha256": manifest["manifest_sha256"],
        "manifest_path_note": "write via freeze script",
    }


def write_freeze_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
