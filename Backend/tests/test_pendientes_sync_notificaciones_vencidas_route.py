"""POST /actuaciones/pendientes/sync-notificaciones-vencidas"""


def test_post_sync_notificaciones_vencidas_sin_jwt_401(client):
    resp = client.post("/actuaciones/pendientes/sync-notificaciones-vencidas")
    assert resp.status_code == 401
    assert "detail" in (resp.get_json() or {})


def test_post_sync_notificaciones_vencidas_ok_metricas(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.domains.actuaciones.routes.pendientes_sync_notificaciones_vencidas.run_sync_notificaciones_vencidas",
        lambda: {
            "status": "ok",
            "created": 1,
            "eligible_notificaciones": 3,
            "skipped_already_blocking": 0,
            "collisions_idempotent": 0,
            "elapsed_ms": 12.5,
            "started_at": "2026-03-30T12:00:00+00:00",
        },
    )
    resp = client.post(
        "/actuaciones/pendientes/sync-notificaciones-vencidas",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert data["status"] == "ok"
    assert data["created"] == 1
    assert data["eligible_notificaciones"] == 3
    assert "elapsed_ms" in data
    assert "started_at" in data
