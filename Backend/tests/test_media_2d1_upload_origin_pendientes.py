"""HOTFIX V1.1-MEDIA.2D.1 — origen de carga vs pendientes Completar trabajo."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_fotos_pendientes_count_service import (
    count_completar_trabajo_fotos_pendientes_inspector,
)
from app.domains.actuaciones.services.completar_trabajo_pendientes_list_service import (
    list_completar_trabajo_pendientes,
)
from app.models import RutaItem, RutaTrabajo
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_media_storage_v1_1_0 import PDF_BYTES, _create_intent

PDF_SHA = hashlib.sha256(PDF_BYTES).hexdigest()


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


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


def test_finalizado_pending_mis_trabajos_no_listado_ni_contador(app, client, scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    ruta = _publish_scope_item(item, d["act_a"].id)
    item.estado_ruta_item = "FINALIZADO"
    item.evidencias_pendientes_abiertas = False
    db.session.commit()

    resp = _create_intent(
        client,
        item.id,
        d["user_a"].id,
        upload_origin="MIS_TRABAJOS",
        sha256=PDF_SHA,
    )
    assert resp.status_code == 201

    rows, meta = list_completar_trabajo_pendientes(
        fecha=ruta.fecha,
        page=1,
        per_page=50,
        inspector_id_effective=d["ins_a"].id,
    )
    assert item.id not in {int(r["ruta_item_id"]) for r in rows}

    count = count_completar_trabajo_fotos_pendientes_inspector(
        inspector_id_effective=int(d["ins_a"].id),
    )
    assert count == 0


def test_finalizado_evidencias_abiertas_si_listado(scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    ruta = _publish_scope_item(item, d["act_a"].id)
    item.estado_ruta_item = "FINALIZADO"
    item.evidencias_pendientes_abiertas = True
    db.session.commit()

    rows, _meta = list_completar_trabajo_pendientes(
        fecha=ruta.fecha,
        page=1,
        per_page=50,
        inspector_id_effective=d["ins_a"].id,
    )
    assert item.id in {int(r["ruta_item_id"]) for r in rows}


def test_finalizar_por_ahora_sigue_excluido(scope_fixture) -> None:
    d = scope_fixture
    item: RutaItem = d["item_a"]
    ruta = _publish_scope_item(item, d["act_a"].id)
    item.estado_ruta_item = "FINALIZADO"
    item.evidencias_pendientes_abiertas = True
    item.fotos_pendientes_cerradas_at = datetime.now(timezone.utc)
    db.session.commit()

    rows, _meta = list_completar_trabajo_pendientes(
        fecha=ruta.fecha,
        page=1,
        per_page=50,
        inspector_id_effective=d["ins_a"].id,
    )
    assert item.id not in {int(r["ruta_item_id"]) for r in rows}
