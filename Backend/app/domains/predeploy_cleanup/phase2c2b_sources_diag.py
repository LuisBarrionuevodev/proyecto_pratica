"""
PREDEPLOY-CLEANUP.3G-DIAG — FASE 2C.2B diagnóstico 110 actuaciones + 26 relevamientos + 110 OT.
Solo SELECT. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import RELEVAMIENTOS_QA_IDS, SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges, topological_delete_order
from app.domains.predeploy_cleanup.manifest_io import load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import (
    _rows,
    audit_otro_relevador_qa,
    audit_rubros_test,
    audit_test_streets_graph,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import load_structured_acts_274
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import (
    ACT_DOCUMENT_REF_COLUMNS,
    PROTECTED_ENTITIES_EXPANDED,
    _collect_act_children,
    _fk_for_table,
    _validate_delete_order_fk,
)
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import PROTECTED_COMP_CLOSURE_8
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    cascade_children_of_actuaciones,
    cascade_children_of_relevamiento,
    load_user_fk_columns,
    protection_closure_check,
    recalculate_ots_deletable,
)

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
    "clausura": 69,
    "decomiso": 25,
    "acta_inspeccion_item": 52,
}

SOURCE_9110_INICIADOR = 9110
SOURCE_9110_ACTUACION = 9145


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts: dict[str, int] = {}
    drift: list[str] = []
    for table, expected in BASELINE_POST_2C2A.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            drift.append(f"{table}: {actual} != {expected}")
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": not drift,
        "drift": drift,
        "do_not_reuse_prior_snapshot": bool(drift),
    }


def load_frozen_universes_from_apply(apply_path: Path) -> dict[str, Any]:
    """Carga universos congelados post-2C.2A desde execution report."""
    data = json.loads(apply_path.read_text(encoding="utf-8"))
    acts = [int(x) for x in data["unlock"]["actuaciones"]["unlocked"]]
    rels = [int(x) for x in data["unlock"]["relevamientos"]["unlocked"]]
    ots = [int(x) for x in data["future_2c2b"]["orden_trabajo_110"]]
    blocked_38 = [int(x) for x in data["unlock"]["actuaciones"]["blocked"]]
    if len(acts) != 110:
        raise ValueError(f"expected 110 acts, got {len(acts)}")
    if len(rels) != 26:
        raise ValueError(f"expected 26 relevamientos, got {len(rels)}")
    if len(ots) != 110:
        raise ValueError(f"expected 110 OT, got {len(ots)}")
    if len(blocked_38) != 38:
        raise ValueError(f"expected 38 blocked acts, got {len(blocked_38)}")
    return {
        "acts_110": acts,
        "relevamientos_26": rels,
        "ot_110": ots,
        "blocked_acts_38": blocked_38,
        "sources_snapshot": data.get("sources_snapshot_before", {}),
        "apply_path": str(apply_path),
    }


def _count_ids_exist(conn: Connection, table: str, ids: set[int]) -> int:
    if not ids:
        return 0
    found = 0
    for chunk in _chunk_ids(ids, 400):
        ph = ",".join(str(i) for i in chunk)
        found += int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE id IN ({ph})") or 0)
    return found


def _act_family_breakdown_with_prot(
    conn: Connection,
    act_ids: set[int],
    prot: dict[str, set[int]],
    structured_acts_path: Path,
) -> dict[str, Any]:
    from app.domains.predeploy_cleanup.phase2_blockers_diag import _blocked_act_ids

    set_act_old = _blocked_act_ids(conn, prot)
    set_act_structured = load_structured_acts_274(structured_acts_path)
    old_only = [a for a in act_ids if a in set_act_old and a not in set_act_structured]
    struct_only = [a for a in act_ids if a in set_act_structured and a not in set_act_old]
    both = [a for a in act_ids if a in set_act_old and a in set_act_structured]
    unknown = [a for a in act_ids if a not in set_act_old and a not in set_act_structured]
    return {
        "SET_ACT_OLD": sorted(old_only),
        "SET_ACT_STRUCTURED": sorted(struct_only),
        "BOTH": sorted(both),
        "UNKNOWN_FAMILY": sorted(unknown),
        "SET_ACT_OLD_count": len(old_only),
        "SET_ACT_STRUCTURED_count": len(struct_only),
        "BOTH_count": len(both),
        "UNKNOWN_count": len(unknown),
        "union_148_context": {
            "SET_ACT_OLD_total": len(set_act_old),
            "SET_ACT_STRUCTURED_total": len(set_act_structured),
            "unlocked_from_old": len(old_only) + len(both),
            "unlocked_from_structured": len(struct_only) + len(both),
        },
    }


def _physical_act_children(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    """COUNT(*) físico + DISTINCT padres por tabla hija."""
    tables: list[tuple[str, str, str | None]] = [
        ("inspeccion", "actuacion_id", "id"),
        ("clausura", "actuacion_id", "id"),
        ("decomiso", "actuacion_id", "id"),
        ("actuaciones_inspector", "actuaciones_id", None),
        ("actuacion_media", "actuacion_id", "id"),
        ("actuacion_epicollect_detalle", "actuacion_id", "id"),
    ]
    by_table: dict[str, Any] = {}
    for tbl, col, pk_col in tables:
        physical = 0
        distinct_parents: set[int] = set()
        child_ids: set[int] = set()
        for chunk in _chunk_ids(act_ids, 300):
            ph = ",".join(str(i) for i in chunk)
            physical += int(
                _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN ({ph})") or 0
            )
            distinct_parents |= _fetch_ids(
                conn, f"SELECT DISTINCT `{col}` FROM `{tbl}` WHERE `{col}` IN ({ph})"
            )
            if pk_col:
                child_ids |= _fetch_ids(
                    conn, f"SELECT `{pk_col}` FROM `{tbl}` WHERE `{col}` IN ({ph})"
                )
        by_table[tbl] = {
            "physical_rows": physical,
            "distinct_parent_ids": len(distinct_parents),
            "child_row_ids_count": len(child_ids),
        }

    insp_ids: set[int] = set()
    for chunk in _chunk_ids(act_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        insp_ids |= _fetch_ids(conn, f"SELECT id FROM inspeccion WHERE actuacion_id IN ({ph})")

    aii_physical = 0
    aii_distinct_insp = set()
    if insp_ids:
        for chunk in _chunk_ids(insp_ids, 300):
            ph = ",".join(str(i) for i in chunk)
            aii_physical += int(
                _scalar(
                    conn,
                    f"SELECT COUNT(*) FROM acta_inspeccion_item WHERE acta_inspeccion_id IN ({ph})",
                )
                or 0
            )
            aii_distinct_insp |= _fetch_ids(
                conn,
                f"SELECT DISTINCT acta_inspeccion_id FROM acta_inspeccion_item WHERE acta_inspeccion_id IN ({ph})",
            )

    by_table["acta_inspeccion_item"] = {
        "physical_rows": aii_physical,
        "distinct_inspeccion_ids": len(aii_distinct_insp),
        "chain": "actuacion → inspeccion → acta_inspeccion_item",
    }

    ai = by_table.get("actuaciones_inspector", {})
    return {
        "by_table": by_table,
        "actuaciones_inspector_note": {
            "physical_rows": ai.get("physical_rows"),
            "distinct_actuaciones_id": ai.get("distinct_parent_ids"),
            "physical_ne_distinct": ai.get("physical_rows") != ai.get("distinct_parent_ids"),
        },
    }


def _act_blockers(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    per_act: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    safe: list[int] = []
    for aid in sorted(act_ids):
        ini = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}"))
        ri = sorted(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}"))
        rp = sorted(_fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}"))
        rec = {
            "actuacion_id": aid,
            "iniciador_ruta_refs": ini,
            "ruta_item_refs": ri,
            "ruta_pool_refs": rp,
        }
        per_act.append(rec)
        if ini or ri or rp:
            blocked.append({**rec, "classification": "BLOCKED_ACT_2C2B"})
        else:
            safe.append(aid)
    return {
        "per_act": per_act,
        "SAFE_ROUTING": safe,
        "BLOCKED_ACT_2C2B": blocked,
        "expected_all_unblocked_post_2c2a": len(blocked) == 0,
    }


def _parent_docs_preserved(conn: Connection, act_ids: set[int], prot: dict[str, set[int]]) -> dict[str, Any]:
    doc_refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for col in ACT_DOCUMENT_REF_COLUMNS:
        tbl = col.replace("_id", "")
        for chunk in _chunk_ids(act_ids, 300):
            ph = ",".join(str(i) for i in chunk)
            rows = conn.execute(
                text(f"SELECT id, {col} FROM actuaciones WHERE id IN ({ph}) AND {col} IS NOT NULL")
            ).fetchall()
            for r in rows:
                doc_id = r[1]
                doc_refs[tbl].append(
                    {
                        "actuacion_id": r[0],
                        "document_id": doc_id,
                        "in_protected": doc_id in prot.get(tbl, set()),
                        "policy": "NO_DELETE_IN_2C2B",
                    }
                )
    protected_doc_cases = [
        ref for refs in doc_refs.values() for ref in refs if ref["in_protected"]
    ]
    return {
        "document_refs": dict(doc_refs),
        "notificacion_ids": sorted({r["document_id"] for r in doc_refs.get("notificacion", [])}),
        "comprobacion_ids": sorted({r["document_id"] for r in doc_refs.get("comprobacion", [])}),
        "protected_document_cases": protected_doc_cases,
        "note": "parent docs stay intact even when actuacion test deleted",
    }


def _classify_acts_safe(
    conn: Connection,
    act_ids: set[int],
    prot: dict[str, set[int]],
    children_report: dict[str, Any],
    routing: dict[str, Any],
) -> dict[str, Any]:
    safe: list[int] = []
    blocked: list[dict[str, Any]] = []
    children_by_table = children_report.get("children_by_table", {})
    doc_refs = children_report.get("document_refs_on_actuaciones", {})

    for aid in sorted(act_ids):
        reasons: list[str] = []
        if aid in prot.get("actuaciones", set()):
            reasons.append("PROTECTED_ACT")
        for entity in PROTECTED_ENTITIES_EXPANDED:
            pids = prot.get(entity, set())
            if not pids:
                continue
            for tbl, ids in children_by_table.items():
                if entity in (tbl, tbl.replace("_id", "")):
                    child_rows = _fetch_ids(
                        conn,
                        f"SELECT id FROM `{tbl}` WHERE actuacion_id = {aid}"
                        if tbl != "actuaciones_inspector"
                        else f"SELECT actuaciones_id FROM actuaciones_inspector WHERE actuaciones_id = {aid}",
                    )
                    if child_rows & pids:
                        reasons.append(f"PROTECTED_CHILD_{entity}")
        b = next((x for x in routing["per_act"] if x["actuacion_id"] == aid), None)
        if b and (b["iniciador_ruta_refs"] or b["ruta_item_refs"] or b["ruta_pool_refs"]):
            reasons.append("ROUTING_BLOCKER")
        if reasons:
            blocked.append({"actuacion_id": aid, "reasons": reasons})
        else:
            safe.append(aid)

    return {
        "SAFE_ACTUACIONES_2C2B": safe,
        "SAFE_count": len(safe),
        "BLOCKED_ACTUACIONES_2C2B": blocked,
        "BLOCKED_count": len(blocked),
        "protected_intersection": sorted(act_ids & prot.get("actuaciones", set())),
    }


def _analyze_ot_frozen(
    conn: Connection,
    ot_ids: set[int],
    safe_act_ids: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    ot_fk = _fk_for_table(conn, "orden_trabajo")
    per_ot: list[dict[str, Any]] = []
    safe: list[int] = []
    blocked: list[dict[str, Any]] = []

    prot_ot = prot.get("orden_trabajo", set())
    for ot_id in sorted(ot_ids):
        acts_on_ot = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        outside = acts_on_ot - safe_act_ids
        numero = _scalar(conn, "SELECT numero_acta FROM orden_trabajo WHERE id = :id", {"id": ot_id})
        incoming_refs: dict[str, int] = {}
        for ch in ot_fk["children"]:
            tbl, col = ch["child_table"], ch["child_column"]
            n = int(
                _scalar(
                    conn,
                    f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :id",
                    {"id": ot_id},
                )
                or 0
            )
            if n:
                incoming_refs[tbl] = n

        reasons: list[str] = []
        if ot_id in prot_ot:
            reasons.append("OT_PROTECTED")
        if outside:
            reasons.append(f"acts_outside_safe:{sorted(outside)[:5]}")
        if incoming_refs and any(tbl != "actuaciones" for tbl in incoming_refs):
            reasons.append(f"non_act_refs:{incoming_refs}")

        rec = {
            "orden_trabajo_id": ot_id,
            "numero_acta": numero,
            "acts_on_ot": sorted(acts_on_ot),
            "acts_outside_safe": sorted(outside),
            "incoming_fk_refs": incoming_refs,
        }
        per_ot.append(rec)
        if reasons:
            blocked.append({**rec, "reasons": reasons, "classification": "BLOCKED_OT_2C2B"})
        else:
            safe.append(ot_id)

    deletable, blocked_recalc, _ = recalculate_ots_deletable(
        conn, ot_ids, prot_ot, safe_act_ids, prot.get("actuaciones", set())
    )

    return {
        "fk_schema": ot_fk,
        "per_ot": per_ot,
        "SAFE_OT_2C2B": sorted(safe),
        "SAFE_count": len(safe),
        "BLOCKED_OT_2C2B": blocked,
        "BLOCKED_count": len(blocked),
        "recalculate_ots_deletable": sorted(deletable),
        "recalculate_blocked": sorted(blocked_recalc),
        "simulated_orphan_after_act_delete": [
            {
                "orden_trabajo_id": ot_id,
                "remaining_acts": sorted(
                    _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
                    - safe_act_ids
                ),
            }
            for ot_id in sorted(ot_ids)
        ],
    }


def _analyze_relevamientos_26(
    conn: Connection,
    rel_ids: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    buckets: Counter[str] = Counter()
    junction_rows = 0
    distinct_rel_junction: set[int] = set()
    domicilio_ids: list[int] = []
    rubro_ids: list[int | None] = []
    legacy_inspector: list[dict[str, Any]] = []

    rel_fk = _fk_for_table(conn, "relevamiento")

    for rid in sorted(rel_ids):
        row = conn.execute(
            text(
                """
                SELECT r.id, r.domicilio_id, r.rubro_id, r.inspector_id,
                       r.created_by_user_id, u.username
                FROM relevamiento r
                LEFT JOIN users u ON u.id = r.created_by_user_id
                WHERE r.id = :id
                """
            ),
            {"id": rid},
        ).fetchone()
        if not row:
            items.append({"relevamiento_id": rid, "missing": True})
            buckets["MISSING"] += 1
            continue

        r = dict(row._mapping)
        domicilio_ids.append(r.get("domicilio_id"))
        rubro_ids.append(r.get("rubro_id"))
        if r.get("inspector_id"):
            legacy_inspector.append({"relevamiento_id": rid, "inspector_id": r["inspector_id"]})

        rr_rows = _rows(
            conn,
            "SELECT relevador_id, relevamiento_id FROM relevamiento_relevador WHERE relevamiento_id = :id",
            {"id": rid},
        )
        junction_rows += len(rr_rows)
        distinct_rel_junction.add(rid)

        relevadores = _rows(
            conn,
            """
            SELECT rel.id, rel.nombre FROM relevador rel
            JOIN relevamiento_relevador rr ON rr.relevador_id = rel.id
            WHERE rr.relevamiento_id = :rid
            """,
            {"rid": rid},
        )
        ini = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}"))
        ri = sorted(
            _fetch_ids(
                conn,
                f"SELECT ri.id FROM ruta_item ri "
                f"JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id "
                f"WHERE ir.relevamiento_id = {rid}",
            )
        )
        rp = sorted(
            _fetch_ids(
                conn,
                f"SELECT rp.id FROM ruta_pool_dia rp "
                f"JOIN iniciador_ruta ir ON ir.id = rp.iniciador_ruta_id "
                f"WHERE ir.relevamiento_id = {rid}",
            )
        )

        reasons: list[str] = []
        if rid in prot.get("relevamiento", set()):
            reasons.append("PROTECTED")
        if ini:
            reasons.append(f"iniciador_ruta:{ini}")
        if ri:
            reasons.append(f"ruta_item:{ri}")
        if rp:
            reasons.append(f"ruta_pool:{rp}")

        if reasons:
            bucket = "BLOCKED_RELEVAMIENTO_2C2B"
        else:
            bucket = "SAFE_RELEVAMIENTO_2C2B"

        buckets[bucket] += 1
        items.append(
            {
                "relevamiento_id": rid,
                "relevadores": relevadores,
                "relevamiento_relevador_rows": rr_rows,
                "domicilio_id": r.get("domicilio_id"),
                "rubro_id": r.get("rubro_id"),
                "inspector_id_legacy": r.get("inspector_id"),
                "created_by_user_id": r.get("created_by_user_id"),
                "username": r.get("username"),
                "iniciador_refs": ini,
                "ruta_item_refs": ri,
                "ruta_pool_refs": rp,
                "classification": bucket,
                "is_qa_focus": rid in RELEVAMIENTOS_QA_IDS,
                "block_reasons": reasons,
            }
        )

    qa_sim = audit_otro_relevador_qa(conn)
    rel_id_qa = qa_sim.get("relevador_id")
    remaining_qa_refs = []
    if rel_id_qa:
        remaining_qa_refs = _rows(
            conn,
            f"""
            SELECT rr.relevamiento_id FROM relevamiento_relevador rr
            WHERE rr.relevador_id = :rid
              AND rr.relevamiento_id NOT IN ({','.join(str(i) for i in sorted(rel_ids)) or '0'})
            """,
            {"rid": rel_id_qa},
        )

    cascade_rel = cascade_children_of_relevamiento(conn, rel_ids)

    return {
        "expected_count": 26,
        "present_count": _count_ids_exist(conn, "relevamiento", rel_ids),
        "qa_focus": {str(k): k in rel_ids for k in RELEVAMIENTOS_QA_IDS},
        "fk_schema": rel_fk,
        "items": items,
        "classification_buckets": dict(buckets),
        "SAFE_RELEVAMIENTOS_2C2B": sorted(
            i["relevamiento_id"] for i in items if i.get("classification") == "SAFE_RELEVAMIENTO_2C2B"
        ),
        "BLOCKED_RELEVAMIENTOS_2C2B": [
            i for i in items if i.get("classification") == "BLOCKED_RELEVAMIENTO_2C2B"
        ],
        "relevamiento_relevador": {
            "distinct_relevamientos": len(distinct_rel_junction),
            "physical_junction_rows": junction_rows,
            "cascade_ids_distinct_relevamiento_id": len(cascade_rel.get("relevamiento_relevador", set())),
        },
        "legacy_inspector_id": legacy_inspector,
        "domicilio_ids": sorted({d for d in domicilio_ids if d}),
        "domicilio_policy": "NO_DELETE",
        "rubro_ids": sorted({r for r in rubro_ids if r}),
        "rubro_policy": "NO_DELETE",
        "otro_relevador_qa_simulation": {
            "current": qa_sim,
            "refs_after_26_deleted": remaining_qa_refs,
            "expected_refs_zero": len(remaining_qa_refs) == 0,
            "relevador_catalog_policy": "READY_FOR_PHASE2E_NOT_IN_2C2B",
        },
    }


def _source_9110_analysis(conn: Connection, safe_acts: set[int]) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT id, tipo_iniciador, notificacion_id, comprobacion_id, oficio_id,
                   actuacion_id, relevamiento_id
            FROM iniciador_ruta WHERE id = :id
            """
        ),
        {"id": SOURCE_9110_INICIADOR},
    ).fetchone()
    ini_exists = bool(row)
    act_in_safe = SOURCE_9110_ACTUACION in safe_acts
    preserved: dict[str, Any] = {}
    for col, tbl in (
        ("comprobacion_id", "comprobacion"),
        ("oficio_id", "oficio"),
        ("actuacion_id", "actuaciones"),
    ):
        if row and row._mapping.get(col):
            vid = row._mapping[col]
            preserved[col] = {
                "id": vid,
                "exists_before": bool(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE id = :id", {"id": vid})),
                "delete_in_2c2b": act_in_safe and col == "actuacion_id",
                "must_remain_after": col != "actuacion_id" or not act_in_safe,
            }
    act_row = conn.execute(
        text("SELECT id, comprobacion_id, notificacion_id FROM actuaciones WHERE id = :id"),
        {"id": SOURCE_9110_ACTUACION},
    ).fetchone()
    return {
        "iniciador_9110_still_exists": ini_exists,
        "actuacion_9145_in_SAFE_ACTUACIONES_2C2B": act_in_safe,
        "iniciador_snapshot": dict(row._mapping) if row else None,
        "actuacion_9145_row": dict(act_row._mapping) if act_row else None,
        "preserved_sources": preserved,
        "policy": "DELETE act 9145 must NOT delete comprobacion 2129 nor oficio 1575",
    }


def _protected_comp_regression(conn: Connection, prot: dict[str, set[int]]) -> dict[str, Any]:
    found = {}
    in_prot = {}
    for cid in PROTECTED_COMP_CLOSURE_8:
        found[cid] = bool(_scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid}))
        in_prot[cid] = cid in prot.get("comprobacion", set())
    return {
        "closure_8_ids": sorted(PROTECTED_COMP_CLOSURE_8),
        "exist_in_db": found,
        "in_expanded_protected": in_prot,
        "all_protected": all(in_prot.values()) and all(found.values()),
    }


