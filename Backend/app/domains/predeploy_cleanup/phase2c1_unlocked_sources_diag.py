"""
PREDEPLOY-CLEANUP.3E-DIAG — FASE 2C.1 diagnóstico actuaciones + denuncias desbloqueadas.
Solo SELECT. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import (
    RELEVAMIENTOS_QA_IDS,
    SQL_TEST_USER_WHERE,
    TEST_ACTUACIONES_SQL,
)
from app.domains.predeploy_cleanup.fk_graph import ForeignKeyEdge, load_fk_edges, topological_delete_order
from app.domains.predeploy_cleanup.manifest_io import file_sha256, load_manifest, validate_ids_exist
from app.domains.predeploy_cleanup.phase2_blockers_diag import _blocked_act_ids, _scalar
from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import load_structured_acts_274
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    cascade_children_of_actuaciones,
    load_user_fk_columns,
    protection_closure_check,
    recalculate_ots_deletable,
)

BASELINE_POST_2B = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8194,
    "actuaciones": 8487,
    "denuncia": 492,
    "relevamiento": 4592,
    "orden_trabajo": 9223,
}

ACT_CHILD_TABLES = (
    "inspeccion",
    "clausura",
    "decomiso",
    "actuaciones_inspector",
    "actuacion_media",
    "actuacion_epicollect_detalle",
)

ACT_DOCUMENT_REF_COLUMNS = ("notificacion_id", "comprobacion_id")

PROTECTED_ENTITIES_EXPANDED = (
    "actuaciones",
    "orden_trabajo",
    "inspeccion",
    "notificacion",
    "comprobacion",
    "clausura",
    "decomiso",
    "oficio",
    "expediente",
)


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts: dict[str, int] = {}
    drift: list[str] = []
    for table, expected in BASELINE_POST_2B.items():
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
    }


def _fk_for_table(conn: Connection, table: str) -> dict[str, list[dict[str, str]]]:
    """FK padres (salientes) e hijos (entrantes) desde INFORMATION_SCHEMA."""
    parents = _rows(
        conn,
        """
        SELECT kcu.TABLE_NAME AS child_table, kcu.COLUMN_NAME AS child_column,
               kcu.REFERENCED_TABLE_NAME AS parent_table,
               kcu.REFERENCED_COLUMN_NAME AS parent_column,
               rc.DELETE_RULE AS delete_rule, rc.UPDATE_RULE AS update_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.TABLE_NAME = :tbl
          AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        """,
        {"tbl": table},
    )
    children = _rows(
        conn,
        """
        SELECT kcu.TABLE_NAME AS child_table, kcu.COLUMN_NAME AS child_column,
               kcu.REFERENCED_TABLE_NAME AS parent_table,
               kcu.REFERENCED_COLUMN_NAME AS parent_column,
               rc.DELETE_RULE AS delete_rule, rc.UPDATE_RULE AS update_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.REFERENCED_TABLE_NAME = :tbl
        """,
        {"tbl": table},
    )
    return {"parents": parents, "children": children}


def _load_act_universes(
    conn: Connection,
    prot: dict[str, set[int]],
    structured_acts_path: Path,
) -> dict[str, Any]:
    """Carga union 413 y clasifica UNLOCKED vs BLOCKED post-2B (criterio congelado)."""
    set_act_old = _blocked_act_ids(conn, prot)
    set_act_structured = load_structured_acts_274(structured_acts_path)
    union_413 = set_act_old | set_act_structured

    unlocked: list[int] = []
    blocked: list[int] = []
    per_act: list[dict[str, Any]] = []

    for aid in sorted(union_413):
        blocking_ini: set[int] = set()
        blocking_ini |= _fetch_ids(
            conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}"
        )
        for iid in _fetch_ids(
            conn,
            f"SELECT DISTINCT iniciador_ruta_id FROM ruta_item WHERE actuacion_id = {aid}",
        ):
            if _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}"):
                blocking_ini.add(iid)
        for iid in _fetch_ids(
            conn,
            f"SELECT DISTINCT iniciador_ruta_id FROM ruta_pool_dia WHERE actuacion_id = {aid}",
        ):
            if _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}"):
                blocking_ini.add(iid)

        ri_refs = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp_refs = _fetch_ids(
            conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}"
        )

        if blocking_ini or ri_refs or rp_refs:
            blocked.append(aid)
            status = "STILL_BLOCKED"
        else:
            unlocked.append(aid)
            status = "UNLOCKED_AFTER_2B"

        family = "SET_ACT_OLD" if aid in set_act_old else "SET_ACT_STRUCTURED"
        if aid in set_act_old and aid in set_act_structured:
            family = "BOTH"
        per_act.append(
            {
                "actuacion_id": aid,
                "family": family,
                "status": status,
                "blocking_iniciadores": sorted(blocking_ini),
                "ruta_item_refs": sorted(ri_refs),
                "ruta_pool_refs": sorted(rp_refs),
            }
        )

    missing = [aid for aid in unlocked if not _scalar(
        conn, "SELECT COUNT(*) FROM actuaciones WHERE id = :id", {"id": aid}
    )]

    return {
        "source": "post_2b_unlock_criteria_from_apply_phase2b",
        "SET_ACT_OLD_count": len(set_act_old),
        "SET_ACT_STRUCTURED_count": len(set_act_structured),
        "union_413_count": len(union_413),
        "overlap_old_structured": sorted(set_act_old & set_act_structured),
        "UNLOCKED_AFTER_2B_ids": unlocked,
        "UNLOCKED_AFTER_2B_count": len(unlocked),
        "STILL_BLOCKED_ids": blocked,
        "STILL_BLOCKED_count": len(blocked),
        "missing_unlocked_ids": missing,
        "family_breakdown_unlocked": {
            "SET_ACT_OLD": len([a for a in unlocked if a in set_act_old and a not in set_act_structured]),
            "SET_ACT_STRUCTURED": len([a for a in unlocked if a in set_act_structured and a not in set_act_old]),
            "BOTH": len([a for a in unlocked if a in set_act_old and a in set_act_structured]),
        },
        "per_act": per_act,
    }


def _load_den_universe(conn: Connection) -> dict[str, Any]:
    cleanup_den = _fetch_ids(
        conn,
        f"""
        SELECT d.id FROM denuncia d
        JOIN users u ON u.id = d.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    unlocked: list[int] = []
    blocked: list[int] = []
    detail: list[dict[str, Any]] = []

    for did in sorted(cleanup_den):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE denuncia_id = {did}")
        ri_surv = rp_surv = 0
        for iid in inis:
            ri_surv += len(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}"))
            rp_surv += len(
                _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}")
            )
        if inis or ri_surv or rp_surv:
            blocked.append(did)
            status = "STILL_BLOCKED"
        else:
            unlocked.append(did)
            status = "UNLOCKED_FOR_PHASE2C"

        detail.append(
            {
                "denuncia_id": did,
                "iniciadores_surviving": sorted(inis),
                "ruta_item_surviving": ri_surv,
                "ruta_pool_surviving": rp_surv,
                "status": status,
            }
        )

    missing = [d for d in unlocked if not _scalar(
        conn, "SELECT COUNT(*) FROM denuncia WHERE id = :id", {"id": d}
    )]

    return {
        "source": "post_2b_unlock_criteria_from_apply_phase2b",
        "total_test_denuncias": len(cleanup_den),
        "UNLOCKED_FOR_PHASE2C_ids": unlocked,
        "UNLOCKED_FOR_PHASE2C_count": len(unlocked),
        "STILL_BLOCKED_ids": blocked,
        "STILL_BLOCKED_count": len(blocked),
        "missing_unlocked_ids": missing,
        "detail": detail,
    }


