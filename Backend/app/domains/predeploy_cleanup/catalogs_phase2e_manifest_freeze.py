"""
PREDEPLOY-CLEANUP.3M.1 — congelar execution manifests FASE 2E catálogos.

2E-R: DELETE relevador id=2
2E-J: DELETE juzgado_catalogo id=922

Solo lectura en DB. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.catalogos.canonical.juzgados import JUZGADOS_CANONICOS
from app.domains.catalogos.canonical.normalize import normalize_catalog_key
from app.domains.catalogos.canonical.relevadores import RELEVADORES_CANONICOS
from app.domains.predeploy_cleanup.catalogs_phase2e_diag import (
    JUZGADO_TEST_ID,
    RELEVADOR_QA_ID,
    _admin_graph_guard,
    _canonical_contract,
    _incoming_fk_schema,
    _protected_juzgado_ids,
)
from app.domains.predeploy_cleanup.fk_graph import children_pointing_to_parent, load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import (
    file_sha256,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import VirtualDeleteState, protection_closure_check

RELEVADOR_SAFE_ID = RELEVADOR_QA_ID
JUZGADO_SAFE_ID = JUZGADO_TEST_ID

EXPECTED_RELEVADOR_NOMBRE = "Otro Relevador QA"
EXPECTED_JUZGADO_CODIGO = "JZSO8430AB"
EXPECTED_JUZGADO_NOMBRE = "Jz Solo Env 8430AC"

RELEVADOR_PROVENANCE = ("relevador_id_2_qa_otro", "qa_name_phase1_candidates")
JUZGADO_PROVENANCE = (
    "suite_cadena_8430",
    "juzgado_922_admin_graph",
    "oficio_1662_deleted",
)

PROTECTED_JUZGADO_IDS = frozenset({1, 164, 195, 210, 221, 235, 271, 273, 341, 395})
BLOCKED_TEST_JUZGADO_COUNT = 749
INDETERMINATE_JUZGADO_COUNT = 69
BLOCKED_QA_CALLE_IDS = (740, 741, 742, 743, 744, 745)
CALLE_ALIAS_KEEP_IDS = (236, 256, 259)
PASAJE_INDEPENDENCIA_ID = 368

BASELINE_POST_3L2 = {
    "users": 1970,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2703,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3685,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8001,
    "actuaciones": 8074,
    "denuncia": 417,
    "relevamiento": 4566,
    "orden_trabajo": 8810,
    "notificacion": 2453,
    "comprobacion": 1529,
    "expediente": 2913,
    "oficio": 1447,
    "inspeccion": 898,
    "actuaciones_inspector": 4180,
    "acta_inspeccion_item": 52,
    "clausura": 69,
    "decomiso": 25,
    "relevamiento_relevador": 525,
    "profiles": 7,
    "password_reset_codes": 1,
}

CATALOG_PHYSICAL_BASELINE = {
    "relevador": 11,
    "juzgado_catalogo": 843,
    "calle_catalogo": 744,
    "rubro": 1224,
}

RELEVADOR_CANONICAL_KEYS = frozenset(normalize_catalog_key(n) for n in RELEVADORES_CANONICOS)
JUZGADO_CANONICAL_CODES = frozenset(c for c, _ in JUZGADOS_CANONICOS)


class ManifestFreezeError(Exception):
    """Aborta freeze de manifests FASE 2E catálogos."""


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check(conn: Connection) -> dict[str, Any]:
    """Valida baseline operativo post-3L.2 y counts físicos de catálogos."""
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ManifestFreezeError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ManifestFreezeError(f"alembic={alembic}")

    counts: dict[str, int] = {}
    drift: list[str] = []
    for table, expected in BASELINE_POST_3L2.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            drift.append(f"{table}: {actual} != {expected}")

    catalog_counts: dict[str, int] = {}
    for table, expected in CATALOG_PHYSICAL_BASELINE.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        catalog_counts[table] = actual
        if actual != expected:
            drift.append(f"{table}: {actual} != {expected}")

    if drift:
        raise ManifestFreezeError(f"baseline drift: {drift}")

    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "catalog_physical_counts": catalog_counts,
        "baseline_ok": True,
        "drift": [],
    }


def load_diag_for_freeze(diag_path: Path) -> dict[str, Any]:
    """Carga y valida diagnóstico 3M sin regenerar."""
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    if data.get("writes_executed") is not False:
        raise ManifestFreezeError("source diag writes_executed != false")
    if not data.get("canonical_missing_zero"):
        raise ManifestFreezeError("canonical_missing_zero != true")

    safe = data.get("safe_global", {})
    safe_rel = safe.get("SAFE_RELEVADORES_2E", [])
    safe_jz = safe.get("SAFE_JUZGADOS_2E", [])
    safe_cal = safe.get("SAFE_CALLES_2E", [])
    safe_rub = safe.get("SAFE_RUBROS_2E", [])

    if safe_rel != [RELEVADOR_SAFE_ID]:
        raise ManifestFreezeError(f"SAFE_RELEVADORES_2E={safe_rel}")
    if safe_jz != [JUZGADO_SAFE_ID]:
        raise ManifestFreezeError(f"SAFE_JUZGADOS_2E={safe_jz}")
    if safe_cal != []:
        raise ManifestFreezeError(f"SAFE_CALLES_2E must be empty: {safe_cal}")
    if safe_rub != []:
        raise ManifestFreezeError(f"SAFE_RUBROS_2E must be empty: {safe_rub}")
    if safe.get("total_safe") != 2:
        raise ManifestFreezeError(f"total_safe={safe.get('total_safe')}")

    jz = data.get("juzgados", {})
    if len(jz.get("BLOCKED_TEST_JUZGADOS", [])) != BLOCKED_TEST_JUZGADO_COUNT:
        raise ManifestFreezeError("BLOCKED_TEST_JUZGADOS count mismatch")
    if len(jz.get("INDETERMINATE_JUZGADOS", [])) != INDETERMINATE_JUZGADO_COUNT:
        raise ManifestFreezeError("INDETERMINATE_JUZGADOS count mismatch")

    return data


def _refs_for_parent_id(
    conn: Connection,
    parent_table: str,
    parent_id: int,
    fk_schema: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cuenta refs físicas por edge para un ID de catálogo."""
    per_edge: dict[str, int] = {}
    cascade = set_null = restrict = 0
    for edge in fk_schema:
        tbl = edge["child_table"]
        col = edge["child_column"]
        cnt = int(
            _scalar(
                conn,
                f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :pid",
                {"pid": parent_id},
            )
            or 0
        )
        if cnt:
            per_edge[f"{tbl}.{col}"] = cnt
            rule = edge["delete_rule"]
            if rule == "CASCADE":
                cascade += cnt
            elif rule == "SET NULL":
                set_null += cnt
            else:
                restrict += cnt
    total = sum(per_edge.values())
    return {
        "refs_by_edge": per_edge,
        "total_refs": total,
        "cascade_refs": cascade,
        "set_null_refs": set_null,
        "restrict_refs": restrict,
        "valid_fk_free": total == 0 and cascade == 0 and set_null == 0 and restrict == 0,
    }


