"""
PREDEPLOY-CLEANUP.3H-DIAG — FASE 2C.2A' forense 38 actuaciones STILL_BLOCKED post-2C.2B.
Solo SELECT. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import OT_TEST_PATTERN, SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.manifest_io import load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import SOURCE_COLUMNS, _classify_source, _scalar
from app.domains.predeploy_cleanup.phase2b_route_items_reconcile import _source_detail
from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import load_structured_acts_274
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import (
    PROTECTED_COMP_CLOSURE_8,
    SYNC_OBS_RE,
    SYNC_REL_OBS_RE,
    TEST_FILES_FOCUS,
    _classify_notificacion,
    _ini_row,
    _is_test_user,
    _notif_row,
    _ot_simulation,
    _protected_regression,
    _scan_tests_for_numeros,
    _users_sim,
)
from app.domains.predeploy_cleanup.phase2c2b_cascade_reconcile import (
    _reconcile_acta_inspeccion_item,
    _reconcile_actuaciones_inspector,
    _reconcile_inspeccion,
    _reconcile_simple_child,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    protection_closure_check,
)

BASELINE_POST_2C2B = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8039,
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

USERS_FK_FREE_POST_2C2B = 833


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
    counts = {t: _count(conn, t) for t in BASELINE_POST_2C2B}
    drift = [f"{t}: {counts[t]} != {e}" for t, e in BASELINE_POST_2C2B.items() if counts[t] != e]
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": not drift,
        "drift": drift,
        "users_test_fk_free_post_2c2b": USERS_FK_FREE_POST_2C2B,
    }


def _load_frozen_acts_38(apply_2c2b_path: Path) -> list[int]:
    data = json.loads(apply_2c2b_path.read_text(encoding="utf-8"))
    ids = data.get("preserved", {}).get("blocked_acts_38") or data.get("excluded", {}).get("blocked_acts_38")
    if not ids:
        raise ValueError("blocked_acts_38 not found in apply report")
    return sorted(int(x) for x in ids)


def _xlsx_protected_ids(protected_manifest: dict[str, Any]) -> dict[str, set[int]]:
    out: dict[str, set[int]] = defaultdict(set)
    for entity, items in protected_manifest.get("entities", {}).items():
        for item in items:
            if isinstance(item, dict) and item.get("id") is not None:
                if item.get("evidence") == "REAL_ADMIN_XLSX" or item.get("match_status"):
                    out[entity].add(int(item["id"]))
    return dict(out)


def _xlsx_match(entity: str, doc_id: int | None, xlsx_ids: dict[str, set[int]]) -> str:
    if doc_id is None:
        return "N/A"
    return "MATCH_REAL_XLSX" if doc_id in xlsx_ids.get(entity, set()) else "NO_MATCH_XLSX"


def _act_row(conn: Connection, aid: int) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT a.id, a.tipo, a.fecha, a.created_at, a.orden_trabajo_id,
                   a.notificacion_id, a.comprobacion_id, a.establecimiento_operativo_id,
                   a.domicilio_id, ot.numero_acta AS ot_numero, ot.created_at AS ot_created_at
            FROM actuaciones a
            LEFT JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
            WHERE a.id = :id
            """
        ),
        {"id": aid},
    ).fetchone()
    if not row:
        return {"actuacion_id": aid, "missing": True}
    return dict(row._mapping)


def _incoming_fk_refs(conn: Connection, table: str, pk: int) -> list[dict[str, Any]]:
    """FK entrantes RESTRICT/NO ACTION que bloquearían DELETE (excluye CASCADE hijos)."""
    skip = {"iniciador_ruta", "ruta_item", "ruta_pool_dia"}
    children = _rows(
        conn,
        """
        SELECT kcu.TABLE_NAME AS child_table, kcu.COLUMN_NAME AS child_column,
               rc.DELETE_RULE AS delete_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.REFERENCED_TABLE_NAME = :parent
        """,
        {"parent": table},
    )
    refs: list[dict[str, Any]] = []
    for ch in children:
        tbl = ch["child_table"]
        if tbl in skip or ch["delete_rule"] == "CASCADE":
            continue
        col = ch["child_column"]
        cnt = int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :pk", {"pk": pk}) or 0)
        if cnt:
            refs.append(
                {
                    "child_table": tbl,
                    "child_column": col,
                    "delete_rule": ch["delete_rule"],
                    "count": cnt,
                }
            )
    return refs


