"""
PREDEPLOY-CLEANUP.3G.1 — congelar execution manifest FASE 2C.2B.
110 actuaciones + 26 relevamientos + 110 OT. Solo lectura / manifest.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import RELEVAMIENTOS_QA_IDS
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import (
    file_sha256,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar, audit_otro_relevador_qa
from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import load_structured_acts_274
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import _validate_delete_order_fk
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import PROTECTED_COMP_CLOSURE_8
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _fetch_ids,
    _table_for_entity,
    protection_closure_check,
    recalculate_ots_deletable,
)

PHASE2C2B_DELETE_ORDER = ["actuaciones", "relevamiento", "orden_trabajo"]

EXPECTED_ACTS = 110
EXPECTED_RELS = 26
EXPECTED_OT = 110
EXPECTED_OLD = 101
EXPECTED_STRUCTURED = 9

SOURCE_9110_ACT = 9145
SOURCE_COMP = 2129
SOURCE_OFICIO = 1575

BASELINE_POST_2C2A = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8039,
    "actuaciones": 8222,
    "denuncia": 417,
    "relevamiento": 4592,
    "orden_trabajo": 8958,
    "inspeccion": 915,
    "actuaciones_inspector": 4189,
    "acta_inspeccion_item": 52,
    "clausura": 69,
    "decomiso": 25,
    "relevamiento_relevador": 535,
}

POST_MAIN = {
    "actuaciones": 8112,
    "relevamiento": 4566,
    "orden_trabajo": 8848,
}

EXPECTED_CASCADE_PHYSICAL = {
    "inspeccion": {
        "physical_rows": 17,
        "distinct_parent_ids": 17,
        "baseline": 915,
        "expected_after": 898,
    },
    "actuaciones_inspector": {
        "physical_rows": 9,
        "distinct_parent_ids": 9,
        "baseline": 4189,
        "expected_after": 4180,
    },
    "acta_inspeccion_item": {
        "physical_rows": 0,
        "distinct_parent_ids": 0,
        "baseline": 52,
        "expected_after": 52,
    },
    "clausura": {
        "physical_rows": 0,
        "distinct_parent_ids": 0,
        "baseline": 69,
        "expected_after": 69,
    },
    "decomiso": {
        "physical_rows": 0,
        "distinct_parent_ids": 0,
        "baseline": 25,
        "expected_after": 25,
    },
    "relevamiento_relevador": {
        "physical_rows": 10,
        "distinct_parent_ids": 5,
        "baseline": 535,
        "expected_after": 525,
    },
}

FORBIDDEN_MANIFEST_ENTITIES = frozenset(
    {
        "notificacion",
        "comprobacion",
        "oficio",
        "expediente",
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
    }
)


class ManifestFreezeError(Exception):
    """Aborta freeze del manifest FASE 2C.2B."""


def load_cascade_reconcile(reconcile_path: Path) -> dict[str, Any]:
    """Carga reconciliación física 3G.0.1."""
    data = json.loads(reconcile_path.read_text(encoding="utf-8"))
    table = {row["tabla"]: row for row in data["corrected_postcounts"]["table"]}
    for tbl, expected in EXPECTED_CASCADE_PHYSICAL.items():
        row = table.get(tbl)
        if not row:
            raise ManifestFreezeError(f"missing cascade table {tbl} in reconcile")
        if row["physical_rows_delete"] != expected["physical_rows"]:
            raise ManifestFreezeError(
                f"{tbl} physical {row['physical_rows_delete']} != {expected['physical_rows']}"
            )
        if row["expected_after"] != expected["expected_after"]:
            raise ManifestFreezeError(
                f"{tbl} after {row['expected_after']} != {expected['expected_after']}"
            )
    return data


def load_safe_sets_from_sources_diag(diag_path: Path) -> dict[str, set[int]]:
    """Carga safe sets del diag 3G."""
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    ss = data["safe_sets"]
    acts = {int(x) for x in ss["SAFE_ACTUACIONES_2C2B"]}
    rels = {int(x) for x in ss["SAFE_RELEVAMIENTOS_2C2B"]}
    ots = {int(x) for x in ss["SAFE_OT_2C2B"]}
    if len(acts) != EXPECTED_ACTS or len(rels) != EXPECTED_RELS or len(ots) != EXPECTED_OT:
        raise ManifestFreezeError("safe set count mismatch")
    if len(acts) != len(ss["SAFE_ACTUACIONES_2C2B"]):
        raise ManifestFreezeError("duplicate act ids")
    return {
        "actuaciones": acts,
        "relevamiento": rels,
        "orden_trabajo": ots,
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
    for table, expected in BASELINE_POST_2C2A.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            raise ManifestFreezeError(f"baseline {table}: {actual} != {expected}")
    return {"database": db, "alembic_revision": alembic, "counts": counts}


def _validate_family(diag: dict[str, Any], act_ids: set[int]) -> dict[str, Any]:
    fam = diag["acts_110"]["act_family_breakdown"]
    old = set(fam["SET_ACT_OLD"])
    structured = set(fam["SET_ACT_STRUCTURED"])
    both = set(fam.get("BOTH", []))
    if len(old) != EXPECTED_OLD:
        raise ManifestFreezeError(f"SET_ACT_OLD: {len(old)} != {EXPECTED_OLD}")
    if len(structured) != EXPECTED_STRUCTURED:
        raise ManifestFreezeError(f"SET_ACT_STRUCTURED: {len(structured)} != {EXPECTED_STRUCTURED}")
    if both:
        raise ManifestFreezeError(f"BOTH non-empty: {both}")
    if old | structured != act_ids:
        raise ManifestFreezeError("family union != safe acts")
    if old & structured:
        raise ManifestFreezeError("family intersection != 0")
    return {
        "SET_ACT_OLD_count": len(old),
        "SET_ACT_STRUCTURED_count": len(structured),
        "BOTH_count": 0,
        "SET_ACT_OLD_ids": sorted(old),
        "SET_ACT_STRUCTURED_ids": sorted(structured),
    }


def _validate_act_blockers(conn: Connection, act_ids: set[int]) -> None:
    for aid in sorted(act_ids):
        ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}")
        if ini or ri or rp:
            raise ManifestFreezeError(f"act {aid} blockers: ini={ini} ri={ri} rp={rp}")


def _validate_rel_blockers(conn: Connection, rel_ids: set[int]) -> None:
    for rid in sorted(rel_ids):
        ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}")
        ri = _fetch_ids(
            conn,
            f"SELECT ri.id FROM ruta_item ri JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id "
            f"WHERE ir.relevamiento_id = {rid}",
        )
        rp = _fetch_ids(
            conn,
            f"SELECT rp.id FROM ruta_pool_dia rp JOIN iniciador_ruta ir ON ir.id = rp.iniciador_ruta_id "
            f"WHERE ir.relevamiento_id = {rid}",
        )
        if ini or ri or rp:
            raise ManifestFreezeError(f"rel {rid} blockers")


def _validate_ot_exclusive(
    conn: Connection,
    ot_ids: set[int],
    act_ids: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    prot_ot = prot.get("orden_trabajo", set())
    violations = []
    for ot_id in sorted(ot_ids):
        if ot_id in prot_ot:
            violations.append({"ot_id": ot_id, "reason": "PROTECTED"})
            continue
        acts_on = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        outside = acts_on - act_ids
        if outside:
            violations.append({"ot_id": ot_id, "outside_acts": sorted(outside)[:5]})
        incoming = _rows_fk_to_ot(conn, ot_id)
        non_act = {k: v for k, v in incoming.items() if k != "actuaciones" and v}
        if non_act:
            violations.append({"ot_id": ot_id, "non_act_refs": non_act})
    if violations:
        raise ManifestFreezeError(f"OT blockers: {violations[:3]}")
    deletable, blocked, _ = recalculate_ots_deletable(conn, ot_ids, prot_ot, act_ids, prot.get("actuaciones", set()))
    if set(deletable) != ot_ids:
        raise ManifestFreezeError(f"OT recalc: deletable {len(deletable)} != {len(ot_ids)}")
    return {"all_exclusive_to_safe_acts": True, "ot_checked": len(ot_ids)}


def _rows_fk_to_ot(conn: Connection, ot_id: int) -> dict[str, int]:
    refs: dict[str, int] = {}
    children = conn.execute(
        text(
            """
            SELECT TABLE_NAME, COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND REFERENCED_TABLE_NAME = 'orden_trabajo'
            """
        )
    ).fetchall()
    for tbl, col in children:
        n = int(
            _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :id", {"id": ot_id}) or 0
        )
        if n:
            refs[tbl] = n
    return refs


def _validate_parent_docs(
    conn: Connection,
    diag: dict[str, Any],
    act_ids: set[int],
) -> dict[str, Any]:
    pd = diag["acts_110"]["parent_docs_preserved"]
    notif_ids = {int(x) for x in pd["notificacion_ids"]}
    comp_ids = {int(x) for x in pd["comprobacion_ids"]}
    if len(notif_ids) != 109:
        raise ManifestFreezeError(f"notificaciones preserve: {len(notif_ids)} != 109")
    if len(comp_ids) != 3:
        raise ManifestFreezeError(f"comprobaciones preserve: {len(comp_ids)} != 3")
    for nid in notif_ids:
        if not _scalar(conn, "SELECT COUNT(*) FROM notificacion WHERE id = :id", {"id": nid}):
            raise ManifestFreezeError(f"notificacion {nid} missing")
    for cid in comp_ids:
        if not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid}):
            raise ManifestFreezeError(f"comprobacion {cid} missing")

    if SOURCE_9110_ACT not in act_ids:
        raise ManifestFreezeError("9145 not in safe acts")
    row = conn.execute(
        text("SELECT comprobacion_id FROM actuaciones WHERE id = :id"),
        {"id": SOURCE_9110_ACT},
    ).fetchone()
    if not row or row[0] != SOURCE_COMP:
        raise ManifestFreezeError("9145 comprobacion mismatch")
    if not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": SOURCE_COMP}):
        raise ManifestFreezeError("comprobacion 2129 missing")
    if not _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = :id", {"id": SOURCE_OFICIO}):
        raise ManifestFreezeError("oficio 1575 missing")

    edges = load_fk_edges(conn)
    act_comp_rule = next(
        (e.delete_rule for e in edges if e.child_table == "actuaciones" and e.child_column == "comprobacion_id"),
        None,
    )
    return {
        "notificaciones_109": sorted(notif_ids),
        "comprobaciones_3": sorted(comp_ids),
        "comprobacion_2129": {"id": SOURCE_COMP, "exists": True, "preserve": True},
        "oficio_1575": {"id": SOURCE_OFICIO, "exists": True, "preserve": True},
        "actuacion_9145": {
            "id": SOURCE_9110_ACT,
            "comprobacion_id": SOURCE_COMP,
            "delete_act_comprobacion_fk_rule": act_comp_rule,
            "policy": "DELETE act must NOT delete comprobacion/oficio",
        },
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


def _protected_closure(
    safe_sets: dict[str, set[int]],
    reconcile: dict[str, Any],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    virtual = VirtualDeleteState()
    virtual.add_explicit("actuaciones", safe_sets["actuaciones"])
    virtual.add_explicit("relevamiento", safe_sets["relevamiento"])
    virtual.add_explicit("orden_trabajo", safe_sets["orden_trabajo"])
    insp_ids = {r["id"] for r in reconcile["inspection_rows"]["rows"]}
    virtual.add_cascade("inspeccion", insp_ids)
    virtual.add_cascade("relevamiento_relevador", {r["relevamiento_id"] for r in reconcile["relevamiento_relevador_rows"]["all_rows"]})
    closure = protection_closure_check(virtual, prot)
    if not closure.get("valid"):
        raise ManifestFreezeError(f"protected closure: {closure.get('conflicts', [])[:3]}")
    return closure


def _load_excluded(diag: dict[str, Any]) -> dict[str, Any]:
    blocked = [int(x) for x in diag["excluded_acts_38"]["ids"]]
    orphan_n = diag.get("orphan_docs_reserved", {}).get("notificaciones_36", {})
    orphan_c = diag.get("orphan_docs_reserved", {}).get("comprobaciones_20", {})
    source_119 = diag.get("source_notificaciones_119_post_2c2a", {})
    return {
        "blocked_acts_38": blocked,
        "orphan_notificaciones_36": orphan_n.get("expected", 36),
        "orphan_comprobaciones_20": orphan_c.get("expected", 20),
        "source_notificaciones_119_count": source_119.get("expected", 119),
    }


def run_phase2c2b_manifest_freeze(
    conn: Connection,
    *,
    sources_diag_path: Path,
    cascade_reconcile_path: Path,
    protected_path: Path,
    apply_2c2a_path: Path | None = None,
) -> dict[str, Any]:
    """Orquestador freeze manifest FASE 2C.2B."""
    baseline = _baseline_check(conn)
    reconcile = load_cascade_reconcile(cascade_reconcile_path)
    loaded = load_safe_sets_from_sources_diag(sources_diag_path)
    diag = loaded["diag"]
    safe_sets = {
        "actuaciones": loaded["actuaciones"],
        "relevamiento": loaded["relevamiento"],
        "orden_trabajo": loaded["orden_trabajo"],
    }

    # Cross-check reconcile safe ids match diag
    rec_safe = reconcile.get("safe_set_ids") or {}
    if set(int(x) for x in rec_safe.get("SAFE_ACTUACIONES_2C2B", [])) != safe_sets["actuaciones"]:
        raise ManifestFreezeError("reconcile acts mismatch diag")
    if set(int(x) for x in rec_safe.get("SAFE_RELEVAMIENTOS_2C2B", [])) != safe_sets["relevamiento"]:
        raise ManifestFreezeError("reconcile rels mismatch diag")
    if set(int(x) for x in rec_safe.get("SAFE_OT_2C2B", [])) != safe_sets["orden_trabajo"]:
        raise ManifestFreezeError("reconcile ots mismatch diag")

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))

    for entity in PHASE2C2B_DELETE_ORDER:
        stale = validate_ids_exist(conn, entity, safe_sets[entity], label=entity)
        if stale:
            raise ManifestFreezeError(f"missing {entity}: {stale[:5]}")

    family = _validate_family(diag, safe_sets["actuaciones"])
    _validate_act_blockers(conn, safe_sets["actuaciones"])
    _validate_rel_blockers(conn, safe_sets["relevamiento"])

    for rid in RELEVAMIENTOS_QA_IDS:
        if rid not in safe_sets["relevamiento"]:
            raise ManifestFreezeError(f"QA relev {rid} missing")

    if safe_sets["actuaciones"] & prot.get("actuaciones", set()):
        raise ManifestFreezeError("protected act intersection")

    ot_val = _validate_ot_exclusive(conn, safe_sets["orden_trabajo"], safe_sets["actuaciones"], prot)
    parent_docs = _validate_parent_docs(conn, diag, safe_sets["actuaciones"])
    comp_reg = _protected_comp_regression(conn, prot)
    if not comp_reg["all_protected"]:
        raise ManifestFreezeError("protected comprobacion regression failed")

    excluded = _load_excluded(diag)
    blocked_set = set(excluded["blocked_acts_38"])
    if safe_sets["actuaciones"] & blocked_set:
        raise ManifestFreezeError("blocked acts intersection")
    if len(blocked_set) != 38:
        raise ManifestFreezeError(f"blocked acts: {len(blocked_set)}")

    closure = _protected_closure(safe_sets, reconcile, prot)
    fk_valid = _validate_delete_order_fk(PHASE2C2B_DELETE_ORDER, load_fk_edges(conn))

    source_119_ids: list[int] = []
    if apply_2c2a_path and apply_2c2a_path.is_file():
        apply_data = json.loads(apply_2c2a_path.read_text(encoding="utf-8"))
        source_119_ids = list(apply_data.get("sources_snapshot_before", {}).get("notificaciones", []))

    cascade_ids = {
        "inspeccion": [r["id"] for r in reconcile["inspection_rows"]["rows"]],
        "actuaciones_inspector": reconcile["actuaciones_inspector_rows"]["all_rows"],
        "relevamiento_relevador": reconcile["relevamiento_relevador_rows"]["all_rows"],
    }

    qa = audit_otro_relevador_qa(conn)
    legacy_inspector = [
        {"relevamiento_id": i["relevamiento_id"], "inspector_id": i.get("inspector_id_legacy")}
        for i in diag["relevamientos_26"]["items"]
        if i.get("inspector_id_legacy")
    ]

    counts_before = dict(baseline["counts"])
    counts_after = dict(counts_before)
    for entity in PHASE2C2B_DELETE_ORDER:
        counts_after[entity] = POST_MAIN[entity]
    for tbl, spec in EXPECTED_CASCADE_PHYSICAL.items():
        counts_after[tbl] = spec["expected_after"]

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2C2B",
        "phase_name": "safe_actuaciones_relevamientos_ot",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(sources_diag_path.resolve()),
        "source_diag_sha256": file_sha256(sources_diag_path),
        "cascade_reconcile_path": str(cascade_reconcile_path.resolve()),
        "cascade_reconcile_sha256": file_sha256(cascade_reconcile_path),
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "safe_set_counts": {
            "actuaciones": EXPECTED_ACTS,
            "relevamiento": EXPECTED_RELS,
            "orden_trabajo": EXPECTED_OT,
        },
        "act_family_breakdown": family,
        "entities": {
            entity: [{"id": i} for i in sorted(safe_sets[entity])]
            for entity in PHASE2C2B_DELETE_ORDER
        },
        "expected_cascades": {
            tbl: {
                "physical_rows": spec["physical_rows"],
                "distinct_parent_ids": spec["distinct_parent_ids"],
                "baseline": spec["baseline"],
                "expected_after": spec["expected_after"],
                "ids": cascade_ids.get(tbl, []),
                "delete_rule": "CASCADE",
                "explicit_delete_in_manifest": False,
            }
            for tbl, spec in EXPECTED_CASCADE_PHYSICAL.items()
        },
        "preserve": {
            "notificaciones_109": parent_docs["notificaciones_109"],
            "comprobaciones_3": parent_docs["comprobaciones_3"],
            "comprobacion_2129": parent_docs["comprobacion_2129"],
            "oficio_1575": parent_docs["oficio_1575"],
            "source_notificaciones_119": source_119_ids,
            "legacy_inspector_id_on_relevamientos": legacy_inspector,
        },
        "excluded": {
            "blocked_acts_38": excluded["blocked_acts_38"],
            "orphan_notificaciones_36": excluded["orphan_notificaciones_36"],
            "orphan_comprobaciones_20": excluded["orphan_comprobaciones_20"],
            "relevador_qa_id_2": {
                "id": 2,
                "nombre": "Otro Relevador QA",
                "current_refs": qa.get("relevamiento_ids", []),
                "expected_refs_after_2c2b": 0,
                "status": "READY_FOR_PHASE2E",
            },
        },
        "delete_order": PHASE2C2B_DELETE_ORDER,
        "forbidden_deletes": {e: 0 for e in FORBIDDEN_MANIFEST_ENTITIES},
        "expected_counts_before": {
            **{e: counts_before[e] for e in PHASE2C2B_DELETE_ORDER},
            **{tbl: EXPECTED_CASCADE_PHYSICAL[tbl]["baseline"] for tbl in EXPECTED_CASCADE_PHYSICAL},
        },
        "expected_counts_after": {
            **{e: counts_after[e] for e in PHASE2C2B_DELETE_ORDER},
            **{tbl: EXPECTED_CASCADE_PHYSICAL[tbl]["expected_after"] for tbl in EXPECTED_CASCADE_PHYSICAL},
        },
        "unchanged_counts": {
            k: counts_before[k]
            for k in (
                "users",
                "establecimiento_operativo",
                "denuncia",
                "ruta_trabajo",
                "ruta_grupo",
                "ruta_grupo_inspector",
                "ruta_item",
                "ruta_pool_dia",
                "iniciador_ruta",
            )
        },
        "users_unlock_simulation": diag.get("user_unlock_simulation", {}),
        "catalog_effects_metadata": diag.get("catalog_effects", {}),
        "protected_intersection": 0,
        "protected_closure_detail": closure,
        "protected_comprobacion_regression": comp_reg,
        "validation": {
            "ids_exist": {e: {"expected": len(safe_sets[e]), "found": len(safe_sets[e]), "missing": 0} for e in PHASE2C2B_DELETE_ORDER},
            "act_blockers_zero": True,
            "relevamiento_blockers_zero": True,
            "ot_exclusive": ot_val,
            "delete_order_validated": fk_valid,
            "excluded_intersection": 0,
        },
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3G.1",
        "writes_executed": False,
        "baseline": baseline,
        "manifest": manifest,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def write_freeze_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
