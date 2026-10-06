"""V1.1-MEDIA.2C.2 — finalizar fotos pendientes por ahora."""

from __future__ import annotations

from datetime import datetime, timezone

from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_pendientes_list_service import (
    list_completar_trabajo_pendientes,
)
from app.models import RutaItem, RutaTrabajo

from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401 — pytest fixture


def _headers(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_finalizar_por_ahora_propio_200_idempotente(app, client, scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    item.estado_ruta_item = "FINALIZADO"
    item.actuacion_id = d["act_a"].id
    item.evidencias_pendientes_abiertas = True
    db.session.commit()

    path = f"/ruta-items/{item.id}/fotos/finalizar-por-ahora"
    h = _headers(d["user_a"].id)
    r1 = client.post(path, headers=h)
    assert r1.status_code == 200
    body1 = r1.get_json()
    assert body1["ruta_item_id"] == item.id
    assert body1.get("already_closed") is False

    r2 = client.post(path, headers=h)
    assert r2.status_code == 200
    assert r2.get_json().get("already_closed") is True

    fresh = db.session.get(RutaItem, item.id)
    assert fresh is not None
    assert fresh.fotos_pendientes_cerradas_at is not None
    assert fresh.evidencias_pendientes_abiertas is False


def test_finalizar_por_ahora_ajeno_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_b"]
    item.estado_ruta_item = "FINALIZADO"
    item.actuacion_id = d["act_b"].id
    db.session.commit()

    resp = client.post(
        f"/ruta-items/{item.id}/fotos/finalizar-por-ahora",
        headers=_headers(d["user_a"].id),
    )
    assert resp.status_code == 403


def test_finalizar_por_ahora_no_cerrado_422(app, client, scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    item.estado_ruta_item = "EN_PROCESO"
    db.session.commit()

    resp = client.post(
        f"/ruta-items/{item.id}/fotos/finalizar-por-ahora",
        headers=_headers(d["user_a"].id),
    )
    assert resp.status_code == 422


def test_list_completar_excluye_finalizado_por_ahora(app, scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    ruta: RutaTrabajo = item.ruta_trabajo
    item.estado_ruta_item = "FINALIZADO"
    item.actuacion_id = d["act_a"].id
    item.evidencias_pendientes_abiertas = True
    item.fotos_pendientes_cerradas_at = datetime.now(timezone.utc)
    db.session.commit()

    rows, meta = list_completar_trabajo_pendientes(
        fecha=ruta.fecha,
        page=1,
        per_page=50,
        inspector_id_effective=d["ins_a"].id,
    )
    ids = {r["ruta_item_id"] for r in rows}
    assert item.id not in ids
    assert meta["total"] >= 0
