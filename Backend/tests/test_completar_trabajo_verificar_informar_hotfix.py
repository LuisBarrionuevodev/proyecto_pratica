"""HOTFIX — Verificar e informar con nueva inspección: contribuyente prefill y cierre."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_to_row,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
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

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_oficio_sin_contrib_en_act(suf: str) -> tuple[RutaItem, Actuaciones, IniciadorRuta, User, Oficio]:
    """Actuación publicada sin contribuyente; iniciador conserva titular en su domicilio."""
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    u = User(
        username=f"u_vi_{suf}",
        email=f"vi_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    doc = str(random.randint(10_000_000, 40_000_000))
    c = Contribuyente(apellido="Origen", nombre="Titular", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom_ini = Domicilio(calle=f"Vi_{suf}", numero="10", rubro_id=rub.id, contribuyente_id=c.id)
    dom_act = Domicilio(calle=f"ViAct_{suf}", numero="11", rubro_id=rub.id, contribuyente_id=None)
    db.session.add_all([dom_ini, dom_act])
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    ofi = Oficio(numero_oficio=str(random.randint(1000, 99999)), anio=2026, causa=f"VI_{suf}")
    db.session.add(ofi)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 6, 10),
        mes=6,
        anio=2026,
        tipo="REINSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom_act.id,
    )
    db.session.add(act)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=date(2026, 6, 10),
        anio=2026,
        mes=6,
        domicilio_id=dom_ini.id,
        oficio_id=ofi.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=date(2026, 6, 10),
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
        actuacion_id=act.id,
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.commit()
    return item, act, ini, u, ofi


def test_presenter_enrich_contrib_desde_domicilio_iniciador(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, _ini, _u, _ofi = _mk_oficio_sin_contrib_en_act(suf)
    item_id = item.id
    db.session.expunge_all()
    item_db = db.session.get(RutaItem, item_id)
    assert item_db is not None
    row = ruta_item_completar_trabajo_to_row(item_db)
    assert row.get("doc_nro")
    assert row.get("contrib_apellido") == "Origen"
    assert row.get("contrib_nombre") == "Titular"


def test_verificar_nueva_inspeccion_cierra_con_contrib_prefill(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
    ofi_id = ini.oficio_id
    doc = act.domicilio.contribuyente.documento if act.domicilio and act.domicilio.contribuyente else None
    assert doc

    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "acta_inspeccion_num": _unique_num(),
            "doc_nro": str(doc),
            "contrib_apellido": "ST4",
            "contrib_nombre": "Tit",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act.id)
    ini_db = IniciadorRuta.query.get(ini.id)
    assert act_db is not None
    assert act_db.tipo == "VERIFICAR E INFORMAR"
    assert act_db.domicilio is not None
    assert act_db.domicilio.contribuyente is not None
    assert str(act_db.domicilio.contribuyente.documento) == str(doc)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "VERIFICAR_INFORMAR_OFICIO"
    assert ini_db.oficio_id == ofi_id
    assert ini_db.estado_iniciador == "CUMPLIDO"


def _mk_oficio_sin_contrib_en_act_ni_ini(suf: str) -> tuple[RutaItem, Actuaciones, IniciadorRuta, User]:
    """Ni actuación ni iniciador tienen contribuyente vinculado."""
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    u = User(
        username=f"u_vi2_{suf}",
        email=f"vi2_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    dom_ini = Domicilio(calle=f"Vi2_{suf}", numero="10", rubro_id=rub.id, contribuyente_id=None)
    dom_act = Domicilio(calle=f"ViAct2_{suf}", numero="11", rubro_id=rub.id, contribuyente_id=None)
    db.session.add_all([dom_ini, dom_act])
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    ofi = Oficio(numero_oficio=str(random.randint(1000, 99999)), anio=2026, causa=f"VI2_{suf}")
    db.session.add(ofi)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 6, 10),
        mes=6,
        anio=2026,
        tipo="REINSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom_act.id,
    )
    db.session.add(act)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=date(2026, 6, 10),
        anio=2026,
        mes=6,
        domicilio_id=dom_ini.id,
        oficio_id=ofi.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=date(2026, 6, 10),
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
        actuacion_id=act.id,
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.commit()
    return item, act, ini, u


def test_verificar_nueva_inspeccion_con_contrib_manual_cierra_ok(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, _ini, u = _mk_oficio_sin_contrib_en_act_ni_ini(suf)
    doc = str(random.randint(10_000_000, 40_000_000))
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "acta_inspeccion_num": _unique_num(),
            "doc_nro": doc,
            "contrib_apellido": "Manual",
            "contrib_nombre": "Carga",
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
    assert act_db.domicilio is not None
    assert act_db.domicilio.contribuyente is not None
    assert str(act_db.domicilio.contribuyente.documento) == doc


def test_verificar_sin_nueva_inspeccion_no_exige_contrib(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, ini, u = _mk_reinspeccion_oficio_item(suf)
    ofi_id = ini.oficio_id
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
    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "VERIFICAR_INFORMAR_OFICIO"
    assert ini_db.oficio_id == ofi_id


def test_ratificacion_clausura_sin_regression(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, ini, u = _mk_reinspeccion_oficio_item(suf)
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "RATIFICACION_CLAUSURA_OFICIO"
    assert ini_db.estado_iniciador == "CUMPLIDO"
