"""
PREDEPLOY-CLEANUP.3C.2 — congelar execution manifest FASE 2B (read-only).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import (
    RELEVAMIENTOS_QA_IDS,
    SQL_TEST_USER_WHERE,
)
from app.domains.predeploy_cleanup.execution_validator import validate_execution_plan
from app.domains.predeploy_cleanup.fk_graph import ForeignKeyEdge, load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import (
    file_sha256,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import (
    SOURCE_COLUMNS,
    _blocked_act_ids,
    _classify_source,
    _scalar,
)
from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import load_structured_acts_274
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    ENTITY_TABLE,
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    protection_closure_check,
)

PHASE2B_DELETE_ORDER = [
    "ruta_grupo_inspector",
    "ruta_item",
    "ruta_pool_dia",
    "ruta_grupo",
    "ruta_trabajo",
    "iniciador_ruta",
]

BASELINE_EXPECTED = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "actuaciones": 8487,
    "ruta_trabajo": 3566,
    "ruta_grupo": 3737,
    "ruta_grupo_inspector": 7637,
    "ruta_item": 4551,
    "ruta_pool_dia": 714,
    "iniciador_ruta": 8563,
    "denuncia": 492,
    "relevamiento": 4592,
    "orden_trabajo": 9223,
}

SAFE_SET_KEYS = {
    "ruta_grupo_inspector": ("SAFE_RUTA_GRUPO_INSPECTOR_FINAL", 1706),
    "ruta_item": ("SAFE_RUTA_ITEM_FINAL", 854),
    "ruta_pool_dia": ("SAFE_RUTA_POOL_FINAL", 353),
    "ruta_grupo": ("SAFE_RUTA_GRUPO_EMPTY_FINAL", 853),
    "ruta_trabajo": ("SAFE_RUTA_TRABAJO_EMPTY_FINAL", 851),
    "iniciador_ruta": ("SAFE_INICIADOR_FINAL", 369),
}

FORBIDDEN_MANIFEST_ENTITIES = frozenset(
    {
        "actuaciones",
        "denuncia",
        "relevamiento",
        "users",
        "establecimiento_operativo",
        "orden_trabajo",
        "domicilio",
        "contribuyente",
    }
)

POST_EXPECTED = {
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "ruta_grupo": 2884,
    "ruta_trabajo": 2715,
    "iniciador_ruta": 8194,
}


class ManifestFreezeError(Exception):
    """Aborta freeze del manifest FASE 2B."""


def load_safe_sets_from_reconcile(reconcile_path: Path) -> dict[str, set[int]]:
    """Carga safe sets congelados del diagnóstico 3C.1."""
    data = json.loads(reconcile_path.read_text(encoding="utf-8"))
    ss = data.get("safe_sets", {})
    result: dict[str, set[int]] = {}
    for entity, (key, expected_count) in SAFE_SET_KEYS.items():
        raw = ss.get(key, [])
        ids = {int(x) for x in raw}
        if len(ids) != expected_count:
            raise ManifestFreezeError(
                f"{key}: expected {expected_count} ids, got {len(ids)}"
            )
        if len(ids) != len(raw):
            raise ManifestFreezeError(f"{key}: duplicate ids detected")
        result[entity] = ids
    return result


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ManifestFreezeError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ManifestFreezeError(f"alembic={alembic}")
    counts = {}
    for table, expected in BASELINE_EXPECTED.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            raise ManifestFreezeError(f"baseline {table}: {actual} != {expected}")
    return {"database": db, "alembic_revision": alembic, "counts": counts}


def _validate_ids_exist_all(conn: Connection, safe_sets: dict[str, set[int]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for entity, ids in safe_sets.items():
        table = entity
        stale = validate_ids_exist(conn, table, ids, label=entity)
        if stale:
            raise ManifestFreezeError(f"missing {entity} ids: {stale[:5]}")
        report[entity] = {"expected": len(ids), "found": len(ids), "missing": 0}
    return report


def _validate_empty_groups(
    conn: Connection,
    safe_items: set[int],
    safe_groups: set[int],
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    for gid in sorted(safe_groups):
        items = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_grupo_id = {gid}")
        surviving = items - safe_items
        if surviving:
            violations.append(
                {"ruta_grupo_id": gid, "surviving_items": sorted(surviving)[:10]}
            )
    if violations:
        raise ManifestFreezeError(
            f"groups not empty after plan: {violations[:3]}"
        )
    return {"groups_checked": len(safe_groups), "all_empty_after_sim": True}


def _validate_empty_routes(
    conn: Connection,
    safe_items: set[int],
    safe_rutas: set[int],
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    for rid in sorted(safe_rutas):
        items = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rid}")
        surviving = items - safe_items
        if surviving:
            violations.append(
                {"ruta_trabajo_id": rid, "surviving_items": sorted(surviving)[:10]}
            )
    if violations:
        raise ManifestFreezeError(f"routes not empty after plan: {violations[:3]}")
    return {"routes_checked": len(safe_rutas), "all_empty_after_sim": True}


def _validate_rgi_scope(
    conn: Connection,
    safe_rgi: set[int],
    safe_groups: set[int],
) -> dict[str, Any]:
    out_of_scope: list[dict[str, Any]] = []
    for rgi_id in sorted(safe_rgi):
        row = conn.execute(
            text("SELECT id, ruta_grupo_id FROM ruta_grupo_inspector WHERE id = :id"),
            {"id": rgi_id},
        ).fetchone()
        if not row:
            raise ManifestFreezeError(f"rgi missing: {rgi_id}")
        gid = row[1]
        if gid not in safe_groups:
            out_of_scope.append({"rgi_id": rgi_id, "ruta_grupo_id": gid})
    if out_of_scope:
        raise ManifestFreezeError(f"rgi outside empty groups: {out_of_scope[:5]}")
    return {"rgi_checked": len(safe_rgi), "all_in_safe_groups": True}


def _validate_iniciadores_no_surviving_refs(
    conn: Connection,
    safe_ini: set[int],
    safe_items: set[int],
    safe_pool: set[int],
) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    for ini_id in sorted(safe_ini):
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {ini_id}")
        rp = _fetch_ids(
            conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {ini_id}"
        )
        ri_surv = ri - safe_items
        rp_surv = rp - safe_pool
        if ri_surv or rp_surv:
            blocked.append(
                {
                    "iniciador_id": ini_id,
                    "ruta_item_surviving": sorted(ri_surv)[:5],
                    "ruta_pool_surviving": sorted(rp_surv)[:5],
                }
            )
    if blocked:
        raise ManifestFreezeError(
            f"iniciadores with surviving refs: {blocked[:5]}"
        )
    return {"iniciadores_checked": len(safe_ini), "all_zero_refs_after_sim": True}


def _classify_iniciador_sources(
    conn: Connection,
    safe_ini: set[int],
    prot: dict[str, set[int]],
    act_test: set[int],
    cleanup_den: set[int],
    cleanup_rel: set[int],
) -> dict[str, Any]:
    buckets: dict[str, list[int]] = {
        "CONFIRMADO_TEST": [],
        "WRAPPER_AROUND_REAL_OR_INDET": [],
        "OTHER_SAFE": [],
    }
    for ini_id in sorted(safe_ini):
        row = conn.execute(
            text(
                """
                SELECT id, tipo_iniciador, denuncia_id, relevamiento_id,
                       notificacion_id, comprobacion_id, oficio_id, actuacion_id
                FROM iniciador_ruta WHERE id = :id
                """
            ),
            {"id": ini_id},
        ).fetchone()
        if not row:
            continue
        m = dict(row._mapping)
        src_classes: list[str] = []
        has_protected = False
        has_conf_test = False
        for col in SOURCE_COLUMNS:
            sid = m.get(col)
            if sid is None:
                continue
            tbl = col.replace("_id", "")
            cls = _classify_source(
                conn, tbl, sid, prot, act_test, cleanup_den, cleanup_rel
            )
            src_classes.append(cls)
            if cls == "PROTECTED_REAL":
                has_protected = True
            if cls == "CONFIRMADO_TEST":
                has_conf_test = True
        if has_conf_test and not has_protected:
            buckets["CONFIRMADO_TEST"].append(ini_id)
        elif has_protected:
            buckets["WRAPPER_AROUND_REAL_OR_INDET"].append(ini_id)
        else:
            buckets["OTHER_SAFE"].append(ini_id)
    return {
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "buckets": buckets,
        "note": "source documentos NO se borran en 2B",
    }


def _validate_wrapper64(
    conn: Connection,
    safe_ini: set[int],
    dry_run_v3_path: Path,
    reconcile_path: Path,
) -> dict[str, Any]:
    v3 = json.loads(dry_run_v3_path.read_text(encoding="utf-8"))
    recon = json.loads(reconcile_path.read_text(encoding="utf-8"))
    wrap = recon.get("wrapper64_reconcile", {})
    protected_ini = set(v3.get("iniciador_wrapper_incorporated", {}).get("protected_from_wrappers_64", []))
    deletable_ini = set(
        v3.get("iniciador_wrapper_incorporated", {}).get("deletable_from_wrappers_64", [])
    )
    leaked = safe_ini & protected_ini
    if leaked:
        raise ManifestFreezeError(f"protected wrapper iniciadores in SAFE_INICIADOR: {sorted(leaked)[:10]}")
    return {
        "wrapper_records": wrap.get("wrapper_records", 64),
        "unique_iniciadores": wrap.get("sum_deletable_protected", 63),
        "deletable_count": wrap.get("deletable_count", 36),
        "protected_count": wrap.get("protected_count", 27),
        "missing_iniciador_ids": wrap.get("missing_iniciador_ids", []),
        "protected_leaked_into_safe_ini": 0,
    }


def _validate_frozen_delete_order(
    delete_order: list[str],
    edges: list[ForeignKeyEdge],
) -> dict[str, Any]:
    """Valida que el orden congelado respeta FK RESTRICT/NO ACTION entre tablas del plan."""
    table_set = set(delete_order)
    order_index = {t: i for i, t in enumerate(delete_order)}
    violations: list[dict[str, str]] = []
    for edge in edges:
        if edge.child_table not in table_set or edge.parent_table not in table_set:
            continue
        if edge.delete_rule not in ("RESTRICT", "NO ACTION"):
            continue
        if order_index[edge.child_table] > order_index[edge.parent_table]:
            violations.append(
                {
                    "child": edge.child_table,
                    "parent": edge.parent_table,
                    "rule": edge.delete_rule,
                    "column": edge.child_column,
                }
            )
    return {"valid": len(violations) == 0, "violations": violations}


def _populate_cascade_deletes(
    conn: Connection,
    virtual: VirtualDeleteState,
    edges: list[ForeignKeyEdge],
    delete_order: list[str],
) -> dict[str, int]:
    """Simula cascades CASCADE por FK al borrar padres en orden."""
    cascade_counts: dict[str, int] = {}
    for table in delete_order:
        parent_ids = virtual.explicit.get(table, set())
        if not parent_ids:
            continue
        cascade_edges = [
            e for e in edges if e.parent_table == table and e.delete_rule == "CASCADE"
        ]
        for edge in cascade_edges:
            new_ids: set[int] = set()
            for chunk in _chunk_ids(parent_ids):
                ph = ",".join(str(i) for i in chunk)
                child_ids = _fetch_ids(
                    conn,
                    f"SELECT id FROM `{edge.child_table}` "
                    f"WHERE `{edge.child_column}` IN ({ph})",
                )
                already = virtual.all_deleted(edge.child_table)
                new_ids |= child_ids - already
            if new_ids:
                virtual.add_cascade(edge.child_table, new_ids)
                cascade_counts[edge.child_table] = (
                    cascade_counts.get(edge.child_table, 0) + len(new_ids)
                )
    return cascade_counts


def _full_protected_intersection(
    virtual: VirtualDeleteState,
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    """Intersección explicit+cascade vs manifest protegido (todas las entidades)."""
    conflicts: list[dict[str, Any]] = []
    total = 0
    for entity, prot_ids in prot.items():
        if not prot_ids:
            continue
        table = _table_for_entity(entity) if entity in ENTITY_TABLE else entity
        deleted = virtual.all_deleted(table)
        inter = deleted & prot_ids
        if inter:
            total += len(inter)
            conflicts.append(
                {
                    "entity": entity,
                    "intersection_count": len(inter),
                    "sample": sorted(inter)[:10],
                }
            )
    return {
        "valid": total == 0,
        "intersection_total": total,
        "conflicts": conflicts,
    }


def _protected_closure(
    conn: Connection,
    safe_sets: dict[str, set[int]],
    prot: dict[str, set[int]],
    edges: list[ForeignKeyEdge],
) -> dict[str, Any]:
    virtual = VirtualDeleteState()
    for entity in PHASE2B_DELETE_ORDER:
        virtual.add_explicit(_table_for_entity(entity), safe_sets.get(entity, set()))
    cascade_counts = _populate_cascade_deletes(conn, virtual, edges, PHASE2B_DELETE_ORDER)
    admin_closure = protection_closure_check(virtual, prot)
    full_inter = _full_protected_intersection(virtual, prot)
    return {
        "cascade_counts": cascade_counts,
        "admin_entities_closure": admin_closure,
        "full_protected_intersection": full_inter,
        "valid": admin_closure["valid"] and full_inter["valid"],
        "intersection_total": full_inter["intersection_total"],
    }


def _cascade_expectations(conn: Connection, safe_sets: dict[str, set[int]]) -> dict[str, Any]:
    edges = load_fk_edges(conn)
    rgi_cascade_children = [
        e for e in edges
        if e.parent_table == "ruta_grupo" and e.child_table == "ruta_grupo_inspector"
    ]
    explicit_rgi = safe_sets["ruta_grupo_inspector"]
    explicit_groups = safe_sets["ruta_grupo"]
    cascade_from_groups = set()
    for gid in explicit_groups:
        cascade_from_groups |= _fetch_ids(
            conn, f"SELECT id FROM ruta_grupo_inspector WHERE ruta_grupo_id = {gid}"
        )
    overlap = explicit_rgi & cascade_from_groups
    return {
        "rgi_explicit": len(explicit_rgi),
        "rgi_would_cascade_from_grupo_delete": len(cascade_from_groups),
        "overlap_explicit_and_cascade": len(overlap),
        "note": "explicit rgi deletes avoid double-counting in apply",
        "fk_rgi_from_grupo": [
            {
                "child": e.child_table,
                "delete_rule": e.delete_rule,
            }
            for e in rgi_cascade_children
        ],
    }


def _compute_unlock_expectations(
    conn: Connection,
    safe_ini: set[int],
    safe_items: set[int],
    safe_pool: set[int],
    prot: dict[str, set[int]],
    structured_acts_path: Path,
) -> dict[str, Any]:
    set_act_structured = load_structured_acts_274(structured_acts_path)
    set_act_old = _blocked_act_ids(conn, prot)
    union_413 = set_act_old | set_act_structured

    acts_unlocked = acts_blocked = 0
    for aid in union_413:
        blocking = set()
        for iid in _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}"):
            if iid not in safe_ini:
                blocking.add(iid)
        for iid in _fetch_ids(
            conn,
            f"SELECT DISTINCT iniciador_ruta_id FROM ruta_item WHERE actuacion_id = {aid}",
        ):
            items = _fetch_ids(
                conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}"
            )
            if items - safe_items and iid not in safe_ini:
                blocking.add(iid)
        if blocking:
            acts_blocked += 1
        else:
            acts_unlocked += 1

    cleanup_den = _fetch_ids(
        conn,
        f"""
        SELECT d.id FROM denuncia d
        JOIN users u ON u.id = d.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    den_unlocked = den_blocked = 0
    for did in cleanup_den:
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE denuncia_id = {did}")
        surv = False
        for iid in inis:
            if iid not in safe_ini:
                surv = True
                break
            if (
                _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}")
                - safe_items
            ):
                surv = True
                break
        if surv:
            den_blocked += 1
        else:
            den_unlocked += 1

    cleanup_rel = _fetch_ids(
        conn,
        f"""
        SELECT r.id FROM relevamiento r
        JOIN users u ON u.id = r.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """
    ) | RELEVAMIENTOS_QA_IDS
    rel_unlocked = rel_blocked = 0
    qa_status: dict[int, str] = {}
    for rid in cleanup_rel:
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}")
        if any(i not in safe_ini for i in inis):
            rel_blocked += 1
            status = "STILL_BLOCKED"
        else:
            rel_unlocked += 1
            status = "UNLOCKED_AFTER_2B"
        if rid in RELEVAMIENTOS_QA_IDS:
            qa_status[int(rid)] = status

    for qa_id in RELEVAMIENTOS_QA_IDS:
        exists = _scalar(conn, "SELECT COUNT(*) FROM relevamiento WHERE id = :id", {"id": qa_id})
        if not exists:
            raise ManifestFreezeError(f"QA relevamiento missing: {qa_id}")

    return {
        "actuaciones_test": {
            "total": len(union_413),
            "UNLOCKED_AFTER_2B": acts_unlocked,
            "STILL_BLOCKED": acts_blocked,
        },
        "denuncias_test": {
            "total": len(cleanup_den),
            "UNLOCKED_FOR_PHASE2C": den_unlocked,
            "STILL_BLOCKED": den_blocked,
            "delete_in_2b": 0,
        },
        "relevamientos_test": {
            "total": len(cleanup_rel),
            "UNLOCKED_AFTER_2B": rel_unlocked,
            "STILL_BLOCKED": rel_blocked,
            "delete_in_2b": 0,
            "qa_focus_status": qa_status,
        },
        "users_test_fk_free_estimate": 727,
        "users_note": "recalcular post-apply; no hard assertion",
    }