def _cascade_simulation_2c2b(
    conn: Connection,
    safe_acts: set[int],
    safe_rels: set[int],
    safe_ots: set[int],
    prot: dict[str, set[int]],
    edges: list,
) -> dict[str, Any]:
    cascade_acts = cascade_children_of_actuaciones(conn, safe_acts)
    cascade_rel = cascade_children_of_relevamiento(conn, safe_rels)

    physical_ai = 0
    for chunk in _chunk_ids(safe_acts, 300):
        ph = ",".join(str(i) for i in chunk)
        physical_ai += int(
            _scalar(conn, f"SELECT COUNT(*) FROM actuaciones_inspector WHERE actuaciones_id IN ({ph})") or 0
        )

    virtual = VirtualDeleteState()
    virtual.add_explicit("actuaciones", safe_acts)
    for tbl, ids in cascade_acts.items():
        virtual.add_cascade(tbl, ids)
    virtual.add_explicit("relevamiento", safe_rels)
    for tbl, ids in cascade_rel.items():
        virtual.add_cascade(tbl, ids)
    virtual.add_explicit("orden_trabajo", safe_ots)
    closure = protection_closure_check(virtual, prot)

    counts_before = {t: int(_scalar(conn, f"SELECT COUNT(*) FROM `{t}`") or 0) for t in BASELINE_POST_2C2A}
    post = dict(counts_before)
    post["actuaciones"] -= len(safe_acts)
    post["relevamiento"] -= len(safe_rels)
    post["orden_trabajo"] -= len(safe_ots)
    for tbl, ids in cascade_acts.items():
        if tbl in post:
            post[tbl] -= len(ids)
    if "actuaciones_inspector" in post:
        post["actuaciones_inspector"] -= physical_ai

    delete_entities = ["actuaciones", "relevamiento", "orden_trabajo"]
    topo = topological_delete_order(delete_entities, edges)
    fk_valid = _validate_delete_order_fk(delete_entities, edges)

    rr_fk = next(
        (e for e in edges if e.child_table == "relevamiento_relevador" and e.parent_table == "relevamiento"),
        None,
    )

    return {
        "explicit_deletes": {
            "actuaciones": len(safe_acts),
            "relevamiento": len(safe_rels),
            "orden_trabajo": len(safe_ots),
        },
        "cascade_from_actuaciones": {k: len(v) for k, v in cascade_acts.items()},
        "cascade_from_actuaciones_physical": {
            **{k: len(v) for k, v in cascade_acts.items()},
            "actuaciones_inspector_physical_rows": physical_ai,
        },
        "cascade_from_relevamiento": {k: len(v) for k, v in cascade_rel.items()},
        "relevamiento_relevador_delete_rule": rr_fk.delete_rule if rr_fk else None,
        "protected_closure": closure,
        "counts_before": counts_before,
        "counts_after_simulated": post,
        "topological_delete_order": topo,
        "fk_order_validated": fk_valid,
        "delete_order_recommended": (
            ["actuaciones", "relevamiento", "orden_trabajo"]
            if fk_valid["valid"]
            else topo
        ),
    }


