"""V1.1-MEDIA.0 / 0A — storage privado, categorías y cupos por RutaItem."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.media.constants import (
    CATEGORIA_FOTO_ACTA,
    CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
)
from app.domains.media.services.cleanup_pending_media_service import cleanup_pending_media
from app.integrations.media_storage.factory import get_media_storage, reset_media_storage_singleton
from app.integrations.media_storage.mock_storage import MockMediaStorage
from app.models import Archivo, RutaItemArchivo
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401

PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"x" * 200
PDF_SHA = hashlib.sha256(PDF_BYTES).hexdigest()


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _intent_payload(**overrides) -> dict:
    body = {
        "categoria": CATEGORIA_FOTO_ACTA,
        "tipo_documento": "ACTA_INSPECCION",
        "filename": "acta-001.pdf",
        "content_type": "application/pdf",
        "byte_size": len(PDF_BYTES),
        "sha256": PDF_SHA,
    }
    body.update(overrides)
    return body


@pytest.fixture(autouse=True)
def _reset_media_storage():
    reset_media_storage_singleton()
    yield
    reset_media_storage_singleton()


def _create_intent(client, item_id: int, user_id: int, **payload_kw):
    resp = client.post(
        f"/ruta-items/{item_id}/archivos/upload-intents",
        headers=_auth_headers(user_id),
        json=_intent_payload(**payload_kw),
    )
    return resp


def _simulate_upload_and_complete(client, user_id: int, intent_resp) -> dict:
    data = intent_resp.get_json()
    storage = get_media_storage()
    assert isinstance(storage, MockMediaStorage)
    storage.ingest_from_presigned_put_url(data["upload_url"], PDF_BYTES)
    complete = client.post(
        f"/archivos/{data['archivo_id']}/complete",
        headers=_auth_headers(user_id),
    )
    assert complete.status_code == 200
    return data


def test_upload_intent_foto_acta_ok(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    resp = _create_intent(client, d["item_a"].id, d["user_a"].id)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body.get("upload_url")
    assert body.get("archivo_id")
    arch = Archivo.query.get(body["archivo_id"])
    assert arch is not None
    assert arch.status == "PENDING"
    assert "acta-001" not in arch.object_key
    assert f"/{CATEGORIA_FOTO_ACTA}/" in arch.object_key


def test_inspector_ajeno_upload_intent_403(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    resp = _create_intent(client, d["item_b"].id, d["user_a"].id)
    assert resp.status_code == 403


def test_foto_inspeccion_intent_imagen_ok_media1b(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    resp = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        categoria="FOTO_INSPECCION",
        tipo_documento=None,
        filename="visita.jpg",
        content_type="image/jpeg",
        byte_size=500,
        sha256="c" * 64,
    )
    assert resp.status_code == 201


def test_mime_no_permitido_422(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    resp = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        content_type="application/zip",
        byte_size=100,
        sha256="a" * 64,
    )
    assert resp.status_code == 422


def test_pdf_tamano_excedido_422(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    resp = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        byte_size=20_000_000,
    )
    assert resp.status_code == 422


def test_imagen_tamano_excedido_422(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    resp = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        filename="foto.jpg",
        content_type="image/jpeg",
        byte_size=11_000_000,
        sha256="b" * 64,
    )
    assert resp.status_code == 422


def test_foto_acta_octavo_archivo_422(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    for i in range(7):
        r = _create_intent(
            client,
            d["item_a"].id,
            d["user_a"].id,
            categoria=CATEGORIA_FOTO_ACTA,
            filename=f"acta{i}.pdf",
        )
        assert r.status_code == 201
    r8 = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        categoria=CATEGORIA_FOTO_ACTA,
        filename="acta8.pdf",
    )
    assert r8.status_code == 422


def test_foto_documentacion_local_decimo_archivo_422(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    for i in range(9):
        r = _create_intent(
            client,
            d["item_a"].id,
            d["user_a"].id,
            categoria=CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
            tipo_documento="HABILITACION",
            filename=f"hab{i}.pdf",
        )
        assert r.status_code == 201
    r10 = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        categoria=CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
        tipo_documento="OTRO_DOCUMENTO_LOCAL",
        filename="hab10.pdf",
    )
    assert r10.status_code == 422


def test_cupos_independientes_entre_categorias(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    for i in range(7):
        assert (
            _create_intent(
                client,
                d["item_a"].id,
                d["user_a"].id,
                categoria=CATEGORIA_FOTO_ACTA,
                filename=f"a{i}.pdf",
            ).status_code
            == 201
        )
    for i in range(9):
        assert (
            _create_intent(
                client,
                d["item_a"].id,
                d["user_a"].id,
                categoria=CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
                tipo_documento="CARNET_MANIPULADOR",
                filename=f"d{i}.pdf",
            ).status_code
            == 201
        )
    assert (
        _create_intent(
            client,
            d["item_a"].id,
            d["user_a"].id,
            categoria=CATEGORIA_FOTO_ACTA,
            filename="extra_acta.pdf",
        ).status_code
        == 422
    )
    assert (
        _create_intent(
            client,
            d["item_a"].id,
            d["user_a"].id,
            categoria=CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
            tipo_documento="CERTIFICADO_DESINFECCION",
            filename="extra_doc.pdf",
        ).status_code
        == 422
    )


def test_complete_pending_to_ready_conserva_categoria(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    intent = _create_intent(
        client,
        d["item_a"].id,
        d["user_a"].id,
        categoria=CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
        tipo_documento="HABILITACION",
    )
    assert intent.status_code == 201
    data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
    arch = Archivo.query.get(data["archivo_id"])
    assert arch.status == "READY"
    link = RutaItemArchivo.query.filter_by(archivo_id=arch.id).one()
    assert link.categoria == CATEGORIA_FOTO_DOCUMENTACION_LOCAL
    assert link.tipo_documento == "HABILITACION"


def test_complete_invalid_magic_rejected(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
    data = intent.get_json()
    storage = get_media_storage()
    assert isinstance(storage, MockMediaStorage)
    storage.ingest_from_presigned_put_url(data["upload_url"], b"not-a-pdf")
    complete = client.post(
        f"/archivos/{data['archivo_id']}/complete",
        headers=_auth_headers(d["user_a"].id),
    )
    assert complete.status_code == 422
    arch = Archivo.query.get(data["archivo_id"])
    assert arch.status == "REJECTED"


def test_download_url_ready(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
    data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
    dl = client.get(
        f"/archivos/{data['archivo_id']}/download-url",
        headers=_auth_headers(d["user_a"].id),
    )
    assert dl.status_code == 200
    body = dl.get_json()
    assert body.get("download_url")
    assert "object_key" not in json.dumps(body)


def test_download_pending_rechazado(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
    archivo_id = intent.get_json()["archivo_id"]
    dl = client.get(
        f"/archivos/{archivo_id}/download-url",
        headers=_auth_headers(d["user_a"].id),
    )
    assert dl.status_code == 422


def test_download_archivo_ajeno_403(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
    data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
    dl = client.get(
        f"/archivos/{data['archivo_id']}/download-url",
        headers=_auth_headers(d["user_b"].id),
    )
    assert dl.status_code == 403


def test_grid_actuaciones_sin_urls_media(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    act_id = int(d["act_a"].id)
    headers = _auth_headers(d["user_a"].id)
    resp = client.get(
        f"/actuaciones?actuacion_id={act_id}&desde=2026-01-01&hasta=2026-12-31",
        headers=headers,
    )
    assert resp.status_code == 200
    raw = json.dumps(resp.get_json())
    assert "object_key" not in raw
    assert "download_url" not in raw
    assert "upload_url" not in raw


def test_cleanup_pending_vencidos(app, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(
            client,
            d["item_a"].id,
            d["user_a"].id,
            categoria=CATEGORIA_FOTO_ACTA,
        )
        archivo_id = intent.get_json()["archivo_id"]
    arch = Archivo.query.get(archivo_id)
    arch.created_at = datetime.utcnow() - timedelta(hours=30)
    db.session.commit()
    result = cleanup_pending_media(older_than_hours=24)
    assert result.processed >= 1
    db.session.expire_all()
    arch2 = Archivo.query.get(archivo_id)
    assert arch2.status == "DELETED"
    assert arch2.deleted_at is not None
    link = RutaItemArchivo.query.filter_by(archivo_id=archivo_id).one()
    assert link.categoria == CATEGORIA_FOTO_ACTA
