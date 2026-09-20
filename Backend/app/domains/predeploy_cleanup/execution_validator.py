"""Validación de ejecutabilidad FK a nivel de IDs para FASE 1."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.fk_graph import ForeignKeyEdge, load_fk_edges, topological_delete_order
from app.domains.predeploy_cleanup.sequential_simulator import (
    ENTITY_TABLE,
    VirtualDeleteState,
    _chunk_ids,
    _entity_for_table,
    _fetch_ids,
    _table_for_entity,
)

PHASE1_TABLES = [
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
]

SOURCE_COLUMNS = (
    "relevamiento_id",
    "denuncia_id",
    "notificacion_id",
    "comprobacion_id",
    "oficio_id",
    "actuacion_id",
)


def load_iniciador_ruta_outgoing_fks(conn: Connection) -> list[dict[str, str]]:
    """FK salientes de iniciador_ruta (hacia sources) desde INFORMATION_SCHEMA."""
    rows = conn.execute(
        text(
            """
            SELECT
                kcu.TABLE_NAME AS child_table,
                kcu.COLUMN_NAME AS child_column,
                kcu.REFERENCED_TABLE_NAME AS parent_table,
                kcu.REFERENCED_COLUMN_NAME AS parent_column,
                rc.DELETE_RULE AS delete_rule
            FROM information_schema.KEY_COLUMN_USAGE kcu
            JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
              ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
             AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.TABLE_NAME = 'iniciador_ruta'
              AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            """
        )
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def load_iniciador_ruta_incoming_fks(conn: Connection) -> list[dict[str, str]]:
    """FK entrantes hacia iniciador_ruta (ruta_item, ruta_pool_dia)."""
    rows = conn.execute(
        text(
            """
            SELECT
                kcu.TABLE_NAME AS child_table,
                kcu.COLUMN_NAME AS child_column,
                kcu.REFERENCED_TABLE_NAME AS parent_table,
                kcu.REFERENCED_COLUMN_NAME AS parent_column,
                rc.DELETE_RULE AS delete_rule
            FROM information_schema.KEY_COLUMN_USAGE kcu
            JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
              ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
             AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.REFERENCED_TABLE_NAME = 'iniciador_ruta'
            """
        )
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def load_test_iniciador_ids(conn: Connection) -> set[int]:
    """Iniciadores creados por usuario test (universo ~3583)."""
    return _fetch_ids(
        conn,
        f"""
        SELECT ir.id FROM iniciador_ruta ir
        JOIN users u ON u.id = ir.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )


def _iniciador_rows(conn: Connection, ini_ids: set[int]) -> dict[int, dict]:
    if not ini_ids:
        return {}
    result: dict[int, dict] = {}
    for chunk in _chunk_ids(ini_ids):
        ph = ",".join(str(i) for i in chunk)
        rows = conn.execute(
            text(
                f"""
                SELECT id, tipo_iniciador, created_by_user_id,
                       relevamiento_id, denuncia_id, notificacion_id,
                       comprobacion_id, oficio_id, actuacion_id, deleted_at
                FROM iniciador_ruta WHERE id IN ({ph})
                """
            )
        ).fetchall()
        for r in rows:
            result[r[0]] = dict(r._mapping)
    return result


def _surviving_route_refs_for_iniciador(
    conn: Connection,
    ini_id: int,
    deleted_ruta_items: set[int],
    deleted_pool: set[int],
) -> tuple[int, int]:
    """Cuenta ruta_item / ruta_pool_dia sobrevivientes que referencian iniciador."""
    items = _fetch_ids(
        conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {ini_id}"
    )
    pools = _fetch_ids(
        conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {ini_id}"
    )
    return len(items - deleted_ruta_items), len(pools - deleted_pool)


