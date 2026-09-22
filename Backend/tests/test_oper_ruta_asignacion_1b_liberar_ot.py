"""OPER-RUTA.ASIGNACION-1B — OT-AUTO: endpoints manuales PATCH/DELETE orden-trabajo rechazados."""

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
from app.models import Domicilio, IniciadorRuta, Inspector, RutaItem, RutaTrabajo, User
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero
from tests.helpers.ruta_ot_test import asignar_ot_legacy_en_item

_OT_AUTO_MSG = "numeración automática al publicar"


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
    f = fecha_ruta_aislada_mismo_anio(2026)
    n = uniq_ruta_numero()
    while RutaTrabajo.query.filter_by(fecha=f, turno="MANIANA", numero=n).first():
        n = uniq_ruta_numero()
    ruta = RutaTrabajo(
        fecha=f,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=n,
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


def _setup_item_borrador(
    ruta: RutaTrabajo,
    ini: IniciadorRuta,
    *,
    legacy_ot: str | None = None,
) -> tuple[int, RutaItem]:
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
    item = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    assert item is not None
    if legacy_ot:
        asignar_ot_legacy_en_item(
            ruta_id=int(ruta.id),
            item_id=int(item.id),
            numero_orden_trabajo=legacy_ot,
        )
    db.session.commit()
    return int(grupo.id), item


def test_1b_patch_manual_rechazado_ot_auto(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item = _setup_item_borrador(ruta, ini)

    with pytest.raises(RuntimeError, match=_OT_AUTO_MSG):
        set_orden_trabajo_on_item(
            ruta_id=int(ruta.id),
            item_id=int(item.id),
            numero_orden_trabajo=unique_ot_numero(),
        )


def test_1b_liberar_manual_rechazado_ot_auto(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    ot_num = unique_ot_numero()
    _grupo_id, item = _setup_item_borrador(ruta, ini, legacy_ot=ot_num)

    with pytest.raises(RuntimeError, match=_OT_AUTO_MSG):
        liberar_orden_trabajo_on_item(ruta_id=int(ruta.id), item_id=int(item.id))


def test_1b_publicada_rechaza_liberacion_manual(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item = _setup_item_borrador(ruta, ini)
    publicar_ruta_trabajo(ruta_id=int(ruta.id))

    with pytest.raises(RuntimeError, match=_OT_AUTO_MSG):
        liberar_orden_trabajo_on_item(ruta_id=int(ruta.id), item_id=int(item.id))


def test_1b_item_de_otra_ruta_rechaza_liberacion(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta_a = _mk_ruta(u)
    ruta_b = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item = _setup_item_borrador(ruta_a, ini, legacy_ot=unique_ot_numero())

    with pytest.raises(RuntimeError, match=_OT_AUTO_MSG):
        liberar_orden_trabajo_on_item(ruta_id=int(ruta_b.id), item_id=int(item.id))


def test_1b_item_sin_ot_liberar_rechazado_ot_auto(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item = _setup_item_borrador(ruta, ini)
    assert item.orden_trabajo_id is None

    with pytest.raises(RuntimeError, match=_OT_AUTO_MSG):
        liberar_orden_trabajo_on_item(ruta_id=int(ruta.id), item_id=int(item.id))


def test_1b_quitar_item_con_ot_legacy_sigue_bloqueado(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item = _setup_item_borrador(ruta, ini, legacy_ot=unique_ot_numero())

    with pytest.raises(RuntimeError, match="Orden de Trabajo"):
        soft_delete_ruta_item(ruta_id=int(ruta.id), item_id=int(item.id))

    assert db.session.get(RutaItem, item.id).deleted_at is None


def test_1b_api_patch_rechazado_ot_auto(app_ctx, client, auth_headers) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    _grupo_id, item = _setup_item_borrador(ruta, ini)

    resp = client.patch(
        f"/rutas-trabajo/{ruta.id}/items/{item.id}/orden-trabajo",
        json={"numero_orden_trabajo": "123456"},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert _OT_AUTO_MSG in resp.get_json()["detail"]


def test_1b_api_delete_rechazado_ot_auto(app_ctx, client, auth_headers) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u)
    ruta = _mk_ruta(u)
    db.session.commit()
    ot_num = unique_ot_numero()
    _grupo_id, item = _setup_item_borrador(ruta, ini, legacy_ot=ot_num)

    resp = client.delete(
        f"/rutas-trabajo/{ruta.id}/items/{item.id}/orden-trabajo",
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert _OT_AUTO_MSG in resp.get_json()["detail"]
    item_db = db.session.get(RutaItem, item.id)
    assert item_db is not None
    assert item_db.orden_trabajo_id is not None
