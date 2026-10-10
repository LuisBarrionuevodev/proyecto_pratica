"""HOTFIX V1.1-CIERRE-INSPECCION.1 — habilitación obligatoria y NO PERMITE INSPECCIÓN."""

from __future__ import annotations

import random
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    planificable_iniciadores_base_query,
)
from app.models import Actuaciones, Comprobacion, IniciadorRuta, RutaItem

from tests.test_gestion_fix_3 import _ensure_catalog_contraproducencia
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from tests.test_inspeccion_checklist import _base_create_payload, _item_id, items_catalogo


def _motivo_no_permite() -> str:
    return "No Permite la Inspección"


def test_inspeccion_sin_tiene_habilitacion_422(app_ctx, items_catalogo) -> None:
    id_bano = _item_id(items_catalogo, "TIENE_BANO")
    with pytest.raises(ValidationError) as exc:
        crear_actuacion_desde_payload(
            _base_create_payload(
                contraproducencia=None,
                items_acta_inspeccion=[{"item_id": id_bano, "estado": "BIEN"}],
            )
        )
    assert "habilitación" in str(exc.value).lower()


def test_inspeccion_habilitacion_si_ok(app_ctx, items_catalogo) -> None:
    id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
    act = crear_actuacion_desde_payload(
        _base_create_payload(
            contraproducencia=None,
            items_acta_inspeccion=[{"item_id": id_hab, "valor_si_no": True}],
        )
    )
    assert act.id is not None


def test_inspeccion_habilitacion_no_ok(app_ctx, items_catalogo) -> None:
    id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
    act = crear_actuacion_desde_payload(
        _base_create_payload(
            contraproducencia=None,
            items_acta_inspeccion=[{"item_id": id_hab, "valor_si_no": False}],
        )
    )
    assert act.id is not None


def test_no_permite_sin_comprobacion_reencola(app_ctx) -> None:
    _ensure_catalog_contraproducencia("NO PERMITE INSPECCION")
    suf = uuid4().hex[:8]
    item_id, _act_id, ini_id, user_id, _rb, _dom = _mk_relevamiento_en_ruta_publicada(suf)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "NO PERMITE INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini = db.session.get(IniciadorRuta, ini_id)
    item = db.session.get(RutaItem, item_id)
    assert ini is not None and ini.estado_iniciador == "PENDIENTE"
    assert item is not None and item.estado_ejecucion == "NO_REALIZADO"
    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id in planif_ids


def test_no_permite_con_comprobacion_valida_cumplido_sin_reencolado(app_ctx) -> None:
    _ensure_catalog_contraproducencia("NO PERMITE INSPECCION")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _rb, _dom = _mk_relevamiento_en_ruta_publicada(suf)
    acta = f"{random.randint(100000, 999999):06d}"
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "contraproducencia": "NO PERMITE INSPECCION",
                "acta_comprobacion_num": acta,
                "comprobacion_motivo": _motivo_no_permite(),
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini = db.session.get(IniciadorRuta, ini_id)
    item = db.session.get(RutaItem, item_id)
    act = db.session.get(Actuaciones, act_id)
    assert ini is not None and ini.estado_iniciador == "CUMPLIDO"
    assert item is not None and item.estado_ejecucion == "REALIZADO"
    assert act is not None and act.comprobacion_id is not None
    comp = db.session.get(Comprobacion, int(act.comprobacion_id))
    assert comp is not None and comp.motivo == _motivo_no_permite()
    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id not in planif_ids


def test_no_permite_numero_sin_motivo_422(app_ctx) -> None:
    _ensure_catalog_contraproducencia("NO PERMITE INSPECCION")
    with pytest.raises(ValidationError):
        CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "contraproducencia": "NO PERMITE INSPECCION",
                "acta_comprobacion_num": "123456",
            }
        )


def test_no_permite_motivo_sin_numero_422(app_ctx) -> None:
    _ensure_catalog_contraproducencia("NO PERMITE INSPECCION")
    with pytest.raises(ValidationError):
        CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "contraproducencia": "NO PERMITE INSPECCION",
                "comprobacion_motivo": _motivo_no_permite(),
            }
        )


def test_no_permite_motivo_distinto_422(app_ctx) -> None:
    _ensure_catalog_contraproducencia("NO PERMITE INSPECCION")
    with pytest.raises(ValidationError):
        CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "contraproducencia": "NO PERMITE INSPECCION",
                "acta_comprobacion_num": "123456",
                "comprobacion_motivo": "Falta de Higiene",
            }
        )


def test_local_cerrado_sigue_reencolando(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, _act_id, ini_id, user_id, _rb, _dom = _mk_relevamiento_en_ruta_publicada(suf)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini = db.session.get(IniciadorRuta, ini_id)
    assert ini is not None and ini.estado_iniciador == "PENDIENTE"