def classify_iniciadores_test(
    conn: Connection,
    protected_all: dict[str, set[int]],
    wrapper_analysis: dict[str, Any],
    deleted_ruta_items: set[int],
    deleted_pool: set[int],
    cleanup_act_ids: set[int] | None = None,
) -> dict[str, Any]:
    """
    Clasifica iniciadores test en buckets finales.

    Incorpora wrappers 64: 36 deletable + 27 protected (no re-inferir).
    """
    test_ids = load_test_iniciador_ids(conn)
    protected_ini = set(wrapper_analysis.get("iniciadores_proteger", []))
    wrapper_deletable = set(wrapper_analysis.get("iniciadores_candidato_test", []))

    delete_phase1: set[int] = set()
    protected_real: set[int] = set(protected_ini)
    blocked_indeterminate: set[int] = set()
    fuera_alcance: set[int] = set()

    rows = _iniciador_rows(conn, test_ids)
    prot_notif = protected_all.get("notificacion", set())
    prot_comp = protected_all.get("comprobacion", set())
    prot_oficio = protected_all.get("oficio", set())
    prot_act = protected_all.get("actuaciones", set())

    for ini_id in sorted(test_ids):
        row = rows.get(ini_id)
        if not row:
            fuera_alcance.add(ini_id)
            continue
        if ini_id in protected_ini:
            protected_real.add(ini_id)
            continue

        # Source administrativo real → bloquear
        if row.get("notificacion_id") in prot_notif:
            blocked_indeterminate.add(ini_id)
            continue
        if row.get("comprobacion_id") in prot_comp:
            blocked_indeterminate.add(ini_id)
            continue
        if row.get("oficio_id") in prot_oficio:
            blocked_indeterminate.add(ini_id)
            continue
        if row.get("actuacion_id") in prot_act:
            blocked_indeterminate.add(ini_id)
            continue

        act_id = row.get("actuacion_id")
        if act_id:
            if act_id in prot_act:
                blocked_indeterminate.add(ini_id)
                continue
            cleanup_acts = cleanup_act_ids or set()
            if act_id not in cleanup_acts:
                blocked_indeterminate.add(ini_id)
                continue

        surv_items, surv_pools = _surviving_route_refs_for_iniciador(
            conn, ini_id, deleted_ruta_items, deleted_pool
        )
        if surv_items > 0 or surv_pools > 0:
            blocked_indeterminate.add(ini_id)
            continue

        # Wrapper candidatos ya validados en v2
        if ini_id in wrapper_deletable:
            delete_phase1.add(ini_id)
            continue

        # Test sin vínculo admin y sin refs de ruta sobrevivientes
        delete_phase1.add(ini_id)

    delete_phase1.update(wrapper_deletable - protected_real - blocked_indeterminate)

    # Buckets disjuntos
    protected_real -= delete_phase1
    protected_real -= blocked_indeterminate
    delete_phase1 -= protected_real
    delete_phase1 -= blocked_indeterminate
    blocked_indeterminate -= protected_real
    blocked_indeterminate -= delete_phase1

    all_classified = delete_phase1 | protected_real | blocked_indeterminate
    fuera_alcance = test_ids - all_classified

    return {
        "test_candidates_total": len(test_ids),
        "delete_phase1": sorted(delete_phase1),
        "protected_real": sorted(protected_real),
        "blocked_indeterminate": sorted(blocked_indeterminate),
        "fuera_de_alcance": sorted(fuera_alcance),
        "delete_phase1_count": len(delete_phase1),
        "protected_real_count": len(protected_real),
        "blocked_indeterminate_count": len(blocked_indeterminate),
        "fuera_de_alcance_count": len(fuera_alcance),
    }


def _surviving_iniciadores_for_source(
    conn: Connection,
    source_column: str,
    source_id: int,
    planned_ini_delete: set[int],
) -> list[dict]:
    rows = conn.execute(
        text(
            f"""
            SELECT id, tipo_iniciador, created_by_user_id
            FROM iniciador_ruta
            WHERE `{source_column}` = :sid
            """
        ),
        {"sid": source_id},
    ).fetchall()
    surviving = []
    for r in rows:
        if r[0] not in planned_ini_delete:
            surviving.append(
                {
                    "iniciador_id": r[0],
                    "tipo_iniciador": r[1],
                    "created_by_user_id": r[2],
                }
            )
    return surviving