def _collect_act_children(
    conn: Connection,
    act_ids: set[int],
    edges: list[ForeignKeyEdge],
) -> dict[str, Any]:
    """Hijos directos de actuaciones con clasificación FK."""
    child_edges = [e for e in edges if e.parent_table == "actuaciones"]
    by_table: dict[str, set[int]] = defaultdict(set)
    by_rule: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))

    for edge in child_edges:
        for chunk in _chunk_ids(act_ids, 300):
            ph = ",".join(str(i) for i in chunk)
            col_rows = conn.execute(
                text(
                    """
                    SELECT COLUMN_NAME FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = :tbl
                      AND COLUMN_NAME = 'id'
                    """
                ),
                {"tbl": edge.child_table},
            ).fetchall()
            if col_rows:
                rows = conn.execute(
                    text(
                        f"SELECT id FROM `{edge.child_table}` "
                        f"WHERE `{edge.child_column}` IN ({ph})"
                    )
                ).fetchall()
                ids = {r[0] for r in rows}
            else:
                rows = conn.execute(
                    text(
                        f"SELECT `{edge.child_column}` FROM `{edge.child_table}` "
                        f"WHERE `{edge.child_column}` IN ({ph})"
                    )
                ).fetchall()
                ids = {r[0] for r in rows}
            by_table[edge.child_table].update(ids)
            bucket = (
                "CASCADE_EXPECTED"
                if edge.delete_rule == "CASCADE"
                else "RESTRICT_BLOCKER"
                if edge.delete_rule in ("RESTRICT", "NO ACTION")
                else "SET_NULL_EFFECT"
                if edge.delete_rule == "SET NULL"
                else "OTHER"
            )
            by_rule[bucket][edge.child_table].extend(sorted(ids))

    # Document refs on actuaciones row (notificacion/comprobacion parents)
    doc_refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for col in ACT_DOCUMENT_REF_COLUMNS:
        tbl = col.replace("_id", "")
        for chunk in _chunk_ids(act_ids, 300):
            ph = ",".join(str(i) for i in chunk)
            rows = conn.execute(
                text(
                    f"SELECT id, {col} FROM actuaciones WHERE id IN ({ph}) AND {col} IS NOT NULL"
                )
            ).fetchall()
            for r in rows:
                doc_refs[tbl].append({"actuacion_id": r[0], "document_id": r[1]})

    cascade_known = cascade_children_of_actuaciones(conn, act_ids)

    return {
        "fk_child_edges_count": len(child_edges),
        "children_by_table": {k: sorted(v) for k, v in by_table.items()},
        "children_counts": {k: len(v) for k, v in by_table.items()},
        "by_fk_rule": {
            rule: {tbl: sorted(set(ids)) for tbl, ids in tables.items()}
            for rule, tables in by_rule.items()
        },
        "document_refs_on_actuaciones": dict(doc_refs),
        "cascade_children_known": {k: sorted(v) for k, v in cascade_known.items()},
    }


