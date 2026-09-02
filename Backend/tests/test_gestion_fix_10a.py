"""GESTIÓN-FIX.10A — geocode/COW, expediente RN, inspectores."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.database import db
from app.domains.actuaciones.audit.inspectores_actuaciones_audit import (
    list_active_inspector_nombres_for_actuacion,
)
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.domicilios.services.domicilio_update_service import _aplicar_rubro_contrib_seguro
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    DomicilioGeocode,
    Inspector,
    OrdenTrabajo,
    Rubro,
    User,
)
from app.models.actuaciones_inspector import actuaciones_inspector


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_user() -> User:
    u = User(
        username=f"fix10a_{uuid4().hex[:8]}",
        email=f"fix10a_{uuid4().hex[:8]}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_actuacion_con_geocode() -> tuple[Actuaciones, Domicilio, Rubro, Contribuyente]:
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=f"RubFix10a_{uuid4().hex[:6]}")
        db.session.add(rub)
        db.session.flush()
    contrib = Contribuyente(
        documento=f"30{random.randint(10000000, 99999999)}",
        apellido="Pérez",
        nombre="Juan",
    )
    db.session.add(contrib)
    db.session.flush()
    dom = Domicilio(
        calle=f"Chacabuco {uuid4().hex[:4]}",
        numero="230",
        rubro_id=rub.id,
        contribuyente_id=contrib.id,
    )
    db.session.add(dom)
    db.session.flush()
    geo = DomicilioGeocode(
        domicilio_id=dom.id,
        lat=-26.8245,
        lng=-65.2223,
        geo_status="OK",
    )
    db.session.add(geo)
    ot = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date.today(),
        anio=2026,
        mes=8,
        domicilio_id=dom.id,
        orden_trabajo_id=ot.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act, dom, rub, contrib


def test_a1_correccion_pura_sin_cow_ni_cambio_domicilio_id(app_ctx) -> None:
    """PUT full-row con mismo rubro/contrib no debe forzar COW ni perder domicilio_id."""
    act, dom, rub, contrib = _mk_actuacion_con_geocode()
    dom_id_antes = int(dom.id)
    geo_antes = DomicilioGeocode.query.filter_by(domicilio_id=dom_id_antes).first()
    assert geo_antes is not None

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren 2 inspectores")

    row = ActuacionGridRowIn.model_validate(
        {
            "id": act.id,
            "orden_trabajo_numero": act.orden_trabajo.numero_acta,
            "fecha_actuacion": act.fecha.strftime("%d/%m/%Y"),
            "tipo_actuacion": "INSPECCION",
            "calle": dom.calle,
            "numero": dom.numero,
            "rubro_nombre": rub.nombre,
            "doc_nro": contrib.documento,
            "contrib_apellido": contrib.apellido,
            "contrib_nombre": contrib.nombre,
            "inspector1": inspectores[0].nombre,
            "inspector2": inspectores[1].nombre,
            "acta_inspeccion_num": _ot_num(),
        }
    )
    act_id = int(act.id)
    actualizar_actuacion(act_id, map_actuacion_row(row))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert int(act_db.domicilio_id) == dom_id_antes
    geo_despues = DomicilioGeocode.query.filter_by(domicilio_id=dom_id_antes).first()
    assert geo_despues is not None
    assert float(geo_despues.lat) == pytest.approx(-26.8245)
    assert float(geo_despues.lng) == pytest.approx(-65.2223)


def test_a2_cow_misma_direccion_hereda_geocode(app_ctx) -> None:
    """COW legítimo por rubro distinto en domicilio compartido hereda geocode."""
    act, dom, rub, _contrib = _mk_actuacion_con_geocode()
    ot2 = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=8)
    db.session.add(ot2)
    db.session.flush()
    act2 = Actuaciones(
        fecha=date.today(),
        anio=2026,
        mes=8,
        domicilio_id=dom.id,
        orden_trabajo_id=ot2.id,
        tipo="INSPECCION",
    )
    db.session.add(act2)
    db.session.flush()

    otro_rub = Rubro(nombre=f"OtroRub_{uuid4().hex[:6]}")
    db.session.add(otro_rub)
    db.session.flush()

    dom_id_antes = int(dom.id)
    nuevo = _aplicar_rubro_contrib_seguro(
        dom,
        contribuyente=None,
        rubro=otro_rub,
        numero_tipo=None,
        contexto="ACTUACION",
        origen_id=int(act.id),
    )
    assert int(nuevo.id) != dom_id_antes
    geo_nuevo = DomicilioGeocode.query.filter_by(domicilio_id=int(nuevo.id)).first()
    assert geo_nuevo is not None
    assert float(geo_nuevo.lat) == pytest.approx(-26.8245)
    assert float(geo_nuevo.lng) == pytest.approx(-65.2223)


def test_b1_presenter_rn_expediente_no_bloquea_actuacion_total(app_ctx) -> None:
    """RN con notificación origen: actuacion_bloqueada_por_expediente permanece false."""
    from tests.test_gestion_fix_8 import _cerrar_rn_realizado, _mk_reinspeccion_notificacion_item

    item, act, _ini, _u, _noti = _mk_reinspeccion_notificacion_item()
    _cerrar_rn_realizado(
        item_id=int(item.id),
        user_id=int(_u.id),
        acta_inspeccion=f"{random.randint(100000, 999999):06d}",
    )
    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    grid = actuacion_to_grid_row(act_db)
    assert grid.get("notificacion_editable") is False
    assert grid.get("actuacion_bloqueada_por_expediente") is False


def test_c4_soft_deleted_inspector_excluido_del_presenter(app_ctx) -> None:
    act, _dom, _rub, _contrib = _mk_actuacion_con_geocode()
    ins_rows = Inspector.query.limit(2).all()
    if len(ins_rows) < 2:
        pytest.skip("Se requieren 2 inspectores")
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=act.id,
            inspector_id=ins_rows[0].id,
        )
    )
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=act.id,
            inspector_id=ins_rows[1].id,
            deleted_at=db.func.current_timestamp(),
        )
    )
    db.session.commit()

    nombres = list_active_inspector_nombres_for_actuacion(int(act.id))
    assert nombres == [ins_rows[0].nombre]
    grid = actuacion_to_grid_row(db.session.get(Actuaciones, act.id))
    assert grid.get("inspectores") == [ins_rows[0].nombre]


def test_c5_actualizar_sin_inspectores_en_payload_conserva_relacion(app_ctx) -> None:
    """Corrección sin key inspectores no borra vínculos existentes."""
    act, dom, rub, contrib = _mk_actuacion_con_geocode()
    ins_rows = Inspector.query.limit(2).all()
    if len(ins_rows) < 2:
        pytest.skip("Se requieren 2 inspectores")
    for ins_row in ins_rows:
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id,
                inspector_id=ins_row.id,
            )
        )
    db.session.commit()

    payload = {
        "tipo_actuacion": "INSPECCION",
        "rubro_nombre": rub.nombre,
        "contribuyente": {
            "doc_nro": contrib.documento,
            "apellido": contrib.apellido,
            "nombre": contrib.nombre,
        },
        "domicilio": {"calle": dom.calle, "numero": dom.numero},
        "acta_inspeccion_num": _ot_num(),
    }
    from app.domains.actuaciones.services.update_service import aplicar_payload_actuacion

    act_db = db.session.get(Actuaciones, act.id)
    aplicar_payload_actuacion(act_db, payload, ejecutar_resolver_previas=False)
    db.session.commit()

    count = db.session.scalar(
        select(func.count())
        .select_from(actuaciones_inspector)
        .where(
            actuaciones_inspector.c.actuaciones_id == act.id,
            actuaciones_inspector.c.deleted_at.is_(None),
        )
    )
    assert count == 2
