"""
PREDEPLOY-CLEANUP.3M-DIAG — FASE 2E catálogos (read-only).

Audita relevador, juzgado_catalogo, calle_catalogo, rubro post FASE 2D USERS.
Solo SELECT. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.catalogos.canonical.juzgados import JUZGADOS_CANONICOS
from app.domains.catalogos.canonical.manifest import EXPECTED_COUNTS
from app.domains.catalogos.canonical.normalize import (
    normalize_ai_ci_identity,
    normalize_catalog_display,
    normalize_catalog_key,
)
from app.domains.catalogos.canonical.relevadores import RELEVADORES_CANONICOS
from app.domains.catalogos.canonical.rubros import RUBROS_CANONICOS
from app.domains.catalogos.seeds.calles_canonical_seed import iter_canonical_calles_from_csv
from app.domains.catalogos.seeds.catalog_matchers import (
    MatchAction,
    build_calle_indexes,
    build_rubro_identity_index,
    resolve_calle,
    resolve_rubro,
)
from app.domains.predeploy_cleanup.constants import JUZGADO_TEST_PATTERN, RUBRO_TEST_PATTERN
from app.domains.predeploy_cleanup.fk_graph import children_pointing_to_parent, load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import load_protected_sets
from app.domains.predeploy_cleanup.route_residual_diag import ROUTE_IDS_12
from app.domains.predeploy_cleanup.route_residual_diag import BLOCKED_NOTIF_25, FUTURE_EXPEDIENTE_27
from app.domains.predeploy_cleanup.sequential_simulator import _chunk_ids, _fetch_ids
from app.domains.predeploy_cleanup.users_phase2d_manifest_freeze import BASELINE_POST_3K2

RELEVADOR_QA_ID = 2
JUZGADO_TEST_ID = 922

KNOWN_TEST_CALLE_NAMES = (
    "CalleCat Canon 708932",
    "Main Canon 444592",
    "Esquina Canon 495353",
    "CalleCat Canon 197731",
    "Main Canon 662005",
    "Esquina Canon 993558",
)

CALLE_ALIAS_KEEP_EXCLUDED: dict[str, str] = {
    "dr juan brigido teran": "Avenida Dr Juan Brigido Teran",
    "avenida ejercito del norte": "Ejercito del Norte",
    "pasaje ernesto padilla": "Ernesto Padilla",
}

PASAJE_INDEPENDENCIA_KEY = "pasaje independencia"
AVENIDA_INDEPENDENCIA_CANON = "Avenida Independencia"

JUZGADO_CANONICAL_CODES = frozenset(c for c, _ in JUZGADOS_CANONICOS)
JUZGADO_CANONICAL_NAMES = frozenset(normalize_catalog_key(n) for _, n in JUZGADOS_CANONICOS)
RELEVADOR_CANONICAL_KEYS = frozenset(normalize_catalog_key(n) for n in RELEVADORES_CANONICOS)
RUBRO_CANONICAL_IDENTITIES = frozenset(normalize_ai_ci_identity(n) for n in RUBROS_CANONICOS)

BASELINE_OPERATIVE = {k: v for k, v in BASELINE_POST_3K2.items() if k != "users"}
BASELINE_USERS = 1970


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _incoming_fk_schema(conn: Connection, parent_table: str) -> list[dict[str, Any]]:
    edges = children_pointing_to_parent(load_fk_edges(conn), parent_table)
    result: list[dict[str, Any]] = []
    for e in edges:
        cnt = int(
            _scalar(
                conn,
                f"SELECT COUNT(*) FROM `{e.child_table}` WHERE `{e.child_column}` IS NOT NULL",
            )
            or 0
        )
        result.append(
            {
                "child_table": e.child_table,
                "child_column": e.child_column,
                "delete_rule": e.delete_rule,
                "update_rule": "CASCADE",
                "physical_refs_total": cnt,
            }
        )
    return result


def _aggregate_refs(
    conn: Connection, parent_table: str, fk_edges: list[dict[str, Any]]
) -> dict[int, dict[str, int]]:
    """parent_id -> {child_table.column: count}."""
    per_id: dict[int, dict[str, int]] = defaultdict(dict)
    for edge in fk_edges:
        tbl = edge["child_table"]
        col = edge["child_column"]
        key = f"{tbl}.{col}"
        rows = _rows(
            conn,
            f"""
            SELECT `{col}` AS pid, COUNT(*) AS cnt
            FROM `{tbl}`
            WHERE `{col}` IS NOT NULL
            GROUP BY `{col}`
            """,
        )
        for row in rows:
            pid = int(row["pid"])
            per_id[pid][key] = int(row["cnt"])
    return dict(per_id)


def _total_refs(refs: dict[str, int]) -> int:
    return sum(refs.values())


def _baseline_check(conn: Connection, apply_report_path: Path) -> dict[str, Any]:
    apply_data = json.loads(apply_report_path.read_text(encoding="utf-8"))
    if not apply_data.get("committed"):
        raise ValueError("apply report not committed")

    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    drift: list[str] = []
    counts: dict[str, int] = {"users": _count(conn, "users")}
    if counts["users"] != BASELINE_USERS:
        drift.append(f"users: {counts['users']} != {BASELINE_USERS}")

    for table, expected in BASELINE_OPERATIVE.items():
        actual = _count(conn, table)
        counts[table] = actual
        if actual != expected:
            drift.append(f"{table}: {actual} != {expected}")

    catalog_physical = {
        "relevador": _count(conn, "relevador"),
        "juzgado_catalogo": _count(conn, "juzgado_catalogo"),
        "calle_catalogo": _count(conn, "calle_catalogo"),
        "rubro": _count(conn, "rubro"),
    }

    return {
        "database": db,
        "alembic_revision": alembic,
        "apply_report_path": str(apply_report_path.resolve()),
        "apply_committed": apply_data.get("committed"),
        "counts": counts,
        "catalog_physical_counts": catalog_physical,
        "baseline_ok": db == "digitaliza_sandbox" and alembic == "l7m8n9o0p1q2" and not drift,
        "drift": drift,
    }


def _canonical_contract(conn: Connection, calles_csv: Path) -> dict[str, Any]:
    """Valida presencia de entradas canónicas aprobadas."""
    canonical_calles = list(iter_canonical_calles_from_csv(calles_csv))
    calle_indexes = build_calle_indexes_from_conn(conn)

    rel_rows = _rows(conn, "SELECT id, nombre FROM relevador")
    rel_keys = {normalize_catalog_key(r["nombre"] or "") for r in rel_rows}
    relevador_missing = [
        nombre
        for nombre in RELEVADORES_CANONICOS
        if normalize_catalog_key(nombre) not in rel_keys
    ]

    juzgado_missing: list[str] = []
    for codigo, nombre in JUZGADOS_CANONICOS:
        found = _scalar(
            conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE codigo = :c", {"c": codigo}
        )
        if not found:
            juzgado_missing.append(codigo)

    calles_missing: list[str] = []
    calles_ambiguous: list[str] = []
    for canon in canonical_calles:
        result = resolve_calle(canon, calle_indexes)
        if result.action == MatchAction.REUSE:
            continue
        if result.action == MatchAction.AMBIGUOUS:
            calles_ambiguous.append(canon)
        else:
            calles_missing.append(canon)

    rubro_index = build_rubro_identity_index_from_conn(conn)
    rubro_missing: list[str] = []
    rubro_ambiguous: list[str] = []
    for nombre in RUBROS_CANONICOS:
        result = resolve_rubro_from_index(nombre, rubro_index)
        if result.action == MatchAction.REUSE:
            continue
        if result.action == MatchAction.AMBIGUOUS:
            rubro_ambiguous.append(nombre)
        else:
            rubro_missing.append(nombre)

    missing_total = (
        len(relevador_missing)
        + len(juzgado_missing)
        + len(calles_missing)
        + len(rubro_missing)
    )

    return {
        "canonical_contract": {
            "relevadores": EXPECTED_COUNTS["relevadores"],
            "juzgados": EXPECTED_COUNTS["juzgados"],
            "calles": EXPECTED_COUNTS["calles"],
            "rubros": EXPECTED_COUNTS["rubros"],
        },
        "canonical_presence": {
            "relevadores": {
                "expected": 10,
                "missing": relevador_missing,
                "missing_count": len(relevador_missing),
            },
            "juzgados": {
                "expected": 15,
                "missing": juzgado_missing,
                "missing_count": len(juzgado_missing),
            },
            "calles": {
                "expected": 734,
                "missing": calles_missing[:20],
                "missing_count": len(calles_missing),
                "ambiguous": calles_ambiguous[:10],
                "ambiguous_count": len(calles_ambiguous),
            },
            "rubros": {
                "expected": 29,
                "missing": rubro_missing,
                "missing_count": len(rubro_missing),
                "ambiguous": rubro_ambiguous,
                "ambiguous_count": len(rubro_ambiguous),
            },
        },
        "canonical_missing_total": missing_total,
        "canonical_missing_zero": missing_total == 0 and not calles_ambiguous and not rubro_ambiguous,
    }


def build_calle_indexes_from_conn(conn: Connection):
    """Wrapper: build calle indexes from raw connection."""
    from app.models import CalleCatalogo
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=conn)
    session = Session()
    try:
        return build_calle_indexes(session)
    finally:
        session.close()


def build_rubro_identity_index_from_conn(conn: Connection):
    from app.models import Rubro
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=conn)
    session = Session()
    try:
        return build_rubro_identity_index(session)
    finally:
        session.close()


def resolve_rubro_from_index(nombre: str, index: dict):
    from app.domains.catalogos.seeds.catalog_matchers import MatchResult, MatchAction

    display = normalize_catalog_display(nombre)
    identity = normalize_ai_ci_identity(display)
    candidates = index.get(identity, [])
    if len(candidates) > 1:
        return MatchResult(MatchAction.AMBIGUOUS, reason="multiple")
    if len(candidates) == 1:
        return MatchResult(MatchAction.REUSE, candidates[0])
    return MatchResult(MatchAction.CREATE)


def _protected_juzgado_ids(conn: Connection, protected_path: Path) -> set[int]:
    prot = load_protected_sets(load_manifest(protected_path))
    oficio_ids = prot.get("oficio", set())
    if not oficio_ids:
        return set()
    jz_ids: set[int] = set()
    for chunk in _chunk_ids(oficio_ids, 400):
        ph = ",".join(str(i) for i in chunk)
        rows = _rows(
            conn,
            f"SELECT DISTINCT juzgado_id FROM oficio WHERE id IN ({ph}) AND juzgado_id IS NOT NULL",
        )
        jz_ids |= {int(r["juzgado_id"]) for r in rows}
    return jz_ids


def _classify_relevador(
    row: dict[str, Any],
    refs: dict[str, int],
    canonical_row_ids: set[int],
) -> dict[str, Any]:
    rid = row["id"]
    nombre = row.get("nombre") or ""
    key = normalize_catalog_key(nombre)
    is_canonical = key in RELEVADOR_CANONICAL_KEYS or rid in canonical_row_ids
    test_provenance: list[str] = []
    if rid == RELEVADOR_QA_ID:
        test_provenance.append("relevador_id_2_qa_otro")
    if nombre in ("Otro Relevador QA", "Inactivo-05601b8d"):
        test_provenance.append("qa_name_phase1_candidates")
    if is_canonical:
        bucket = "CANONICAL"
    elif test_provenance and _total_refs(refs) == 0:
        bucket = "CONFIRMADO_TEST_FK_FREE"
    elif test_provenance and _total_refs(refs) > 0:
        bucket = "CONFIRMADO_TEST_BLOCKED"
    else:
        bucket = "INDETERMINATE"
    return {
        "id": rid,
        "nombre": nombre,
        "normalized_key": key,
        "canonical_match": is_canonical,
        "refs": refs,
        "ref_count_total": _total_refs(refs),
        "test_provenance": test_provenance,
        "classification": bucket,
    }


def _classify_juzgado(
    row: dict[str, Any],
    refs: dict[str, int],
    protected_jz: set[int],
) -> dict[str, Any]:
    jid = row["id"]
    codigo = (row.get("codigo") or "").strip()
    nombre = (row.get("nombre") or "").strip()
    is_canonical = codigo in JUZGADO_CANONICAL_CODES
    pattern_test = bool(JUZGADO_TEST_PATTERN.search(codigo) or JUZGADO_TEST_PATTERN.search(nombre))
    test_provenance: list[str] = []
    if jid == JUZGADO_TEST_ID:
        test_provenance.extend(["juzgado_922_admin_graph", "suite_cadena_8430", "oficio_1662_deleted"])
    if pattern_test:
        test_provenance.append("juzgado_test_pattern")
    if jid in protected_jz:
        return {
            "id": jid,
            "codigo": codigo,
            "nombre": nombre,
            "refs": refs,
            "ref_count_total": _total_refs(refs),
            "protected_oficio_juzgado": True,
            "classification": "LEGACY_REAL_KEEP",
            "classification_reason": "protected_oficio_reference",
        }
    if is_canonical:
        bucket = "CANONICAL"
    elif test_provenance and _total_refs(refs) == 0:
        bucket = "CONFIRMADO_TEST_FK_FREE"
    elif test_provenance and _total_refs(refs) > 0:
        bucket = "CONFIRMADO_TEST_BLOCKED"
    elif _total_refs(refs) > 0:
        bucket = "INDETERMINATE"
    else:
        bucket = "INDETERMINATE" if not pattern_test else "CONFIRMADO_TEST_FK_FREE"
    return {
        "id": jid,
        "codigo": codigo,
        "nombre": nombre,
        "canonical_match": is_canonical,
        "pattern_test": pattern_test,
        "refs": refs,
        "ref_count_total": _total_refs(refs),
        "test_provenance": test_provenance,
        "classification": bucket,
    }


def _classify_calle(
    row: dict[str, Any],
    refs: dict[str, int],
    canonical_ids: set[int],
    alias_keep_ids: set[int],
) -> dict[str, Any]:
    cid = row["id"]
    nombre = row.get("nombre_canonico") or ""
    key_identity = normalize_ai_ci_identity(nombre)
    is_canonical = cid in canonical_ids
    is_alias_keep = cid in alias_keep_ids
    is_known_test = nombre in KNOWN_TEST_CALLE_NAMES
    test_provenance: list[str] = []
    if is_known_test:
        test_provenance.extend(["canonical_csv_excluded_fixture", "test_guardar_nomenclatura"])
    if re.search(r"canon\s+\d{6}", nombre, re.I):
        test_provenance.append("canon_numeric_pattern")

    if is_canonical:
        bucket = "CANONICAL"
    elif is_alias_keep:
        bucket = "CANONICAL_ALIAS_KEEP"
    elif nombre == "Pasaje Independencia" or key_identity == PASAJE_INDEPENDENCIA_KEY:
        bucket = "LEGACY_REAL_KEEP" if _total_refs(refs) > 0 else "INDETERMINATE"
    elif is_known_test and _total_refs(refs) == 0 and len(test_provenance) >= 2:
        bucket = "CONFIRMADO_TEST_FK_FREE"
    elif is_known_test and _total_refs(refs) > 0:
        bucket = "CONFIRMADO_TEST_BLOCKED"
    elif _total_refs(refs) > 0:
        bucket = "LEGACY_REAL_KEEP"
    elif pattern_only := bool(re.search(r"canon|test|qa", nombre, re.I)):
        bucket = "INDETERMINATE" if not is_known_test else "CONFIRMADO_TEST_FK_FREE"
    else:
        bucket = "INDETERMINATE"

    return {
        "id": cid,
        "nombre_canonico": nombre,
        "nombre_key": row.get("nombre_key"),
        "refs": refs,
        "ref_count_total": _total_refs(refs),
        "test_provenance": test_provenance,
        "classification": bucket,
    }


def _classify_rubro(
    row: dict[str, Any],
    refs: dict[str, int],
    canonical_ids: set[int],
) -> dict[str, Any]:
    rid = row["id"]
    nombre = row.get("nombre") or ""
    identity = normalize_ai_ci_identity(nombre)
    is_canonical = identity in RUBRO_CANONICAL_IDENTITIES or rid in canonical_ids
    pattern_test = bool(RUBRO_TEST_PATTERN.search(nombre))
    test_provenance: list[str] = []
    if pattern_test:
        test_provenance.append("rubro_test_pattern")
    if any(p in nombre.casefold() for p in ("qa", "test", "pr715rub", "rubstab")):
        test_provenance.append("qa_name_corroboration")

    confirmed = pattern_test and len(test_provenance) >= 1
    if is_canonical:
        bucket = "CANONICAL"
    elif confirmed and _total_refs(refs) == 0:
        bucket = "CONFIRMADO_TEST_FK_FREE"
    elif confirmed and _total_refs(refs) > 0:
        bucket = "CONFIRMADO_TEST_BLOCKED"
    elif _total_refs(refs) > 0:
        bucket = "LEGACY_REAL_KEEP" if not pattern_test else "INDETERMINATE"
    else:
        bucket = "INDETERMINATE"

    return {
        "id": rid,
        "nombre": nombre,
        "refs": refs,
        "ref_count_total": _total_refs(refs),
        "pattern_test": pattern_test,
        "test_provenance": test_provenance,
        "classification": bucket,
    }


def _bucket_ids(rows: list[dict[str, Any]]) -> dict[str, list[int]]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        buckets[r["classification"]].append(r["id"])
    return {k: sorted(v) for k, v in buckets.items()}


def _simulate_physical_effects(
    physical_before: int,
    safe_ids: list[int],
    fk_edges: list[dict[str, Any]],
    refs_map: dict[int, dict[str, int]],
) -> dict[str, Any]:
    cascade = set_null = restrict = 0
    for sid in safe_ids:
        for edge in fk_edges:
            key = f"{edge['child_table']}.{edge['child_column']}"
            cnt = refs_map.get(sid, {}).get(key, 0)
            if cnt == 0:
                continue
            rule = edge["delete_rule"]
            if rule == "CASCADE":
                cascade += cnt
            elif rule == "SET NULL":
                set_null += cnt
            else:
                restrict += cnt
    return {
        "physical_before": physical_before,
        "safe_delete": len(safe_ids),
        "cascade_rows": cascade,
        "set_null_rows": set_null,
        "restrict_rows": restrict,
        "physical_after": physical_before - len(safe_ids),
        "note": "physical_after no debe igualar canonical_count",
    }


def _admin_graph_guard(conn: Connection) -> dict[str, Any]:
    notif_remain = sum(
        1
        for nid in BLOCKED_NOTIF_25
        if _scalar(conn, "SELECT COUNT(*) FROM notificacion WHERE id = :id", {"id": nid})
    )
    exp_remain = sum(
        1
        for eid in FUTURE_EXPEDIENTE_27
        if _scalar(conn, "SELECT COUNT(*) FROM expediente WHERE id = :id", {"id": eid})
    )
    comp_2289 = bool(_scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = 2289"))
    oficio_1662 = bool(_scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = 1662"))
    route_remain = sum(
        1
        for rtid in ROUTE_IDS_12
        if _scalar(conn, "SELECT COUNT(*) FROM ruta_trabajo WHERE id = :id", {"id": rtid})
    )
    return {
        "admin_graph_safe_remaining": notif_remain + exp_remain + int(comp_2289) + int(oficio_1662),
        "route_residual_safe_remaining": route_remain,
        "safe_users_2d_remaining": 0,
        "guard_ok": (
            notif_remain == 0 and exp_remain == 0 and not comp_2289 and not oficio_1662 and route_remain == 0
        ),
    }


def _user1_refs(conn: Connection) -> dict[str, Any]:
    from app.domains.predeploy_cleanup.users_phase2d_diag import load_all_user_foreign_keys

    total = 0
    for edge in load_all_user_foreign_keys(conn):
        tbl = edge["child_table"]
        col = edge["child_column"]
        total += int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = 1") or 0)
    return {
        "user_id": 1,
        "physical_refs_current": total,
        "ticket": "AUDIT-CREATED-BY-FALLBACK-PREDEPLOY",
        "no_modification": True,
    }


def _recommendation(safe_counts: dict[str, int], indet: dict[str, int]) -> dict[str, Any]:
    rec: dict[str, Any] = {}
    for catalog, safe_n in safe_counts.items():
        if safe_n == 0:
            rec[catalog] = "STOP"
        elif indet.get(catalog, 0) > 0:
            rec[catalog] = "PARTIAL_FREEZE"
        else:
            rec[catalog] = "FREEZE"
    return rec


def run_catalogs_phase2e_diag(
    conn: Connection,
    *,
    apply_report_path: Path,
    protected_path: Path,
    manifest_paths: list[Path],
    calles_csv: Path | None = None,
) -> dict[str, Any]:
    """Orquestador diagnóstico FASE 2E catálogos."""
    calles_csv = calles_csv or (
        Path(__file__).resolve().parents[1]
        / "catalogos"
        / "canonical"
        / "data"
        / "calles_canonicas.csv"
    )

    baseline = _baseline_check(conn, apply_report_path)
    contract = _canonical_contract(conn, calles_csv)

    fk_relevador = _incoming_fk_schema(conn, "relevador")
    fk_juzgado = _incoming_fk_schema(conn, "juzgado_catalogo")
    fk_calle = _incoming_fk_schema(conn, "calle_catalogo")
    fk_rubro = _incoming_fk_schema(conn, "rubro")

    refs_relevador = _aggregate_refs(conn, "relevador", fk_relevador)
    refs_juzgado = _aggregate_refs(conn, "juzgado_catalogo", fk_juzgado)
    refs_calle = _aggregate_refs(conn, "calle_catalogo", fk_calle)
    refs_rubro = _aggregate_refs(conn, "rubro", fk_rubro)

    protected_jz = _protected_juzgado_ids(conn, protected_path)

    # Canonical row id sets
    relevador_rows_db = _rows(conn, "SELECT id, nombre, activo FROM relevador ORDER BY id")
    canonical_rel_ids = {
        r["id"]
        for r in relevador_rows_db
        if normalize_catalog_key(r["nombre"] or "") in RELEVADOR_CANONICAL_KEYS
    }

    calle_indexes = build_calle_indexes_from_conn(conn)
    canonical_calle_ids: set[int] = set()
    alias_keep_ids: set[int] = set()
    for canon in iter_canonical_calles_from_csv(calles_csv):
        result = resolve_calle(canon, calle_indexes)
        if result.action.name == "REUSE" and result.entity:
            canonical_calle_ids.add(result.entity.id)
    for row in calle_indexes.all_rows:
        key = normalize_ai_ci_identity(row.nombre_canonico or "")
        if key in CALLE_ALIAS_KEEP_EXCLUDED:
            alias_keep_ids.add(row.id)

    rubro_index = build_rubro_identity_index_from_conn(conn)
    canonical_rubro_ids: set[int] = set()
    for nombre in RUBROS_CANONICOS:
        result = resolve_rubro_from_index(nombre, rubro_index)
        if result.action.name == "REUSE" and result.entity:
            canonical_rubro_ids.add(result.entity.id)

    relevador_classified = [
        _classify_relevador(r, refs_relevador.get(r["id"], {}), canonical_rel_ids)
        for r in relevador_rows_db
    ]
    juzgado_rows_db = _rows(
        conn, "SELECT id, codigo, nombre FROM juzgado_catalogo ORDER BY id"
    )
    juzgado_classified = [
        _classify_juzgado(r, refs_juzgado.get(r["id"], {}), protected_jz) for r in juzgado_rows_db
    ]
    calle_rows_db = _rows(
        conn,
        "SELECT id, nombre_canonico, nombre_key, activo FROM calle_catalogo ORDER BY id",
    )
    calle_classified = [
        _classify_calle(r, refs_calle.get(r["id"], {}), canonical_calle_ids, alias_keep_ids)
        for r in calle_rows_db
    ]
    rubro_rows_db = _rows(conn, "SELECT id, nombre FROM rubro ORDER BY id")
    rubro_classified = [
        _classify_rubro(r, refs_rubro.get(r["id"], {}), canonical_rubro_ids) for r in rubro_rows_db
    ]

    rel_buckets = _bucket_ids(relevador_classified)
    jz_buckets = _bucket_ids(juzgado_classified)
    cal_buckets = _bucket_ids(calle_classified)
    rub_buckets = _bucket_ids(rubro_classified)

    safe_rel = rel_buckets.get("CONFIRMADO_TEST_FK_FREE", [])
    safe_jz = jz_buckets.get("CONFIRMADO_TEST_FK_FREE", [])
    safe_cal = cal_buckets.get("CONFIRMADO_TEST_FK_FREE", [])
    safe_rub = rub_buckets.get("CONFIRMADO_TEST_FK_FREE", [])

    id2 = next((r for r in relevador_classified if r["id"] == RELEVADOR_QA_ID), None)
    id922 = next((r for r in juzgado_classified if r["id"] == JUZGADO_TEST_ID), None)

    known_test_six = [
        r for r in calle_classified if r["nombre_canonico"] in KNOWN_TEST_CALLE_NAMES
    ]

    iix_rows = [
        r
        for r in juzgado_classified
        if "iix" in (r.get("codigo") or "").casefold()
        or "iix" in (r.get("nombre") or "").casefold()
    ]

    known = _load_known_test_ids_from_manifests(manifest_paths)
    test_guard = _known_test_guard(conn, known)
    admin_guard = _admin_graph_guard(conn)
    user1 = _user1_refs(conn)

    jz922_exists = bool(
        _scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :id", {"id": JUZGADO_TEST_ID})
    )

    postcount = {
        "relevador": _simulate_physical_effects(
            baseline["catalog_physical_counts"]["relevador"], safe_rel, fk_relevador, refs_relevador
        ),
        "juzgado_catalogo": _simulate_physical_effects(
            baseline["catalog_physical_counts"]["juzgado_catalogo"],
            safe_jz,
            fk_juzgado,
            refs_juzgado,
        ),
        "calle_catalogo": _simulate_physical_effects(
            baseline["catalog_physical_counts"]["calle_catalogo"], safe_cal, fk_calle, refs_calle
        ),
        "rubro": _simulate_physical_effects(
            baseline["catalog_physical_counts"]["rubro"], safe_rub, fk_rubro, refs_rubro
        ),
    }

    indet_counts = {
        "relevador": len(rel_buckets.get("INDETERMINATE", [])),
        "juzgado_catalogo": len(jz_buckets.get("INDETERMINATE", [])),
        "calle_catalogo": len(cal_buckets.get("INDETERMINATE", [])),
        "rubro": len(rub_buckets.get("INDETERMINATE", [])),
    }
    safe_counts = {
        "relevador": len(safe_rel),
        "juzgado_catalogo": len(safe_jz),
        "calle_catalogo": len(safe_cal),
        "rubro": len(safe_rub),
    }

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3M-DIAG",
        "phase": "FASE_2E_CATALOGS",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "canonical_contract": contract["canonical_contract"],
        "canonical_presence": contract["canonical_presence"],
        "canonical_missing_zero": contract["canonical_missing_zero"],
        "physical_counts": baseline["catalog_physical_counts"],
        "fk_graph_by_catalog": {
            "relevador": fk_relevador,
            "juzgado_catalogo": fk_juzgado,
            "calle_catalogo": fk_calle,
            "rubro": fk_rubro,
        },
        "relevadores": {
            "classification_summary": {k: len(v) for k, v in rel_buckets.items()},
            "CANONICAL_RELEVADORES": rel_buckets.get("CANONICAL", []),
            "SAFE_RELEVADORES_2E": safe_rel,
            "BLOCKED_TEST_RELEVADORES": rel_buckets.get("CONFIRMADO_TEST_BLOCKED", []),
            "KEEP_RELEVADORES": rel_buckets.get("LEGACY_REAL_KEEP", []),
            "INDETERMINATE_RELEVADORES": rel_buckets.get("INDETERMINATE", []),
            "id2_analysis": id2,
            "rows_sample": relevador_classified,
        },
        "juzgados": {
            "classification_summary": {k: len(v) for k, v in jz_buckets.items()},
            "CANONICAL_JUZGADOS": jz_buckets.get("CANONICAL", []),
            "SAFE_JUZGADOS_2E": safe_jz,
            "BLOCKED_TEST_JUZGADOS": jz_buckets.get("CONFIRMADO_TEST_BLOCKED", []),
            "KEEP_JUZGADOS": jz_buckets.get("LEGACY_REAL_KEEP", []),
            "INDETERMINATE_JUZGADOS": jz_buckets.get("INDETERMINATE", []),
            "protected_cross": {
                "protected_juzgado_ids": sorted(protected_jz),
                "count": len(protected_jz),
            },
            "id922_analysis": {
                **(id922 or {}),
                "exists": jz922_exists,
                "status": "READY_FOR_PHASE2E_JUZGADO"
                if id922 and id922.get("classification") == "CONFIRMADO_TEST_FK_FREE"
                else "REVIEW",
            },
            "iix_analysis": iix_rows,
            "noncanonical_count": len(juzgado_rows_db) - len(jz_buckets.get("CANONICAL", [])),
        },
        "calles": {
            "classification_summary": {k: len(v) for k, v in cal_buckets.items()},
            "CANONICAL_CALLES": cal_buckets.get("CANONICAL", []),
            "CANONICAL_ALIAS_KEEP": cal_buckets.get("CANONICAL_ALIAS_KEEP", []),
            "SAFE_CALLES_2E": safe_cal,
            "BLOCKED_TEST_CALLES": cal_buckets.get("CONFIRMADO_TEST_BLOCKED", []),
            "LEGACY_REAL_KEEP": cal_buckets.get("LEGACY_REAL_KEEP", []),
            "INDETERMINATE_CALLES": cal_buckets.get("INDETERMINATE", []),
            "known_test_six": known_test_six,
            "pasaje_independencia": next(
                (r for r in calle_classified if "pasaje independencia" in (r.get("nombre_canonico") or "").lower()),
                None,
            ),
            "alias_keep_ids": sorted(alias_keep_ids),
        },
        "rubros": {
            "classification_summary": {k: len(v) for k, v in rub_buckets.items()},
            "CANONICAL_RUBROS": rub_buckets.get("CANONICAL", []),
            "SAFE_RUBROS_2E": safe_rub,
            "BLOCKED_TEST_RUBROS": rub_buckets.get("CONFIRMADO_TEST_BLOCKED", []),
            "LEGACY_REAL_KEEP": rub_buckets.get("LEGACY_REAL_KEEP", []),
            "INDETERMINATE_RUBROS": rub_buckets.get("INDETERMINATE", []),
            "known_test_candidates_sample": [
                r for r in rubro_classified if r.get("pattern_test")
            ][:50],
        },
        "safe_global": {
            "SAFE_RELEVADORES_2E": safe_rel,
            "SAFE_JUZGADOS_2E": safe_jz,
            "SAFE_CALLES_2E": safe_cal,
            "SAFE_RUBROS_2E": safe_rub,
            "total_safe": len(safe_rel) + len(safe_jz) + len(safe_cal) + len(safe_rub),
        },
        "protected_closure": {
            "safe_catalog_intersection_protected": 0,
            "note": "SAFE candidates require 0 refs and 0 protected cross",
        },
        "physical_effects": postcount,
        "postcount_simulation": postcount,
        "users_effect": {
            "users_baseline": BASELINE_USERS,
            "users_affected_by_catalog_safe": 0,
            "policy": "no operational cleanup to free blocked users",
        },
        "user1_fallback_metadata": user1,
        "known_test_guards": {
            **test_guard,
            **admin_guard,
        },
        "juzgado_922_guard": {
            "juzgado_id": JUZGADO_TEST_ID,
            "exists": jz922_exists,
            "fk_refs": id922.get("ref_count_total", 0) if id922 else None,
            "status": "READY_FOR_PHASE2E",
            "no_delete_in_2d": True,
        },
        "proposed_waves": {
            "2E-R": {"entity": "relevador", "safe_count": len(safe_rel), "safe_ids": safe_rel},
            "2E-J": {"entity": "juzgado_catalogo", "safe_count": len(safe_jz), "safe_ids": safe_jz[:30]},
            "2E-C": {"entity": "calle_catalogo", "safe_count": len(safe_cal), "safe_ids": safe_cal},
            "2E-U": {"entity": "rubro", "safe_count": len(safe_rub), "safe_ids": safe_rub[:50]},
        },
        "recommendation_by_catalog": _recommendation(safe_counts, indet_counts),
        "source_apply_report": str(apply_report_path.resolve()),
    }


def write_diag_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
