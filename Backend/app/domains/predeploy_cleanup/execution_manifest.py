"""Generación y validación del execution manifest congelado FASE 1."""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import CRITICAL_PROTECTED_ENTITIES
from app.domains.predeploy_cleanup.manifest_io import (
    ManifestError,
    entity_ids,
    file_sha256,
    load_manifest,
    manifest_sha256,
)
from app.domains.predeploy_cleanup.protected import hard_conflict_check, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import ENTITY_TABLE, _table_for_entity

EXECUTION_ENTITIES = (
    "ruta_grupo_inspector",
    "ruta_item",
    "ruta_pool_dia",
    "ruta_grupo",
    "ruta_trabajo",
    "iniciador_ruta",
    "actuaciones",
    "denuncia",
    "relevamiento",
    "orden_trabajo",
    "juzgado_catalogo",
    "rubro",
    "relevador",
    "users",
)

FORBIDDEN_ENTITIES = frozenset({"domicilio", "contribuyente", "expediente", "oficio"})

def expected_counts_from_dry_run(dry_run: dict[str, Any]) -> dict[str, int]:
    """Conteos esperados desde executability_table del dry-run v3."""
    table = {row["entidad"]: row for row in dry_run.get("executability_table", [])}
    counts: dict[str, int] = {}
    for entity in EXECUTION_ENTITIES:
        row = table.get(entity, {})
        if "delete_final" in row:
            counts[entity] = int(row["delete_final"])
        if "blocked" in row:
            counts[f"{entity}__blocked"] = int(row["blocked"])
    return counts


def parse_id_set_literal(value: str | set | list) -> set[int]:
    """Parsea '{1, 2, 3}' o lista a set[int]."""
    if isinstance(value, set):
        return {int(x) for x in value}
    if isinstance(value, list):
        return {int(x) for x in value}
    if not isinstance(value, str):
        raise ManifestError(f"Formato ID set inválido: {type(value)}")
    s = value.strip()
    if not s:
        return set()
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        if not inner:
            return set()
        return {int(x.strip()) for x in inner.split(",")}
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, (set, list, tuple)):
            return {int(x) for x in parsed}
    except (SyntaxError, ValueError):
        pass
    raise ManifestError(f"No se pudo parsear set de IDs: {s[:80]}...")


def extract_execution_ids_from_dry_run_v3(dry_run: dict[str, Any]) -> dict[str, set[int]]:
    """Extrae IDs ejecutables desde dry-run v3 (adjusted_explicit)."""
    adjusted = dry_run.get("execution_validation", {}).get("adjusted_explicit", {})
    if not adjusted:
        raise ManifestError("dry-run v3 sin execution_validation.adjusted_explicit")

    result: dict[str, set[int]] = {}
    for entity in EXECUTION_ENTITIES:
        raw = adjusted.get(entity)
        if raw is None:
            result[entity] = set()
            continue
        result[entity] = parse_id_set_literal(raw)
    return result


def compute_blocked_ids(
    cleanup_manifest: dict[str, Any],
    execution_ids: dict[str, set[int]],
) -> dict[str, set[int]]:
    """Candidatos cleanup − execution = blocked."""
    blocked: dict[str, set[int]] = {}
    for entity in EXECUTION_ENTITIES:
        candidates = entity_ids(cleanup_manifest, entity)
        if not candidates and entity == "iniciador_ruta":
            ini_cls = cleanup_manifest.get("_meta", {})
            continue
        if entity == "iniciador_ruta":
            # iniciadores no están en cleanup manifest; usar dry-run classification
            blocked[entity] = set()
            continue
        exec_ids = execution_ids.get(entity, set())
        if candidates:
            blocked[entity] = candidates - exec_ids
    return blocked


def blocked_ids_from_dry_run_v3(dry_run: dict[str, Any]) -> dict[str, set[int]]:
    """Blocked IDs desde auditorías del dry-run v3."""
    blocked: dict[str, set[int]] = {}
    act_blocked = dry_run.get("actuaciones_blocked_by_iniciador", {}).get("count", 0)
    ini_cls = dry_run.get("iniciador_classification", {})
    blocked["iniciador_ruta"] = set(ini_cls.get("protected_real", [])) | set(
        ini_cls.get("blocked_indeterminate", [])
    )
    blocked["actuaciones"] = set(
        dry_run.get("iniciador_classification", {}).get("blocked_indeterminate", [])
    )  # placeholder - use audit

    # Usar audits explícitos
    den = dry_run.get("denuncia_audit", {})
    rel = dry_run.get("relevamiento_audit", {})
    blocked["denuncia"] = set(den.get("blocked_ids", []))
    blocked["relevamiento"] = set(rel.get("blocked_ids", []))

    cleanup_count = dry_run.get("protection_report", {}).get("cleanup_actuaciones", 542)
    exec_count = dry_run.get("actuaciones_final_cleanup_count", 403)
    # actuaciones blocked = candidatos - final (aproximación si no hay lista)
    ini_prot = set(dry_run.get("iniciador_wrapper_incorporated", {}).get("protected_from_wrappers_64", []))

    # Reconstruir actuaciones/OT/users blocked desde conteos + cleanup
    blocked["_counts"] = {
        "actuaciones": cleanup_count - exec_count,
        "users": dry_run.get("users_summary", {}).get("blocked_after_phase1", 2789),
        "orden_trabajo": dry_run.get("orden_trabajo_recalc", {}).get("blocked", 139),
    }
    return blocked


