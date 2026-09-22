"""
PREDEPLOY-CLEANUP.3E.1 — congelar execution manifest FASE 2C.1 (read-only).
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
from app.domains.predeploy_cleanup.fk_graph import ForeignKeyEdge, load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import (
    file_sha256,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _blocked_act_ids, _scalar
from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import load_structured_acts_274
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import (
    BASELINE_POST_2B,
    _validate_delete_order_fk,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    cascade_children_of_actuaciones,
    protection_closure_check,
)

PHASE2C1_DELETE_ORDER = ["actuaciones", "denuncia", "orden_trabajo"]

SAFE_SET_SPECS = {
    "actuaciones": ("SAFE_ACTUACIONES_2C1", 265),
    "denuncia": ("SAFE_DENUNCIAS_2C1", 75),
    "orden_trabajo": ("SAFE_OT_AFTER_ACT_2C1", 265),
}

EXPECTED_CASCADE_COUNTS = {
    "inspeccion": 217,
    "actuaciones_inspector": 119,
    "clausura": 4,
    "decomiso": 4,
    "acta_inspeccion_item": 0,
}

CASCADE_TABLES = tuple(EXPECTED_CASCADE_COUNTS.keys())

POST_EXPECTED = {
    "actuaciones": 8222,
    "denuncia": 417,
    "orden_trabajo": 8958,
}

FORBIDDEN_MANIFEST_ENTITIES = frozenset(
    {
        "notificacion",
        "comprobacion",
        "domicilio",
        "contribuyente",
        "rubro",
        "calle_catalogo",
        "users",
        "establecimiento_operativo",
        "relevamiento",
        "inspeccion",
        "clausura",
        "decomiso",
        "actuaciones_inspector",
        "acta_inspeccion_item",
    }
)

PROTECTED_POSTCONDITION_MIN = {
    "actuaciones": 1189,
    "orden_trabajo": 1176,
    "inspeccion": 170,
    "notificacion": 168,
    "comprobacion": 48,
    "oficio": 40,
    "expediente": 40,
}


class ManifestFreezeError(Exception):
    """Aborta freeze del manifest FASE 2C.1."""


def load_safe_sets_from_diag(diag_path: Path) -> dict[str, set[int]]:
    """Carga safe sets congelados del diagnóstico 3E."""
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    ss = data.get("safe_sets", {})
    result: dict[str, set[int]] = {}
    for entity, (key, expected_count) in SAFE_SET_SPECS.items():
        raw = ss.get(key, [])
        ids = {int(x) for x in raw}
        if len(ids) != expected_count:
            raise ManifestFreezeError(f"{key}: expected {expected_count}, got {len(ids)}")
        if len(ids) != len(raw):
            raise ManifestFreezeError(f"{key}: duplicate ids")
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
    for table, expected in BASELINE_POST_2B.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            raise ManifestFreezeError(f"baseline {table}: {actual} != {expected}")
    return {"database": db, "alembic_revision": alembic, "counts": counts}


def _validate_ids_exist_all(conn: Connection, safe_sets: dict[str, set[int]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for entity, ids in safe_sets.items():
        stale = validate_ids_exist(conn, entity, ids, label=entity)
        if stale:
            raise ManifestFreezeError(f"missing {entity}: {stale[:5]}")
        report[entity] = {"expected": len(ids), "found": len(ids), "missing": 0}
    return report


def _validate_act_family(
    conn: Connection,
    act_ids: set[int],
    structured_acts_path: Path,
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    set_act_old = _blocked_act_ids(conn, prot)
    set_act_structured = load_structured_acts_274(structured_acts_path)
    old_in_set = sorted(act_ids & set_act_old)
    not_structured = sorted(act_ids - set_act_structured)
    if old_in_set:
        raise ManifestFreezeError(f"SET_ACT_OLD in manifest: {old_in_set[:5]}")
    if not_structured:
        raise ManifestFreezeError(f"not STRUCTURED: {not_structured[:5]}")
    return {
        "all_SET_ACT_STRUCTURED": True,
        "SET_ACT_OLD_in_set": 0,
        "count": len(act_ids),
    }


def _validate_act_routing_blockers(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    for aid in sorted(act_ids):
        ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}")
        if ini or ri or rp:
            violations.append(
                {
                    "actuacion_id": aid,
                    "iniciador_ruta": sorted(ini),
                    "ruta_item": sorted(ri),
                    "ruta_pool": sorted(rp),
                }
            )
    if violations:
        raise ManifestFreezeError(f"act routing blockers: {violations[:3]}")
    return {"acts_checked": len(act_ids), "all_zero_refs": True}


def _validate_den_routing_blockers(conn: Connection, den_ids: set[int]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    for did in sorted(den_ids):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE denuncia_id = {did}")
        ri = rp = 0
        for iid in inis:
            ri += len(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}"))
            rp += len(
                _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}")
            )
        if inis or ri or rp:
            violations.append(
                {"denuncia_id": did, "iniciadores": sorted(inis), "ri": ri, "rp": rp}
            )
    if violations:
        raise ManifestFreezeError(f"den routing blockers: {violations[:3]}")
    return {"denuncias_checked": len(den_ids), "all_zero_refs": True}


def _fk_child_rules(conn: Connection, parent_table: str) -> dict[str, str]:
    rows = conn.execute(
        text(
            """
            SELECT kcu.TABLE_NAME AS child_table, rc.DELETE_RULE AS delete_rule
            FROM information_schema.KEY_COLUMN_USAGE kcu
            JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
              ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
             AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.REFERENCED_TABLE_NAME = :parent
            """
        ),
        {"parent": parent_table},
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _collect_and_freeze_cascades(
    conn: Connection,
    act_ids: set[int],
    edges: list[ForeignKeyEdge],
) -> dict[str, Any]:
    fk_rules = _fk_child_rules(conn, "actuaciones")
    cascade_ids = cascade_children_of_actuaciones(conn, act_ids)

    for tbl in ("inspeccion", "clausura", "decomiso", "actuaciones_inspector"):
        rule = fk_rules.get(tbl)
        if rule != "CASCADE":
            raise ManifestFreezeError(f"{tbl} DELETE_RULE={rule}, expected CASCADE")

    counts = {tbl: len(cascade_ids.get(tbl, set())) for tbl in CASCADE_TABLES}
    for tbl, expected in EXPECTED_CASCADE_COUNTS.items():
        if counts.get(tbl, 0) != expected:
            raise ManifestFreezeError(
                f"cascade {tbl}: {counts.get(tbl)} != {expected}"
            )

    prot_inter: list[dict[str, Any]] = []
    return {
        "fk_rules_actuaciones_children": fk_rules,
        "cascade_ids": {k: sorted(v) for k, v in cascade_ids.items()},
        "cascade_counts": counts,
        "expected_cascade_counts": EXPECTED_CASCADE_COUNTS,
        "explicit_child_delete_required": False,
    }


def _protected_child_intersection(
    cascade_ids: dict[str, set[int]],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    conflicts: list[dict[str, Any]] = []
    total = 0
    entity_map = {
        "inspeccion": "inspeccion",
        "clausura": "clausura",
        "decomiso": "decomiso",
        "actuaciones_inspector": "actuaciones_inspector",
    }
    for tbl, entity in entity_map.items():
        ids = cascade_ids.get(tbl, set())
        inter = ids & prot.get(entity, set())
        if inter:
            total += len(inter)
            conflicts.append({"entity": entity, "intersection": sorted(inter)[:10]})
    return {"valid": total == 0, "intersection_total": total, "conflicts": conflicts}


def _collect_document_refs_preserved(
    conn: Connection,
    act_ids: set[int],
) -> dict[str, list[int]]:
    notif: set[int] = set()
    comp: set[int] = set()
    for chunk in _chunk_ids(act_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = conn.execute(
            text(
                f"""
                SELECT notificacion_id, comprobacion_id FROM actuaciones
                WHERE id IN ({ph})
                """
            )
        ).fetchall()
        for r in rows:
            if r[0]:
                notif.add(r[0])
            if r[1]:
                comp.add(r[1])
    return {
        "notificacion": sorted(notif),
        "comprobacion": sorted(comp),
        "policy": "NO_DELETE_NO_UPDATE_IN_2C1",
    }


def _validate_ot_exclusive(
    conn: Connection,
    safe_acts: set[int],
    safe_ot: set[int],
    prot: dict[str, set[int]],
    blocked_acts: set[int],
) -> dict[str, Any]:
    prot_ot = prot.get("orden_trabajo", set())
    leaked_prot = safe_ot & prot_ot
    if leaked_prot:
        raise ManifestFreezeError(f"protected OT in safe set: {sorted(leaked_prot)[:5]}")

    violations: list[dict[str, Any]] = []
    for ot_id in sorted(safe_ot):
        acts_on_ot = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        outside_safe = acts_on_ot - safe_acts
        outside_blocked = outside_safe & blocked_acts
        if outside_safe:
            violations.append(
                {
                    "orden_trabajo_id": ot_id,
                    "acts_outside_safe": sorted(outside_safe)[:10],
                    "shared_with_blocked_148": sorted(outside_blocked)[:5],
                }
            )
        remaining_after = acts_on_ot - safe_acts
        if remaining_after:
            continue
        if not acts_on_ot <= safe_acts:
            violations.append({"orden_trabajo_id": ot_id, "reason": "not_subset_safe_acts"})

    if violations:
        raise ManifestFreezeError(f"OT not exclusive: {violations[:3]}")

    return {
        "ot_checked": len(safe_ot),
        "all_exclusive_to_safe_acts": True,
        "protected_leaked": 0,
    }


def _load_excluded_from_diag(diag_path: Path) -> dict[str, list[int]]:
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    blocked = data.get("blocked_sets", {}).get("STILL_BLOCKED_ACTS_148", [])
    rel_detail = data.get("out_of_scope", {}).get("relevamientos", {})
    rel_ids = sorted(
        {
            int(r["relevamiento_id"])
            for r in rel_detail.get("detail", [])
            if r.get("relevamiento_id") is not None
        }
    )
    return {
        "blocked_acts_148": [int(x) for x in blocked],
        "relevamientos_26": rel_ids,
    }


def _validate_excluded_sets(
    conn: Connection,
    safe_sets: dict[str, set[int]],
    diag_path: Path,
) -> dict[str, Any]:
    excluded = _load_excluded_from_diag(diag_path)
    blocked_set = set(excluded["blocked_acts_148"])
    rel_set = set(excluded["relevamientos_26"])

    if not rel_set:
        rel_set = _fetch_ids(
            conn,
            f"""
            SELECT r.id FROM relevamiento r
            JOIN users u ON u.id = r.created_by_user_id
            WHERE {SQL_TEST_USER_WHERE}
            """
        ) | RELEVAMIENTOS_QA_IDS

    inter_acts = safe_sets["actuaciones"] & blocked_set
    if inter_acts:
        raise ManifestFreezeError(f"blocked acts in manifest: {sorted(inter_acts)[:5]}")

    manifest_all = safe_sets["actuaciones"] | safe_sets["denuncia"] | safe_sets["orden_trabajo"]
    inter_rel = manifest_all & rel_set

    present_blocked = sum(
        1
        for aid in blocked_set
        if _scalar(conn, "SELECT COUNT(*) FROM actuaciones WHERE id = :id", {"id": aid})
    )
    present_rel = sum(
        1
        for rid in rel_set
        if _scalar(conn, "SELECT COUNT(*) FROM relevamiento WHERE id = :id", {"id": rid})
    )
    qa_present = {}
    for qa_id in RELEVAMIENTOS_QA_IDS:
        qa_present[qa_id] = bool(
            _scalar(conn, "SELECT COUNT(*) FROM relevamiento WHERE id = :id", {"id": qa_id})
        )

    return {
        "blocked_acts_148_present": present_blocked,
        "blocked_acts_manifest_intersection": len(inter_acts),
        "relevamientos_26_present": present_rel,
        "relevamientos_manifest_intersection": len(inter_rel),
        "qa_focus_present": qa_present,
        "blocked_act_ids_frozen": sorted(blocked_set),
        "relevamiento_ids_frozen": sorted(rel_set),
    }


def _protected_closure(
    safe_sets: dict[str, set[int]],
    cascade_ids: dict[str, set[int]],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    virtual = VirtualDeleteState()
    for entity in PHASE2C1_DELETE_ORDER:
        virtual.add_explicit(_table_for_entity(entity), safe_sets[entity])
    for tbl, ids in cascade_ids.items():
        if ids:
            virtual.add_cascade(tbl, set(ids))
    admin = protection_closure_check(virtual, prot)
    intersection_total = sum(
        admin["by_entity"].get(e, {}).get("intersection_total", 0)
        for e in admin.get("by_entity", {})
    )
    return {
        "admin_entities_closure": admin,
        "intersection_total": intersection_total,
        "valid": admin["valid"] and intersection_total == 0,
    }


def _protected_preserved_snapshot(prot: dict[str, set[int]]) -> dict[str, int]:
    return {k: len(prot.get(k, set())) for k in PROTECTED_POSTCONDITION_MIN}


def build_phase2c1_execution_manifest(
    safe_sets: dict[str, set[int]],
    cascade_report: dict[str, Any],
    validation_report: dict[str, Any],
    *,
    diag_path: Path,
    protected_path: Path,
) -> dict[str, Any]:
    baseline = validation_report["baseline"]
    counts_before = baseline["counts"]
    counts_after = dict(counts_before)
    for entity in PHASE2C1_DELETE_ORDER:
        counts_after[entity] = POST_EXPECTED[entity]

    cascade_baseline = {
        tbl: int(validation_report["cascade_baseline_counts"].get(tbl, 0))
        for tbl in CASCADE_TABLES
    }
    cascade_after = {
        tbl: cascade_baseline[tbl] - EXPECTED_CASCADE_COUNTS[tbl]
        for tbl in CASCADE_TABLES
    }

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2C1",
        "phase_name": "unlocked_actuaciones_denuncias_ot",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(diag_path),
        "source_diag_sha256": file_sha256(diag_path),
        "protected_manifest_path": str(protected_path),
        "protected_manifest_sha256": file_sha256(protected_path),
        "safe_set_counts": {k: len(safe_sets[k]) for k in PHASE2C1_DELETE_ORDER},
        "entities": {
            entity: [{"id": i} for i in sorted(safe_sets[entity])]
            for entity in PHASE2C1_DELETE_ORDER
        },
        "expected_cascades": {
            tbl: {
                "count": EXPECTED_CASCADE_COUNTS[tbl],
                "ids": cascade_report["cascade_ids"].get(tbl, []),
            }
            for tbl in CASCADE_TABLES
        },
        "preserve_document_refs": validation_report["document_refs_preserved"],
        "excluded": {
            "blocked_acts_148": validation_report["excluded"]["blocked_act_ids_frozen"],
            "relevamientos_26": validation_report["excluded"]["relevamiento_ids_frozen"],
        },
        "delete_order": PHASE2C1_DELETE_ORDER,
        "expected_counts_before": {k: counts_before[k] for k in PHASE2C1_DELETE_ORDER},
        "expected_counts_after": {k: counts_after[k] for k in PHASE2C1_DELETE_ORDER},
        "cascade_counts_before": cascade_baseline,
        "cascade_counts_after": cascade_after,
        "unchanged_entities": {
            k: counts_before[k]
            for k in (
                "users",
                "establecimiento_operativo",
                "relevamiento",
                "ruta_trabajo",
                "ruta_grupo",
                "ruta_grupo_inspector",
                "ruta_item",
                "ruta_pool_dia",
                "iniciador_ruta",
            )
        },
        "forbidden_deletes": {e: 0 for e in FORBIDDEN_MANIFEST_ENTITIES},
        "protected_postcondition_min": PROTECTED_POSTCONDITION_MIN,
        "protected_preserved_at_freeze": validation_report["protected_preserved"],
        "unlock_expectations": {
            "users_test_fk_free_post_2b": 727,
            "users_test_fk_free_post_2c1_estimate": 802,
            "note": "recalcular post-apply",
        },
        "validation": validation_report,
        "protected_intersection": 0,
    }
    manifest["protected_intersection"] = (
        0 if validation_report["protected_closure"]["valid"] else -1
    )
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def run_phase2c1_manifest_freeze(
    conn: Connection,
    *,
    diag_path: Path,
    protected_path: Path,
    structured_acts_path: Path,
) -> dict[str, Any]:
    """Orquestador freeze manifest 3E.1."""
    baseline = _baseline_check(conn)
    safe_sets = load_safe_sets_from_diag(diag_path)
    ids_report = _validate_ids_exist_all(conn, safe_sets)

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))

    prot_act_inter = safe_sets["actuaciones"] & prot.get("actuaciones", set())
    prot_den_inter = safe_sets["denuncia"] & prot.get("denuncia", set())
    if prot_act_inter or prot_den_inter:
        raise ManifestFreezeError("protected intersection in safe sets")

    family = _validate_act_family(
        conn, safe_sets["actuaciones"], structured_acts_path, prot
    )
    act_blockers = _validate_act_routing_blockers(conn, safe_sets["actuaciones"])
    den_blockers = _validate_den_routing_blockers(conn, safe_sets["denuncia"])

    edges = load_fk_edges(conn)
    cascade_report = _collect_and_freeze_cascades(conn, safe_sets["actuaciones"], edges)
    cascade_ids_raw = {k: set(v) for k, v in cascade_report["cascade_ids"].items()}

    child_prot = _protected_child_intersection(cascade_ids_raw, prot)
    if not child_prot["valid"]:
        raise ManifestFreezeError(f"protected children: {child_prot['conflicts']}")

    doc_refs = _collect_document_refs_preserved(conn, safe_sets["actuaciones"])

    set_act_old = _blocked_act_ids(conn, prot)
    set_act_structured = load_structured_acts_274(structured_acts_path)
    union_413 = set_act_old | set_act_structured
    blocked_acts: set[int] = set()
    for aid in union_413:
        if aid in safe_sets["actuaciones"]:
            continue
        ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}")
        if ini or ri or rp:
            blocked_acts.add(aid)

    ot_report = _validate_ot_exclusive(
        conn, safe_sets["actuaciones"], safe_sets["orden_trabajo"], prot, blocked_acts
    )
    excluded = _validate_excluded_sets(conn, safe_sets, diag_path)

    protected_closure = _protected_closure(safe_sets, cascade_ids_raw, prot)
    if not protected_closure["valid"]:
        raise ManifestFreezeError(f"protected closure failed: {protected_closure}")

    delete_order_check = _validate_delete_order_fk(PHASE2C1_DELETE_ORDER, edges)

    cascade_baseline_counts = {}
    for tbl in CASCADE_TABLES:
        cascade_baseline_counts[tbl] = int(
            _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}`") or 0
        )

    post_arithmetic = {}
    for entity in PHASE2C1_DELETE_ORDER:
        before = baseline["counts"][entity]
        delete_n = len(safe_sets[entity])
        after = before - delete_n
        if after != POST_EXPECTED[entity]:
            raise ManifestFreezeError(f"post-count {entity}: {after} != {POST_EXPECTED[entity]}")
        post_arithmetic[entity] = {"before": before, "delete": delete_n, "after": after}

    for forbidden in FORBIDDEN_MANIFEST_ENTITIES:
        if forbidden in safe_sets and safe_sets.get(forbidden):
            raise ManifestFreezeError(f"forbidden in safe_sets: {forbidden}")

    validation_report = {
        "baseline": baseline,
        "ids_exist": ids_report,
        "act_family": family,
        "act_routing_blockers": act_blockers,
        "den_routing_blockers": den_blockers,
        "cascade_report": cascade_report,
        "protected_child_intersection": child_prot,
        "document_refs_preserved": doc_refs,
        "ot_exclusive": ot_report,
        "excluded": excluded,
        "protected_closure": protected_closure,
        "delete_order_validated": delete_order_check,
        "post_arithmetic": post_arithmetic,
        "protected_preserved": _protected_preserved_snapshot(prot),
        "cascade_baseline_counts": cascade_baseline_counts,
    }

    manifest = build_phase2c1_execution_manifest(
        safe_sets,
        cascade_report,
        validation_report,
        diag_path=diag_path,
        protected_path=protected_path,
    )

    if manifest["protected_intersection"] != 0:
        raise ManifestFreezeError("protected_intersection must be 0")

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3E.1",
        "mode": "READ_ONLY_FREEZE",
        "writes_executed": False,
        "manifest": manifest,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def write_freeze_report(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path
