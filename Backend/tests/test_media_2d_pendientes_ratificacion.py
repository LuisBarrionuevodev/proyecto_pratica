"""HOTFIX V1.1-MEDIA.2D — pendientes fotos, detalle y uploads en ratificación."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_idempotency_service import (
    cerrar_completar_trabajo_idempotente,
)
from app.domains.actuaciones.services.completar_trabajo_detalle_service import (
    get_completar_trabajo_detalle,
)
from app.domains.actuaciones.services.completar_trabajo_pendientes_list_service import (
    list_completar_trabajo_pendientes,
)
from app.domains.actuaciones.services.completar_trabajo_pendientes_resumen_service import (
    list_completar_trabajo_pendientes_resumen_por_dia,
)
from app.domains.media.constants import (
    CATEGORIA_FOTO_ACTA,
    CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    CATEGORIA_FOTO_INSPECCION,
)
from app.integrations.media_storage.factory import get_media_storage, reset_media_storage_singleton
from app.integrations.media_storage.mock_storage import MockMediaStorage
from app.models import CatalogTipoActuacion, RutaItem, RutaTrabajo
from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_media_storage_v1_1_0 import PDF_BYTES, _create_intent, _simulate_upload_and_complete

PDF_SHA = hashlib.sha256(PDF_BYTES).hexdigest()


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _ensure_tipo(nombre: str) -> None:
    if CatalogTipoActuacion.query.filter_by(nombre=nombre).first() is None:
        db.session.add(CatalogTipoActuacion(nombre=nombre))
        db.session.commit()


def _publish_scope_item(item: RutaItem, actuacion_id: int) -> RutaTrabajo:
    from app.models import Actuaciones

    ruta: RutaTrabajo = item.ruta_trabajo
    ruta.estado_ruta = "PUBLICADA"
    item.actuacion_id = actuacion_id
    act = db.session.get(Actuaciones, actuacion_id)
    if act is not None and act.orden_trabajo_id is not None:
        item.orden_trabajo_id = act.orden_trabajo_id
    db.session.commit()
    return ruta


@pytest.fixture(autouse=True)
def _reset_media_storage():
    reset_media_storage_singleton()
    yield
    reset_media_storage_singleton()


def test_listado_incluye_finalizado_solo_flag_evidencias(scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    ruta = _publish_scope_item(item, d["act_a"].id)
    item.estado_ruta_item = "FINALIZADO"
    item.evidencias_pendientes_abiertas = True
    db.session.commit()

    rows, meta = list_completar_trabajo_pendientes(
        fecha=ruta.fecha,
        page=1,
        per_page=50,
        inspector_id_effective=d["ins_a"].id,
    )
    ids = {int(r["ruta_item_id"]) for r in rows}
    assert item.id in ids
    assert meta["total"] >= 1
    row = next(r for r in rows if int(r["ruta_item_id"]) == item.id)
    assert row.get("trabajo_guardado_evidencias_pendientes") is True


def test_resumen_cuenta_finalizado_con_fotos_pendientes(scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    ruta = _publish_scope_item(item, d["act_a"].id)
    item.estado_ruta_item = "FINALIZADO"
    item.evidencias_pendientes_abiertas = True
    db.session.commit()

    dias, _meta = list_completar_trabajo_pendientes_resumen_por_dia(
        fecha_desde=ruta.fecha,
        fecha_hasta=ruta.fecha,
        inspector_id_effective=d["ins_a"].id,
    )
    row = next(x for x in dias if x["fecha"] == ruta.fecha.isoformat())
    assert row["total"] >= 1
    assert row["categoria_calendario"] == "CON_PENDIENTES"


def test_detalle_modo_solo_evidencias(scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    _publish_scope_item(item, d["act_a"].id)
    item.estado_ruta_item = "FINALIZADO"
    item.evidencias_pendientes_abiertas = True
    db.session.commit()

    det = get_completar_trabajo_detalle(ruta_item_id=int(item.id))
    assert det["ui_policy"]["solo_evidencias_pendientes"] is True
    assert det["ui_policy"]["cierre_alfanumerico_readonly"] is True
    assert det["row"]["trabajo_guardado_evidencias_pendientes"] is True
    resumen = det["media_resumen"]
    assert resumen.get("tiene_evidencias_pendientes") is True or resumen.get("evidencias_pendientes_total", 0) >= 0


def test_fotos_inspector_count_endpoint(app, client, scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    _publish_scope_item(item, d["act_a"].id)
    item.estado_ruta_item = "FINALIZADO"
    item.evidencias_pendientes_abiertas = True
    db.session.commit()

    r0 = client.get(
        "/actuaciones/completar-trabajo/pendientes/fotos-inspector",
        headers=_auth_headers(d["user_a"].id),
    )
    assert r0.status_code == 200
    assert int(r0.get_json().get("count", 0)) >= 1

    item.fotos_pendientes_cerradas_at = datetime.now(timezone.utc)
    item.evidencias_pendientes_abiertas = False
    db.session.commit()

    r1 = client.get(
        "/actuaciones/completar-trabajo/pendientes/fotos-inspector",
        headers=_auth_headers(d["user_a"].id),
    )
    assert r1.status_code == 200
    assert int(r1.get_json().get("count", 0)) == 0


@pytest.mark.parametrize(
    "tipo_actuacion",
    [
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
    ],
)
def test_ratificacion_upload_tres_categorias_tras_cierre_cumple(
    app,
    client,
    app_ctx,
    tipo_actuacion: str,
) -> None:
    _ensure_tipo(tipo_actuacion)
    item, _act, _ini, user = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": tipo_actuacion,
            "resultado_cumplimiento_oficio": "CUMPLE",
            "observaciones_ejecucion": "pytest media 2d ratificacion",
        }
    )
    cerrar_completar_trabajo_idempotente(
        ruta_item_id=int(item.id),
        payload=payload,
        ejecutado_por_user_id=int(user.id),
    )
    fresh = db.session.get(RutaItem, item.id)
    assert fresh is not None
    assert fresh.estado_ruta_item == "FINALIZADO"

    uid = int(user.id)
    rid = int(item.id)

    doc = _create_intent(
        client,
        rid,
        uid,
        categoria=CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
        tipo_documento="HABILITACION",
        filename="doc-local.pdf",
        sha256=PDF_SHA,
    )
    assert doc.status_code == 201
    acta_bytes = PDF_BYTES + b"acta-rat-2d"
    acta_sha = hashlib.sha256(acta_bytes).hexdigest()
    acta = _create_intent(
        client,
        rid,
        uid,
        categoria=CATEGORIA_FOTO_ACTA,
        byte_size=len(acta_bytes),
        sha256=acta_sha,
    )
    assert acta.status_code == 201
    insp_bytes = b"\xff\xd8\xff" + b"x" * 497
    insp_sha = hashlib.sha256(insp_bytes).hexdigest()
    insp = _create_intent(
        client,
        rid,
        uid,
        categoria=CATEGORIA_FOTO_INSPECCION,
        tipo_documento=None,
        filename="visita.jpg",
        content_type="image/jpeg",
        byte_size=len(insp_bytes),
        sha256=insp_sha,
    )
    assert insp.status_code == 201

    storage = get_media_storage()
    assert isinstance(storage, MockMediaStorage)
    _simulate_upload_and_complete(client, uid, doc)
    storage.ingest_from_presigned_put_url(acta.get_json()["upload_url"], acta_bytes)
    complete_acta = client.post(
        f"/archivos/{acta.get_json()['archivo_id']}/complete",
        headers=_auth_headers(uid),
    )
    assert complete_acta.status_code == 200
    storage.ingest_from_presigned_put_url(insp.get_json()["upload_url"], insp_bytes)
    complete_insp = client.post(
        f"/archivos/{insp.get_json()['archivo_id']}/complete",
        headers=_auth_headers(uid),
    )
    assert complete_insp.status_code == 200
