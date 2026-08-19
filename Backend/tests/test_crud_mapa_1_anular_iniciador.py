"""CRUD-MAPA.1 — Baja de Relevamiento/Denuncia limpia iniciador operativo."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.denuncias.services.denuncias_service import (
    crear_denuncia_con_iniciador,
    eliminar_denuncia_logicamente,
)
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.delete_service import eliminar_relevamiento
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    planificable_iniciadores_base_query,
)
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import (
    create_ruta_pool_dia_entry,
    list_ruta_pool_dia,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.domains.rutas_trabajo.services.anular_iniciador_por_origen_service import (
    IniciadorOrigenEnUsoError,
    _MSG_INICIADOR_EN_USO,
)
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaPoolDia,
    RutaTrabajo,
    User,
)
from tests.helpers.fixture_isolation import fecha_fixture_aislada, fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _ensure_user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u:
        return u
    u = User(
        username=f"crudmapa_{unique_ot_numero()}",
        email=f"crudmapa_{unique_ot_numero()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _inspector_y_rubro() -> tuple[Inspector, Rubro]:
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere inspector y rubro en BD de test")
    return ins, rub


def _crear_relevamiento(*, mock_user) -> tuple[object, IniciadorRuta]:
    ins, rub = _inspector_y_rubro()
    rel = crear_relevamiento_desde_payload(
        {
            "fecha": "2026-08-15",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": _uniq("RelCrudMapa"), "numero": "10"},
            "rubro_nombre": rub.nombre,
        }
    )
    ini = IniciadorRuta.query.filter(
        IniciadorRuta.relevamiento_id == rel.id,
        IniciadorRuta.deleted_at.is_(None),
    ).first()
    assert ini is not None
    return rel, ini


def _crear_denuncia(*, mock_user) -> tuple[object, IniciadorRuta]:
    den, ini = crear_denuncia_con_iniciador(
        fecha=date(2026, 8, 16),
        domicilio_id=None,
        calle=_uniq("DenCrudMapa"),
        numero="20",
        interseccion=None,
        motivo="Motivo CRUD-MAPA.1",
    )
    return den, ini


def _planificables_ids() -> set[int]:
    return {row.id for row in planificable_iniciadores_base_query().all()}


def _dos_inspectores() -> tuple[Inspector, Inspector]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores")
    return rows[0], rows[1]


def _setup_borrador(
    ini: IniciadorRuta,
    *,
    con_ot: bool = False,
    estado_ruta: str = "BORRADOR",
) -> tuple[RutaTrabajo, RutaItem]:
    u = _ensure_user()
    ins1, ins2 = _dos_inspectores()
    f = fecha_ruta_aislada_mismo_anio(2026)
    ruta = RutaTrabajo(
        fecha=f,
        turno="MANIANA",
        estado_ruta=estado_ruta,
        numero=uniq_ruta_numero(),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo CRUD-MAPA.1", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini.id],
    )
    item = items[0]
    if con_ot:
        set_orden_trabajo_on_item(
            ruta_id=ruta.id,
            item_id=item.id,
            numero_orden_trabajo=unique_ot_numero(),
        )
    db.session.commit()
    return ruta, item


@pytest.fixture
def mock_user(monkeypatch):
    u = _ensure_user()
    monkeypatch.setattr(
        "app.domains.denuncias.services.denuncias_service._get_current_user_id",
        lambda: int(u.id),
    )
    return u


def test_crud_mapa_1_borrar_relevamiento_pendiente_limpia_iniciador(app_ctx, mock_user) -> None:
    rel, ini = _crear_relevamiento(mock_user=mock_user)
    db.session.commit()
    assert ini.id in _planificables_ids()

    eliminar_relevamiento(int(rel.id))
    db.session.expire_all()

    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None
    assert ini_db.deleted_at is not None
    assert ini_db.estado_iniciador == "ANULADO"
    assert ini.id not in _planificables_ids()


def test_crud_mapa_1_borrar_denuncia_pendiente_limpia_iniciador(app_ctx, mock_user) -> None:
    den, ini = _crear_denuncia(mock_user=mock_user)
    db.session.commit()
    assert ini.id in _planificables_ids()

    eliminar_denuncia_logicamente(int(den.id))
    db.session.expire_all()

    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None
    assert ini_db.deleted_at is not None
    assert ini_db.estado_iniciador == "ANULADO"
    assert ini.id not in _planificables_ids()


def test_crud_mapa_1_borrar_relevamiento_en_pool_descarta_pool(app_ctx, mock_user) -> None:
    u = _ensure_user()
    rel, ini = _crear_relevamiento(mock_user=mock_user)
    db.session.commit()
    pool_fecha = fecha_fixture_aislada(anio=2097)

    pool = create_ruta_pool_dia_entry(
        fecha=pool_fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    db.session.commit()

    eliminar_relevamiento(int(rel.id))
    db.session.expire_all()

    pool_db = RutaPoolDia.query.get(pool.id)
    assert pool_db is not None
    assert pool_db.estado == "DESCARTADO"
    assert pool_db.deleted_at is not None
    assert ini.id not in _planificables_ids()

    items, total = list_ruta_pool_dia(fecha=pool_fecha, estado="EN_POOL")
    assert all(int(row.id) != int(pool.id) for row in items)
    assert int(pool.id) not in {int(row.id) for row in items}


def test_crud_mapa_1_borrar_denuncia_en_pool_descarta_pool(app_ctx, mock_user) -> None:
    u = _ensure_user()
    den, ini = _crear_denuncia(mock_user=mock_user)
    db.session.commit()
    pool_fecha = fecha_fixture_aislada(anio=2096)

    pool = create_ruta_pool_dia_entry(
        fecha=pool_fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    db.session.commit()

    eliminar_denuncia_logicamente(int(den.id))
    db.session.expire_all()

    pool_db = RutaPoolDia.query.get(pool.id)
    assert pool_db is not None
    assert pool_db.estado == "DESCARTADO"
    assert ini.id not in _planificables_ids()


def test_crud_mapa_1_borrar_relevamiento_borrador_sin_ot_limpia_item(app_ctx, mock_user) -> None:
    rel, ini = _crear_relevamiento(mock_user=mock_user)
    db.session.commit()
    ruta, item = _setup_borrador(ini, con_ot=False)
    db.session.expire(ini)
    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None
    assert ini_db.estado_iniciador == "PLANIFICADO"

    eliminar_relevamiento(int(rel.id))
    db.session.expire_all()

    item_db = RutaItem.query.get(item.id)
    ini_final = IniciadorRuta.query.get(ini.id)
    assert item_db is not None
    assert item_db.deleted_at is not None
    assert ini_final is not None
    assert ini_final.deleted_at is not None
    assert ini_final.estado_iniciador == "ANULADO"
    assert ini.id not in _planificables_ids()
    ruta_db = RutaTrabajo.query.get(ruta.id)
    assert ruta_db is not None
    assert ruta_db.estado_ruta == "BORRADOR"


def test_crud_mapa_1_borrar_denuncia_borrador_sin_ot_limpia_item(app_ctx, mock_user) -> None:
    den, ini = _crear_denuncia(mock_user=mock_user)
    db.session.commit()
    _ruta, item = _setup_borrador(ini, con_ot=False)

    eliminar_denuncia_logicamente(int(den.id))
    db.session.expire_all()

    item_db = RutaItem.query.get(item.id)
    ini_final = IniciadorRuta.query.get(ini.id)
    assert item_db is not None
    assert item_db.deleted_at is not None
    assert ini_final is not None
    assert ini_final.deleted_at is not None
    assert ini.id not in _planificables_ids()


def test_crud_mapa_1_borrar_relevamiento_ruta_publicada_bloquea(app_ctx, mock_user) -> None:
    rel, ini = _crear_relevamiento(mock_user=mock_user)
    db.session.commit()
    ruta, item = _setup_borrador(ini, con_ot=True)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    db.session.expire_all()

    with pytest.raises(IniciadorOrigenEnUsoError, match=_MSG_INICIADOR_EN_USO):
        eliminar_relevamiento(int(rel.id))

    db.session.expire_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    item_db = RutaItem.query.get(item.id)
    rel_db = db.session.get(type(rel), rel.id)
    assert ini_db is not None
    assert ini_db.deleted_at is None
    assert item_db is not None
    assert item_db.deleted_at is None
    assert rel_db is not None
    assert rel_db.deleted_at is None


def test_crud_mapa_1_borrar_denuncia_ruta_publicada_bloquea(app_ctx, mock_user) -> None:
    den, ini = _crear_denuncia(mock_user=mock_user)
    db.session.commit()
    ruta, item = _setup_borrador(ini, con_ot=True)
    publicar_ruta_trabajo(ruta_id=ruta.id)

    with pytest.raises(IniciadorOrigenEnUsoError, match=_MSG_INICIADOR_EN_USO):
        eliminar_denuncia_logicamente(int(den.id))

    db.session.expire_all()
    assert IniciadorRuta.query.get(ini.id).deleted_at is None
    assert RutaItem.query.get(item.id).deleted_at is None


def test_crud_mapa_1_borrar_relevamiento_con_actuacion_vinculada_bloquea(app_ctx, mock_user) -> None:
    rel, ini = _crear_relevamiento(mock_user=mock_user)
    db.session.commit()
    ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        tipo="RELEVAMIENTO",
        fecha=date(2026, 8, 15),
        mes=8,
        anio=2026,
        domicilio_id=ini.domicilio_id,
        orden_trabajo_id=ot.id,
    )
    db.session.add(act)
    db.session.flush()
    ini.actuacion_id = act.id
    db.session.commit()

    with pytest.raises(IniciadorOrigenEnUsoError, match=_MSG_INICIADOR_EN_USO):
        eliminar_relevamiento(int(rel.id))

    db.session.expire_all()
    assert IniciadorRuta.query.get(ini.id).deleted_at is None