def _validate_relevador_id2(conn: Connection, diag_data: dict[str, Any]) -> dict[str, Any]:
    """Revalida relevador id=2 contra DB y diagnóstico."""
    row = _rows(
        conn,
        "SELECT id, nombre, activo FROM relevador WHERE id = :id",
        {"id": RELEVADOR_SAFE_ID},
    )
    if not row:
        raise ManifestFreezeError(f"relevador {RELEVADOR_SAFE_ID} missing")

    rel = row[0]
    nombre = (rel.get("nombre") or "").strip()
    if nombre != EXPECTED_RELEVADOR_NOMBRE:
        raise ManifestFreezeError(f"relevador id2 nombre={nombre!r}")

    key = normalize_catalog_key(nombre)
    if key in RELEVADOR_CANONICAL_KEYS:
        raise ManifestFreezeError("relevador id2 is canonical")

    id2_diag = diag_data["relevadores"]["id2_analysis"]
    if id2_diag.get("classification") != "CONFIRMADO_TEST_FK_FREE":
        raise ManifestFreezeError("diag id2 classification mismatch")

    fk_schema = _incoming_fk_schema(conn, "relevador")
    fk_validation = _refs_for_parent_id(conn, "relevador", RELEVADOR_SAFE_ID, fk_schema)
    if not fk_validation["valid_fk_free"]:
        raise ManifestFreezeError(f"relevador id2 FK refs: {fk_validation}")

    rr_refs = int(
        _scalar(
            conn,
            "SELECT COUNT(*) FROM relevamiento_relevador WHERE relevador_id = :id",
            {"id": RELEVADOR_SAFE_ID},
        )
        or 0
    )
    if rr_refs != 0:
        raise ManifestFreezeError(f"relevamiento_relevador refs={rr_refs}")

    fabian_refs = int(
        _scalar(
            conn,
            "SELECT COUNT(*) FROM relevamiento_relevador WHERE relevador_id = 1",
        )
        or 0
    )
    if fabian_refs != 525:
        raise ManifestFreezeError(f"relevador id1 refs={fabian_refs} != 525")

    canonical_rows = _rows(conn, "SELECT id, nombre FROM relevador WHERE id != :id", {"id": RELEVADOR_SAFE_ID})
    canonical_ids = [
        r["id"]
        for r in canonical_rows
        if normalize_catalog_key(r.get("nombre") or "") in RELEVADOR_CANONICAL_KEYS
    ]
    if len(canonical_ids) != 10:
        raise ManifestFreezeError(f"canonical relevadores after sim={len(canonical_ids)}")

    if 1 not in canonical_ids:
        raise ManifestFreezeError("relevador id1 not in canonical survivors")

    return {
        "id": RELEVADOR_SAFE_ID,
        "nombre": nombre,
        "normalized_name": key,
        "activo": rel.get("activo"),
        "classification": "CONFIRMADO_TEST_FK_FREE",
        "provenance": list(RELEVADOR_PROVENANCE),
        "fk_schema": fk_schema,
        "fk_validation": fk_validation,
        "canonical_survivors": sorted(canonical_ids),
        "canonical_survivor_count": 10,
        "relevador_id1_fabian_refs": fabian_refs,
    }


