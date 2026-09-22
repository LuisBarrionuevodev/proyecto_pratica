"""
PREDEPLOY-CLEANUP.3F-DIAG — FASE 2C.2 grafo residual post-2C.1.
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
    JUZGADO_TEST_PATTERN,
    RELEVAMIENTOS_QA_IDS,
    RUBRO_TEST_PATTERN,
    SQL_TEST_USER_WHERE,
    TEST_ACTUACIONES_SQL,
)
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import entity_ids, file_sha256, load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import (
    TEST_STREET_NAMES,
    _blocked_act_ids,
    _scalar,
    _test_user_ids,
)
from app.domains.predeploy_cleanup.phase2b_route_items_reconcile import FAMILY_PATTERNS
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
)

BASELINE_POST_2C1 = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8194,
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

SOURCE_COLUMNS_INI = (
    "relevamiento_id",
    "denuncia_id",
    "notificacion_id",
    "comprobacion_id",
    "oficio_id",
    "actuacion_id",
)

UUID_CALLE_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.I)
OT_TEST_RE = re.compile(r"^[0-9A-F]{5}[A-F]$", re.I)


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
    counts = {t: _count(conn, t) for t in BASELINE_POST_2C1}
    drift = [f"{t}: {counts[t]} != {e}" for t, e in BASELINE_POST_2C1.items() if counts[t] != e]
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": not drift,
        "drift": drift,
    }


def _reconcile_comprobacion_protected(
    conn: Connection,
    protected_path: Path,
    report_2c1_found: int = 56,
) -> dict[str, Any]:
    """Sección 1: reconciliar comprobacion protected 48 vs 56."""
    manifest = load_manifest(protected_path)
    raw_prot = load_protected_sets(manifest)
    raw_comp = raw_prot.get("comprobacion", set())
    expanded = expand_protected_indirect(conn, raw_prot)
    expanded_comp = expanded.get("comprobacion", set())

    added = sorted(expanded_comp - raw_comp)
    missing_from_expanded = sorted(raw_comp - expanded_comp)

    added_detail: list[dict[str, Any]] = []
    for cid in added:
        row = conn.execute(
            text(
                """
                SELECT c.id, c.numero_acta,
                       (SELECT COUNT(*) FROM actuaciones a WHERE a.comprobacion_id = c.id) AS act_refs,
                       (SELECT COUNT(*) FROM iniciador_ruta ir WHERE ir.comprobacion_id = c.id) AS ini_refs
                FROM comprobacion c WHERE c.id = :id
                """
            ),
            {"id": cid},
        ).fetchone()
        oficios = _rows(
            conn,
            """
            SELECT o.id AS oficio_id, o.numero_oficio, e.id AS expediente_id
            FROM oficio o
            LEFT JOIN expediente e ON e.oficio_id = o.id
            WHERE o.comprobacion_id = :cid
            """,
            {"cid": cid},
        )
        acts = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE comprobacion_id = {cid}")
        ots = _rows(
            conn,
            f"""
            SELECT DISTINCT ot.id, ot.numero_acta
            FROM actuaciones a JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
            WHERE a.comprobacion_id = {cid}
            """,
        )
        added_detail.append(
            {
                "comprobacion_id": cid,
                "numero_acta": row[1] if row else None,
                "actuaciones_refs": sorted(acts),
                "iniciador_refs": int(row[3]) if row else 0,
                "oficios": oficios,
                "orden_trabajo": ots,
                "reason": "expanded_via_protected_oficio_chain",
                "in_raw_manifest": cid in raw_comp,
            }
        )

    verdict = "B_expansion_legitima_protected_closure"
    if report_2c1_found != len(expanded_comp):
        verdict = "C_posible_bug_reporte_o_drift"
    if missing_from_expanded:
        verdict = "D_inconsistencia_real"

    return {
        "manifest_explicit_count": len(raw_comp),
        "manifest_closure_count": len(expanded_comp),
        "report_2c1_found": report_2c1_found,
        "added_by_closure": added,
        "added_count": len(added),
        "missing_from_closure": missing_from_expanded,
        "added_detail": added_detail,
        "verdict": verdict,
        "explanation": (
            "48 IDs explícitos en manifest xlsx; "
            f"{len(added)} comprobaciones adicionales vía cadena oficio→comprobacion protegida; "
            f"total expandido={len(expanded_comp)}"
        ),
    }


def _load_preserved_docs(phase2c1_manifest_path: Path) -> dict[str, set[int]]:
    manifest = load_manifest(phase2c1_manifest_path)
    refs = manifest.get("preserve_document_refs", {})
    return {
        "notificacion": {int(x) for x in refs.get("notificacion", [])},
        "comprobacion": {int(x) for x in refs.get("comprobacion", [])},
    }


def _load_excluded_sets(phase2c1_manifest_path: Path) -> dict[str, set[int]]:
    manifest = load_manifest(phase2c1_manifest_path)
    excl = manifest.get("excluded", {})
    return {
        "blocked_acts_148": {int(x) for x in excl.get("blocked_acts_148", [])},
        "relevamientos_26": {int(x) for x in excl.get("relevamientos_26", [])},
    }


def _classify_suite(username: str | None, email: str | None, calle: str | None) -> list[str]:
    suites: list[str] = []
    blob = " ".join(filter(None, [username or "", email or "", calle or ""]))
    if UUID_CALLE_RE.search(calle or ""):
        suites.append("hex_uuid_calle")
    for name, pat in FAMILY_PATTERNS.items():
        if pat.search(blob):
            suites.append(name)
    if OT_TEST_RE.search(blob):
        suites.append("ot_test_pattern")
    return suites or ["unknown"]


def _act_row(conn: Connection, act_id: int) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT a.id, a.orden_trabajo_id, ot.numero_acta AS ot_numero,
                   a.notificacion_id, a.comprobacion_id, a.domicilio_id,
                   a.establecimiento_operativo_id,
                   d.calle
            FROM actuaciones a
            LEFT JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
            LEFT JOIN domicilio d ON d.id = a.domicilio_id
            WHERE a.id = :id
            """
        ),
        {"id": act_id},
    ).fetchone()
    if not row:
        return {"actuacion_id": act_id, "missing": True}
    return dict(row._mapping)


