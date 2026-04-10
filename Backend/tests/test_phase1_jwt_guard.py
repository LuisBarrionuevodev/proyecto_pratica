"""JWT guard: mutaciones (fase 1) y lecturas PR-A exigen Bearer; login público."""


def test_post_actuaciones_sin_jwt_401(client):
    resp = client.post("/actuaciones/", json={})
    assert resp.status_code == 401
    body = resp.get_json()
    assert body is not None
    assert "detail" in body


def test_post_actuaciones_con_jwt_no_es_401_por_auth(client, auth_headers):
    """Puede fallar por validación/negocio, pero no por guard de fase 1."""
    resp = client.post("/actuaciones/", json={}, headers=auth_headers)
    assert resp.status_code != 401


def test_get_actuaciones_sin_jwt_401_pr_a(client):
    resp = client.get("/actuaciones/")
    assert resp.status_code == 401
    assert "detail" in (resp.get_json() or {})


def test_get_actuaciones_con_jwt_no_401_por_auth(client, auth_headers):
    resp = client.get("/actuaciones/", headers=auth_headers)
    assert resp.status_code != 401


def test_get_denuncias_sin_jwt_401_pr_a(client):
    resp = client.get("/api/denuncias")
    assert resp.status_code == 401


def test_get_rutas_trabajo_sin_jwt_401_pr_a(client):
    resp = client.get("/rutas-trabajo/1")
    assert resp.status_code == 401


def test_get_relevamientos_sin_jwt_401_pr_b(client):
    resp = client.get("/relevamientos/")
    assert resp.status_code == 401
    assert "detail" in (resp.get_json() or {})


def test_get_map_puntos_sin_jwt_401_pr_c1(client):
    resp = client.get("/map/puntos")
    assert resp.status_code == 401


def test_get_api_map_pendientes_sin_jwt_401_pr_c1(client):
    resp = client.get("/api/map/pendientes")
    assert resp.status_code == 401


def test_get_geo_pending_sin_jwt_401_pr_c1(client):
    resp = client.get("/geo/pending")
    assert resp.status_code == 401


def test_get_geolocalizacion_calles_catalogo_sin_jwt_401_pr_c1(client):
    resp = client.get("/geolocalizacion/calles/catalogo")
    assert resp.status_code == 401


def test_get_grid_catalogs_inspectores_sin_jwt_401_pr_c2(client):
    resp = client.get("/grid/catalogs/inspectores")
    assert resp.status_code == 401
    assert "detail" in (resp.get_json() or {})


def test_get_grid_catalogs_inspectores_con_jwt_no_401_por_auth(client, auth_headers):
    resp = client.get("/grid/catalogs/inspectores", headers=auth_headers)
    assert resp.status_code != 401


def test_post_grid_start_sin_jwt_no_lo_pide_pr_c2(client):
    """PR-C2 solo cubre GET catálogos; start batch sigue sin JWT en fase 1."""
    resp = client.post("/grid/start", json={"kind": "actuaciones"})
    assert resp.status_code != 401


def test_get_relevamientos_con_jwt_no_401_por_auth(client, auth_headers):
    # Rango explícito: el default “mes actual” del schema puede fallar en último día del mes (bug conocido).
    resp = client.get(
        "/relevamientos/?desde=2026-01-01&hasta=2026-01-31",
        headers=auth_headers,
    )
    assert resp.status_code != 401


def test_login_publico_sin_jwt(client):
    resp = client.post("/api/auth/login", json={"username": "x", "password": "y"})
    assert resp.status_code != 401
