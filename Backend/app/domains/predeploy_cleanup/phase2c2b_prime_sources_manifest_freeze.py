"""
PREDEPLOY-CLEANUP.3H.3 — congelar execution manifest FASE 2C.2B'
(38 actuaciones CONFIRMADO_TEST + 38 OT EXCLUSIVE_TEST). Solo lectura.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import (
    file_sha256,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import _validate_delete_order_fk
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import PROTECTED_COMP_CLOSURE_8
from app.domains.predeploy_cleanup.phase2c2a_prime_residual_acts_diag import _new_orphan_docs
from app.domains.predeploy_cleanup.phase2c2b_cascade_reconcile import (
    _reconcile_acta_inspeccion_item,
    _reconcile_actuaciones_inspector,
    _reconcile_inspeccion,
    _reconcile_simple_child,
)
from app.domains.predeploy_cleanup.phase2c2b_sources_manifest_freeze import (
    _protected_comp_regression,
    _validate_act_blockers,
    _validate_ot_exclusive,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    load_user_fk_columns,
    protection_closure_check,
)

PHASE2C2B_PRIME_DELETE_ORDER = ["actuaciones", "orden_trabajo"]

EXPECTED_ACTS = 38
EXPECTED_OT = 38
EXPECTED_OLD = 38
EXPECTED_STRUCTURED = 0

EMPTY_ROUTE_IDS = (
    4938,
    4944,
    5195,
    5199,
    5204,
    5245,
    5261,
    5550,
    5560,
    5574,
    6372,
    6461,
)

BASELINE_POST_2C2A_PRIME = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3685,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8001,
    "actuaciones": 8112,
    "denuncia": 417,
    "relevamiento": 4566,
    "orden_trabajo": 8848,
    "inspeccion": 898,
    "actuaciones_inspector": 4180,
    "acta_inspeccion_item": 52,
    "clausura": 69,
    "decomiso": 25,
    "relevamiento_relevador": 525,
}

POST_EXPLICIT = {
    "actuaciones": 8074,
    "orden_trabajo": 8810,
}

USERS_FK_FREE_POST_2C2A_PRIME = 833

EXPECTED_CASCADE_PHYSICAL = {
    "inspeccion": {"physical_rows": 0, "expected_after": 898},
    "actuaciones_inspector": {"physical_rows": 0, "expected_after": 4180},
    "acta_inspeccion_item": {"physical_rows": 0, "expected_after": 52},
    "clausura": {"physical_rows": 0, "expected_after": 69},
    "decomiso": {"physical_rows": 0, "expected_after": 25},
}

FORBIDDEN_MANIFEST_ENTITIES = frozenset(
    {
        "notificacion",
        "comprobacion",
        "oficio",
        "expediente",
        "relevamiento",
        "denuncia",
        "domicilio",
        "users",
        "rubro",
        "relevador",
        "inspector",
        "inspeccion",
        "actuaciones_inspector",
        "acta_inspeccion_item",
        "clausura",
        "decomiso",
        "relevamiento_relevador",
        "iniciador_ruta",
        "ruta_item",
        "ruta_pool_dia",
        "ruta_trabajo",
        "ruta_grupo",
        "ruta_grupo_inspector",
    }
)


class ManifestFreezeError(Exception):
    """Aborta freeze del manifest FASE 2C.2B'."""


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ManifestFreezeError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ManifestFreezeError(f"alembic={alembic}")
    counts = {}
    for table, expected in BASELINE_POST_2C2A_PRIME.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            raise ManifestFreezeError(f"baseline {table}: {actual} != {expected}")
    return {"database": db, "alembic_revision": alembic, "counts": counts}


def load_safe_sets_from_apply_report(apply_path: Path) -> dict[str, Any]:
    """Carga safe sets desde execution report 2C.2A' apply."""
    data = json.loads(apply_path.read_text(encoding="utf-8"))
    future = data["future_2c2b_prime"]
    acts = [int(x) for x in future["unlocked_acts"]["UNLOCKED_ids"]]
    ots = [int(x) for x in future["orden_trabajo_38"]]
    if future["unlocked_acts"]["UNLOCKED"] != EXPECTED_ACTS:
        raise ManifestFreezeError(f"unlocked acts: {future['unlocked_acts']['UNLOCKED']}")
    if future["unlocked_acts"]["STILL_BLOCKED"] != 0:
        raise ManifestFreezeError("STILL_BLOCKED != 0 in apply report")
    if len(acts) != EXPECTED_ACTS or len(set(acts)) != EXPECTED_ACTS:
        raise ManifestFreezeError(f"acts count: {len(acts)}")
    if len(ots) != EXPECTED_OT or len(set(ots)) != EXPECTED_OT:
        raise ManifestFreezeError(f"ot count: {len(ots)}")
    return {
        "actuaciones": set(acts),
        "orden_trabajo": set(ots),
        "apply_data": data,
    }