def _validate_juzgado_id922(
    conn: Connection,
    diag_data: dict[str, Any],
    protected_jz: set[int],
) -> dict[str, Any]:
    """Revalida juzgado id=922 contra DB y diagnóstico."""
    row = _rows(
        conn,
        "SELECT id, codigo, nombre FROM juzgado_catalogo WHERE id = :id",
        {"id": JUZGADO_SAFE_ID},
    )
    if not row:
        raise ManifestFreezeError(f"juzgado {JUZGADO_SAFE_ID} missing")

    jz = row[0]
    codigo = (jz.get("codigo") or "").strip()
    nombre = (jz.get("nombre") or "").strip()
    if codigo != EXPECTED_JUZGADO_CODIGO:
        raise ManifestFreezeError(f"juzgado 922 codigo={codigo!r}")
    if nombre != EXPECTED_JUZGADO_NOMBRE:
        raise ManifestFreezeError(f"juzgado 922 nombre={nombre!r}")

    if codigo in JUZGADO_CANONICAL_CODES:
        raise ManifestFreezeError("juzgado 922 is canonical code")

    id922_diag = diag_data["juzgados"]["id922_analysis"]
    if id922_diag.get("classification") != "CONFIRMADO_TEST_FK_FREE":
        raise ManifestFreezeError("diag id922 classification mismatch")

    if JUZGADO_SAFE_ID in protected_jz:
        raise ManifestFreezeError("juzgado 922 in protected set")

    fk_schema = _incoming_fk_schema(conn, "juzgado_catalogo")
    fk_validation = _refs_for_parent_id(conn, "juzgado_catalogo", JUZGADO_SAFE_ID, fk_schema)
    if not fk_validation["valid_fk_free"]:
        raise ManifestFreezeError(f"juzgado 922 FK refs: {fk_validation}")

    oficio_refs = int(
        _scalar(
            conn,
            "SELECT COUNT(*) FROM oficio WHERE juzgado_id = :id",
            {"id": JUZGADO_SAFE_ID},
        )
        or 0
    )
    if oficio_refs != 0:
        raise ManifestFreezeError(f"oficio refs={oficio_refs}")

    missing_codes: list[str] = []
    for code, _ in JUZGADOS_CANONICOS:
        found = _scalar(
            conn,
            "SELECT COUNT(*) FROM juzgado_catalogo WHERE codigo = :c AND id != :id",
            {"c": code, "id": JUZGADO_SAFE_ID},
        )
        if not found:
            missing_codes.append(code)
    if missing_codes:
        raise ManifestFreezeError(f"canonical juzgados missing after sim: {missing_codes}")

    return {
        "id": JUZGADO_SAFE_ID,
        "codigo": codigo,
        "nombre": nombre,
        "classification": "CONFIRMADO_TEST_FK_FREE",
        "provenance": list(JUZGADO_PROVENANCE),
        "fk_schema": fk_schema,
        "fk_validation": fk_validation,
        "oficio_refs": oficio_refs,
        "canonical_missing_after_sim": 0,
    }


