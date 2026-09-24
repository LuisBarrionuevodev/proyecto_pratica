"""Tests validación ejecutabilidad FK FASE 1."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.domains.predeploy_cleanup.execution_validator import (
    build_delete_order,
    filter_parents_blocked_by_iniciador,
    validate_execution_plan,
)
from app.domains.predeploy_cleanup.fk_graph import ForeignKeyEdge
from app.domains.predeploy_cleanup.sequential_simulator import VirtualDeleteState


def test_parent_blocked_by_restrict_child_surviving():
    """Parent con child RESTRICT sobreviviente → blocked."""
    virtual = VirtualDeleteState()
    edges = [
        ForeignKeyEdge(
            "iniciador_ruta", "relevamiento_id", "relevamiento", "id", "RESTRICT"
        ),
    ]
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ("id",)
    conn.execute.return_value.fetchall.return_value = [(99, 100)]

    explicit = {"relevamiento": {100}}
    result = validate_execution_plan(conn, explicit, virtual, edges)
    assert not result["valid"]
    assert "relevamiento" in result["blocked_ids_by_entity"]


def test_parent_allowed_when_child_planned_delete():
    """Parent permitido si child ya está en virtual delete."""
    virtual = VirtualDeleteState()
    virtual.add_explicit("iniciador_ruta", {99})
    edges = [
        ForeignKeyEdge(
            "iniciador_ruta", "relevamiento_id", "relevamiento", "id", "RESTRICT"
        ),
    ]
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ("id",)
    conn.execute.return_value.fetchall.return_value = [(99, 100)]

    explicit = {"relevamiento": {100}}
    result = validate_execution_plan(conn, explicit, virtual, edges)
    assert result["valid"]


def test_relevamiento_blocked_with_surviving_iniciador():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [
        (50, "RELEVAMIENTO", 2),
    ]
    deletable, blocked, _ = filter_parents_blocked_by_iniciador(
        conn, "relevamiento", "relevamiento_id", {100}, planned_ini_delete=set()
    )
    assert 100 in blocked
    assert 100 not in deletable


def test_relevamiento_allowed_when_iniciador_planned_delete():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    deletable, blocked, _ = filter_parents_blocked_by_iniciador(
        conn, "relevamiento", "relevamiento_id", {100}, planned_ini_delete={50}
    )
    assert 100 in deletable
    assert not blocked


def test_denuncia_blocked_with_surviving_iniciador():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [(77, "DENUNCIA", 3)]
    deletable, blocked, _ = filter_parents_blocked_by_iniciador(
        conn, "denuncia", "denuncia_id", {200}, planned_ini_delete=set()
    )
    assert 200 in blocked


def test_topological_order_iniciador_before_relevamiento():
    from app.domains.predeploy_cleanup.execution_validator import PHASE1_DELETE_ORDER_V3

    edges = [
        ForeignKeyEdge("iniciador_ruta", "relevamiento_id", "relevamiento", "id", "RESTRICT"),
        ForeignKeyEdge("ruta_item", "iniciador_ruta_id", "iniciador_ruta", "id", "RESTRICT"),
    ]
    order = build_delete_order(edges)
    assert order.index("ruta_item") < order.index("iniciador_ruta")
    assert order.index("iniciador_ruta") < order.index("relevamiento")
    assert order[: len(PHASE1_DELETE_ORDER_V3)] == PHASE1_DELETE_ORDER_V3


def test_protected_iniciador_blocks_relevamiento():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [(999, "RELEVAMIENTO", 1)]
    _, blocked, _ = filter_parents_blocked_by_iniciador(
        conn, "relevamiento", "relevamiento_id", {4811}, planned_ini_delete={50}
    )
    assert 4811 in blocked
