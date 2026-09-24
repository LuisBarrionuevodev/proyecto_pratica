"""Inspectores del grupo de ruta en cierre Completar trabajo."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.domains.actuaciones.services.completar_trabajo_inspectores_grupo import (
    list_inspector_nombres_desde_ruta_item_grupo,
)


def test_sin_grupo_devuelve_vacio():
    item = MagicMock()
    item.ruta_grupo = None
    assert list_inspector_nombres_desde_ruta_item_grupo(item) == []


def test_ordena_por_link_id_y_dedupe_inspector():
    ins_a = MagicMock()
    ins_a.id = 1
    ins_a.nombre = "Ana"
    ins_b = MagicMock()
    ins_b.id = 2
    ins_b.nombre = "Bob"

    link2 = MagicMock()
    link2.id = 20
    link2.inspector = ins_b
    link1 = MagicMock()
    link1.id = 10
    link1.inspector = ins_a

    grupo = MagicMock()
    grupo.grupo_inspectores = [link2, link1]

    item = MagicMock()
    item.ruta_grupo = grupo

    assert list_inspector_nombres_desde_ruta_item_grupo(item) == ["Ana", "Bob"]


def test_ignora_duplicado_mismo_inspector():
    ins = MagicMock()
    ins.id = 7
    ins.nombre = "Solo"

    l1 = MagicMock()
    l1.id = 1
    l1.inspector = ins
    l2 = MagicMock()
    l2.id = 2
    l2.inspector = ins

    grupo = MagicMock()
    grupo.grupo_inspectores = [l1, l2]
    item = MagicMock()
    item.ruta_grupo = grupo

    assert list_inspector_nombres_desde_ruta_item_grupo(item) == ["Solo"]