def _canonical_contract_guard(conn: Connection, calles_csv: Path) -> dict[str, Any]:
    """Revalida contrato canónico 10/15/734/29."""
    contract = _canonical_contract(conn, calles_csv)
    if not contract["canonical_missing_zero"]:
        raise ManifestFreezeError(
            f"canonical contract failed: missing_total={contract['canonical_missing_total']}"
        )
    return contract


def _protected_closure_check(
    conn: Connection,
    protected_path: Path,
    entity_table: str,
    entity_ids: set[int],
) -> dict[str, Any]:
    """Verifica intersección cero con grafo protected."""
    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    virtual = VirtualDeleteState()
    virtual.add_explicit(entity_table, entity_ids)
    closure = protection_closure_check(virtual, prot)
    intersection = entity_ids & prot.get(entity_table, set())
    if intersection:
        raise ManifestFreezeError(f"protected intersection {entity_table}: {intersection}")
    if not closure.get("valid"):
        raise ManifestFreezeError(f"protected closure invalid: {closure.get('conflicts', [])[:3]}")
    return {"protected_intersection": 0, "closure_valid": True, "detail": closure}


def _operational_guards(conn: Connection, manifest_paths: list[Path]) -> dict[str, Any]:
    """Guards conocidos post-fases previas."""
    known = _load_known_test_ids_from_manifests(manifest_paths)
    test_guard = _known_test_guard(conn, known)
    admin_guard = _admin_graph_guard(conn)
    if not test_guard["guard_ok"]:
        raise ManifestFreezeError("known_test act/ot guard failed")
    if not admin_guard["guard_ok"]:
        raise ManifestFreezeError("admin/route/users guards failed")
    return {**test_guard, **admin_guard}


