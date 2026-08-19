"""OPER-RUTA.6G — Asignación exacta de ruta/turno al agregar desde pool."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_pool_agregar_desde_pool_service import (
    agregar_desde_pool_a_ruta,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.models import Domicilio, IniciadorRuta, RutaItem, RutaTrabajo, User
from tests.helpers.fixture_isolation import uniq_ruta_numero, unique_ot_numero


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    suf = unique_ot_numero()
    u = User(
        username=f"op6g_{suf}",
        email=f"op6g_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_iniciador(user: User) -> IniciadorRuta:
    dom = Domicilio(calle=f"Op6g_{unique_ot_numero()}", numero="1")
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="PENDIENTE",
        fecha_origen=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom.id,
        prioridad=3,
        created_by_user_id=user.id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def _mk_ruta_borrador(
    user: User,
    *,
    fecha: date,
    turno: str,
) -> RutaTrabajo:
    ruta = RutaTrabajo(
        fecha=fecha,
        turno=turno,
        estado_ruta="BORRADOR",
        numero=uniq_ruta_numero(),
        created_by_user_id=user.id,
    )
    db.session.add(ruta)
    db.session.flush()
    return ruta


def test_asignar_pool_a_ruta_tarde_crea_item_solo_en_tarde(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 3, 10)
    ruta_maniana = _mk_ruta_borrador(u, fecha=fecha, turno="MANIANA")
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    grupo_tarde = create_ruta_grupo(ruta_id=ruta_tarde.id, nombre="GT", estado="ACTIVO")
    db.session.commit()

    row = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    result = agregar_desde_pool_a_ruta(
        ruta_id=int(ruta_tarde.id),
        grupo_id=int(grupo_tarde.id),
        pool_ids=[int(row.id)],
    )
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert int(item.ruta_trabajo_id) == int(ruta_tarde.id)
    assert int(item.ruta_grupo_id) == int(grupo_tarde.id)

    db.session.refresh(row)
    assert row.estado == "ASIGNADO_A_RUTA"
    assert int(row.ruta_trabajo_id) == int(ruta_tarde.id)

    items_maniana = RutaItem.query.filter(
        RutaItem.ruta_trabajo_id == ruta_maniana.id,
        RutaItem.iniciador_ruta_id == ini.id,
        RutaItem.deleted_at.is_(None),
    ).all()
    assert items_maniana == []


def test_grupo_maniana_path_tarde_rechaza_409(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 3, 11)
    ruta_maniana = _mk_ruta_borrador(u, fecha=fecha, turno="MANIANA")
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    grupo_maniana = create_ruta_grupo(ruta_id=ruta_maniana.id, nombre="GM", estado="ACTIVO")
    db.session.commit()

    row = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    with pytest.raises(RuntimeError, match="otra ruta activa"):
        agregar_desde_pool_a_ruta(
            ruta_id=int(ruta_tarde.id),
            grupo_id=int(grupo_maniana.id),
            pool_ids=[int(row.id)],
        )


def test_pool_asociado_a_maniana_no_asigna_a_tarde(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 3, 12)
    ruta_maniana = _mk_ruta_borrador(u, fecha=fecha, turno="MANIANA")
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    grupo_tarde = create_ruta_grupo(ruta_id=ruta_tarde.id, nombre="GT2", estado="ACTIVO")
    db.session.commit()

    row = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_maniana.id),
    )
    with pytest.raises(RuntimeError, match="otra ruta activa"):
        agregar_desde_pool_a_ruta(
            ruta_id=int(ruta_tarde.id),
            grupo_id=int(grupo_tarde.id),
            pool_ids=[int(row.id)],
        )


def test_pool_sin_ruta_asigna_a_tarde_y_setea_ruta_trabajo_id(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 3, 13)
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    grupo_tarde = create_ruta_grupo(ruta_id=ruta_tarde.id, nombre="GT3", estado="ACTIVO")
    db.session.commit()

    row = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=None,
    )
    assert row.ruta_trabajo_id is None

    result = agregar_desde_pool_a_ruta(
        ruta_id=int(ruta_tarde.id),
        grupo_id=int(grupo_tarde.id),
        pool_ids=[int(row.id)],
    )
    assert len(result["items"]) == 1
    db.session.refresh(row)
    assert int(row.ruta_trabajo_id) == int(ruta_tarde.id)


def test_iniciador_en_item_maniana_no_asigna_a_tarde(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 3, 14)
    ruta_maniana = _mk_ruta_borrador(u, fecha=fecha, turno="MANIANA")
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    grupo_maniana = create_ruta_grupo(ruta_id=ruta_maniana.id, nombre="GM2", estado="ACTIVO")
    grupo_tarde = create_ruta_grupo(ruta_id=ruta_tarde.id, nombre="GT4", estado="ACTIVO")
    db.session.flush()

    item_maniana = RutaItem(
        ruta_trabajo_id=ruta_maniana.id,
        ruta_grupo_id=grupo_maniana.id,
        iniciador_ruta_id=ini.id,
        estado_ruta_item="ASIGNADO",
        created_by_user_id=u.id,
    )
    db.session.add(item_maniana)
    ini.estado_iniciador = "PLANIFICADO"
    db.session.flush()

    from app.models import RutaPoolDia

    row = RutaPoolDia(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        origen_tipo="INICIADOR",
        iniciador_ruta_id=int(ini.id),
        domicilio_id=ini.domicilio_id,
        estado="EN_POOL",
    )
    db.session.add(row)
    db.session.commit()

    with pytest.raises(RuntimeError, match="otra ruta activa"):
        agregar_desde_pool_a_ruta(
            ruta_id=int(ruta_tarde.id),
            grupo_id=int(grupo_tarde.id),
            pool_ids=[int(row.id)],
        )
