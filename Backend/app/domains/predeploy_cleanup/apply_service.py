"""Aplicación segura FASE 1: preflight, transacción única, postconditions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import CRITICAL_PROTECTED_ENTITIES
from app.domains.predeploy_cleanup.execution_manifest import (
    EXECUTION_ENTITIES,
    FORBIDDEN_ENTITIES,
    load_execution_sets,
    verify_manifest_hash,
)
from app.domains.predeploy_cleanup.execution_validator import (
    PHASE1_DELETE_ORDER_V3,
    validate_execution_plan,
)
from app.domains.predeploy_cleanup.manifest_io import (
    ManifestError,
    entity_ids,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.protected import hard_conflict_check, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    ENTITY_TABLE,
    VirtualDeleteState,
    _chunk_ids,
    _table_for_entity,
)

AFFECTED_TABLES = (
    "actuaciones",
    "inspeccion",
    "acta_inspeccion_item",
    "clausura",
    "decomiso",
    "actuaciones_inspector",
    "ruta_trabajo",
    "ruta_grupo",
    "ruta_grupo_inspector",
    "ruta_item",
    "ruta_pool_dia",
    "iniciador_ruta",
    "denuncia",
    "relevamiento",
    "relevamiento_relevador",
    "orden_trabajo",
    "users",
    "rubro",
    "juzgado_catalogo",
    "relevador",
)

CASCADE_OBSERVE_TABLES = (
    "inspeccion",
    "acta_inspeccion_item",
    "clausura",
    "decomiso",
    "actuaciones_inspector",
)

TRANSACTIONAL_ENGINES = frozenset({"InnoDB"})

ADMIN_USERNAMES = frozenset({"admin"})

EXPECTED_POST_COUNTS = {
    "actuaciones": 8487,
    "ruta_trabajo": 3566,
    "ruta_item": 4551,
    "iniciador_ruta": 8563,
    "denuncia": 492,
    "relevamiento": 4592,
    "orden_trabajo": 9223,
    "users": 2803,
    "rubro": 1217,
    "juzgado_catalogo": 831,
    "relevador": 2,
}

PROTECTED_ENTITIES_ALL = (
    "actuaciones",
    "orden_trabajo",
    "inspeccion",
    "notificacion",
    "comprobacion",
    "oficio",
    "expediente",
)


class ApplyAbortError(Exception):
    """Preflight o postcondition falló; transacción abortada."""


def audit_table_engines(conn: Connection, tables: tuple[str, ...] | None = None) -> dict[str, Any]:
    """
    Consulta ENGINE en INFORMATION_SCHEMA.TABLES.

    Retorna dict con engines por tabla y apply_enabled=False si alguna no es transaccional.
    """
    tables = tables or AFFECTED_TABLES
    placeholders = ",".join(f"'{t}'" for t in tables)
    rows = conn.execute(
        text(
            f"""
            SELECT TABLE_NAME, ENGINE
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME IN ({placeholders})
            """
        )
    ).fetchall()
    engines = {r[0]: r[1] for r in rows}
    non_tx = {t: engines.get(t) for t in tables if engines.get(t) not in TRANSACTIONAL_ENGINES}
    return {
        "engines": engines,
        "non_transactional": non_tx,
        "apply_enabled": len(non_tx) == 0 and len(engines) == len(tables),
    }


def _count_table(conn: Connection, table: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar() or 0


def _count_ids_exist(conn: Connection, table: str, ids: set[int]) -> int:
    if not ids:
        return 0
    total = 0
    for chunk in _chunk_ids(ids, 500):
        ph = ",".join(str(x) for x in chunk)
        total += conn.execute(text(f"SELECT COUNT(*) FROM `{table}` WHERE id IN ({ph})")).scalar() or 0
    return total


def check_fk_orphans(conn: Connection, tables: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """
    Busca filas hijas cuyo padre FK ya no existe (orphans).

    Retorna lista vacía si no hay orphans.
    """
    tables_set = set(tables or AFFECTED_TABLES)
    child_placeholders = ",".join(f"'{t}'" for t in sorted(tables_set))
    fk_rows = conn.execute(
        text(
            f"""
            SELECT
                kcu.TABLE_NAME AS child_table,
                kcu.COLUMN_NAME AS child_column,
                kcu.REFERENCED_TABLE_NAME AS parent_table,
                kcu.REFERENCED_COLUMN_NAME AS parent_column
            FROM information_schema.KEY_COLUMN_USAGE kcu
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
              AND kcu.TABLE_NAME IN ({child_placeholders})
            """
        )
    ).fetchall()

    orphans: list[dict[str, Any]] = []
    for row in fk_rows:
        child_table, child_col, parent_table, parent_col = (
            row[0],
            row[1],
            row[2],
            row[3],
        )
        orphan_count = conn.execute(
            text(
                f"""
                SELECT COUNT(*) FROM `{child_table}` c
                LEFT JOIN `{parent_table}` p ON c.`{child_col}` = p.`{parent_col}`
                WHERE c.`{child_col}` IS NOT NULL AND p.`{parent_col}` IS NULL
                """
            )
        ).scalar() or 0
        if orphan_count:
            sample = conn.execute(
                text(
                    f"""
                    SELECT c.`{child_col}` AS parent_ref
                    FROM `{child_table}` c
                    LEFT JOIN `{parent_table}` p ON c.`{child_col}` = p.`{parent_col}`
                    WHERE c.`{child_col}` IS NOT NULL AND p.`{parent_col}` IS NULL
                    LIMIT 3
                    """
                )
            ).fetchall()
            orphans.append(
                {
                    "child_table": child_table,
                    "child_column": child_col,
                    "parent_table": parent_table,
                    "orphan_count": orphan_count,
                    "sample_parent_refs": [r[0] for r in sample],
                }
            )
    return orphans


def preflight_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    confirm_database: str,
    backup_confirmed: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Validación inmediatamente previa a BEGIN/DELETE.

    Raises ApplyAbortError si cualquier check falla.
    """
    errors: list[str] = []
    db_name = conn.execute(text("SELECT DATABASE()")).scalar()
    if db_name != confirm_database:
        errors.append(f"DATABASE()={db_name} != {confirm_database}")
    if not dry_run and not backup_confirmed:
        errors.append("--backup-confirmed requerido para apply")

    if execution_manifest.get("database") and execution_manifest["database"] != db_name:
        errors.append("execution manifest database mismatch")

    if not verify_manifest_hash(execution_manifest):
        errors.append("execution_manifest_hash inválido")

    prot_hash = protected_manifest.get("manifest_sha256")
    if prot_hash and execution_manifest.get("source_protected_manifest_hash") != prot_hash:
        errors.append("protected manifest hash mismatch")

    alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    if execution_manifest.get("alembic_revision") and execution_manifest["alembic_revision"] != alembic:
        errors.append(f"alembic drift: db={alembic} manifest={execution_manifest['alembic_revision']}")

    snapshot = execution_manifest.get("precondition_snapshot", {})
    snap_counts = snapshot.get("counts", {})
    for entity, expected in snap_counts.items():
        table = _table_for_entity(entity)
        actual = _count_table(conn, table)
        if actual != expected:
            errors.append(f"baseline drift {entity}: db={actual} snapshot={expected}")

    execution_ids = load_execution_sets(execution_manifest)
    protected = load_protected_sets(protected_manifest)
    conflicts = hard_conflict_check(execution_ids, protected, critical_entities=CRITICAL_PROTECTED_ENTITIES)
    if conflicts:
        errors.append(f"execution ∩ protected: {conflicts[:3]}")

    blocked = execution_manifest.get("blocked_preserve", {})
    for entity in ("actuaciones", "iniciador_ruta", "relevamiento", "denuncia", "orden_trabajo", "users"):
        blocked_ids = set(blocked.get(entity, []))
        inter = blocked_ids & execution_ids.get(entity, set())
        if inter:
            errors.append(f"blocked∩execution {entity}: {len(inter)} IDs")

    for forbidden in FORBIDDEN_ENTITIES:
        if execution_ids.get(forbidden):
            errors.append(f"{forbidden} en execution manifest")

    engine_audit = audit_table_engines(conn)
    if not engine_audit["apply_enabled"]:
        errors.append(f"non-InnoDB tables: {engine_audit['non_transactional']}")

    stale_exec: list[dict] = []
    for entity, ids in execution_ids.items():
        if not ids:
            continue
        table = _table_for_entity(entity)
        missing = validate_ids_exist(conn, table, ids, label=entity)
        if missing:
            stale_exec.extend(missing[:5])

    if stale_exec:
        errors.append(f"execution IDs stale/missing: {stale_exec[:5]}")

    virtual = VirtualDeleteState()
    for entity, ids in execution_ids.items():
        virtual.add_explicit(entity, ids)
    fk_validation = validate_execution_plan(conn, execution_ids, virtual)
    if not fk_validation["valid"]:
        errors.append(f"FK blockers: {fk_validation.get('blocked_ids_by_entity')}")

    try:
        _assert_admin_and_fabian(conn)
    except ApplyAbortError as exc:
        errors.append(str(exc))

    inspector_count = conn.execute(text("SELECT COUNT(*) FROM inspector")).scalar() or 0
    if inspector_count != 24:
        errors.append(f"inspectores count {inspector_count} != 24")

    if errors:
        raise ApplyAbortError("; ".join(errors))

    return {
        "status": "PREFLIGHT_OK",
        "database": db_name,
        "alembic_revision": alembic,
        "engine_audit": engine_audit,
        "execution_counts": {e: len(execution_ids.get(e, set())) for e in EXECUTION_ENTITIES},
        "fk_validation_status": fk_validation["status"],
    }


