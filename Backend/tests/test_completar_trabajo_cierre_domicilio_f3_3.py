"""
F3.3 — Regresión: cambio de domicilio en Completar trabajo (ORM + geocode hook).

No ejecuta geocode real: se parchea ``on_domicilio_changed``.
"""

from __future__ import annotations

import random
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import joinedload

from app.database import db
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
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)


def _ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user(suf: str) -> User:
    u = User(
        username=f"u_f33_{suf}",
        email=f"f33_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_item_base(suf: str) -> tuple[RutaItem, Actuaciones, Domicilio, IniciadorRuta, User, Rubro]:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    u = _mk_user(suf)
    doc = str(random.randint(10_000_000, 40_000_000))
    c = Contribuyente(apellido="F33", nombre="Tit", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(calle=f"OldF33_{suf}", numero="1", rubro_id=rub.id, contribuyente_id=c.id)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=5)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 5, 10),
        mes=5,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=date(2026, 5, 10),
        anio=2026,
        mes=5,
        domicilio_id=dom.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=date(2026, 5, 10),
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
    db.session.flush()
    db.session.commit()
    return item, act, dom, ini, u, rub


def test_f33_visita_realizada_cambio_domicilio_orm_y_geo(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, dom_old, ini, u, rub = _mk_item_base(suf)
    new_calle = f"NewF33_{suf}"
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "calle": new_calle,
            "numero": "200",
            "numero_tipo": "NUMERO",
            "rubro_nombre": rub.nombre,
        }
    )
    with patch(
        "app.domains.actuaciones.services.completar_trabajo_cierre_service.on_domicilio_changed"
    ) as geo:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )
        geo.assert_called_once()
        new_dom_id = geo.call_args[0][0]

    assert new_dom_id == dom_old.id
    db.session.expunge_all()
    act_db = (
        Actuaciones.query.filter_by(id=act.id)
        .options(joinedload(Actuaciones.domicilio))
        .first()
    )
    ini_db = IniciadorRuta.query.filter_by(id=ini.id).first()
    assert act_db is not None and ini_db is not None
    assert act_db.domicilio_id == new_dom_id
    assert ini_db.domicilio_id == new_dom_id
    assert act_db.domicilio is not None
    assert act_db.domicilio.id == act_db.domicilio_id
    assert act_db.domicilio.calle == new_calle
    assert act_db.domicilio.numero == "200"


def test_f33_direccion_incorrecta_cambio_domicilio_y_geo(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, dom_old, ini, u, rub = _mk_item_base(suf)
    new_calle = f"CorrDirF33_{suf}"
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "contraproducencia": "DIRECCION INCORRECTA",
            "tipo_actuacion": "INSPECCION",
            "calle": new_calle,
            "numero": "300",
            "rubro_nombre": rub.nombre,
        }
    )
    with patch(
        "app.domains.actuaciones.services.completar_trabajo_cierre_service.on_domicilio_changed"
    ) as geo:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )
        geo.assert_called_once()
        new_dom_id = geo.call_args[0][0]

    assert new_dom_id == dom_old.id
    db.session.expunge_all()
    act_db = (
        Actuaciones.query.filter_by(id=act.id)
        .options(joinedload(Actuaciones.domicilio))
        .first()
    )
    ini_db = IniciadorRuta.query.filter_by(id=ini.id).first()
    item_db = RutaItem.query.filter_by(id=item.id).first()
    assert act_db.domicilio_id == new_dom_id
    assert ini_db.domicilio_id == new_dom_id
    assert act_db.domicilio is not None
    assert act_db.domicilio.id == act_db.domicilio_id
    assert ini_db.estado_iniciador == "PENDIENTE"
    assert item_db.estado_ruta_item == "NO_REALIZADO"


def test_f33_no_es_el_rubro_cambio_rubro_reingreso_y_domicilio_alineado(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, dom_old, ini, u, rub = _mk_item_base(suf)
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first()
    if rub2 is None:
        pytest.skip("Se requieren dos rubros en catálogo")
    new_calle = f"RubroF33_{suf}"
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "contraproducencia": "NO ES EL RUBRO",
            "tipo_actuacion": "INSPECCION",
            "calle": new_calle,
            "numero": "400",
            "rubro_nombre": rub2.nombre,
        }
    )
    with patch(
        "app.domains.actuaciones.services.completar_trabajo_cierre_service.on_domicilio_changed"
    ) as geo:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )
        geo.assert_called_once()
        new_dom_id = geo.call_args[0][0]

    assert new_dom_id == dom_old.id
    db.session.expunge_all()
    act_db = (
        Actuaciones.query.filter_by(id=act.id)
        .options(joinedload(Actuaciones.domicilio))
        .first()
    )
    ini_db = IniciadorRuta.query.filter_by(id=ini.id).first()
    item_db = RutaItem.query.filter_by(id=item.id).first()
    assert act_db.domicilio_id == new_dom_id
    assert ini_db.domicilio_id == new_dom_id
    assert act_db.domicilio is not None
    assert act_db.domicilio.id == act_db.domicilio_id
    assert act_db.domicilio.rubro_id == rub2.id
    assert ini_db.estado_iniciador == "PENDIENTE"
    assert item_db.estado_ruta_item == "NO_REALIZADO"