def _user_unlock_simulation(
    conn: Connection,
    safe_acts: set[int],
    safe_rels: set[int],
    safe_ots: set[int],
    baseline_fk_free: int,
) -> dict[str, Any]:
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)

    def has_refs(uid: int, skip_acts: set[int], skip_rels: set[int]) -> bool:
        for table, col in fk_columns:
            if table == "actuaciones" and skip_acts:
                n = 0
                for chunk in _chunk_ids(skip_acts, 400):
                    ph = ",".join(str(i) for i in chunk)
                    n += int(
                        _scalar(
                            conn,
                            f"SELECT COUNT(*) FROM actuaciones WHERE `{col}` = :uid AND id NOT IN ({ph})",
                            {"uid": uid},
                        )
                        or 0
                    )
            elif table == "relevamiento" and skip_rels:
                n = 0
                for chunk in _chunk_ids(skip_rels, 400):
                    ph = ",".join(str(i) for i in chunk)
                    n += int(
                        _scalar(
                            conn,
                            f"SELECT COUNT(*) FROM relevamiento WHERE `{col}` = :uid AND id NOT IN ({ph})",
                            {"uid": uid},
                        )
                        or 0
                    )
            else:
                n = int(
                    _scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` = :uid", {"uid": uid}) or 0
                )
            if n:
                return True
        return False

    after_free = 0
    additionally: list[int] = []
    for uid in test_users:
        blocked_now = has_refs(uid, set(), set())
        blocked_after = has_refs(uid, safe_acts, safe_rels)
        if not blocked_after:
            after_free += 1
            if blocked_now:
                additionally.append(uid)

    return {
        "users_test_fk_free_baseline_post_2c2a": baseline_fk_free,
        "users_test_fk_free_after_2c2b_sim": after_free,
        "users_additionally_unlocked_by_2c2b_sim": len(additionally),
        "users_test_still_blocked_sim": len(test_users) - after_free,
        "additionally_unlocked_sample": sorted(additionally)[:40],
    }


def _catalog_effects(conn: Connection, safe_rels: set[int]) -> dict[str, Any]:
    rubros = audit_rubros_test(conn)
    streets = audit_test_streets_graph(conn)
    qa = audit_otro_relevador_qa(conn)

    rubro_refs_after: list[dict[str, Any]] = []
    rubro_entries = []
    for bucket_items in rubros.get("buckets", {}).values():
        rubro_entries.extend(bucket_items)
    for r in rubro_entries:
        rid = r.get("id")
        if not rid:
            continue
        rel_after = 0
        for chunk in _chunk_ids(safe_rels, 300):
            ph = ",".join(str(i) for i in chunk)
            rel_after += int(
                _scalar(
                    conn,
                    f"SELECT COUNT(*) FROM relevamiento WHERE rubro_id = :rid AND id NOT IN ({ph})",
                    {"rid": rid},
                )
                or 0
            )
        rubro_refs_after.append(
            {
                "rubro_id": rid,
                "nombre": r.get("nombre"),
                "relevamiento_refs_before": r.get("relevamientos", 0),
                "relevamiento_refs_after_2c2b_sim": rel_after,
                "future_zero_refs_candidate": rel_after == 0,
            }
        )

    return {
        "otro_relevador_qa": qa,
        "rubros_test": rubros,
        "rubro_refs_after_2c2b_sim_sample": rubro_refs_after[:30],
        "test_streets_fixture": streets,
        "policy": "NO_DELETE catalogos en 2C.2B",
    }


def _reserved_out_of_scope(
    conn: Connection,
    blocked_38: set[int],
    notif_diag_path: Path | None,
) -> dict[str, Any]:
    blocked_present = _count_ids_exist(conn, "actuaciones", blocked_38)
    orphan_notif: list[int] = []
    if notif_diag_path and notif_diag_path.is_file():
        nd = json.loads(notif_diag_path.read_text(encoding="utf-8"))
        orphan_notif = list(
            nd.get("notifications_199_frozen", {}).get("ORPHAN_CONFIRMED_TEST", [])
            or nd.get("orphan_docs_reserved", {}).get("notificaciones_36_ORPHAN_CONFIRMED_TEST", [])
        )
    orphan_notif_present = _count_ids_exist(conn, "notificacion", set(orphan_notif)) if orphan_notif else 0
    return {
        "blocked_acts_38": {
            "expected": 38,
            "present": blocked_present,
            "ids": sorted(blocked_38),
        },
        "orphan_notificaciones_36_reserved_2c2c": {
            "expected": 36,
            "present": orphan_notif_present,
            "policy": "NO_DELETE",
        },
        "orphan_comprobaciones_20_reserved_2c2c": {
            "expected": 20,
            "policy": "NO_DELETE reserved per 3F.1",
        },
    }


def run_phase2c2b_sources_diag(
    conn: Connection,
    *,
    apply_2c2a_path: Path,
    protected_path: Path,
    structured_acts_path: Path,
    notif_source_diag_path: Path | None = None,
    users_fk_free_post_2c2a: int = 812,
) -> dict[str, Any]:
    """Orquestador diagnóstico 3G FASE 2C.2B."""
    baseline = _baseline_check(conn)
    frozen = load_frozen_universes_from_apply(apply_2c2a_path)
    acts_110 = set(frozen["acts_110"])
    rel_26 = set(frozen["relevamientos_26"])
    ot_110 = set(frozen["ot_110"])
    blocked_38 = set(frozen["blocked_acts_38"])

    acts_present = _count_ids_exist(conn, "actuaciones", acts_110)
    rel_present = _count_ids_exist(conn, "relevamiento", rel_26)
    ot_present = _count_ids_exist(conn, "orden_trabajo", ot_110)

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    edges = load_fk_edges(conn)

    family = _act_family_breakdown_with_prot(conn, acts_110, prot, structured_acts_path)
    routing = _act_blockers(conn, acts_110)
    act_fk = _fk_for_table(conn, "actuaciones")
    children = _collect_act_children(conn, acts_110, edges)
    physical = _physical_act_children(conn, acts_110)
    parent_docs = _parent_docs_preserved(conn, acts_110, prot)
    act_class = _classify_acts_safe(conn, acts_110, prot, children, routing)

    safe_acts = set(act_class["SAFE_ACTUACIONES_2C2B"])
    ot_analysis = _analyze_ot_frozen(conn, ot_110, safe_acts, prot)
    safe_ots = set(ot_analysis["SAFE_OT_2C2B"])

    relev = _analyze_relevamientos_26(conn, rel_26, prot)
    safe_rels = set(relev["SAFE_RELEVAMIENTOS_2C2B"])

    cascade = _cascade_simulation_2c2b(conn, safe_acts, safe_rels, safe_ots, prot, edges)
    user_sim = _user_unlock_simulation(conn, safe_acts, safe_rels, safe_ots, users_fk_free_post_2c2a)
    catalog = _catalog_effects(conn, safe_rels)
    reserved = _reserved_out_of_scope(conn, blocked_38, notif_source_diag_path)
    source_9110 = _source_9110_analysis(conn, safe_acts)
    comp_reg = _protected_comp_regression(conn, prot)

    notif_119 = frozen.get("sources_snapshot", {}).get("notificaciones", [])
    notif_119_present = _count_ids_exist(conn, "notificacion", set(notif_119)) if notif_119 else 0

    inter_38 = sorted(safe_acts & blocked_38)

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3G-DIAG",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "source_artifacts": {
            "apply_2c2a": str(apply_2c2a_path),
            "protected_manifest": str(protected_path),
            "structured_acts_diag": str(structured_acts_path),
            "notif_source_diag": str(notif_source_diag_path) if notif_source_diag_path else None,
        },
        "acts_110": {
            "ids": sorted(acts_110),
            "present_count": acts_present,
            "expected_count": 110,
            "act_family_breakdown": family,
            "act_blockers": routing,
            "fk_schema": act_fk,
            "children_fk_report": children,
            "act_children_physical_rows": physical,
            "parent_docs_preserved": parent_docs,
            "classification": act_class,
        },
        "relevamientos_26": relev,
        "ot_110": ot_analysis,
        "safe_sets": {
            "SAFE_ACTUACIONES_2C2B": sorted(safe_acts),
            "SAFE_RELEVAMIENTOS_2C2B": sorted(safe_rels),
            "SAFE_OT_2C2B": sorted(safe_ots),
        },
        "blocked_sets": {
            "BLOCKED_ACTUACIONES_2C2B": act_class["BLOCKED_ACTUACIONES_2C2B"],
            "BLOCKED_RELEVAMIENTOS_2C2B": relev["BLOCKED_RELEVAMIENTOS_2C2B"],
            "BLOCKED_OT_2C2B": ot_analysis["BLOCKED_OT_2C2B"],
        },
        "cascade_simulation": cascade,
        "protected_closure": cascade["protected_closure"],
        "protected_comprobacion_regression": comp_reg,
        "excluded_acts_38": reserved["blocked_acts_38"],
        "intersection_safe_acts_vs_blocked_38": inter_38,
        "orphan_docs_reserved": {
            "notificaciones_36": reserved["orphan_notificaciones_36_reserved_2c2c"],
            "comprobaciones_20": reserved["orphan_comprobaciones_20_reserved_2c2c"],
        },
        "source_notificaciones_119_post_2c2a": {
            "expected": len(notif_119),
            "present": notif_119_present,
            "policy": "NO_DELETE_IN_2C2B",
        },
        "source_9110_analysis": source_9110,
        "user_unlock_simulation": user_sim,
        "catalog_effects": catalog,
        "post_count_simulation": {
            "actuaciones": f"{baseline['counts']['actuaciones']} - {len(safe_acts)} = {baseline['counts']['actuaciones'] - len(safe_acts)}",
            "relevamiento": f"{baseline['counts']['relevamiento']} - {len(safe_rels)} = {baseline['counts']['relevamiento'] - len(safe_rels)}",
            "orden_trabajo": f"{baseline['counts']['orden_trabajo']} - {len(safe_ots)} = {baseline['counts']['orden_trabajo'] - len(safe_ots)}",
            "unchanged": {
                "users": baseline["counts"]["users"],
                "establecimiento_operativo": baseline["counts"]["establecimiento_operativo"],
                "iniciador_ruta": baseline["counts"]["iniciador_ruta"],
                "denuncia": baseline["counts"]["denuncia"],
                "routing_tables": {
                    k: baseline["counts"][k]
                    for k in ("ruta_trabajo", "ruta_grupo", "ruta_item", "ruta_pool_dia")
                },
            },
            "cascade_detail": cascade["counts_after_simulated"],
        },
        "delete_order_recommended": cascade["delete_order_recommended"],
    }


def write_diag_report(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path