def dry_run_execution_manifest(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    confirm_database: str,
) -> dict[str, Any]:
    """Dry-run contra execution manifest congelado: valida sin writes."""
    preflight = preflight_apply(
        conn,
        execution_manifest,
        protected_manifest,
        confirm_database=confirm_database,
        dry_run=True,
    )
    execution_ids = load_execution_sets(execution_manifest)
    manifest_counts = execution_manifest.get("counts", {})

    count_checks = []
    for entity in EXECUTION_ENTITIES:
        expected = manifest_counts.get(entity, len(execution_ids.get(entity, set())))
        actual_ids = len(execution_ids.get(entity, set()))
        count_checks.append(
            {
                "entity": entity,
                "manifest_count": expected,
                "parsed_ids": actual_ids,
                "match": expected == actual_ids,
            }
        )

    return {
        "mode": "DRY_RUN_EXECUTION_MANIFEST",
        "writes_executed": False,
        "preflight": preflight,
        "count_checks": count_checks,
        "all_counts_match": all(c["match"] for c in count_checks),
        "frozen_counts": manifest_counts,
    }


def _delete_explicit(
    conn: Connection,
    table: str,
    ids: set[int],
) -> int:
    """DELETE explícito por chunks; retorna filas afectadas."""
    if not ids:
        return 0
    deleted = 0
    for chunk in _chunk_ids(ids, 500):
        ph = ",".join(str(x) for x in chunk)
        result = conn.execute(text(f"DELETE FROM `{table}` WHERE id IN ({ph})"))
        deleted += result.rowcount or 0
    return deleted


