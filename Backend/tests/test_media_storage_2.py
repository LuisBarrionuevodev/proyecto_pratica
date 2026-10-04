"""V1.1-MEDIA.2 — cleanup operativo, idempotencia y observabilidad."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.database import db
from app.domains.media.services.cleanup_pending_media_service import cleanup_pending_media
from app.integrations.media_storage.factory import get_media_storage, reset_media_storage_singleton
from app.integrations.media_storage.mock_storage import MockMediaStorage
from app.models import Archivo
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_media_storage_v1_1_0 import _create_intent, _simulate_upload_and_complete

pytestmark = pytest.mark.usefixtures("_reset_media_storage")


@pytest.fixture(autouse=True)
def _reset_media_storage():
    reset_media_storage_singleton()
    yield
    reset_media_storage_singleton()


def test_cleanup_idempotent(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        archivo_id = intent.get_json()["archivo_id"]
    arch = Archivo.query.get(archivo_id)
    arch.created_at = datetime.utcnow() - timedelta(hours=30)
    db.session.commit()
    first = cleanup_pending_media(older_than_hours=24)
    assert first.processed == 1
    second = cleanup_pending_media(older_than_hours=24)
    assert second.processed == 0


def test_cleanup_no_toca_ready(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
    arch = Archivo.query.get(data["archivo_id"])
    arch.created_at = datetime.utcnow() - timedelta(hours=48)
    db.session.commit()
    result = cleanup_pending_media(older_than_hours=24)
    assert result.processed == 0
    arch2 = Archivo.query.get(data["archivo_id"])
    assert arch2.status == "READY"
    assert arch2.deleted_at is None


def test_cleanup_storage_delete_error_soft_deletes(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        archivo_id = intent.get_json()["archivo_id"]
    arch = Archivo.query.get(archivo_id)
    arch.created_at = datetime.utcnow() - timedelta(hours=30)
    db.session.commit()
    storage = get_media_storage()
    assert isinstance(storage, MockMediaStorage)

    with patch.object(storage, "delete_object", side_effect=RuntimeError("s3 down")):
        result = cleanup_pending_media(older_than_hours=24)
    assert result.processed == 1
    assert result.storage_delete_errors == 1
    arch2 = Archivo.query.get(archivo_id)
    assert arch2.status == "DELETED"
    assert arch2.deleted_at is not None


def test_logs_no_presigned_url(app, client, app_ctx, scope_fixture, caplog) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="app.domains.media")
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
    body = intent.get_json()
    assert "upload_url" in body
    url = body["upload_url"]
    for record in caplog.records:
        msg = record.getMessage()
        assert url not in msg
        assert "AWS_SECRET" not in msg
    assert any("media_upload_intent_created" in r.getMessage() for r in caplog.records)
