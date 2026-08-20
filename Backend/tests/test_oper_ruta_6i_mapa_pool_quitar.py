"""OPER-RUTA.6I — Candidatos mapa agregables + quitar/eliminar grupo + pool idempotente."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    get_iniciadores_pendientes_para_ruta,
)
from app.domains.rutas_trabajo.services.ruta_items_service import (
    assign_iniciadores_to_grupo,
    soft_delete_grupo,
    soft_delete_ruta_item,
)
from app.domains.rutas_trabajo.services.ruta_pool_agregar_desde_pool_service import (
    agregar_desde_pool_a_ruta,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_eligibility_service import (
    es_iniciador_agregable_a_ruta,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import (
    create_ruta_pool_dia_entry,
    ensure_pool_en_pool_para_ruta,
    list_ruta_pool_dia,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.models import Domicilio, IniciadorRuta, Inspector, RutaItem, RutaPoolDia, RutaTrabajo, User
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero

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
    u = User(
        username=f"op6i_{unique_ot_numero()}",
        email=f"op6i_{unique_ot_numero()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_iniciador(user: User, *, distrito_id: int | None = None) -> IniciadorRuta:
    dom = Domicilio(calle=f"Op6i_{unique_ot_numero()}", numero="10", distrito_id=distrito_id)
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 9, 1),
        anio=2026,
        mes=9,
        domicilio_id=dom.id,
        prioridad=1,
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


def _setup_grupo_con_iniciador(
    ruta: RutaTrabajo,
    ini: IniciadorRuta,
    *,
    via_pool: bool,
) -> tuple[int, RutaItem]:
    ins1, ins2 = _dos_inspectores()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G6I", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    u = User.query.get(ruta.created_by_user_id)
    assert u is not None
    if via_pool:
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
    else:
        assign_iniciadores_to_grupo(
            ruta_id=int(ruta.id),
            grupo_id=int(grupo.id),
            iniciador_ids=[int(ini.id)],
        )
    db.session.commit()
    item = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    assert item is not None
    return int(grupo.id), item


def test_candidatos_excluyen_iniciador_en_pool_otra_ruta(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u, distrito_id=1)
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

    assert es_iniciador_agregable_a_ruta(int(ini.id), int(ruta_maniana.id)) is False
    dom = db.session.get(Domicilio, ini.domicilio_id)
    assert dom is not None
    items, _total = get_iniciadores_pendientes_para_ruta(
        ruta_id=int(ruta_maniana.id),
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        distrito=int(dom.distrito_id) if dom.distrito_id else 1,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=500,
        solo_agregables_ruta=True,
    )
    assert int(ini.id) not in {int(row.id) for row in items}


def test_candidatos_excluyen_iniciador_en_pool_misma_ruta(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u, distrito_id=2)
    ruta = _mk_ruta(u)
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=ruta.fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta.id),
    )

    assert es_iniciador_agregable_a_ruta(int(ini.id), int(ruta.id)) is False


def test_candidatos_incluyen_iniciador_libre(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u, distrito_id=3)
    ruta = _mk_ruta(u)
    db.session.commit()

    assert es_iniciador_agregable_a_ruta(int(ini.id), int(ruta.id)) is True
    items, total = get_iniciadores_pendientes_para_ruta(
        ruta_id=int(ruta.id),
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        distrito=3,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=50,
        solo_agregables_ruta=True,
    )
    assert total >= 1
    assert int(ini.id) in {int(row.id) for row in items}


def test_quitar_item_devuelve_pool_con_ruta_trabajo_id(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item = _setup_grupo_con_iniciador(ruta, ini, via_pool=True)

    soft_delete_ruta_item(ruta_id=int(ruta.id), item_id=int(item.id))
    db.session.expire_all()

    pools, total = list_ruta_pool_dia(
        fecha=ruta.fecha,
        estado="EN_POOL",
        ruta_trabajo_id=int(ruta.id),
    )
    assert total == 1
    assert len(pools) == 1
    assert int(pools[0].iniciador_ruta_id) == int(ini.id)
    assert int(pools[0].ruta_trabajo_id) == int(ruta.id)


def test_quitar_item_dos_veces_idempotente_en_pool(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item = _setup_grupo_con_iniciador(ruta, ini, via_pool=True)

    soft_delete_ruta_item(ruta_id=int(ruta.id), item_id=int(item.id))
    with pytest.raises(LookupError):
        soft_delete_ruta_item(ruta_id=int(ruta.id), item_id=int(item.id))

    pools, total = list_ruta_pool_dia(
        fecha=ruta.fecha,
        estado="EN_POOL",
        ruta_trabajo_id=int(ruta.id),
    )
    assert total == 1


def test_eliminar_grupo_devuelve_items_al_pool(app_ctx) -> None:
    u = _mk_user()
    ini_a = _mk_iniciador(u)
    ini_b = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    grupo_id, _item_a = _setup_grupo_con_iniciador(ruta, ini_a, via_pool=True)
    assign_iniciadores_to_grupo(
        ruta_id=int(ruta.id),
        grupo_id=grupo_id,
        iniciador_ids=[int(ini_b.id)],
    )
    db.session.commit()

    soft_delete_grupo(ruta_id=int(ruta.id), grupo_id=grupo_id)
    db.session.expire_all()

    pools, total = list_ruta_pool_dia(
        fecha=ruta.fecha,
        estado="EN_POOL",
        ruta_trabajo_id=int(ruta.id),
    )
    assert total == 2
    ids = {int(p.iniciador_ruta_id) for p in pools}
    assert ids == {int(ini_a.id), int(ini_b.id)}


def test_eliminar_grupo_con_item_ot_bloquea(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    grupo_id, item = _setup_grupo_con_iniciador(ruta, ini, via_pool=False)
    set_orden_trabajo_on_item(
        ruta_id=int(ruta.id),
        item_id=int(item.id),
        numero_orden_trabajo=unique_ot_numero(),
    )

    with pytest.raises(RuntimeError, match="Orden de Trabajo"):
        soft_delete_grupo(ruta_id=int(ruta.id), grupo_id=grupo_id)

    assert RutaItem.query.get(item.id).deleted_at is None


def test_ensure_pool_no_duplica_misma_ruta(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()

    p1 = ensure_pool_en_pool_para_ruta(
        iniciador_ruta_id=int(ini.id),
        fecha=ruta.fecha,
        ruta_trabajo_id=int(ruta.id),
        usuario_id=u.id,
    )
    p2 = ensure_pool_en_pool_para_ruta(
        iniciador_ruta_id=int(ini.id),
        fecha=ruta.fecha,
        ruta_trabajo_id=int(ruta.id),
        usuario_id=u.id,
    )
    assert int(p1.id) == int(p2.id)
    count = RutaPoolDia.query.filter(
        RutaPoolDia.iniciador_ruta_id == ini.id,
        RutaPoolDia.ruta_trabajo_id == ruta.id,
        RutaPoolDia.deleted_at.is_(None),
        RutaPoolDia.estado == "EN_POOL",
    ).count()
    assert count == 1


def test_ensure_pool_otra_ruta_activa_bloquea(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta_a = _mk_ruta(u, turno="MANIANA")
    ruta_b = _mk_ruta(u, turno="TARDE")
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=ruta_a.fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta_a.id),
    )

    with pytest.raises(RuntimeError, match=_MSG_OTRA_RUTA):
        ensure_pool_en_pool_para_ruta(
            iniciador_ruta_id=int(ini.id),
            fecha=ruta_b.fecha,
            ruta_trabajo_id=int(ruta_b.id),
            usuario_id=u.id,
        )


def test_candidatos_excluyen_iniciador_en_ruta_publicada(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u, distrito_id=4)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item = _setup_grupo_con_iniciador(ruta, ini, via_pool=False)
    set_orden_trabajo_on_item(
        ruta_id=int(ruta.id),
        item_id=int(item.id),
        numero_orden_trabajo=unique_ot_numero(),
    )
    publicar_ruta_trabajo(ruta_id=int(ruta.id))

    assert es_iniciador_agregable_a_ruta(int(ini.id), int(ruta.id)) is False