def _assert_protected_exist(
    conn: Connection,
    protected_manifest: dict[str, Any],
    entities: tuple[str, ...],
) -> None:
    protected = load_protected_sets(protected_manifest)
    for entity in entities:
        ids = protected.get(entity, set())
        if not ids:
            continue
        table = _table_for_entity(entity)
        missing = validate_ids_exist(conn, table, ids, label=entity)
        if missing:
            raise ApplyAbortError(f"protected {entity} missing: {missing[:3]}")


def _assert_blocked_preserved(
    conn: Connection,
    execution_manifest: dict[str, Any],
) -> None:
    blocked = execution_manifest.get("blocked_preserve", {})
    for entity, id_list in blocked.items():
        if entity in ("protected_iniciadores", "wrapper_protected_count"):
            continue
        ids = set(id_list) if isinstance(id_list, list) else set()
        if not ids:
            continue
        table = _table_for_entity(entity) if entity in ENTITY_TABLE else None
        if not table:
            continue
        exist = _count_ids_exist(conn, table, ids)
        if exist != len(ids):
            raise ApplyAbortError(f"blocked {entity}: expected {len(ids)} exist, found {exist}")


def _assert_execution_gone(conn: Connection, execution_ids: dict[str, set[int]]) -> None:
    for entity, ids in execution_ids.items():
        if not ids:
            continue
        table = _table_for_entity(entity)
        remain = _count_ids_exist(conn, table, ids)
        if remain:
            raise ApplyAbortError(f"execution {entity}: {remain} IDs still exist")


