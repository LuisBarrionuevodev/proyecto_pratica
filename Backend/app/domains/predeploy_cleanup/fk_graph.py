"""Grafo FK desde INFORMATION_SCHEMA para orden de borrado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


@dataclass(frozen=True)
class ForeignKeyEdge:
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    delete_rule: str


def load_fk_edges(conn: Connection) -> list[ForeignKeyEdge]:
    """Carga todas las FK del schema actual."""
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
              AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            """
        )
    ).fetchall()
    return [
        ForeignKeyEdge(
            child_table=r.child_table,
            child_column=r.child_column,
            parent_table=r.parent_table,
            parent_column=r.parent_column,
            delete_rule=r.delete_rule,
        )
        for r in rows
    ]


def children_pointing_to_parent(edges: list[ForeignKeyEdge], parent_table: str) -> list[ForeignKeyEdge]:
    return [e for e in edges if e.parent_table == parent_table]


def classify_delete_mode(delete_rule: str) -> str:
    if delete_rule == "CASCADE":
        return "CASCADE_DELETE"
    if delete_rule in ("SET NULL", "NO ACTION"):
        return "EXPLICIT_DELETE"
    return "BLOCKED_BY_RESTRICT"


def topological_delete_order(tables: list[str], edges: list[ForeignKeyEdge]) -> list[str]:
    """
    Orden aproximado hijos→padres para tablas del plan.

    Tablas con FK RESTRICT hacia otra del plan deben borrarse antes.
    """
    table_set = set(tables)
    # depend[child] = parents in plan that child references
    depend: dict[str, set[str]] = {t: set() for t in tables}
    for e in edges:
        if e.child_table in table_set and e.parent_table in table_set:
            if e.delete_rule == "RESTRICT":
                depend[e.child_table].add(e.parent_table)

    ordered: list[str] = []
    remaining = set(tables)
    while remaining:
        ready = [t for t in remaining if not (depend[t] & remaining)]
        if not ready:
            ordered.extend(sorted(remaining))
            break
        ready.sort()
        ordered.extend(ready)
        remaining -= set(ready)
    return ordered
