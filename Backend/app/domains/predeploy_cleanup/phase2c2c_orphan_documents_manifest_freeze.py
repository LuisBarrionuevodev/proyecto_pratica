"""
PREDEPLOY-CLEANUP.3I.1 — congelar execution manifest FASE 2C.2C
(36 notificaciones + 20 comprobaciones CONFIRMADO_TEST huérfanas). Solo lectura.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
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
from app.domains.predeploy_cleanup.phase2c2b_sources_manifest_freeze import _protected_comp_regression
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    EMPTY_ROUTE_IDS,
    USERS_FK_FREE_POST_3H,
    _cascade_on_delete,
    _incoming_fk_edges,
    _known_test_guard,
    _load_known_test_ids_from_manifests,
    _surviving_refs,
    _users_simulation,
    _verify_empty_routes,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _fetch_ids,
    protection_closure_check,
)

PHASE2C2C_DELETE_ORDER = ["notificacion", "comprobacion"]

EXPECTED_SAFE_NOTIF = 36
EXPECTED_SAFE_COMP = 20
EXPECTED_BLOCKED_NOTIF = 25
EXPECTED_BLOCKED_COMP = 1

SAFE_NOTIFICACIONES_2C2C = (
    1480,
    1536,
    1557,
    1627,
    1636,
    1684,
    1738,
    1758,
    1761,
    1771,
    1852,
    1854,
    1859,
    1860,
    2003,
    2308,
    2312,
    2394,
    2563,
    2564,
    2573,
    2707,
    2910,
    2913,
    2921,
    2928,
    2933,
    2939,
    2942,
    2950,
    2953,
    2970,
    2976,
    2978,
    2991,
    3032,
)

SAFE_COMPROBACIONES_2C2C = (
    758,
    759,
    760,
    984,
    1485,
    1486,
    1496,
    1615,
    1679,
    2130,
    2197,
    2221,
    2231,
    2241,
    2275,
    2279,
    2283,
    2291,
    2303,
    2307,
)

BLOCKED_NOTIFICACIONES_25 = (
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

BLOCKED_COMPROBACION_2289 = 2289

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
    "notificacion": 2514,
    "comprobacion": 1550,
}

POST_EXPLICIT = {
    "notificacion": 2478,
    "comprobacion": 1530,
}

FORBIDDEN_MANIFEST_ENTITIES = frozenset(
    {
        "actuaciones",
        "orden_trabajo",
        "oficio",
        "expediente",
        "relevamiento",
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
        "ruta_trabajo",
        "ruta_grupo",
        "ruta_grupo_inspector",
    }
)


class ManifestFreezeError(Exception):
    """Aborta freeze del manifest FASE 2C.2C."""


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ManifestFreezeError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ManifestFreezeError(f"alembic={alembic}")
    counts: dict[str, int] = {}
    for table, expected in BASELINE_POST_3H.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            raise ManifestFreezeError(f"baseline {table}: {actual} != {expected}")
    return {"database": db, "alembic_revision": alembic, "counts": counts}


def load_safe_sets_from_diag(diag_path: Path) -> dict[str, Any]:
    """Carga y valida safe/blocked sets desde diagnóstico 3I."""
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    if data.get("writes_executed") is not False:
        raise ManifestFreezeError("source diag writes_executed != false")

    hist = data["historical_candidate_sets"]
    if hist["notif_raw_count"] != 61 or hist["comp_raw_count"] != 21:
        raise ManifestFreezeError(
            f"raw counts: notif={hist['notif_raw_count']} comp={hist['comp_raw_count']}"
        )

    notif = data["notifications"]
    comp = data["comprobaciones"]
    if notif["safe"]["count"] != EXPECTED_SAFE_NOTIF:
        raise ManifestFreezeError(f"safe notif count: {notif['safe']['count']}")
    if notif["blocked"]["count"] != EXPECTED_BLOCKED_NOTIF:
        raise ManifestFreezeError(f"blocked notif count: {notif['blocked']['count']}")
    if comp["safe"]["count"] != EXPECTED_SAFE_COMP:
        raise ManifestFreezeError(f"safe comp count: {comp['safe']['count']}")
    if comp["blocked"]["count"] != EXPECTED_BLOCKED_COMP:
        raise ManifestFreezeError(f"blocked comp count: {comp['blocked']['count']}")

    safe_notif = set(notif["safe"]["SAFE_NOTIFICACIONES_2C2C"])
    safe_comp = set(comp["safe"]["SAFE_COMPROBACIONES_2C2C"])
    blocked_notif = {b["id"] for b in notif["blocked"]["BLOCKED_NOTIFICACIONES_2C2C"]}
    blocked_comp = {b["id"] for b in comp["blocked"]["BLOCKED_COMPROBACIONES_2C2C"]}

    if safe_notif != set(SAFE_NOTIFICACIONES_2C2C):
        raise ManifestFreezeError("safe notif IDs != expected frozen list")
    if safe_comp != set(SAFE_COMPROBACIONES_2C2C):
        raise ManifestFreezeError("safe comp IDs != expected frozen list")
    if blocked_notif != set(BLOCKED_NOTIFICACIONES_25):
        raise ManifestFreezeError("blocked notif IDs != expected frozen list")
    if blocked_comp != {BLOCKED_COMPROBACION_2289}:
        raise ManifestFreezeError("blocked comp IDs != {2289}")

    if len(notif["safe"]["from_existing_36"]) != EXPECTED_SAFE_NOTIF:
        raise ManifestFreezeError("from_existing_36 != 36")
    if notif["safe"]["from_new_25"]:
        raise ManifestFreezeError("from_new_25 must be empty for SAFE set")
    if len(comp["safe"]["from_existing_20"]) != EXPECTED_SAFE_COMP:
        raise ManifestFreezeError("from_existing_20 != 20")

    source_119 = set(hist["source_notificaciones_119"])
    if safe_notif & source_119:
        raise ManifestFreezeError("safe notif intersects source_119")

    return {
        "diag_data": data,
        "safe_notificacion": safe_notif,
        "safe_comprobacion": safe_comp,
        "blocked_notificacion": blocked_notif,
        "blocked_comprobacion": blocked_comp,
        "source_119": source_119,
        "source_119_overlap_candidates": set(data["source_119_cross"]["candidate_cap_source_119"]),
    }


def _validate_safe_fk_zero(conn: Connection, table: str, ids: set[int]) -> dict[str, Any]:
    """Valida 0 refs entrantes para cada ID SAFE."""
    per_id: list[dict[str, Any]] = []
    for pk_id in sorted(ids):
        refs = _surviving_refs(conn, table, pk_id)
        act_refs = _fetch_ids(
            conn, f"SELECT id FROM actuaciones WHERE {table}_id = {pk_id}"
        )
        ini_refs = _fetch_ids(
            conn, f"SELECT id FROM iniciador_ruta WHERE {table}_id = {pk_id}"
        )
        if act_refs or ini_refs or refs["total_refs"] > 0:
            raise ManifestFreezeError(
                f"{table} {pk_id} has refs: act={act_refs} ini={ini_refs} fk={refs}"
            )
        per_id.append({"id": pk_id, "total_refs": 0})
    return {
        "incoming_fk_edges": _incoming_fk_edges(conn, table),
        "all_zero": True,
        "validated_ids": len(per_id),
    }


def _validate_cascades_zero(
    conn: Connection,
    safe_notif: set[int],
    safe_comp: set[int],
) -> dict[str, Any]:
    notif_casc = _cascade_on_delete(conn, "notificacion", safe_notif)
    comp_casc = _cascade_on_delete(conn, "comprobacion", safe_comp)
    if notif_casc["cascade_total"] != 0 or notif_casc["set_null_total"] != 0:
        raise ManifestFreezeError(f"notif cascade: {notif_casc}")
    if comp_casc["cascade_total"] != 0 or comp_casc["set_null_total"] != 0:
        raise ManifestFreezeError(f"comp cascade: {comp_casc}")
    nm_count = 0
    if safe_notif:
        ph = ",".join(str(i) for i in sorted(safe_notif))
        nm_count = int(
            _scalar(conn, f"SELECT COUNT(*) FROM notificacion_motivo WHERE notificacion_id IN ({ph})")
            or 0
        )
    if nm_count != 0:
        raise ManifestFreezeError(f"notificacion_motivo rows for SAFE: {nm_count}")
    return {
        "notificacion": notif_casc,
        "comprobacion": comp_casc,
        "notificacion_motivo_physical_rows": nm_count,
    }


def _validate_blocked_notificaciones(conn: Connection, blocked: set[int]) -> list[dict[str, Any]]:
    """Cada blocked notif debe tener >=1 expediente.notificacion_id."""
    links: list[dict[str, Any]] = []
    for nid in sorted(blocked):
        if not _scalar(conn, "SELECT COUNT(*) FROM notificacion WHERE id = :id", {"id": nid}):
            raise ManifestFreezeError(f"blocked notif {nid} missing")
        rows = _rows(
            conn,
            "SELECT id, oficio_id FROM expediente WHERE notificacion_id = :nid",
            {"nid": nid},
        )
        if not rows:
            raise ManifestFreezeError(f"blocked notif {nid} has no expediente ref")
        links.append(
            {
                "notificacion_id": nid,
                "expediente_ids": [r["id"] for r in rows],
                "expediente_count": len(rows),
            }
        )
    return links


def _audit_comprobacion_2289(conn: Connection) -> dict[str, Any]:
    cid = BLOCKED_COMPROBACION_2289
    if not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid}):
        raise ManifestFreezeError("comprobacion 2289 missing")

    act_refs = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE comprobacion_id = {cid}")
    ini_refs = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE comprobacion_id = {cid}")
    oficios = _rows(
        conn,
        "SELECT id, numero_oficio, comprobacion_id, juzgado_id FROM oficio WHERE comprobacion_id = :id",
        {"id": cid},
    )
    expedientes: list[dict[str, Any]] = []
    for o in oficios:
        expedientes.extend(
            _rows(
                conn,
                "SELECT id, oficio_id, notificacion_id, comprobacion_id FROM expediente WHERE oficio_id = :oid",
                {"oid": o["id"]},
            )
        )
    exp_by_comp = _rows(
        conn,
        "SELECT id, oficio_id, notificacion_id FROM expediente WHERE comprobacion_id = :id",
        {"id": cid},
    )

    exp_comp_count = int(
        _scalar(conn, "SELECT COUNT(*) FROM expediente WHERE comprobacion_id = :id", {"id": cid})
        or 0
    )
    oficio_count = int(
        _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE comprobacion_id = :id", {"id": cid}) or 0
    )

    if act_refs:
        raise ManifestFreezeError(f"2289 act refs: {act_refs}")
    if ini_refs:
        raise ManifestFreezeError(f"2289 ini refs: {ini_refs}")
    if exp_comp_count != 2:
        raise ManifestFreezeError(f"2289 expediente.comprobacion_id count: {exp_comp_count}")
    if oficio_count != 1:
        raise ManifestFreezeError(f"2289 oficio count: {oficio_count}")

    oficio_1662 = next((o for o in oficios if o["id"] == 1662), None)
    if not oficio_1662 or oficio_1662.get("numero_oficio") != "OF8430":
        raise ManifestFreezeError(f"oficio 1662/OF8430 mismatch: {oficios}")

    exp_3104 = next((e for e in expedientes if e["id"] == 3104), None)
    if not exp_3104 or exp_3104.get("oficio_id") != 1662:
        raise ManifestFreezeError(f"expediente 3104 chain mismatch: {expedientes}")

    return {
        "comprobacion_id": cid,
        "classification": "INDETERMINATE",
        "keep_policy": "KEEP_ADMIN_CHAIN",
        "graph_classification": "ALL_TEST_ORPHAN",
        "actuaciones_refs": act_refs,
        "iniciador_ruta_refs": ini_refs,
        "expediente_comprobacion_count": exp_comp_count,
        "oficio_comprobacion_count": oficio_count,
        "oficios": oficios,
        "expedientes_via_oficio": expedientes,
        "expedientes_via_comprobacion": exp_by_comp,
    }


def _build_future_admin_graph(
    conn: Connection,
    blocked_notif_links: list[dict[str, Any]],
    comp_2289_audit: dict[str, Any],
) -> dict[str, Any]:
    notif_exp_links = [
        {
            "notificacion_id": link["notificacion_id"],
            "expediente_id": eid,
            "classification": "FUTURE_ADMIN_GRAPH_CANDIDATE",
        }
        for link in blocked_notif_links
        for eid in link["expediente_ids"]
    ]
    exp_ids = sorted({x["expediente_id"] for x in notif_exp_links})
    exp_ids_from_2289 = sorted(
        {e["id"] for e in comp_2289_audit["expedientes_via_comprobacion"]}
        | {e["id"] for e in comp_2289_audit["expedientes_via_oficio"]}
    )
    all_exp = sorted(set(exp_ids) | set(exp_ids_from_2289))

    oficio_ids = sorted({o["id"] for o in comp_2289_audit["oficios"]})
    oficio_links = [
        {
            "oficio_id": o["id"],
            "numero_oficio": o.get("numero_oficio"),
            "comprobacion_id": o.get("comprobacion_id"),
            "classification": "FUTURE_ADMIN_GRAPH_CANDIDATE",
        }
        for o in comp_2289_audit["oficios"]
    ]

    return {
        "policy": "FUTURE_ADMIN_GRAPH_CANDIDATE — NOT SAFE_DELETE until dedicated diag",
        "notification_expediente_ids": exp_ids,
        "notification_expediente_links": notif_exp_links,
        "comprobacion_2289_expediente_ids": exp_ids_from_2289,
        "expediente_ids_union": all_exp,
        "oficio_ids": oficio_ids,
        "oficio_links": oficio_links,
        "source_links": {
            "blocked_notificaciones_25": len(blocked_notif_links),
            "blocked_comprobacion_2289": BLOCKED_COMPROBACION_2289,
        },
    }


def _validate_protected_intersection(
    conn: Connection,
    safe_notif: set[int],
    safe_comp: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    pn = safe_notif & prot.get("notificacion", set())
    pc = safe_comp & prot.get("comprobacion", set())
    pc8 = safe_comp & PROTECTED_COMP_CLOSURE_8
    if pn or pc or pc8:
        raise ManifestFreezeError(f"protected intersection: notif={pn} comp={pc} closure8={pc8}")

    comp_reg = _protected_comp_regression(conn, prot)
    if not comp_reg["all_protected"]:
        raise ManifestFreezeError("protected comprobacion regression failed")

    for cid in PROTECTED_COMP_CLOSURE_8:
        if cid in safe_comp:
            raise ManifestFreezeError(f"closure-8 {cid} in safe comp")

    return {
        "notificacion_intersection": sorted(pn),
        "comprobacion_intersection": sorted(pc),
        "closure_8_intersection": sorted(pc8),
        "protected_comprobacion_regression": comp_reg,
        "intersection_total": 0,
    }


def run_phase2c2c_orphan_documents_manifest_freeze(
    conn: Connection,
    *,
    diag_path: Path,
    protected_path: Path,
    manifest_paths: list[Path],
) -> dict[str, Any]:
    """Orquestador freeze manifest FASE 2C.2C."""
    baseline = _baseline_check(conn)
    loaded = load_safe_sets_from_diag(diag_path)
    diag_data = loaded["diag_data"]

    safe_notif = loaded["safe_notificacion"]
    safe_comp = loaded["safe_comprobacion"]
    blocked_notif = loaded["blocked_notificacion"]
    blocked_comp = loaded["blocked_comprobacion"]

    if safe_notif & blocked_notif or safe_comp & blocked_comp:
        raise ManifestFreezeError("safe intersects blocked")

    for entity, ids in (("notificacion", safe_notif), ("comprobacion", safe_comp)):
        stale = validate_ids_exist(conn, entity, ids, label=entity)
        if stale:
            raise ManifestFreezeError(f"missing safe {entity}: {stale[:5]}")

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    prot_check = _validate_protected_intersection(conn, safe_notif, safe_comp, prot)

    notif_fk = _validate_safe_fk_zero(conn, "notificacion", safe_notif)
    comp_fk = _validate_safe_fk_zero(conn, "comprobacion", safe_comp)
    cascades = _validate_cascades_zero(conn, safe_notif, safe_comp)

    blocked_links = _validate_blocked_notificaciones(conn, blocked_notif)
    comp_2289 = _audit_comprobacion_2289(conn)
    future_admin = _build_future_admin_graph(conn, blocked_links, comp_2289)

    source_119_overlap = sorted(loaded["source_119_overlap_candidates"])
    if set(source_119_overlap) & safe_notif:
        raise ManifestFreezeError("source_119 overlap in safe notif")

    empty_routes = _verify_empty_routes(conn)
    for r in empty_routes:
        if not r["exists"] or r["ruta_item_refs"] != 0:
            raise ManifestFreezeError(f"empty route invalid: {r}")

    known = _load_known_test_ids_from_manifests(manifest_paths)
    test_guard = _known_test_guard(conn, known)
    if not test_guard["guard_ok"]:
        raise ManifestFreezeError(
            f"known test guard: acts={test_guard['known_test_act_ids_remaining_count']} "
            f"ots={test_guard['known_test_ot_ids_remaining_count']}"
        )

    virtual = VirtualDeleteState()
    virtual.add_explicit("notificacion", safe_notif)
    virtual.add_explicit("comprobacion", safe_comp)
    closure = protection_closure_check(virtual, prot)
    if not closure.get("valid"):
        raise ManifestFreezeError(f"protected closure: {closure.get('conflicts', [])[:3]}")

    fk_valid = _validate_delete_order_fk(PHASE2C2C_DELETE_ORDER, load_fk_edges(conn))
    if not fk_valid.get("valid"):
        raise ManifestFreezeError(f"delete order: {fk_valid.get('violations')}")

    users_sim = _users_simulation(conn, safe_notif, safe_comp)
    if users_sim["users_test_fk_free_after_2c2c_sim"] != USERS_FK_FREE_POST_3H:
        raise ManifestFreezeError(
            f"users fk-free after sim: {users_sim['users_test_fk_free_after_2c2c_sim']}"
        )
    if users_sim["users_additionally_unlocked"] != 0:
        raise ManifestFreezeError("users_additionally_unlocked != 0")

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2C2C",
        "phase_name": "safe_orphan_test_documents_notificacion_comprobacion",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(diag_path.resolve()),
        "source_diag_sha256": file_sha256(diag_path),
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "safe_set_counts": {
            "notificacion": EXPECTED_SAFE_NOTIF,
            "comprobacion": EXPECTED_SAFE_COMP,
            "total_documents": EXPECTED_SAFE_NOTIF + EXPECTED_SAFE_COMP,
        },
        "classification": {
            "safe_orphan_test_notificacion": EXPECTED_SAFE_NOTIF,
            "safe_orphan_test_comprobacion": EXPECTED_SAFE_COMP,
        },
        "entities": {
            "notificacion": sorted(safe_notif),
            "comprobacion": sorted(safe_comp),
        },
        "delete_order": PHASE2C2C_DELETE_ORDER,
        "forbidden_deletes": {e: 0 for e in FORBIDDEN_MANIFEST_ENTITIES},
        "expected_counts_before": {
            "notificacion": BASELINE_POST_3H["notificacion"],
            "comprobacion": BASELINE_POST_3H["comprobacion"],
        },
        "expected_counts_after": POST_EXPLICIT,
        "unchanged_counts": {
            k: v
            for k, v in BASELINE_POST_3H.items()
            if k not in POST_EXPLICIT
        },
        "expected_cascades": {
            "notificacion": cascades["notificacion"]["cascade_physical"],
            "comprobacion": cascades["comprobacion"]["cascade_physical"],
            "cascade_total": 0,
        },
        "expected_set_null": {
            "notificacion": cascades["notificacion"]["set_null_physical"],
            "comprobacion": cascades["comprobacion"]["set_null_physical"],
            "set_null_total": 0,
        },
        "blocked": {
            "notificacion": sorted(blocked_notif),
            "comprobacion": sorted(blocked_comp),
        },
        "future_admin_graph": future_admin,
        "future_admin_cleanup": {
            "blocked_notificaciones": EXPECTED_BLOCKED_NOTIF,
            "blocked_comprobaciones": [BLOCKED_COMPROBACION_2289],
            "notification_expediente_ids": future_admin["notification_expediente_ids"],
        },
        "preserve": {
            "blocked_notificaciones_25": sorted(blocked_notif),
            "blocked_comprobacion_2289": BLOCKED_COMPROBACION_2289,
            "source_119_overlap_15": source_119_overlap,
            "protected_notificaciones": len(prot.get("notificacion", set())),
            "protected_comprobaciones": len(prot.get("comprobacion", set())),
            "future_admin_graph": future_admin["expediente_ids_union"],
            "empty_routes_12": list(EMPTY_ROUTE_IDS),
            "policy": "IDs in preserve MUST NOT appear in entities DELETE",
        },
        "comprobacion_2289_audit": comp_2289,
        "blocked_notificacion_expediente_links": blocked_links,
        "empty_routes_residual": empty_routes,
        "known_test_guards": {
            "acts_remaining": test_guard["known_test_act_ids_remaining_count"],
            "ot_remaining": test_guard["known_test_ot_ids_remaining_count"],
            "guard_ok": test_guard["guard_ok"],
            "detail": test_guard,
        },
        "source_119_cross": {
            "candidate_cap_source_119": source_119_overlap,
            "safe_cap_source_119": [],
            "count_safe_overlap": 0,
        },
        "protected_intersection": 0,
        "protected_closure_detail": closure,
        "protected_validation": prot_check,
        "users_unlock_simulation": users_sim,
        "catalog_effects": {
            "rubro": "no direct FK from SAFE docs",
            "juzgado_catalogo": "NO_DELETE — oficio 1662 retains juzgado ref",
            "policy": "NO_DELETE catalogos",
        },
        "validation": {
            "ids_exist": {
                "notificacion": {
                    "expected": EXPECTED_SAFE_NOTIF,
                    "found": EXPECTED_SAFE_NOTIF,
                    "missing": 0,
                },
                "comprobacion": {
                    "expected": EXPECTED_SAFE_COMP,
                    "found": EXPECTED_SAFE_COMP,
                    "missing": 0,
                },
            },
            "safe_fk_zero": {
                "notificacion": notif_fk,
                "comprobacion": comp_fk,
            },
            "blocked_notificaciones_expediente_refs": len(blocked_links),
            "delete_order_validated": fk_valid,
            "cascade_physical_total": 0,
            "set_null_physical_total": 0,
            "notificacion_motivo_physical_rows": cascades["notificacion_motivo_physical_rows"],
        },
        "document_cleanup_policy": diag_data.get("document_cleanup_policy"),
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3I.1",
        "writes_executed": False,
        "baseline": baseline,
        "manifest": manifest,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def write_freeze_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
