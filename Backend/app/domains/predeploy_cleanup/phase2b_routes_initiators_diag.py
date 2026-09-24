"""
PREDEPLOY-CLEANUP.3C-DIAG — FASE 2B rutas/iniciadores (read-only).

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

from app.domains.predeploy_cleanup.constants import (
    RELEVAMIENTOS_QA_IDS,
    SQL_TEST_USER_WHERE,
    TEST_ACTUACIONES_SQL,
)
from app.domains.predeploy_cleanup.execution_validator import (
    load_iniciador_ruta_incoming_fks,
    load_iniciador_ruta_outgoing_fks,
    load_test_iniciador_ids,
    validate_execution_plan,
)
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges, topological_delete_order
from app.domains.predeploy_cleanup.manifest_io import load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import (
    SOURCE_COLUMNS,
    _blocked_act_ids,
    _classify_source,
    _scalar,
    _rows,
    _test_user_ids,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    load_user_fk_columns,
)

PHASE2B_DELETE_ORDER = [
    "ruta_grupo_inspector",
    "ruta_item",
    "ruta_pool_dia",
    "ruta_grupo",
    "ruta_trabajo",
    "iniciador_ruta",
]

BASELINE_TABLES = (
    "users",
    "establecimiento_operativo",
    "ruta_trabajo",
    "ruta_grupo",
    "ruta_grupo_inspector",
    "ruta_item",
    "ruta_pool_dia",
    "iniciador_ruta",
    "actuaciones",
    "denuncia",
    "relevamiento",
    "orden_trabajo",
)

KNOWN_POST_2A = {
    "establecimiento_operativo": 1657,
    "actuaciones": 8487,
    "users": 2803,
}

SUITE_PATTERNS = re.compile(
    r"(hotfix_|reenc_|stab4|st4_|op_ruta|qa_|pr111_|test_hotfix|test_reenc|completar_trabajo)",
    re.I,
)

TEST_STREET_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-|St4_|Canon \d+", re.I)


def _count_table(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _baseline(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts = {t: _count_table(conn, t) for t in BASELINE_TABLES}
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "known_post_2a_check": {
            k: {"expected": v, "actual": counts.get(k), "match": counts.get(k) == v}
            for k, v in KNOWN_POST_2A.items()
        },
    }


def load_structured_acts_274(path: Path) -> set[int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {a["actuacion_id"] for a in data.get("acts", [])}


def _is_test_user(conn: Connection, user_id: int | None, test_users: set[int]) -> bool:
    return user_id is not None and user_id in test_users


def _suite_evidence(*texts: str | None) -> bool:
    blob = " ".join(t for t in texts if t)
    return bool(SUITE_PATTERNS.search(blob))


def _load_test_initiators_detail(conn: Connection, test_ini_ids: set[int]) -> list[dict[str, Any]]:
    if not test_ini_ids:
        return []
    detail: list[dict[str, Any]] = []
    for chunk in _chunk_ids(test_ini_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = _rows(
            conn,
            f"""
            SELECT ir.id, ir.tipo_iniciador, ir.estado_iniciador, ir.created_by_user_id,
                   ir.domicilio_id, ir.relevamiento_id, ir.denuncia_id, ir.notificacion_id,
                   ir.comprobacion_id, ir.oficio_id, ir.actuacion_id, ir.observaciones,
                   ir.created_at, ir.deleted_at,
                   (SELECT COUNT(*) FROM ruta_item ri WHERE ri.iniciador_ruta_id = ir.id) AS ruta_item_refs,
                   (SELECT COUNT(*) FROM ruta_pool_dia rpd WHERE rpd.iniciador_ruta_id = ir.id) AS ruta_pool_refs
            FROM iniciador_ruta ir
            WHERE ir.id IN ({ph})
            ORDER BY ir.id
            """,
        )
        detail.extend(rows)
    return detail


def _classify_ruta_item(
    row: dict[str, Any],
    prot: dict[str, set[int]],
    act_test_union: set[int],
    test_users: set[int],
) -> tuple[str, list[str]]:
    """Clasifica ruta_item en bucket A-D."""
    reasons: list[str] = []
    act_id = row.get("actuacion_id")
    ot_id = row.get("orden_trabajo_id")

    if act_id and act_id in prot.get("actuaciones", set()):
        reasons.append("actuacion_PROTECTED_REAL")
        return "TEST_WRAPPER_AROUND_REAL", reasons
    if ot_id and ot_id in prot.get("orden_trabajo", set()):
        reasons.append("orden_trabajo_PROTECTED_REAL")
        return "TEST_WRAPPER_AROUND_REAL", reasons

    if act_id and act_id in act_test_union:
        reasons.append("actuacion_CONFIRMADO_TEST")
        return "TEST_WRAPPER_SAFE", reasons

    ruta_creator_test = row.get("ruta_created_by_user_id") in test_users
    item_creator_test = row.get("created_by_user_id") in test_users
    ini_creator_test = row.get("ini_created_by_user_id") in test_users

    if ruta_creator_test:
        reasons.append("ruta_created_by_test")
    if item_creator_test:
        reasons.append("item_created_by_test")
    if ini_creator_test:
        reasons.append("iniciador_created_by_test")

    if _suite_evidence(row.get("observaciones_ejecucion"), row.get("ruta_observaciones")):
        reasons.append("suite_pattern_match")

    calle = row.get("calle") or ""
    if TEST_STREET_PATTERN.search(calle):
        reasons.append("fixture_calle")

    if ruta_creator_test and ini_creator_test:
        return "TEST_WRAPPER_SAFE", reasons
    if ini_creator_test and (item_creator_test or act_id in act_test_union):
        return "TEST_WRAPPER_SAFE", reasons
    if ini_creator_test and not act_id:
        return "TEST_WRAPPER_SAFE", reasons + ["iniciador_test_sin_actuacion"]

    if act_id and act_id not in act_test_union:
        return "INDETERMINADO", reasons + ["actuacion_no_en_conjunto_test"]

    if not ini_creator_test:
        return "REAL", reasons + ["iniciador_no_test"]

    return "INDETERMINADO", reasons + ["evidencia_insuficiente"]


def audit_route_items(
    conn: Connection,
    test_ini_ids: set[int],
    prot: dict[str, set[int]],
    act_test_union: set[int],
    test_users: set[int],
) -> dict[str, Any]:
    """Todos los ruta_item que referencian iniciadores test."""
    if not test_ini_ids:
        return {"total": 0, "bucket_counts": {}, "items": [], "buckets": {}}

    ph_ini = ",".join(str(i) for i in sorted(test_ini_ids))
    rows = _rows(
        conn,
        f"""
        SELECT ri.id AS ruta_item_id, ri.ruta_trabajo_id, ri.ruta_grupo_id,
               ri.iniciador_ruta_id, ri.orden_trabajo_id, ri.actuacion_id,
               ri.estado_ruta_item, ri.estado_ejecucion, ri.created_by_user_id,
               ri.observaciones_ejecucion, ri.deleted_at,
               rt.created_by_user_id AS ruta_created_by_user_id,
               rt.fecha AS ruta_fecha, rt.turno AS ruta_turno, rt.estado_ruta,
               ir.created_by_user_id AS ini_created_by_user_id, ir.tipo_iniciador,
               d.calle
        FROM ruta_item ri
        JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id
        JOIN ruta_trabajo rt ON rt.id = ri.ruta_trabajo_id
        LEFT JOIN domicilio d ON d.id = ir.domicilio_id
        WHERE ri.iniciador_ruta_id IN ({ph_ini})
        ORDER BY ri.id
        """,
    )

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    items: list[dict[str, Any]] = []

    for row in rows:
        bucket, reasons = _classify_ruta_item(row, prot, act_test_union, test_users)
        rec = {
            "ruta_item_id": row["ruta_item_id"],
            "ruta_trabajo_id": row["ruta_trabajo_id"],
            "ruta_grupo_id": row["ruta_grupo_id"],
            "iniciador_ruta_id": row["iniciador_ruta_id"],
            "estado_ruta_item": row["estado_ruta_item"],
            "estado_ejecucion": row["estado_ejecucion"],
            "orden_trabajo_id": row["orden_trabajo_id"],
            "actuacion_id": row["actuacion_id"],
            "grupo_id": row["ruta_grupo_id"],
            "created_by_user_id": row["created_by_user_id"],
            "classification": bucket,
            "reasons": reasons,
        }
        buckets[bucket].append(rec)
        items.append(rec)

    return {
        "total": len(items),
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "items": items,
        "buckets": {k: v for k, v in buckets.items()},
        "wrapper_around_real_count": len(buckets.get("TEST_WRAPPER_AROUND_REAL", [])),
        "wrapper_around_real_note": (
            "wrapper test eliminable; actuación PROTECTED_REAL permanece"
        ),
    }


def audit_route_pool(
    conn: Connection,
    test_ini_ids: set[int],
    prot: dict[str, set[int]],
    act_test_union: set[int],
    test_users: set[int],
) -> dict[str, Any]:
    if not test_ini_ids:
        return {"total": 0, "bucket_counts": {}, "rows": []}

    ph_ini = ",".join(str(i) for i in sorted(test_ini_ids))
    rows = _rows(
        conn,
        f"""
        SELECT rpd.id AS pool_id, rpd.iniciador_ruta_id, rpd.fecha, rpd.turno_id,
               rpd.estado, rpd.origen_tipo, rpd.actuacion_id, rpd.usuario_id,
               rpd.ruta_trabajo_id, rpd.ruta_item_id, rpd.created_at,
               ir.created_by_user_id AS ini_created_by_user_id, ir.tipo_iniciador
        FROM ruta_pool_dia rpd
        JOIN iniciador_ruta ir ON ir.id = rpd.iniciador_ruta_id
        WHERE rpd.iniciador_ruta_id IN ({ph_ini})
        ORDER BY rpd.id
        """,
    )

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        act_id = row.get("actuacion_id")
        if act_id and act_id in prot.get("actuaciones", set()):
            cls = "REAL/PROTECTED"
            reasons = ["actuacion_PROTECTED_REAL"]
        elif act_id and act_id in act_test_union:
            cls = "TEST_SAFE"
            reasons = ["actuacion_CONFIRMADO_TEST"]
        elif row.get("ini_created_by_user_id") in test_users and row.get("usuario_id") in test_users:
            cls = "TEST_SAFE"
            reasons = ["iniciador_y_usuario_test"]
        elif row.get("ini_created_by_user_id") in test_users:
            cls = "TEST_SAFE"
            reasons = ["iniciador_test"]
        else:
            cls = "INDETERMINADO"
            reasons = ["evidencia_insuficiente"]

        rec = {
            "pool_id": row["pool_id"],
            "iniciador_id": row["iniciador_ruta_id"],
            "fecha": str(row["fecha"]) if row.get("fecha") else None,
            "turno_id": row.get("turno_id"),
            "estado": row.get("estado"),
            "origen_tipo": row.get("origen_tipo"),
            "actuacion_id": act_id,
            "usuario_id": row.get("usuario_id"),
            "ruta_trabajo_id": row.get("ruta_trabajo_id"),
            "ruta_item_id": row.get("ruta_item_id"),
            "created_at": str(row.get("created_at")),
            "classification": cls,
            "reasons": reasons,
        }
        buckets[cls].append(rec)

    return {
        "total": len(rows),
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "rows": [r for lst in buckets.values() for r in lst],
        "buckets": {k: v for k, v in buckets.items()},
    }


def audit_routes_composition(
    conn: Connection,
    route_items_audit: dict[str, Any],
) -> dict[str, Any]:
    """Clasifica rutas según composición de items (incluye items no-test en la misma ruta)."""
    candidate_ruta_ids = {i["ruta_trabajo_id"] for i in route_items_audit.get("items", [])}
    if not candidate_ruta_ids:
        return {"routes_with_test_items": 0, "classification_counts": {}, "routes": []}

    route_class: dict[int, str] = {}
    routes_detail: list[dict[str, Any]] = []

    for ruta_id in sorted(candidate_ruta_ids):
        all_items = _rows(
            conn,
            """
            SELECT ri.id, ri.iniciador_ruta_id, ri.actuacion_id,
                   ir.created_by_user_id AS ini_created_by
            FROM ruta_item ri
            JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id
            WHERE ri.ruta_trabajo_id = :rid
            """,
            {"rid": ruta_id},
        )
        test_item_ids = {
            i["ruta_item_id"]
            for i in route_items_audit.get("items", [])
            if i["ruta_trabajo_id"] == ruta_id
        }
        item_cls_map = {
            i["ruta_item_id"]: i["classification"]
            for i in route_items_audit.get("items", [])
            if i["ruta_trabajo_id"] == ruta_id
        }

        classifications = []
        for it in all_items:
            if it["id"] in test_item_ids:
                classifications.append(item_cls_map.get(it["id"], "INDETERMINADO"))
            else:
                classifications.append("REAL")

        has_real = "REAL" in classifications or "TEST_WRAPPER_AROUND_REAL" in classifications
        has_indet = "INDETERMINADO" in classifications
        all_test_safe = classifications and all(c == "TEST_WRAPPER_SAFE" for c in classifications)

        if all_test_safe:
            cls = "ALL_TEST"
        elif has_real and any(c == "TEST_WRAPPER_SAFE" for c in classifications):
            cls = "MIXED_TEST_REAL"
        elif has_indet:
            cls = "MIXED_TEST_INDETERMINATE"
        else:
            cls = "REAL/INDETERMINATE"

        rt = _rows(
            conn,
            "SELECT id, fecha, turno, estado_ruta, created_by_user_id FROM ruta_trabajo WHERE id = :id",
            {"id": ruta_id},
        )
        route_class[ruta_id] = cls
        routes_detail.append(
            {
                "ruta_trabajo_id": ruta_id,
                "classification": cls,
                "items_total": len(all_items),
                "items_test_refs": len(test_item_ids),
                "ruta_meta": rt[0] if rt else None,
                "item_classifications": Counter(classifications),
            }
        )

    cls_counts = Counter(r["classification"] for r in routes_detail)
    return {
        "routes_with_test_items": len(routes_detail),
        "classification_counts": dict(cls_counts),
        "routes": routes_detail,
        "note_mixed": "MIXED: borrar solo items TEST_WRAPPER_SAFE; no ruta completa",
    }


def audit_groups_orphans(
    conn: Connection,
    safe_item_ids: set[int],
    safe_pool_ids: set[int],
) -> dict[str, Any]:
    """Simula grupos vacíos tras delete de items test seguros."""
    virtual = VirtualDeleteState()
    virtual.add_explicit("ruta_item", safe_item_ids)
    virtual.add_explicit("ruta_pool_dia", safe_pool_ids)

    all_groups = _fetch_ids(conn, "SELECT id FROM ruta_grupo")
    orphan_candidates: list[dict[str, Any]] = []

    for gid in sorted(all_groups):
        items = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_grupo_id = {gid}")
        surviving = items - virtual.all_deleted("ruta_item")
        if items and not surviving:
            grp = _rows(
                conn,
                "SELECT id, ruta_trabajo_id, nombre FROM ruta_grupo WHERE id = :id",
                {"id": gid},
            )
            orphan_candidates.append(
                {
                    "ruta_grupo_id": gid,
                    "ruta_trabajo_id": grp[0]["ruta_trabajo_id"] if grp else None,
                    "items_before": len(items),
                    "items_after_sim": 0,
                    "classification": "ORPHAN_GROUP_CANDIDATE",
                }
            )

    all_rutas = _fetch_ids(conn, "SELECT id FROM ruta_trabajo")
    empty_ruta_candidates: list[dict[str, Any]] = []
    for rid in sorted(all_rutas):
        items = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rid}")
        surviving_items = items - virtual.all_deleted("ruta_item")
        groups = _fetch_ids(conn, f"SELECT id FROM ruta_grupo WHERE ruta_trabajo_id = {rid}")
        surviving_groups = groups.copy()
        for g in groups:
            g_items = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_grupo_id = {g}")
            if g_items and not (g_items - virtual.all_deleted("ruta_item")):
                surviving_groups.discard(g)
        if items and not surviving_items:
            rt = _rows(
                conn,
                "SELECT created_by_user_id, fecha FROM ruta_trabajo WHERE id = :id",
                {"id": rid},
            )
            empty_ruta_candidates.append(
                {
                    "ruta_trabajo_id": rid,
                    "items_before": len(items),
                    "groups_before": len(groups),
                    "classification": "EMPTY_TEST_CONTAINER",
                    "ruta_meta": rt[0] if rt else None,
                }
            )

    return {
        "orphan_group_candidates": len(orphan_candidates),
        "empty_ruta_candidates": len(empty_ruta_candidates),
        "orphan_groups": orphan_candidates[:200],
        "empty_rutas": empty_ruta_candidates[:200],
    }


def _classify_iniciador_source(
    conn: Connection,
    ini_row: dict[str, Any],
    prot: dict[str, set[int]],
    cleanup_act_ids: set[int],
    cleanup_den_ids: set[int],
    cleanup_rel_ids: set[int],
) -> list[dict[str, Any]]:
    sources = []
    for col in SOURCE_COLUMNS:
        sid = ini_row.get(col)
        if sid is None:
            continue
        tbl = col.replace("_id", "")
        cls = _classify_source(
            conn, tbl, sid, prot, cleanup_act_ids, cleanup_den_ids, cleanup_rel_ids
        )
        sources.append({"column": col, "source_id": sid, "classification": cls})
    return sources


def classify_iniciadores_final(
    conn: Connection,
    test_ini_ids: set[int],
    ini_detail: list[dict[str, Any]],
    prot: dict[str, set[int]],
    act_test_union: set[int],
    safe_item_ids: set[int],
    safe_pool_ids: set[int],
    wrapper_protected: set[int],
    cleanup_den_ids: set[int],
    cleanup_rel_ids: set[int],
) -> dict[str, Any]:
    buckets: dict[str, list[int]] = defaultdict(list)
    detail: list[dict[str, Any]] = []

    for row in ini_detail:
        iid = row["id"]
        sources = _classify_iniciador_source(
            conn, row, prot, act_test_union, cleanup_den_ids, cleanup_rel_ids
        )
        src_classes = {s["classification"] for s in sources}

        ri_surv = _fetch_ids(
            conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}"
        ) - safe_item_ids
        rp_surv = _fetch_ids(
            conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}"
        ) - safe_pool_ids

        if iid in wrapper_protected:
            bucket = "PROTECTED_REAL_SOURCE"
        elif "PROTECTED_REAL" in src_classes:
            bucket = "PROTECTED_REAL_SOURCE"
        elif ri_surv or rp_surv:
            bucket = "BLOCKED_BY_SURVIVING_ROUTE"
        elif "INDETERMINADO" in src_classes and not (
            row.get("tipo_iniciador") in ("DENUNCIA", "RELEVAMIENTO")
            and any(s["classification"] == "CONFIRMADO_TEST" for s in sources)
        ):
            bucket = "INDETERMINATE_SOURCE"
        elif row.get("created_by_user_id") and iid in test_ini_ids:
            bucket = "DELETE_AFTER_ROUTE_WRAPPERS"
        else:
            bucket = "BLOCKED_OTHER"

        buckets[bucket].append(iid)
        if len(detail) < 50:
            detail.append(
                {
                    "iniciador_id": iid,
                    "tipo_iniciador": row.get("tipo_iniciador"),
                    "estado_iniciador": row.get("estado_iniciador"),
                    "created_by_user_id": row.get("created_by_user_id"),
                    "sources": sources,
                    "ruta_item_surviving": len(ri_surv),
                    "ruta_pool_surviving": len(rp_surv),
                    "final_bucket": bucket,
                }
            )

    return {
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "buckets": {k: sorted(v) for k, v in buckets.items()},
        "detail_sample": detail,
    }


def audit_actuaciones_two_families(
    conn: Connection,
    set_act_old: set[int],
    set_act_structured: set[int],
    prot: dict[str, set[int]],
    safe_ini_delete: set[int],
) -> dict[str, Any]:
    union = set_act_old | set_act_structured
    overlap = set_act_old & set_act_structured
    prot_inter = union & prot.get("actuaciones", set())
    missing = []
    for aid in sorted(union):
        exists = _scalar(conn, "SELECT COUNT(*) FROM actuaciones WHERE id = :id", {"id": aid})
        if not exists:
            missing.append(aid)

    unlocked = 0
    still_blocked = 0
    per_act: list[dict[str, Any]] = []

    for act_id in sorted(union):
        inis = _fetch_ids(
            conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {act_id}"
        )
        blocking = inis - safe_ini_delete
        ini_via_item = _fetch_ids(
            conn,
            f"""
            SELECT DISTINCT ri.iniciador_ruta_id FROM ruta_item ri
            WHERE ri.actuacion_id = {act_id}
            """,
        )
        blocking |= ini_via_item - safe_ini_delete

        if blocking:
            still_blocked += 1
            status = "STILL_BLOCKED_AFTER_2B_SIM"
        else:
            unlocked += 1
            status = "UNLOCKED_AFTER_2B_SIM"

        if len(per_act) < 30:
            per_act.append(
                {
                    "actuacion_id": act_id,
                    "family": "SET_ACT_OLD" if act_id in set_act_old else "SET_ACT_STRUCTURED",
                    "iniciadores_direct": sorted(inis),
                    "blocking_after_2b_sim": sorted(blocking),
                    "status": status,
                }
            )

    return {
        "SET_ACT_OLD_count": len(set_act_old),
        "SET_ACT_STRUCTURED_count": len(set_act_structured),
        "union_count": len(union),
        "disjoint": len(overlap) == 0,
        "overlap_ids": sorted(overlap),
        "all_exist": len(missing) == 0,
        "missing_ids": missing,
        "protected_intersection": sorted(prot_inter),
        "protected_intersection_count": len(prot_inter),
        "unlocked_after_2b_sim": unlocked,
        "still_blocked_after_2b_sim": still_blocked,
        "note": "actuaciones NO en execution 2B; delete en FASE 2C",
        "sample": per_act,
    }


def audit_denuncias_unlock(
    conn: Connection,
    cleanup_den_ids: set[int],
    safe_item_ids: set[int],
    safe_pool_ids: set[int],
    safe_ini_delete: set[int],
) -> dict[str, Any]:
    blocked_phase1 = 75
    unlocked = 0
    still = 0
    detail: list[dict[str, Any]] = []

    for did in sorted(cleanup_den_ids):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE denuncia_id = {did}")
        blocking_ini = inis - safe_ini_delete
        ri = 0
        rp = 0
        for iid in inis:
            ri += len(
                _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}")
                - safe_item_ids
            )
            rp += len(
                _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}")
                - safe_pool_ids
            )
        if blocking_ini or ri or rp:
            still += 1
            status = "STILL_BLOCKED"
        else:
            unlocked += 1
            status = "UNLOCKED_AFTER_2B"

        if len(detail) < 20:
            detail.append(
                {
                    "denuncia_id": did,
                    "iniciadores": sorted(inis),
                    "blocking_iniciadores": sorted(blocking_ini),
                    "ruta_item_surviving": ri,
                    "ruta_pool_surviving": rp,
                    "status": status,
                }
            )

    return {
        "total_test_denuncias": len(cleanup_den_ids),
        "phase1_blocked_count": blocked_phase1,
        "unlocked_after_2b_sim": unlocked,
        "still_blocked": still,
        "note": "NO delete denuncias en 2B",
        "sample": detail,
    }


def audit_relevamientos_unlock(
    conn: Connection,
    cleanup_rel_ids: set[int],
    safe_ini_delete: set[int],
) -> dict[str, Any]:
    qa_focus = sorted(RELEVAMIENTOS_QA_IDS)
    unlocked = 0
    still = 0
    detail: list[dict[str, Any]] = []

    for rid in sorted(cleanup_rel_ids):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}")
        blocking = inis - safe_ini_delete
        if blocking:
            still += 1
            status = "STILL_BLOCKED"
        else:
            unlocked += 1
            status = "UNLOCKED_AFTER_2B"

        rec = {
            "relevamiento_id": rid,
            "iniciadores": sorted(inis),
            "blocking_iniciadores": sorted(blocking),
            "status": status,
            "qa_focus": rid in RELEVAMIENTOS_QA_IDS,
        }
        detail.append(rec)

    qa_status = {r["relevamiento_id"]: r["status"] for r in detail if r["qa_focus"]}

    return {
        "total_test_relevamientos": len(cleanup_rel_ids),
        "phase1_blocked_count": 26,
        "unlocked_after_2b_sim": unlocked,
        "still_blocked": still,
        "qa_focus_ids": qa_focus,
        "qa_focus_status": qa_status,
        "note": "NO delete relevamientos en 2B",
        "detail": detail,
    }


def simulate_user_unlock(
    conn: Connection,
    test_users: set[int],
    virtual: VirtualDeleteState,
    users_unlocked_after_2a: int,
) -> dict[str, Any]:
    """Simula users test sin FK tras 2B (incremental sobre 2A)."""
    fk_columns = load_user_fk_columns(conn)
    unlocked_now: set[int] = set()
    still_blocked: set[int] = set()

    deleted_by_table: dict[str, set[int]] = defaultdict(set)
    for table in virtual.explicit:
        deleted_by_table[table].update(virtual.explicit[table])

    for uid in test_users:
        has_ref = False
        for table, col in fk_columns:
            rows = conn.execute(
                text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"),
                {"uid": uid},
            ).fetchall()
            for r in rows:
                rid = r[0]
                if rid in deleted_by_table.get(table, set()):
                    continue
                has_ref = True
                break
            if has_ref:
                break
        if has_ref:
            still_blocked.add(uid)
        else:
            unlocked_now.add(uid)

    additionally = unlocked_now  # full recount; report delta vs 2A separately
    return {
        "users_unlocked_after_2a_baseline": users_unlocked_after_2a,
        "users_test_without_any_fk_after_2b_sim": len(unlocked_now),
        "users_test_still_blocked_after_2b_sim": len(still_blocked),
        "users_additionally_unlocked_by_2b_estimate": max(
            0, len(unlocked_now) - users_unlocked_after_2a
        ),
        "note": "recuento completo post-sim; delta vs 231 de 2A",
        "unlocked_sample": sorted(unlocked_now)[:40],
    }


def build_safe_sets(
    route_items_audit: dict[str, Any],
    pool_audit: dict[str, Any],
    groups_audit: dict[str, Any],
    ini_final: dict[str, Any],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    safe_items = {
        i["ruta_item_id"]
        for i in route_items_audit.get("items", [])
        if i["classification"] == "TEST_WRAPPER_SAFE"
    }
    safe_pool = {
        r["pool_id"]
        for r in pool_audit.get("rows", [])
        if r["classification"] == "TEST_SAFE"
    }
    safe_ini = set(ini_final.get("buckets", {}).get("DELETE_AFTER_ROUTE_WRAPPERS", []))
    safe_rgi = set()  # populated in topological sim if needed
    safe_grupos = {
        g["ruta_grupo_id"]
        for g in groups_audit.get("orphan_groups", [])
        if g.get("classification") == "ORPHAN_GROUP_CANDIDATE"
    }
    safe_rutas = {
        r["ruta_trabajo_id"]
        for r in groups_audit.get("empty_rutas", [])
        if r.get("classification") == "EMPTY_TEST_CONTAINER"
    }

    conflicts = []
    for i in route_items_audit.get("items", []):
        if i["classification"] == "TEST_WRAPPER_AROUND_REAL":
            act = i.get("actuacion_id")
            if act and act in prot.get("actuaciones", set()):
                conflicts.append(
                    {
                        "type": "wrapper_around_real",
                        "ruta_item_id": i["ruta_item_id"],
                        "actuacion_id": act,
                        "action": "delete_wrapper_only",
                    }
                )

    return {
        "SAFE_RUTA_ITEM": sorted(safe_items),
        "SAFE_RUTA_POOL": sorted(safe_pool),
        "SAFE_RUTA_GRUPO_INSPECTOR": sorted(safe_rgi),
        "SAFE_RUTA_GRUPO_EMPTY": sorted(safe_grupos),
        "SAFE_RUTA_TRABAJO_EMPTY": sorted(safe_rutas),
        "SAFE_INICIADOR": sorted(safe_ini),
        "counts": {
            "SAFE_RUTA_ITEM": len(safe_items),
            "SAFE_RUTA_POOL": len(safe_pool),
            "SAFE_RUTA_GRUPO_EMPTY": len(safe_grupos),
            "SAFE_RUTA_TRABAJO_EMPTY": len(safe_rutas),
            "SAFE_INICIADOR": len(safe_ini),
        },
        "protected_conflicts": conflicts,
        "manifest_ready": len(conflicts) == 0,
        "note": "No generar apply manifest definitivo si quedan INDETERMINADO sin resolver",
    }


def topological_simulation(
    conn: Connection,
    safe_sets: dict[str, Any],
) -> dict[str, Any]:
    edges = load_fk_edges(conn)
    order = topological_delete_order(PHASE2B_DELETE_ORDER, edges)

    explicit: dict[str, set[int]] = {
        "ruta_item": set(safe_sets["SAFE_RUTA_ITEM"]),
        "ruta_pool_dia": set(safe_sets["SAFE_RUTA_POOL"]),
        "ruta_grupo": set(safe_sets["SAFE_RUTA_GRUPO_EMPTY"]),
        "ruta_trabajo": set(safe_sets["SAFE_RUTA_TRABAJO_EMPTY"]),
        "iniciador_ruta": set(safe_sets["SAFE_INICIADOR"]),
    }

    rgi_ids: set[int] = set()
    for gid in safe_sets["SAFE_RUTA_GRUPO_EMPTY"]:
        rgi_ids |= _fetch_ids(
            conn, f"SELECT id FROM ruta_grupo_inspector WHERE ruta_grupo_id = {gid}"
        )
    explicit["ruta_grupo_inspector"] = rgi_ids
    safe_sets["SAFE_RUTA_GRUPO_INSPECTOR"] = sorted(rgi_ids)
    safe_sets["counts"]["SAFE_RUTA_GRUPO_INSPECTOR"] = len(rgi_ids)

    virtual = VirtualDeleteState()
    for table, ids in explicit.items():
        virtual.add_explicit(table, ids)

    validation = validate_execution_plan(
        conn,
        {t: explicit.get(t, set()) for t in PHASE2B_DELETE_ORDER},
        virtual,
        edges,
    )

    before = {t: _count_table(conn, t) for t in PHASE2B_DELETE_ORDER}
    after = {
        t: before[t] - len(explicit.get(t, set()))
        for t in PHASE2B_DELETE_ORDER
    }

    incoming_ini = load_iniciador_ruta_incoming_fks(conn)
    outgoing_ini = load_iniciador_ruta_outgoing_fks(conn)

    return {
        "proposed_delete_order": order,
        "fk_incoming_iniciador": incoming_ini,
        "fk_outgoing_iniciador": outgoing_ini,
        "explicit_counts": {k: len(v) for k, v in explicit.items()},
        "validation": validation,
        "post_simulated_counts": {
            "before": before,
            "after": after,
            "delta": {t: before[t] - after[t] for t in PHASE2B_DELETE_ORDER},
        },
        "actuaciones_unchanged": _count_table(conn, "actuaciones"),
        "denuncia_unchanged": _count_table(conn, "denuncia"),
        "relevamiento_unchanged": _count_table(conn, "relevamiento"),
        "users_unchanged": _count_table(conn, "users"),
    }


def run_phase2b_routes_initiators_diag(
    conn: Connection,
    *,
    protected_manifest_path: Path,
    structured_acts_diag_path: Path,
    phase2a_apply_path: Path | None = None,
    dry_run_v3_path: Path | None = None,
) -> dict[str, Any]:
    """Orquestador read-only FASE 2B."""
    protected_manifest = load_manifest(protected_manifest_path)
    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))

    set_act_structured = load_structured_acts_274(structured_acts_diag_path)
    set_act_old = _blocked_act_ids(conn, prot)
    act_test_union = set_act_old | set_act_structured

    test_users = _test_user_ids(conn)
    test_ini_ids = load_test_iniciador_ids(conn)

    cleanup_den_ids = _fetch_ids(
        conn,
        f"""
        SELECT d.id FROM denuncia d
        JOIN users u ON u.id = d.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    cleanup_rel_ids = _fetch_ids(
        conn,
        f"""
        SELECT r.id FROM relevamiento r
        JOIN users u ON u.id = r.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """
    ) | RELEVAMIENTOS_QA_IDS

    wrapper_protected: set[int] = set()
    wrapper_deletable: set[int] = set()
    if dry_run_v3_path and dry_run_v3_path.is_file():
        v3 = json.loads(dry_run_v3_path.read_text(encoding="utf-8"))
        wrap = v3.get("iniciador_wrapper_incorporated", {})
        wrapper_protected = set(wrap.get("protected_from_wrappers_64", []))
        wrapper_deletable = set(wrap.get("deletable_from_wrappers_64", []))

    users_unlocked_2a = 231
    if phase2a_apply_path and phase2a_apply_path.is_file():
        p2a = json.loads(phase2a_apply_path.read_text(encoding="utf-8"))
        users_unlocked_2a = p2a.get("post_commit_users", {}).get(
            "UNLOCKED_FOR_PHASE2D_count", 231
        )

    baseline = _baseline(conn)
    ini_detail = _load_test_initiators_detail(conn, test_ini_ids)

    route_items = audit_route_items(conn, test_ini_ids, prot, act_test_union, test_users)
    pool_audit = audit_route_pool(conn, test_ini_ids, prot, act_test_union, test_users)
    routes_audit = audit_routes_composition(conn, route_items)

    safe_item_ids = {
        i["ruta_item_id"]
        for i in route_items.get("items", [])
        if i["classification"] == "TEST_WRAPPER_SAFE"
    }
    safe_pool_ids = {
        r["pool_id"] for r in pool_audit.get("rows", []) if r["classification"] == "TEST_SAFE"
    }
    groups_audit = audit_groups_orphans(conn, safe_item_ids, safe_pool_ids)

    ini_final = classify_iniciadores_final(
        conn,
        test_ini_ids,
        ini_detail,
        prot,
        act_test_union,
        safe_item_ids,
        safe_pool_ids,
        wrapper_protected,
        cleanup_den_ids,
        cleanup_rel_ids,
    )
    safe_ini_delete = set(ini_final["buckets"].get("DELETE_AFTER_ROUTE_WRAPPERS", []))

    acts_families = audit_actuaciones_two_families(
        conn, set_act_old, set_act_structured, prot, safe_ini_delete
    )
    denuncias_unlock = audit_denuncias_unlock(
        conn, cleanup_den_ids, safe_item_ids, safe_pool_ids, safe_ini_delete
    )
    relevamientos_unlock = audit_relevamientos_unlock(conn, cleanup_rel_ids, safe_ini_delete)

    safe_sets = build_safe_sets(route_items, pool_audit, groups_audit, ini_final, prot)
    topo = topological_simulation(conn, safe_sets)

    virtual = VirtualDeleteState()
    for table in PHASE2B_DELETE_ORDER:
        entity_key = {
            "ruta_grupo_inspector": "SAFE_RUTA_GRUPO_INSPECTOR",
            "ruta_item": "SAFE_RUTA_ITEM",
            "ruta_pool_dia": "SAFE_RUTA_POOL",
            "ruta_grupo": "SAFE_RUTA_GRUPO_EMPTY",
            "ruta_trabajo": "SAFE_RUTA_TRABAJO_EMPTY",
            "iniciador_ruta": "SAFE_INICIADOR",
        }[table]
        virtual.add_explicit(table, set(safe_sets.get(entity_key, [])))

    user_unlock = simulate_user_unlock(conn, test_users, virtual, users_unlocked_2a)

    # OT readiness after 2C acts (simulation only)
    ot_from_413 = set()
    for aid in act_test_union:
        ot = _scalar(conn, "SELECT orden_trabajo_id FROM actuaciones WHERE id = :id", {"id": aid})
        if ot:
            ot_from_413.add(ot)

    ots_ready_2c = 0
    for ot_id in ot_from_413:
        acts = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        non_test = acts - act_test_union - prot.get("actuaciones", set())
        if not non_test and ot_id not in prot.get("orden_trabajo", set()):
            ots_ready_2c += 1

    source_classification: dict[str, Counter] = defaultdict(Counter)
    for row in ini_detail:
        sources = _classify_iniciador_source(
            conn, row, prot, act_test_union, cleanup_den_ids, cleanup_rel_ids
        )
        for s in sources:
            source_classification[s["column"]][s["classification"]] += 1

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3C-DIAG",
        "mode": "READ_ONLY_SELECT",
        "writes_executed": False,
        "baseline": baseline,
        "test_initiators": {
            "count_exact": len(test_ini_ids),
            "detail_count": len(ini_detail),
            "by_tipo": dict(Counter(r["tipo_iniciador"] for r in ini_detail)),
            "by_estado": dict(Counter(r["estado_iniciador"] for r in ini_detail)),
            "with_ruta_item_refs": sum(1 for r in ini_detail if r.get("ruta_item_refs")),
            "with_ruta_pool_refs": sum(1 for r in ini_detail if r.get("ruta_pool_refs")),
            "sample": ini_detail[:25],
        },
        "route_items": route_items,
        "route_pool": pool_audit,
        "routes": routes_audit,
        "groups": groups_audit,
        "iniciadores_final": ini_final,
        "source_classification": {
            col: dict(cnt) for col, cnt in source_classification.items()
        },
        "wrapper_64": {
            "protected_iniciadores": sorted(wrapper_protected),
            "deletable_iniciadores": sorted(wrapper_deletable),
            "protected_count": len(wrapper_protected),
            "deletable_count": len(wrapper_deletable),
        },
        "actuaciones_two_families": acts_families,
        "denuncias": denuncias_unlock,
        "relevamientos": relevamientos_unlock,
        "safe_sets": safe_sets,
        "blocked": {
            "iniciadores_BLOCKED_BY_SURVIVING_ROUTE": ini_final["bucket_counts"].get(
                "BLOCKED_BY_SURVIVING_ROUTE", 0
            ),
            "iniciadores_INDETERMINATE_SOURCE": ini_final["bucket_counts"].get(
                "INDETERMINATE_SOURCE", 0
            ),
            "iniciadores_PROTECTED_REAL_SOURCE": ini_final["bucket_counts"].get(
                "PROTECTED_REAL_SOURCE", 0
            ),
            "ruta_items_INDETERMINADO": route_items["bucket_counts"].get("INDETERMINADO", 0),
            "ruta_items_AROUND_REAL": route_items["bucket_counts"].get(
                "TEST_WRAPPER_AROUND_REAL", 0
            ),
        },
        "protected_conflicts": safe_sets.get("protected_conflicts", []),
        "topological_plan": topo,
        "unlock_simulation": {
            "actuaciones_413": acts_families,
            "denuncias_75": {
                "unlocked": denuncias_unlock["unlocked_after_2b_sim"],
                "still_blocked": denuncias_unlock["still_blocked"],
            },
            "relevamientos_26": {
                "unlocked": relevamientos_unlock["unlocked_after_2b_sim"],
                "still_blocked": relevamientos_unlock["still_blocked"],
            },
            "ots_ready_after_2c_acts_sim": ots_ready_2c,
            "ots_from_413_total": len(ot_from_413),
        },
        "user_unlock_simulation": user_unlock,
        "eo_note": {
            "establecimiento_operativo": baseline["counts"]["establecimiento_operativo"],
            "outside_2b_scope": True,
        },
    }


def write_phase2b_diag_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
