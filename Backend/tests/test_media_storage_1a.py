"""V1.1-MEDIA.1A — listado y eliminación autorizada."""

from __future__ import annotations

import hashlib

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.media.constants import (
    CATEGORIA_FOTO_ACTA,
    CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
)
from app.integrations.media_storage.factory import get_media_storage, reset_media_storage_singleton
from app.integrations.media_storage.mock_storage import MockMediaStorage
from app.models import Archivo, RutaItemArchivo
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_media_storage_v1_1_0 import PDF_BYTES, PDF_SHA, _auth_headers, _create_intent, _simulate_upload_and_complete

pytestmark = pytest.mark.usefixtures("_reset_media_storage")


@pytest.fixture(autouse=True)
def _reset_media_storage():
    reset_media_storage_singleton()
    yield
    reset_media_storage_singleton()


def test_get_archivos_respeta_scope(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
    data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
    ok = client.get(
        f"/ruta-items/{d['item_a'].id}/archivos",
        headers=_auth_headers(d["user_a"].id),
    )
    assert ok.status_code == 200
    body = ok.get_json()
    assert len(body["foto_acta"]) == 1
    assert body["foto_acta"][0]["archivo_id"] == data["archivo_id"]
    assert "object_key" not in str(body)
    assert "download_url" not in str(body)

    forbidden = client.get(
        f"/ruta-items/{d['item_b'].id}/archivos",
        headers=_auth_headers(d["user_a"].id),
    )
    assert forbidden.status_code == 403


def test_delete_autorizado_libera_cupo(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
    data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
    archivo_id = data["archivo_id"]
    resp = client.delete(f"/archivos/{archivo_id}", headers=_auth_headers(d["user_a"].id))
    assert resp.status_code == 200
    arch = Archivo.query.get(archivo_id)
    assert arch.status == "DELETED"
    assert arch.deleted_at is not None
    assert arch.deleted_by_user_id == d["user_a"].id
    storage = get_media_storage()
    assert isinstance(storage, MockMediaStorage)
    assert storage.head_object(arch.object_key) is None

    intent2 = _create_intent(client, d["item_a"].id, d["user_a"].id, filename="nuevo.pdf")
    assert intent2.status_code == 201


def test_delete_ajeno_403(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
    data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
    resp = client.delete(
        f"/archivos/{data['archivo_id']}",
        headers=_auth_headers(d["user_b"].id),
    )
    assert resp.status_code == 403


def test_list_incluye_foto_inspeccion_vacio(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    resp = client.get(
        f"/ruta-items/{d['item_a'].id}/archivos",
        headers=_auth_headers(d["user_a"].id),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["foto_inspeccion"] == []