def _validate_family(diag_3h: dict[str, Any], act_ids: set[int]) -> dict[str, Any]:
    fam = diag_3h["acts_38"]["family"]
    old = {int(x) for x in fam["SET_ACT_OLD"]}
    structured = {int(x) for x in fam.get("SET_ACT_STRUCTURED", [])}
    if len(old) != EXPECTED_OLD or len(structured) != EXPECTED_STRUCTURED:
        raise ManifestFreezeError(f"family: old={len(old)} structured={len(structured)}")
    if old != act_ids:
        raise ManifestFreezeError("family SET_ACT_OLD != safe acts")
    return {
        "SET_ACT_OLD_count": len(old),
        "SET_ACT_STRUCTURED_count": len(structured),
        "SET_ACT_OLD_ids": sorted(old),
    }


def _incoming_fk_to_actuaciones(conn: Connection) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT kcu.TABLE_NAME AS child_table, kcu.COLUMN_NAME AS child_column,
               rc.DELETE_RULE AS delete_rule, rc.UPDATE_RULE AS update_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.REFERENCED_TABLE_NAME = 'actuaciones'
        ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
        """,
    )


def _incoming_fk_to_orden_trabajo(conn: Connection) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT kcu.TABLE_NAME AS child_table, kcu.COLUMN_NAME AS child_column,
               rc.DELETE_RULE AS delete_rule, rc.UPDATE_RULE AS update_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.REFERENCED_TABLE_NAME = 'orden_trabajo'
        ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
        """,
    )