def _blockers_for_act(conn: Connection, aid: int) -> dict[str, Any]:
    act = _act_row(conn, aid)
    ini_ids = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}"))
    ri_ids = sorted(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}"))
    rp_ids: set[int] = set()
    for iid in ini_ids:
        rp_ids |= _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}")
    other_fk = _incoming_fk_refs(conn, "actuaciones", aid)
    blocking_reasons: list[str] = []
    if ini_ids:
        blocking_reasons.append(f"iniciador_ruta:{len(ini_ids)}")
    if ri_ids:
        blocking_reasons.append(f"ruta_item:{len(ri_ids)}")
    if rp_ids:
        blocking_reasons.append(f"ruta_pool_dia:{len(rp_ids)}")
    for ref in other_fk:
        if ref["child_table"] not in ("iniciador_ruta", "ruta_item", "ruta_pool_dia"):
            blocking_reasons.append(f"{ref['child_table']}:{ref['count']}")
    return {
        "actuacion_id": aid,
        "row": act,
        "iniciador_ruta_ids": ini_ids,
        "ruta_item_ids": ri_ids,
        "ruta_pool_dia_ids": sorted(rp_ids),
        "other_incoming_fk": other_fk,
        "blocking_reasons": blocking_reasons,
        "is_blocked": bool(ini_ids or ri_ids or rp_ids or other_fk),
    }


def _prior_ini_map(diag_3f1_path: Path) -> dict[int, dict[str, Any]]:
    data = json.loads(diag_3f1_path.read_text(encoding="utf-8"))
    return {int(it["iniciador_id"]): it for it in data["initiators_167"]["items"]}


def _prior_act_still_blocked(diag_3f1_path: Path) -> dict[int, dict[str, Any]]:
    data = json.loads(diag_3f1_path.read_text(encoding="utf-8"))
    still = data["acts_unlock_simulation"].get("STILL_BLOCKED_sample", [])
    full_still = data["acts_unlock_simulation"].get("STILL_BLOCKED", still)
    if isinstance(full_still, list) and full_still and isinstance(full_still[0], dict):
        return {int(x["actuacion_id"]): x for x in full_still}
    return {}


def _comprobacion_chain(conn: Connection, comp_id: int) -> dict[str, Any]:
    comp = _rows(
        conn,
        "SELECT id, numero_acta, created_at FROM comprobacion WHERE id = :id",
        {"id": comp_id},
    )
    exps = _rows(conn, "SELECT id, oficio_id FROM expediente WHERE comprobacion_id = :id", {"id": comp_id})
    oficios = []
    for exp in exps:
        if exp.get("oficio_id"):
            oficios.extend(
                _rows(conn, "SELECT id, numero_oficio, comprobacion_id FROM oficio WHERE id = :id", {"id": exp["oficio_id"]})
            )
    inis = _rows(
        conn,
        """
        SELECT id, tipo_iniciador, notificacion_id, comprobacion_id, oficio_id, actuacion_id
        FROM iniciador_ruta WHERE comprobacion_id = :id OR oficio_id IN (
            SELECT oficio_id FROM expediente WHERE comprobacion_id = :id AND oficio_id IS NOT NULL
        )
        """,
        {"id": comp_id},
    )
    return {"comprobacion": comp, "expedientes": exps, "oficios": oficios, "iniciadores": inis}


