"""OPER-RUTA.ASIGNACION-1B — Liberar OT en ítem de ruta BORRADOR."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    liberar_orden_trabajo_on_item,
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import (
    assign_iniciadores_to_grupo,
    soft_delete_ruta_item,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import Domicilio, IniciadorRuta, Inspector, OrdenTrabajo, RutaItem, RutaTrabajo, User
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"op1b_{unique_ot_numero()}",
        email=f"op1b_{unique_ot_numero()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_iniciador(user: User) -> IniciadorRuta:
    dom = Domicilio(calle=f"Op1b_{unique_ot_numero()}", numero="10")
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


def _setup_item_con_ot(
    ruta: RutaTrabajo,
    ini: IniciadorRuta,
    *,
    ot_num: str | None = None,
) -> tuple[int, RutaItem, str, int]:
    ins1, ins2 = _dos_inspectores()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G1B", estado="ACTIVO")
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
    numero = ot_num or unique_ot_numero()
    item = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    assert item is not None
    updated = set_orden_trabajo_on_item(
        ruta_id=int(ruta.id),
        item_id=int(item.id),
        numero_orden_trabajo=numero,
    )
    assert updated.orden_trabajo_id is not None
    ot_id = int(updated.orden_trabajo_id)
    db.session.commit()
    return int(grupo.id), item, numero, ot_id


def test_1b_borrador_item_con_ot_libera_correctamente(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    grupo_id, item, _ot_num, ot_id = _setup_item_con_ot(ruta, ini)

    liberado = liberar_orden_trabajo_on_item(ruta_id=int(ruta.id), item_id=int(item.id))

    assert liberado.orden_trabajo_id is None
    assert liberado.orden_trabajo is None
    assert liberado.ruta_grupo_id == grupo_id
    assert liberado.deleted_at is None
    assert db.session.get(OrdenTrabajo, ot_id) is not None


def test_1b_ot_liberada_puede_asignarse_a_otro_item(app_ctx) -> None:
    u = _mk_user()
    ini_a = _mk_iniciador(u)
    ini_b = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    grupo_id, item_a, ot_num, ot_id = _setup_item_con_ot(ruta, ini_a)

    liberar_orden_trabajo_on_item(ruta_id=int(ruta.id), item_id=int(item_a.id))

    assign_iniciadores_to_grupo(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo_id),
        iniciador_ids=[int(ini_b.id)],
    )
    item_b = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.iniciador_ruta_id == ini_b.id,
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    assert item_b is not None
    updated_b = set_orden_trabajo_on_item(
        ruta_id=int(ruta.id),
        item_id=int(item_b.id),
        numero_orden_trabajo=ot_num,
    )
    assert int(updated_b.orden_trabajo_id) == ot_id


def test_1b_publicada_rechaza_liberacion(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item, _ot_num, _ot_id = _setup_item_con_ot(ruta, ini)
    publicar_ruta_trabajo(ruta_id=int(ruta.id))

    with pytest.raises(RuntimeError, match="BORRADOR"):
        liberar_orden_trabajo_on_item(ruta_id=int(ruta.id), item_id=int(item.id))


def test_1b_item_de_otra_ruta_rechaza(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta_a = _mk_ruta(u)
    ruta_b = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item, _ot_num, _ot_id = _setup_item_con_ot(ruta_a, ini)

    with pytest.raises(LookupError, match="Item no encontrado"):
        liberar_orden_trabajo_on_item(ruta_id=int(ruta_b.id), item_id=int(item.id))


def test_1b_item_sin_ot_respuesta_controlada(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    ins1, ins2 = _dos_inspectores()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G1B-sin", estado="ACTIVO")
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
    item = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.iniciador_ruta_id == ini.id,
        )
        .first()
    )
    assert item is not None
    assert item.orden_trabajo_id is None

    with pytest.raises(RuntimeError, match="no tiene una orden de trabajo asignada"):
        liberar_orden_trabajo_on_item(ruta_id=int(ruta.id), item_id=int(item.id))


def test_1b_item_ejecutado_no_permite_liberacion(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item, _ot_num, _ot_id = _setup_item_con_ot(ruta, ini)
    item_db = db.session.get(RutaItem, item.id)
    assert item_db is not None
    item_db.estado_ejecucion = "REALIZADO"
    db.session.commit()

    with pytest.raises(RuntimeError, match="Orden de Trabajo"):
        liberar_orden_trabajo_on_item(ruta_id=int(ruta.id), item_id=int(item.id))


def test_1b_quitar_item_con_ot_sigue_bloqueado(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item, _ot_num, _ot_id = _setup_item_con_ot(ruta, ini)

    with pytest.raises(RuntimeError, match="Orden de Trabajo"):
        soft_delete_ruta_item(ruta_id=int(ruta.id), item_id=int(item.id))

    assert db.session.get(RutaItem, item.id).deleted_at is None


def test_1b_liberar_ot_y_quitar_item_funciona(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item, _ot_num, _ot_id = _setup_item_con_ot(ruta, ini)

    liberar_orden_trabajo_on_item(ruta_id=int(ruta.id), item_id=int(item.id))
    soft_delete_ruta_item(ruta_id=int(ruta.id), item_id=int(item.id))

    item_db = db.session.get(RutaItem, item.id)
    assert item_db is not None
    assert item_db.deleted_at is not None
    assert item_db.orden_trabajo_id is None


def test_1b_api_delete_liberar_ot(app_ctx, client, auth_headers) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item, ot_num, _ot_id = _setup_item_con_ot(ruta, ini)

    resp = client.delete(
        f"/rutas-trabajo/{ruta.id}/items/{item.id}/orden-trabajo",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["item"]["orden_trabajo_id"] is None
    assert body["item"].get("orden_trabajo") is None

    item_db = db.session.get(RutaItem, item.id)
    assert item_db is not None
    assert item_db.orden_trabajo_id is None


def test_1b_api_delete_sin_ot_409(app_ctx, client, auth_headers) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    ins1, ins2 = _dos_inspectores()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G1B-api", estado="ACTIVO")
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
    item = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.iniciador_ruta_id == ini.id,
        )
        .first()
    )
    assert item is not None
    db.session.commit()

    resp = client.delete(
        f"/rutas-trabajo/{ruta.id}/items/{item.id}/orden-trabajo",
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "no tiene una orden de trabajo asignada" in resp.get_json()["detail"]
