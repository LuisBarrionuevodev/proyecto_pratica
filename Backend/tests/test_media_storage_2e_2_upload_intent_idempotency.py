"""P0 V1.1-MEDIA.2E.2 — idempotencia real en upload-intents."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from app.database import db
from app.integrations.media_storage.factory import reset_media_storage_singleton
from app.integrations.media_storage.mock_storage import MockMediaStorage
from app.models import Archivo, RutaItemArchivo
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_media_storage_v1_1_0 import (
    PDF_BYTES,
    PDF_SHA,
    _create_intent,
    _intent_payload,
    _simulate_upload_and_complete,
)

pytestmark = pytest.mark.usefixtures("_reset_media_storage")


@pytest.fixture(autouse=True)
def _reset_media_storage():
    reset_media_storage_singleton()
    yield
    reset_media_storage_singleton()


def _count_vinculos_activos(ruta_item_id: int) -> int:
    return (
        db.session.query(RutaItemArchivo)
        .join(Archivo, Archivo.id == RutaItemArchivo.archivo_id)
        .filter(
            RutaItemArchivo.ruta_item_id == ruta_item_id,
            Archivo.deleted_at.is_(None),
            Archivo.status.in_(("PENDING", "READY")),
        )
        .count()
    )


def _count_vinculos_por_sha(ruta_item_id: int, sha: str) -> int:
    return (
        db.session.query(RutaItemArchivo)
        .filter(
            RutaItemArchivo.ruta_item_id == ruta_item_id,
            RutaItemArchivo.content_sha256 == sha.lower(),
        )
        .count()
    )


def test_dos_intents_consecutivos_un_solo_vinculo(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        first = _create_intent(client, d["item_a"].id, d["user_a"].id)
        second = _create_intent(client, d["item_a"].id, d["user_a"].id)
    assert first.status_code == 201
    assert second.status_code == 201
    aid = first.get_json()["archivo_id"]
    assert second.get_json()["archivo_id"] == aid
    assert _count_vinculos_por_sha(d["item_a"].id, PDF_SHA) == 1
    assert db.session.query(Archivo).filter(Archivo.id == aid).count() == 1


def test_pending_reintento_mismo_archivo_id_y_url_renovada(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        first = _create_intent(client, d["item_a"].id, d["user_a"].id)
        second = _create_intent(client, d["item_a"].id, d["user_a"].id)
    body1 = first.get_json()
    body2 = second.get_json()
    assert body1["status"] == "PENDING"
    assert body2["status"] == "PENDING"
    assert body2["archivo_id"] == body1["archivo_id"]
    assert body2["upload_url"]
    assert body2["expires_at"] >= body1["expires_at"]


def test_ready_no_duplica_ni_consume_cupo(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        _simulate_upload_and_complete(client, d["user_a"].id, intent)
        activos_antes = _count_vinculos_activos(d["item_a"].id)
        retry = _create_intent(client, d["item_a"].id, d["user_a"].id)
    assert retry.status_code == 201
    body = retry.get_json()
    assert body["status"] == "READY"
    assert body["upload_url"] == ""
    assert _count_vinculos_activos(d["item_a"].id) == activos_antes == 1


def test_concurrent_intents_sin_500_y_un_solo_vinculo(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    item_id = d["item_a"].id
    user_id = d["user_a"].id

    def _post():
        with app.app_context():
            with app.test_client() as c:
                return _create_intent(c, item_id, user_id)

    statuses: list[int] = []
    archivo_ids: set[int] = set()
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_post) for _ in range(6)]
        for f in as_completed(futures):
            resp = f.result()
            statuses.append(resp.status_code)
            if resp.status_code == 201:
                archivo_ids.add(resp.get_json()["archivo_id"])
    assert all(s == 201 for s in statuses)
    assert len(archivo_ids) == 1
    with app.app_context():
        assert _count_vinculos_por_sha(item_id, PDF_SHA) == 1