def filter_parents_blocked_by_iniciador(
    conn: Connection,
    parent_entity: str,
    parent_column: str,
    candidate_ids: set[int],
    planned_ini_delete: set[int],
) -> tuple[set[int], set[int], list[dict]]:
    """Filtra parents cuyo delete está bloqueado por iniciador RESTRICT sobreviviente."""
    deletable: set[int] = set()
    blocked: set[int] = set()
    detail: list[dict] = []
    for pid in sorted(candidate_ids):
        surviving = _surviving_iniciadores_for_source(conn, parent_column, pid, planned_ini_delete)
        if surviving:
            blocked.add(pid)
            detail.append(
                {
                    f"{parent_entity}_id": pid,
                    "status": "BLOCKED_BY_SURVIVING_INICIADOR",
                    "surviving_iniciadores": surviving[:5],
                }
            )
        else:
            deletable.add(pid)
    return deletable, blocked, detail


def filter_actuaciones_blocked_by_iniciador(
    conn: Connection,
    act_candidates: set[int],
    planned_ini_delete: set[int],
) -> tuple[set[int], set[int], list[dict]]:
    return filter_parents_blocked_by_iniciador(
        conn, "actuaciones", "actuacion_id", act_candidates, planned_ini_delete
    )


def _child_pk_column(conn: Connection, table: str) -> str:
    row = conn.execute(
        text(
            """
            SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :tbl
              AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
            LIMIT 1
            """
        ),
        {"tbl": table},
    ).fetchone()
    return row[0] if row else "id"


def find_surviving_child_refs(
    conn: Connection,
    edge: ForeignKeyEdge,
    parent_ids: set[int],
    virtual: VirtualDeleteState,
) -> list[dict]:
    """Filas child que referencian parent y NO están en virtual delete."""
    if not parent_ids:
        return []
    pk_col = _child_pk_column(conn, edge.child_table)
    blockers: list[dict] = []
    for chunk in _chunk_ids(parent_ids):
        ph = ",".join(str(i) for i in chunk)
        try:
            rows = conn.execute(
                text(
                    f"""
                    SELECT `{pk_col}`, `{edge.child_column}`
                    FROM `{edge.child_table}`
                    WHERE `{edge.child_column}` IN ({ph})
                    """
                )
            ).fetchall()
        except Exception:
            rows = conn.execute(
                text(
                    f"""
                    SELECT `{edge.child_column}`
                    FROM `{edge.child_table}`
                    WHERE `{edge.child_column}` IN ({ph})
                    """
                )
            ).fetchall()
            for r in rows:
                parent_id = r[0]
                blockers.append(
                    {
                        "parent_table": edge.parent_table,
                        "parent_id": parent_id,
                        "child_table": edge.child_table,
                        "child_column": edge.child_column,
                        "child_id": None,
                        "delete_rule": edge.delete_rule,
                    }
                )
            continue

        deleted_children = virtual.all_deleted(edge.child_table)
        for child_id, parent_id in rows:
            if child_id in deleted_children:
                continue
            blockers.append(
                {
                    "parent_table": edge.parent_table,
                    "parent_id": parent_id,
                    "child_table": edge.child_table,
                    "child_column": edge.child_column,
                    "child_id": child_id,
                    "delete_rule": edge.delete_rule,
                }
            )
    return blockers


