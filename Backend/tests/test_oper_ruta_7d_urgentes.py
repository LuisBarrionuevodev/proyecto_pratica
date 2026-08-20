"""OPER-RUTA.7D — Tests M3 urgentes optimizado server-side."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.planificacion_service import get_planificacion_urgentes
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.models import Domicilio, IniciadorRuta, Inspector, RutaItem, RutaTrabajo, User
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"op7d_{unique_ot_numero()}",
        email=f"op7d_{unique_ot_numero()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_iniciador(
    user: User,
    *,
    prioridad: int = 3,
    tipo: str = "DENUNCIA",
    distrito_id: int | None = None,
    calle: str | None = None,
) -> IniciadorRuta:
    dom = Domicilio(
        calle=calle or f"Op7d_{unique_ot_numero()}",
        numero="10",
        distrito_id=distrito_id,
    )
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador=tipo,
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 9, 1),
        anio=2026,
        mes=9,
        domicilio_id=dom.id,
        prioridad=prioridad,
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


def _dos_inspectores() -> tuple[Inspector, Inspector]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores")
    return rows[0], rows[1]


def test_urgente_libre_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op7dLibre_{unique_ot_numero()}"
    ini = _mk_iniciador(u, calle=calle)
    ruta = _mk_ruta(u)
    db.session.commit()

    items, total = get_planificacion_urgentes(int(ruta.id), page=1, per_page=50, q_domicilio=calle)
    assert total >= 1
    assert int(ini.id) in {int(i.id) for i in items}


def test_no_urgente_prioridad_baja_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op7dBaja_{unique_ot_numero()}"
    ini = _mk_iniciador(u, prioridad=2, calle=calle)
    ruta = _mk_ruta(u)
    db.session.commit()

    items, _ = get_planificacion_urgentes(int(ruta.id), page=1, per_page=50, q_domicilio=calle)
    assert int(ini.id) not in {int(i.id) for i in items}


def test_relevamiento_excluido_aun_con_prioridad_alta(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op7dRel_{unique_ot_numero()}"
    ini = _mk_iniciador(u, prioridad=5, tipo="RELEVAMIENTO", calle=calle)
    ruta = _mk_ruta(u)
    db.session.commit()

    items, _ = get_planificacion_urgentes(int(ruta.id), page=1, per_page=50, q_domicilio=calle)
    assert int(ini.id) not in {int(i.id) for i in items}


def test_urgente_en_pool_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op7dPool_{unique_ot_numero()}"
    ini = _mk_iniciador(u, calle=calle)
    ruta = _mk_ruta(u)
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=ruta.fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta.id),
    )

    items, _ = get_planificacion_urgentes(int(ruta.id), page=1, per_page=50, q_domicilio=calle)
    assert int(ini.id) not in {int(i.id) for i in items}


def test_urgente_en_grupo_borrador_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op7dGrupo_{unique_ot_numero()}"
    ini = _mk_iniciador(u, calle=calle)
    ruta = _mk_ruta(u)
    ins1, ins2 = _dos_inspectores()
    db.session.commit()

    grupo = create_ruta_grupo(ruta_id=int(ruta.id), nombre="G7D", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        inspector_ids=[ins1.id, ins2.id],
    )
    assign_iniciadores_to_grupo(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        iniciador_ids=[int(ini.id)],
    )

    items, _ = get_planificacion_urgentes(int(ruta.id), page=1, per_page=50, q_domicilio=calle)
    assert int(ini.id) not in {int(i.id) for i in items}


def test_urgente_en_ruta_publicada_no_aparece(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op7dPub_{unique_ot_numero()}"
    ini = _mk_iniciador(u, calle=calle)
    ruta_pub = _mk_ruta(u, turno="TARDE")
    ruta_query = _mk_ruta(u, turno="MANIANA")
    ins1, ins2 = _dos_inspectores()
    db.session.commit()

    grupo = create_ruta_grupo(ruta_id=int(ruta_pub.id), nombre="G7Dpub", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=int(ruta_pub.id),
        grupo_id=int(grupo.id),
        inspector_ids=[ins1.id, ins2.id],
    )
    assign_iniciadores_to_grupo(
        ruta_id=int(ruta_pub.id),
        grupo_id=int(grupo.id),
        iniciador_ids=[int(ini.id)],
    )
    item = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta_pub.id,
            RutaItem.iniciador_ruta_id == ini.id,
        )
        .first()
    )
    assert item is not None
    set_orden_trabajo_on_item(
        ruta_id=int(ruta_pub.id),
        item_id=int(item.id),
        numero_orden_trabajo=unique_ot_numero(),
    )
    publicar_ruta_trabajo(ruta_id=int(ruta_pub.id))

    items, _ = get_planificacion_urgentes(int(ruta_query.id), page=1, per_page=50, q_domicilio=calle)
    assert int(ini.id) not in {int(i.id) for i in items}


def test_reencolado_finalizado_aparece_si_urgente_libre(app_ctx) -> None:
    u = _mk_user()
    calle = f"Op7dReenc_{unique_ot_numero()}"
    ini = _mk_iniciador(u, calle=calle)
    ruta_hist = _mk_ruta(u, turno="TARDE")
    ruta_query = _mk_ruta(u, turno="MANIANA")
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

    items, _ = get_planificacion_urgentes(int(ruta_query.id), page=1, per_page=50, q_domicilio=calle)
    assert int(ini.id) in {int(i.id) for i in items}


def test_paginacion_real_distintas_paginas(app_ctx) -> None:
    u = _mk_user()
    pref = f"Op7dPag_{unique_ot_numero()}"
    ruta = _mk_ruta(u)
    for i in range(3):
        _mk_iniciador(u, prioridad=3 + i, calle=f"{pref}_{i}")
    db.session.commit()

    page1, total = get_planificacion_urgentes(
        int(ruta.id), page=1, per_page=2, q_domicilio=pref
    )
    page2, total2 = get_planificacion_urgentes(
        int(ruta.id), page=2, per_page=2, q_domicilio=pref
    )
    assert total >= 3
    assert total2 == total
    ids1 = {int(i.id) for i in page1}
    ids2 = {int(i.id) for i in page2}
    assert len(page1) == 2
    assert ids1.isdisjoint(ids2)


def test_filtro_distrito(app_ctx) -> None:
    from app.models import Distrito

    distritos = Distrito.query.order_by(Distrito.id.asc()).limit(2).all()
    if len(distritos) < 2:
        pytest.skip("Se requieren al menos 2 distritos")
    d1, d2 = int(distritos[0].id), int(distritos[1].id)

    u = _mk_user()
    ini_d1 = _mk_iniciador(u, distrito_id=d1, calle=f"Op7dD1_{unique_ot_numero()}")
    ini_d2 = _mk_iniciador(u, distrito_id=d2, calle=f"Op7dD2_{unique_ot_numero()}")
    ruta = _mk_ruta(u)
    db.session.commit()

    items, _ = get_planificacion_urgentes(
        int(ruta.id), page=1, per_page=50, distrito_id=d1
    )
    ids = {int(i.id) for i in items}
    assert int(ini_d1.id) in ids
    assert int(ini_d2.id) not in ids


def test_filtro_tipo_urgente_denuncia(app_ctx) -> None:
    u = _mk_user()
    pref = f"Op7dTipo_{unique_ot_numero()}"
    ini_den = _mk_iniciador(u, tipo="DENUNCIA", calle=f"{pref}_den")
    ini_notif = _mk_iniciador(u, tipo="REINSPECCION_NOTIFICACION", calle=f"{pref}_not")
    ruta = _mk_ruta(u)
    db.session.commit()

    items, _ = get_planificacion_urgentes(
        int(ruta.id),
        page=1,
        per_page=50,
        tipo_urgente="DENUNCIA",
        q_domicilio=pref,
    )
    ids = {int(i.id) for i in items}
    assert int(ini_den.id) in ids
    assert int(ini_notif.id) not in ids