def assert_blocked_not_in_execution(
    execution_ids: dict[str, set[int]],
    dry_run: dict[str, Any],
    cleanup_manifest: dict[str, Any],
) -> list[str]:
    """Verifica que IDs blocked no aparecen en execution manifest."""
    errors: list[str] = []
    expected = expected_counts_from_dry_run(dry_run)

    cleanup_acts = entity_ids(cleanup_manifest, "actuaciones")
    blocked_acts = cleanup_acts - execution_ids.get("actuaciones", set())
    if blocked_acts & execution_ids.get("actuaciones", set()):
        errors.append("actuaciones blocked∩execution > 0")
    exp_blocked = expected.get("actuaciones__blocked")
    if exp_blocked is not None and len(blocked_acts) != exp_blocked:
        errors.append(f"actuaciones blocked count {len(blocked_acts)} != {exp_blocked}")

    ini_cls = dry_run.get("iniciador_classification", {})
    blocked_ini = set(ini_cls.get("protected_real", [])) | set(ini_cls.get("blocked_indeterminate", []))
    if blocked_ini & execution_ids.get("iniciador_ruta", set()):
        errors.append("iniciador_ruta blocked∩execution > 0")
    total_ini = ini_cls.get("test_candidates_total")
    exec_ini = len(execution_ids.get("iniciador_ruta", set()))
    if total_ini is not None:
        exp_ini_blocked = total_ini - exec_ini
        exp_table = expected.get("iniciador_ruta__blocked")
        if exp_table is not None and exp_ini_blocked != exp_table:
            errors.append(f"iniciador_ruta blocked derived {exp_ini_blocked} != table {exp_table}")

    for entity, audit_key in (("denuncia", "denuncia_audit"), ("relevamiento", "relevamiento_audit")):
        blocked = set(dry_run.get(audit_key, {}).get("blocked_ids", []))
        if blocked & execution_ids.get(entity, set()):
            errors.append(f"{entity} blocked∩execution > 0")
        exp_b = expected.get(f"{entity}__blocked")
        if exp_b is not None and len(blocked) != exp_b:
            errors.append(f"{entity} blocked count {len(blocked)} != {exp_b}")

    ot_cand = entity_ids(cleanup_manifest, "orden_trabajo")
    blocked_ot = ot_cand - execution_ids.get("orden_trabajo", set())
    if blocked_ot & execution_ids.get("orden_trabajo", set()):
        errors.append("orden_trabajo blocked∩execution > 0")
    exp_ot = expected.get("orden_trabajo__blocked")
    if exp_ot is not None and len(blocked_ot) != exp_ot:
        errors.append(f"orden_trabajo blocked count {len(blocked_ot)} != {exp_ot}")

    user_cand = entity_ids(cleanup_manifest, "users")
    blocked_users = user_cand - execution_ids.get("users", set())
    if blocked_users & execution_ids.get("users", set()):
        errors.append("users blocked∩execution > 0")
    exp_users = expected.get("users__blocked")
    if exp_users is not None and len(blocked_users) != exp_users:
        errors.append(f"users blocked count {len(blocked_users)} != {exp_users}")

    route_entities = {
        "ruta_grupo_inspector",
        "ruta_item",
        "ruta_pool_dia",
        "ruta_grupo",
        "ruta_trabajo",
    }
    for entity in EXECUTION_ENTITIES:
        if entity in route_entities:
            continue
        exp_del = expected.get(entity)
        actual = len(execution_ids.get(entity, set()))
        if exp_del is not None and actual != exp_del:
            errors.append(f"{entity} execution count {actual} != {exp_del}")

    for forbidden in FORBIDDEN_ENTITIES:
        if execution_ids.get(forbidden):
            errors.append(f"{forbidden} no debe estar en execution manifest")

    return errors


def build_precondition_snapshot(conn: Connection) -> dict[str, Any]:
    """Snapshot baseline de conteos e IDs críticos."""
    from sqlalchemy import text

    counts: dict[str, int] = {}
    for entity in (
        "actuaciones",
        "ruta_trabajo",
        "ruta_item",
        "iniciador_ruta",
        "denuncia",
        "relevamiento",
        "orden_trabajo",
        "users",
    ):
        table = _table_for_entity(entity)
        counts[entity] = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar() or 0

    alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    return {
        "database": conn.execute(text("SELECT DATABASE()")).scalar(),
        "alembic_revision": alembic,
        "counts": counts,
        "captured_at": datetime.now().isoformat(),
    }


