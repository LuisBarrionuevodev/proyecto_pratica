"""OPER-RUTA.6H — Pool del día acotado por ruta_trabajo_id."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.ruta_pool_agregar_desde_pool_service import (
    agregar_desde_pool_a_ruta,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import (
    create_ruta_pool_dia_entry,
    descartar_ruta_pool_dia_entry,
    liberar_ruta_pool_dia_entry,
    list_ruta_pool_dia,
)
from app.models import Domicilio, IniciadorRuta, RutaPoolDia, RutaTrabajo, User
from tests.helpers.fixture_isolation import uniq_ruta_numero, unique_ot_numero

_MSG_OTRA_RUTA = (
    "El pendiente ya está asociado a otra ruta activa. "
    "Sacalo de esa ruta antes de asignarlo a una nueva."
)


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    suf = unique_ot_numero()
    u = User(
        username=f"op6h_{suf}",
        email=f"op6h_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_iniciador(user: User) -> IniciadorRuta:
    dom = Domicilio(calle=f"Op6h_{unique_ot_numero()}", numero="1")
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


def test_list_pool_filtra_por_ruta_trabajo_id(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 4, 1)
    ruta_maniana = _mk_ruta_borrador(u, fecha=fecha, turno="MANIANA")
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    db.session.commit()

    pool_tarde = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_tarde.id),
    )

    items_tarde, total_tarde = list_ruta_pool_dia(
        fecha=fecha,
        estado="EN_POOL",
        ruta_trabajo_id=int(ruta_tarde.id),
    )
    assert total_tarde == 1
    assert len(items_tarde) == 1
    assert int(items_tarde[0].id) == int(pool_tarde.id)

    items_maniana, total_maniana = list_ruta_pool_dia(
        fecha=fecha,
        estado="EN_POOL",
        ruta_trabajo_id=int(ruta_maniana.id),
    )
    assert total_maniana == 0
    assert items_maniana == []


def test_pool_sin_ruta_trabajo_id_no_aparece_en_listado_por_ruta(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 4, 2)
    ruta_maniana = _mk_ruta_borrador(u, fecha=fecha, turno="MANIANA")
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )

    items_maniana, total_maniana = list_ruta_pool_dia(
        fecha=fecha,
        estado="EN_POOL",
        ruta_trabajo_id=int(ruta_maniana.id),
    )
    assert total_maniana == 0
    assert items_maniana == []


def test_delete_pool_por_id_no_afecta_historico_mismo_iniciador(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 4, 3)
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    db.session.commit()

    historico = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_tarde.id),
    )
    descartar_ruta_pool_dia_entry(pool_id=int(historico.id))

    activo = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_tarde.id),
    )

    descartar_ruta_pool_dia_entry(pool_id=int(activo.id))

    db.session.refresh(historico)
    assert historico.estado == "DESCARTADO"
    assert historico.deleted_at is not None

    rows = RutaPoolDia.query.filter(RutaPoolDia.iniciador_ruta_id == ini.id).all()
    assert len(rows) == 2
    assert all(row.estado == "DESCARTADO" for row in rows)


def test_liberar_por_pool_id_solo_afecta_ese_pool(app_ctx) -> None:
    u = _mk_user()
    ini_a = _mk_iniciador(u)
    ini_b = _mk_iniciador(u)
    fecha = date(2098, 4, 4)
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    db.session.commit()

    pool_a = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini_a.id),
        ruta_trabajo_id=int(ruta_tarde.id),
    )
    pool_b = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini_b.id),
        ruta_trabajo_id=int(ruta_tarde.id),
    )

    liberar_ruta_pool_dia_entry(pool_id=int(pool_a.id))

    db.session.refresh(pool_a)
    db.session.refresh(pool_b)
    assert pool_a.estado == "DESCARTADO"
    assert pool_b.estado == "EN_POOL"


def test_crear_pool_misma_ruta_duplicado_rechaza(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 4, 5)
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_tarde.id),
    )

    with pytest.raises(RuntimeError, match="El iniciador ya está en el pool del día"):
        create_ruta_pool_dia_entry(
            fecha=fecha,
            turno_id=None,
            usuario_id=u.id,
            iniciador_ruta_id=int(ini.id),
            ruta_trabajo_id=int(ruta_tarde.id),
        )


def test_crear_pool_otra_ruta_activa_rechaza_409(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 4, 6)
    ruta_maniana = _mk_ruta_borrador(u, fecha=fecha, turno="MANIANA")
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_tarde.id),
    )

    with pytest.raises(RuntimeError, match=_MSG_OTRA_RUTA):
        create_ruta_pool_dia_entry(
            fecha=fecha,
            turno_id=None,
            usuario_id=u.id,
            iniciador_ruta_id=int(ini.id),
            ruta_trabajo_id=int(ruta_maniana.id),
        )


def test_asignar_pool_tarde_a_ruta_maniana_rechaza_409(app_ctx) -> None:
    from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo

    u = _mk_user()
    ini = _mk_iniciador(u)
    fecha = date(2098, 4, 7)
    ruta_maniana = _mk_ruta_borrador(u, fecha=fecha, turno="MANIANA")
    ruta_tarde = _mk_ruta_borrador(u, fecha=fecha, turno="TARDE")
    grupo_maniana = create_ruta_grupo(ruta_id=ruta_maniana.id, nombre="GM", estado="ACTIVO")
    db.session.commit()

    pool_tarde = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_tarde.id),
    )

    with pytest.raises(RuntimeError, match=_MSG_OTRA_RUTA):
        agregar_desde_pool_a_ruta(
            ruta_id=int(ruta_maniana.id),
            grupo_id=int(grupo_maniana.id),
            pool_ids=[int(pool_tarde.id)],
        )