def _classify_source_graph(
    conn: Connection,
    ini: dict[str, Any],
    notif_class: dict[int, dict[str, Any]],
    prot: dict[str, set[int]],
    acts_38: set[int],
    xlsx_ids: dict[str, set[int]],
) -> dict[str, Any]:
    nid = ini.get("notificacion_id")
    cid = ini.get("comprobacion_id")
    oid = ini.get("oficio_id")
    graph: dict[str, Any] = {"tipo": ini.get("tipo_iniciador")}
    if nid:
        nf = _notif_row(conn, nid)
        nc = notif_class.get(nid, {})
        graph["notificacion"] = {
            **nf,
            "classification": nc.get("classification"),
            "xlsx": _xlsx_match("notificacion", nid, xlsx_ids),
            "in_protected": nid in prot.get("notificacion", set()),
            "in_source_119": False,
        }
    if cid:
        chain = _comprobacion_chain(conn, cid)
        graph["comprobacion_chain"] = chain
        graph["comprobacion"] = {
            "id": cid,
            "xlsx": _xlsx_match("comprobacion", cid, xlsx_ids),
            "in_protected": cid in prot.get("comprobacion", set()),
        }
    if oid:
        graph["oficio"] = {
            "id": oid,
            "xlsx": _xlsx_match("oficio", oid, xlsx_ids),
            "in_protected": oid in prot.get("oficio", set()),
        }
    labels: set[str] = set()
    if graph.get("notificacion"):
        labels.add(graph["notificacion"].get("classification", "INDETERMINATE"))
    if graph.get("comprobacion", {}).get("in_protected"):
        labels.add("PROTECTED_REAL")
    elif cid and not graph.get("comprobacion", {}).get("xlsx") == "MATCH_REAL_XLSX":
        labels.add("INDETERMINATE")
    if len(labels) > 1:
        graph["graph_classification"] = "MIXED"
    elif labels:
        g = next(iter(labels))
        graph["graph_classification"] = (
            "CONFIRMADO_TEST" if g == "CONFIRMADO_TEST_DOCUMENT" else g.replace("_DOCUMENT", "")
        )
    else:
        graph["graph_classification"] = "INDETERMINATE"
    act_on_ini = ini.get("actuacion_id")
    if act_on_ini and act_on_ini in acts_38:
        graph["actuacion_link"] = "CONFIRMADO_TEST_ACT"
    return graph


ANNULLED_SYNC_RE = re.compile(r"\[sync notif vencidas\].*Anulado", re.I)


def _classify_initiator_prime(
    conn: Connection,
    full: dict[str, Any],
    acts_38: set[int],
    notif_class: dict[int, dict[str, Any]],
    prot: dict[str, set[int]],
    source_119: set[int],
    xlsx_ids: dict[str, set[int]],
    prior_bucket: str,
) -> tuple[str, list[str]]:
    """
    Clasificación 2C.2A' sobre iniciadores que bloquean las 38 acts CONFIRMADO_TEST.

    Regla base: act en universo 38 => iniciador es wrapper test salvo source protected.
    """
    reasons: list[str] = []
    act_id = full.get("actuacion_id")
    if act_id not in acts_38:
        return "OTHER_INDETERMINATE", ["act_not_in_38"]

    nid = full.get("notificacion_id")
    cid = full.get("comprobacion_id")
    oid = full.get("oficio_id")
    obs = full.get("observaciones") or ""

    def _preserved_notif(n: int | None) -> bool:
        return bool(
            n
            and (
                n in prot.get("notificacion", set())
                or n in source_119
                or _xlsx_match("notificacion", n, xlsx_ids) == "MATCH_REAL_XLSX"
            )
        )

    def _preserved_comp(c: int | None) -> bool:
        return bool(
            c
            and (
                c in prot.get("comprobacion", set())
                or _xlsx_match("comprobacion", c, xlsx_ids) == "MATCH_REAL_XLSX"
            )
        )

    def _preserved_oficio(o: int | None) -> bool:
        return bool(
            o
            and (
                o in prot.get("oficio", set())
                or _xlsx_match("oficio", o, xlsx_ids) == "MATCH_REAL_XLSX"
            )
        )

    if _preserved_notif(nid):
        reasons.append("wrapper_on_preserved_notif")
        return "SAFE_WRAPPER_AROUND_REAL", reasons
    if _preserved_comp(cid):
        reasons.append("wrapper_on_preserved_comp")
        return "SAFE_WRAPPER_AROUND_REAL", reasons
    if _preserved_oficio(oid):
        reasons.append("wrapper_on_preserved_oficio")
        return "SAFE_WRAPPER_AROUND_REAL", reasons

    if ANNULLED_SYNC_RE.search(obs):
        reasons.append("sync_annulled_stub")
        return "SAFE_TEST_INITIATOR", reasons

    if SYNC_OBS_RE.search(obs) or SYNC_REL_OBS_RE.search(obs) or "Derivado autom" in obs:
        reasons.append("sync_derived")
        return "SAFE_TEST_INITIATOR", reasons

    act_row = _act_row(conn, act_id) if act_id else {}
    ot_num = str(act_row.get("ot_numero") or "")
    if OT_TEST_PATTERN.match(ot_num):
        reasons.append("ot_test_pattern")
        return "SAFE_TEST_INITIATOR", reasons

    nc = notif_class.get(nid, {}).get("classification") if nid else None
    if nc == "PROTECTED_REAL_DOCUMENT":
        reasons.append("notif_protected_real")
        return "SAFE_WRAPPER_AROUND_REAL", reasons
    if nc == "CONFIRMADO_TEST_DOCUMENT":
        reasons.append("notif_confirmed_test")
        return "SAFE_TEST_INITIATOR", reasons

    if full.get("tipo_iniciador") == "REINSPECCION_OFICIO" and not _preserved_comp(cid) and not _preserved_oficio(oid):
        reasons.append("oficio_chain_no_xlsx_match_on_test_act")
        return "SAFE_TEST_INITIATOR", reasons

    reasons.append("act_in_confirmed_test_38_universe")
    return "SAFE_TEST_INITIATOR", reasons