def build_phase2b_execution_manifest(
    conn: Connection,
    safe_sets: dict[str, set[int]],
    *,
    routes_diag_path: Path,
    reconcile_path: Path,
    protected_path: Path,
    dry_run_v3_path: Path,
    validation_report: dict[str, Any],
) -> dict[str, Any]:
    """Construye manifest congelado FASE 2B."""
    baseline = validation_report["baseline"]
    counts_before = baseline["counts"]
    counts_after = dict(counts_before)
    for entity in PHASE2B_DELETE_ORDER:
        counts_after[entity] = POST_EXPECTED[entity]

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2B",
        "phase_name": "routes_and_iniciadores_wrappers",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_report_hashes": {
            "routes_initiators_diag": file_sha256(routes_diag_path),
            "route_items_reconcile": file_sha256(reconcile_path),
        },
        "protected_manifest_hash": file_sha256(protected_path),
        "safe_set_counts": {k: len(safe_sets[k]) for k in PHASE2B_DELETE_ORDER},
        "baseline_counts": counts_before,
        "expected_counts_before": {k: counts_before[k] for k in PHASE2B_DELETE_ORDER},
        "expected_counts_after": {k: counts_after[k] for k in PHASE2B_DELETE_ORDER},
        "unchanged_entities": {
            k: counts_before[k]
            for k in (
                "actuaciones",
                "denuncia",
                "relevamiento",
                "users",
                "establecimiento_operativo",
                "orden_trabajo",
            )
        },
        "delete_order": PHASE2B_DELETE_ORDER,
        "entities": {
            entity: [{"id": i} for i in sorted(safe_sets[entity])]
            for entity in PHASE2B_DELETE_ORDER
        },
        "validation": validation_report,
        "protected_intersection": 0,
        "forbidden_deletes": {e: 0 for e in FORBIDDEN_MANIFEST_ENTITIES},
        "unlock_expectations": validation_report.get("unlock_expectations", {}),
        "wrapper64_metadata": validation_report.get("wrapper64", {}),
    }
    manifest["protected_intersection"] = validation_report["protected_closure"][
        "intersection_total"
    ]
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def run_phase2b_manifest_freeze(
    conn: Connection,
    *,
    routes_diag_path: Path,
    reconcile_path: Path,
    protected_path: Path,
    structured_acts_path: Path,
    dry_run_v3_path: Path,
) -> dict[str, Any]:
    """Orquestador freeze manifest 3C.2."""
    baseline = _baseline_check(conn)
    safe_sets = load_safe_sets_from_reconcile(reconcile_path)
    ids_report = _validate_ids_exist_all(conn, safe_sets)

    safe_items = safe_sets["ruta_item"]
    safe_pool = safe_sets["ruta_pool_dia"]
    safe_groups = safe_sets["ruta_grupo"]
    safe_rutas = safe_sets["ruta_trabajo"]
    safe_rgi = safe_sets["ruta_grupo_inspector"]
    safe_ini = safe_sets["iniciador_ruta"]

    empty_groups = _validate_empty_groups(conn, safe_items, safe_groups)
    empty_routes = _validate_empty_routes(conn, safe_items, safe_rutas)
    rgi_scope = _validate_rgi_scope(conn, safe_rgi, safe_groups)
    ini_refs = _validate_iniciadores_no_surviving_refs(
        conn, safe_ini, safe_items, safe_pool
    )

    prot = expand_protected_indirect(
        conn, load_protected_sets(load_manifest(protected_path))
    )
    act_test = _blocked_act_ids(conn, prot) | load_structured_acts_274(structured_acts_path)
    cleanup_den = _fetch_ids(
        conn,
        f"""
        SELECT d.id FROM denuncia d
        JOIN users u ON u.id = d.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    cleanup_rel = _fetch_ids(
        conn,
        f"""
        SELECT r.id FROM relevamiento r
        JOIN users u ON u.id = r.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """
    ) | RELEVAMIENTOS_QA_IDS

    ini_sources = _classify_iniciador_sources(
        conn, safe_ini, prot, act_test, cleanup_den, cleanup_rel
    )
    wrapper64 = _validate_wrapper64(conn, safe_ini, dry_run_v3_path, reconcile_path)
    edges = load_fk_edges(conn)
    protected_closure = _protected_closure(conn, safe_sets, prot, edges)
    if not protected_closure["valid"]:
        raise ManifestFreezeError(
            f"protected closure: {protected_closure['full_protected_intersection']['conflicts']}"
        )

    virtual = VirtualDeleteState()
    for entity in PHASE2B_DELETE_ORDER:
        virtual.add_explicit(_table_for_entity(entity), safe_sets[entity])
    exec_validation = validate_execution_plan(
        conn,
        {e: safe_sets[e] for e in PHASE2B_DELETE_ORDER},
        virtual,
        edges,
    )
    if not exec_validation.get("valid"):
        raise ManifestFreezeError(f"execution plan invalid: {exec_validation}")

    cascade = _cascade_expectations(conn, safe_sets)
    unlock = _compute_unlock_expectations(
        conn, safe_ini, safe_items, safe_pool, prot, structured_acts_path
    )

    for entity in FORBIDDEN_MANIFEST_ENTITIES:
        if entity in safe_sets:
            raise ManifestFreezeError(f"forbidden entity in safe_sets: {entity}")

    post_arithmetic = {}
    for entity in PHASE2B_DELETE_ORDER:
        before = baseline["counts"][entity]
        delete_n = len(safe_sets[entity])
        after = before - delete_n
        if after != POST_EXPECTED[entity]:
            raise ManifestFreezeError(
                f"post-count {entity}: {before}-{delete_n}={after} != {POST_EXPECTED[entity]}"
            )
        post_arithmetic[entity] = {"before": before, "delete": delete_n, "after": after}

    validation_report = {
        "baseline": baseline,
        "ids_exist": ids_report,
        "empty_groups": empty_groups,
        "empty_routes": empty_routes,
        "rgi_scope": rgi_scope,
        "iniciador_refs": ini_refs,
        "iniciador_sources": ini_sources,
        "wrapper64": wrapper64,
        "protected_closure": protected_closure,
        "execution_validation": exec_validation,
        "cascade_expectations": cascade,
        "unlock_expectations": unlock,
        "post_arithmetic": post_arithmetic,
        "delete_order_validated": _validate_frozen_delete_order(
            PHASE2B_DELETE_ORDER, edges
        ),
    }

    manifest = build_phase2b_execution_manifest(
        conn,
        safe_sets,
        routes_diag_path=routes_diag_path,
        reconcile_path=reconcile_path,
        protected_path=protected_path,
        dry_run_v3_path=dry_run_v3_path,
        validation_report=validation_report,
    )

    if manifest["protected_intersection"] != 0:
        raise ManifestFreezeError("protected_intersection must be 0")

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3C.2",
        "mode": "READ_ONLY_FREEZE",
        "writes_executed": False,
        "manifest": manifest,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def write_freeze_report(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path
