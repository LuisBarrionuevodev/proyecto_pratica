"""
PREDEPLOY-CLEANUP.3H.1 — congelar execution manifest FASE 2C.2A' (12 ruta_item + 38 iniciadores).
Solo lectura / generación de manifest.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.execution_validator import load_iniciador_ruta_incoming_fks
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import (
    file_sha256,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
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

PHASE2C2A_PRIME_DELETE_ORDER = ["ruta_item", "iniciador_ruta"]

EXPECTED_RI = 12
EXPECTED_INI = 38
EXPECTED_TEST_INITIATOR = 23
EXPECTED_PRESERVED_SOURCE = 15
EXPECTED_RN = 35
EXPECTED_RO = 3
EXPECTED_ACTS_38 = 38
EXPECTED_OT_38 = 38

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

POST_EXPLICIT = {
    "ruta_item": 3685,
    "iniciador_ruta": 8001,
}

USERS_FK_FREE_POST_2C2B = 833

FORBIDDEN_MANIFEST_ENTITIES = frozenset(
    {
        "actuaciones",
        "orden_trabajo",
        "notificacion",
        "comprobacion",
        "oficio",
        "expediente",
        "users",
        "relevamiento",
        "denuncia",
        "ruta_trabajo",
        "ruta_grupo",
        "ruta_grupo_inspector",
        "ruta_pool_dia",
    }
)


class ManifestFreezeError(Exception):
    """Aborta freeze del manifest FASE 2C.2A'."""


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ManifestFreezeError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ManifestFreezeError(f"alembic={alembic}")
    counts = {}
    for table, expected in BASELINE_POST_2C2B.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            raise ManifestFreezeError(f"baseline {table}: {actual} != {expected}")
    return {"database": db, "alembic_revision": alembic, "counts": counts}


def load_safe_sets_from_diag(diag_path: Path) -> dict[str, Any]:
    """Carga safe sets congelados del diagnóstico 3H."""
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    ri = [int(x) for x in data["safe_sets"]["SAFE_RUTA_ITEM_2C2A_PRIME"]]
    ini = [int(x) for x in data["safe_sets"]["SAFE_INITIATOR_2C2A_PRIME"]]
    acts = [int(x) for x in data["acts_38"]["ids"]]
    ots = [int(x) for x in data["safe_sets"]["SAFE_OT_AFTER_PRIME"]]
    if len(ri) != EXPECTED_RI or len(set(ri)) != EXPECTED_RI:
        raise ManifestFreezeError(f"SAFE_RUTA_ITEM: {len(ri)}")
    if len(ini) != EXPECTED_INI or len(set(ini)) != EXPECTED_INI:
        raise ManifestFreezeError(f"SAFE_INITIATOR: {len(ini)}")
    if len(acts) != EXPECTED_ACTS_38:
        raise ManifestFreezeError(f"acts_38: {len(acts)}")
    if len(ots) != EXPECTED_OT_38:
        raise ManifestFreezeError(f"SAFE_OT: {len(ots)}")
    fam = data["acts_38"]["family"]
    if fam.get("SET_ACT_OLD_count") != 38 or fam.get("SET_ACT_STRUCTURED_count") != 0:
        raise ManifestFreezeError("acts family mismatch")
    return {
        "ruta_item": set(ri),
        "iniciador_ruta": set(ini),
        "acts_38": set(acts),
        "ot_38": set(ots),
        "diag": data,
    }


def _semantic_classification(diag: dict[str, Any]) -> dict[str, Any]:
    """Mapea clasificación 3H a nombres del manifest."""
    test_init = 0
    preserved = 0
    by_ini: dict[int, dict[str, str]] = {}
    for it in diag["initiators"]["items"]:
        iid = it["iniciador_id"]
        orig = it["final_classification"]
        if orig == "SAFE_WRAPPER_AROUND_REAL":
            sem = "SAFE_WRAPPER_AROUND_PRESERVED_SOURCE"
            preserved += 1
        elif orig == "SAFE_TEST_INITIATOR":
            sem = "SAFE_TEST_INITIATOR"
            test_init += 1
        else:
            raise ManifestFreezeError(f"unexpected class {orig} on ini {iid}")
        by_ini[iid] = {"manifest_classification": sem, "diag_classification_original": orig}
    if test_init != EXPECTED_TEST_INITIATOR or preserved != EXPECTED_PRESERVED_SOURCE:
        raise ManifestFreezeError(f"classification: {test_init}/{preserved}")
    return {
        "safe_test_initiator": test_init,
        "safe_wrapper_around_preserved_source": preserved,
        "by_iniciador_id": by_ini,
    }


