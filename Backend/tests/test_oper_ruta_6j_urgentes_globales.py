"""OPER-RUTA.6J — Urgentes globales excluyen iniciadores no agregables (pool/ruta activa)."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.planificacion_service import get_planificacion_urgentes
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_pool_agregar_desde_pool_service import (
    agregar_desde_pool_a_ruta,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.models import Domicilio, IniciadorRuta, Inspector, RutaItem, RutaTrabajo, User
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"op6j_{unique_ot_numero()}",
        email=f"op6j_{unique_ot_numero()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_urgente(user: User, *, calle: str | None = None) -> IniciadorRuta:
    dom = Domicilio(calle=calle or f"Op6j_{unique_ot_numero()}", numero="10")
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="DENUNCIA",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 9, 1),
        anio=2026,
        mes=9,
        domicilio_id=dom.id,
        prioridad=3,
        created_by_user_id=user.id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def _mk_ruta(user: User, *, turno: str = "MANIANA") -> RutaTrabajo:
    ruta = RutaTrabajo(
        fecha=fecha_ruta_aislada_mismo_anio(2026),
        turno=turno,
        estado_ruta="BORRADOR",
        numero=uniq_ruta_numero(),
        created_by_user_id=user.id,
    )
    db.session.add(ruta)
    db.session.flush()
    return ruta


def _urgentes_ids(ruta_id: int, *, calle: str) -> set[int]:
    items, _total = get_planificacion_urgentes(
        int(ruta_id),
        page=1,
        per_page=500,
        q_domicilio=calle,
    )
    return {int(row.id) for row in items}


def _dos_inspectores() -> tuple[Inspector, Inspector]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores")
    return rows[0], rows[1]


def test_urgente_libre_aparece_en_urgentes_globales(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op6jLibre_{unique_ot_numero()}"
    ini = _mk_urgente(u, calle=calle)
    ruta = _mk_ruta(u)
    db.session.commit()

    assert int(ini.id) in _urgentes_ids(int(ruta.id), calle=calle)


def test_urgente_en_pool_en_pool_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op6jPool_{unique_ot_numero()}"
    ini = _mk_urgente(u, calle=calle)
    ruta = _mk_ruta(u)
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=ruta.fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta.id),
    )
    db.session.commit()

    assert int(ini.id) not in _urgentes_ids(int(ruta.id), calle=calle)


def test_urgente_en_pool_otra_ruta_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op6jOtraRuta_{unique_ot_numero()}"
    ini = _mk_urgente(u, calle=calle)
    ruta_maniana = _mk_ruta(u, turno="MANIANA")
    ruta_tarde = _mk_ruta(u, turno="TARDE")
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=ruta_tarde.fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_tarde.id),
    )
    db.session.commit()

    assert int(ini.id) not in _urgentes_ids(int(ruta_maniana.id), calle=calle)


def test_urgente_asignado_a_ruta_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op6jAsignado_{unique_ot_numero()}"
    ini = _mk_urgente(u, calle=calle)
    ruta = _mk_ruta(u)
    ins1, ins2 = _dos_inspectores()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G6J", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    pool = create_ruta_pool_dia_entry(
        fecha=ruta.fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta.id),
    )
    agregar_desde_pool_a_ruta(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        pool_ids=[int(pool.id)],
    )
    db.session.commit()

    assert int(ini.id) not in _urgentes_ids(int(ruta.id), calle=calle)


def test_urgente_en_grupo_borrador_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op6jGrupo_{unique_ot_numero()}"
    ini = _mk_urgente(u, calle=calle)
    ruta = _mk_ruta(u)
    ins1, ins2 = _dos_inspectores()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G6J2", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    assign_iniciadores_to_grupo(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        iniciador_ids=[int(ini.id)],
    )
    db.session.commit()

    assert int(ini.id) not in _urgentes_ids(int(ruta.id), calle=calle)


def test_urgente_en_ruta_publicada_activa_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op6jPub_{unique_ot_numero()}"
    ini = _mk_urgente(u, calle=calle)
    ruta_pub = _mk_ruta(u, turno="TARDE")
    ruta_borrador = _mk_ruta(u, turno="MANIANA")
    item = RutaItem(
        ruta_trabajo_id=ruta_pub.id,
        iniciador_ruta_id=ini.id,
        estado_ruta_item="ASIGNADO",
        created_by_user_id=u.id,
    )
    db.session.add(item)
    ruta_pub.estado_ruta = "PUBLICADA"
    db.session.commit()

    assert int(ini.id) not in _urgentes_ids(int(ruta_borrador.id), calle=calle)


def test_urgente_reencolado_finalizado_aparece_sin_pool_activo(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op6jReenc_{unique_ot_numero()}"
    ini = _mk_urgente(u, calle=calle)
    ruta_hist = _mk_ruta(u, turno="TARDE")
    ruta_borrador = _mk_ruta(u, turno="MANIANA")
    item = RutaItem(
        ruta_trabajo_id=ruta_hist.id,
        iniciador_ruta_id=ini.id,
        estado_ruta_item="FINALIZADO",
        estado_ejecucion="NO_REALIZADO",
        motivo_no_realizado="LOCAL_CERRADO",
        created_by_user_id=u.id,
    )
    db.session.add(item)
    ruta_hist.estado_ruta = "PUBLICADA"
    db.session.commit()

    assert int(ini.id) in _urgentes_ids(int(ruta_borrador.id), calle=calle)


def test_urgente_anulado_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op6jAnul_{unique_ot_numero()}"
    ini = _mk_urgente(u, calle=calle)
    ini.estado_iniciador = "ANULADO"
    ruta = _mk_ruta(u)
    db.session.commit()

    assert int(ini.id) not in _urgentes_ids(int(ruta.id), calle=calle)


def test_urgente_cumplido_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op6jCumpl_{unique_ot_numero()}"
    ini = _mk_urgente(u, calle=calle)
    ini.estado_iniciador = "CUMPLIDO"
    ruta = _mk_ruta(u)
    db.session.commit()

    assert int(ini.id) not in _urgentes_ids(int(ruta.id), calle=calle)