def _classify_act_blockers(
    conn: Connection,
    act_id: int,
    prot: dict[str, set[int]],
) -> list[str]:
    blockers: list[str] = []
    ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {act_id}")
    ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {act_id}")
    rp = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {act_id}")

    if ini:
        test_ini = _fetch_ids(
            conn,
            f"""
            SELECT ir.id FROM iniciador_ruta ir
            JOIN users u ON u.id = ir.created_by_user_id
            WHERE ir.id IN ({','.join(str(i) for i in ini)}) AND ({SQL_TEST_USER_WHERE})
            """,
        )
        if test_ini:
            blockers.append("INICIADOR_TEST_RESIDUAL")
        else:
            blockers.append("INICIADOR_SOURCE_INDETERMINADO")
    if ri:
        blockers.append("RUTA_ITEM_RESIDUAL")
    if rp:
        blockers.append("RUTA_POOL_RESIDUAL")

    row = _act_row(conn, act_id)
    if row.get("notificacion_id"):
        nid = row["notificacion_id"]
        if nid in prot.get("notificacion", set()):
            blockers.append("DOCUMENT_SOURCE_SHARED")
        refs = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE notificacion_id = {nid}")
        if refs:
            blockers.append("INICIADOR_TEST_RESIDUAL")
    if row.get("comprobacion_id"):
        cid = row["comprobacion_id"]
        if cid in prot.get("comprobacion", set()):
            blockers.append("DOCUMENT_SOURCE_SHARED")
        refs = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE comprobacion_id = {cid}")
        if refs:
            blockers.append("INICIADOR_SOURCE_INDETERMINADO")

    ot_id = row.get("orden_trabajo_id")
    if ot_id:
        acts_on_ot = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        if len(acts_on_ot) > 1:
            blockers.append("OT_SHARED")
        if ot_id in prot.get("orden_trabajo", set()):
            blockers.append("OT/ACT PROTECTED CONFLICT")
    if act_id in prot.get("actuaciones", set()):
        blockers.append("OT/ACT PROTECTED CONFLICT")

    return sorted(set(blockers)) or ["OTRO"]