def _classify_acts_for_delete(
    conn: Connection,
    unlocked_ids: set[int],
    prot: dict[str, set[int]],
    children_report: dict[str, Any],
) -> dict[str, Any]:
    safe: list[int] = []
    blocked: list[dict[str, Any]] = []

    children_by_table = children_report.get("children_by_table", {})
    doc_refs = children_report.get("document_refs_on_actuaciones", {})

    for aid in sorted(unlocked_ids):
        reasons: list[str] = []
        if aid in prot.get("actuaciones", set()):
            reasons.append("PROTECTED_ACT")

        for entity in PROTECTED_ENTITIES_EXPANDED:
            pids = prot.get(entity, set())
            if not pids:
                continue
            for tbl, ids in children_by_table.items():
                if tbl == entity or tbl.replace("_id", "") == entity:
                    overlap = set(ids) & pids
                    if overlap:
                        reasons.append(f"PROTECTED_CHILD_{entity}:{sorted(overlap)[:3]}")

        for tbl, refs in doc_refs.items():
            prot_docs = prot.get(tbl, set())
            for ref in refs:
                if ref["actuacion_id"] == aid and ref["document_id"] in prot_docs:
                    reasons.append(f"PROTECTED_DOC_{tbl}:{ref['document_id']}")

        ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}")
        if ini:
            reasons.append(f"iniciador_ruta_refs:{sorted(ini)[:5]}")
        if ri:
            reasons.append(f"ruta_item_refs:{sorted(ri)[:5]}")
        if rp:
            reasons.append(f"ruta_pool_refs:{sorted(rp)[:5]}")

        if reasons:
            blocked.append({"actuacion_id": aid, "reasons": reasons})
        else:
            safe.append(aid)

    return {
        "SAFE_ACTUACIONES_2C1": safe,
        "SAFE_count": len(safe),
        "BLOCKED_ACTUACIONES_2C1": blocked,
        "BLOCKED_count": len(blocked),
    }