def _assert_admin_and_fabian(conn: Connection) -> None:
    admin = conn.execute(
        text("SELECT id FROM users WHERE LOWER(username) = 'admin' LIMIT 1")
    ).fetchone()
    if not admin:
        raise ApplyAbortError("admin user missing")

    fabian = conn.execute(
        text("SELECT id FROM relevador WHERE nombre LIKE '%Fabian Esquivel%' LIMIT 1")
    ).fetchone()
    if not fabian:
        raise ApplyAbortError("Fabian Esquivel relevador missing")


def _count_protected_preserved(
    conn: Connection,
    protected_manifest: dict[str, Any],
) -> dict[str, dict[str, int]]:
    """Conteos de IDs protegidos que siguen existiendo."""
    protected = load_protected_sets(protected_manifest)
    result: dict[str, dict[str, int]] = {}
    for entity in PROTECTED_ENTITIES_ALL:
        ids = protected.get(entity, set())
        if not ids:
            result[entity] = {"expected": 0, "found": 0}
            continue
        table = _table_for_entity(entity)
        found = _count_ids_exist(conn, table, ids)
        result[entity] = {"expected": len(ids), "found": found}
        if found != len(ids):
            raise ApplyAbortError(f"protected {entity}: expected {len(ids)}, found {found}")
    return result


def _assert_expected_post_counts(conn: Connection) -> dict[str, int]:
    """Valida conteos post-delete esperados FASE 1 antes de COMMIT."""
    actual: dict[str, int] = {}
    errors: list[str] = []
    for entity, expected in EXPECTED_POST_COUNTS.items():
        table = _table_for_entity(entity)
        count = _count_table(conn, table)
        actual[entity] = count
        if count != expected:
            errors.append(f"{entity}: actual={count} expected={expected}")
    if errors:
        raise ApplyAbortError("post-count mismatch: " + "; ".join(errors))
    return actual


def _assert_zero_delete_tables(conn: Connection, tables: tuple[str, ...], counts_before: dict[str, int]) -> None:
    for table in tables:
        after = _count_table(conn, table)
        if after != counts_before.get(table, after):
            raise ApplyAbortError(f"{table} count changed: before={counts_before.get(table)} after={after}")


