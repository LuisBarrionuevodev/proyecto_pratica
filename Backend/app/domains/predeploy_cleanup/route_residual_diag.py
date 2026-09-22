"""
PREDEPLOY-CLEANUP.3J-DIAG — ROUTE-RESIDUAL-CLEANUP auditoría 12 rutas vacías post-prime.
Solo SELECT. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import _validate_delete_order_fk
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    load_user_fk_columns,
    protection_closure_check,
)

ROUTE_IDS_12 = (
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

DELETED_RUTA_ITEM_IDS = (
    5376,
    5382,
    5637,
    5641,
    5646,
    5686,
    5701,
    5970,
    5980,
    6003,
    6889,
    6972,
)

BLOCKED_NOTIF_25 = (
    1603,
    1606,
    1607,
    1663,
    1665,
    1785,
    1786,
    1787,
    1884,
    1885,
    1888,
    2090,
    2340,
    2500,
    2589,
    2620,
    2725,
    2728,
    2744,
    2754,
    2755,
    2756,
    2799,
    2856,
    2860,
)

FUTURE_EXPEDIENTE_27 = (
    1972,
    1975,
    1976,
    1985,
    1987,
    2073,
    2074,
    2075,
    2139,
    2140,
    2141,
    2334,
    2761,
    2900,
    2914,
    2942,
    2980,
    2983,
    2991,
    3006,
    3007,
    3008,
    3034,
    3040,
    3044,
    3103,
    3104,
)

USERS_FK_FREE_POST_3I = 833

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
    "relevamiento": 4566,
    "orden_trabajo": 8810,
    "notificacion": 2478,
    "comprobacion": 1530,
}

PROPOSED_DELETE_ORDER = [
    "ruta_grupo_inspector",
    "ruta_grupo",
    "ruta_trabajo",
]


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _incoming_fk_edges(conn: Connection, parent_table: str) -> list[dict[str, Any]]:
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
          AND kcu.REFERENCED_TABLE_NAME = :parent
        ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
        """,
        {"parent": parent_table},
    )


def _cascade_on_delete(conn: Connection, parent_table: str, ids: set[int]) -> dict[str, Any]:
    cascades: dict[str, int] = {}
    set_nulls: dict[str, int] = {}
    for edge in _incoming_fk_edges(conn, parent_table):
        if edge["delete_rule"] not in ("CASCADE", "SET NULL"):
            continue
        tbl, col = edge["child_table"], edge["child_column"]
        total = 0
        for chunk in _chunk_ids(ids, 300):
            ph = ",".join(str(i) for i in chunk)
            total += int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN ({ph})") or 0)
        if total:
            bucket = cascades if edge["delete_rule"] == "CASCADE" else set_nulls
            bucket[f"{parent_table}->{tbl}.{col}"] = total
    return {
        "cascade_physical": cascades,
        "set_null_physical": set_nulls,
        "cascade_total": sum(cascades.values()),
        "set_null_total": sum(set_nulls.values()),
    }


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts = {t: _count(conn, t) for t in BASELINE_POST_3I2}
    drift = [f"{t}: {counts[t]} != {e}" for t, e in BASELINE_POST_3I2.items() if counts[t] != e]
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": not drift,
        "drift": drift,
    }


def load_deleted_item_provenance(prime_manifest_path: Path) -> dict[int, dict[str, Any]]:
    """Carga metadata de los 12 ruta_item eliminados en 2C.2A'."""
    data = load_manifest(prime_manifest_path)
    by_route: dict[int, dict[str, Any]] = {}
    for item in data["entities"]["ruta_item"]:
        rtid = int(item["ruta_trabajo_id"])
        by_route[rtid] = {
            "deleted_ruta_item_id": int(item["id"]),
            "iniciador_ruta_id": item.get("iniciador_ruta_id"),
            "actuacion_id": item.get("actuacion_id"),
            "estado_ruta_item": item.get("estado_ruta_item"),
            "estado_ejecucion": item.get("estado_ejecucion"),
            "created_by_user_id": item.get("created_by_user_id"),
            "ruta_grupo_id": item.get("ruta_grupo_id"),
            "wave": "2C.2A_PRIME",
            "manifest_classification": "SAFE_TEST_WRAPPER_ITEM",
        }
    expected_routes = set(ROUTE_IDS_12)
    if set(by_route.keys()) != expected_routes:
        missing = expected_routes - set(by_route.keys())
        extra = set(by_route.keys()) - expected_routes
        raise ValueError(f"prime manifest route mapping mismatch: missing={missing} extra={extra}")
    return by_route


