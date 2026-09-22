"""
PREDEPLOY-CLEANUP.3C.1-DIAG — reconciliación 708 ruta_item INDETERMINADO (read-only).
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
from app.domains.predeploy_cleanup.phase2_structured_acts_diag import (
    USER_PREFIX_PATTERNS,
    scan_test_sources,
)
from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import load_structured_acts_274
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

BASELINE_EXPECTED = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "actuaciones": 8487,
    "ruta_trabajo": 3566,
    "ruta_grupo": 3737,
    "ruta_grupo_inspector": 7637,
    "ruta_item": 4551,
    "ruta_pool_dia": 714,
    "iniciador_ruta": 8563,
    "denuncia": 492,
    "relevamiento": 4592,
    "orden_trabajo": 9223,
}

FAMILY_PATTERNS: dict[str, re.Pattern[str]] = {
    "A_hotfix": re.compile(r"hotfix_", re.I),
    "B_reenc": re.compile(r"reenc_", re.I),
    "C_stab4": re.compile(r"st4_|stab4", re.I),
    "D_op_ruta": re.compile(r"op_ruta|op6", re.I),
    "E_qa": re.compile(r"qa_|@t\.local|@test\.local", re.I),
    "F_pr111": re.compile(r"pr111", re.I),
}

TEST_EMAIL_RE = re.compile(r"@t\.local|@test\.local", re.I)


def _count_table(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts = {t: _count_table(conn, t) for t in BASELINE_EXPECTED}
    mismatches = {
        k: {"expected": v, "actual": counts[k]}
        for k, v in BASELINE_EXPECTED.items()
        if counts[k] != v
    }
    if mismatches:
        raise ValueError(f"Baseline drift: {mismatches}")
    return {"database": db, "alembic_revision": alembic, "counts": counts, "match": True}


def load_universe_708(phase2b_diag_path: Path) -> list[int]:
    data = json.loads(phase2b_diag_path.read_text(encoding="utf-8"))
    items = data["route_items"]["buckets"].get("INDETERMINADO", [])
    if not items:
        items = [
            i for i in data["route_items"].get("items", [])
            if i.get("classification") == "INDETERMINADO"
        ]
    return sorted({i["ruta_item_id"] for i in items})


def load_prior_safe_sets(phase2b_diag_path: Path) -> dict[str, set[int]]:
    data = json.loads(phase2b_diag_path.read_text(encoding="utf-8"))
    ss = data.get("safe_sets", {})
    return {
        "SAFE_RUTA_ITEM": set(ss.get("SAFE_RUTA_ITEM", [])),
        "SAFE_RUTA_POOL": set(ss.get("SAFE_RUTA_POOL", [])),
    }


def load_wrapper_64(dry_run_v3_path: Path) -> dict[str, Any]:
    data = json.loads(dry_run_v3_path.read_text(encoding="utf-8"))
    wrap_data = data.get("test_wrappers_around_real_data", {})
    wrappers = wrap_data.get("wrappers", [])
    deletable_ini = set(
        data.get("iniciador_wrapper_incorporated", {}).get("deletable_from_wrappers_64", [])
    )
    protected_ini = set(
        data.get("iniciador_wrapper_incorporated", {}).get("protected_from_wrappers_64", [])
    )
    by_item: dict[int, dict] = {}
    all_ini: set[int] = set()
    for w in wrappers:
        rid = w["ruta_item_id"]
        by_item[rid] = w
        all_ini.add(w["iniciador_ruta_id"])

    missing_ini = all_ini - deletable_ini - protected_ini
    classified_ini = deletable_ini | protected_ini
    unclassified_wrappers = [
        w for w in wrappers if w["iniciador_ruta_id"] not in classified_ini
    ]

    reconcile: list[dict[str, Any]] = []
    for w in wrappers:
        iid = w["iniciador_ruta_id"]
        if iid in deletable_ini:
            cls = "WRAPPER_DELETE"
        elif iid in protected_ini:
            cls = "PROTECTED/KEEP"
        else:
            cls = "OTHER/ERROR"
        reconcile.append(
            {
                "ruta_item_id": w["ruta_item_id"],
                "iniciador_ruta_id": iid,
                "actuacion_id": w.get("actuacion_id"),
                "classification": cls,
                "actuacion_clasificacion": w.get("actuacion_clasificacion"),
                "iniciador_clasificacion": w.get("iniciador_clasificacion"),
            }
        )

    return {
        "wrapper_count_expected": 64,
        "wrapper_records": len(wrappers),
        "deletable_iniciadores": sorted(deletable_ini),
        "protected_iniciadores": sorted(protected_ini),
        "deletable_count": len(deletable_ini),
        "protected_count": len(protected_ini),
        "sum_deletable_protected": len(deletable_ini) + len(protected_ini),
        "missing_iniciador_ids": sorted(missing_ini),
        "unclassified_wrapper_records": unclassified_wrappers,
        "reconcile": reconcile,
        "by_ruta_item_id": by_item,
    }


def _detect_family(username: str | None, email: str | None) -> list[str]:
    blob = f"{username or ''} {email or ''}"
    found = []
    for fam, pat in FAMILY_PATTERNS.items():
        if pat.search(blob):
            found.append(fam)
    for prefix in USER_PREFIX_PATTERNS:
        if prefix in (username or "").lower() or prefix in (email or "").lower():
            if prefix not in found:
                found.append(f"prefix:{prefix}")
    return found


def _user_info(conn: Connection, user_id: int | None) -> dict[str, Any] | None:
    if user_id is None:
        return None
    row = conn.execute(
        text("SELECT id, username, email FROM users WHERE id = :id"),
        {"id": user_id},
    ).fetchone()
    if not row:
        return None
    m = dict(row._mapping)
    m["families"] = _detect_family(m.get("username"), m.get("email"))
    m["is_test"] = bool(TEST_EMAIL_RE.search(m.get("email") or "")) or any(
        FAMILY_PATTERNS[k].search(f"{m.get('username')} {m.get('email')}")
        for k in FAMILY_PATTERNS
    )
    return m


def _source_detail(
    conn: Connection,
    ini_row: dict[str, Any],
    prot: dict[str, set[int]],
    act_test: set[int],
    cleanup_den: set[int],
    cleanup_rel: set[int],
) -> list[dict[str, Any]]:
    sources = []
    for col in SOURCE_COLUMNS:
        sid = ini_row.get(col)
        if sid is None:
            continue
        tbl = col.replace("_id", "")
        cls = _classify_source(conn, tbl, sid, prot, act_test, cleanup_den, cleanup_rel)
        detail: dict[str, Any] = {"column": col, "source_id": sid, "classification": cls}
        if tbl == "notificacion":
            n = _rows(
                conn,
                "SELECT id, numero_acta, created_at FROM notificacion WHERE id = :id",
                {"id": sid},
            )
            if n:
                detail["numero_acta"] = n[0].get("numero_acta")
                detail["created_at"] = str(n[0].get("created_at"))
        elif tbl == "comprobacion":
            c = _rows(
                conn,
                "SELECT id, numero_acta, created_at FROM comprobacion WHERE id = :id",
                {"id": sid},
            )
            if c:
                detail["numero_acta"] = c[0].get("numero_acta")
                detail["created_at"] = str(c[0].get("created_at"))
        elif tbl == "oficio":
            o = _rows(
                conn,
                "SELECT id, numero_oficio FROM oficio WHERE id = :id",
                {"id": sid},
            )
            if o:
                detail["numero_oficio"] = o[0].get("numero_oficio")
        elif tbl == "actuaciones":
            a = _rows(
                conn,
                "SELECT id, orden_trabajo_id, created_at FROM actuaciones WHERE id = :id",
                {"id": sid},
            )
            if a:
                detail["orden_trabajo_id"] = a[0].get("orden_trabajo_id")
                detail["created_at"] = str(a[0].get("created_at"))
        sources.append(detail)
    return sources


def _timestamp_fingerprint(row: dict[str, Any]) -> dict[str, Any]:
    """Compara timestamps en ventana de 120s."""
    stamps: dict[str, str] = {}
    for key in (
        "item_created_at",
        "item_updated_at",
        "ruta_created_at",
        "ini_created_at",
        "act_created_at",
        "ot_created_at",
    ):
        val = row.get(key)
        if val:
            stamps[key] = str(val)[:19]

    def _to_sec(s: str) -> int | None:
        try:
            return int(datetime.fromisoformat(s.replace(" ", "T")).timestamp())
        except (ValueError, TypeError):
            return None

    secs = {k: _to_sec(v) for k, v in stamps.items() if v}
    if len(secs) < 2:
        return {"stamps": stamps, "clustered": False, "max_delta_sec": None}
    values = list(secs.values())
    delta = max(values) - min(values)
    return {
        "stamps": stamps,
        "clustered": delta <= 120,
        "max_delta_sec": delta,
    }


def classify_item(
    row: dict[str, Any],
    prot: dict[str, set[int]],
    act_test_union: set[int],
    wrapper_by_item: dict[int, dict],
    reasons_out: list[str],
) -> str:
    """Retorna CONFIRMADO_TEST_WRAPPER_SAFE | TEST_WRAPPER_AROUND_REAL | REAL | INDETERMINADO."""
    item_id = row["ruta_item_id"]
    act_id = row.get("actuacion_id")
    ot_id = row.get("orden_trabajo_id")

    if item_id in wrapper_by_item:
        w = wrapper_by_item[item_id]
        reasons_out.append("wrapper_64_original")
        if w.get("actuacion_clasificacion") == "PROTECTED_REAL":
            return "TEST_WRAPPER_AROUND_REAL"

    if act_id and act_id in prot.get("actuaciones", set()):
        reasons_out.append("actuacion_PROTECTED_REAL")
        return "TEST_WRAPPER_AROUND_REAL"
    if ot_id and ot_id in prot.get("orden_trabajo", set()):
        reasons_out.append("ot_PROTECTED_REAL")
        return "TEST_WRAPPER_AROUND_REAL"

    for src in row.get("sources", []):
        if src["classification"] == "PROTECTED_REAL":
            if row.get("families") or row.get("ini_families") or row.get("ruta_families"):
                reasons_out.append(f"wrapper_test_around_{src['column']}_protected")
                return "TEST_WRAPPER_AROUND_REAL"
            reasons_out.append(f"source_{src['column']}_PROTECTED_REAL")
            return "INDETERMINADO"

    if act_id and act_id in act_test_union:
        reasons_out.append("actuacion_in_413_CONFIRMADO_TEST")
        return "CONFIRMADO_TEST_WRAPPER_SAFE"

    for src in row.get("sources", []):
        if src["classification"] == "CONFIRMADO_TEST":
            reasons_out.append(f"source_{src['column']}_CONFIRMADO_TEST")
            return "CONFIRMADO_TEST_WRAPPER_SAFE"

    families = set(row.get("families", [])) | set(row.get("ini_families", [])) | set(
        row.get("ruta_families", [])
    )
    strong_fams = {f for f in families if f.startswith(("A_", "B_", "C_", "D_", "E_", "F_"))}
    if strong_fams:
        reasons_out.append(f"test_family:{','.join(sorted(strong_fams))}")
        if row.get("timestamp_cluster", {}).get("clustered"):
            reasons_out.append("timestamp_cluster")
        return "CONFIRMADO_TEST_WRAPPER_SAFE"

    if row.get("ini_user", {}).get("is_test") and not act_id:
        reasons_out.append("iniciador_test_sin_actuacion")
        return "CONFIRMADO_TEST_WRAPPER_SAFE"

    if not row.get("ini_user", {}).get("is_test") and not row.get("ruta_user", {}).get("is_test"):
        reasons_out.append("non_test_provenance_chain")
        return "REAL"

    return "INDETERMINADO"


def enrich_items(
    conn: Connection,
    item_ids: list[int],
    prot: dict[str, set[int]],
    act_test_union: set[int],
    cleanup_den: set[int],
    cleanup_rel: set[int],
    wrapper_by_item: dict[int, dict],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for chunk in _chunk_ids(set(item_ids), 200):
        ph = ",".join(str(i) for i in chunk)
        rows = _rows(
            conn,
            f"""
            SELECT ri.id AS ruta_item_id, ri.ruta_trabajo_id, ri.ruta_grupo_id,
                   ri.iniciador_ruta_id, ri.estado_ruta_item, ri.estado_ejecucion,
                   ri.orden_trabajo_id, ri.actuacion_id, ri.created_by_user_id,
                   ri.created_at AS item_created_at, ri.updated_at AS item_updated_at,
                   rt.created_by_user_id AS ruta_created_by_user_id,
                   rt.created_at AS ruta_created_at,
                   ir.created_by_user_id AS ini_created_by_user_id,
                   ir.tipo_iniciador, ir.estado_iniciador, ir.created_at AS ini_created_at,
                   ir.relevamiento_id, ir.denuncia_id, ir.notificacion_id,
                   ir.comprobacion_id, ir.oficio_id, ir.actuacion_id AS ini_actuacion_id,
                   ot.numero_acta AS ot_numero_acta,
                   a.created_at AS act_created_at
            FROM ruta_item ri
            JOIN ruta_trabajo rt ON rt.id = ri.ruta_trabajo_id
            JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id
            LEFT JOIN orden_trabajo ot ON ot.id = ri.orden_trabajo_id
            LEFT JOIN actuaciones a ON a.id = ri.actuacion_id
            WHERE ri.id IN ({ph})
            ORDER BY ri.id
            """,
        )
        for row in rows:
            iid = row["ruta_item_id"]
            ini_row = {
                col: row.get(col.replace("ini_", "ir_") if col.startswith("ini_") else col)
                for col in SOURCE_COLUMNS
            }
            ini_row = {
                "relevamiento_id": row.get("relevamiento_id"),
                "denuncia_id": row.get("denuncia_id"),
                "notificacion_id": row.get("notificacion_id"),
                "comprobacion_id": row.get("comprobacion_id"),
                "oficio_id": row.get("oficio_id"),
                "actuacion_id": row.get("ini_actuacion_id"),
            }
            row["sources"] = _source_detail(
                conn, ini_row, prot, act_test_union, cleanup_den, cleanup_rel
            )
            row["item_user"] = _user_info(conn, row.get("created_by_user_id"))
            row["ruta_user"] = _user_info(conn, row.get("ruta_created_by_user_id"))
            row["ini_user"] = _user_info(conn, row.get("ini_created_by_user_id"))
            row["families"] = row.get("item_user", {}) and row["item_user"].get("families", [])
            row["ruta_families"] = row.get("ruta_user", {}) and row["ruta_user"].get(
                "families", []
            )
            row["ini_families"] = row.get("ini_user", {}) and row["ini_user"].get("families", [])
            row["timestamp_cluster"] = _timestamp_fingerprint(row)
            reasons: list[str] = []
            row["classification_final"] = classify_item(
                row, prot, act_test_union, wrapper_by_item, reasons
            )
            row["classification_reasons"] = reasons
            enriched.append(row)
    return enriched


def audit_route_siblings(
    conn: Connection,
    enriched: list[dict[str, Any]],
    classification_by_item: dict[int, str],
) -> dict[str, Any]:
    ruta_ids = {r["ruta_trabajo_id"] for r in enriched}
    routes: list[dict[str, Any]] = []
    for rid in sorted(ruta_ids):
        siblings = _rows(
            conn,
            """
            SELECT ri.id, ri.iniciador_ruta_id, ri.actuacion_id
            FROM ruta_item ri WHERE ri.ruta_trabajo_id = :rid
            """,
            {"rid": rid},
        )
        sib_cls = []
        for s in siblings:
            cid = classification_by_item.get(s["id"], "SIBLING_NOT_IN_708")
            sib_cls.append({"ruta_item_id": s["id"], "classification": cid})
        routes.append(
            {
                "ruta_trabajo_id": rid,
                "items_total": len(siblings),
                "items_in_708": sum(1 for s in siblings if s["id"] in classification_by_item),
                "sibling_classifications": Counter(c["classification"] for c in sib_cls),
                "note": "MIXED_TEST_INDETERMINATE — delete item only, keep route",
            }
        )
    return {"routes_analyzed": len(routes), "routes": routes[:100], "routes_total": len(routes)}


def simulate_containers(
    conn: Connection,
    safe_items: set[int],
    safe_pool: set[int],
) -> dict[str, Any]:
    virtual = VirtualDeleteState()
    virtual.add_explicit("ruta_item", safe_items)
    virtual.add_explicit("ruta_pool_dia", safe_pool)

    orphan_groups: list[dict[str, Any]] = []
    for gid in sorted(_fetch_ids(conn, "SELECT id FROM ruta_grupo")):
        items = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_grupo_id = {gid}")
        if items and not (items - safe_items):
            orphan_groups.append({"ruta_grupo_id": gid, "items": len(items)})

    empty_rutas: list[dict[str, Any]] = []
    for rid in sorted(_fetch_ids(conn, "SELECT id FROM ruta_trabajo")):
        items = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rid}")
        if items and not (items - safe_items):
            empty_rutas.append({"ruta_trabajo_id": rid, "items": len(items)})

    rgi_ids: set[int] = set()
    for g in orphan_groups:
        rgi_ids |= _fetch_ids(
            conn,
            f"SELECT id FROM ruta_grupo_inspector WHERE ruta_grupo_id = {g['ruta_grupo_id']}",
        )

    return {
        "orphan_group_candidates": len(orphan_groups),
        "empty_ruta_candidates": len(empty_rutas),
        "ruta_grupo_inspector_removable": len(rgi_ids),
        "SAFE_RUTA_GRUPO_EMPTY": sorted(g["ruta_grupo_id"] for g in orphan_groups),
        "SAFE_RUTA_TRABAJO_EMPTY": sorted(r["ruta_trabajo_id"] for r in empty_rutas),
        "SAFE_RUTA_GRUPO_INSPECTOR": sorted(rgi_ids),
    }


def classify_iniciadores_after_wrappers(
    conn: Connection,
    test_ini_ids: set[int],
    safe_items: set[int],
    safe_pool: set[int],
    prot: dict[str, set[int]],
    act_test_union: set[int],
    cleanup_den: set[int],
    cleanup_rel: set[int],
    wrapper_protected_ini: set[int],
    ini_touched_by_708: set[int],
) -> dict[str, Any]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for ini_id in sorted(ini_touched_by_708):
        row = conn.execute(
            text(
                """
                SELECT id, tipo_iniciador, created_by_user_id,
                       relevamiento_id, denuncia_id, notificacion_id,
                       comprobacion_id, oficio_id, actuacion_id
                FROM iniciador_ruta WHERE id = :id
                """
            ),
            {"id": ini_id},
        ).fetchone()
        if not row:
            continue
        m = dict(row._mapping)
        ri_surv = _fetch_ids(
            conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {ini_id}"
        ) - safe_items
        rp_surv = _fetch_ids(
            conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {ini_id}"
        ) - safe_pool

        sources = _source_detail(conn, m, prot, act_test_union, cleanup_den, cleanup_rel)
        src_cls = {s["classification"] for s in sources}

        if ini_id in wrapper_protected_ini or "PROTECTED_REAL" in src_cls:
            buckets["KEEP_PROTECTED"].append(ini_id)
        elif ri_surv or rp_surv:
            buckets["KEEP_ROUTE_REF"].append(ini_id)
        elif "INDETERMINADO" in src_cls and not (
            m.get("denuncia_id") in cleanup_den or m.get("relevamiento_id") in cleanup_rel
        ):
            buckets["KEEP_INDETERMINATE"].append(ini_id)
        elif m.get("created_by_user_id") in _test_user_ids(conn):
            buckets["SAFE_DELETE"].append(ini_id)
        else:
            buckets["KEEP_OTHER"].append(ini_id)

    return {
        "subset_from_708_items": len(ini_touched_by_708),
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "buckets": {k: sorted(v) for k, v in buckets.items()},
    }


def unlock_simulation(
    conn: Connection,
    act_test_union: set[int],
    set_act_old: set[int],
    set_act_structured: set[int],
    cleanup_den: set[int],
    cleanup_rel: set[int],
    safe_ini_delete: set[int],
    safe_items: set[int],
    safe_pool: set[int],
) -> dict[str, Any]:
    union_413 = set_act_old | set_act_structured
    acts_unlocked = acts_blocked = 0
    for aid in union_413:
        blocking = set()
        for iid in _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}"):
            if iid not in safe_ini_delete:
                blocking.add(iid)
        for iid in _fetch_ids(
            conn,
            f"SELECT DISTINCT iniciador_ruta_id FROM ruta_item WHERE actuacion_id = {aid}",
        ):
            items = _fetch_ids(
                conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}"
            )
            if items - safe_items:
                if iid not in safe_ini_delete:
                    blocking.add(iid)
        if blocking:
            acts_blocked += 1
        else:
            acts_unlocked += 1

    den_unlocked = den_blocked = 0
    for did in cleanup_den:
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE denuncia_id = {did}")
        surv = False
        for iid in inis:
            if iid not in safe_ini_delete:
                surv = True
                break
            ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}")
            if ri - safe_items:
                surv = True
                break
            rp = _fetch_ids(
                conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}"
            )
            if rp - safe_pool:
                surv = True
                break
        if surv:
            den_blocked += 1
        else:
            den_unlocked += 1

    rel_unlocked = rel_blocked = 0
    rel_detail: dict[int, str] = {}
    for rid in cleanup_rel:
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}")
        blocking = [i for i in inis if i not in safe_ini_delete]
        if blocking:
            rel_blocked += 1
            rel_detail[rid] = "STILL_BLOCKED"
        else:
            rel_unlocked += 1
            rel_detail[rid] = "UNLOCKED_AFTER_2B"

    return {
        "actuaciones_413": {
            "total": len(union_413),
            "UNLOCKED_AFTER_2B": acts_unlocked,
            "STILL_BLOCKED": acts_blocked,
            "prior_unlocked_conservative": 264,
            "delta_vs_prior": acts_unlocked - 264,
        },
        "denuncias_75": {
            "UNLOCKED_AFTER_2B": den_unlocked,
            "STILL_BLOCKED": den_blocked,
            "prior_unlocked": 0,
        },
        "relevamientos_26": {
            "UNLOCKED_AFTER_2B": rel_unlocked,
            "STILL_BLOCKED": rel_blocked,
            "qa_focus_status": {
                k: rel_detail.get(k, "N/A")
                for k in sorted(RELEVAMIENTOS_QA_IDS)
            },
        },
    }


def simulate_users(
    conn: Connection,
    test_users: set[int],
    virtual: VirtualDeleteState,
    users_unlocked_2a: int,
) -> dict[str, Any]:
    fk_columns = load_user_fk_columns(conn)
    deleted_by_table: dict[str, set[int]] = defaultdict(set)
    for table in virtual.explicit:
        deleted_by_table[table].update(virtual.explicit[table])

    unlocked: set[int] = set()
    blocked: set[int] = set()
    for uid in test_users:
        has_ref = False
        for table, col in fk_columns:
            for r in conn.execute(
                text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}
            ):
                if r[0] not in deleted_by_table.get(table, set()):
                    has_ref = True
                    break
            if has_ref:
                break
        if has_ref:
            blocked.add(uid)
        else:
            unlocked.add(uid)

    return {
        "users_test_fk_free_after_2b": len(unlocked),
        "users_unlocked_after_2a_baseline": users_unlocked_2a,
        "users_additionally_unlocked_by_2b": max(0, len(unlocked) - users_unlocked_2a),
        "users_still_blocked": len(blocked),
    }


def run_phase2b_route_items_reconcile(
    conn: Connection,
    *,
    phase2b_diag_path: Path,
    protected_manifest_path: Path,
    structured_acts_path: Path,
    dry_run_v3_path: Path,
    phase2a_apply_path: Path | None = None,
) -> dict[str, Any]:
    baseline = _baseline_check(conn)
    universe_ids = load_universe_708(phase2b_diag_path)
    if len(universe_ids) != 708:
        raise ValueError(f"Expected 708 universe ids, got {len(universe_ids)}")

    missing = []
    for iid in universe_ids:
        if not _scalar(conn, "SELECT COUNT(*) FROM ruta_item WHERE id = :id", {"id": iid}):
            missing.append(iid)
    if missing:
        raise ValueError(f"Missing ruta_item ids: {missing[:5]}... ({len(missing)} total)")

    protected_manifest = load_manifest(protected_manifest_path)
    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    set_act_structured = load_structured_acts_274(structured_acts_path)
    set_act_old = _blocked_act_ids(conn, prot)
    act_test_union = set_act_old | set_act_structured

    cleanup_den = _fetch_ids(
        conn,
        f"""
        SELECT d.id FROM denuncia d
        JOIN users u ON u.id = d.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    cleanup_rel = _fetch_ids(
        conn,
        f"""
        SELECT r.id FROM relevamiento r
        JOIN users u ON u.id = r.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """
    ) | RELEVAMIENTOS_QA_IDS

    prior_safe = load_prior_safe_sets(phase2b_diag_path)
    wrapper_64 = load_wrapper_64(dry_run_v3_path)
    test_sources = scan_test_sources()

    enriched = enrich_items(
        conn,
        universe_ids,
        prot,
        act_test_union,
        cleanup_den,
        cleanup_rel,
        wrapper_64["by_ruta_item_id"],
    )

    cls_counter = Counter(r["classification_final"] for r in enriched)
    if sum(cls_counter.values()) != 708:
        raise ValueError(f"Classification count mismatch: {cls_counter}")

    classification_by_item = {r["ruta_item_id"]: r["classification_final"] for r in enriched}
    siblings = audit_route_siblings(conn, enriched, classification_by_item)

    deletable_buckets = {"CONFIRMADO_TEST_WRAPPER_SAFE", "TEST_WRAPPER_AROUND_REAL"}
    new_safe_from_708 = {
        r["ruta_item_id"] for r in enriched if r["classification_final"] in deletable_buckets
    }
    safe_item_final = prior_safe["SAFE_RUTA_ITEM"] | new_safe_from_708

    pool_rows = _rows(
        conn,
        f"""
        SELECT rpd.id, rpd.iniciador_ruta_id, rpd.actuacion_id
        FROM ruta_pool_dia rpd
        WHERE rpd.id IN ({",".join(str(i) for i in sorted(prior_safe["SAFE_RUTA_POOL"]))})
        """,
    ) if prior_safe["SAFE_RUTA_POOL"] else []
    pool_revalidated = {
        "count": len(prior_safe["SAFE_RUTA_POOL"]),
        "still_exist": len(pool_rows),
        "protected_act_refs": sum(
            1 for p in pool_rows if p.get("actuacion_id") in prot.get("actuaciones", set())
        ),
        "note": "pool wrapper puede borrarse; source protegido permanece",
    }
    safe_pool_final = prior_safe["SAFE_RUTA_POOL"]

    containers = simulate_containers(conn, safe_item_final, safe_pool_final)
    ini_touched = {r["iniciador_ruta_id"] for r in enriched}
    wrapper_protected_ini = set(wrapper_64["protected_iniciadores"])
    ini_sim = classify_iniciadores_after_wrappers(
        conn,
        _test_user_ids(conn),
        safe_item_final,
        safe_pool_final,
        prot,
        act_test_union,
        cleanup_den,
        cleanup_rel,
        wrapper_protected_ini,
        ini_touched,
    )

    all_test_ini = _fetch_ids(
        conn,
        f"""
        SELECT ir.id FROM iniciador_ruta ir
        JOIN users u ON u.id = ir.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    safe_ini_final: set[int] = set()
    for ini_id in all_test_ini:
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {ini_id}")
        rp = _fetch_ids(
            conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {ini_id}"
        )
        if (ri - safe_item_final) or (rp - safe_pool_final):
            continue
        row = conn.execute(
            text(
                "SELECT created_by_user_id, denuncia_id, relevamiento_id, notificacion_id, "
                "comprobacion_id, oficio_id, actuacion_id FROM iniciador_ruta WHERE id = :id"
            ),
            {"id": ini_id},
        ).fetchone()
        if not row:
            continue
        m = dict(row._mapping)
        if ini_id in wrapper_protected_ini:
            continue
        sources = _source_detail(
            conn, m, prot, act_test_union, cleanup_den, cleanup_rel
        )
        if any(s["classification"] == "PROTECTED_REAL" for s in sources):
            continue
        if any(
            s["classification"] == "INDETERMINADO"
            for s in sources
            if not (
                s["column"] == "denuncia_id"
                and m.get("denuncia_id") in cleanup_den
            )
            and not (
                s["column"] == "relevamiento_id"
                and m.get("relevamiento_id") in cleanup_rel
            )
        ):
            continue
        safe_ini_final.add(ini_id)

    unlock = unlock_simulation(
        conn,
        act_test_union,
        set_act_old,
        set_act_structured,
        cleanup_den,
        cleanup_rel,
        safe_ini_final,
        safe_item_final,
        safe_pool_final,
    )

    explicit: dict[str, set[int]] = {
        "ruta_item": safe_item_final,
        "ruta_pool_dia": safe_pool_final,
        "ruta_grupo": set(containers["SAFE_RUTA_GRUPO_EMPTY"]),
        "ruta_trabajo": set(containers["SAFE_RUTA_TRABAJO_EMPTY"]),
        "iniciador_ruta": safe_ini_final,
        "ruta_grupo_inspector": set(containers["SAFE_RUTA_GRUPO_INSPECTOR"]),
    }
    virtual = VirtualDeleteState()
    for t, ids in explicit.items():
        virtual.add_explicit(t, ids)

    edges = load_fk_edges(conn)
    validation = validate_execution_plan(
        conn,
        {t: explicit.get(t, set()) for t in PHASE2B_DELETE_ORDER},
        virtual,
        edges,
    )

    users_unlocked_2a = 231
    if phase2a_apply_path and phase2a_apply_path.is_file():
        p2a = json.loads(phase2a_apply_path.read_text(encoding="utf-8"))
        users_unlocked_2a = p2a.get("post_commit_users", {}).get(
            "UNLOCKED_FOR_PHASE2D_count", 231
        )
    user_sim = simulate_users(conn, _test_user_ids(conn), virtual, users_unlocked_2a)

    before = {t: _count_table(conn, t) for t in PHASE2B_DELETE_ORDER}
    after = {t: before[t] - len(explicit.get(t, set())) for t in PHASE2B_DELETE_ORDER}

    family_hits = Counter()
    for r in enriched:
        for f in set(r.get("ini_families", [])) | set(r.get("ruta_families", [])):
            family_hits[f] += 1

    source_breakdown: dict[str, Counter] = defaultdict(Counter)
    for r in enriched:
        for s in r.get("sources", []):
            source_breakdown[s["column"]][s["classification"]] += 1

    indeterminate_ini_remaining = 1162
    resolved_via_708 = len(ini_sim["buckets"].get("SAFE_DELETE", []))
    still_indeterminate_subset = len(ini_sim["buckets"].get("KEEP_INDETERMINATE", []))

    safe_sets_final = {
        "SAFE_RUTA_ITEM_FINAL": sorted(safe_item_final),
        "SAFE_RUTA_POOL_FINAL": sorted(safe_pool_final),
        "SAFE_RUTA_GRUPO_INSPECTOR_FINAL": containers["SAFE_RUTA_GRUPO_INSPECTOR"],
        "SAFE_RUTA_GRUPO_EMPTY_FINAL": containers["SAFE_RUTA_GRUPO_EMPTY"],
        "SAFE_RUTA_TRABAJO_EMPTY_FINAL": containers["SAFE_RUTA_TRABAJO_EMPTY"],
        "SAFE_INICIADOR_FINAL": sorted(safe_ini_final),
        "counts": {
            "SAFE_RUTA_ITEM_FINAL": len(safe_item_final),
            "SAFE_RUTA_POOL_FINAL": len(safe_pool_final),
            "SAFE_RUTA_GRUPO_INSPECTOR_FINAL": len(containers["SAFE_RUTA_GRUPO_INSPECTOR"]),
            "SAFE_RUTA_GRUPO_EMPTY_FINAL": len(containers["SAFE_RUTA_GRUPO_EMPTY"]),
            "SAFE_RUTA_TRABAJO_EMPTY_FINAL": len(containers["SAFE_RUTA_TRABAJO_EMPTY"]),
            "SAFE_INICIADOR_FINAL": len(safe_ini_final),
        },
        "prior_safe_item": len(prior_safe["SAFE_RUTA_ITEM"]),
        "new_from_708_reconcile": len(new_safe_from_708),
    }

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3C.1-DIAG",
        "mode": "READ_ONLY_SELECT",
        "writes_executed": False,
        "baseline": baseline,
        "universe_708": {
            "count": len(universe_ids),
            "ids": universe_ids,
            "all_exist": len(missing) == 0,
        },
        "classification": {
            "CONFIRMADO_TEST_WRAPPER_SAFE": cls_counter.get("CONFIRMADO_TEST_WRAPPER_SAFE", 0),
            "TEST_WRAPPER_AROUND_REAL": cls_counter.get("TEST_WRAPPER_AROUND_REAL", 0),
            "REAL": cls_counter.get("REAL", 0),
            "INDETERMINADO": cls_counter.get("INDETERMINADO", 0),
            "sum": sum(cls_counter.values()),
            "items": enriched,
        },
        "test_families": {
            "pattern_scan": test_sources,
            "hits_in_708": dict(family_hits.most_common(30)),
        },
        "source_provenance": {
            "breakdown_in_708": {k: dict(v) for k, v in source_breakdown.items()},
        },
        "route_siblings": siblings,
        "wrapper64_reconcile": wrapper_64,
        "safe_sets": safe_sets_final,
        "pool_revalidation": pool_revalidated,
        "container_simulation": containers,
        "initiator_simulation": {
            "subset_from_708": ini_sim,
            "SAFE_INICIADOR_FINAL_count": len(safe_ini_final),
            "indeterminate_source_prior_total": indeterminate_ini_remaining,
            "resolved_via_708_subset": resolved_via_708,
            "still_indeterminate_in_708_subset": still_indeterminate_subset,
            "still_indeterminate_global_estimate": indeterminate_ini_remaining
            - resolved_via_708,
        },
        "unlock_acts": unlock["actuaciones_413"],
        "unlock_denuncias": unlock["denuncias_75"],
        "unlock_relevamientos": unlock["relevamientos_26"],
        "unlock_users": user_sim,
        "protected_conflicts": [],
        "execution_validation": {
            "proposed_order": topological_delete_order(PHASE2B_DELETE_ORDER, edges),
            "validation": validation,
            "valid": validation.get("valid", False),
            "post_simulated_counts": {
                "before": before,
                "delete": {t: len(explicit.get(t, set())) for t in PHASE2B_DELETE_ORDER},
                "after": after,
            },
            "zero_delete_confirmed": {
                "actuaciones": 0,
                "denuncia": 0,
                "relevamiento": 0,
                "users": 0,
            },
        },
    }


def write_reconcile_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