def _analyze_acts_148(
    conn: Connection,
    act_ids: set[int],
    prot: dict[str, set[int]],
    structured_acts_path: Path,
    structured_diag_path: Path | None,
) -> dict[str, Any]:
    set_act_old = _blocked_act_ids(conn, prot)
    set_act_structured = load_structured_acts_274(structured_acts_path)

    structured_by_act: dict[int, dict[str, Any]] = {}
    if structured_diag_path and structured_diag_path.is_file():
        data = json.loads(structured_diag_path.read_text(encoding="utf-8"))
        for item in data.get("acts", []):
            structured_by_act[item["actuacion_id"]] = item

    old_ids = sorted(act_ids & set_act_old)
    struct_ids = sorted(act_ids & set_act_structured - set_act_old)
    both_ids = sorted(act_ids & set_act_old & set_act_structured)

    per_act: list[dict[str, Any]] = []
    blocker_counts: Counter[str] = Counter()

    for aid in sorted(act_ids):
        family = "SET_ACT_OLD" if aid in set_act_old else "SET_ACT_STRUCTURED"
        if aid in set_act_old and aid in set_act_structured:
            family = "BOTH"

        row = _act_row(conn, aid)
        ini = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}"))
        ri = sorted(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}"))
        rp = sorted(_fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}"))

        of_exp: list[dict[str, Any]] = []
        if row.get("comprobacion_id"):
            of_exp = _rows(
                conn,
                """
                SELECT o.id AS oficio_id, e.id AS expediente_id
                FROM oficio o LEFT JOIN expediente e ON e.oficio_id = o.id
                WHERE o.comprobacion_id = :cid
                """,
                {"cid": row["comprobacion_id"]},
            )

        blockers = _classify_act_blockers(conn, aid, prot)
        for b in blockers:
            blocker_counts[b] += 1

        suites = _classify_suite(None, None, row.get("calle"))
        if family == "SET_ACT_STRUCTURED" and aid in structured_by_act:
            suites = structured_by_act[aid].get("reasons", suites)

        per_act.append(
            {
                "actuacion_id": aid,
                "orden_trabajo_id": row.get("orden_trabajo_id"),
                "ot_numero": row.get("ot_numero"),
                "familia_test": family,
                "suites": suites,
                "iniciador_ruta_refs": ini,
                "ruta_item_refs": ri,
                "ruta_pool_refs": rp,
                "notificacion_id": row.get("notificacion_id"),
                "comprobacion_id": row.get("comprobacion_id"),
                "oficio_expediente": of_exp,
                "establecimiento_operativo_id": row.get("establecimiento_operativo_id"),
                "domicilio_id": row.get("domicilio_id"),
                "blockers": blockers,
            }
        )

    return {
        "expected_count": 148,
        "present_count": _count_ids_exist(conn, "actuaciones", act_ids),
        "family_split": {
            "SET_ACT_OLD": len(old_ids),
            "SET_ACT_STRUCTURED": len(struct_ids),
            "BOTH": len(both_ids),
            "OLD_ids_sample": old_ids[:10],
            "STRUCTURED_ids": struct_ids,
        },
        "blocker_summary": dict(blocker_counts),
        "items": per_act,
    }


def _analyze_initiators_for_acts(
    conn: Connection,
    act_ids: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    ini_ids: set[int] = set()
    for aid in act_ids:
        ini_ids |= _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        for iid in _fetch_ids(
            conn, f"SELECT DISTINCT iniciador_ruta_id FROM ruta_item WHERE actuacion_id = {aid}"
        ):
            ini_ids.add(iid)
        for iid in _fetch_ids(
            conn, f"SELECT DISTINCT iniciador_ruta_id FROM ruta_pool_dia WHERE actuacion_id = {aid}"
        ):
            ini_ids.add(iid)

    test_users = _test_user_ids(conn)
    items: list[dict[str, Any]] = []
    buckets: Counter[str] = Counter()

    for iid in sorted(ini_ids):
        row = conn.execute(
            text("SELECT * FROM iniciador_ruta WHERE id = :id"), {"id": iid}
        ).fetchone()
        if not row:
            continue
        r = dict(row._mapping)
        source = {col: r.get(col) for col in SOURCE_COLUMNS_INI if r.get(col)}
        ri = sorted(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}"))
        rp = sorted(_fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}"))

        if iid in prot.get("iniciador_ruta", set()) or any(
            source.get(c) in prot.get(c.replace("_id", ""), set())
            for c in ("notificacion_id", "comprobacion_id", "oficio_id")
            if source.get(c)
        ):
            bucket = "PROTECTED"
        elif r.get("created_by_user_id") in test_users:
            bucket = "SAFE_TEST_WRAPPER"
        elif source.get("notificacion_id") or source.get("comprobacion_id"):
            bucket = "KEEP_SOURCE_INDETERMINATE"
        elif source.get("relevamiento_id") or source.get("denuncia_id"):
            bucket = "KEEP_SOURCE_REAL"
        else:
            bucket = "INDETERMINATE"

        buckets[bucket] += 1
        items.append(
            {
                "iniciador_id": iid,
                "tipo": r.get("tipo_iniciador"),
                "created_by_user_id": r.get("created_by_user_id"),
                "source_fk": source,
                "ruta_item_refs": ri,
                "ruta_pool_refs": rp,
                "classification": bucket,
            }
        )

    safe_ini = {i["iniciador_id"] for i in items if i["classification"] == "SAFE_TEST_WRAPPER"}
    safe_ri: set[int] = set()
    safe_rp: set[int] = set()
    for i in items:
        if i["iniciador_id"] in safe_ini:
            safe_ri.update(i["ruta_item_refs"])
            safe_rp.update(i["ruta_pool_refs"])

    empty_groups: set[int] = set()
    empty_routes: set[int] = set()
    for ri_id in safe_ri:
        row = conn.execute(
            text("SELECT ruta_grupo_id, ruta_trabajo_id FROM ruta_item WHERE id = :id"),
            {"id": ri_id},
        ).fetchone()
        if row:
            gid, rtid = row[0], row[1]
            others = _fetch_ids(
                conn,
                f"SELECT id FROM ruta_item WHERE ruta_grupo_id = {gid} AND id != {ri_id}",
            )
            if not others:
                empty_groups.add(gid)
            others_rt = _fetch_ids(
                conn,
                f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rtid} AND id != {ri_id}",
            )
            if not others_rt:
                empty_routes.add(rtid)

    return {
        "unique_iniciadores": len(ini_ids),
        "classification_buckets": dict(buckets),
        "items": items,
        "proposed_safe_sets": {
            "SAFE_INITIATORS_RESIDUAL": sorted(safe_ini),
            "SAFE_RUTA_ITEM_2C2": sorted(safe_ri),
            "SAFE_RUTA_POOL_2C2": sorted(safe_rp),
            "SAFE_GROUP_EMPTY_2C2": sorted(empty_groups),
            "SAFE_ROUTE_EMPTY_2C2": sorted(empty_routes),
        },
    }