def _is_test_user(conn: Connection, user_id: int) -> bool:
    return bool(
        _scalar(
            conn,
            f"SELECT COUNT(*) FROM users u WHERE u.id = :uid AND ({SQL_TEST_USER_WHERE})",
            {"uid": user_id},
        )
    )


def _classify_grupo(conn: Connection, grupo: dict[str, Any], route_rtid: int) -> str:
    gid = grupo["id"]
    item_refs = len(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_grupo_id = {gid}"))
    if item_refs > 0:
        return "STILL_USED"
    pool_refs = int(
        _scalar(
            conn,
            "SELECT COUNT(*) FROM ruta_pool_dia WHERE ruta_trabajo_id = :rtid",
            {"rtid": route_rtid},
        )
        or 0
    )
    if pool_refs > 0:
        return "STILL_USED"
    if grupo.get("deleted_at"):
        return "EMPTY_TEST_GROUP"
    return "EMPTY_TEST_GROUP"


def _audit_route(
    conn: Connection,
    rtid: int,
    deleted_prov: dict[str, Any],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT id, fecha, turno, estado_ruta, numero, observaciones,
                   created_by_user_id, created_at, updated_at
            FROM ruta_trabajo WHERE id = :id
            """
        ),
        {"id": rtid},
    ).fetchone()
    if not row:
        return {
            "ruta_trabajo_id": rtid,
            "exists": False,
            "classification": "MISSING",
        }

    prov = dict(row._mapping)
    item_refs = sorted(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rtid}"))
    pool_direct = _rows(
        conn,
        """
        SELECT id, iniciador_ruta_id, ruta_trabajo_id, ruta_item_id, estado, origen_tipo
        FROM ruta_pool_dia WHERE ruta_trabajo_id = :rtid
        """,
        {"rtid": rtid},
    )
    pool_via_item = _rows(
        conn,
        """
        SELECT rp.id, rp.iniciador_ruta_id, rp.ruta_trabajo_id, rp.ruta_item_id, rp.estado
        FROM ruta_pool_dia rp
        WHERE rp.ruta_item_id IN (
            SELECT id FROM ruta_item WHERE ruta_trabajo_id = :rtid
        )
        """,
        {"rtid": rtid},
    )
    grupos = _rows(
        conn,
        """
        SELECT id, nombre, estado, created_by_user_id, created_at, updated_at, deleted_at
        FROM ruta_grupo WHERE ruta_trabajo_id = :rtid
        """,
        {"rtid": rtid},
    )

    grupo_details: list[dict[str, Any]] = []
    all_rgi: list[dict[str, Any]] = []
    for g in grupos:
        gid = g["id"]
        inspectors = _rows(
            conn,
            """
            SELECT rgi.id, rgi.ruta_grupo_id, rgi.inspector_id, rgi.created_by_user_id,
                   i.nombre AS inspector_nombre
            FROM ruta_grupo_inspector rgi
            JOIN inspector i ON i.id = rgi.inspector_id
            WHERE rgi.ruta_grupo_id = :gid
            """,
            {"gid": gid},
        )
        gclass = _classify_grupo(conn, g, rtid)
        grupo_details.append(
            {
                **g,
                "classification": gclass,
                "ruta_item_refs": len(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_grupo_id = {gid}")),
                "ruta_grupo_inspector_rows": len(inspectors),
                "inspectors": inspectors,
            }
        )
        all_rgi.extend(inspectors)

    fk_refs = _incoming_fk_surviving(conn, "ruta_trabajo", rtid)
    prot_hit = rtid in prot.get("ruta_trabajo", set())
    grupo_prot = [g["id"] for g in grupos if g["id"] in prot.get("ruta_grupo", set())]

    truly_empty = (
        len(item_refs) == 0
        and len(pool_direct) == 0
        and len(pool_via_item) == 0
        and all(g["classification"] == "EMPTY_TEST_GROUP" for g in grupo_details)
    )

    act_id = deleted_prov.get("actuacion_id")
    act_exists = bool(
        act_id and _scalar(conn, "SELECT COUNT(*) FROM actuaciones WHERE id = :id", {"id": act_id})
    )

    classification = "INDETERMINATE"
    reasons: list[str] = []
    if not prov:
        classification = "MISSING"
    elif prot_hit or grupo_prot:
        classification = "PROTECTED"
        reasons.append("protected_graph")
    elif not truly_empty:
        classification = "STILL_USED"
        reasons.append("not_fully_empty")
    elif deleted_prov and not act_exists:
        classification = "CONFIRMADO_TEST_ROUTE"
        reasons.append("deleted_test_item_2c2a_prime")
        reasons.append("actuacion_source_deleted_2c2b_prime")
    else:
        classification = "INDETERMINATE"
        reasons.append("needs_manual_review")

    creator_test = _is_test_user(conn, int(prov["created_by_user_id"]))

    return {
        "ruta_trabajo_id": rtid,
        "exists": True,
        "provenance": {
            **{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in prov.items()},
            "created_by_is_test_user": creator_test,
        },
        "deleted_item_2c2a_prime": deleted_prov,
        "emptiness": {
            "ruta_item_refs": item_refs,
            "ruta_item_count": len(item_refs),
            "ruta_pool_dia_direct": pool_direct,
            "ruta_pool_dia_via_deleted_item": pool_via_item,
            "ruta_pool_dia_total": len(pool_direct) + len(pool_via_item),
            "ruta_grupo_count": len(grupos),
            "ruta_grupo_inspector_physical_rows": len(all_rgi),
            "ruta_grupo_inspector_distinct_grupos": len({r["ruta_grupo_id"] for r in all_rgi}),
            "truly_empty_operational": truly_empty,
        },
        "grupos": grupo_details,
        "group_inspectors": {
            "physical_row_count": len(all_rgi),
            "distinct_grupo_ids": len({r["ruta_grupo_id"] for r in all_rgi}),
            "distinct_inspector_ids": sorted({r["inspector_id"] for r in all_rgi}),
            "rows": all_rgi,
            "policy": "NO_DELETE_INSPECTOR",
        },
        "pool": {
            "direct_refs": pool_direct,
            "via_item_refs": pool_via_item,
            "classification": "KEEP" if pool_direct or pool_via_item else "NONE",
        },
        "surviving_fk_incoming": fk_refs,
        "protected_intersection": {
            "ruta_trabajo": prot_hit,
            "ruta_grupo_ids": grupo_prot,
        },
        "classification": classification,
        "classification_reasons": reasons,
    }


def _incoming_fk_surviving(conn: Connection, parent_table: str, pk_id: int) -> dict[str, Any]:
    by_fk: dict[str, int] = {}
    total = 0
    for edge in _incoming_fk_edges(conn, parent_table):
        tbl, col = edge["child_table"], edge["child_column"]
        n = int(
            _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :id", {"id": pk_id}) or 0
        )
        if n:
            key = f"{tbl}.{col}"
            by_fk[key] = n
            total += n
    return {"total_refs": total, "by_fk": by_fk, "edges": _incoming_fk_edges(conn, parent_table)}


def _build_safe_sets(routes: list[dict[str, Any]]) -> dict[str, Any]:
    safe_rt: list[int] = []
    safe_grupo: list[int] = []
    safe_rgi: list[int] = []
    safe_pool: list[int] = []
    blocked: list[dict[str, Any]] = []

    for r in routes:
        if r.get("classification") == "CONFIRMADO_TEST_ROUTE":
            safe_rt.append(r["ruta_trabajo_id"])
            for g in r.get("grupos", []):
                if g.get("classification") == "EMPTY_TEST_GROUP":
                    safe_grupo.append(g["id"])
                    for insp in g.get("inspectors", []):
                        safe_rgi.append(insp["id"])
        elif r.get("classification") not in ("MISSING",):
            blocked.append(
                {
                    "ruta_trabajo_id": r["ruta_trabajo_id"],
                    "classification": r.get("classification"),
                    "reasons": r.get("classification_reasons"),
                }
            )

    return {
        "SAFE_RUTA_TRABAJO_RESIDUAL": sorted(safe_rt),
        "SAFE_RUTA_GRUPO_RESIDUAL": sorted(set(safe_grupo)),
        "SAFE_RUTA_GRUPO_INSPECTOR_RESIDUAL": sorted(set(safe_rgi)),
        "SAFE_RUTA_POOL_RESIDUAL": sorted(set(safe_pool)),
        "BLOCKED_ROUTES": blocked,
    }


def _users_simulation(
    conn: Connection,
    safe_rt: set[int],
    safe_grupo: set[int],
    safe_rgi: set[int],
) -> dict[str, Any]:
    fk_columns = load_user_fk_columns(conn)
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    deleted_entities: dict[str, set[int]] = {
        "ruta_trabajo": safe_rt,
        "ruta_grupo": safe_grupo,
        "ruta_grupo_inspector": safe_rgi,
    }
    free_after = 0
    unlocked_ids: list[int] = []
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                if table in deleted_entities and r[0] in deleted_entities[table]:
                    continue
                blocked = True
                break
            if blocked:
                break
        if not blocked:
            free_after += 1
            unlocked_ids.append(uid)
    return {
        "users_test_fk_free_baseline_post_3i": USERS_FK_FREE_POST_3I,
        "users_test_fk_free_after_route_residual_sim": free_after,
        "users_additionally_unlocked": free_after - USERS_FK_FREE_POST_3I,
        "users_test_still_blocked": len(test_users) - free_after,
        "referenced_user_ids": _collect_referenced_users(conn, safe_rt),
        "policy": "NO_DELETE users",
    }


def _collect_referenced_users(conn: Connection, route_ids: set[int]) -> dict[str, list[int]]:
    if not route_ids:
        return {}
    ph = ",".join(str(i) for i in sorted(route_ids))
    rt_users = sorted(
        {
            int(r[0])
            for r in conn.execute(
                text(f"SELECT DISTINCT created_by_user_id FROM ruta_trabajo WHERE id IN ({ph})")
            )
        }
    )
    grupo_users = sorted(
        {
            int(r[0])
            for r in conn.execute(
                text(f"SELECT DISTINCT created_by_user_id FROM ruta_grupo WHERE ruta_trabajo_id IN ({ph})")
            )
        }
    )
    rgi_users = sorted(
        {
            int(r[0])
            for r in conn.execute(
                text(
                    f"""
                    SELECT DISTINCT rgi.created_by_user_id
                    FROM ruta_grupo_inspector rgi
                    JOIN ruta_grupo rg ON rg.id = rgi.ruta_grupo_id
                    WHERE rg.ruta_trabajo_id IN ({ph})
                    """
                )
            )
        }
    )
    return {
        "ruta_trabajo_created_by": rt_users,
        "ruta_grupo_created_by": grupo_users,
        "ruta_grupo_inspector_created_by": rgi_users,
    }


def _admin_graph_guard(conn: Connection) -> dict[str, Any]:
    blocked_notif = _count_ids_exist(conn, "notificacion", set(BLOCKED_NOTIF_25))
    comp_2289 = bool(_scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = 2289"))
    exp_27 = _count_ids_exist(conn, "expediente", set(FUTURE_EXPEDIENTE_27))
    oficio_1662 = bool(
        _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = 1662 AND numero_oficio = 'OF8430'")
    )
    return {
        "policy": "ADMIN_GRAPH_NOT_IN_SCOPE",
        "blocked_notificaciones_25_present": blocked_notif,
        "comprobacion_2289_present": comp_2289,
        "future_expedientes_27_present": exp_27,
        "oficio_1662_present": oficio_1662,
        "touched_by_this_diag": False,
    }


def _count_ids_exist(conn: Connection, table: str, ids: set[int]) -> int:
    if not ids:
        return 0
    found = 0
    for chunk in _chunk_ids(ids, 400):
        ph = ",".join(str(i) for i in chunk)
        found += int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE id IN ({ph})") or 0)
    return found


def _postcount_simulation(
    conn: Connection,
    safe_rt: set[int],
    safe_grupo: set[int],
    safe_rgi: set[int],
    baseline: dict[str, int],
) -> dict[str, Any]:
    rt_casc = _cascade_on_delete(conn, "ruta_trabajo", safe_rt)
    grupo_casc = _cascade_on_delete(conn, "ruta_grupo", safe_grupo)
    rgi_casc = _cascade_on_delete(conn, "ruta_grupo_inspector", safe_rgi)

    explicit = {
        "ruta_trabajo": len(safe_rt),
        "ruta_grupo": len(safe_grupo),
        "ruta_grupo_inspector": len(safe_rgi),
    }
    cascade_total = rt_casc["cascade_total"] + grupo_casc["cascade_total"] + rgi_casc["cascade_total"]
    set_null_total = rt_casc["set_null_total"] + grupo_casc["set_null_total"] + rgi_casc["set_null_total"]

    after = dict(baseline)
    after["ruta_trabajo"] = baseline["ruta_trabajo"] - len(safe_rt)
    after["ruta_grupo"] = baseline["ruta_grupo"] - len(safe_grupo)
    after["ruta_grupo_inspector"] = baseline["ruta_grupo_inspector"] - len(safe_rgi)
    after["ruta_trabajo"] -= max(0, rt_casc["cascade_total"] - len(safe_grupo) - len(safe_rgi))

    return {
        "before": baseline,
        "explicit_delete": explicit,
        "cascade_by_entity": {
            "ruta_trabajo": rt_casc,
            "ruta_grupo": grupo_casc,
            "ruta_grupo_inspector": rgi_casc,
        },
        "cascade_total": cascade_total,
        "set_null_total": set_null_total,
        "after_simulated": {
            "ruta_trabajo": baseline["ruta_trabajo"] - len(safe_rt),
            "ruta_grupo": baseline["ruta_grupo"] - len(safe_grupo),
            "ruta_grupo_inspector": baseline["ruta_grupo_inspector"] - len(safe_rgi),
            "note": "if delete ruta_trabajo only, grupo/rgi cascade from FK; explicit counts additive",
        },
    }


def run_route_residual_diag(
    conn: Connection,
    *,
    prime_manifest_path: Path,
    protected_path: Path,
    manifest_paths: list[Path],
) -> dict[str, Any]:
    """Orquestador diagnóstico ROUTE-RESIDUAL-CLEANUP."""
    baseline = _baseline_check(conn)
    deleted_prov_by_route = load_deleted_item_provenance(prime_manifest_path)
    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))

    routes: list[dict[str, Any]] = []
    for rtid in ROUTE_IDS_12:
        routes.append(_audit_route(conn, rtid, deleted_prov_by_route.get(rtid, {}), prot))

    exists_count = sum(1 for r in routes if r.get("exists"))
    classification_buckets = Counter(r.get("classification") for r in routes)
    safe_sets = _build_safe_sets(routes)

    safe_rt = set(safe_sets["SAFE_RUTA_TRABAJO_RESIDUAL"])
    safe_grupo = set(safe_sets["SAFE_RUTA_GRUPO_RESIDUAL"])
    safe_rgi = set(safe_sets["SAFE_RUTA_GRUPO_INSPECTOR_RESIDUAL"])

    virtual = VirtualDeleteState()
    virtual.add_explicit("ruta_trabajo", safe_rt)
    virtual.add_explicit("ruta_grupo", safe_grupo)
    virtual.add_explicit("ruta_grupo_inspector", safe_rgi)
    closure = protection_closure_check(virtual, prot)

    fk_graph = {
        "ruta_trabajo": _incoming_fk_edges(conn, "ruta_trabajo"),
        "ruta_grupo": _incoming_fk_edges(conn, "ruta_grupo"),
        "ruta_grupo_inspector": _incoming_fk_edges(conn, "ruta_grupo_inspector"),
    }
    delete_order_validation = _validate_delete_order_fk(PROPOSED_DELETE_ORDER, load_fk_edges(conn))

    known = _load_known_test_ids_from_manifests(manifest_paths)
    test_guard = _known_test_guard(conn, known)

    users_sim = _users_simulation(conn, safe_rt, safe_grupo, safe_rgi)
    postcount = _postcount_simulation(
        conn, safe_rt, safe_grupo, safe_rgi, baseline["counts"]
    )
    admin_guard = _admin_graph_guard(conn)

    deleted_item_map = [
        {
            "ruta_trabajo_id": rtid,
            "deleted_ruta_item_id": deleted_prov_by_route[rtid]["deleted_ruta_item_id"],
            "actuacion_id": deleted_prov_by_route[rtid].get("actuacion_id"),
        }
        for rtid in ROUTE_IDS_12
    ]

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3J-DIAG",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "routes_12": {
            "ids": list(ROUTE_IDS_12),
            "exists_count": exists_count,
            "duplicate_check": len(ROUTE_IDS_12) == len(set(ROUTE_IDS_12)),
            "deleted_ruta_item_ids": list(DELETED_RUTA_ITEM_IDS),
            "ruta_trabajo_to_deleted_item": deleted_item_map,
        },
        "provenance": {str(r["ruta_trabajo_id"]): r for r in routes},
        "routes_detail": routes,
        "classification_buckets": dict(classification_buckets),
        "groups": [g for r in routes for g in r.get("grupos", [])],
        "group_inspectors_summary": {
            "total_physical_rows": sum(
                r.get("group_inspectors", {}).get("physical_row_count", 0) for r in routes
            ),
            "total_distinct_grupos": len(
                {
                    insp["ruta_grupo_id"]
                    for r in routes
                    for insp in r.get("group_inspectors", {}).get("rows", [])
                }
            ),
        },
        "pool_summary": {
            "routes_with_pool_refs": [
                r["ruta_trabajo_id"]
                for r in routes
                if r.get("pool", {}).get("classification") != "NONE"
            ],
        },
        "fk_graph": fk_graph,
        "delete_order_proposed": {
            "order": PROPOSED_DELETE_ORDER,
            "validation": delete_order_validation,
            "note": "ruta_trabajo CASCADE deletes ruta_grupo and ruta_item; ruta_grupo CASCADE deletes ruta_grupo_inspector; ruta_pool_dia SET NULL on ruta_trabajo",
        },
        "classification": {
            "CONFIRMADO_TEST_ROUTE_definition": (
                "Had sole test ruta_item deleted in 2C.2A'; actuacion deleted in 2C.2B'; "
                "no operational refs; no protected intersection; empty of items/pool"
            ),
            "per_route": {r["ruta_trabajo_id"]: r.get("classification") for r in routes},
        },
        "safe_sets": safe_sets,
        "blocked_sets": safe_sets["BLOCKED_ROUTES"],
        "protected_closure": {
            "intersection_total": closure.get("by_entity", {}),
            "valid": closure.get("valid"),
            "conflicts": closure.get("conflicts", []),
        },
        "user_unlock_simulation": users_sim,
        "post_count_simulation": postcount,
        "admin_graph_guard": admin_guard,
        "known_test_guards": test_guard,
        "source_prime_manifest": str(prime_manifest_path.resolve()),
    }


def write_diag_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
