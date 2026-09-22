"""
PREDEPLOY-CLEANUP.3J.1 — congelar execution manifest ROUTE-RESIDUAL
(12 ruta_trabajo CONFIRMADO_TEST_ROUTE). Solo lectura.
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
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.route_residual_diag import (
    BLOCKED_NOTIF_25,
    FUTURE_EXPEDIENTE_27,
    ROUTE_IDS_12,
    USERS_FK_FREE_POST_3I,
    _admin_graph_guard,
    _cascade_on_delete,
    _incoming_fk_edges,
    load_deleted_item_provenance,
)
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _fetch_ids,
    load_user_fk_columns,
    protection_closure_check,
)

ROUTE_RESIDUAL_DELETE_ORDER = ["ruta_trabajo"]

EXPECTED_SAFE_ROUTES = 12

SAFE_RUTA_TRABAJO_RESIDUAL = ROUTE_IDS_12

PROVENANCE_ROUTE_TO_ITEM_ACT: dict[int, dict[str, int]] = {
    4938: {"deleted_ruta_item_id": 5376, "deleted_actuacion_id": 6999},
    4944: {"deleted_ruta_item_id": 5382, "deleted_actuacion_id": 7025},
    5195: {"deleted_ruta_item_id": 5637, "deleted_actuacion_id": 7458},
    5199: {"deleted_ruta_item_id": 5641, "deleted_actuacion_id": 7493},
    5204: {"deleted_ruta_item_id": 5646, "deleted_actuacion_id": 7507},
    5245: {"deleted_ruta_item_id": 5686, "deleted_actuacion_id": 7577},
    5261: {"deleted_ruta_item_id": 5701, "deleted_actuacion_id": 7619},
    5550: {"deleted_ruta_item_id": 5970, "deleted_actuacion_id": 7932},
    5560: {"deleted_ruta_item_id": 5980, "deleted_actuacion_id": 7964},
    5574: {"deleted_ruta_item_id": 6003, "deleted_actuacion_id": 8015},
    6372: {"deleted_ruta_item_id": 6889, "deleted_actuacion_id": 9612},
    6461: {"deleted_ruta_item_id": 6972, "deleted_actuacion_id": 9942},
}

BASELINE_POST_3I2 = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3685,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8001,
    "actuaciones": 8074,
    "denuncia": 417,
    "relevamiento": 4566,
    "orden_trabajo": 8810,
    "notificacion": 2478,
    "comprobacion": 1530,
    "inspeccion": 898,
    "actuaciones_inspector": 4180,
    "acta_inspeccion_item": 52,
    "clausura": 69,
    "decomiso": 25,
    "relevamiento_relevador": 525,
}

POST_EXPLICIT = {"ruta_trabajo": 2703}

FORBIDDEN_MANIFEST_ENTITIES = frozenset(
    {
        "ruta_grupo",
        "ruta_grupo_inspector",
        "ruta_item",
        "ruta_pool_dia",
        "iniciador_ruta",
        "actuaciones",
        "orden_trabajo",
        "notificacion",
        "comprobacion",
        "oficio",
        "expediente",
        "users",
        "relevamiento",
        "denuncia",
        "domicilio",
        "rubro",
        "relevador",
        "inspector",
    }
)


class ManifestFreezeError(Exception):
    """Aborta freeze del manifest ROUTE-RESIDUAL."""


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check_extended(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ManifestFreezeError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ManifestFreezeError(f"alembic={alembic}")
    counts: dict[str, int] = {}
    for table, expected in BASELINE_POST_3I2.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            raise ManifestFreezeError(f"baseline {table}: {actual} != {expected}")
    return {"database": db, "alembic_revision": alembic, "counts": counts, "baseline_ok": True, "drift": []}


def load_safe_sets_from_diag(diag_path: Path) -> dict[str, Any]:
    """Carga y valida safe sets desde diagnóstico 3J."""
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    if data.get("writes_executed") is not False:
        raise ManifestFreezeError("source diag writes_executed != false")

    safe = data["safe_sets"]
    if len(safe["SAFE_RUTA_TRABAJO_RESIDUAL"]) != EXPECTED_SAFE_ROUTES:
        raise ManifestFreezeError(f"safe routes count: {len(safe['SAFE_RUTA_TRABAJO_RESIDUAL'])}")
    if safe["SAFE_RUTA_GRUPO_RESIDUAL"]:
        raise ManifestFreezeError("SAFE_RUTA_GRUPO_RESIDUAL must be empty")
    if safe["SAFE_RUTA_GRUPO_INSPECTOR_RESIDUAL"]:
        raise ManifestFreezeError("SAFE_RUTA_GRUPO_INSPECTOR_RESIDUAL must be empty")
    if safe["SAFE_RUTA_POOL_RESIDUAL"]:
        raise ManifestFreezeError("SAFE_RUTA_POOL_RESIDUAL must be empty")
    if safe["BLOCKED_ROUTES"]:
        raise ManifestFreezeError("BLOCKED_ROUTES must be empty")

    route_ids = set(safe["SAFE_RUTA_TRABAJO_RESIDUAL"])
    if route_ids != set(SAFE_RUTA_TRABAJO_RESIDUAL):
        raise ManifestFreezeError("safe route IDs != frozen list")

    buckets = data.get("classification_buckets", {})
    if buckets.get("CONFIRMADO_TEST_ROUTE") != EXPECTED_SAFE_ROUTES:
        raise ManifestFreezeError(f"classification count: {buckets}")

    return {"diag_data": data, "safe_ruta_trabajo": route_ids}


def _validate_operational_empty(conn: Connection, rtid: int) -> dict[str, Any]:
    """Valida vacío operacional completo para una ruta."""
    item_refs = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rtid}")
    grupo_refs = _fetch_ids(conn, f"SELECT id FROM ruta_grupo WHERE ruta_trabajo_id = {rtid}")
    rgi_count = 0
    if grupo_refs:
        ph = ",".join(str(i) for i in grupo_refs)
        rgi_count = int(
            _scalar(conn, f"SELECT COUNT(*) FROM ruta_grupo_inspector WHERE ruta_grupo_id IN ({ph})") or 0
        )
    pool_direct = int(
        _scalar(conn, "SELECT COUNT(*) FROM ruta_pool_dia WHERE ruta_trabajo_id = :id", {"id": rtid}) or 0
    )
    pool_via_item = int(
        _scalar(
            conn,
            """
            SELECT COUNT(*) FROM ruta_pool_dia
            WHERE ruta_item_id IN (SELECT id FROM ruta_item WHERE ruta_trabajo_id = :id)
            """,
            {"id": rtid},
        )
        or 0
    )
    result = {
        "ruta_trabajo_id": rtid,
        "ruta_item_refs": len(item_refs),
        "ruta_grupo_refs": len(grupo_refs),
        "ruta_grupo_inspector_refs": rgi_count,
        "ruta_pool_dia_refs": pool_direct + pool_via_item,
    }
    if any(
        result[k] > 0
        for k in (
            "ruta_item_refs",
            "ruta_grupo_refs",
            "ruta_grupo_inspector_refs",
            "ruta_pool_dia_refs",
        )
    ):
        raise ManifestFreezeError(f"route {rtid} not empty: {result}")
    return result


def _validate_child_physical_rows(conn: Connection, route_ids: set[int]) -> dict[str, Any]:
    """Valida 0 filas físicas hijas CASCADE/SET NULL."""
    casc = _cascade_on_delete(conn, "ruta_trabajo", route_ids)
    if casc["cascade_total"] != 0 or casc["set_null_total"] != 0:
        raise ManifestFreezeError(f"cascade physical: {casc}")

    ph = ",".join(str(i) for i in sorted(route_ids))
    physical = {
        "ruta_grupo": int(
            _scalar(conn, f"SELECT COUNT(*) FROM ruta_grupo WHERE ruta_trabajo_id IN ({ph})") or 0
        ),
        "ruta_item": int(
            _scalar(conn, f"SELECT COUNT(*) FROM ruta_item WHERE ruta_trabajo_id IN ({ph})") or 0
        ),
        "ruta_pool_dia": int(
            _scalar(conn, f"SELECT COUNT(*) FROM ruta_pool_dia WHERE ruta_trabajo_id IN ({ph})") or 0
        ),
    }
    grupo_ids = _fetch_ids(conn, f"SELECT id FROM ruta_grupo WHERE ruta_trabajo_id IN ({ph})")
    rgi = 0
    if grupo_ids:
        gph = ",".join(str(i) for i in grupo_ids)
        rgi = int(
            _scalar(conn, f"SELECT COUNT(*) FROM ruta_grupo_inspector WHERE ruta_grupo_id IN ({gph})") or 0
        )
    physical["ruta_grupo_inspector"] = rgi

    for tbl, n in physical.items():
        if n != 0:
            raise ManifestFreezeError(f"child physical {tbl}: {n}")

    return {
        "ruta_grupo": {"physical_rows": 0},
        "ruta_grupo_inspector": {"physical_rows": 0},
        "ruta_item": {"physical_rows": 0},
        "ruta_pool_dia": {"set_null_rows": 0},
        "other": {"physical_rows": 0},
        "cascade_detail": casc,
    }


def _validate_provenance(
    prime_prov: dict[int, dict[str, Any]],
    route_ids: set[int],
) -> list[dict[str, Any]]:
    """Valida provenance 1:1 con mapping congelado."""
    links: list[dict[str, Any]] = []
    for rtid in sorted(route_ids):
        expected = PROVENANCE_ROUTE_TO_ITEM_ACT[rtid]
        actual = prime_prov.get(rtid, {})
        if actual.get("deleted_ruta_item_id") != expected["deleted_ruta_item_id"]:
            raise ManifestFreezeError(f"provenance item mismatch route {rtid}")
        if actual.get("actuacion_id") != expected["deleted_actuacion_id"]:
            raise ManifestFreezeError(f"provenance act mismatch route {rtid}")
        links.append(
            {
                "ruta_trabajo_id": rtid,
                "deleted_ruta_item_id": expected["deleted_ruta_item_id"],
                "deleted_actuacion_id": expected["deleted_actuacion_id"],
                "classification": "CONFIRMADO_TEST_ROUTE",
                "note": "created_by_user_id=1 is admin audit field, not evidence of real data",
            }
        )
    return links


def _users_simulation(conn: Connection, safe_rt: set[int]) -> dict[str, Any]:
    fk_columns = load_user_fk_columns(conn)
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    free_after = 0
    still = 0
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                if table == "ruta_trabajo" and r[0] in safe_rt:
                    continue
                blocked = True
                break
            if blocked:
                break
        if blocked:
            still += 1
        else:
            free_after += 1
    return {
        "users_test_fk_free_baseline_post_3i": USERS_FK_FREE_POST_3I,
        "users_test_fk_free_after_route_cleanup": free_after,
        "users_additionally_unlocked": free_after - USERS_FK_FREE_POST_3I,
        "users_test_still_blocked": still,
        "policy": "NO_DELETE users; admin user_id=1 not deleted",
    }


def run_route_residual_manifest_freeze(
    conn: Connection,
    *,
    diag_path: Path,
    protected_path: Path,
    prime_manifest_path: Path,
    manifest_paths: list[Path],
) -> dict[str, Any]:
    """Orquestador freeze manifest ROUTE-RESIDUAL."""
    baseline = _baseline_check_extended(conn)
    loaded = load_safe_sets_from_diag(diag_path)
    safe_rt = loaded["safe_ruta_trabajo"]

    stale = validate_ids_exist(conn, "ruta_trabajo", safe_rt, label="ruta_trabajo")
    if stale:
        raise ManifestFreezeError(f"missing routes: {stale}")

    prime_prov = load_deleted_item_provenance(prime_manifest_path)
    provenance_links = _validate_provenance(prime_prov, safe_rt)

    emptiness = [_validate_operational_empty(conn, rtid) for rtid in sorted(safe_rt)]
    expected_cascades = _validate_child_physical_rows(conn, safe_rt)

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    if safe_rt & prot.get("ruta_trabajo", set()):
        raise ManifestFreezeError("protected ruta_trabajo intersection")

    virtual = VirtualDeleteState()
    virtual.add_explicit("ruta_trabajo", safe_rt)
    closure = protection_closure_check(virtual, prot)
    if not closure.get("valid"):
        raise ManifestFreezeError(f"protected closure: {closure.get('conflicts', [])[:3]}")

    fk_valid = _validate_delete_order_fk(ROUTE_RESIDUAL_DELETE_ORDER, load_fk_edges(conn))
    if not fk_valid.get("valid"):
        raise ManifestFreezeError(f"delete order: {fk_valid.get('violations')}")

    known = _load_known_test_ids_from_manifests(manifest_paths)
    test_guard = _known_test_guard(conn, known)
    if not test_guard["guard_ok"]:
        raise ManifestFreezeError(
            f"known test guard: acts={test_guard['known_test_act_ids_remaining_count']}"
        )

    admin_guard = _admin_graph_guard(conn)
    if admin_guard["blocked_notificaciones_25_present"] != 25:
        raise ManifestFreezeError("admin graph blocked notifs")
    if not admin_guard["comprobacion_2289_present"]:
        raise ManifestFreezeError("comprobacion 2289 missing")
    if admin_guard["future_expedientes_27_present"] != 27:
        raise ManifestFreezeError("expedientes 27 missing")
    if not admin_guard["oficio_1662_present"]:
        raise ManifestFreezeError("oficio 1662 missing")

    users_sim = _users_simulation(conn, safe_rt)
    if users_sim["users_additionally_unlocked"] != 0:
        raise ManifestFreezeError("users_additionally_unlocked != 0")

    fk_graph = {"ruta_trabajo": _incoming_fk_edges(conn, "ruta_trabajo")}

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "ROUTE_RESIDUAL",
        "phase_name": "confirmado_test_route_wrappers_post_2c2a_prime",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(diag_path.resolve()),
        "source_diag_sha256": file_sha256(diag_path),
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "safe_set_counts": {
            "ruta_trabajo": EXPECTED_SAFE_ROUTES,
            "ruta_grupo": 0,
            "ruta_grupo_inspector": 0,
            "ruta_pool_dia": 0,
        },
        "classification": {
            "confirmado_test_route": EXPECTED_SAFE_ROUTES,
        },
        "entities": {
            "ruta_trabajo": sorted(safe_rt),
        },
        "delete_order": ROUTE_RESIDUAL_DELETE_ORDER,
        "forbidden_deletes": {e: 0 for e in FORBIDDEN_MANIFEST_ENTITIES},
        "expected_counts_before": {
            "ruta_trabajo": BASELINE_POST_3I2["ruta_trabajo"],
        },
        "expected_counts_after": POST_EXPLICIT,
        "unchanged_counts": {
            k: v for k, v in BASELINE_POST_3I2.items() if k != "ruta_trabajo"
        },
        "provenance": {
            "route_to_deleted_item": [
                {"ruta_trabajo_id": l["ruta_trabajo_id"], "deleted_ruta_item_id": l["deleted_ruta_item_id"]}
                for l in provenance_links
            ],
            "route_to_deleted_act": [
                {"ruta_trabajo_id": l["ruta_trabajo_id"], "deleted_actuacion_id": l["deleted_actuacion_id"]}
                for l in provenance_links
            ],
            "full_links": provenance_links,
            "created_by_admin_note": "created_by_user_id=1 is audit metadata, not real-data evidence",
        },
        "operational_emptiness_revalidated": emptiness,
        "expected_cascades": expected_cascades,
        "expected_set_null": {
            "ruta_pool_dia": {"set_null_rows": 0},
            "set_null_total": 0,
        },
        "excluded": {
            "ruta_grupo": "NO_DELETE — safe set empty",
            "ruta_grupo_inspector": "NO_DELETE — safe set empty",
            "ruta_item": "NO_DELETE — already removed in 2C.2A'",
            "ruta_pool_dia": "NO_DELETE — safe set empty",
            "iniciador_ruta": "NO_DELETE",
            "admin_graph": "NO_DELETE",
            "users": "NO_DELETE",
            "catalogs": "NO_DELETE",
            "operational_entities": "NO_DELETE",
        },
        "preserve": {
            "admin_graph_25_notificaciones": sorted(BLOCKED_NOTIF_25),
            "comprobacion_2289": 2289,
            "expedientes_27": sorted(FUTURE_EXPEDIENTE_27),
            "oficio_1662": 1662,
            "policy": "IDs in preserve MUST NOT appear in entities DELETE",
        },
        "fk_graph": fk_graph,
        "known_test_guards": {
            "acts_remaining": test_guard["known_test_act_ids_remaining_count"],
            "ot_remaining": test_guard["known_test_ot_ids_remaining_count"],
            "guard_ok": test_guard["guard_ok"],
            "detail": test_guard,
        },
        "admin_graph_guard": admin_guard,
        "users_simulation": users_sim,
        "protected_intersection": 0,
        "protected_closure_detail": closure,
        "validation": {
            "ids_exist": {
                "ruta_trabajo": {
                    "expected": EXPECTED_SAFE_ROUTES,
                    "found": EXPECTED_SAFE_ROUTES,
                    "missing": 0,
                },
            },
            "operational_empty": True,
            "child_physical_zero": True,
            "delete_order_validated": fk_valid,
            "no_child_entities_in_manifest": True,
        },
        "document_cleanup_policy": (
            "DELETE only CONFIRMADO_TEST_ROUTE wrappers with zero operational children. "
            "NOT delete based on created_by_user_id=1 alone."
        ),
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3J.1",
        "writes_executed": False,
        "baseline": baseline,
        "manifest": manifest,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def write_freeze_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
