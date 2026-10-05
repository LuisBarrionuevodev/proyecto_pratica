"""Observaciones de la visita (RutaItem) en detalle y PUT de Gestión de Actuaciones."""

from __future__ import annotations

from app.database import db
from app.domains.actuaciones.presenters.actuacion_gestion_seguimiento_presenter import (
    present_actuacion_gestion_detalle,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.models import Actuaciones, RutaItem
from tests.test_acta_seguimiento_v1_1 import (
    _mk_relevamiento_item_en_proceso,
    _payload_relevamiento_inspeccion,
    _unique_ot,
)


def _cerrar_con_observaciones(texto: str) -> tuple[Actuaciones, int]:
    item, u, _dom = _mk_relevamiento_item_en_proceso()
    body = _payload_relevamiento_inspeccion(acta=_unique_ot(), solicita=False)
    body["observaciones_ejecucion"] = texto
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(body),
        ejecutado_por_user_id=u.id,
    )
    act = Actuaciones.query.get(item.actuacion_id)
    assert act is not None
    return act, u.id


def test_gestion_detalle_expone_observaciones_tras_cierre(app_ctx) -> None:
    act, _uid = _cerrar_con_observaciones("Puerta cerrada, se volverá")
    row = present_actuacion_gestion_detalle(act)
    assert row.get("ruta_item_id") is not None
    assert row.get("observaciones_ejecucion") == "Puerta cerrada, se volverá"


def test_gestion_put_actualiza_observaciones_en_ruta_item(app_ctx) -> None:
    act, uid = _cerrar_con_observaciones("Texto inicial")
    actualizar_actuacion(
        int(act.id),
        {"observaciones_ejecucion": "Texto editado desde CRUD"},
        actor_user_id=uid,
    )
    db.session.expire_all()
    item = (
        RutaItem.query.filter_by(actuacion_id=act.id, deleted_at=None)
        .order_by(RutaItem.id.desc())
        .first()
    )
    assert item is not None
    assert item.observaciones_ejecucion == "Texto editado desde CRUD"
    row = present_actuacion_gestion_detalle(Actuaciones.query.get(act.id))
    assert row["observaciones_ejecucion"] == "Texto editado desde CRUD"


def test_gestion_detalle_observaciones_vacio_es_none(app_ctx) -> None:
    act, _uid = _cerrar_con_observaciones("")
    row = present_actuacion_gestion_detalle(act)
    assert row.get("observaciones_ejecucion") is None