def _simulate_unlock_prime(
    conn: Connection,
    acts_38: set[int],
    safe_ini: set[int],
    safe_ri: set[int],
    safe_rp: set[int],
) -> dict[str, Any]:
    unlocked: list[int] = []
    still: list[dict[str, Any]] = []
    for aid in sorted(acts_38):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp: set[int] = set()
        for iid in inis:
            rp |= _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}")
        remain_ini = inis - safe_ini
        remain_ri = ri - safe_ri
        remain_rp = rp - safe_rp
        if not remain_ini and not remain_ri and not remain_rp:
            unlocked.append(aid)
        else:
            still.append(
                {
                    "actuacion_id": aid,
                    "remaining_iniciadores": sorted(remain_ini),
                    "ruta_item_refs": sorted(remain_ri),
                    "ruta_pool_refs": sorted(remain_rp),
                }
            )
    return {
        "UNLOCKED_AFTER_2C2A_PRIME_count": len(unlocked),
        "STILL_BLOCKED_count": len(still),
        "UNLOCKED_ids": unlocked,
        "STILL_BLOCKED": still,
    }


def _classify_route_wrapper(
    conn: Connection,
    ini_id: int,
    ri_ids: set[int],
    rp_ids: set[int],
    prot: dict[str, set[int]],
) -> str:
    if not ri_ids and not rp_ids:
        return "NONE"
    for ri in ri_ids:
        row = conn.execute(
            text(
                "SELECT actuacion_id, orden_trabajo_id, iniciador_ruta_id FROM ruta_item WHERE id = :id"
            ),
            {"id": ri},
        ).fetchone()
        if row and row[0] in prot.get("actuaciones", set()):
            return "KEEP"
        if row and row[1] in prot.get("orden_trabajo", set()):
            return "KEEP"
    return "SAFE_TEST_WRAPPER"


