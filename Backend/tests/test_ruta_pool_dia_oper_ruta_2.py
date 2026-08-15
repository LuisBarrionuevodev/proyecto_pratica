"""OPER-RUTA.2 — Pool del día persistente."""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_pool_agregar_desde_pool_service import (
    agregar_desde_pool_a_ruta,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import (
    create_ruta_pool_dia_entry,
    descartar_ruta_pool_dia_entry,
    liberar_ruta_pool_dia_entry,
    list_ruta_pool_dia,
)
from app.models import Domicilio, IniciadorRuta, RutaItem, RutaPoolDia, RutaTrabajo, User


def _unique() -> str:
    return f"{random.randint(0, 999999):06d}"


def _fecha_aislada() -> date:
    """Día único para evitar colisión con datos persistentes de otros tests."""
    return date(2099, 1, 1) + timedelta(days=random.randint(0, 300))


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"pool_{_unique()}",
        email=f"pool_{_unique()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_iniciador(*, estado: str = "PENDIENTE", calle: str | None = None) -> IniciadorRuta:
    u = _mk_user()
    dom = Domicilio(calle=calle or f"PoolCalle{_unique()}", numero="100")
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador=estado,
        fecha_origen=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom.id,
        prioridad=3,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def _mk_ruta(*, user: User, estado: str = "BORRADOR") -> RutaTrabajo:
    ruta = RutaTrabajo(
        fecha=date.today() + timedelta(days=random.randint(1, 300)),
        turno="MANIANA",
        estado_ruta=estado,
        numero=random.randint(100, 32000),
        created_by_user_id=user.id,
    )
    db.session.add(ruta)
    db.session.flush()
    return ruta


def test_crear_pool_con_iniciador_pendiente(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    db.session.commit()

    row = create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    assert row.estado == "EN_POOL"
    assert row.iniciador_ruta_id == ini.id
    assert row.domicilio_id == ini.domicilio_id


def test_rechazar_iniciador_cumplido(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador(estado="CUMPLIDO")
    db.session.commit()

    with pytest.raises(RuntimeError, match="PENDIENTE"):
        create_ruta_pool_dia_entry(
            fecha=date.today(),
            turno_id=None,
            usuario_id=u.id,
            iniciador_ruta_id=int(ini.id),
        )


def test_rechazar_iniciador_en_ruta_publicada(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    ruta = _mk_ruta(user=u, estado="PUBLICADA")
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        ruta_grupo_id=None,
        iniciador_ruta_id=ini.id,
        estado_ruta_item="ASIGNADO",
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.commit()

    with pytest.raises(RuntimeError, match="publicada"):
        create_ruta_pool_dia_entry(
            fecha=date.today(),
            turno_id=None,
            usuario_id=u.id,
            iniciador_ruta_id=int(ini.id),
        )


def test_rechazar_duplicado_mismo_dia(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    with pytest.raises(RuntimeError, match="pool del día"):
        create_ruta_pool_dia_entry(
            fecha=date.today(),
            turno_id=None,
            usuario_id=u.id,
            iniciador_ruta_id=int(ini.id),
        )


def test_mismo_iniciador_otro_dia_permitido(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    row2 = create_ruta_pool_dia_entry(
        fecha=date.today() + timedelta(days=1),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    assert row2.fecha == date.today() + timedelta(days=1)


def test_delete_baja_logica_no_toca_iniciador(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    db.session.commit()
    row = create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    descartar_ruta_pool_dia_entry(pool_id=int(row.id))
    db.session.refresh(ini)
    assert ini.estado_iniciador == "PENDIENTE"
    refreshed = RutaPoolDia.query.get(row.id)
    assert refreshed is not None
    assert refreshed.estado == "DESCARTADO"
    assert refreshed.deleted_at is not None


def test_listado_filtra_por_fecha(app_ctx):
    u = _mk_user()
    ini1 = _mk_iniciador()
    ini2 = _mk_iniciador()
    db.session.commit()
    fecha_hoy = _fecha_aislada()
    create_ruta_pool_dia_entry(
        fecha=fecha_hoy,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini1.id),
    )
    create_ruta_pool_dia_entry(
        fecha=fecha_hoy + timedelta(days=1),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini2.id),
    )
    items, total = list_ruta_pool_dia(fecha=fecha_hoy)
    assert total == 1
    assert len(items) == 1
    assert items[0].iniciador_ruta_id == ini1.id


def test_listado_filtra_por_estado(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    db.session.commit()
    fecha = _fecha_aislada()
    row = create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    items_en_pool, total_en_pool = list_ruta_pool_dia(fecha=fecha, estado="EN_POOL")
    assert total_en_pool == 1
    descartar_ruta_pool_dia_entry(pool_id=int(row.id))
    items_en_pool_after, total_en_pool_after = list_ruta_pool_dia(fecha=fecha, estado="EN_POOL")
    assert total_en_pool_after == 0


def test_listado_filtra_por_distrito(app_ctx):
    u = _mk_user()
    from app.models import Distrito

    dist = Distrito.query.first()
    if dist is None:
        pytest.skip("Se requiere al menos un distrito en BD")
    dom = Domicilio(calle=f"DistDom{_unique()}", numero="1", distrito_id=dist.id)
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="DENUNCIA",
        estado_iniciador="PENDIENTE",
        fecha_origen=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom.id,
        prioridad=3,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.commit()
    fecha = _fecha_aislada()
    create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    items, total = list_ruta_pool_dia(fecha=fecha, distrito_id=int(dist.id))
    assert total == 1
    assert items[0].distrito_id == dist.id


def test_listado_filtra_por_rubro(app_ctx):
    u = _mk_user()
    from app.models import Rubro

    rub = Rubro(nombre=f"RubPool{_unique()}")
    db.session.add(rub)
    db.session.flush()
    dom = Domicilio(calle=f"RubDom{_unique()}", numero="1", rubro_id=rub.id)
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="PENDIENTE",
        fecha_origen=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom.id,
        prioridad=1,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.commit()
    fecha = _fecha_aislada()
    create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    items, total = list_ruta_pool_dia(fecha=fecha, rubro_id=int(rub.id))
    assert total == 1
    assert items[0].rubro_id == rub.id


def test_listado_busca_por_q(app_ctx):
    u = _mk_user()
    calle = f"UnicaPoolQ{_unique()}"
    ini = _mk_iniciador(calle=calle)
    db.session.commit()
    fecha = _fecha_aislada()
    create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    items, total = list_ruta_pool_dia(fecha=fecha, q=calle[5:12])
    assert total >= 1


def test_agregar_desde_pool_asigna_ruta_borrador(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    ruta = _mk_ruta(user=u, estado="BORRADOR")
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G Pool", estado="ACTIVO")
    db.session.commit()
    row = create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    result = agregar_desde_pool_a_ruta(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        pool_ids=[int(row.id)],
    )
    assert len(result["items"]) == 1
    db.session.refresh(row)
    assert row.estado == "ASIGNADO_A_RUTA"
    assert row.ruta_trabajo_id == ruta.id
    assert row.ruta_item_id is not None


def test_soft_delete_item_revierte_pool_en_fecha_ruta(app_ctx):
    """OPER-RUTA.6E: al quitar ítem de grupo, pool vuelve EN_POOL en fecha de la ruta."""
    from app.domains.rutas_trabajo.services.ruta_items_service import soft_delete_ruta_item

    u = _mk_user()
    ini = _mk_iniciador()
    pool_fecha = _fecha_aislada()
    ruta_fecha = pool_fecha + timedelta(days=45)
    ruta = RutaTrabajo(
        fecha=ruta_fecha,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(100, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G Revert", estado="ACTIVO")
    db.session.commit()

    row = create_ruta_pool_dia_entry(
        fecha=pool_fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    result = agregar_desde_pool_a_ruta(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        pool_ids=[int(row.id)],
    )
    item = result["items"][0]
    db.session.refresh(row)
    assert row.estado == "ASIGNADO_A_RUTA"

    items_before, _ = list_ruta_pool_dia(fecha=ruta_fecha, estado="EN_POOL")
    assert not any(int(i.iniciador_ruta_id) == int(ini.id) for i in items_before)

    soft_delete_ruta_item(ruta_id=int(ruta.id), item_id=int(item.id))

    items_after, _ = list_ruta_pool_dia(fecha=ruta_fecha, estado="EN_POOL")
    reverted = next(i for i in items_after if int(i.iniciador_ruta_id) == int(ini.id))
    assert reverted.estado == "EN_POOL"
    assert reverted.ruta_item_id is None
    assert reverted.fecha == ruta_fecha
    assert int(reverted.iniciador_ruta_id) == int(ini.id)


def test_agregar_desde_pool_rechaza_ruta_publicada(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    ruta = _mk_ruta(user=u, estado="BORRADOR")
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G Pub", estado="ACTIVO")
    ruta.estado_ruta = "PUBLICADA"
    db.session.commit()
    row = create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    with pytest.raises(RuntimeError, match="BORRADOR"):
        agregar_desde_pool_a_ruta(
            ruta_id=int(ruta.id),
            grupo_id=int(grupo.id),
            pool_ids=[int(row.id)],
        )


def test_agregar_desde_pool_rechaza_descartado(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    ruta = _mk_ruta(user=u, estado="BORRADOR")
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G Desc", estado="ACTIVO")
    db.session.commit()
    row = create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    descartar_ruta_pool_dia_entry(pool_id=int(row.id))
    with pytest.raises(RuntimeError, match="descartada"):
        agregar_desde_pool_a_ruta(
            ruta_id=int(ruta.id),
            grupo_id=int(grupo.id),
            pool_ids=[int(row.id)],
        )


def test_api_get_pool_filtra_fecha(client, auth_headers, app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    db.session.commit()
    fecha = _fecha_aislada()
    create_ruta_pool_dia_entry(
        fecha=fecha,
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    rv = client.get(
        "/ruta-pool-dia",
        headers=auth_headers,
        query_string={"fecha": fecha.isoformat(), "page": 1, "per_page": 10},
    )
    assert rv.status_code == 200, rv.get_data(as_text=True)
    body = rv.get_json()
    assert body["meta"]["total"] >= 1
    assert body["items"][0]["estado"] == "EN_POOL"


def test_api_post_pool_y_delete(client, auth_headers, app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    db.session.commit()
    fecha = _fecha_aislada()
    rv = client.post(
        "/ruta-pool-dia",
        headers=auth_headers,
        json={
            "fecha": fecha.isoformat(),
            "iniciador_id": int(ini.id),
            "origen_tipo": "INICIADOR",
        },
    )
    assert rv.status_code == 201, rv.get_data(as_text=True)
    pool_id = rv.get_json()["item"]["pool_id"]
    rv_del = client.delete(f"/ruta-pool-dia/{pool_id}", headers=auth_headers)
    assert rv_del.status_code == 200
    assert rv_del.get_json()["item"]["estado"] == "DESCARTADO"


def test_liberar_pool_en_pool_sin_ruta_item(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    db.session.commit()
    row = create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    assert row.estado == "EN_POOL"
    liberado = liberar_ruta_pool_dia_entry(pool_id=int(row.id))
    assert liberado.estado == "DESCARTADO"
    assert liberado.deleted_at is not None


def test_liberar_pool_asignado_borrador_sin_ot(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    ruta = _mk_ruta(user=u, estado="BORRADOR")
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G Lib", estado="ACTIVO")
    db.session.commit()
    row = create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    agregar_desde_pool_a_ruta(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        pool_ids=[int(row.id)],
    )
    db.session.refresh(row)
    assert row.estado == "ASIGNADO_A_RUTA"
    item_id = row.ruta_item_id
    liberado = liberar_ruta_pool_dia_entry(pool_id=int(row.id))
    assert liberado.estado == "DESCARTADO"
    item = RutaItem.query.filter(RutaItem.id == item_id).first()
    assert item is not None
    assert item.deleted_at is not None
    db.session.refresh(ini)
    assert ini.estado_iniciador == "PENDIENTE"


def test_liberar_pool_rechaza_ruta_publicada(app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    ruta = _mk_ruta(user=u, estado="BORRADOR")
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G PubLib", estado="ACTIVO")
    db.session.commit()
    row = create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    agregar_desde_pool_a_ruta(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        pool_ids=[int(row.id)],
    )
    ruta.estado_ruta = "PUBLICADA"
    db.session.commit()
    with pytest.raises(RuntimeError, match="publicada"):
        liberar_ruta_pool_dia_entry(pool_id=int(row.id))


def test_liberar_pool_rechaza_con_ot(app_ctx):
    from app.models import OrdenTrabajo

    u = _mk_user()
    ini = _mk_iniciador()
    ruta = _mk_ruta(user=u, estado="BORRADOR")
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G OT", estado="ACTIVO")
    db.session.commit()
    row = create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    result = agregar_desde_pool_a_ruta(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        pool_ids=[int(row.id)],
    )
    item = result["items"][0]
    ot = OrdenTrabajo(numero_acta=f"{random.randint(0, 999999):06d}", mes=date.today().month, anio=date.today().year)
    db.session.add(ot)
    db.session.flush()
    item.orden_trabajo_id = ot.id
    db.session.commit()
    with pytest.raises(RuntimeError, match="Orden de Trabajo"):
        liberar_ruta_pool_dia_entry(pool_id=int(row.id))


def test_api_liberar_pool_en_pool(client, auth_headers, app_ctx):
    u = _mk_user()
    ini = _mk_iniciador()
    db.session.commit()
    fecha = _fecha_aislada()
    rv = client.post(
        "/ruta-pool-dia",
        headers=auth_headers,
        json={"fecha": fecha.isoformat(), "iniciador_id": int(ini.id), "origen_tipo": "INICIADOR"},
    )
    pool_id = rv.get_json()["item"]["pool_id"]
    rv_lib = client.post(f"/ruta-pool-dia/{pool_id}/liberar", headers=auth_headers)
    assert rv_lib.status_code == 200, rv_lib.get_data(as_text=True)
    assert rv_lib.get_json()["item"]["estado"] == "DESCARTADO"
