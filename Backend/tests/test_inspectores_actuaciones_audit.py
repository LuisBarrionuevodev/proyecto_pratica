"""Tests del inventario de inspectores por actuación (PR A)."""

from unittest.mock import patch

from app.domains.actuaciones.audit.inspectores_actuaciones_audit import (
    audit_actuaciones_inspectores_summary,
)


@patch(
    "app.domains.actuaciones.audit.inspectores_actuaciones_audit._distribution_rows",
    return_value=[(100, 1), (200, 3), (300, 4), (301, 5)],
)
def test_audit_summary_detects_mas_de_tres(_mock_rows) -> None:
    s = audit_actuaciones_inspectores_summary(max_detail_ids=50)
    assert s["actuaciones_con_al_menos_un_inspector"] == 4
    assert s["max_inspectores_por_actuacion"] == 5
    assert s["con_mas_de_3_inspectores"] == 2
    assert s["actuacion_ids_mas_de_3"] == [301, 300]
    assert s["buckets_por_cantidad"]["4+"] == 2
    assert s["buckets_por_cantidad"]["1"] == 1
    assert s["buckets_por_cantidad"]["3"] == 1


@patch(
    "app.domains.actuaciones.audit.inspectores_actuaciones_audit._distribution_rows",
    return_value=[],
)
def test_audit_summary_empty(_mock_rows) -> None:
    s = audit_actuaciones_inspectores_summary()
    assert s["con_mas_de_3_inspectores"] == 0
    assert s["max_inspectores_por_actuacion"] == 0