def _recalc_cascades(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    insp = _reconcile_inspeccion(conn, act_ids)
    ai = _reconcile_actuaciones_inspector(conn, act_ids)
    cl = _reconcile_simple_child(conn, "clausura", "actuacion_id", act_ids)
    de = _reconcile_simple_child(conn, "decomiso", "actuacion_id", act_ids)
    aii = _reconcile_acta_inspeccion_item(conn, set(insp["inspeccion_ids"]))
    cascades = {
        "inspeccion": insp,
        "actuaciones_inspector": ai,
        "clausura": cl,
        "decomiso": de,
        "acta_inspeccion_item": aii,
    }
    for tbl, spec in EXPECTED_CASCADE_PHYSICAL.items():
        row = cascades[tbl]
        if row["physical_rows"] != spec["physical_rows"]:
            raise ManifestFreezeError(
                f"cascade {tbl}: physical {row['physical_rows']} != {spec['physical_rows']}"
            )
        if row.get("expected_after") != spec["expected_after"]:
            raise ManifestFreezeError(f"cascade {tbl} after mismatch")
    if insp["physical_rows"] > 0:
        raise ManifestFreezeError(f"inspeccion cascade {insp['physical_rows']} > 0, reconcile required")
    return cascades


def _collect_parent_documents(
    conn: Connection,
    act_ids: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    notif_ids: set[int] = set()
    comp_ids: set[int] = set()
    act_doc_map: list[dict[str, Any]] = []
    for aid in sorted(act_ids):
        row = conn.execute(
            text(
                "SELECT id, notificacion_id, comprobacion_id FROM actuaciones WHERE id = :id"
            ),
            {"id": aid},
        ).fetchone()
        if not row:
            raise ManifestFreezeError(f"act {aid} missing")
        nid, cid = row[1], row[2]
        if nid:
            notif_ids.add(int(nid))
        if cid:
            comp_ids.add(int(cid))
        act_doc_map.append(
            {
                "actuacion_id": aid,
                "notificacion_id": nid,
                "comprobacion_id": cid,
            }
        )
    prot_notif = notif_ids & prot.get("notificacion", set())
    prot_comp = comp_ids & prot.get("comprobacion", set())
    return {
        "notificacion_ids": sorted(notif_ids),
        "comprobacion_ids": sorted(comp_ids),
        "by_actuacion": act_doc_map,
        "preserve_policy": "NO_DELETE_NO_UPDATE",
        "protected_parent_notificaciones": sorted(prot_notif),
        "protected_parent_comprobaciones": sorted(prot_comp),
        "PRESERVE_PROTECTED_PARENT": bool(prot_notif or prot_comp),
    }


def _load_source_documents(apply_data: dict[str, Any], prime_manifest: dict[str, Any]) -> dict[str, Any]:
    preserved = apply_data.get("preserved_sources", {})
    excluded = prime_manifest.get("excluded", {})
    return {
        "direct_notificaciones_29": preserved.get("direct_notificaciones_29", []),
        "source_notificaciones_119": excluded.get("source_notificaciones_119", []),
        "oficio_chains": preserved.get("oficio_chains", []),
        "preserve_policy": "NO_DELETE from 2C.2A' wave",
    }


def _verify_empty_routes(conn: Connection) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for rtid in EMPTY_ROUTE_IDS:
        if not _scalar(conn, "SELECT COUNT(*) FROM ruta_trabajo WHERE id = :id", {"id": rtid}):
            raise ManifestFreezeError(f"empty route {rtid} missing")
        refs = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rtid}")
        if refs:
            raise ManifestFreezeError(f"route {rtid} has {len(refs)} ruta_item refs")
        routes.append({"ruta_trabajo_id": rtid, "ruta_item_refs": 0})
    return routes


def _users_simulation(conn: Connection, act_ids: set[int], ot_ids: set[int]) -> dict[str, Any]:
    fk_columns = load_user_fk_columns(conn)
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    deleted_tables = {"actuaciones": act_ids, "orden_trabajo": ot_ids}
    base_free = USERS_FK_FREE_POST_2C2A_PRIME
    free_after = 0
    still_blocked: list[int] = []
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                if r[0] not in deleted_tables.get(table, set()):
                    blocked = True
                    break
            if blocked:
                break
        if not blocked:
            free_after += 1
        else:
            still_blocked.append(uid)
    return {
        "users_test_fk_free_baseline_post_2c2a_prime": base_free,
        "users_test_fk_free_after_2c2b_prime": free_after,
        "users_additionally_unlocked": free_after - base_free,
        "users_test_still_blocked": len(still_blocked),
    }


def run_phase2c2b_prime_manifest_freeze(
    conn: Connection,
    *,
    apply_2c2a_prime_path: Path,
    diag_3h_path: Path,
    protected_path: Path,
    prime_manifest_path: Path,
) -> dict[str, Any]:
    """Orquestador freeze manifest FASE 2C.2B'."""
    baseline = _baseline_check(conn)
    loaded = load_safe_sets_from_apply_report(apply_2c2a_prime_path)
    apply_data = loaded["apply_data"]
    act_ids = loaded["actuaciones"]
    ot_ids = loaded["orden_trabajo"]

    diag_3h = json.loads(diag_3h_path.read_text(encoding="utf-8"))
    prime_manifest = load_manifest(prime_manifest_path)
    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))

    diag_acts = {int(x) for x in diag_3h["acts_38"]["ids"]}
    diag_ots = {int(x) for x in diag_3h["safe_sets"]["SAFE_OT_AFTER_PRIME"]}
    if act_ids != diag_acts:
        raise ManifestFreezeError("acts != diag 3H")
    if ot_ids != diag_ots:
        raise ManifestFreezeError("ots != diag 3H SAFE_OT_AFTER_PRIME")

    for entity, ids in (("actuaciones", act_ids), ("orden_trabajo", ot_ids)):
        stale = validate_ids_exist(conn, entity, ids, label=entity)
        if stale:
            raise ManifestFreezeError(f"missing {entity}: {stale[:5]}")

    family = _validate_family(diag_3h, act_ids)
    _validate_act_blockers(conn, act_ids)

    if act_ids & prot.get("actuaciones", set()):
        raise ManifestFreezeError("protected act intersection")

    ot_val = _validate_ot_exclusive(conn, ot_ids, act_ids, prot)
    cascades = _recalc_cascades(conn, act_ids)
    parent_docs = _collect_parent_documents(conn, act_ids, prot)
    source_docs = _load_source_documents(apply_data, prime_manifest)

    orphan_36 = {int(x) for x in prime_manifest["excluded"]["orphan_notificaciones_36"]}
    orphan_20 = {int(x) for x in prime_manifest["excluded"]["orphan_comprobaciones_20"]}
    new_orphans = _new_orphan_docs(conn, act_ids, orphan_36, orphan_20)
    new_notif = new_orphans["NEW_ORPHAN_TEST_DOCUMENTS"]["notificaciones"]
    new_comp = new_orphans["NEW_ORPHAN_TEST_DOCUMENTS"]["comprobaciones"]

    comp_reg = _protected_comp_regression(conn, prot)
    if not comp_reg["all_protected"]:
        raise ManifestFreezeError("protected comprobacion regression")

    empty_routes = _verify_empty_routes(conn)
    act_fk = _incoming_fk_to_actuaciones(conn)
    ot_fk = _incoming_fk_to_orden_trabajo(conn)

    virtual = VirtualDeleteState()
    virtual.add_explicit("actuaciones", act_ids)
    virtual.add_explicit("orden_trabajo", ot_ids)
    closure = protection_closure_check(virtual, prot)
    if not closure.get("valid"):
        raise ManifestFreezeError(f"protected closure: {closure.get('conflicts', [])[:3]}")

    fk_valid = _validate_delete_order_fk(PHASE2C2B_PRIME_DELETE_ORDER, load_fk_edges(conn))
    if not fk_valid.get("valid"):
        raise ManifestFreezeError(f"delete order: {fk_valid.get('violations')}")

    users_sim = _users_simulation(conn, act_ids, ot_ids)

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2C2B_PRIME",
        "phase_name": "safe_actuaciones_and_ot_exclusive_test_residual",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_apply_2c2a_prime_path": str(apply_2c2a_prime_path.resolve()),
        "source_apply_2c2a_prime_sha256": file_sha256(apply_2c2a_prime_path),
        "source_diag_3h_path": str(diag_3h_path.resolve()),
        "source_diag_3h_sha256": file_sha256(diag_3h_path),
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "safe_set_counts": {
            "actuaciones": EXPECTED_ACTS,
            "orden_trabajo": EXPECTED_OT,
        },
        "act_family_breakdown": family,
        "entities": {
            "actuaciones": sorted(act_ids),
            "orden_trabajo": sorted(ot_ids),
        },
        "delete_order": PHASE2C2B_PRIME_DELETE_ORDER,
        "forbidden_deletes": {e: 0 for e in FORBIDDEN_MANIFEST_ENTITIES},
        "expected_counts_before": {
            "actuaciones": BASELINE_POST_2C2A_PRIME["actuaciones"],
            "orden_trabajo": BASELINE_POST_2C2A_PRIME["orden_trabajo"],
        },
        "expected_counts_after": POST_EXPLICIT,
        "unchanged_counts": {
            k: v
            for k, v in BASELINE_POST_2C2A_PRIME.items()
            if k not in POST_EXPLICIT
        },
        "expected_cascades": cascades,
        "preserve_parent_documents": parent_docs,
        "preserve_source_documents": source_docs,
        "future_orphan_documents_after_apply": {
            "NEW_ORPHAN_NOTIFICACION_AFTER_2C2B_PRIME": new_notif,
            "NEW_ORPHAN_COMPROBACION_AFTER_2C2B_PRIME": new_comp,
            "policy": "reserved for post-2C.2B' audit; NOT 2C.2C yet",
        },
        "empty_routes_residual_12": empty_routes,
        "excluded": {
            "empty_routes_12": list(EMPTY_ROUTE_IDS),
            "orphan_notificaciones_36": sorted(orphan_36),
            "orphan_comprobaciones_20": sorted(orphan_20),
            "future_orphan_notif_candidates": new_notif,
            "future_orphan_comp_candidates": new_comp,
            "source_notificaciones_119": source_docs["source_notificaciones_119"],
            "oficio_chains": source_docs["oficio_chains"],
            "users": "NO_DELETE",
            "catalogos": "NO_DELETE",
            "domicilios_contribuyentes": "NO_DELETE",
        },
        "protected_intersection": 0,
        "protected_closure_detail": closure,
        "protected_comprobacion_regression": comp_reg,
        "users_unlock_simulation": users_sim,
        "validation": {
            "ids_exist": {
                "actuaciones": {"expected": EXPECTED_ACTS, "found": EXPECTED_ACTS, "missing": 0},
                "orden_trabajo": {"expected": EXPECTED_OT, "found": EXPECTED_OT, "missing": 0},
            },
            "act_blockers_zero": True,
            "ot_exclusive": ot_val,
            "incoming_fk_actuaciones": act_fk,
            "incoming_fk_orden_trabajo": ot_fk,
            "delete_order_validated": fk_valid,
            "cascade_physical_total": sum(c["physical_rows"] for c in cascades.values()),
        },
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3H.3",
        "writes_executed": False,
        "baseline": baseline,
        "manifest": manifest,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def write_freeze_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
