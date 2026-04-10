"""GET /api/indicadores/resumen: JWT, validación y respuesta mínima."""


def test_get_indicadores_resumen_sin_jwt_401(client):
    resp = client.get("/api/indicadores/resumen?desde=2026-01-01&hasta=2026-01-31")
    assert resp.status_code == 401
    assert "detail" in (resp.get_json() or {})


def test_get_indicadores_resumen_sin_fechas_422(client, auth_headers):
    resp = client.get("/api/indicadores/resumen", headers=auth_headers)
    assert resp.status_code == 422
    body = resp.get_json()
    assert body is not None
    assert body.get("detail") == "Validation error"
    assert "errors" in body


def test_get_indicadores_resumen_desde_mayor_hasta_422(client, auth_headers):
    resp = client.get(
        "/api/indicadores/resumen?desde=2026-02-01&hasta=2026-01-01",
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_get_indicadores_resumen_ok_shape(client, auth_headers):
    resp = client.get(
        "/api/indicadores/resumen?desde=2026-01-01&hasta=2026-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert "periodo" in data and "desde" in data["periodo"] and "hasta" in data["periodo"]
    assert "filtros" in data
    assert "actuaciones" in data
    assert set(data["actuaciones"].keys()) >= {
        "total",
        "con_contraproducencia",
        "sin_contraproducencia",
    }
    assert data["actuaciones"]["total"] == (
        data["actuaciones"]["con_contraproducencia"]
        + data["actuaciones"]["sin_contraproducencia"]
    )
    assert "contraproducencias_top" in data
    assert isinstance(data["contraproducencias_top"], list)
    assert "actas_por_tipo" in data
    for k in ("inspeccion", "notificacion", "comprobacion", "clausura", "decomiso"):
        assert k in data["actas_por_tipo"]
    assert "ruta_items_ejecucion" in data
    ri = data["ruta_items_ejecucion"]
    assert "total" in ri
    assert "estado_ejecucion_realizado" in ri
    assert "top_rubros" in data
    assert isinstance(data["top_rubros"], list)
    assert "decomiso_kg" in data
    dk = data["decomiso_kg"]
    assert "total_kg" in dk
    assert "por_mes" in dk
    assert isinstance(dk["por_mes"], list)
