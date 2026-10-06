"""V1.1-MEDIA.2A — idempotencia upload intent y complete."""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.integrations.media_storage.factory import get_media_storage, reset_media_storage_singleton
from app.integrations.media_storage.mock_storage import MockMediaStorage
from app.models import Archivo, RutaItemArchivo
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_media_storage_v1_1_0 import (
    PDF_BYTES,
    PDF_SHA,
    _create_intent,
    _intent_payload,
    pdf_bytes_variant,
)

pytestmark = pytest.mark.usefixtures("_reset_media_storage")


@pytest.fixture(autouse=True)
def _reset_media_storage():
    reset_media_storage_singleton()
    yield
    reset_media_storage_singleton()


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _simulate_upload_and_complete(client, user_id: int, intent_resp) -> dict:
    data = intent_resp.get_json()
    if data.get("status") == "READY":
        return data
    storage = get_media_storage()
    assert isinstance(storage, MockMediaStorage)
    storage.ingest_from_presigned_put_url(data["upload_url"], PDF_BYTES)
    complete = client.post(
        f"/archivos/{data['archivo_id']}/complete",
        headers=_auth_headers(user_id),
    )
    assert complete.status_code == 200
    return data


def test_same_sha_returns_same_archivo_id(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        first = _create_intent(client, d["item_a"].id, d["user_a"].id)
        assert first.status_code == 201
        aid1 = first.get_json()["archivo_id"]
        second = _create_intent(client, d["item_a"].id, d["user_a"].id)
        assert second.status_code == 201
        body2 = second.get_json()
        assert body2["archivo_id"] == aid1
        assert db.session.query(Archivo).filter(Archivo.id == aid1).count() == 1


def test_concurrent_intents_single_archivo(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    item_id = d["item_a"].id
    user_id = d["user_a"].id

    def _post():
        with app.app_context():
            with app.test_client() as c:
                return _create_intent(c, item_id, user_id)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_post) for _ in range(4)]
        ids = {f.result().get_json()["archivo_id"] for f in as_completed(futures)}
    assert len(ids) == 1


def test_complete_idempotent_ready(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
        again = client.post(
            f"/archivos/{data['archivo_id']}/complete",
            headers=_auth_headers(d["user_a"].id),
        )
    assert again.status_code == 200
    assert again.get_json()["status"] == "READY"


def test_retry_intent_does_not_consume_extra_cupo(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        aid = intent.get_json()["archivo_id"]
        for _ in range(3):
            retry = _create_intent(client, d["item_a"].id, d["user_a"].id)
            assert retry.get_json()["archivo_id"] == aid
        count = (
            db.session.query(RutaItemArchivo)
            .join(Archivo, Archivo.id == RutaItemArchivo.archivo_id)
            .filter(
                RutaItemArchivo.ruta_item_id == d["item_a"].id,
                Archivo.deleted_at.is_(None),
                Archivo.status.in_(("PENDING", "READY")),
            )
            .count()
        )
        assert count == 1


def test_quota_error_has_code(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        for i in range(10):
            content = pdf_bytes_variant(500 + i)
            sha = hashlib.sha256(content).hexdigest()
            resp = client.post(
                f"/ruta-items/{d['item_a'].id}/archivos/upload-intents",
                headers=_auth_headers(d["user_a"].id),
                json=_intent_payload(sha256=sha, byte_size=len(content), filename=f"a{i}.pdf"),
            )
            assert resp.status_code == 201
            data = resp.get_json()
            storage = get_media_storage()
            storage.ingest_from_presigned_put_url(data["upload_url"], content)
            client.post(
                f"/archivos/{data['archivo_id']}/complete",
                headers=_auth_headers(d["user_a"].id),
            )
        overflow_content = pdf_bytes_variant(510)
        overflow = _create_intent(
            client,
            d["item_a"].id,
            d["user_a"].id,
            byte_size=len(overflow_content),
            sha256=hashlib.sha256(overflow_content).hexdigest(),
        )
    assert overflow.status_code == 422
    body = overflow.get_json()
    assert body.get("code") == "MEDIA_QUOTA_EXCEEDED"


def test_ready_not_deleted_by_cleanup(app, client, app_ctx, scope_fixture) -> None:
    from datetime import datetime, timedelta

    from app.domains.media.services.cleanup_pending_media_service import cleanup_pending_media

    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
    arch = Archivo.query.get(data["archivo_id"])
    arch.created_at = datetime.utcnow() - timedelta(hours=48)
    db.session.commit()
    result = cleanup_pending_media(older_than_hours=24)
    assert result.processed == 0
    assert Archivo.query.get(data["archivo_id"]).status == "READY"