def _ruta_item_metadata(conn: Connection, ri_ids: set[int]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for rid in sorted(ri_ids):
        row = conn.execute(
            text(
                """
                SELECT ri.id, ri.ruta_trabajo_id, ri.ruta_grupo_id, ri.iniciador_ruta_id,
                       ri.actuacion_id, ri.estado_ruta_item, ri.estado_ejecucion, ri.created_by_user_id
                FROM ruta_item ri WHERE ri.id = :id
                """
            ),
            {"id": rid},
        ).fetchone()
        if not row:
            raise ManifestFreezeError(f"ruta_item {rid} missing")
        items.append(dict(row._mapping))
    return items


def _incoming_fk_to_table(conn: Connection, parent_table: str) -> list[dict[str, Any]]:
    return _rows(
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
        {"parent": parent_table},
    )


def _outgoing_fk_from_table(conn: Connection, child_table: str) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT kcu.COLUMN_NAME AS child_column, kcu.REFERENCED_TABLE_NAME AS parent_table,
               kcu.REFERENCED_COLUMN_NAME AS parent_column, rc.DELETE_RULE AS delete_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.TABLE_NAME = :child
          AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        """,
        {"child": child_table},
    )


def _validate_ruta_item_fks(conn: Connection, ri_ids: set[int]) -> dict[str, Any]:
    incoming = _incoming_fk_to_table(conn, "ruta_item")
    outgoing = _outgoing_fk_from_table(conn, "ruta_item")
    child_blockers: list[dict[str, Any]] = []
    for edge in incoming:
        tbl, col = edge["child_table"], edge["child_column"]
        if edge["delete_rule"] == "CASCADE":
            continue
        for chunk in _chunk_ids(ri_ids, 300):
            ph = ",".join(str(i) for i in chunk)
            n = int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN ({ph})") or 0)
            if n:
                child_blockers.append({**edge, "count": n})
    if child_blockers:
        raise ManifestFreezeError(f"ruta_item child blockers: {child_blockers}")
    return {"incoming_fk": incoming, "outgoing_fk": outgoing, "child_blockers": []}


def _validate_iniciadores_after_ri_sim(
    conn: Connection, ini_ids: set[int], ri_ids: set[int]
) -> dict[str, Any]:
    incoming = load_iniciador_ruta_incoming_fks(conn)
    violations: list[dict[str, Any]] = []
    for iid in sorted(ini_ids):
        ri_surv = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}") - ri_ids
        rp_surv = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}")
        if ri_surv or rp_surv:
            violations.append(
                {
                    "iniciador_id": iid,
                    "ruta_item_surviving": sorted(ri_surv),
                    "ruta_pool_surviving": sorted(rp_surv),
                }
            )
        for edge in incoming:
            tbl, col = edge["child_table"], edge["child_column"]
            if tbl in ("ruta_item", "ruta_pool_dia"):
                continue
            n = int(
                _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :id", {"id": iid}) or 0
            )
            if n and edge.get("delete_rule") not in ("CASCADE",):
                violations.append({"iniciador_id": iid, "blocker": edge, "count": n})
    if violations:
        raise ManifestFreezeError(f"ini blockers after ri sim: {violations[:3]}")
    return {"valid": True, "violations": []}


def _tipo_counts(conn: Connection, ini_ids: set[int]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for iid in ini_ids:
        t = _scalar(conn, "SELECT tipo_iniciador FROM iniciador_ruta WHERE id = :id", {"id": iid})
        counts[str(t)] = counts.get(str(t), 0) + 1
    return counts


def _empty_routes_metadata(conn: Connection, ri_ids: set[int]) -> dict[str, Any]:
    groups_empty: list[dict[str, Any]] = []
    routes_empty: list[dict[str, Any]] = []
    affected_groups: set[int] = set()
    affected_routes: set[int] = set()
    for rid in ri_ids:
        row = conn.execute(
            text("SELECT ruta_trabajo_id, ruta_grupo_id FROM ruta_item WHERE id = :id"),
            {"id": rid},
        ).fetchone()
        if not row:
            continue
        if row[0]:
            affected_routes.add(row[0])
        if row[1]:
            affected_groups.add(row[1])
    for gid in sorted(affected_groups):
        items = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_grupo_id = {gid}")
        if items <= ri_ids:
            groups_empty.append({"ruta_grupo_id": gid, "items_in_group": len(items)})
    for rtid in sorted(affected_routes):
        items = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rtid}")
        if items <= ri_ids:
            routes_empty.append({"ruta_trabajo_id": rtid, "items_in_route": len(items)})
    return {
        "groups_becoming_empty": groups_empty,
        "routes_becoming_empty": routes_empty,
        "policy": "NO auto-delete ruta_grupo/ruta_trabajo in 2C.2A'",
    }


def _resolve_notificacion_id(
    conn: Connection, iniciador_id: int, fk: dict[str, Any]
) -> int | None:
    """Resuelve notificacion_id desde diag, iniciador_ruta o actuacion."""
    nid = fk.get("notificacion_id")
    if nid:
        return int(nid)
    row = conn.execute(
        text("SELECT notificacion_id, actuacion_id FROM iniciador_ruta WHERE id = :id"),
        {"id": iniciador_id},
    ).fetchone()
    if row and row[0]:
        return int(row[0])
    act_id = fk.get("actuacion_id") or (row[1] if row else None)
    if act_id:
        act_nid = _scalar(
            conn, "SELECT notificacion_id FROM actuaciones WHERE id = :id", {"id": act_id}
        )
        if act_nid:
            return int(act_nid)
    return None


def _preserve_sources(
    conn: Connection,
    diag: dict[str, Any],
    source_119: set[int],
) -> dict[str, Any]:
    notif_sources: list[dict[str, Any]] = []
    oficio_chains: list[dict[str, Any]] = []
    for it in diag["initiators"]["items"]:
        iid = it["iniciador_id"]
        tipo = it["tipo_iniciador"]
        fk = it.get("source_fk") or {}
        if tipo == "REINSPECCION_NOTIFICACION":
            nid = _resolve_notificacion_id(conn, iid, fk)
            if nid:
                in_119 = nid in source_119
                bucket = "source_119_preserved" if in_119 else "other_source_preserved"
            else:
                in_119 = False
                bucket = "no_direct_source_notificacion"
            notif_sources.append(
                {
                    "iniciador_id": iid,
                    "notificacion_id": nid,
                    "preserve_policy": "NO_DELETE_NO_UPDATE",
                    "source_bucket": bucket,
                    "in_source_119": in_119,
                }
            )
        if tipo == "REINSPECCION_OFICIO":
            sg = it.get("source_graph") or {}
            oficio_chains.append(
                {
                    "iniciador_id": iid,
                    "comprobacion_id": fk.get("comprobacion_id"),
                    "oficio_id": fk.get("oficio_id"),
                    "chain": sg.get("comprobacion_chain"),
                    "preserve_policy": "NO_DELETE comprobacion/expediente/oficio",
                }
            )
    if len(notif_sources) != EXPECTED_RN:
        raise ManifestFreezeError(f"notif_sources: {len(notif_sources)} != {EXPECTED_RN}")
    for nid in {n["notificacion_id"] for n in notif_sources if n["notificacion_id"]}:
        if not _scalar(conn, "SELECT COUNT(*) FROM notificacion WHERE id = :id", {"id": nid}):
            raise ManifestFreezeError(f"notificacion {nid} missing")
    return {
        "notificaciones": notif_sources,
        "oficio_chains": oficio_chains,
        "source_119_count_referenced": sum(1 for n in notif_sources if n["in_source_119"]),
        "no_direct_source_count": sum(
            1 for n in notif_sources if n["source_bucket"] == "no_direct_source_notificacion"
        ),
    }


def _detect_cascades(
    conn: Connection,
    ri_ids: set[int],
    ini_ids: set[int],
) -> dict[str, Any]:
    """Cuenta filas hijas CASCADE que caerían con los deletes explícitos."""
    cascades: dict[str, int] = {}
    for parent, ids in (("ruta_item", ri_ids), ("iniciador_ruta", ini_ids)):
        for edge in _incoming_fk_to_table(conn, parent):
            if edge["delete_rule"] != "CASCADE":
                continue
            tbl, col = edge["child_table"], edge["child_column"]
            total = 0
            for chunk in _chunk_ids(ids, 300):
                ph = ",".join(str(i) for i in chunk)
                total += int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN ({ph})") or 0)
            if total:
                cascades[f"{parent}->{tbl}"] = total
    return {"physical_rows_by_edge": cascades, "total_physical": sum(cascades.values())}


def _simulate_unlock(conn: Connection, acts_38: set[int], ri_ids: set[int], ini_ids: set[int]) -> dict[str, Any]:
    unlocked: list[int] = []
    still: list[dict[str, Any]] = []
    for aid in sorted(acts_38):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp: set[int] = set()
        for iid in inis:
            rp |= _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}")
        if not (inis - ini_ids) and not (ri - ri_ids) and not rp:
            unlocked.append(aid)
        else:
            still.append({"actuacion_id": aid})
    if len(unlocked) != EXPECTED_ACTS_38 or still:
        raise ManifestFreezeError(f"unlock sim: {len(unlocked)}/38 still={len(still)}")
    return {
        "UNLOCKED_AFTER_2C2A_PRIME": EXPECTED_ACTS_38,
        "STILL_BLOCKED": 0,
        "UNLOCKED_ids": unlocked,
    }


def _protected_comp_regression(conn: Connection, prot: dict[str, set[int]]) -> dict[str, Any]:
    found = {
        str(cid): bool(_scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid}))
        for cid in PROTECTED_COMP_CLOSURE_8
    }
    in_prot = {str(cid): cid in prot.get("comprobacion", set()) for cid in PROTECTED_COMP_CLOSURE_8}
    return {
        "closure_8_ids": sorted(PROTECTED_COMP_CLOSURE_8),
        "exist_in_db": found,
        "in_expanded_protected": in_prot,
        "all_protected": all(in_prot.values()) and all(found.values()),
    }


def _users_simulation(conn: Connection, diag: dict[str, Any]) -> dict[str, Any]:
    us = diag.get("users_simulation", {})
    return {
        "users_test_fk_free_baseline_post_2c2b": USERS_FK_FREE_POST_2C2B,
        "users_test_fk_free_after_prime": us.get("after_2c2a_prime_sim", USERS_FK_FREE_POST_2C2B),
        "users_additionally_unlocked": us.get("incremental_prime", 0),
        "users_test_still_blocked": us.get("users_test_still_blocked"),
        "note": "informative; iniciador delete alone may not unlock users",
    }


def run_phase2c2a_prime_manifest_freeze(
    conn: Connection,
    *,
    source_diag_path: Path,
    protected_path: Path,
    apply_2c2b_path: Path,
) -> dict[str, Any]:
    """Orquestador freeze manifest FASE 2C.2A'."""
    baseline = _baseline_check(conn)
    loaded = load_safe_sets_from_diag(source_diag_path)
    diag = loaded["diag"]
    ri_ids = loaded["ruta_item"]
    ini_ids = loaded["iniciador_ruta"]
    acts_38 = loaded["acts_38"]
    ot_38 = loaded["ot_38"]

    for entity, ids in (("ruta_item", ri_ids), ("iniciador_ruta", ini_ids)):
        stale = validate_ids_exist(conn, entity, ids, label=entity)
        if stale:
            raise ManifestFreezeError(f"missing {entity}: {stale[:5]}")

    sem = _semantic_classification(diag)
    ri_meta = _ruta_item_metadata(conn, ri_ids)
    ri_fk = _validate_ruta_item_fks(conn, ri_ids)
    ini_fk = _validate_iniciadores_after_ri_sim(conn, ini_ids, ri_ids)
    tipo = _tipo_counts(conn, ini_ids)
    if tipo.get("REINSPECCION_NOTIFICACION") != EXPECTED_RN or tipo.get("REINSPECCION_OFICIO") != EXPECTED_RO:
        raise ManifestFreezeError(f"tipo counts: {tipo}")

    fk_valid = _validate_delete_order_fk(PHASE2C2A_PRIME_DELETE_ORDER, load_fk_edges(conn))
    if not fk_valid.get("valid"):
        raise ManifestFreezeError(f"delete order: {fk_valid.get('violations')}")

    apply_data = json.loads(apply_2c2b_path.read_text(encoding="utf-8"))
    source_119 = {int(x) for x in apply_data.get("preserved", {}).get("source_notificaciones_119", [])}
    if len(source_119) != 119:
        raise ManifestFreezeError(f"source_119: {len(source_119)}")
    preserve = _preserve_sources(conn, diag, source_119)
    empty_meta = _empty_routes_metadata(conn, ri_ids)
    cascades = _detect_cascades(conn, ri_ids, ini_ids)
    if cascades["total_physical"] != 0:
        raise ManifestFreezeError(f"unexpected cascades: {cascades}")

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    virtual = VirtualDeleteState()
    virtual.add_explicit("ruta_item", ri_ids)
    virtual.add_explicit("iniciador_ruta", ini_ids)
    closure = protection_closure_check(virtual, prot)
    if not closure.get("valid"):
        raise ManifestFreezeError(f"protected closure: {closure.get('conflicts', [])[:3]}")

    unlock = _simulate_unlock(conn, acts_38, ri_ids, ini_ids)
    comp_reg = _protected_comp_regression(conn, prot)
    users_sim = _users_simulation(conn, diag)

    orphan_36 = apply_data.get("preserved", {}).get("orphan_notificaciones_36", [])
    orphan_20 = apply_data.get("preserved", {}).get("orphan_comprobaciones_20", [])
    new_orphan = diag.get("new_orphan_docs", {}).get("NEW_ORPHAN_TEST_DOCUMENTS", {})

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2C2A_PRIME",
        "phase_name": "safe_ruta_item_and_initiator_wrappers_residual",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(source_diag_path.resolve()),
        "source_diag_sha256": file_sha256(source_diag_path),
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "safe_set_counts": {
            "ruta_item": EXPECTED_RI,
            "iniciador_ruta": EXPECTED_INI,
        },
        "classification": {
            "safe_test_initiator": EXPECTED_TEST_INITIATOR,
            "safe_wrapper_around_preserved_source": EXPECTED_PRESERVED_SOURCE,
            "by_iniciador_id": {str(k): v for k, v in sem["by_iniciador_id"].items()},
        },
        "acts_38_metadata": {
            "count": EXPECTED_ACTS_38,
            "SET_ACT_OLD": 38,
            "SET_ACT_STRUCTURED": 0,
            "policy": "NOT deleted in 2C.2A'",
        },
        "entities": {
            "ruta_item": [{"id": i, **next(m for m in ri_meta if m["id"] == i)} for i in sorted(ri_ids)],
            "iniciador_ruta": [
                {
                    "id": i,
                    "tipo_iniciador": next(
                        x["tipo_iniciador"]
                        for x in diag["initiators"]["items"]
                        if x["iniciador_id"] == i
                    ),
                    "manifest_classification": sem["by_iniciador_id"][i]["manifest_classification"],
                    "diag_classification_original": sem["by_iniciador_id"][i]["diag_classification_original"],
                }
                for i in sorted(ini_ids)
            ],
        },
        "delete_order": PHASE2C2A_PRIME_DELETE_ORDER,
        "forbidden_deletes": {e: 0 for e in FORBIDDEN_MANIFEST_ENTITIES},
        "expected_counts_before": {
            "ruta_item": BASELINE_POST_2C2B["ruta_item"],
            "iniciador_ruta": BASELINE_POST_2C2B["iniciador_ruta"],
        },
        "expected_counts_after": POST_EXPLICIT,
        "unchanged_counts": {
            k: v
            for k, v in BASELINE_POST_2C2B.items()
            if k not in POST_EXPLICIT
        },
        "expected_cascades": cascades,
        "preserve_sources": preserve,
        "future_2c2b_prime": {
            "actuaciones_38": sorted(acts_38),
            "orden_trabajo_38": sorted(ot_38),
            "ot_exclusive": diag["ot_analysis"]["EXCLUSIVE_TEST_count"] == 38,
            "future_cascades_metadata": diag.get("future_cascades", {}),
        },
        "future_orphan_candidates": {
            "notificaciones_25": new_orphan.get("notificaciones", []),
            "comprobacion_2289": new_orphan.get("comprobaciones", []),
            "policy": "reserved for post-2C.2B' audit; NOT 2C.2C yet",
        },
        "excluded": {
            "actuaciones_38": sorted(acts_38),
            "orden_trabajo_38": sorted(ot_38),
            "orphan_notificaciones_36": orphan_36,
            "orphan_comprobaciones_20": orphan_20,
            "source_notificaciones_119": sorted(source_119),
            "users": "NO_DELETE",
            "catalogos": "NO_DELETE",
            "ruta_grupo_ruta_trabajo": "NO_DELETE unless future ticket",
        },
        "admin_fallback_metadata": diag.get("admin_fallback_analysis", {}),
        "xlsx_cross_summary": "NO_MATCH_XLSX on blocker sources per 3H; protected closure applied",
        "empty_routes_metadata": empty_meta,
        "unlock_expected": unlock,
        "protected_intersection": 0,
        "protected_closure_detail": closure,
        "protected_comprobacion_regression": comp_reg,
        "users_unlock_simulation": users_sim,
        "validation": {
            "ids_exist": {
                "ruta_item": {"expected": EXPECTED_RI, "found": EXPECTED_RI, "missing": 0},
                "iniciador_ruta": {"expected": EXPECTED_INI, "found": EXPECTED_INI, "missing": 0},
            },
            "ruta_item_fk": ri_fk,
            "iniciador_fk_after_ri_sim": ini_fk,
            "tipo_counts": tipo,
            "delete_order_validated": fk_valid,
            "cascade_physical_total": cascades["total_physical"],
        },
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3H.1",
        "writes_executed": False,
        "baseline": baseline,
        "manifest": manifest,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def write_freeze_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