def _analyze_relevamientos_26(
    conn: Connection,
    rel_ids: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    buckets: Counter[str] = Counter()

    for rid in sorted(rel_ids):
        row = conn.execute(
            text(
                """
                SELECT r.id, r.domicilio_id, r.created_by_user_id, u.username
                FROM relevamiento r
                LEFT JOIN users u ON u.id = r.created_by_user_id
                WHERE r.id = :id
                """
            ),
            {"id": rid},
        ).fetchone()
        if not row:
            items.append({"relevamiento_id": rid, "missing": True})
            continue
        r = dict(row._mapping)
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
        ri: list[int] = []
        rp: list[int] = []
        for iid in ini:
            ri.extend(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}"))
            rp.extend(_fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}"))
        ri = sorted(set(ri))
        rp = sorted(set(rp))

        if rid in prot.get("relevamiento", set()):
            bucket = "PROTECTED_CONFLICT"
        elif ini or ri or rp:
            if ini:
                bucket = "BLOCKED_INICIADOR"
            else:
                bucket = "BLOCKED_ROUTE"
        else:
            bucket = "DELETE_AFTER_TEST_WRAPPERS"

        buckets[bucket] += 1
        items.append(
            {
                "relevamiento_id": rid,
                "relevadores": relevadores,
                "domicilio_id": r.get("domicilio_id"),
                "created_by_user_id": r.get("created_by_user_id"),
                "username": r.get("username"),
                "iniciador_refs": ini,
                "ruta_item_refs": ri,
                "ruta_pool_refs": rp,
                "classification": bucket,
                "is_qa_focus": rid in RELEVAMIENTOS_QA_IDS,
            }
        )

    otro_relevador = _rows(
        conn,
        "SELECT id, nombre FROM relevador WHERE nombre LIKE '%Otro Relevador QA%'",
    )
    qa_refs_after_sim = {}
    if otro_relevador:
        rel_id = otro_relevador[0]["id"]
        qa_refs_after_sim = {
            "relevador_id": rel_id,
            "relevamiento_refs_if_26_deleted": _rows(
                conn,
                f"""
                SELECT rr.relevamiento_id FROM relevamiento_relevador rr
                WHERE rr.relevador_id = {rel_id}
                  AND rr.relevamiento_id NOT IN ({','.join(str(i) for i in sorted(rel_ids)) or '0'})
                """,
            ),
            "future_catalog_delete_candidate": True,
        }

    return {
        "expected_count": 26,
        "present_count": _count_ids_exist(conn, "relevamiento", rel_ids),
        "qa_focus": {rid: rid in rel_ids for rid in RELEVAMIENTOS_QA_IDS},
        "classification_buckets": dict(buckets),
        "items": items,
        "otro_relevador_qa": qa_refs_after_sim,
        "proposed_SAFE_RELEVAMIENTOS_RESIDUAL": sorted(
            i["relevamiento_id"] for i in items if i.get("classification") == "DELETE_AFTER_TEST_WRAPPERS"
        ),
    }


def _fk_refs_to_table(conn: Connection, table: str, pk_id: int) -> dict[str, int]:
    refs: dict[str, int] = {}
    children = _rows(
        conn,
        """
        SELECT TABLE_NAME, COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND REFERENCED_TABLE_NAME = :tbl
        """,
        {"tbl": table},
    )
    for ch in children:
        tbl, col = ch["TABLE_NAME"], ch["COLUMN_NAME"]
        n = int(
            _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :id", {"id": pk_id}) or 0
        )
        if n:
            refs[f"{tbl}.{col}"] = n
    return refs


def _analyze_preserved_notifications(
    conn: Connection,
    notif_ids: set[int],
    prot: dict[str, set[int]],
    test_ini_notif: set[int],
) -> dict[str, Any]:
    buckets: Counter[str] = Counter()
    items: list[dict[str, Any]] = []

    for nid in sorted(notif_ids):
        act_refs = sorted(_fetch_ids(conn, f"SELECT id FROM actuaciones WHERE notificacion_id = {nid}"))
        ini_refs = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE notificacion_id = {nid}"))
        fk_refs = _fk_refs_to_table(conn, "notificacion", nid)

        if nid in prot.get("notificacion", set()):
            bucket = "PROTECTED"
        elif ini_refs and set(ini_refs) <= test_ini_notif:
            bucket = "SOURCE_OF_TEST_INITIATOR"
        elif not act_refs and not ini_refs:
            bucket = "ORPHAN_CONFIRMED_TEST"
        elif act_refs or ini_refs:
            bucket = "STILL_REFERENCED_REAL/INDET"
        else:
            bucket = "INDETERMINATE"

        buckets[bucket] += 1
        items.append(
            {
                "notificacion_id": nid,
                "actuaciones_refs": act_refs,
                "iniciador_ruta_refs": ini_refs,
                "other_fk_refs": fk_refs,
                "classification": bucket,
            }
        )

    return {
        "count": len(notif_ids),
        "present": _count_ids_exist(conn, "notificacion", notif_ids),
        "classification_buckets": dict(buckets),
        "items": items,
        "proposed_SAFE_NOTIFICACION_ORPHAN_TEST": sorted(
            i["notificacion_id"] for i in items if i["classification"] == "ORPHAN_CONFIRMED_TEST"
        ),
    }


def _analyze_preserved_comprobaciones(
    conn: Connection,
    comp_ids: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    buckets: Counter[str] = Counter()
    items: list[dict[str, Any]] = []
    graphs: list[dict[str, Any]] = []

    for cid in sorted(comp_ids):
        act_refs = sorted(_fetch_ids(conn, f"SELECT id FROM actuaciones WHERE comprobacion_id = {cid}"))
        ini_refs = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE comprobacion_id = {cid}"))
        oficios = _rows(
            conn,
            "SELECT id, numero_oficio FROM oficio WHERE comprobacion_id = :cid",
            {"cid": cid},
        )
        expedientes = _rows(
            conn,
            """
            SELECT e.id, e.oficio_id FROM expediente e
            JOIN oficio o ON o.id = e.oficio_id
            WHERE o.comprobacion_id = :cid
            """,
            {"cid": cid},
        )
        ini_from_oficio: list[int] = []
        for o in oficios:
            ini_from_oficio.extend(
                _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE oficio_id = {o['id']}")
            )

        if cid in prot.get("comprobacion", set()):
            bucket = "PROTECTED"
        elif oficios or expedientes or ini_from_oficio:
            bucket = "INDETERMINATE"
        elif not act_refs and not ini_refs:
            bucket = "ORPHAN_TEST"
        else:
            bucket = "STILL_USED"

        buckets[bucket] += 1
        graph_class = "INDETERMINATE"
        if bucket == "ORPHAN_TEST":
            graph_class = "ALL_TEST"
        elif bucket == "PROTECTED":
            graph_class = "PROTECTED"

        items.append(
            {
                "comprobacion_id": cid,
                "actuaciones_refs": act_refs,
                "iniciador_refs": ini_refs,
                "oficios": oficios,
                "expedientes": expedientes,
                "iniciadores_from_oficio": sorted(set(ini_from_oficio)),
                "classification": bucket,
            }
        )
        graphs.append(
            {
                "comprobacion_id": cid,
                "chain": {
                    "comprobacion": cid,
                    "expedientes": expedientes,
                    "oficios": oficios,
                    "iniciadores": sorted(set(ini_refs) | set(ini_from_oficio)),
                },
                "graph_classification": graph_class,
            }
        )

    return {
        "count": len(comp_ids),
        "present": _count_ids_exist(conn, "comprobacion", comp_ids),
        "classification_buckets": dict(buckets),
        "items": items,
        "expediente_oficio_graph": graphs,
        "proposed_SAFE_COMPROBACION_ORPHAN_TEST": sorted(
            i["comprobacion_id"] for i in items if i["classification"] == "ORPHAN_TEST"
        ),
    }


def _ot_analysis(conn: Connection, act_ids: set[int], prot: dict[str, set[int]]) -> dict[str, Any]:
    ot_map: dict[int, set[int]] = defaultdict(set)
    for aid in act_ids:
        row = conn.execute(
            text("SELECT orden_trabajo_id FROM actuaciones WHERE id = :id"), {"id": aid}
        ).fetchone()
        if row and row[0]:
            ot_map[row[0]].add(aid)

    items: list[dict[str, Any]] = []
    buckets: Counter[str] = Counter()
    deletable_after_acts = 0

    for ot_id, acts in sorted(ot_map.items()):
        all_on_ot = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        outside = all_on_ot - act_ids
        if ot_id in prot.get("orden_trabajo", set()):
            bucket = "PROTECTED"
        elif outside:
            bucket = "SHARED"
        elif len(acts) == len(all_on_ot):
            bucket = "EXCLUSIVE_TEST"
            deletable_after_acts += 1
        else:
            bucket = "INDETERMINATE"
        buckets[bucket] += 1
        items.append(
            {
                "orden_trabajo_id": ot_id,
                "acts_in_148": sorted(acts),
                "acts_total_on_ot": len(all_on_ot),
                "acts_outside_148": sorted(outside),
                "classification": bucket,
            }
        )

    return {
        "unique_ot_count": len(ot_map),
        "classification_buckets": dict(buckets),
        "deletable_after_148_acts_sim": deletable_after_acts,
        "items": items,
        "proposed_SAFE_OT_RESIDUAL": sorted(
            i["orden_trabajo_id"] for i in items if i["classification"] == "EXCLUSIVE_TEST"
        ),
    }


def _child_docs_analysis(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    cascade = cascade_children_of_actuaciones(conn, act_ids)
    preserved_notif: set[int] = set()
    preserved_comp: set[int] = set()
    for chunk in _chunk_ids(act_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = conn.execute(
            text(f"SELECT notificacion_id, comprobacion_id FROM actuaciones WHERE id IN ({ph})")
        ).fetchall()
        for r in rows:
            if r[0]:
                preserved_notif.add(r[0])
            if r[1]:
                preserved_comp.add(r[1])

    return {
        "cascade_counts": {k: len(v) for k, v in cascade.items()},
        "preserved_parent_notificacion_on_148": sorted(preserved_notif),
        "preserved_parent_comprobacion_on_148": sorted(preserved_comp),
        "policy": "PRESERVED_PARENT_DOCUMENT blocks act delete until wrappers resolved",
    }


def _simulate_wave(
    conn: Connection,
    prot: dict[str, set[int]],
    explicit: dict[str, set[int]],
    label: str,
) -> dict[str, Any]:
    virtual = VirtualDeleteState()
    for entity, ids in explicit.items():
        if entity == "actuaciones":
            for tbl, cids in cascade_children_of_actuaciones(conn, ids).items():
                virtual.add_cascade(tbl, cids)
        virtual.add_explicit(_table_for_entity(entity), ids)

    closure = protection_closure_check(virtual, prot)
    before = {t: _count(conn, t) for t in BASELINE_POST_2C1 if t in explicit or t in (
        "inspeccion", "actuaciones_inspector", "clausura", "decomiso"
    )}
    after = dict(before)
    for entity, ids in explicit.items():
        table = _table_for_entity(entity)
        if table in after:
            after[table] -= len(ids)
    if "actuaciones" in explicit:
        casc = cascade_children_of_actuaciones(conn, explicit["actuaciones"])
        for tbl, ids in casc.items():
            if tbl in after:
                after[tbl] -= len(ids)

    return {
        "wave": label,
        "explicit": {k: len(v) for k, v in explicit.items()},
        "counts_before": before,
        "counts_after_simulated": after,
        "protected_closure": closure,
    }


def _user_unlock_count(conn: Connection) -> dict[str, int]:
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    free = 0
    blocked = 0
    for uid in test_users:
        refs = 0
        for table, col in fk_columns:
            refs += int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` = :uid", {"uid": uid}) or 0)
        if refs == 0:
            free += 1
        else:
            blocked += 1
    return {"users_test_fk_free": free, "users_test_still_blocked": blocked}


def _calle_fixture_analysis(conn: Connection) -> dict[str, Any]:
    items = []
    for street in TEST_STREET_NAMES:
        dom_ids = _fetch_ids(
            conn, f"SELECT id FROM domicilio WHERE calle = '{street.replace(chr(39), chr(39)+chr(39))}'"
        )
        refs = 0
        for did in dom_ids:
            refs += int(_scalar(conn, f"SELECT COUNT(*) FROM actuaciones WHERE domicilio_id = :d", {"d": did}) or 0)
            refs += int(_scalar(conn, f"SELECT COUNT(*) FROM relevamiento WHERE domicilio_id = :d", {"d": did}) or 0)
            refs += int(_scalar(conn, f"SELECT COUNT(*) FROM denuncia WHERE domicilio_id = :d", {"d": did}) or 0)
            refs += int(_scalar(conn, f"SELECT COUNT(*) FROM iniciador_ruta WHERE domicilio_id = :d", {"d": did}) or 0)
        items.append(
            {
                "calle": street,
                "domicilio_ids": sorted(dom_ids),
                "operational_refs": refs,
                "orphan_after_residual_sim": refs == 0,
            }
        )
    return {"fixture_calles": items}


def _catalog_effects(conn: Connection, prot: dict[str, set[int]]) -> dict[str, Any]:
    rubros_test = _rows(conn, "SELECT id, nombre FROM rubro")
    rubros_zero: list[dict[str, Any]] = []
    for r in rubros_test:
        if not RUBRO_TEST_PATTERN.search(r["nombre"] or ""):
            continue
        if r["id"] in prot.get("rubro", set()):
            continue
        n = int(_scalar(conn, "SELECT COUNT(*) FROM domicilio WHERE rubro_id = :id", {"id": r["id"]}) or 0)
        if n == 0:
            rubros_zero.append(r)

    juzgados = _rows(conn, "SELECT id, nombre FROM juzgado_catalogo")
    juz_zero: list[dict[str, Any]] = []
    for j in juzgados:
        if not JUZGADO_TEST_PATTERN.search(j["nombre"] or ""):
            continue
        n = int(
            _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE juzgado_id = :id", {"id": j["id"]}) or 0
        )
        if n == 0:
            juz_zero.append(j)

    return {
        "rubros_test_zero_refs_eventual": rubros_zero[:30],
        "rubros_test_zero_refs_count": len(rubros_zero),
        "juzgados_test_zero_refs_eventual": juz_zero[:30],
        "juzgados_test_zero_refs_count": len(juz_zero),
        "note": "NO cleanup en este ticket; solo impacto eventual post-waves",
    }


def run_phase2c2_residual_graph_diag(
    conn: Connection,
    *,
    protected_path: Path,
    phase2c1_manifest_path: Path,
    structured_acts_path: Path,
    structured_diag_path: Path | None = None,
    phase2c1_apply_path: Path | None = None,
) -> dict[str, Any]:
    """Orquestador diagnóstico 3F."""
    baseline = _baseline_check(conn)
    raw_prot = load_protected_sets(load_manifest(protected_path))
    prot = expand_protected_indirect(conn, raw_prot)

    report_2c1_comp = 56
    if phase2c1_apply_path and phase2c1_apply_path.is_file():
        apply_data = json.loads(phase2c1_apply_path.read_text(encoding="utf-8"))
        pp = apply_data.get("protected_preserved", {}).get("comprobacion", {})
        report_2c1_comp = pp.get("found", 56)

    comp_reconcile = _reconcile_comprobacion_protected(conn, protected_path, report_2c1_comp)

    excluded = _load_excluded_sets(phase2c1_manifest_path)
    preserved = _load_preserved_docs(phase2c1_manifest_path)
    act_ids = excluded["blocked_acts_148"]
    rel_ids = excluded["relevamientos_26"]

    acts_148 = _analyze_acts_148(conn, act_ids, prot, structured_acts_path, structured_diag_path)
    initiators = _analyze_initiators_for_acts(conn, act_ids, prot)
    relevamientos = _analyze_relevamientos_26(conn, rel_ids, prot)

    test_ini_notif = {
        i["iniciador_id"]
        for i in initiators["items"]
        if i.get("classification") == "SAFE_TEST_WRAPPER"
        and i.get("source_fk", {}).get("notificacion_id")
    }
    notifications = _analyze_preserved_notifications(
        conn, preserved["notificacion"], prot, test_ini_notif
    )
    comprobaciones = _analyze_preserved_comprobaciones(conn, preserved["comprobacion"], prot)

    doc_ini_cross = {
        "iniciadores_sostenidos_por_notif_preservada": sum(
            1 for i in notifications["items"] if i["iniciador_ruta_refs"]
        ),
        "iniciadores_sostenidos_por_comp_preservada": sum(
            1 for i in comprobaciones["items"] if i["iniciador_refs"] or i["iniciadores_from_oficio"]
        ),
    }

    ot_analysis = _ot_analysis(conn, act_ids, prot)
    child_docs = _child_docs_analysis(conn, act_ids)

    safe_wrappers = initiators["proposed_safe_sets"]
    safe_acts = sorted(act_ids)
    safe_rel = relevamientos["proposed_SAFE_RELEVAMIENTOS_RESIDUAL"]
    safe_ot = ot_analysis["proposed_SAFE_OT_RESIDUAL"]

    wave_2c2a = _simulate_wave(
        conn,
        prot,
        {
            "iniciador_ruta": set(safe_wrappers["SAFE_INITIATORS_RESIDUAL"]),
            "ruta_item": set(safe_wrappers["SAFE_RUTA_ITEM_2C2"]),
            "ruta_pool_dia": set(safe_wrappers["SAFE_RUTA_POOL_2C2"]),
        },
        "2C.2A_wrappers",
    )
    wave_2c2b = _simulate_wave(
        conn,
        prot,
        {
            "actuaciones": set(safe_acts),
            "relevamiento": set(safe_rel),
            "orden_trabajo": set(safe_ot),
        },
        "2C.2B_acts_relevamientos_ot",
    )
    wave_2c2c = _simulate_wave(
        conn,
        prot,
        {
            "notificacion": set(notifications["proposed_SAFE_NOTIFICACION_ORPHAN_TEST"]),
            "comprobacion": set(comprobaciones["proposed_SAFE_COMPROBACION_ORPHAN_TEST"]),
        },
        "2C.2C_orphan_docs_test",
    )

    users_baseline = _user_unlock_count(conn)
    users_after_a = users_baseline.copy()
    users_after_b = users_baseline.copy()
    users_after_c = users_baseline.copy()

    safe_sets = {
        "SAFE_ROUTE_WRAPPERS_RESIDUAL": {
            "ruta_item": safe_wrappers["SAFE_RUTA_ITEM_2C2"],
            "ruta_pool": safe_wrappers["SAFE_RUTA_POOL_2C2"],
            "empty_groups": safe_wrappers["SAFE_GROUP_EMPTY_2C2"],
            "empty_routes": safe_wrappers["SAFE_ROUTE_EMPTY_2C2"],
        },
        "SAFE_INITIATORS_RESIDUAL": safe_wrappers["SAFE_INITIATORS_RESIDUAL"],
        "SAFE_ACTUACIONES_RESIDUAL": safe_acts,
        "SAFE_RELEVAMIENTOS_RESIDUAL": safe_rel,
        "SAFE_OT_RESIDUAL": safe_ot,
        "SAFE_NOTIFICACION_ORPHAN_TEST": notifications["proposed_SAFE_NOTIFICACION_ORPHAN_TEST"],
        "SAFE_COMPROBACION_ORPHAN_TEST": comprobaciones["proposed_SAFE_COMPROBACION_ORPHAN_TEST"],
        "SAFE_EXPEDIENTE_TEST": [],
        "SAFE_OFICIO_TEST": [],
    }

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3F-DIAG",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "source_artifacts": {
            "protected_manifest": str(protected_path),
            "phase2c1_execution_manifest": str(phase2c1_manifest_path),
            "structured_acts_path": str(structured_acts_path),
        },
        "protected_comprobacion_reconcile": comp_reconcile,
        "acts_148": acts_148,
        "relevamientos_26": relevamientos,
        "route_wrappers": initiators,
        "initiators": initiators,
        "notifications_199": notifications,
        "comprobaciones_20": comprobaciones,
        "document_iniciador_cross": doc_ini_cross,
        "expediente_oficio_graph": comprobaciones["expediente_oficio_graph"],
        "ot_analysis": ot_analysis,
        "child_docs": child_docs,
        "safe_sets": safe_sets,
        "blocked_sets": {
            "acts_148": sorted(act_ids),
            "relevamientos_blocked_route_or_ini": [
                i["relevamiento_id"]
                for i in relevamientos["items"]
                if i.get("classification") in ("BLOCKED_ROUTE", "BLOCKED_INICIADOR")
            ],
        },
        "proposed_waves": {
            "2C.2A": wave_2c2a,
            "2C.2B": wave_2c2b,
            "2C.2C": wave_2c2c,
            "ordering": ["2C.2A", "2C.2B", "2C.2C"],
            "note": "No mezclar por conveniencia; cada wave requiere manifest freeze propio",
        },
        "protected_closure": {
            "2C.2A": wave_2c2a["protected_closure"],
            "2C.2B": wave_2c2b["protected_closure"],
            "2C.2C": wave_2c2c["protected_closure"],
        },
        "user_unlock_simulation": {
            "baseline_post_2c1": users_baseline,
            "after_2C2A_sim": users_after_a,
            "after_2C2B_sim": users_after_b,
            "after_2C2C_sim": users_after_c,
            "note": "Simulación conservadora; recálculo exacto en apply",
        },
        "catalog_effects": _catalog_effects(conn, prot),
        "calle_fixture_refs": _calle_fixture_analysis(conn),
        "domicilios_policy": "NO DELETE en 2C.2 diag",
    }


def write_diag_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
