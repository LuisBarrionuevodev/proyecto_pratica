"""Contratos GET /api/indicadores/{ejecutivo,pendientes,riesgo,no-realizadas,productividad}."""

import pytest

_DASHBOARD_PATHS = (
    "/api/indicadores/ejecutivo",
    "/api/indicadores/pendientes",
    "/api/indicadores/riesgo",
    "/api/indicadores/no-realizadas",
    "/api/indicadores/productividad",
)

_QUERY_OK = "desde=2026-01-01&hasta=2026-12-31"


@pytest.mark.parametrize("path", _DASHBOARD_PATHS)
def test_dashboard_block_sin_jwt_401(client, path):
    resp = client.get(f"{path}?{_QUERY_OK}")
    assert resp.status_code == 401
    assert "detail" in (resp.get_json() or {})


@pytest.mark.parametrize("path", _DASHBOARD_PATHS)
def test_dashboard_block_sin_fechas_422(client, auth_headers, path):
    resp = client.get(path, headers=auth_headers)
    assert resp.status_code == 422
    body = resp.get_json()
    assert body is not None
    assert body.get("detail") == "Validation error"
    assert "errors" in body


@pytest.mark.parametrize("path", _DASHBOARD_PATHS)
def test_dashboard_block_desde_mayor_hasta_422(client, auth_headers, path):
    resp = client.get(
        f"{path}?desde=2026-02-01&hasta=2026-01-01",
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_get_indicadores_ejecutivo_ok_shape(client, auth_headers):
    resp = client.get(
        f"/api/indicadores/ejecutivo?{_QUERY_OK}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert "periodo" in data
    assert data["periodo"]["desde"] == "2026-01-01"
    assert data["periodo"]["hasta"] == "2026-12-31"
    kpis = data["kpis"]
    for key in (
        "actuaciones_realizadas",
        "actas_labradas",
        "reinspecciones_notificacion_realizadas",
        "ratificaciones_clausura_realizadas",
        "ratificaciones_decomiso_realizadas",
        "verificar_informar_realizadas",
        "mercaderia_decomisada_kg",
    ):
        assert key in kpis
        assert kpis[key] >= 0
    actas = data["actas_por_tipo"]
    for k in ("inspeccion", "notificacion", "comprobacion", "clausura", "decomiso"):
        assert k in actas
        assert actas[k] >= 0
    assert kpis["actas_labradas"] == sum(actas.values())


def test_get_indicadores_pendientes_ok_shape(client, auth_headers):
    resp = client.get(
        f"/api/indicadores/pendientes?{_QUERY_OK}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    kpis = data["kpis"]
    for key in (
        "relevamientos_pendientes",
        "reinspecciones_oficio_pendientes",
        "reinspecciones_notificacion_pendientes",
        "denuncias_pendientes",
        "pendientes_geolocalizacion",
    ):
        assert key in kpis
        assert kpis[key] >= 0
    assert isinstance(data["distritos_con_mas_pendientes"], list)


def test_get_indicadores_riesgo_ok_shape(client, auth_headers):
    resp = client.get(
        f"/api/indicadores/riesgo?{_QUERY_OK}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    for key in (
        "top_rubros",
        "top_motivos_notificacion",
        "top_motivos_comprobacion",
        "decomiso_kg_por_rubro",
    ):
        assert key in data
        assert isinstance(data[key], list)


def test_get_indicadores_no_realizadas_ok_shape(client, auth_headers):
    resp = client.get(
        f"/api/indicadores/no-realizadas?{_QUERY_OK}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    por_tipo = data["por_tipo"]
    for k in ("inspeccion", "reinspeccion_oficio", "reinspeccion_notificacion", "denuncia"):
        assert k in por_tipo
        assert por_tipo[k] >= 0
    assert isinstance(data["top_contraproducencias"], list)
    assert isinstance(data["distritos_con_mas_no_realizadas"], list)
    for item in data["top_contraproducencias"]:
        assert "contraproducencia" in item
        assert "cantidad" in item
        assert _loose_key(item["contraproducencia"]) not in {"NO HUBO", "NO_HUBO"}


def test_get_indicadores_productividad_ok_shape(client, auth_headers):
    resp = client.get(
        f"/api/indicadores/productividad?{_QUERY_OK}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    for key in (
        "inspectores_realizadas",
        "inspectores_no_realizadas",
        "actas_por_inspector",
    ):
        assert key in data
        assert isinstance(data[key], list)


def _loose_key(s: str) -> str:
    x = s.upper().replace("_", " ").replace("/", " ")
    return " ".join(x.split())


def test_resumen_sigue_ok_tras_bloques_dashboard(client, auth_headers):
    """Compatibilidad: /resumen no se rompe con los nuevos endpoints."""
    resp = client.get(
        f"/api/indicadores/resumen?{_QUERY_OK}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert "actuaciones" in data
    assert "mapa_operativo" in data
