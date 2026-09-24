"""Planificador dry-run FASE 1 con simulación secuencial v2."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import (
    CRITICAL_PROTECTED_ENTITIES,
    PHASE1_NO_AUTO_DELETE,
)
from app.domains.predeploy_cleanup.fk_graph import (
    classify_delete_mode,
    load_fk_edges,
    topological_delete_order,
)
from app.domains.predeploy_cleanup.manifest_io import entity_ids, validate_ids_exist
from app.domains.predeploy_cleanup.phase1_candidates import build_phase1_cleanup_entities
from app.domains.predeploy_cleanup.protected import (
    expand_protected_indirect,
    hard_conflict_check,
    load_protected_sets,
)
from app.domains.predeploy_cleanup.sequential_simulator import simulate_phase1


def analyze_wrappers(conn: Connection, protected_act_ids: set[int]) -> dict[str, Any]:
    """Analiza TEST_WRAPPER_AROUND_REAL_DATA e iniciadores asociados."""
    if not protected_act_ids:
        return {"wrappers": [], "iniciadores_candidato_test": [], "iniciadores_proteger": []}
    ph = ",".join(str(i) for i in sorted(protected_act_ids))
    wrappers = conn.execute(
        text(
            f"""
            SELECT ri.id AS ruta_item_id, ri.ruta_trabajo_id, ri.iniciador_ruta_id,
                   ri.actuacion_id, rt.created_by_user_id, u.email AS ruta_creator_email,
                   ir.created_by_user_id AS iniciador_created_by,
                   ir.tipo_iniciador, ir.relevamiento_id, ir.denuncia_id,
                   ir.notificacion_id, ir.comprobacion_id, ir.oficio_id, ir.actuacion_id AS ini_actuacion_id
            FROM ruta_item ri
            JOIN ruta_trabajo rt ON rt.id = ri.ruta_trabajo_id
            LEFT JOIN users u ON u.id = rt.created_by_user_id
            LEFT JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id
            WHERE ri.actuacion_id IN ({ph})
              AND (u.email LIKE '%@t.local' OR u.email LIKE '%@test.local')
            """
        )
    ).fetchall()

    wrapper_list = []
    ini_test: list[int] = []
    ini_protect: list[int] = []
    for w in wrappers:
        row = dict(w._mapping)
        row["ruta_clasificacion"] = "CONFIRMADO_TEST"
        row["actuacion_clasificacion"] = "PROTECTED_REAL"
        ini_id = row.get("iniciador_ruta_id")
        if ini_id:
            if row.get("ini_actuacion_id") in protected_act_ids:
                ini_protect.append(ini_id)
                row["iniciador_clasificacion"] = "PROTEGER_FLUJO_REAL"
            elif row.get("notificacion_id") or row.get("comprobacion_id") or row.get("oficio_id"):
                ini_protect.append(ini_id)
                row["iniciador_clasificacion"] = "PROTEGER_FLUJO_REAL_ADMIN"
            else:
                ini_test.append(ini_id)
                row["iniciador_clasificacion"] = "DELETABLE_PHASE1_CANDIDATE"
        wrapper_list.append(row)

    return {
        "wrappers": wrapper_list,
        "wrapper_count": len(wrapper_list),
        "iniciadores_candidato_test": sorted(set(ini_test)),
        "iniciadores_proteger": sorted(set(ini_protect)),
    }


def count_table(conn: Connection, table: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar() or 0


def plan_phase1_dry_run(
    conn: Connection,
    protected_manifest: dict[str, Any],
    cleanup_manifest: dict[str, Any],
) -> dict[str, Any]:
    """
    Ejecuta dry-run FASE 1 v2 con simulación secuencial sin writes.

    Raises ValueError si hard conflict manifest o simulación inválida.
    """
    protected = load_protected_sets(protected_manifest)
    protected = expand_protected_indirect(conn, protected)

    cleanup: dict[str, set[int]] = {
        entity: entity_ids(cleanup_manifest, entity)
        for entity in cleanup_manifest.get("entities", {})
    }

    conflicts = hard_conflict_check(cleanup, protected, critical_entities=CRITICAL_PROTECTED_ENTITIES)
    if conflicts:
        raise ValueError(f"HARD_CONFLICT_ABORT: {conflicts}")

    stale_protected: list[dict[str, Any]] = []
    table_map = {
        "orden_trabajo": "orden_trabajo",
        "actuaciones": "actuaciones",
        "inspeccion": "inspeccion",
        "notificacion": "notificacion",
        "comprobacion": "comprobacion",
        "oficio": "oficio",
        "expediente": "expediente",
    }
    for entity, table in table_map.items():
        stale_protected.extend(
            validate_ids_exist(conn, table, protected.get(entity, set()), label=entity)
        )

    edges = load_fk_edges(conn)
    plan_tables = [
        "acta_inspeccion_item",
        "actuaciones_inspector",
        "notificacion_motivo",
        "clausura",
        "decomiso",
        "inspeccion",
        "ruta_grupo_inspector",
        "ruta_item",
        "ruta_pool_dia",
        "ruta_grupo",
        "ruta_trabajo",
        "denuncia",
        "relevamiento_relevador",
        "relevamiento",
        "orden_trabajo",
        "juzgado_catalogo",
        "rubro",
        "relevador",
        "users",
    ]
    delete_order = topological_delete_order(plan_tables, edges)

    wrapper_analysis = analyze_wrappers(conn, protected.get("actuaciones", set()))
    simulation = simulate_phase1(conn, cleanup, protected, wrapper_analysis)

    if not simulation["dry_run_valid"]:
        closure_conflicts = simulation["protection_closure"]["conflicts"]
        assertion_invalid = simulation["protected_assertions"]["invalid_keys"]
        exec_invalid = simulation.get("execution_validation", {})
        raise ValueError(
            f"DRY_RUN_INVALID: closure_conflicts={closure_conflicts}, "
            f"assertion_failures={assertion_invalid}, "
            f"execution={exec_invalid.get('status')}"
        )

    alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    user_audit = simulation["user_audit"]

    return {
        "version": simulation.get("version", "cleanup_phase1_dry_run_v3"),
        "delete_order": simulation.get("delete_order", delete_order),
        "iniciador_ruta_fks_outgoing": simulation.get("iniciador_ruta_fks_outgoing", []),
        "iniciador_ruta_fks_incoming": simulation.get("iniciador_ruta_fks_incoming", []),
        "blocked_by_surviving_fk": simulation.get("blocked_by_surviving_fk", {}),
        "execution_validation": simulation.get("execution_validation", {}),
        "executability_table": simulation.get("executability_table", []),
        "iniciador_classification": simulation.get("iniciador_classification", {}),
        "iniciador_wrapper_incorporated": simulation.get("iniciador_wrapper_incorporated", {}),
        "denuncia_audit": simulation.get("denuncia_audit", {}),
        "relevamiento_audit": simulation.get("relevamiento_audit", {}),
        "actuaciones_blocked_by_iniciador": simulation.get("actuaciones_blocked_by_iniciador", {}),
        "v2_contradiction_explanation": simulation.get("v2_contradiction_explanation", ""),
        "database": conn.execute(text("SELECT DATABASE()")).scalar(),
        "alembic_revision": alembic,
        "generated_at": datetime.now().isoformat(),
        "writes_executed": False,
        "counts_before": simulation["counts_before"],
        "counts_after_exact": simulation["counts_after_exact"],
        "summary_table": simulation["summary_table"],
        "explicit_deletes": simulation["explicit_deletes"],
        "cascade_deletes": simulation["cascade_deletes"],
        "deletable_now": simulation["deletable_now"],
        "deletable_after_dependencies": simulation["deletable_after_dependencies"],
        "blocked_after_phase1": simulation["blocked_after_phase1"],
        "user_audit": user_audit,
        "users_summary": {
            "users_before": user_audit["users_before"],
            "cleanup_candidates": user_audit["cleanup_candidates"],
            "deletable_now": user_audit["deletable_before_phase1"],
            "deletable_after_dependencies": user_audit[
                "deletable_after_phase1_dependencies_removed"
            ],
            "blocked_after_phase1": user_audit["blocked_after_phase1"],
            "users_after_exact": user_audit["users_after_exact"],
            "blocked_only_by_planned_deletes": user_audit[
                "blocked_only_by_rows_deleted_in_phase1"
            ],
            "blocked_by_surviving_rows": user_audit["blocked_by_rows_surviving_phase1"],
            "protected_users": len(user_audit["protected_users"]),
            "indeterminate_users": user_audit["indeterminate_users"],
        },
        "protection_closure": simulation["protection_closure"],
        "protected_assertions": simulation["protected_assertions"],
        "conflicts": conflicts,
        "stale_protected_ids": stale_protected,
        "delete_order": delete_order,
        "fk_delete_modes_sample": [
            {
                "child": e.child_table,
                "parent": e.parent_table,
                "rule": e.delete_rule,
                "mode": classify_delete_mode(e.delete_rule),
            }
            for e in edges
            if e.parent_table in ("actuaciones", "ruta_trabajo", "iniciador_ruta", "orden_trabajo")
        ][:30],
        "protection_report": {
            "protected_actuaciones": len(protected.get("actuaciones", set())),
            "cleanup_actuaciones": len(cleanup.get("actuaciones", set())),
            "intersection_actuaciones": len(
                cleanup.get("actuaciones", set()) & protected.get("actuaciones", set())
            ),
            "test_wrappers_around_real": wrapper_analysis["wrapper_count"],
            "actuaciones_final_cleanup": simulation["actuaciones_final_cleanup_count"],
            "actuaciones_removed_cascade_conflict": len(
                simulation["actuaciones_removed_from_cleanup"]
            ),
        },
        "test_wrappers_around_real_data": wrapper_analysis,
        "orden_trabajo_recalc": simulation["orden_trabajo_recalc"],
        "juzgado_recalc": simulation["juzgado_recalc"],
        "relevador_recalc": simulation["relevador_recalc"],
        "document_orphan_analysis": simulation["document_orphan_analysis"],
        "orphan_candidates_phase2": cleanup_manifest.get("entities", {}).get("_meta", {})
        or cleanup_manifest.get("meta", {}),
        "blocked_phase2_only": {
            entity: {"count": len(ids), "reason": "PHASE2_ONLY"}
            for entity, ids in cleanup.items()
            if entity in PHASE1_NO_AUTO_DELETE
        },
        "virtual_state": simulation["virtual_state"],
        "dry_run_valid": simulation["dry_run_valid"],
    }


def build_cleanup_manifest_from_db(
    conn: Connection,
    protected_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Genera cleanup manifest congelado desde DB (SELECT only)."""
    protected = load_protected_sets(protected_manifest)
    protected = expand_protected_indirect(conn, protected)
    entities = build_phase1_cleanup_entities(conn, protected)
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "phase": 1,
        "mode": "CLEANUP_MANIFEST_FROZEN",
        "entities": {k: v for k, v in entities.items() if not k.startswith("_")},
        "meta": entities.get("_meta", {}),
        "baseline_counts": {
            "actuaciones": count_table(conn, "actuaciones"),
            "users": count_table(conn, "users"),
            "ruta_trabajo": count_table(conn, "ruta_trabajo"),
        },
    }
    return manifest