def _future_cascades(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    if not act_ids:
        return {t: {"physical_rows": 0} for t in (
            "inspeccion", "actuaciones_inspector", "clausura", "decomiso", "acta_inspeccion_item"
        )}
    insp = _reconcile_inspeccion(conn, act_ids)
    ai = _reconcile_actuaciones_inspector(conn, act_ids)
    cl = _reconcile_simple_child(conn, "clausura", "actuacion_id", act_ids)
    de = _reconcile_simple_child(conn, "decomiso", "actuacion_id", act_ids)
    aii = _reconcile_acta_inspeccion_item(conn, set(insp["inspeccion_ids"]))
    return {
        "inspeccion": insp,
        "actuaciones_inspector": ai,
        "clausura": cl,
        "decomiso": de,
        "acta_inspeccion_item": aii,
    }


def _new_orphan_docs(
    conn: Connection,
    unlockable_acts: set[int],
    reserved_orphan_notifs: set[int],
    reserved_orphan_comps: set[int],
) -> dict[str, Any]:
    new_notifs: list[int] = []
    new_comps: list[int] = []
    for aid in unlockable_acts:
        row = _act_row(conn, aid)
        nid = row.get("notificacion_id")
        cid = row.get("comprobacion_id")
        if nid and nid not in reserved_orphan_notifs:
            refs = int(_scalar(conn, "SELECT COUNT(*) FROM actuaciones WHERE notificacion_id = :id", {"id": nid}) or 0)
            only_this = refs == 1
            if only_this:
                new_notifs.append(nid)
        if cid and cid not in reserved_orphan_comps:
            refs = int(_scalar(conn, "SELECT COUNT(*) FROM actuaciones WHERE comprobacion_id = :id", {"id": cid}) or 0)
            if refs == 1:
                new_comps.append(cid)
    return {
        "NEW_ORPHAN_TEST_DOCUMENTS": {
            "notificaciones": sorted(set(new_notifs)),
            "comprobaciones": sorted(set(new_comps)),
        },
        "policy": "NO sumar aún a set 2C.2C",
    }


def _users_incremental(
    conn: Connection,
    virtual: VirtualDeleteState,
    unlockable_acts: set[int],
    exclusive_ots: set[int],
) -> dict[str, Any]:
    base = _users_sim(conn)
    v2 = VirtualDeleteState()
    v2.explicit = {k: set(v) for k, v in virtual.explicit.items()}
    v2.cascade = {k: set(v) for k, v in virtual.cascade.items()}
    v2.add_explicit("actuaciones", unlockable_acts)
    v2.add_explicit("orden_trabajo", exclusive_ots)
    fk_columns = __import__(
        "app.domains.predeploy_cleanup.sequential_simulator", fromlist=["load_user_fk_columns"]
    ).load_user_fk_columns(conn)
    deleted_by_table: dict[str, set[int]] = defaultdict(set)
    for table in v2.explicit:
        deleted_by_table[table].update(v2.explicit[table])
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    free_after_prime = free_after_bprime = 0
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                if r[0] not in deleted_by_table.get(table, set()):
                    blocked = True
                    break
            if blocked:
                break
        if not blocked:
            free_after_bprime += 1
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                rid = r[0]
                if table == "iniciador_ruta" and rid in v2.explicit.get("iniciador_ruta", set()):
                    continue
                if table == "ruta_item" and rid in v2.explicit.get("ruta_item", set()):
                    continue
                if table == "ruta_pool_dia" and rid in v2.explicit.get("ruta_pool_dia", set()):
                    continue
                blocked = True
                break
            if blocked:
                break
        if not blocked:
            free_after_prime += 1
    return {
        "baseline_post_2c2b": USERS_FK_FREE_POST_2C2B,
        "after_2c2a_prime_sim": free_after_prime,
        "after_2c2b_prime_sim": free_after_bprime,
        "incremental_prime": free_after_prime - USERS_FK_FREE_POST_2C2B,
        "incremental_bprime": free_after_bprime - free_after_prime,
    }


def run_phase2c2a_prime_residual_acts_diag(
    conn: Connection,
    *,
    apply_2c2b_path: Path,
    diag_3f1_path: Path,
    protected_path: Path,
    structured_acts_path: Path,
    source_119_path: Path | None = None,
    tests_root: Path,
) -> dict[str, Any]:
    """Orquestador diagnóstico 3H FASE 2C.2A'."""
    baseline = _baseline_check(conn)
    if not baseline["baseline_ok"]:
        return {
            "generated_at": datetime.now().isoformat(),
            "ticket": "PREDEPLOY-CLEANUP.3H-DIAG",
            "mode": "READ_ONLY_DIAG",
            "writes_executed": False,
            "baseline": baseline,
            "abort_reason": "baseline_drift",
        }

    acts_38_list = _load_frozen_acts_38(apply_2c2b_path)
    acts_38 = set(acts_38_list)
    present = _count_ids_exist(conn, "actuaciones", acts_38)
    if present != 38:
        raise ValueError(f"acts_38 present {present} != 38")

    set_act_structured = load_structured_acts_274(structured_acts_path) & acts_38
    set_act_old = acts_38 - set_act_structured

    prot_manifest = load_manifest(protected_path)
    prot = expand_protected_indirect(conn, load_protected_sets(prot_manifest))
    xlsx_ids = _xlsx_protected_ids(prot_manifest)
    prior_ini = _prior_ini_map(diag_3f1_path)
    prior_still = _prior_act_still_blocked(diag_3f1_path)

    apply_data = json.loads(apply_2c2b_path.read_text(encoding="utf-8"))
    source_119 = set(apply_data.get("preserved", {}).get("source_notificaciones_119", []))
    orphan_36 = set(apply_data.get("preserved", {}).get("orphan_notificaciones_36", []))
    orphan_20 = set(apply_data.get("preserved", {}).get("orphan_comprobaciones_20", []))

    acts_detail = [_blockers_for_act(conn, aid) for aid in acts_38_list]
    ini_universe: set[int] = set()
    for ad in acts_detail:
        ini_universe.update(ad["iniciador_ruta_ids"])

    notif_ids: set[int] = set()
    numeros: set[str] = set()
    for iid in ini_universe:
        ini = _ini_row(conn, iid)
        nid = ini.get("notificacion_id")
        if nid:
            notif_ids.add(nid)
            nf = _notif_row(conn, nid)
            if nf.get("numero_acta"):
                numeros.add(str(nf["numero_acta"]))
    test_hits = _scan_tests_for_numeros(tests_root, numeros)

    diag3f = json.loads(diag_3f1_path.read_text(encoding="utf-8"))
    from_265 = set()
    for nid, det in diag3f.get("notifications_199_frozen", {}).get("details", {}).items():
        if det.get("from_265_preserved_set"):
            from_265.add(int(nid))
    blocked_148 = set()
    for item in diag3f.get("acts_unlock_simulation", {}).get("STILL_BLOCKED_sample", []):
        pass
    phase2c1_manifest = apply_2c2b_path.parent / "cleanup_execution_manifest_phase2c1_sources_20260920.json"
    if phase2c1_manifest.is_file():
        blocked_148 = {int(x) for x in load_manifest(phase2c1_manifest).get("excluded", {}).get("blocked_acts_148", [])}

    notif_class: dict[int, dict[str, Any]] = {}
    for nid in notif_ids:
        nf = _notif_row(conn, nid)
        if nid in orphan_36:
            notif_class[nid] = {"notificacion_id": nid, "classification": "CONFIRMADO_TEST_DOCUMENT"}
        elif nid in prot.get("notificacion", set()):
            notif_class[nid] = {"notificacion_id": nid, "classification": "PROTECTED_REAL_DOCUMENT"}
        else:
            notif_class[nid] = _classify_notificacion(
                conn, nid, nf, prot, orphan_36, from_265, blocked_148 | acts_38, test_hits
            )
        notif_class[nid]["in_source_119"] = nid in source_119

    iniciators: list[dict[str, Any]] = []
    safe_ri: set[int] = set()
    safe_rp: set[int] = set()
    route_class: dict[int, str] = {}
    for iid in sorted(ini_universe):
        full = _ini_row(conn, iid)
        prior = prior_ini.get(iid, {})
        prev_bucket = prior.get("classification", prior.get("final_classification", "INDETERMINATE"))
        final_cls, cls_reasons = _classify_initiator_prime(
            conn, full, acts_38, notif_class, prot, source_119, xlsx_ids, prev_bucket
        )
        ri = set(full.get("ruta_item_refs") or [])
        rp = set(full.get("ruta_pool_refs") or [])
        rw = _classify_route_wrapper(conn, iid, ri, rp, prot)
        route_class[iid] = rw
        if rw == "SAFE_TEST_WRAPPER":
            safe_ri.update(ri)
            safe_rp.update(rp)
        if final_cls in ("SAFE_TEST_INITIATOR", "SAFE_WRAPPER_AROUND_REAL"):
            safe_ri.update(ri)
            safe_rp.update(rp)
        sources = _source_detail(conn, full, prot, acts_38, set(), set())
        graph = _classify_source_graph(conn, full, notif_class, prot, acts_38, xlsx_ids)
        obs = full.get("observaciones") or ""
        iniciators.append(
            {
                "iniciador_id": iid,
                "tipo_iniciador": full.get("tipo_iniciador"),
                "estado": full.get("estado"),
                "created_by_user_id": full.get("created_by_user_id"),
                "observaciones": obs,
                "created_at": str(full.get("created_at")) if full.get("created_at") else None,
                "source_fk": {c: full.get(c) for c in SOURCE_COLUMNS if full.get(c)},
                "ruta_item_refs": sorted(ri),
                "ruta_pool_refs": sorted(rp),
                "route_wrapper_classification": rw,
                "prior_classification_3f1": prev_bucket,
                "prior_final_3f1": prior.get("final_classification"),
                "final_classification": final_cls,
                "classification_reasons": cls_reasons,
                "is_sync_derived": bool(SYNC_OBS_RE.search(obs) or SYNC_REL_OBS_RE.search(obs)),
                "is_sync_annulled": bool(ANNULLED_SYNC_RE.search(obs)),
                "created_by_test_user": _is_test_user(conn, full.get("created_by_user_id")),
                "source_detail": sources,
                "source_graph": graph,
                "blocked_actuacion_ids": sorted(
                    _fetch_ids(conn, f"SELECT actuacion_id FROM iniciador_ruta WHERE id = {iid} AND actuacion_id IS NOT NULL")
                ),
            }
        )

    ini_final_counts = Counter(i["final_classification"] for i in iniciators)
    tipo_counts = Counter(i["tipo_iniciador"] for i in iniciators)

    safe_ini = {
        i["iniciador_id"]
        for i in iniciators
        if i["final_classification"] in ("SAFE_TEST_INITIATOR", "SAFE_WRAPPER_AROUND_REAL")
    }
    for iid, rw in route_class.items():
        if rw == "SAFE_TEST_WRAPPER" and iid in safe_ini:
            full = _ini_row(conn, iid)
            safe_ri.update(full.get("ruta_item_refs") or [])
            safe_rp.update(full.get("ruta_pool_refs") or [])

    unlock = _simulate_unlock_prime(conn, acts_38, safe_ini, safe_ri, safe_rp)
    unlocked_ids = set(unlock["UNLOCKED_ids"])
    still_ids = acts_38 - unlocked_ids
    ot_analysis = _ot_simulation(conn, list(unlocked_ids))
    cascades = _future_cascades(conn, unlocked_ids)
    orphans_new = _new_orphan_docs(conn, unlocked_ids, orphan_36, orphan_20)

    xlsx_cross: list[dict[str, Any]] = []
    for ini in iniciators:
        sg = ini.get("source_graph", {})
        if sg.get("notificacion"):
            xlsx_cross.append(
                {
                    "entity": "notificacion",
                    "id": sg["notificacion"].get("id"),
                    "xlsx": sg["notificacion"].get("xlsx"),
                    "iniciador_id": ini["iniciador_id"],
                }
            )
        if sg.get("comprobacion"):
            xlsx_cross.append(
                {
                    "entity": "comprobacion",
                    "id": sg["comprobacion"].get("id"),
                    "xlsx": sg["comprobacion"].get("xlsx"),
                    "iniciador_id": ini["iniciador_id"],
                }
            )

    virtual = VirtualDeleteState()
    virtual.add_explicit("iniciador_ruta", safe_ini)
    if safe_ri:
        virtual.add_explicit("ruta_item", safe_ri)
    if safe_rp:
        virtual.add_explicit("ruta_pool_dia", safe_rp)
    closure = protection_closure_check(virtual, prot)
    comp_reg = _protected_regression(conn, prot)

    reserved_orphans = {
        "orphan_notificaciones_36": {
            "expected": 36,
            "present": _count_ids_exist(conn, "notificacion", orphan_36),
        },
        "orphan_comprobaciones_20": {
            "expected": 20,
            "present": _count_ids_exist(conn, "comprobacion", orphan_20),
        },
        "source_notificaciones_119": {
            "expected": len(source_119),
            "present": _count_ids_exist(conn, "notificacion", source_119),
        },
    }

    exclusive_ots = set(ot_analysis.get("EXCLUSIVE_OT_ids", []))
    users_sim = _users_incremental(conn, virtual, unlocked_ids, exclusive_ots)

    unlocked_n = len(unlocked_ids)
    still_n = len(still_ids)
    if unlocked_n == 38:
        closure_rec = "A: 38/38 unlock -> 2C.2A' wrappers/iniciadores -> 2C.2B' acts+OT"
    elif unlocked_n > 0:
        closure_rec = f"B: {unlocked_n}/38 unlock -> limpiar {unlocked_n}; {still_n} INDETERMINADO"
    else:
        closure_rec = "C: 0/38 unlock -> requiere mas forense antes de apply"

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3H-DIAG",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "acts_38": {
            "ids": acts_38_list,
            "present": present,
            "family": {
                "SET_ACT_OLD": sorted(set_act_old),
                "SET_ACT_STRUCTURED": sorted(set_act_structured),
                "SET_ACT_OLD_count": len(set_act_old),
                "SET_ACT_STRUCTURED_count": len(set_act_structured),
            },
            "items": acts_detail,
        },
        "initiators": {
            "unique_blocker_count": len(ini_universe),
            "ids": sorted(ini_universe),
            "tipo_counts": dict(tipo_counts),
            "final_classification_counts": dict(ini_final_counts),
            "items": iniciators,
        },
        "sources": {
            "notificaciones_analyzed": len(notif_ids),
            "notificacion_classification": {str(k): v for k, v in notif_class.items()},
        },
        "xlsx_cross": xlsx_cross,
        "test_provenance": {
            "test_files_scanned": list(TEST_FILES_FOCUS),
            "numero_acta_hits": test_hits,
            "sync_observacion_pattern": "Derivado automático por vencimiento de notificación",
            "admin_fallback_rule": "created_by_user_id=1 NO prueba realidad",
        },
        "admin_fallback_analysis": {
            "sync_derived_count": sum(1 for i in iniciators if i["is_sync_derived"]),
            "admin_creator_count": sum(1 for i in iniciators if i.get("created_by_user_id") == 1),
            "test_user_creator_count": sum(1 for i in iniciators if i["created_by_test_user"]),
        },
        "route_refs": {
            "SAFE_TEST_WRAPPER_iniciadores": [i for i, c in route_class.items() if c == "SAFE_TEST_WRAPPER"],
            "KEEP_route_refs": [i for i, c in route_class.items() if c == "KEEP"],
        },
        "classification": {
            "initiator_final": dict(ini_final_counts),
            "allowed_labels": [
                "SAFE_TEST_INITIATOR",
                "SAFE_WRAPPER_AROUND_REAL",
                "KEEP_PROTECTED_SOURCE",
                "KEEP_REAL_SOURCE",
                "KEEP_INDETERMINATE_SOURCE",
                "OTHER_INDETERMINATE",
            ],
            "sums_to_universe": sum(ini_final_counts.values()) == len(ini_universe),
        },
        "safe_wrappers": {
            "SAFE_RUTA_ITEM_2C2A_PRIME": sorted(safe_ri),
            "SAFE_RUTA_POOL_2C2A_PRIME": sorted(safe_rp),
        },
        "safe_initiators": {
            "SAFE_INITIATOR_2C2A_PRIME": sorted(safe_ini),
            "count": len(safe_ini),
        },
        "acts_unlock_simulation": {
            **unlock,
            "UNLOCKED_AFTER_2C2A_PRIME_ids": sorted(unlocked_ids),
            "STILL_BLOCKED_ids": sorted(still_ids),
            "UNLOCKED_count": unlocked_n,
            "STILL_BLOCKED_count": still_n,
            "simulation_includes": ["SAFE_INITIATOR_2C2A_PRIME", "SAFE_RUTA_ITEM_2C2A_PRIME", "SAFE_RUTA_POOL_2C2A_PRIME"],
        },
        "ot_analysis": {
            **ot_analysis,
            "policy": "EXCLUSIVE_TEST prepara 2C.2B'; no delete en este ticket",
        },
        "future_cascades": cascades,
        "new_orphan_docs": orphans_new,
        "reserved_orphan_docs": reserved_orphans,
        "protected_closure": closure,
        "protected_comprobacion_regression": comp_reg,
        "users_simulation": users_sim,
        "safe_sets": {
            "SAFE_RUTA_ITEM_2C2A_PRIME": sorted(safe_ri),
            "SAFE_RUTA_POOL_2C2A_PRIME": sorted(safe_rp),
            "SAFE_INITIATOR_2C2A_PRIME": sorted(safe_ini),
            "SAFE_ACTUACIONES_AFTER_PRIME": sorted(unlocked_ids),
            "SAFE_OT_AFTER_PRIME": ot_analysis.get("EXCLUSIVE_OT_ids", []),
            "KEEP_INITIATORS": sorted(ini_universe - safe_ini),
            "KEEP_ACTUACIONES": sorted(still_ids),
        },
        "operational_closure_recommendation": closure_rec,
        "prior_3f1_still_blocked_cross": {
            "acts_in_prior_still_sample": len(prior_still),
            "note": "38 acts frozen from 2C.2B apply preserved.blocked_acts_38",
        },
    }


def write_diag_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
