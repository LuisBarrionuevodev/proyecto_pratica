"""V1.1-MEDIA.1B — FOTO_INSPECCION (cupo 12, solo imágenes)."""

from __future__ import annotations

import hashlib

import pytest

from app.domains.media.constants import CATEGORIA_FOTO_INSPECCION
from app.integrations.media_storage.factory import get_media_storage, reset_media_storage_singleton
from app.integrations.media_storage.mock_storage import MockMediaStorage
from app.models import Archivo
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_media_storage_v1_1_0 import PDF_BYTES, PDF_SHA, _auth_headers, _create_intent

JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 32
JPEG_SHA = hashlib.sha256(JPEG_BYTES).hexdigest()

pytestmark = pytest.mark.usefixtures("_reset_media_storage")


@pytest.fixture(autouse=True)
def _reset_media_storage():
    reset_media_storage_singleton()
    yield
    reset_media_storage_singleton()


def _simulate_upload_jpeg_and_complete(client, user_id: int, intent_resp) -> dict:
    data = intent_resp.get_json()
    storage = get_media_storage()
    assert isinstance(storage, MockMediaStorage)
    storage.ingest_from_presigned_put_url(data["upload_url"], JPEG_BYTES)
    complete = client.post(
        f"/archivos/{data['archivo_id']}/complete",
        headers=_auth_headers(user_id),
    )
    assert complete.status_code == 200
    return data


def test_foto_inspeccion_intent_autorizado_cupo_12(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    for i in range(12):
        r = _create_intent(
            client,
            d["item_a"].id,
            d["user_a"].id,
            categoria=CATEGORIA_FOTO_INSPECCION,
            tipo_documento=None,
            filename=f"insp{i}.jpg",
            content_type="image/jpeg",
            byte_size=len(JPEG_BYTES),
            sha256=JPEG_SHA,
        )
        assert r.status_code == 201
    r13 = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        categoria=CATEGORIA_FOTO_INSPECCION,
        tipo_documento=None,
        filename="insp13.jpg",
        content_type="image/jpeg",
        byte_size=len(JPEG_BYTES),
        sha256=JPEG_SHA,
    )
    assert r13.status_code == 422


def test_foto_inspeccion_pdf_rechazado_422(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    resp = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        categoria=CATEGORIA_FOTO_INSPECCION,
        tipo_documento=None,
        filename="doc.pdf",
        content_type="application/pdf",
        byte_size=len(PDF_BYTES),
        sha256=PDF_SHA,
    )
    assert resp.status_code == 422


def test_foto_inspeccion_list_delete_scope(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    intent = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        categoria=CATEGORIA_FOTO_INSPECCION,
        tipo_documento=None,
        filename="f1.jpg",
        content_type="image/jpeg",
        byte_size=len(JPEG_BYTES),
        sha256=JPEG_SHA,
    )
    assert intent.status_code == 201
    data = _simulate_upload_jpeg_and_complete(client, d["user_a"].id, intent)

    lista = client.get(
        f"/ruta-items/{d['item_a'].id}/archivos",
        headers=_auth_headers(d["user_a"].id),
    )
    assert lista.status_code == 200
    body = lista.get_json()
    assert len(body["foto_inspeccion"]) == 1
    assert body["foto_inspeccion"][0]["archivo_id"] == data["archivo_id"]

    ajeno_list = client.get(
        f"/ruta-items/{d['item_a'].id}/archivos",
        headers=_auth_headers(d["user_b"].id),
    )
    assert ajeno_list.status_code == 403

    ajeno_del = client.delete(
        f"/archivos/{data['archivo_id']}",
        headers=_auth_headers(d["user_b"].id),
    )
    assert ajeno_del.status_code == 403

    ok_del = client.delete(
        f"/archivos/{data['archivo_id']}",
        headers=_auth_headers(d["user_a"].id),
    )
    assert ok_del.status_code == 200
    arch = Archivo.query.get(data["archivo_id"])
    assert arch is not None
    assert arch.status == "DELETED"

    intent2 = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        categoria=CATEGORIA_FOTO_INSPECCION,
        tipo_documento=None,
        filename="f2.jpg",
        content_type="image/jpeg",
        byte_size=len(JPEG_BYTES),
        sha256=JPEG_SHA,
    )
    assert intent2.status_code == 201


def test_foto_inspeccion_png_webp_intent_ok(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    png_sha = hashlib.sha256(b"\x89PNG\r\n\x1a\n" + b"x" * 40).hexdigest()
    webp_sha = hashlib.sha256(b"RIFF" + b"\x00" * 4 + b"WEBP" + b"y" * 20).hexdigest()
    for filename, ct, sha, size in (
        ("f.png", "image/png", png_sha, 48),
        ("f.webp", "image/webp", webp_sha, 32),
    ):
        r = _create_intent(
            client,
            d["item_a"].id,
            d["user_a"].id,
            categoria=CATEGORIA_FOTO_INSPECCION,
            tipo_documento=None,
            filename=filename,
            content_type=ct,
            byte_size=size,
            sha256=sha,
        )
        assert r.status_code == 201