def validate_execution_plan(
    conn: Connection,
    explicit_by_entity: dict[str, set[int]],
    virtual: VirtualDeleteState,
    edges: list[ForeignKeyEdge] | None = None,
) -> dict[str, Any]:
    """
    Pre-flight reusable: valida que cada planned delete no tiene child RESTRICT sobreviviente.

    Raises ValueError si hay bloqueos no resueltos (para futuro --apply).
    """
    if edges is None:
        edges = load_fk_edges(conn)

    blocked_by_fk: dict[str, list[dict]] = {}
    blocked_ids: dict[str, set[int]] = {}

    restrict_edges = [
        e for e in edges if e.delete_rule in ("RESTRICT", "NO ACTION")
    ]

    for entity, parent_ids in explicit_by_entity.items():
        if not parent_ids:
            continue
        parent_table = _table_for_entity(entity)
        entity_blockers: list[dict] = []
        entity_blocked: set[int] = set()

        child_edges = [e for e in restrict_edges if e.parent_table == parent_table]
        for edge in child_edges:
            refs = find_surviving_child_refs(conn, edge, parent_ids, virtual)
            for ref in refs:
                entity_blocked.add(ref["parent_id"])
                entity_blockers.append(ref)

        if entity_blockers:
            blocked_by_fk[entity] = entity_blockers[:100]
            blocked_ids[entity] = entity_blocked

    # Filtrar explicit plan
    adjusted: dict[str, set[int]] = {}
    for entity, ids in explicit_by_entity.items():
        bad = blocked_ids.get(entity, set())
        adjusted[entity] = ids - bad

    valid = not any(blocked_ids.values())
    return {
        "valid": valid,
        "blocked_by_surviving_fk": blocked_by_fk,
        "blocked_ids_by_entity": {k: sorted(v) for k, v in blocked_ids.items()},
        "adjusted_explicit": adjusted,
        "status": "EXECUTION_PLAN_VALID" if valid else "EXECUTION_PLAN_BLOCKED",
    }


PHASE1_DELETE_ORDER_V3 = [
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
]


def build_delete_order(edges: list[ForeignKeyEdge]) -> list[str]:
    """Orden de borrado FASE 1 v3 (hijos→padres, iniciador antes de sources RESTRICT)."""
    topo = topological_delete_order(PHASE1_TABLES, edges)
    # Garantizar secuencia crítica iniciador_ruta antes de relevamiento/denuncia/actuaciones
    ordered = list(PHASE1_DELETE_ORDER_V3)
    for t in topo:
        if t not in ordered:
            ordered.append(t)
    return ordered


def audit_source_with_iniciadores(
    conn: Connection,
    source_entity: str,
    source_column: str,
    candidate_ids: set[int],
    planned_ini_delete: set[int],
    protected_ini: set[int],
) -> dict[str, Any]:
    """Auditoría detallada relevamiento/denuncia vs iniciadores."""
    deletable, blocked, detail = filter_parents_blocked_by_iniciador(
        conn, source_entity, source_column, candidate_ids, planned_ini_delete
    )
    audit_rows: list[dict] = []
    for pid in sorted(candidate_ids):
        inis = conn.execute(
            text(
                f"""
                SELECT id, tipo_iniciador, created_by_user_id
                FROM iniciador_ruta WHERE `{source_column}` = :sid
                """
            ),
            {"sid": pid},
        ).fetchall()
        ini_detail = []
        for ini in inis:
            ini_id = ini[0]
            if ini_id in planned_ini_delete:
                cls = "DELETE_PHASE1_INICIADOR"
            elif ini_id in protected_ini:
                cls = "PROTECTED_REAL"
            else:
                cls = "SURVIVING_INDETERMINATE"
            ini_detail.append({"iniciador_id": ini_id, "clasificacion": cls})
        audit_rows.append(
            {
                f"{source_entity}_id": pid,
                "iniciadores": ini_detail,
                "status": "DELETE_PHASE1" if pid in deletable else "BLOCKED",
            }
        )
    return {
        "candidates": len(candidate_ids),
        "deletable": len(deletable),
        "blocked": len(blocked),
        "deletable_ids": sorted(deletable),
        "blocked_ids": sorted(blocked),
        "detail": detail[:30],
        "audit": audit_rows[:20],
    }
