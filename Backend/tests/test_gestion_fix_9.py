"""GESTIÓN-FIX.9 — circuito canónico, actas RN, lifecycle de reintentos."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.actuacion_reencolado_service import (
    actuacion_bloqueada_por_intento_posterior,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.actuaciones.utils.circuito_operativo import (
    CIRCUITO_REINSPECCION_NOTIFICACION,
    build_actuacion_grid_validation_context,
    omite_identidad_operativa,
)
from app.domains.actuaciones.attach.clausura import attach_clausura
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.models import Actuaciones, CatalogContraproducencia, IniciadorRuta, RutaItem

from tests.test_gestion_fix_5 import _republicar_iniciador_generico
from tests.test_gestion_fix_8 import (
    _cerrar_rn_realizado,
    _ensure_catalog_contraproducencia,
    _mk_reinspeccion_notificacion_item,
    _ot_numerica,
    _prep_ot_numerica_unica,
)
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_acta_num() -> str:
    return f"{random.randint(100000, 999999):06d}"


def test_f9_presenter_rn_realizada_con_actas_visita(app_ctx) -> None:
    """Presenter: actas de visita en GET; notificación origen separada."""
    item, act, ini, u, noti = _mk_reinspeccion_notificacion_item()
    acta_ins = _unique_acta_num()
    acta_comp = _unique_acta_num()
    acta_clau = _unique_acta_num()
    acta_dec = _unique_acta_num()
    _cerrar_rn_realizado(
        item_id=int(item.id),
        user_id=int(u.id),
        acta_inspeccion=acta_ins,
        acta_comprobacion=acta_comp,
    )
    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    attach_clausura(act_db, {"acta_num": acta_clau}, crear=False)
    attach_decomiso(act_db, {"acta_num": acta_dec, "kilos_total": 5}, crear=False)
    db.session.commit()
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act.id)
    ini_db = db.session.get(IniciadorRuta, ini.id)
    grid = actuacion_to_grid_row(act_db, iniciador_desde_ruta=ini_db)

    assert str(grid.get("acta_inspeccion_num")) == acta_ins
    assert str(grid.get("acta_comprobacion_num")) == acta_comp
    assert str(grid.get("acta_clausura_num")) == acta_clau
    assert str(grid.get("acta_decomiso_num")) == acta_dec
    assert grid.get("acta_notificacion_num") in (None, "")
    origen = grid.get("origen_reinspeccion_notificacion") or {}
    assert str(origen.get("notificacion_acta_numero")) == str(noti.numero_acta)


def test_f9_omite_identidad_rn_en_validation_context(app_ctx) -> None:
    """Backend: contexto unificado omite identidad para RN."""
    _item, act, _ini, _u, _noti = _mk_reinspeccion_notificacion_item()
    ctx = build_actuacion_grid_validation_context(int(act.id))
    assert ctx["circuito_operativo"] == CIRCUITO_REINSPECCION_NOTIFICACION
    assert ctx["omite_identidad_operativa"] is True
    assert omite_identidad_operativa(CIRCUITO_REINSPECCION_NOTIFICACION) is True


def test_f9_rn_grid_sin_calle_cuando_omite_identidad(app_ctx) -> None:
    """RN: PUT sin calle no dispara reglas de domicilio."""
    item, act, ini, u, _noti = _mk_reinspeccion_notificacion_item()
    _cerrar_rn_realizado(item_id=int(item.id), user_id=int(u.id), acta_inspeccion=_unique_acta_num())
    act_db = _prep_ot_numerica_unica(int(act.id))
    from app.models import Inspector

    ins_rows = Inspector.query.limit(2).all()
    if len(ins_rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores")
    row = ActuacionGridRowIn.model_validate(
        {
            "id": int(act_db.id),
            "orden_trabajo_numero": _ot_numerica(act_db),
            "fecha_actuacion": act_db.fecha.strftime("%d/%m/%Y"),
            "tipo_actuacion": "REINSPECCION",
            "contraproducencia": "LOCAL CERRADO",
            "inspector1": ins_rows[0].nombre,
            "inspector2": ins_rows[1].nombre,
            "actas_a_quitar": ["INSPECCION"],
        },
        context=build_actuacion_grid_validation_context(int(act_db.id)),
    )
    assert row.contraproducencia == "LOCAL CERRADO"


def test_f9_r2_relevamiento_replanificado_sin_ejecutar_permite_corregir_a(app_ctx) -> None:
    """R2: Act A editable y corregible con B publicada pero sin ejecución real."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act1_id, ini_id, user_id, _, _ = _mk_relevamiento_en_ruta_publicada(suf)
    act1 = db.session.get(Actuaciones, act1_id)
    assert act1 is not None
    ot_num = act1.orden_trabajo.numero_acta if act1.orden_trabajo else "000001"
    fecha = act1.fecha.strftime("%d/%m/%Y") if act1.fecha else "10/06/2026"

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    item2 = _republicar_iniciador_generico(ini_db, user_id, date(2099, 1, 15))
    item2_id = int(item2.id)
    assert item2.actuacion_id is not None

    bloq, _ = actuacion_bloqueada_por_intento_posterior(int(act1_id))
    assert bloq is False

    from app.models import Inspector

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores")
    row = ActuacionGridRowIn.model_validate(
        {
            "id": act1_id,
            "orden_trabajo_numero": ot_num,
            "fecha_actuacion": fecha,
            "tipo_actuacion": "INSPECCION",
            "calle": "San Martín",
            "numero": "100",
            "rubro_nombre": "Bar",
            "doc_nro": "30123456",
            "contrib_apellido": "Titular",
            "contrib_nombre": "Prueba",
            "inspector1": inspectores[0].nombre,
            "inspector2": inspectores[1].nombre,
            "acta_inspeccion_num": f"{random.randint(0, 999999):06d}",
            "limpiar_contraproducencia": True,
            "contraproducencia": None,
        }
    )
    actualizar_actuacion(act1_id, map_actuacion_row(row))
    db.session.expunge_all()

    act1_db = db.session.get(Actuaciones, act1_id)
    ini_final = db.session.get(IniciadorRuta, ini_id)
    item2_db = db.session.get(RutaItem, item2_id)
    assert act1_db is not None
    assert act1_db.contraproducencia is None
    assert ini_final is not None
    assert ini_final.estado_iniciador == "CUMPLIDO"
    assert item2_db is not None
    assert item2_db.deleted_at is not None
