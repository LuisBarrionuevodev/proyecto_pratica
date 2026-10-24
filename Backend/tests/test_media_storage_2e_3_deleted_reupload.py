"""P0 V1.1-MEDIA.2E.3 — reingreso seguro tras eliminar evidencia."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.media.errors import MEDIA_STATE_INVALID
from app.domains.media.services.cleanup_pending_media_service import cleanup_pending_media
from app.integrations.media_storage.factory import reset_media_storage_singleton
from app.models import Archivo, RutaItemArchivo
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_media_storage_v1_1_0 import (
    PDF_BYTES,
    PDF_SHA,
    _auth_headers,
    _create_intent,
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


def _count_vinculos_con_sha(ruta_item_id: int, sha: str) -> int:
    return (
        db.session.query(RutaItemArchivo)
        .filter(
            RutaItemArchivo.ruta_item_id == ruta_item_id,
            RutaItemArchivo.content_sha256 == sha.lower(),
        )
        .count()
    )


def test_eliminar_y_resubir_mismo_archivo_nuevo_id_y_ready(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
        old_id = data["archivo_id"]
        deleted = client.delete(
            f"/archivos/{old_id}",
            headers=_auth_headers(d["user_a"].id),
        )
        assert deleted.status_code == 200
        retry = _create_intent(client, d["item_a"].id, d["user_a"].id)
        assert retry.status_code == 201
        new_id = retry.get_json()["archivo_id"]
        assert new_id != old_id
        _simulate_upload_and_complete(client, d["user_a"].id, retry)
    assert Archivo.query.get(old_id).status == "DELETED"
    assert Archivo.query.get(new_id).status == "READY"
    assert _count_vinculos_activos(d["item_a"].id) == 1
    assert _count_vinculos_con_sha(d["item_a"].id, PDF_SHA) == 1
    hist = (
        db.session.query(RutaItemArchivo)
        .filter(RutaItemArchivo.archivo_id == old_id)
        .one()
    )
    assert hist.content_sha256 is None


def test_cleanup_pending_libera_sha_y_permite_nueva_carga(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        old_id = intent.get_json()["archivo_id"]
    arch = Archivo.query.get(old_id)
    arch.created_at = datetime.utcnow() - timedelta(hours=48)
    db.session.commit()
    cleanup_pending_media(older_than_hours=24)
    assert Archivo.query.get(old_id).status == "DELETED"
    with app.test_client() as client:
        retry = _create_intent(client, d["item_a"].id, d["user_a"].id)
    assert retry.status_code == 201
    assert retry.get_json()["archivo_id"] != old_id
    assert _count_vinculos_con_sha(d["item_a"].id, PDF_SHA) == 1


def test_rejected_mantiene_422_sin_nuevos_registros(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        aid = intent.get_json()["archivo_id"]
    arch = Archivo.query.get(aid)
    link = (
        db.session.query(RutaItemArchivo)
        .filter(RutaItemArchivo.archivo_id == aid)
        .one()
    )
    arch.status = "REJECTED"
    link.content_sha256 = PDF_SHA.lower()
    db.session.commit()
    archivos_antes = db.session.query(Archivo).count()
    vinculos_antes = db.session.query(RutaItemArchivo).count()
    with app.test_client() as client:
        retry = _create_intent(client, d["item_a"].id, d["user_a"].id)
    assert retry.status_code == 422
    assert retry.get_json().get("code") == MEDIA_STATE_INVALID
    assert db.session.query(Archivo).count() == archivos_antes
    assert db.session.query(RutaItemArchivo).count() == vinculos_antes


def test_ready_idempotencia_sin_cambios(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    with app.test_client() as client:
        intent = _create_intent(client, d["item_a"].id, d["user_a"].id)
        data = _simulate_upload_and_complete(client, d["user_a"].id, intent)
        aid = data["archivo_id"]
        retry = _create_intent(client, d["item_a"].id, d["user_a"].id)
    assert retry.status_code == 201
    body = retry.get_json()
    assert body["archivo_id"] == aid
    assert body["status"] == "READY"
    assert _count_vinculos_activos(d["item_a"].id) == 1


def test_delete_y_reintento_concurrentes_sin_500(app, client, app_ctx, scope_fixture) -> None:
    d = scope_fixture
    item_id = d["item_a"].id
    user_id = d["user_a"].id
    with app.test_client() as client:
        intent = _create_intent(client, item_id, user_id)
        data = _simulate_upload_and_complete(client, user_id, intent)
        archivo_id = data["archivo_id"]

    def _delete():
        with app.app_context():
            with app.test_client() as c:
                return c.delete(f"/archivos/{archivo_id}", headers=_auth_headers(user_id))

    def _intent():
        with app.app_context():
            with app.test_client() as c:
                return _create_intent(c, item_id, user_id)

    statuses: list[int] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_delete)]
        futures += [pool.submit(_intent) for _ in range(3)]
        for f in as_completed(futures):
            statuses.append(f.result().status_code)

    assert all(s in (200, 201, 404) for s in statuses)
    assert not any(s >= 500 for s in statuses)
    with app.app_context():
        assert _count_vinculos_con_sha(item_id, PDF_SHA) <= 1
        assert _count_vinculos_activos(item_id) <= 1
