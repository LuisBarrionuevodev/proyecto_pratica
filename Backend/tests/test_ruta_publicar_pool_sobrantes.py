"""RUTA-PUBLISH-FIX.1 — Publicar descarta sobrantes EN_POOL y los devuelve a Pendientes."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.planificacion_service import (
    get_planificacion_pendientes_contexto,
)
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_pool_agregar_desde_pool_service import (
    agregar_desde_pool_a_ruta,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import RutaPublicarDebugError
from app.models import Actuaciones, Distrito, Domicilio, Inspector, IniciadorRuta, RutaItem, RutaPoolDia, RutaTrabajo, User
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"pubpool_{unique_ot_numero()}",
        email=f"pubpool_{unique_ot_numero()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _distrito_id() -> int:
    row = Distrito.query.first()
    if row is None:
        pytest.skip("Se requiere al menos un distrito en BD")
    return int(row.id)


def _mk_iniciador(user: User, *, distrito_id: int | None = None) -> IniciadorRuta:
    distrito = distrito_id if distrito_id is not None else _distrito_id()
    dom = Domicilio(
        calle=f"PubPool_{unique_ot_numero()}",
        numero="10",
        distrito_id=distrito,
    )
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


def _mk_ruta(user: User) -> RutaTrabajo:
    ruta = RutaTrabajo(
        fecha=fecha_ruta_aislada_mismo_anio(2026),
        turno="MANIANA",
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


def _agregar_al_pool(
    ruta: RutaTrabajo, user: User, iniciadores: list[IniciadorRuta]
) -> list[RutaPoolDia]:
    pools: list[RutaPoolDia] = []
    for ini in iniciadores:
        pool = create_ruta_pool_dia_entry(
            fecha=ruta.fecha,
            turno_id=None,
            usuario_id=user.id,
            iniciador_ruta_id=int(ini.id),
            ruta_trabajo_id=int(ruta.id),
        )
        pools.append(pool)
    return pools


def _asignar_desde_pool(
    ruta: RutaTrabajo,
    grupo_id: int,
    pools: list[RutaPoolDia],
) -> list[RutaItem]:
    agregar_desde_pool_a_ruta(
        ruta_id=int(ruta.id),
        grupo_id=grupo_id,
        pool_ids=[int(p.id) for p in pools],
    )
    items: list[RutaItem] = []
    for pool in pools:
        item = (
            RutaItem.query.filter(
                RutaItem.ruta_trabajo_id == ruta.id,
                RutaItem.iniciador_ruta_id == pool.iniciador_ruta_id,
                RutaItem.deleted_at.is_(None),
            )
            .first()
        )
        assert item is not None
        items.append(item)
    return items


def _pendientes_ids(ruta: RutaTrabajo, distrito_id: int) -> set[int]:
    items, _ = get_planificacion_pendientes_contexto(
        int(ruta.id),
        distrito_id=distrito_id,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=500,
        orden="prioridad",
    )
    return {int(i.id) for i in items}


def test_publicar_descarta_sobrantes_en_pool_y_publica_asignados(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ins1, ins2 = _dos_inspectores()
    grupo = create_ruta_grupo(ruta_id=int(ruta.id), nombre="G-PubPool", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        inspector_ids=[ins1.id, ins2.id],
    )

    distrito = _distrito_id()
    asignados = [_mk_iniciador(u, distrito_id=distrito) for _ in range(5)]
    sobrantes = [_mk_iniciador(u, distrito_id=distrito) for _ in range(5)]
    db.session.commit()

    pools_asignados = _agregar_al_pool(ruta, u, asignados)
    pools_sobrantes = _agregar_al_pool(ruta, u, sobrantes)
    items = _asignar_desde_pool(ruta, int(grupo.id), pools_asignados)
    for item in items:
        set_orden_trabajo_on_item(
            ruta_id=int(ruta.id),
            item_id=int(item.id),
            numero_orden_trabajo=unique_ot_numero(),
        )
    db.session.commit()

    actuaciones_antes = {a.id for a in Actuaciones.query.all()}
    sobrante_ids = {int(ini.id) for ini in sobrantes}
    asignado_ids = {int(ini.id) for ini in asignados}

    publicar_ruta_trabajo(ruta_id=int(ruta.id))
    db.session.expire_all()

    ruta_db = db.session.get(RutaTrabajo, ruta.id)
    assert ruta_db is not None
    assert ruta_db.estado_ruta == "PUBLICADA"

    for ini_id in asignado_ids:
        item = (
            RutaItem.query.filter(
                RutaItem.ruta_trabajo_id == ruta.id,
                RutaItem.iniciador_ruta_id == ini_id,
                RutaItem.deleted_at.is_(None),
            )
            .first()
        )
        assert item is not None
        assert item.estado_ruta_item == "EN_PROCESO"
        assert item.actuacion_id is not None
        ini_db = db.session.get(IniciadorRuta, ini_id)
        assert ini_db is not None
        assert ini_db.estado_iniciador == "EN_EJECUCION"

    for pool in pools_sobrantes:
        pool_db = db.session.get(RutaPoolDia, pool.id)
        assert pool_db is not None
        assert pool_db.estado == "DESCARTADO"
        assert pool_db.deleted_at is not None
        assert pool_db.ruta_item_id is None
        ini_db = db.session.get(IniciadorRuta, pool.iniciador_ruta_id)
        assert ini_db is not None
        assert ini_db.estado_iniciador == "PENDIENTE"
        assert (
            RutaItem.query.filter(
                RutaItem.ruta_trabajo_id == ruta.id,
                RutaItem.iniciador_ruta_id == pool.iniciador_ruta_id,
                RutaItem.deleted_at.is_(None),
            ).first()
            is None
        )

    for pool in pools_asignados:
        pool_db = db.session.get(RutaPoolDia, pool.id)
        assert pool_db is not None
        assert pool_db.estado == "ASIGNADO_A_RUTA"
        assert pool_db.deleted_at is None

    actuaciones_despues = {a.id for a in Actuaciones.query.all()}
    nuevas = actuaciones_despues - actuaciones_antes
    assert len(nuevas) == len(asignado_ids)

    ruta_consulta = _mk_ruta(u)
    db.session.commit()
    pendientes = _pendientes_ids(ruta_consulta, distrito)
    assert sobrante_ids.issubset(pendientes)
    assert asignado_ids.isdisjoint(pendientes)


def test_publicar_sin_sobrantes_no_descarta_pool_asignado(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ins1, ins2 = _dos_inspectores()
    grupo = create_ruta_grupo(ruta_id=int(ruta.id), nombre="G-SoloAsig", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        inspector_ids=[ins1.id, ins2.id],
    )

    distrito = _distrito_id()
    asignados = [_mk_iniciador(u, distrito_id=distrito) for _ in range(5)]
    db.session.commit()

    pools = _agregar_al_pool(ruta, u, asignados)
    items = _asignar_desde_pool(ruta, int(grupo.id), pools)
    for item in items:
        set_orden_trabajo_on_item(
            ruta_id=int(ruta.id),
            item_id=int(item.id),
            numero_orden_trabajo=unique_ot_numero(),
        )
    db.session.commit()

    publicar_ruta_trabajo(ruta_id=int(ruta.id))
    db.session.expire_all()

    for pool in pools:
        pool_db = db.session.get(RutaPoolDia, pool.id)
        assert pool_db is not None
        assert pool_db.estado == "ASIGNADO_A_RUTA"
        assert pool_db.deleted_at is None

    en_pool_activos = RutaPoolDia.query.filter(
        RutaPoolDia.ruta_trabajo_id == ruta.id,
        RutaPoolDia.deleted_at.is_(None),
        RutaPoolDia.estado == "EN_POOL",
    ).count()
    assert en_pool_activos == 0


def test_publicar_sin_items_no_descarta_pool(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    distrito = _distrito_id()
    solo_pool = [_mk_iniciador(u, distrito_id=distrito) for _ in range(3)]
    db.session.commit()
    pools = _agregar_al_pool(ruta, u, solo_pool)
    db.session.commit()

    with pytest.raises(RutaPublicarDebugError):
        publicar_ruta_trabajo(ruta_id=int(ruta.id))

    db.session.expire_all()
    for pool in pools:
        pool_db = db.session.get(RutaPoolDia, pool.id)
        assert pool_db is not None
        assert pool_db.estado == "EN_POOL"
        assert pool_db.deleted_at is None