def _analyze_ot(
    conn: Connection,
    safe_act_ids: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    ot_map: dict[int, list[int]] = defaultdict(list)
    ot_numero: dict[int, str | None] = {}
    for chunk in _chunk_ids(safe_act_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = conn.execute(
            text(
                f"""
                SELECT a.id, a.orden_trabajo_id, ot.numero_acta
                FROM actuaciones a
                LEFT JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
                WHERE a.id IN ({ph})
                """
            )
        ).fetchall()
        for r in rows:
            if r[1]:
                ot_map[r[1]].append(r[0])
                ot_numero[r[1]] = r[2]

    exclusive: list[dict[str, Any]] = []
    shared: list[dict[str, Any]] = []
    protected_ot: list[dict[str, Any]] = []
    indeterminate: list[dict[str, Any]] = []
    no_ot: list[int] = []

    prot_ot = prot.get("orden_trabajo", set())
    prot_act = prot.get("actuaciones", set())

    for aid in safe_act_ids:
        row = conn.execute(
            text("SELECT orden_trabajo_id FROM actuaciones WHERE id = :id"),
            {"id": aid},
        ).fetchone()
        if not row or not row[0]:
            no_ot.append(aid)
            continue

    unique_ots = set(ot_map.keys())
    for ot_id in sorted(unique_ots):
        acts_on_ot = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        candidate_acts = acts_on_ot & safe_act_ids
        outside = acts_on_ot - safe_act_ids
        rec = {
            "orden_trabajo_id": ot_id,
            "numero_acta": ot_numero.get(ot_id),
            "acts_on_ot": len(acts_on_ot),
            "acts_in_candidate": len(candidate_acts),
            "acts_outside_candidate": sorted(outside)[:10],
        }
        if ot_id in prot_ot:
            protected_ot.append({**rec, "classification": "OT_PROTECTED"})
        elif outside & prot_act:
            indeterminate.append({**rec, "classification": "OT_INDETERMINATE"})
        elif outside:
            shared.append({**rec, "classification": "OT_SHARED"})
        else:
            exclusive.append({**rec, "classification": "OT_EXCLUSIVE_TEST"})

    ot_candidates = unique_ots | set()
    deletable, blocked_ot, detail = recalculate_ots_deletable(
        conn,
        ot_candidates,
        prot_ot,
        safe_act_ids,
        prot_act,
    )

    orphan_after_sim: list[dict[str, Any]] = []
    for ot_id in sorted(deletable):
        remaining = _fetch_ids(
            conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}"
        ) - safe_act_ids
        orphan_after_sim.append(
            {
                "orden_trabajo_id": ot_id,
                "numero_acta": ot_numero.get(ot_id),
                "remaining_acts_after_safe_delete": sorted(remaining),
            }
        )

    return {
        "unique_ot_from_safe_acts": len(unique_ots),
        "acts_without_ot": sorted(no_ot),
        "OT_EXCLUSIVE_TEST": exclusive,
        "OT_SHARED": shared,
        "OT_PROTECTED": protected_ot,
        "OT_INDETERMINATE": indeterminate,
        "SAFE_OT_AFTER_ACT_DELETE": sorted(deletable),
        "SAFE_OT_AFTER_ACT_DELETE_count": len(deletable),
        "KEEP_OT": sorted(blocked_ot),
        "KEEP_OT_count": len(blocked_ot),
        "recalculate_detail_sample": detail[:30],
        "orphan_ot_simulation": orphan_after_sim[:50],
        "note": "No asumir 265 OT; X unique OT from safe acts",
    }


def _classify_denuncias(
    conn: Connection,
    unlocked_den: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    safe: list[int] = []
    blocked: list[dict[str, Any]] = []
    domicilio_refs: list[dict[str, Any]] = []

    den_fk = _fk_for_table(conn, "denuncia")

    for did in sorted(unlocked_den):
        reasons: list[str] = []
        if did in prot.get("denuncia", set()):
            reasons.append("PROTECTED_DENUNCIA")

        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE denuncia_id = {did}")
        if inis:
            reasons.append(f"iniciador_ruta:{sorted(inis)}")

        row = conn.execute(
            text("SELECT domicilio_id, created_by_user_id FROM denuncia WHERE id = :id"),
            {"id": did},
        ).fetchone()
        dom_id = row[0] if row else None
        if dom_id:
            total_refs = int(
                _scalar(
                    conn,
                    "SELECT COUNT(*) FROM denuncia WHERE domicilio_id = :d",
                    {"d": dom_id},
                )
                or 0
            )
            domicilio_refs.append(
                {
                    "denuncia_id": did,
                    "domicilio_id": dom_id,
                    "denuncia_refs_to_domicilio": total_refs,
                    "domicilio_policy": "KEEP",
                }
            )

        if reasons:
            blocked.append({"denuncia_id": did, "reasons": reasons})
        else:
            safe.append(did)

    return {
        "SAFE_DENUNCIAS_2C1": safe,
        "SAFE_count": len(safe),
        "BLOCKED_DENUNCIAS_2C1": blocked,
        "BLOCKED_count": len(blocked),
        "denuncia_fk_schema": den_fk,
        "domicilio_refs": domicilio_refs,
    }


def _eo_snapshot(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    with_eo: list[dict[str, Any]] = []
    without_eo = 0
    for chunk in _chunk_ids(act_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = conn.execute(
            text(
                f"SELECT id, establecimiento_operativo_id FROM actuaciones WHERE id IN ({ph})"
            )
        ).fetchall()
        for r in rows:
            if r[1]:
                with_eo.append({"actuacion_id": r[0], "establecimiento_operativo_id": r[1]})
            else:
                without_eo += 1
    return {
        "with_eo_count": len(with_eo),
        "without_eo_count": without_eo,
        "with_eo_sample": with_eo[:40],
        "note": "NO delete EO adicional en 2C.1",
    }


def _cascade_simulation(
    conn: Connection,
    safe_acts: set[int],
    safe_den: set[int],
    safe_ot: set[int],
    prot: dict[str, set[int]],
    edges: list[ForeignKeyEdge],
) -> dict[str, Any]:
    virtual = VirtualDeleteState()
    explicit: dict[str, set[int]] = {
        "actuaciones": safe_acts,
        "denuncia": safe_den,
        "orden_trabajo": safe_ot,
    }

    cascade_from_acts = cascade_children_of_actuaciones(conn, safe_acts)
    for tbl, ids in cascade_from_acts.items():
        virtual.add_cascade(tbl, ids)

    for entity, ids in explicit.items():
        virtual.add_explicit(_table_for_entity(entity), ids)

    closure = protection_closure_check(virtual, prot)

    counts_before = {t: int(_scalar(conn, f"SELECT COUNT(*) FROM `{t}`") or 0) for t in (
        "actuaciones",
        "denuncia",
        "orden_trabajo",
        "inspeccion",
        "notificacion",
        "comprobacion",
        "clausura",
        "decomiso",
        "actuaciones_inspector",
    )}

    post = dict(counts_before)
    post["actuaciones"] -= len(safe_acts)
    post["denuncia"] -= len(safe_den)
    post["orden_trabajo"] -= len(safe_ot)
    for tbl, ids in cascade_from_acts.items():
        if tbl in post:
            post[tbl] -= len(ids)

    delete_order_tables = ["actuaciones", "denuncia", "orden_trabajo"]
    topo = topological_delete_order(delete_order_tables, edges)
    fk_valid_order = _validate_delete_order_fk(delete_order_tables, edges)

    return {
        "explicit_deletes": {k: len(v) for k, v in explicit.items()},
        "cascade_from_actuaciones": {k: len(v) for k, v in cascade_from_acts.items()},
        "cascade_ids_sample": {
            k: sorted(v)[:10] for k, v in cascade_from_acts.items() if v
        },
        "protected_closure": closure,
        "counts_before": counts_before,
        "counts_after_simulated": post,
        "topological_delete_order_raw": topo,
        "topological_delete_order_fk_validated": fk_valid_order,
        "delete_order_recommended": (
            ["actuaciones", "denuncia", "orden_trabajo"]
            if fk_valid_order["valid"]
            else topo
        ),
        "ot_in_same_wave_recommended": len(safe_ot) > 0 and closure["valid"],
    }


def _validate_delete_order_fk(
    delete_order: list[str],
    edges: list[ForeignKeyEdge],
) -> dict[str, Any]:
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
                }
            )
    return {"valid": len(violations) == 0, "violations": violations}


def _user_has_fk_refs(
    conn: Connection,
    uid: int,
    fk_columns: list[tuple[str, str]],
    skip_acts: set[int],
    skip_den: set[int],
) -> bool:
    """True si el usuario tiene alguna FK sobreviviente (con skips opcionales)."""
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
        elif table == "denuncia" and skip_den:
            n = 0
            for chunk in _chunk_ids(skip_den, 400):
                ph = ",".join(str(i) for i in chunk)
                n += int(
                    _scalar(
                        conn,
                        f"SELECT COUNT(*) FROM denuncia WHERE `{col}` = :uid AND id NOT IN ({ph})",
                        {"uid": uid},
                    )
                    or 0
                )
        else:
            n = int(
                _scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` = :uid", {"uid": uid})
                or 0
            )
        if n:
            return True
    return False


def _user_unlock_simulation(
    conn: Connection,
    safe_acts: set[int],
    safe_den: set[int],
    users_fk_free_post_2b: int,
) -> dict[str, Any]:
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)

    after_2c1_free = 0
    additionally: list[int] = []
    for uid in test_users:
        blocked_now = _user_has_fk_refs(conn, uid, fk_columns, set(), set())
        blocked_after = _user_has_fk_refs(conn, uid, fk_columns, safe_acts, safe_den)
        if not blocked_after:
            after_2c1_free += 1
            if blocked_now:
                additionally.append(uid)

    return {
        "users_test_fk_free_post_2b": users_fk_free_post_2b,
        "users_test_fk_free_after_2c1_sim": after_2c1_free,
        "users_additionally_unlocked_by_2c1_sim": len(additionally),
        "users_still_blocked_after_2c1_sim": len(test_users) - after_2c1_free,
        "additionally_unlocked_sample": sorted(additionally)[:40],
    }


def _denuncia_act_overlap(
    conn: Connection,
    safe_acts: set[int],
    safe_den: set[int],
) -> dict[str, Any]:
    """Relaciones denuncia↔actuación (no fusionar por domicilio)."""
    links: list[dict[str, Any]] = []
    for did in sorted(safe_den):
        row = conn.execute(
            text("SELECT domicilio_id FROM denuncia WHERE id = :id"), {"id": did}
        ).fetchone()
        dom_den = row[0] if row else None
        for aid in safe_acts:
            arow = conn.execute(
                text("SELECT domicilio_id FROM actuaciones WHERE id = :id"), {"id": aid}
            ).fetchone()
            dom_act = arow[0] if arow else None
            if dom_den and dom_act and dom_den == dom_act:
                links.append(
                    {
                        "denuncia_id": did,
                        "actuacion_id": aid,
                        "shared_domicilio_id": dom_den,
                        "note": "MISMA_GEO_NO_MISMO_TITULAR",
                    }
                )
    return {
        "shared_domicilio_pairs_count": len(links),
        "sample": links[:20],
        "independent_delete_sets": True,
    }


def _relevamientos_out_of_scope(conn: Connection) -> dict[str, Any]:
    cleanup_rel = _fetch_ids(
        conn,
        f"""
        SELECT r.id FROM relevamiento r
        JOIN users u ON u.id = r.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """
    ) | RELEVAMIENTOS_QA_IDS
    present = _count_ids_exist(conn, "relevamiento", cleanup_rel)
    qa = {}
    for rid in RELEVAMIENTOS_QA_IDS:
        qa[rid] = bool(_scalar(conn, "SELECT COUNT(*) FROM relevamiento WHERE id = :id", {"id": rid}))
    return {
        "total_test_relevamientos": len(cleanup_rel),
        "present": present,
        "out_of_scope": True,
        "qa_focus_present": qa,
    }


def _count_ids_exist(conn: Connection, table: str, ids: set[int]) -> int:
    if not ids:
        return 0
    found = 0
    for chunk in _chunk_ids(ids, 400):
        ph = ",".join(str(i) for i in chunk)
        found += int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE id IN ({ph})") or 0)
    return found


def run_phase2c1_unlocked_sources_diag(
    conn: Connection,
    *,
    protected_path: Path,
    structured_acts_path: Path,
    phase2b_apply_path: Path | None = None,
) -> dict[str, Any]:
    """Orquestador diagnóstico 3E."""
    baseline = _baseline_check(conn)
    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))

    acts_univ = _load_act_universes(conn, prot, structured_acts_path)
    den_univ = _load_den_universe(conn)

    unlocked_acts = set(acts_univ["UNLOCKED_AFTER_2B_ids"])
    unlocked_den = set(den_univ["UNLOCKED_FOR_PHASE2C_ids"])

    if acts_univ["UNLOCKED_AFTER_2B_count"] != 265:
        acts_univ["count_warning"] = f"expected 265 unlocked, got {acts_univ['UNLOCKED_AFTER_2B_count']}"
    if den_univ["UNLOCKED_FOR_PHASE2C_count"] != 75:
        den_univ["count_warning"] = f"expected 75 unlocked, got {den_univ['UNLOCKED_FOR_PHASE2C_count']}"

    prot_act_inter = sorted(unlocked_acts & prot.get("actuaciones", set()))
    prot_den_inter = sorted(unlocked_den & prot.get("denuncia", set()))

    edges = load_fk_edges(conn)
    act_fk = _fk_for_table(conn, "actuaciones")
    children = _collect_act_children(conn, unlocked_acts, edges)
    act_class = _classify_acts_for_delete(conn, unlocked_acts, prot, children)
    ot_analysis = _analyze_ot(conn, set(act_class["SAFE_ACTUACIONES_2C1"]), prot)
    den_class = _classify_denuncias(conn, unlocked_den, prot)
    eo_snap = _eo_snapshot(conn, unlocked_acts)

    safe_acts = set(act_class["SAFE_ACTUACIONES_2C1"])
    safe_den = set(den_class["SAFE_DENUNCIAS_2C1"])
    safe_ot = set(ot_analysis["SAFE_OT_AFTER_ACT_DELETE"])

    cascade = _cascade_simulation(conn, safe_acts, safe_den, safe_ot, prot, edges)

    users_post_2b = 727
    if phase2b_apply_path and phase2b_apply_path.is_file():
        apply_data = json.loads(phase2b_apply_path.read_text(encoding="utf-8"))
        users_post_2b = apply_data.get("users", {}).get("users_test_fk_free", 727)

    user_sim = _user_unlock_simulation(conn, safe_acts, safe_den, users_post_2b)
    overlap = _denuncia_act_overlap(conn, safe_acts, safe_den)
    relev = _relevamientos_out_of_scope(conn)

    protected_preserved_counts = {}
    for entity in PROTECTED_ENTITIES_EXPANDED:
        protected_preserved_counts[entity] = len(prot.get(entity, set()))

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3E-DIAG",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "source_artifacts": {
            "protected_manifest": str(protected_path),
            "structured_acts_diag": str(structured_acts_path),
            "phase2b_apply": str(phase2b_apply_path) if phase2b_apply_path else None,
        },
        "acts_265": {
            "universe": acts_univ,
            "protected_intersection": prot_act_inter,
            "protected_intersection_count": len(prot_act_inter),
            "fk_schema": act_fk,
            "children": children,
            "classification": act_class,
            "eo_snapshot": eo_snap,
        },
        "denuncias_75": {
            "universe": den_univ,
            "protected_intersection": prot_den_inter,
            "protected_intersection_count": len(prot_den_inter),
            "classification": den_class,
        },
        "ot_analysis": ot_analysis,
        "cascade_simulation": cascade,
        "safe_sets": {
            "SAFE_ACTUACIONES_2C1": act_class["SAFE_ACTUACIONES_2C1"],
            "SAFE_DENUNCIAS_2C1": den_class["SAFE_DENUNCIAS_2C1"],
            "SAFE_OT_AFTER_ACT_2C1": ot_analysis["SAFE_OT_AFTER_ACT_DELETE"],
        },
        "blocked_sets": {
            "BLOCKED_ACTUACIONES_2C1": act_class["BLOCKED_ACTUACIONES_2C1"],
            "BLOCKED_DENUNCIAS_2C1": den_class["BLOCKED_DENUNCIAS_2C1"],
            "KEEP_OT": ot_analysis["KEEP_OT"],
            "STILL_BLOCKED_ACTS_148": acts_univ["STILL_BLOCKED_ids"],
        },
        "out_of_scope": {
            "still_blocked_acts_count": acts_univ["STILL_BLOCKED_count"],
            "relevamientos": relev,
        },
        "denuncia_act_overlap": overlap,
        "protected_closure": cascade["protected_closure"],
        "protected_preserved_manifest_counts": protected_preserved_counts,
        "user_unlock_simulation": user_sim,
        "post_count_simulation": {
            "actuaciones": f"{baseline['counts']['actuaciones']} - {len(safe_acts)} = {baseline['counts']['actuaciones'] - len(safe_acts)}",
            "denuncia": f"{baseline['counts']['denuncia']} - {len(safe_den)} = {baseline['counts']['denuncia'] - len(safe_den)}",
            "orden_trabajo": f"{baseline['counts']['orden_trabajo']} - {len(safe_ot)} = {baseline['counts']['orden_trabajo'] - len(safe_ot)}",
            "unchanged": {
                "users": baseline["counts"]["users"],
                "establecimiento_operativo": baseline["counts"]["establecimiento_operativo"],
                "relevamiento": baseline["counts"]["relevamiento"],
            },
            "cascade_detail": cascade["counts_after_simulated"],
        },
        "delete_order_recommended": cascade.get(
            "delete_order_recommended", cascade.get("topological_delete_order_raw")
        ),
        "wave_recommendation": {
            "include_ot_in_2c1": cascade["ot_in_same_wave_recommended"],
            "note": "OT solo si 0 act restantes + CONFIRMADO_TEST + sin protected + FK lo permite",
        },
    }


def write_diag_report(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path
