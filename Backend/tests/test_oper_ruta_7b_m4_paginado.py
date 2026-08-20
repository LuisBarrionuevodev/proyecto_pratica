"""OPER-RUTA.7B — Tests M4 paginado/filtrado server-side."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    get_iniciadores_pendientes_para_ruta,
)
from app.domains.rutas_trabajo.services.planificacion_service import (
    get_planificacion_pendientes_contexto,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import Domicilio, Inspector, IniciadorRuta, RutaItem, RutaTrabajo, User
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"op7b_{unique_ot_numero()}",
        email=f"op7b_{unique_ot_numero()}@t.local",
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
    distrito_id: int,
    prioridad: int = 1,
    tipo: str = "RELEVAMIENTO",
) -> IniciadorRuta:
    dom = Domicilio(
        calle=f"Op7b_{unique_ot_numero()}",
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


def test_m4_paginacion_real_distintas_paginas(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    distrito = 10
    for _ in range(3):
        _mk_iniciador(u, distrito_id=distrito, prioridad=2)
    db.session.commit()

    page1, total = get_planificacion_pendientes_contexto(
        int(ruta.id),
        distrito_id=distrito,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=2,
        orden="prioridad",
    )
    page2, _ = get_planificacion_pendientes_contexto(
        int(ruta.id),
        distrito_id=distrito,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=2,
        per_page=2,
        orden="prioridad",
    )
    assert total >= 3
    ids1 = {int(i.id) for i in page1}
    ids2 = {int(i.id) for i in page2}
    assert len(page1) == 2
    assert ids1.isdisjoint(ids2)


def test_m4_filtro_distrito(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini_d1 = _mk_iniciador(u, distrito_id=11)
    ini_d2 = _mk_iniciador(u, distrito_id=12)
    db.session.commit()

    items, total = get_planificacion_pendientes_contexto(
        int(ruta.id),
        distrito_id=11,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=50,
        orden="prioridad",
    )
    ids = {int(i.id) for i in items}
    assert int(ini_d1.id) in ids
    assert int(ini_d2.id) not in ids
    assert total >= 1


def test_m4_excluye_pool_en_pool(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u, distrito_id=13)
    ruta = _mk_ruta(u)
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=ruta.fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta.id),
    )

    items, _ = get_planificacion_pendientes_contexto(
        int(ruta.id),
        distrito_id=13,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=50,
        orden="prioridad",
    )
    assert int(ini.id) not in {int(i.id) for i in items}


def test_m4_excluye_pool_otra_ruta(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u, distrito_id=14)
    ruta_a = _mk_ruta(u, turno="MANIANA")
    ruta_b = _mk_ruta(u, turno="TARDE")
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=ruta_b.fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_b.id),
    )

    items, _ = get_planificacion_pendientes_contexto(
        int(ruta_a.id),
        distrito_id=14,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=50,
        orden="prioridad",
    )
    assert int(ini.id) not in {int(i.id) for i in items}


def test_m4_excluye_grupo_borrador(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u, distrito_id=15)
    ruta = _mk_ruta(u)
    ins1, ins2 = _dos_inspectores()
    db.session.commit()

    grupo = create_ruta_grupo(ruta_id=int(ruta.id), nombre="G7B", estado="ACTIVO")
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

    items, _ = get_planificacion_pendientes_contexto(
        int(ruta.id),
        distrito_id=15,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=50,
        orden="prioridad",
    )
    assert int(ini.id) not in {int(i.id) for i in items}


def test_m4_excluye_ruta_publicada_activa(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u, distrito_id=16)
    ruta_pub = _mk_ruta(u, turno="MANIANA")
    ruta_query = _mk_ruta(u, turno="TARDE")
    ins1, ins2 = _dos_inspectores()
    db.session.commit()

    grupo = create_ruta_grupo(ruta_id=int(ruta_pub.id), nombre="G7Bpub", estado="ACTIVO")
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
            RutaItem.deleted_at.is_(None),
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

    items, _ = get_planificacion_pendientes_contexto(
        int(ruta_query.id),
        distrito_id=16,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=50,
        orden="prioridad",
    )
    assert int(ini.id) not in {int(i.id) for i in items}


def test_m4_filtro_tipo(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini_rel = _mk_iniciador(u, distrito_id=17, tipo="RELEVAMIENTO")
    ini_den = _mk_iniciador(u, distrito_id=17, tipo="DENUNCIA")
    db.session.commit()

    items, _ = get_planificacion_pendientes_contexto(
        int(ruta.id),
        distrito_id=17,
        tipo="DENUNCIA",
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=50,
        orden="prioridad",
    )
    ids = {int(i.id) for i in items}
    assert int(ini_den.id) in ids
    assert int(ini_rel.id) not in ids


def test_m4_busqueda_q(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    suf = unique_ot_numero()
    ini = _mk_iniciador(u, distrito_id=18)
    dom = db.session.get(Domicilio, ini.domicilio_id)
    assert dom is not None
    dom.calle = f"BuscaQ_{suf}"
    db.session.commit()

    items, total = get_planificacion_pendientes_contexto(
        int(ruta.id),
        distrito_id=18,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=f"BuscaQ_{suf}",
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=50,
        orden="prioridad",
    )
    assert total >= 1
    assert int(ini.id) in {int(i.id) for i in items}


def test_m4_metadata_total_coherente(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    for _ in range(4):
        _mk_iniciador(u, distrito_id=19)
    db.session.commit()

    _, total = get_planificacion_pendientes_contexto(
        int(ruta.id),
        distrito_id=19,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=2,
        orden="prioridad",
    )
    assert total >= 4

    _, total2 = get_iniciadores_pendientes_para_ruta(
        ruta_id=int(ruta.id),
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        distrito=19,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=2,
        orden_planificacion=True,
        planificacion_orden="prioridad",
        solo_agregables_ruta=True,
    )
    assert total2 == total
