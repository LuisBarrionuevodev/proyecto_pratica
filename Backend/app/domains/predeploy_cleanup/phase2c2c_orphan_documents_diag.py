"""
PREDEPLOY-CLEANUP.3I-DIAG — FASE 2C.2C documentos test huérfanos post-3H.
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

from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import entity_ids, load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import _validate_delete_order_fk
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import PROTECTED_COMP_CLOSURE_8
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    load_user_fk_columns,
    protection_closure_check,
)

BASELINE_POST_3H = {
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
    "inspeccion": 898,
    "actuaciones_inspector": 4180,
    "acta_inspeccion_item": 52,
    "clausura": 69,
    "decomiso": 25,
    "relevamiento_relevador": 525,
}

EMPTY_ROUTE_IDS = (
    4938, 4944, 5195, 5199, 5204, 5245, 5261, 5550, 5560, 5574, 6372, 6461,
)

USERS_FK_FREE_POST_3H = 833


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _count_ids_exist(conn: Connection, table: str, ids: set[int]) -> int:
    if not ids:
        return 0
    found = 0
    for chunk in _chunk_ids(ids, 400):
        ph = ",".join(str(i) for i in chunk)
        found += int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE id IN ({ph})") or 0)
    return found


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts = {t: _count(conn, t) for t in BASELINE_POST_3H}
    drift = [f"{t}: {counts[t]} != {e}" for t, e in BASELINE_POST_3H.items() if counts[t] != e]
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": not drift,
        "drift": drift,
        "users_test_fk_free_post_3h": USERS_FK_FREE_POST_3H,
    }


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


def _surviving_refs(conn: Connection, parent_table: str, pk_id: int) -> dict[str, Any]:
    """Refs físicas hacia parent_table.id = pk_id (COUNT; no asume columna id en hijos)."""
    by_table: dict[str, dict[str, Any]] = {}
    total = 0
    for edge in _incoming_fk_edges(conn, parent_table):
        tbl, col = edge["child_table"], edge["child_column"]
        n = int(
            _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :id", {"id": pk_id}) or 0
        )
        if n:
            key = f"{tbl}.{col}"
            by_table[key] = {"count": n, "delete_rule": edge["delete_rule"]}
            total += n
    return {"total_refs": total, "by_fk": by_table}


def _cascade_on_delete(conn: Connection, parent_table: str, ids: set[int]) -> dict[str, Any]:
    """Cuenta filas hijas físicas por DELETE_RULE al borrar parent IDs."""
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


def load_historical_candidate_sets(
    *,
    apply_2c2b_path: Path,
    apply_2c2b_prime_path: Path,
    notif_source_diag_path: Path | None = None,
    residual_graph_diag_path: Path | None = None,
) -> dict[str, Any]:
    """Carga universos históricos A/B/C/D."""
    apply_2c2b = json.loads(apply_2c2b_path.read_text(encoding="utf-8"))
    apply_prime = json.loads(apply_2c2b_prime_path.read_text(encoding="utf-8"))

    a_36 = {int(x) for x in apply_2c2b.get("preserved", {}).get("orphan_notificaciones_36", [])}
    b_20 = {int(x) for x in apply_2c2b.get("preserved", {}).get("orphan_comprobaciones_20", [])}
    c_25 = {
        int(x)
        for x in apply_prime.get("new_orphans_post_apply", {}).get("notificaciones", [])
    }
    d_2289 = {2289}

    if notif_source_diag_path and notif_source_diag_path.is_file():
        nd = json.loads(notif_source_diag_path.read_text(encoding="utf-8"))
        frozen = nd.get("notifications_199_frozen", {}).get("ORPHAN_CONFIRMED_TEST", [])
        if frozen and not a_36:
            a_36 = {int(x) for x in frozen}

    if residual_graph_diag_path and residual_graph_diag_path.is_file():
        rd = json.loads(residual_graph_diag_path.read_text(encoding="utf-8"))
        safe_comp = rd.get("safe_sets", {}).get("SAFE_COMPROBACION_ORPHAN_TEST", [])
        if safe_comp and not b_20:
            b_20 = {int(x) for x in safe_comp}

    source_119 = {
        int(x) for x in apply_2c2b.get("preserved", {}).get("source_notificaciones_119", [])
    }

    notif_raw = a_36 | c_25
    comp_raw = b_20 | d_2289

    return {
        "A_existing_36_orphan_notif": sorted(a_36),
        "B_existing_20_orphan_comp": sorted(b_20),
        "C_new_25_orphan_notif_post_3h4": sorted(c_25),
        "D_new_2289_comp": sorted(d_2289),
        "intersections": {
            "A_cap_C_notif": sorted(a_36 & c_25),
            "B_cap_D_comp": sorted(b_20 & d_2289),
        },
        "NOTIF_CANDIDATES_RAW": sorted(notif_raw),
        "COMP_CANDIDATES_RAW": sorted(comp_raw),
        "notif_raw_count": len(notif_raw),
        "comp_raw_count": len(comp_raw),
        "source_notificaciones_119": sorted(source_119),
    }


def _comprobacion_admin_graph(conn: Connection, cid: int) -> dict[str, Any]:
    oficios = _rows(
        conn,
        "SELECT id, numero_oficio, comprobacion_id FROM oficio WHERE comprobacion_id = :id",
        {"id": cid},
    )
    expedientes: list[dict[str, Any]] = []
    for o in oficios:
        expedientes.extend(
            _rows(
                conn,
                "SELECT id, oficio_id FROM expediente WHERE oficio_id = :oid",
                {"oid": o["id"]},
            )
        )
    ini_from_comp = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE comprobacion_id = {cid}"))
    ini_from_oficio: list[int] = []
    for o in oficios:
        ini_from_oficio.extend(
            _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE oficio_id = {o['id']}")
        )
    return {
        "oficios": oficios,
        "expedientes": expedientes,
        "iniciadores_from_comprobacion": ini_from_comp,
        "iniciadores_from_oficio": sorted(set(ini_from_oficio)),
    }


def _classify_notificacion(
    conn: Connection,
    nid: int,
    prot: dict[str, set[int]],
    source_119: set[int],
    origin: dict[str, bool],
    provenance_3f: dict[str, Any] | None,
) -> dict[str, Any]:
    refs = _surviving_refs(conn, "notificacion", nid)
    act_refs = sorted(_fetch_ids(conn, f"SELECT id FROM actuaciones WHERE notificacion_id = {nid}"))
    ini_refs = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE notificacion_id = {nid}"))

    prov: dict[str, Any] = {"origin": origin}
    if provenance_3f and nid in provenance_3f.get("by_id", {}):
        prov["diag_3f"] = provenance_3f["by_id"][nid]

    if nid in prot.get("notificacion", set()):
        classification = "PROTECTED"
        reason = "in_protected_notificacion_set"
    elif act_refs:
        classification = "STILL_REFERENCED"
        reason = f"actuaciones_refs={act_refs[:5]}"
    elif ini_refs:
        classification = "STILL_REFERENCED"
        reason = f"iniciador_ruta_refs={ini_refs[:5]}"
    elif refs["total_refs"] > 0:
        classification = "STILL_REFERENCED"
        reason = f"other_fk_refs={list(refs['by_fk'].keys())[:5]}"
    elif nid in source_119 and ini_refs:
        classification = "INDETERMINATE"
        reason = "source_119_with_surviving_iniciador"
    else:
        classification = "SAFE_ORPHAN_TEST"
        reason = "CONFIRMADO_TEST_orphan_no_surviving_refs"
        if nid in source_119:
            prov["source_119_note"] = "was_source_119_no_surviving_iniciador"

    return {
        "notificacion_id": nid,
        "origin": origin,
        "provenance": prov,
        "surviving_refs": {
            "actuaciones": act_refs,
            "iniciador_ruta": ini_refs,
            "all_fk": refs,
        },
        "in_source_119": nid in source_119,
        "classification": classification,
        "classification_reason": reason,
        "preserve_policy": "NO_DELETE_NO_UPDATE" if classification != "SAFE_ORPHAN_TEST" else None,
    }


def _classify_comprobacion(
    conn: Connection,
    cid: int,
    prot: dict[str, set[int]],
    origin: dict[str, bool],
) -> dict[str, Any]:
    graph = _comprobacion_admin_graph(conn, cid)
    act_refs = sorted(_fetch_ids(conn, f"SELECT id FROM actuaciones WHERE comprobacion_id = {cid}"))
    ini_refs = sorted(
        set(graph["iniciadores_from_comprobacion"]) | set(graph["iniciadores_from_oficio"])
    )
    refs = _surviving_refs(conn, "comprobacion", cid)

    graph_class = "ALL_TEST_ORPHAN"
    if graph["oficios"] or graph["expedientes"]:
        if ini_refs or act_refs:
            graph_class = "STILL_USED"
        elif cid in prot.get("comprobacion", set()) or any(
            o["id"] in prot.get("oficio", set()) for o in graph["oficios"]
        ):
            graph_class = "PROTECTED"
        else:
            graph_class = "ALL_TEST_ORPHAN"

    if cid in prot.get("comprobacion", set()) or cid in PROTECTED_COMP_CLOSURE_8:
        classification = "PROTECTED"
        reason = "protected_comprobacion"
    elif act_refs:
        classification = "STILL_REFERENCED"
        reason = f"actuaciones_refs={act_refs}"
    elif ini_refs:
        classification = "STILL_REFERENCED"
        reason = f"iniciador_refs={ini_refs}"
    elif graph["expedientes"] or graph["oficios"]:
        classification = "INDETERMINATE"
        reason = "expediente_oficio_chain_present"
    elif refs["total_refs"] > 0:
        classification = "STILL_REFERENCED"
        reason = f"other_fk={list(refs['by_fk'].keys())}"
    else:
        classification = "SAFE_ORPHAN_TEST"
        reason = "ORPHAN_TEST_no_surviving_refs"

    return {
        "comprobacion_id": cid,
        "origin": origin,
        "surviving_refs": {
            "actuaciones": act_refs,
            "iniciador_ruta": ini_refs,
            "all_fk": refs,
        },
        "expediente_oficio_graph": graph,
        "graph_classification": graph_class,
        "classification": classification,
        "classification_reason": reason,
        "in_protected_closure_8": cid in PROTECTED_COMP_CLOSURE_8,
    }


def _load_known_test_ids_from_manifests(manifest_paths: list[Path]) -> dict[str, Any]:
    all_acts: set[int] = set()
    all_ots: set[int] = set()
    by_phase: dict[str, dict[str, list[int]]] = {}
    for p in manifest_paths:
        if not p.is_file():
            continue
        data = load_manifest(p)
        phase = data.get("phase", p.stem)
        acts = entity_ids(data, "actuaciones") if "actuaciones" in data.get("entities", data) else set()
        ots = entity_ids(data, "orden_trabajo") if "orden_trabajo" in data.get("entities", data) else set()
        if not acts and "entities" in data:
            acts = {int(x) for x in data["entities"].get("actuaciones", []) if isinstance(x, int)}
            if not acts:
                acts = entity_ids(data, "actuaciones")
        by_phase[phase] = {
            "actuaciones": sorted(acts),
            "orden_trabajo": sorted(ots),
        }
        all_acts |= acts
        all_ots |= ots
    return {
        "by_phase": by_phase,
        "known_test_act_ids_union": sorted(all_acts),
        "known_test_ot_ids_union": sorted(all_ots),
    }


def _known_test_guard(conn: Connection, known: dict[str, Any]) -> dict[str, Any]:
    acts = set(known["known_test_act_ids_union"])
    ots = set(known["known_test_ot_ids_union"])
    acts_remaining = sorted(acts & _fetch_ids(conn, "SELECT id FROM actuaciones"))
    ots_remaining = sorted(ots & _fetch_ids(conn, "SELECT id FROM orden_trabajo"))
    return {
        "known_test_act_ids_union_count": len(acts),
        "known_test_ot_ids_union_count": len(ots),
        "known_test_act_ids_remaining": acts_remaining,
        "known_test_act_ids_remaining_count": len(acts_remaining),
        "known_test_ot_ids_remaining": ots_remaining,
        "known_test_ot_ids_remaining_count": len(ots_remaining),
        "guard_ok": len(acts_remaining) == 0 and len(ots_remaining) == 0,
    }


def _verify_empty_routes(conn: Connection) -> list[dict[str, Any]]:
    routes = []
    for rtid in EMPTY_ROUTE_IDS:
        exists = bool(_scalar(conn, "SELECT COUNT(*) FROM ruta_trabajo WHERE id = :id", {"id": rtid}))
        refs = len(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rtid}"))
        routes.append({"ruta_trabajo_id": rtid, "exists": exists, "ruta_item_refs": refs})
    return routes


def _users_simulation(conn: Connection, safe_notif: set[int], safe_comp: set[int]) -> dict[str, Any]:
    fk_columns = load_user_fk_columns(conn)
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    deleted_doc_tables = {"notificacion": safe_notif, "comprobacion": safe_comp}
    free_after = 0
    still = 0
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                parent_table = table
                if parent_table in deleted_doc_tables and r[0] in deleted_doc_tables[parent_table]:
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
        "users_test_fk_free_baseline_post_3h": USERS_FK_FREE_POST_3H,
        "users_test_fk_free_after_2c2c_sim": free_after,
        "users_additionally_unlocked": free_after - USERS_FK_FREE_POST_3H,
        "users_test_still_blocked": still,
    }


def _catalog_effects(conn: Connection, safe_notif: set[int], safe_comp: set[int]) -> dict[str, Any]:
    effects: dict[str, Any] = {}
    for tbl in ("rubro", "juzgado_catalogo", "calle"):
        if not _scalar(conn, f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=:t", {"t": tbl}):
            continue
        effects[tbl] = {"note": "no direct FK from notif/comp candidates in standard schema"}
    juz_refs = int(
        _scalar(
            conn,
            """
            SELECT COUNT(*) FROM oficio o
            JOIN juzgado_catalogo j ON j.id = o.juzgado_id
            WHERE o.comprobacion_id IN (2289)
            """,
        )
        or 0
    )
    effects["juzgado_via_oficio_2289"] = juz_refs
    effects["policy"] = "NO_DELETE catalogos en 2C.2C diag"
    return effects


def _propose_delete_order(conn: Connection) -> dict[str, Any]:
    order = ["notificacion", "comprobacion"]
    fk_valid = _validate_delete_order_fk(order, load_fk_edges(conn))
    independent = not fk_valid.get("violations")
    return {
        "proposed_order": order if independent else ["comprobacion", "notificacion"],
        "fk_validation": fk_valid,
        "note": "notificacion and comprobacion have no FK between them; order independent if valid",
    }


def _postcount_simulation(
    conn: Connection,
    safe_notif: set[int],
    safe_comp: set[int],
    baseline_counts: dict[str, int],
) -> dict[str, Any]:
    notif_casc = _cascade_on_delete(conn, "notificacion", safe_notif)
    comp_casc = _cascade_on_delete(conn, "comprobacion", safe_comp)
    return {
        "notificacion": {
            "before": baseline_counts.get("notificacion", _count(conn, "notificacion")),
            "explicit_delete": len(safe_notif),
            "cascade": notif_casc,
            "after": baseline_counts.get("notificacion", 0) - len(safe_notif),
        },
        "comprobacion": {
            "before": baseline_counts.get("comprobacion", _count(conn, "comprobacion")),
            "explicit_delete": len(safe_comp),
            "cascade": comp_casc,
            "after": baseline_counts.get("comprobacion", 0) - len(safe_comp),
        },
    }


def run_phase2c2c_orphan_documents_diag(
    conn: Connection,
    *,
    protected_path: Path,
    apply_2c2b_path: Path,
    apply_2c2b_prime_path: Path,
    manifest_paths: list[Path],
    notif_source_diag_path: Path | None = None,
    residual_graph_diag_path: Path | None = None,
) -> dict[str, Any]:
    """Orquestador diagnóstico FASE 2C.2C."""
    baseline = _baseline_check(conn)
    historical = load_historical_candidate_sets(
        apply_2c2b_path=apply_2c2b_path,
        apply_2c2b_prime_path=apply_2c2b_prime_path,
        notif_source_diag_path=notif_source_diag_path,
        residual_graph_diag_path=residual_graph_diag_path,
    )

    a_set = set(historical["A_existing_36_orphan_notif"])
    c_set = set(historical["C_new_25_orphan_notif_post_3h4"])
    b_set = set(historical["B_existing_20_orphan_comp"])
    notif_candidates = set(historical["NOTIF_CANDIDATES_RAW"])
    comp_candidates = set(historical["COMP_CANDIDATES_RAW"])
    source_119 = set(historical["source_notificaciones_119"])

    notif_present = _count_ids_exist(conn, "notificacion", notif_candidates)
    comp_present = _count_ids_exist(conn, "comprobacion", comp_candidates)
    notif_missing = sorted(notif_candidates - _fetch_ids(conn, f"SELECT id FROM notificacion WHERE id IN ({','.join(str(i) for i in notif_candidates) or '0'})"))
    comp_missing = sorted(comp_candidates - _fetch_ids(conn, f"SELECT id FROM comprobacion WHERE id IN ({','.join(str(i) for i in comp_candidates) or '0'})"))

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    provenance_3f: dict[str, Any] | None = None
    if notif_source_diag_path and notif_source_diag_path.is_file():
        nd = json.loads(notif_source_diag_path.read_text(encoding="utf-8"))
        by_id = {}
        for it in nd.get("notifications_199", {}).get("items", []):
            by_id[it["notificacion_id"]] = it
        provenance_3f = {"by_id": by_id}

    notif_items: list[dict[str, Any]] = []
    for nid in sorted(notif_candidates):
        origin = {
            "from_existing_36": nid in a_set,
            "from_new_25": nid in c_set,
        }
        notif_items.append(
            _classify_notificacion(conn, nid, prot, source_119, origin, provenance_3f)
        )

    comp_items: list[dict[str, Any]] = []
    for cid in sorted(comp_candidates):
        origin = {
            "from_existing_20": cid in b_set,
            "from_new_2289": cid == 2289,
        }
        comp_items.append(_classify_comprobacion(conn, cid, prot, origin))

    safe_notif = {i["notificacion_id"] for i in notif_items if i["classification"] == "SAFE_ORPHAN_TEST"}
    blocked_notif = [i for i in notif_items if i["classification"] != "SAFE_ORPHAN_TEST"]
    safe_comp = {i["comprobacion_id"] for i in comp_items if i["classification"] == "SAFE_ORPHAN_TEST"}
    blocked_comp = [i for i in comp_items if i["classification"] != "SAFE_ORPHAN_TEST"]

    source_119_overlap = sorted(safe_notif & source_119)
    comp_2289 = next((i for i in comp_items if i["comprobacion_id"] == 2289), None)

    future_exp: list[dict[str, Any]] = []
    future_of: list[dict[str, Any]] = []
    for item in comp_items:
        g = item["expediente_oficio_graph"]
        if item["classification"] == "INDETERMINATE" and g["expedientes"]:
            for e in g["expedientes"]:
                future_exp.append({"expediente_id": e["id"], "from_comprobacion": item["comprobacion_id"]})
        if item["classification"] == "INDETERMINATE" and g["oficios"]:
            for o in g["oficios"]:
                future_of.append({"oficio_id": o["id"], "from_comprobacion": item["comprobacion_id"]})

    known = _load_known_test_ids_from_manifests(manifest_paths)
    test_guard = _known_test_guard(conn, known)

    virtual = VirtualDeleteState()
    virtual.add_explicit("notificacion", safe_notif)
    virtual.add_explicit("comprobacion", safe_comp)
    closure = protection_closure_check(virtual, prot)

    notif_buckets = Counter(i["classification"] for i in notif_items)
    comp_buckets = Counter(i["classification"] for i in comp_items)

    safe_notif_casc = _cascade_on_delete(conn, "notificacion", safe_notif)
    safe_comp_casc = _cascade_on_delete(conn, "comprobacion", safe_comp)

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3I-DIAG",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "historical_candidate_sets": historical,
        "set_intersections": historical["intersections"],
        "raw_candidate_union": {
            "notificaciones_count": historical["notif_raw_count"],
            "comprobaciones_count": historical["comp_raw_count"],
            "expected_naive_61_21": "not assumed; see actual counts",
        },
        "existence": {
            "notificaciones": {"present": notif_present, "missing": notif_missing, "expected": len(notif_candidates)},
            "comprobaciones": {"present": comp_present, "missing": comp_missing, "expected": len(comp_candidates)},
        },
        "incoming_fk_schema": {
            "notificacion": _incoming_fk_edges(conn, "notificacion"),
            "comprobacion": _incoming_fk_edges(conn, "comprobacion"),
        },
        "notifications": {
            "candidates": notif_items,
            "classification_buckets": dict(notif_buckets),
            "safe": {
                "SAFE_NOTIFICACIONES_2C2C": sorted(safe_notif),
                "count": len(safe_notif),
                "from_existing_36": sorted(safe_notif & a_set),
                "from_new_25": sorted(safe_notif & c_set),
                "from_intersection_AC": sorted(safe_notif & a_set & c_set),
            },
            "blocked": {
                "BLOCKED_NOTIFICACIONES_2C2C": [
                    {
                        "id": i["notificacion_id"],
                        "reason": i["classification_reason"],
                        "classification": i["classification"],
                        "surviving_refs": i["surviving_refs"],
                    }
                    for i in blocked_notif
                ],
                "count": len(blocked_notif),
            },
        },
        "comprobaciones": {
            "candidates": comp_items,
            "classification_buckets": dict(comp_buckets),
            "safe": {
                "SAFE_COMPROBACIONES_2C2C": sorted(safe_comp),
                "count": len(safe_comp),
                "from_existing_20": sorted(safe_comp & b_set),
                "from_new_2289": sorted(safe_comp & {2289}),
            },
            "blocked": {
                "BLOCKED_COMPROBACIONES_2C2C": [
                    {
                        "id": i["comprobacion_id"],
                        "reason": i["classification_reason"],
                        "classification": i["classification"],
                        "surviving_refs": i["surviving_refs"],
                        "graph_classification": i["graph_classification"],
                    }
                    for i in blocked_comp
                ],
                "count": len(blocked_comp),
            },
            "comprobacion_2289_audit": comp_2289,
        },
        "source_119_cross": {
            "candidate_cap_source_119": sorted(notif_candidates & source_119),
            "safe_cap_source_119": source_119_overlap,
            "count": len(source_119_overlap),
        },
        "future_exp_oficio_candidates": {
            "FUTURE_SAFE_EXPEDIENTE": future_exp,
            "FUTURE_SAFE_OFICIO": future_of,
            "policy": "NO DELETE in 2C.2C diag",
        },
        "known_test_act_guard": test_guard,
        "known_test_ot_guard": {
            "known_test_ot_ids_remaining": test_guard["known_test_ot_ids_remaining"],
            "count": test_guard["known_test_ot_ids_remaining_count"],
        },
        "empty_routes_residual": {
            "EMPTY_TEST_ROUTES_POST_PRIME": _verify_empty_routes(conn),
            "count": 12,
            "policy": "ROUTE-RESIDUAL-CLEANUP future ticket",
        },
        "protected_comprobacion_regression": {
            "closure_8_ids": sorted(PROTECTED_COMP_CLOSURE_8),
            "all_present": all(
                bool(_scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid}))
                for cid in PROTECTED_COMP_CLOSURE_8
            ),
            "explicit_protected_notif": len(prot.get("notificacion", set())),
            "explicit_protected_comp": len(prot.get("comprobacion", set())),
            "closure_protected_comp": len(prot.get("comprobacion", set())),
        },
        "protected_closure": {
            "intersection_total": closure.get("by_entity", {}),
            "valid": closure.get("valid"),
            "conflicts": closure.get("conflicts", []),
        },
        "cascade_on_safe_delete": {
            "notificacion": safe_notif_casc,
            "comprobacion": safe_comp_casc,
        },
        "user_unlock_simulation": _users_simulation(conn, safe_notif, safe_comp),
        "catalog_effects": _catalog_effects(conn, safe_notif, safe_comp),
        "delete_order_proposed": _propose_delete_order(conn),
        "post_count_simulation": _postcount_simulation(
            conn,
            safe_notif,
            safe_comp,
            {
                "notificacion": _count(conn, "notificacion"),
                "comprobacion": _count(conn, "comprobacion"),
            },
        ),
        "document_cleanup_policy": (
            "DELETE only CONFIRMADO_TEST documents with zero operational surviving refs, "
            "no protected intersection, no surviving iniciador source, no admin chain to preserve. "
            "NOT delete solely for missing XLSX or missing actuacion."
        ),
    }


def write_diag_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