def _build_manifest_2e_r(
    *,
    baseline: dict[str, Any],
    diag_path: Path,
    protected_path: Path,
    source_diag_sha: str,
    relevador_audit: dict[str, Any],
    protected_closure: dict[str, Any],
    operational_guards: dict[str, Any],
) -> dict[str, Any]:
    """Construye manifest congelado 2E-R."""
    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2E_R_RELEVADOR",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(diag_path.resolve()),
        "source_diag_sha256": source_diag_sha,
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "entities": {"relevador": [RELEVADOR_SAFE_ID]},
        "classification": {"CONFIRMADO_TEST_FK_FREE": 1},
        "identity_snapshot": [
            {
                "id": relevador_audit["id"],
                "nombre": relevador_audit["nombre"],
                "normalized_name": relevador_audit["normalized_name"],
                "provenance": relevador_audit["provenance"],
                "classification": relevador_audit["classification"],
            }
        ],
        "fk_schema": {"relevador": relevador_audit["fk_schema"]},
        "fk_validation": relevador_audit["fk_validation"],
        "expected_effects": {
            "explicit_delete": 1,
            "cascade": 0,
            "set_null": 0,
            "restrict": 0,
        },
        "expected_counts_before": {
            "relevador": CATALOG_PHYSICAL_BASELINE["relevador"],
            "relevamiento_relevador": BASELINE_POST_3L2["relevamiento_relevador"],
        },
        "expected_counts_after": {
            "relevador": 10,
            "relevamiento_relevador": 525,
        },
        "canonical_survivors": relevador_audit["canonical_survivors"],
        "canonical_survivor_count": 10,
        "relevador_id1_preserved": {
            "id": 1,
            "nombre": "Fabian Esquivel",
            "relevamiento_relevador_refs": relevador_audit["relevador_id1_fabian_refs"],
        },
        "protected_intersection": protected_closure["protected_intersection"],
        "protected_closure_detail": protected_closure["detail"],
        "excluded": {
            "canonical_relevadores": sorted(relevador_audit["canonical_survivors"]),
            "juzgado_922": "NO_DELETE in 2E-R",
            "calle_catalogo": "NO_DELETE",
            "rubro": "NO_DELETE",
            "users": "NO_DELETE",
            "operational_data": "NO_DELETE",
        },
        "known_test_guards": operational_guards,
        "users_effect": {
            "users_baseline": BASELINE_POST_3L2["users"],
            "users_affected": 0,
        },
        "validation": {
            "entity_set": [RELEVADOR_SAFE_ID],
            "single_table_only": True,
            "fk_refs_zero": relevador_audit["fk_validation"]["valid_fk_free"],
        },
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def _build_manifest_2e_j(
    *,
    baseline: dict[str, Any],
    diag_path: Path,
    protected_path: Path,
    source_diag_sha: str,
    diag_data: dict[str, Any],
    juzgado_audit: dict[str, Any],
    protected_jz: set[int],
    protected_closure: dict[str, Any],
    operational_guards: dict[str, Any],
) -> dict[str, Any]:
    """Construye manifest congelado 2E-J."""
    jz_section = diag_data["juzgados"]
    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2E_J_JUZGADO",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(diag_path.resolve()),
        "source_diag_sha256": source_diag_sha,
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "execution_precondition": {
            "phase2e_r_applied": True,
            "phase2e_r_expected_state": {"relevador": 10},
            "relevador_count": 10,
            "juzgado_catalogo_before": CATALOG_PHYSICAL_BASELINE["juzgado_catalogo"],
        },
        "entities": {"juzgado_catalogo": [JUZGADO_SAFE_ID]},
        "classification": {"CONFIRMADO_TEST_FK_FREE": 1},
        "identity_snapshot": [
            {
                "id": juzgado_audit["id"],
                "codigo": juzgado_audit["codigo"],
                "nombre": juzgado_audit["nombre"],
                "provenance": juzgado_audit["provenance"],
                "classification": juzgado_audit["classification"],
            }
        ],
        "fk_schema": {"juzgado_catalogo": juzgado_audit["fk_schema"]},
        "fk_validation": juzgado_audit["fk_validation"],
        "expected_effects": {
            "explicit_delete": 1,
            "cascade": 0,
            "set_null": 0,
            "restrict": 0,
        },
        "expected_counts_before": {
            "juzgado_catalogo": CATALOG_PHYSICAL_BASELINE["juzgado_catalogo"],
            "oficio": BASELINE_POST_3L2["oficio"],
        },
        "expected_counts_after": {
            "juzgado_catalogo": 842,
            "oficio": BASELINE_POST_3L2["oficio"],
        },
        "preserve": {
            "protected_juzgado_ids": sorted(protected_jz),
            "canonical_juzgados": jz_section.get("CANONICAL_JUZGADOS", []),
            "blocked_test_juzgados_count": BLOCKED_TEST_JUZGADO_COUNT,
            "indeterminate_juzgados_count": INDETERMINATE_JUZGADO_COUNT,
            "policy": "NO remapear oficios protected; NO delete blocked/indeterminate",
        },
        "protected_intersection": protected_closure["protected_intersection"],
        "protected_closure_detail": protected_closure["detail"],
        "excluded": {
            "relevador": "deleted in 2E-R only",
            "calle_catalogo": "NO_DELETE",
            "rubro": "NO_DELETE",
            "users": "NO_DELETE",
            "operational_data": "NO_DELETE",
        },
        "known_test_guards": operational_guards,
        "users_effect": {
            "users_baseline": BASELINE_POST_3L2["users"],
            "users_affected": 0,
        },
        "validation": {
            "entity_set": [JUZGADO_SAFE_ID],
            "single_table_only": True,
            "fk_refs_zero": juzgado_audit["fk_validation"]["valid_fk_free"],
            "canonical_missing_after": 0,
        },
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def run_catalogs_phase2e_manifest_freeze(
    conn: Connection,
    *,
    diag_path: Path,
    protected_path: Path,
    manifest_paths: list[Path],
    calles_csv: Path,
) -> dict[str, Any]:
    """
    Orquestador freeze manifests 2E-R y 2E-J.

    Raises ManifestFreezeError si cualquier guard falla.
    """
    baseline = _baseline_check(conn)
    diag_data = load_diag_for_freeze(diag_path)
    source_diag_sha = file_sha256(diag_path)
    _canonical_contract_guard(conn, calles_csv)

    stale_r = validate_ids_exist(conn, "relevador", {RELEVADOR_SAFE_ID}, label="relevador")
    stale_j = validate_ids_exist(conn, "juzgado_catalogo", {JUZGADO_SAFE_ID}, label="juzgado")
    if stale_r or stale_j:
        raise ManifestFreezeError(f"stale ids: relevador={stale_r} juzgado={stale_j}")

    protected_jz = _protected_juzgado_ids(conn, protected_path)
    if protected_jz != set(PROTECTED_JUZGADO_IDS):
        raise ManifestFreezeError(f"protected_juzgado_ids drift: {sorted(protected_jz)}")

    relevador_audit = _validate_relevador_id2(conn, diag_data)
    juzgado_audit = _validate_juzgado_id922(conn, diag_data, protected_jz)
    operational_guards = _operational_guards(conn, manifest_paths)

    closure_r = _protected_closure_check(
        conn, protected_path, "relevador", {RELEVADOR_SAFE_ID}
    )
    closure_j = _protected_closure_check(
        conn, protected_path, "juzgado_catalogo", {JUZGADO_SAFE_ID}
    )

    manifest_r = _build_manifest_2e_r(
        baseline=baseline,
        diag_path=diag_path,
        protected_path=protected_path,
        source_diag_sha=source_diag_sha,
        relevador_audit=relevador_audit,
        protected_closure=closure_r,
        operational_guards=operational_guards,
    )
    manifest_j = _build_manifest_2e_j(
        baseline=baseline,
        diag_path=diag_path,
        protected_path=protected_path,
        source_diag_sha=source_diag_sha,
        diag_data=diag_data,
        juzgado_audit=juzgado_audit,
        protected_jz=protected_jz,
        protected_closure=closure_j,
        operational_guards=operational_guards,
    )

    if set(manifest_r["entities"]) & set(manifest_j["entities"]):
        raise ManifestFreezeError("cross-manifest entity table overlap")

    combined_postcounts = {
        "current": CATALOG_PHYSICAL_BASELINE,
        "after_2e_r": {
            **CATALOG_PHYSICAL_BASELINE,
            "relevador": 10,
        },
        "after_2e_j": {
            "relevador": 10,
            "juzgado_catalogo": 842,
            "calle_catalogo": CATALOG_PHYSICAL_BASELINE["calle_catalogo"],
            "rubro": CATALOG_PHYSICAL_BASELINE["rubro"],
        },
    }

    return {
        "ticket": "PREDEPLOY-CLEANUP.3M.1",
        "generated_at": datetime.now().isoformat(),
        "writes_executed": False,
        "baseline": baseline,
        "source_diag_path": str(diag_path.resolve()),
        "source_diag_sha256": source_diag_sha,
        "canonical_contract_ok": True,
        "2e_r": {
            "manifest": manifest_r,
            "manifest_sha256": manifest_r["manifest_sha256"],
            "entities": manifest_r["entities"],
            "expected_effects": manifest_r["expected_effects"],
            "tests": "tests/test_cleanup_catalogs_phase2e_manifest.py::TestPhase2eRelevador",
        },
        "2e_j": {
            "manifest": manifest_j,
            "manifest_sha256": manifest_j["manifest_sha256"],
            "entities": manifest_j["entities"],
            "expected_effects": manifest_j["expected_effects"],
            "tests": "tests/test_cleanup_catalogs_phase2e_manifest.py::TestPhase2eJuzgado",
        },
        "2e_c": {
            "generated": False,
            "status": "STOP",
            "safe_calles_2e": [],
            "blocked_qa_ids": list(BLOCKED_QA_CALLE_IDS),
            "alias_keep_ids": list(CALLE_ALIAS_KEEP_IDS),
            "indeterminate_ids": [PASAJE_INDEPENDENCIA_ID],
            "policy": "NO DELETE; NO SET NULL; NO REMAP DOMICILIO",
        },
        "2e_u": {
            "generated": False,
            "status": "STOP",
            "safe_rubros_2e": [],
            "classification": {
                "CANONICAL": 29,
                "CONFIRMADO_TEST_BLOCKED": 669,
                "LEGACY_REAL_KEEP": 515,
                "INDETERMINATE": 11,
            },
        },
        "cross_manifest_disjointness": {
            "entity_tables_disjoint": True,
            "relevador_ids": [RELEVADOR_SAFE_ID],
            "juzgado_ids": [JUZGADO_SAFE_ID],
            "intersection": [],
        },
        "combined_postcounts": combined_postcounts,
        "protected_guard": {
            "2e_r_protected_intersection": closure_r["protected_intersection"],
            "2e_j_protected_intersection": closure_j["protected_intersection"],
            "combined_protected_intersection": 0,
        },
        "users_effect": {
            "users_baseline": BASELINE_POST_3L2["users"],
            "users_affected": 0,
        },
        "known_test_guards": operational_guards,
        "manifest_2e_r": manifest_r,
        "manifest_2e_j": manifest_j,
    }


def write_freeze_report(report: dict[str, Any], path: Path) -> None:
    """Escribe freeze report JSON (sin manifests embebidos duplicados si se guardan aparte)."""
    export = {k: v for k, v in report.items() if k not in ("manifest_2e_r", "manifest_2e_j")}
    export["2e_r"] = {
        "manifest_path": None,
        "manifest_sha256": report["2e_r"]["manifest_sha256"],
        "entities": report["2e_r"]["entities"],
        "expected_effects": report["2e_r"]["expected_effects"],
        "tests": report["2e_r"]["tests"],
    }
    export["2e_j"] = {
        "manifest_path": None,
        "manifest_sha256": report["2e_j"]["manifest_sha256"],
        "entities": report["2e_j"]["entities"],
        "expected_effects": report["2e_j"]["expected_effects"],
        "tests": report["2e_j"]["tests"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(export, indent=2, default=str), encoding="utf-8")