def apply_phase1_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    confirm_database: str,
    backup_path: str | None = None,
    backup_size: int | None = None,
    backup_hash: str | None = None,
) -> dict[str, Any]:
    """
    Ejecuta DELETE en transacción única con rollback ante cualquier fallo.

    NO invocar sin backup confirmado y preflight OK.
    """
    started_at = datetime.now().isoformat()
    execution_ids = load_execution_sets(execution_manifest)
    delete_order = execution_manifest.get("delete_order") or list(PHASE1_DELETE_ORDER_V3)

    counts_before = {t: _count_table(conn, t) for t in AFFECTED_TABLES}
    cascade_before = {t: _count_table(conn, t) for t in CASCADE_OBSERVE_TABLES}
    protected_tables_before = {
        "domicilio": _count_table(conn, "domicilio"),
        "contribuyente": _count_table(conn, "contribuyente"),
        "expediente": _count_table(conn, "expediente"),
        "oficio": _count_table(conn, "oficio"),
    }

    preflight_apply(
        conn,
        execution_manifest,
        protected_manifest,
        confirm_database=confirm_database,
        backup_confirmed=True,
    )

    explicit_deleted: dict[str, int] = {}
    committed = False
    transaction_status = "ROLLED_BACK"
    protected_preserved: dict[str, dict[str, int]] = {}
    expected_post_counts: dict[str, int] = {}
    inspector_count = 0

    if conn.in_transaction():
        conn.rollback()

    trans = conn.begin()
    try:
        for entity in delete_order:
            ids = execution_ids.get(entity, set())
            if not ids:
                explicit_deleted[entity] = 0
                continue
            table = _table_for_entity(entity)
            before = _count_ids_exist(conn, table, ids)
            if before != len(ids):
                raise ApplyAbortError(f"{entity}: expected {len(ids)} exist pre-delete, found {before}")
            expected_count = len(ids)
            deleted = _delete_explicit(conn, table, ids)
            explicit_deleted[entity] = deleted
            manifest_expected = execution_manifest.get("counts", {}).get(entity, expected_count)
            if deleted != manifest_expected:
                raise ApplyAbortError(
                    f"{entity}: deleted={deleted} != manifest={manifest_expected}"
                )

        _assert_execution_gone(conn, execution_ids)
        protected_preserved = _count_protected_preserved(conn, protected_manifest)
        _assert_blocked_preserved(conn, execution_manifest)
        _assert_admin_and_fabian(conn)
        _assert_zero_delete_tables(conn, ("domicilio", "contribuyente", "expediente", "oficio"), protected_tables_before)
        expected_post_counts = _assert_expected_post_counts(conn)

        inspector_count = conn.execute(text("SELECT COUNT(*) FROM inspector")).scalar() or 0
        if inspector_count != 24:
            raise ApplyAbortError(f"inspectores post-delete {inspector_count} != 24")

        orphans = check_fk_orphans(conn)
        if orphans:
            raise ApplyAbortError(f"FK orphans detected: {orphans[:5]}")

        trans.commit()
        committed = True
        transaction_status = "COMMITTED"
    except Exception:
        trans.rollback()
        raise
    finally:
        if not committed and trans.is_active:
            trans.rollback()

    counts_after = {t: _count_table(conn, t) for t in AFFECTED_TABLES}
    cascade_observed = {
        t: cascade_before[t] - _count_table(conn, t) for t in CASCADE_OBSERVE_TABLES
    }
    qa_counts = {entity: _count_table(conn, _table_for_entity(entity)) for entity in EXPECTED_POST_COUNTS}

    return {
        "database": confirm_database,
        "backup_path": backup_path,
        "backup_size": backup_size,
        "backup_hash": backup_hash,
        "backup_timestamp": started_at,
        "execution_manifest_hash": execution_manifest.get("execution_manifest_hash"),
        "source_protected_manifest_hash": execution_manifest.get("source_protected_manifest_hash"),
        "started_at": started_at,
        "finished_at": datetime.now().isoformat(),
        "counts_before": counts_before,
        "explicit_deleted": explicit_deleted,
        "cascade_observed": cascade_observed,
        "protected_preserved": protected_preserved,
        "protected_deleted": 0,
        "expected_post_counts": expected_post_counts,
        "blocked_preserved": {
            k: len(v) if isinstance(v, list) else v
            for k, v in execution_manifest.get("blocked_preserve", {}).items()
        },
        "counts_after": counts_after,
        "qa_counts_after": qa_counts,
        "orphan_checks": check_fk_orphans(conn),
        "transaction_status": transaction_status,
        "committed": committed,
        "writes_executed": committed,
        "inspectors_count": inspector_count,
    }
