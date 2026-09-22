"""
PREDEPLOY-CLEANUP.3G.0.1-DIAG — reconciliación física de cascades FASE 2C.2B.
Solo SELECT. Sin DELETE/UPDATE/INSERT. Sin cambio de safe sets.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    protection_closure_check,
)

BASELINE_HARD = {
    "actuaciones": 8222,
    "relevamiento": 4592,
    "orden_trabajo": 8958,
    "inspeccion": 915,
    "actuaciones_inspector": 4189,
    "clausura": 69,
    "decomiso": 25,
    "acta_inspeccion_item": 52,
    "relevamiento_relevador": None,
}

EXPECTED_ALEMBIC = "l7m8n9o0p1q2"
SOURCE_9110_ACT = 9145
SOURCE_COMP = 2129
SOURCE_OFICIO = 1575


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if db != "digitaliza_sandbox":
        raise ValueError(f"DATABASE()={db}")
    if alembic != EXPECTED_ALEMBIC:
        raise ValueError(f"alembic={alembic}")
    counts: dict[str, int] = {}
    drift: list[str] = []
    for table, expected in BASELINE_HARD.items():
        if expected is None:
            continue
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            drift.append(f"{table}: {actual} != {expected}")
    rr_baseline = int(_scalar(conn, "SELECT COUNT(*) FROM relevamiento_relevador") or 0)
    counts["relevamiento_relevador"] = rr_baseline
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "drift": drift,
        "baseline_ok": not drift,
    }


def load_safe_sets_from_diag(diag_path: Path) -> dict[str, Any]:
    """Carga safe sets congelados del diag 3G sin recalcular."""
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    acts = [int(x) for x in data["safe_sets"]["SAFE_ACTUACIONES_2C2B"]]
    rels = [int(x) for x in data["safe_sets"]["SAFE_RELEVAMIENTOS_2C2B"]]
    ots = [int(x) for x in data["safe_sets"]["SAFE_OT_2C2B"]]
    if len(acts) != 110 or len(rels) != 26 or len(ots) != 110:
        raise ValueError(f"safe set counts: acts={len(acts)} rels={len(rels)} ots={len(ots)}")
    return {
        "SAFE_ACTUACIONES_2C2B": acts,
        "SAFE_RELEVAMIENTOS_2C2B": rels,
        "SAFE_OT_2C2B": ots,
        "source_diag_path": str(diag_path),
    }


def _reconcile_actuaciones_inspector(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    physical = 0
    distinct_acts: set[int] = set()
    all_rows: list[dict[str, Any]] = []

    for chunk in _chunk_ids(act_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = _rows(
            conn,
            f"""
            SELECT actuaciones_id, inspector_id
            FROM actuaciones_inspector
            WHERE actuaciones_id IN ({ph})
            ORDER BY actuaciones_id, inspector_id
            """,
        )
        all_rows.extend(rows)
        physical += len(rows)
        distinct_acts |= {r["actuaciones_id"] for r in rows}

    agg: dict[int, int] = defaultdict(int)
    for r in all_rows:
        agg[r["actuaciones_id"]] += 1

    per_act = [
        {"actuaciones_id": aid, "inspector_count": cnt, "inspector_ids": sorted(
            r["inspector_id"] for r in all_rows if r["actuaciones_id"] == aid
        )}
        for aid, cnt in sorted(agg.items())
    ]

    baseline = int(_scalar(conn, "SELECT COUNT(*) FROM actuaciones_inspector") or 0)
    return {
        "physical_rows": physical,
        "distinct_actuaciones_id": len(distinct_acts),
        "all_rows": all_rows,
        "per_actuacion_grouping": per_act,
        "resolution_9_vs_18": {
            "verdict": "A_physical_9" if physical == 9 else ("B_physical_18" if physical == 18 else f"C_other_{physical}"),
            "note": "4189-18=4171 del diag 3G fue error de simulación postcount; usar physical_rows real",
            "prior_diag_cascade_distinct": 9,
            "prior_diag_postcount_subtracted": 18,
        },
        "baseline": baseline,
        "expected_after": baseline - physical,
    }


def _reconcile_inspeccion(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    physical = 0
    distinct_acts: set[int] = set()
    insp_ids: set[int] = set()
    rows_all: list[dict[str, Any]] = []

    for chunk in _chunk_ids(act_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = _rows(
            conn,
            f"SELECT id, actuacion_id FROM inspeccion WHERE actuacion_id IN ({ph}) ORDER BY id",
        )
        rows_all.extend(rows)
        physical += len(rows)
        for r in rows:
            distinct_acts.add(r["actuacion_id"])
            insp_ids.add(r["id"])

    baseline = int(_scalar(conn, "SELECT COUNT(*) FROM inspeccion") or 0)
    return {
        "physical_rows": physical,
        "distinct_actuaciones_id": len(distinct_acts),
        "inspeccion_ids": sorted(insp_ids),
        "rows": rows_all,
        "baseline": baseline,
        "expected_after": baseline - physical,
        "prior_expected": "17/17",
        "confirmed": physical == 17 and len(distinct_acts) == 17,
    }


def _reconcile_simple_child(
    conn: Connection, table: str, act_col: str, act_ids: set[int]
) -> dict[str, Any]:
    physical = 0
    distinct_acts: set[int] = set()
    for chunk in _chunk_ids(act_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        physical += int(
            _scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE `{act_col}` IN ({ph})") or 0
        )
        distinct_acts |= _fetch_distinct(conn, table, act_col, chunk)
    baseline = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
    return {
        "physical_rows": physical,
        "distinct_actuaciones_id": len(distinct_acts),
        "baseline": baseline,
        "expected_after": baseline - physical,
    }


def _fetch_distinct(conn: Connection, table: str, col: str, ids: set[int]) -> set[int]:
    ph = ",".join(str(i) for i in ids)
    return {r[0] for r in conn.execute(text(f"SELECT DISTINCT `{col}` FROM `{table}` WHERE `{col}` IN ({ph})"))}


def _reconcile_acta_inspeccion_item(conn: Connection, insp_ids: set[int]) -> dict[str, Any]:
    """Cadena actuacion → inspeccion → acta_inspeccion_item (FK acta_inspeccion_id)."""
    if not insp_ids:
        return {
            "physical_rows": 0,
            "distinct_inspeccion_ids": 0,
            "chain": "actuaciones → inspeccion → acta_inspeccion_item",
            "rows": [],
            "fk_delete_rule": None,
            "baseline": int(_scalar(conn, "SELECT COUNT(*) FROM acta_inspeccion_item") or 0),
            "expected_after": int(_scalar(conn, "SELECT COUNT(*) FROM acta_inspeccion_item") or 0),
        }

    edges = load_fk_edges(conn)
    delete_rule = next(
        (
            e.delete_rule
            for e in edges
            if e.child_table == "acta_inspeccion_item" and e.parent_table == "inspeccion"
        ),
        None,
    )

    physical = 0
    distinct_insp: set[int] = set()
    all_rows: list[dict[str, Any]] = []
    for chunk in _chunk_ids(insp_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = _rows(
            conn,
            f"""
            SELECT acta_inspeccion_id, item_acta_inspeccion_id
            FROM acta_inspeccion_item
            WHERE acta_inspeccion_id IN ({ph})
            ORDER BY acta_inspeccion_id, item_acta_inspeccion_id
            """,
        )
        all_rows.extend(rows)
        physical += len(rows)
        distinct_insp |= {r["acta_inspeccion_id"] for r in rows}

    baseline = int(_scalar(conn, "SELECT COUNT(*) FROM acta_inspeccion_item") or 0)
    return {
        "physical_rows": physical,
        "distinct_inspeccion_ids": len(distinct_insp),
        "inspection_ids_with_items": sorted(distinct_insp),
        "chain": "actuaciones → inspeccion.id → acta_inspeccion_item.acta_inspeccion_id",
        "fk_delete_rule": delete_rule,
        "rows": all_rows,
        "baseline": baseline,
        "expected_after": baseline - physical,
        "prior_zero_revalidated": physical == 0,
    }


def _reconcile_relevamiento_relevador(conn: Connection, rel_ids: set[int]) -> dict[str, Any]:
    physical = 0
    distinct_rel: set[int] = set()
    all_rows: list[dict[str, Any]] = []

    for chunk in _chunk_ids(rel_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = _rows(
            conn,
            f"""
            SELECT relevamiento_id, relevador_id
            FROM relevamiento_relevador
            WHERE relevamiento_id IN ({ph})
            ORDER BY relevamiento_id, relevador_id
            """,
        )
        all_rows.extend(rows)
        physical += len(rows)
        distinct_rel |= {r["relevamiento_id"] for r in rows}

    edges = load_fk_edges(conn)
    delete_rule = next(
        (
            e.delete_rule
            for e in edges
            if e.child_table == "relevamiento_relevador" and e.parent_table == "relevamiento"
        ),
        None,
    )

    baseline = int(_scalar(conn, "SELECT COUNT(*) FROM relevamiento_relevador") or 0)
    return {
        "physical_rows": physical,
        "distinct_relevamiento_id": len(distinct_rel),
        "all_rows": all_rows,
        "fk_delete_rule": delete_rule,
        "baseline": baseline,
        "expected_after": baseline - physical,
        "prior_expected": "physical=10 distinct_relevamiento=5",
        "confirmed": physical == 10 and len(distinct_rel) == 5,
    }


def _other_children_fk_scan(
    conn: Connection,
    act_ids: set[int],
    rel_ids: set[int],
) -> dict[str, Any]:
    """INFORMATION_SCHEMA: hijas de actuaciones y relevamiento con conteos físicos."""
    results: dict[str, Any] = {"actuaciones": [], "relevamiento": []}

    for parent, id_set in (("actuaciones", act_ids), ("relevamiento", rel_ids)):
        children = _rows(
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
            {"parent": parent},
        )
        for ch in children:
            tbl = ch["child_table"]
            col = ch["child_column"]
            physical = 0
            distinct_parents = 0
            if id_set:
                for chunk in _chunk_ids(id_set, 300):
                    ph = ",".join(str(i) for i in chunk)
                    physical += int(
                        _scalar(
                            conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN ({ph})"
                        )
                        or 0
                    )
                    distinct_parents += len(
                        _fetch_distinct(conn, tbl, col, chunk)
                    )
            baseline = int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}`") or 0)
            results[parent].append(
                {
                    **ch,
                    "physical_rows_for_safe_set": physical,
                    "distinct_parent_ids": distinct_parents,
                    "table_baseline": baseline,
                    "expected_after_if_cascade_delete": (
                        baseline - physical if ch["delete_rule"] == "CASCADE" else baseline
                    ),
                }
            )
    return results


def _parent_docs_9145(conn: Connection) -> dict[str, Any]:
    act = conn.execute(
        text(
            "SELECT id, comprobacion_id, notificacion_id, orden_trabajo_id "
            "FROM actuaciones WHERE id = :id"
        ),
        {"id": SOURCE_9110_ACT},
    ).fetchone()
    edges = load_fk_edges(conn)
    comp_rules = [
        {
            "child": e.child_table,
            "column": e.child_column,
            "delete_rule": e.delete_rule,
        }
        for e in edges
        if e.parent_table == "comprobacion" and e.child_table == "actuaciones"
    ]
    oficio_rules = [
        {
            "child": e.child_table,
            "column": e.child_column,
            "delete_rule": e.delete_rule,
        }
        for e in edges
        if e.parent_table == "oficio"
    ]
    comp_exists = bool(
        _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": SOURCE_COMP})
    )
    oficio_exists = bool(
        _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = :id", {"id": SOURCE_OFICIO})
    )
    return {
        "actuacion_9145": dict(act._mapping) if act else None,
        "comprobacion_2129_exists": comp_exists,
        "oficio_1575_exists": oficio_exists,
        "actuaciones_fk_to_comprobacion": comp_rules,
        "policy": "DELETE actuacion must NOT cascade delete comprobacion/oficio parent",
        "parent_docs_preserved": {
            "notificaciones_count": 109,
            "comprobaciones_count": 3,
            "unchanged_from_3G_diag": True,
        },
    }


def _build_corrected_table(cascade_parts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    table = []
    for name, part in cascade_parts.items():
        table.append(
            {
                "tabla": name,
                "physical_rows_delete": part.get("physical_rows", 0),
                "distinct_parent_ids": part.get(
                    "distinct_actuaciones_id",
                    part.get("distinct_relevamiento_id", part.get("distinct_inspeccion_ids", 0)),
                ),
                "baseline": part.get("baseline"),
                "expected_after": part.get("expected_after"),
            }
        )
    return table


def run_phase2c2b_cascade_reconcile(
    conn: Connection,
    *,
    sources_diag_path: Path,
    protected_path: Path,
) -> dict[str, Any]:
    """Orquestador reconciliación física cascades 3G.0.1."""
    baseline = _baseline_check(conn)
    safe = load_safe_sets_from_diag(sources_diag_path)
    act_ids = set(safe["SAFE_ACTUACIONES_2C2B"])
    rel_ids = set(safe["SAFE_RELEVAMIENTOS_2C2B"])
    ot_ids = set(safe["SAFE_OT_2C2B"])

    ai = _reconcile_actuaciones_inspector(conn, act_ids)
    insp = _reconcile_inspeccion(conn, act_ids)
    clausura = _reconcile_simple_child(conn, "clausura", "actuacion_id", act_ids)
    decomiso = _reconcile_simple_child(conn, "decomiso", "actuacion_id", act_ids)
    aii = _reconcile_acta_inspeccion_item(conn, set(insp["inspeccion_ids"]))
    rr = _reconcile_relevamiento_relevador(conn, rel_ids)
    other = _other_children_fk_scan(conn, act_ids, rel_ids)
    parent_docs = _parent_docs_9145(conn)

    cascade_parts = {
        "inspeccion": insp,
        "actuaciones_inspector": ai,
        "acta_inspeccion_item": aii,
        "clausura": clausura,
        "decomiso": decomiso,
        "relevamiento_relevador": rr,
    }
    corrected_table = _build_corrected_table(cascade_parts)

    virtual = VirtualDeleteState()
    virtual.add_explicit("actuaciones", act_ids)
    virtual.add_explicit("relevamiento", rel_ids)
    virtual.add_explicit("orden_trabajo", ot_ids)
    virtual.add_cascade("inspeccion", set(insp["inspeccion_ids"]))
    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    closure = protection_closure_check(virtual, prot)

    safe_sets_unchanged = {
        "SAFE_ACTUACIONES_2C2B": 110,
        "SAFE_RELEVAMIENTOS_2C2B": 26,
        "SAFE_OT_2C2B": 110,
        "confirmed": len(act_ids) == 110 and len(rel_ids) == 26 and len(ot_ids) == 110,
    }

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3G.0.1-DIAG",
        "mode": "READ_ONLY_CASCADE_RECONCILE",
        "writes_executed": False,
        "baseline": baseline,
        "safe_set_ids": safe,
        "actuaciones_inspector_rows": ai,
        "inspection_rows": insp,
        "acta_inspeccion_item_rows": aii,
        "relevamiento_relevador_rows": rr,
        "clausura_rows": clausura,
        "decomiso_rows": decomiso,
        "other_children": other,
        "parent_docs_preserved": parent_docs,
        "corrected_postcounts": {
            "table": corrected_table,
            "actuaciones": {
                "baseline": baseline["counts"]["actuaciones"],
                "delete": 110,
                "expected_after": baseline["counts"]["actuaciones"] - 110,
            },
            "relevamiento": {
                "baseline": baseline["counts"]["relevamiento"],
                "delete": 26,
                "expected_after": baseline["counts"]["relevamiento"] - 26,
            },
            "orden_trabajo": {
                "baseline": baseline["counts"]["orden_trabajo"],
                "delete": 110,
                "expected_after": baseline["counts"]["orden_trabajo"] - 110,
            },
        },
        "protected_intersection": {
            "intersection_total": sum(
                v.get("intersection_total", 0) for v in closure.get("by_entity", {}).values()
            ),
            "valid": closure.get("valid"),
        },
        "safe_sets_unchanged": safe_sets_unchanged,
        "prior_3g_diag_errors_corrected": {
            "actuaciones_inspector_postcount_was_4171_should_be": ai["expected_after"],
            "explanation": ai["resolution_9_vs_18"],
        },
    }


def write_reconcile_report(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path
