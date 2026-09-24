"""Contrato HTTP del resumen Completar trabajo por día (servicio mockeado)."""

from __future__ import annotations

from unittest.mock import patch


@patch(
    "app.domains.actuaciones.routes.completar_trabajo_pendientes_resumen.list_completar_trabajo_pendientes_resumen_por_dia"
)
def test_get_resumen_200_y_shape(mock_svc, client, auth_headers):
    mock_svc.return_value = (
        [
            {
                "fecha": "2026-04-01",
                "total": 3,
                "atrasado": False,
                "items_con_actuacion": 5,
                "hubo_actividad": True,
                "sin_pendientes_cierre": False,
                "categoria_calendario": "CON_PENDIENTES",
            },
            {
                "fecha": "2026-04-02",
                "total": 0,
                "atrasado": False,
                "items_con_actuacion": 2,
                "hubo_actividad": True,
                "sin_pendientes_cierre": True,
                "categoria_calendario": "COMPLETO",
            },
        ],
        {
            "fecha_desde": "2026-04-01",
            "fecha_hasta": "2026-04-30",
            "hoy": "2026-04-10",
        },
    )
    r = client.get(
        "/actuaciones/completar-trabajo/pendientes/resumen?fecha_desde=2026-04-01&fecha_hasta=2026-04-30",
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["dias"][0]["fecha"] == "2026-04-01"
    assert body["dias"][0]["total"] == 3
    assert body["dias"][0]["categoria_calendario"] == "CON_PENDIENTES"
    assert body["dias"][1]["categoria_calendario"] == "COMPLETO"
    assert body["meta"]["fecha_desde"] == "2026-04-01"
    mock_svc.assert_called_once()


def test_get_resumen_422_sin_parametros(client, auth_headers):
    r = client.get("/actuaciones/completar-trabajo/pendientes/resumen", headers=auth_headers)
    assert r.status_code == 422