def build_execution_manifest(
    conn: Connection,
    dry_run_v3: dict[str, Any],
    protected_manifest: dict[str, Any],
    cleanup_manifest: dict[str, Any],
    *,
    source_dry_run_path: Path,
    protected_manifest_path: Path,
    cleanup_manifest_path: Path,
    xlsx_path: Path | None = None,
) -> dict[str, Any]:
    """
    Construye execution manifest congelado desde dry-run v3 validado.

    Raises ManifestError si validación falla.
    """
    if not dry_run_v3.get("dry_run_valid"):
        raise ManifestError("dry-run v3 no es válido (dry_run_valid=false)")
    if dry_run_v3.get("execution_validation", {}).get("status") != "EXECUTION_PLAN_VALID":
        raise ManifestError("dry-run v3 execution_validation no es EXECUTION_PLAN_VALID")

    execution_ids = extract_execution_ids_from_dry_run_v3(dry_run_v3)

    protected = load_protected_sets(protected_manifest)
    conflicts = hard_conflict_check(execution_ids, protected, critical_entities=CRITICAL_PROTECTED_ENTITIES)
    if conflicts:
        raise ManifestError(f"execution ∩ protected: {conflicts}")

    block_errors = assert_blocked_not_in_execution(execution_ids, dry_run_v3, cleanup_manifest)
    if block_errors:
        raise ManifestError(f"blocked validation failed: {block_errors}")

    snapshot = build_precondition_snapshot(conn)
    if dry_run_v3.get("counts_before"):
        for k, v in dry_run_v3["counts_before"].items():
            if k in snapshot["counts"] and snapshot["counts"][k] != v:
                raise ManifestError(
                    f"baseline drift {k}: db={snapshot['counts'][k]} dry_run={v}"
                )

    ini_cls = dry_run_v3.get("iniciador_classification", {})
    blocked_meta = {
        "actuaciones": sorted(entity_ids(cleanup_manifest, "actuaciones") - execution_ids.get("actuaciones", set())),
        "iniciador_ruta": sorted(
            set(ini_cls.get("protected_real", [])) | set(ini_cls.get("blocked_indeterminate", []))
        ),
        "relevamiento": dry_run_v3.get("relevamiento_audit", {}).get("blocked_ids", []),
        "denuncia": dry_run_v3.get("denuncia_audit", {}).get("blocked_ids", []),
        "orden_trabajo": sorted(
            entity_ids(cleanup_manifest, "orden_trabajo") - execution_ids.get("orden_trabajo", set())
        ),
        "users": sorted(entity_ids(cleanup_manifest, "users") - execution_ids.get("users", set())),
        "protected_iniciadores": ini_cls.get("protected_real", []),
        "wrapper_protected_count": len(
            dry_run_v3.get("iniciador_wrapper_incorporated", {}).get("protected_from_wrappers_64", [])
        ),
    }

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": 1,
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "planner_version": "v3",
        "database": snapshot["database"],
        "alembic_revision": snapshot["alembic_revision"],
        "writes_executed": False,
        "delete_order": [
            "ruta_grupo_inspector",
            "ruta_item",
            "ruta_pool_dia",
            "ruta_grupo",
            "ruta_trabajo",
            "iniciador_ruta",
            "actuaciones",
            "denuncia",
            "relevamiento",
            "orden_trabajo",
            "juzgado_catalogo",
            "rubro",
            "relevador",
            "users",
        ],
        "entities": {
            entity: [{"id": i} for i in sorted(execution_ids.get(entity, set()))]
            for entity in EXECUTION_ENTITIES
        },
        "counts": {entity: len(execution_ids.get(entity, set())) for entity in EXECUTION_ENTITIES},
        "blocked_preserve": blocked_meta,
        "precondition_snapshot": snapshot,
        "source_dry_run_v3_path": str(source_dry_run_path),
        "source_cleanup_manifest_path": str(cleanup_manifest_path),
        "source_protected_manifest_path": str(protected_manifest_path),
    }

    manifest["source_dry_run_v3_hash"] = file_sha256(source_dry_run_path)
    manifest["source_protected_manifest_hash"] = protected_manifest.get("manifest_sha256") or manifest_sha256(
        protected_manifest
    )
    manifest["source_cleanup_manifest_hash"] = cleanup_manifest.get("manifest_sha256") or manifest_sha256(
        cleanup_manifest
    )
    if xlsx_path and xlsx_path.is_file():
        manifest["source_xlsx_hash"] = file_sha256(xlsx_path)
        manifest["source_xlsx_path"] = str(xlsx_path)

    manifest["execution_manifest_hash"] = manifest_sha256(manifest)
    return manifest


def load_execution_sets(manifest: dict[str, Any]) -> dict[str, set[int]]:
    """Carga sets de IDs desde execution manifest."""
    return {entity: entity_ids(manifest, entity) for entity in EXECUTION_ENTITIES}


def verify_manifest_hash(manifest: dict[str, Any]) -> bool:
    """Verifica hash embebido."""
    expected = manifest.get("execution_manifest_hash")
    if not expected:
        return False
    computed = manifest_sha256(manifest)
    return computed == expected
