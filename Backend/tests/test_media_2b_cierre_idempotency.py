"""V1.1-MEDIA.2B — idempotencia POST cerrar Completar trabajo."""

from __future__ import annotations

import uuid
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_idempotency_service import (
    cerrar_completar_trabajo_idempotente,
    digest_cierre_payload,
)
from app.models import (
    Actuaciones,
    CatalogTipoActuacion,
    CompletarTrabajoCierreIdempotency,
    RutaItem,
)
from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item

_TIPO_CIERRE = "RATIFICACION DE CLAUSURA"


def _ensure_tipo_actuacion_catalog(nombre: str) -> None:
    if CatalogTipoActuacion.query.filter_by(nombre=nombre).first() is None:
        db.session.add(CatalogTipoActuacion(nombre=nombre))
        db.session.commit()


def _payload_minimo() -> CompletarTrabajoCierreCompletoIn:
    _ensure_tipo_actuacion_catalog(_TIPO_CIERRE)
    return CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": _TIPO_CIERRE,
            "resultado_cumplimiento_oficio": "CUMPLE",
            "observaciones_ejecucion": "pytest media 2b",
        }
    )


def test_misma_idempotency_key_no_duplica_cierre(app_ctx) -> None:
    item, _act, _ini, user = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(user.id)
    ruta_item_id = int(item.id)
    key = str(uuid.uuid4())
    payload = _payload_minimo().model_copy(update={"idempotency_key": key})

    row1 = cerrar_completar_trabajo_idempotente(
        ruta_item_id=ruta_item_id,
        payload=payload,
        ejecutado_por_user_id=user_id,
    )
    act_id_1 = int(row1["actuacion_id"])
    count_actas = db.session.query(Actuaciones).filter(Actuaciones.id == act_id_1).count()

    row2 = cerrar_completar_trabajo_idempotente(
        ruta_item_id=ruta_item_id,
        payload=payload,
        ejecutado_por_user_id=user_id,
    )
    assert row2["actuacion_id"] == act_id_1
    assert (
        db.session.query(CompletarTrabajoCierreIdempotency)
        .filter_by(ruta_item_id=ruta_item_id, idempotency_key=key.lower())
        .count()
        == 1
    )
    assert db.session.query(Actuaciones).filter(Actuaciones.id == act_id_1).count() == count_actas

    fresh = db.session.get(RutaItem, ruta_item_id)
    assert fresh is not None
    assert fresh.estado_ruta_item == "FINALIZADO"


def test_idempotency_key_payload_distinto_falla(app_ctx) -> None:
    item, _act, _ini, user = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(user.id)
    ruta_item_id = int(item.id)
    key = str(uuid.uuid4())
    p1 = _payload_minimo().model_copy(
        update={"idempotency_key": key, "observaciones_ejecucion": "uno"}
    )
    cerrar_completar_trabajo_idempotente(
        ruta_item_id=ruta_item_id,
        payload=p1,
        ejecutado_por_user_id=user_id,
    )
    p2 = _payload_minimo().model_copy(
        update={"idempotency_key": key, "observaciones_ejecucion": "dos"}
    )
    with pytest.raises(ValueError, match="idempotency_key"):
        cerrar_completar_trabajo_idempotente(
            ruta_item_id=ruta_item_id,
            payload=p2,
            ejecutado_por_user_id=user_id,
        )


def test_digest_excluye_claves_de_transporte(app_ctx) -> None:
    base = _payload_minimo()
    d1 = digest_cierre_payload(base.model_copy(update={"idempotency_key": "a"}))
    d2 = digest_cierre_payload(
        base.model_copy(
            update={
                "idempotency_key": "b",
                "evidencias_pendientes_al_cierre": True,
            }
        )
    )
    assert d1 == d2
