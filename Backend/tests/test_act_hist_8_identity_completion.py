"""ACT-HIST.8 — identidad operativa en Verificar e informar → Nueva inspección."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_to_row,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.utils.identity_operativa_mode import (
    COMPLETE_EXISTING,
    COMPLETE_HISTORICAL,
    prefill_identidad_verificar_informar,
    resolver_modo_identidad_operativa,
)
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    IniciadorRuta,
    Oficio,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)
from app.models.inspector import Inspector

from tests.test_act_hist_7_domicilio_auth_fix import _historical_payload, _mk_user
from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item, _ot_num


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _inspector_nombre() -> str:
    row = Inspector.query.first()
    if row is None:
        pytest.skip("Se requiere al menos un inspector en catálogo")
    return str(row.nombre)


def _rubro_nombre() -> str:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    return str(rub.nombre)


def _mk_historical_origin_act(suf: str) -> Actuaciones:
    calle = f"Hist8 {suf}"
    act = crear_actuacion_desde_payload(
        _historical_payload(
            calle=calle,
            numero="123",
            contrib_apellido="Pérez",
            contrib_nombre="Juan",
        )
    )
    db.session.flush()
    assert act.carga_solo_comprobacion is True
    assert act.titular_nombre_historico == "Juan"
    assert act.titular_apellido_historico == "Pérez"
    dom = Domicilio.query.get(act.domicilio_id)
    assert dom is not None
    assert dom.contribuyente_id is None
    assert dom.rubro_id is None
    return act


def _mk_verificar_item_from_origin(
    origin: Actuaciones,
    suf: str,
    *,
    work_dom_contrib: bool = False,
) -> tuple[RutaItem, Actuaciones, IniciadorRuta, User]:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere rubro en catálogo")
    u = _mk_user()
    origin_dom = Domicilio.query.get(origin.domicilio_id)
    dom_work = Domicilio(
        calle=origin_dom.calle,
        numero=origin_dom.numero,
        rubro_id=rub.id if work_dom_contrib else None,
        contribuyente_id=None,
    )
    db.session.add(dom_work)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=9)
    db.session.add(ot)
    db.session.flush()
    ofi = Oficio(numero_oficio=str(random.randint(1000, 99999)), anio=2026, causa=f"AH8_{suf}")
    db.session.add(ofi)
    db.session.flush()
    act_work = Actuaciones(
        fecha=date(2026, 9, 21),
        mes=9,
        anio=2026,
        tipo="REINSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom_work.id,
        carga_solo_comprobacion=False,
    )
    db.session.add(act_work)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=date(2026, 9, 21),
        anio=2026,
        mes=9,
        domicilio_id=dom_work.id,
        oficio_id=ofi.id,
        actuacion_id=origin.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=date(2026, 9, 21),
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item="EN_PROCESO",
        actuacion_id=act_work.id,
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.commit()
    return item, act_work, ini, u


def test_resolver_modo_historical_desde_origen(app_ctx) -> None:
    try:
        suf = uuid4().hex[:8]
        origin = _mk_historical_origin_act(suf)
        _item, act_work, ini, _u = _mk_verificar_item_from_origin(origin, suf)
        assert resolver_modo_identidad_operativa(ini, act_work) == COMPLETE_HISTORICAL
        assert act_work.carga_solo_comprobacion is False
    finally:
        db.session.rollback()


def test_resolver_modo_existing_desde_origen(app_ctx) -> None:
    try:
        suf = uuid4().hex[:8]
        item, act, ini, _u = _mk_reinspeccion_oficio_item(suf)
        ini.actuacion_id = act.id
        db.session.commit()
        assert resolver_modo_identidad_operativa(ini, act) == COMPLETE_EXISTING
    finally:
        db.session.rollback()


def test_prefill_historical_presenter(app_ctx) -> None:
    try:
        suf = uuid4().hex[:8]
        origin = _mk_historical_origin_act(suf)
        item, act_work, ini, _u = _mk_verificar_item_from_origin(origin, suf)
        pre = prefill_identidad_verificar_informar(ini, act_work)
        assert pre["identity_mode"] == COMPLETE_HISTORICAL
        assert pre["contrib_nombre"] == "Juan"
        assert pre["contrib_apellido"] == "Pérez"
        assert pre["doc_nro"] is None
        assert pre["rubro_nombre"] is None
        assert pre["calle"] == origin.domicilio.calle

        item_db = (
            db.session.query(RutaItem)
            .options(
                joinedload(RutaItem.iniciador_ruta),
                joinedload(RutaItem.actuacion).joinedload(Actuaciones.domicilio),
            )
            .filter(RutaItem.id == item.id)
            .one()
        )
        row = ruta_item_completar_trabajo_to_row(item_db)
        assert row.get("identity_mode") == COMPLETE_HISTORICAL
        assert row.get("contrib_nombre") == "Juan"
        assert row.get("doc_nro") is None
        assert row.get("rubro_nombre") is None
    finally:
        db.session.rollback()


def test_prefill_existing_presenter(app_ctx) -> None:
    try:
        suf = uuid4().hex[:8]
        item, act, ini, _u = _mk_reinspeccion_oficio_item(suf)
        ini.actuacion_id = act.id
        db.session.commit()
        doc = act.domicilio.contribuyente.documento
        rub = act.domicilio.rubro.nombre
        pre = prefill_identidad_verificar_informar(ini, act)
        assert pre["identity_mode"] == COMPLETE_EXISTING
        assert pre["doc_nro"] == str(doc)
        assert pre["rubro_nombre"] == rub
    finally:
        db.session.rollback()


def test_e2e_historical_materializa_identidad_y_preserva_origen(app_ctx) -> None:
    try:
        suf = uuid4().hex[:8]
        origin = _mk_historical_origin_act(suf)
        origin_id = origin.id
        origin_dom_id = origin.domicilio_id
        origin_snapshot = {
            "carga_solo_comprobacion": origin.carga_solo_comprobacion,
            "titular_nombre_historico": origin.titular_nombre_historico,
            "titular_apellido_historico": origin.titular_apellido_historico,
            "titular_razon_social_historica": origin.titular_razon_social_historica,
            "domicilio_id": origin.domicilio_id,
            "orden_trabajo_id": origin.orden_trabajo_id,
            "tipo": origin.tipo,
            "comprobacion_id": origin.comprobacion_id,
        }
        item, act_work, ini, u = _mk_verificar_item_from_origin(origin, suf)
        doc = str(random.randint(20_000_000, 29_000_000))
        rubro = _rubro_nombre()
        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": _unique_num(),
                "contrib_apellido": "Pérez",
                "contrib_nombre": "Juan",
                "doc_nro": doc,
                "rubro_nombre": rubro,
                "calle": origin.domicilio.calle,
                "numero": origin.domicilio.numero,
            }
        )
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )
        db.session.expunge_all()

        act_db = Actuaciones.query.get(act_work.id)
        origin_db = Actuaciones.query.get(origin_id)
        origin_dom = Domicilio.query.get(origin_dom_id)
        assert act_db is not None
        assert act_db.tipo == "VERIFICAR E INFORMAR"
        assert act_db.realizo_nueva_inspeccion is True
        assert act_db.inspeccion is not None
        assert act_db.domicilio is not None
        assert act_db.domicilio.contribuyente is not None
        assert str(act_db.domicilio.contribuyente.documento) == doc
        assert act_db.domicilio.rubro is not None
        assert act_db.domicilio.rubro.nombre == rubro

        assert origin_db is not None
        for k, v in origin_snapshot.items():
            assert getattr(origin_db, k) == v
        assert origin_dom is not None
        assert origin_dom.contribuyente_id is None
        assert origin_dom.rubro_id is None
        if act_db.domicilio_id != origin_dom_id:
            assert act_db.domicilio.contribuyente_id is not None
            assert act_db.domicilio.rubro_id is not None
    finally:
        db.session.rollback()


def test_e2e_existing_preserva_identidad(app_ctx) -> None:
    try:
        suf = uuid4().hex[:8]
        item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
        ini.actuacion_id = act.id
        db.session.commit()
        doc = str(act.domicilio.contribuyente.documento)
        rubro = act.domicilio.rubro.nombre
        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": _unique_num(),
            }
        )
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )
        db.session.expunge_all()
        act_db = Actuaciones.query.get(act.id)
        assert act_db is not None
        assert act_db.tipo == "VERIFICAR E INFORMAR"
        assert str(act_db.domicilio.contribuyente.documento) == doc
        assert act_db.domicilio.rubro.nombre == rubro
    finally:
        db.session.rollback()


def test_tampering_existing_rechaza(app_ctx) -> None:
    try:
        suf = uuid4().hex[:8]
        item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
        ini.actuacion_id = act.id
        db.session.commit()
        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": _unique_num(),
                "doc_nro": "99999999",
                "rubro_nombre": "RubroInventado",
                "contrib_apellido": "Otro",
                "contrib_nombre": "Titular",
            }
        )
        with pytest.raises(ValueError, match="no coincide"):
            cerrar_completar_trabajo_por_ruta_item(
                ruta_item_id=item.id,
                payload=payload,
                ejecutado_por_user_id=u.id,
            )
    finally:
        db.session.rollback()


def test_sin_nueva_inspeccion_no_materializa_historico(app_ctx) -> None:
    try:
        suf = uuid4().hex[:8]
        origin = _mk_historical_origin_act(suf)
        contrib_before = Contribuyente.query.count()
        item, act_work, _ini, u = _mk_verificar_item_from_origin(origin, suf)
        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": False,
            }
        )
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )
        db.session.expunge_all()
        act_db = Actuaciones.query.get(act_work.id)
        assert act_db is not None
        dom = act_db.domicilio
        assert dom is None or dom.contribuyente_id is None
        assert Contribuyente.query.count() == contrib_before
    finally:
        db.session.rollback()
