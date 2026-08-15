"""OPER-RUTA.3 — Notificaciones: filtros fecha/número + estado pool/ruta read-only."""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_estado_operativo_pool_service import (
    build_estado_operativo_pool_por_iniciador,
)
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.domains.actuaciones.services.pendientes_service import get_pendientes_expediente
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.models import Actuaciones, Domicilio, IniciadorRuta, Notificacion, OrdenTrabajo, RutaItem, RutaTrabajo, User


def _unique() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"op_ruta3_{_unique()}",
        email=f"op_ruta3_{_unique()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_notif_act(
    *,
    fecha: date,
    numero: str | None = None,
    vencimiento: date | None = None,
) -> tuple[Actuaciones, Notificacion]:
    ot = OrdenTrabajo(numero_acta=_unique(), anio=fecha.year, mes=fecha.month)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=numero or _unique(), anio=fecha.year, mes=fecha.month)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=fecha)
    if vencimiento is not None:
        noti.fecha_vencimiento = vencimiento
    dom = Domicilio(calle=f"Calle{_unique()}", numero="10")
    db.session.add(dom)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=fecha.month,
        anio=fecha.year,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    return act, noti


def _filters_plazo(**extra) -> ActuacionesPendientesFilters:
    base = {"omitir_rango_fecha": True, "source_type": "notificacion", "plazo_slice": "en_plazo"}
    base.update(extra)
    return ActuacionesPendientesFilters.model_validate(base)


def _mk_iniciador_reinspeccion(act: Actuaciones, user: User) -> IniciadorRuta:
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="PENDIENTE",
        fecha_origen=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=act.domicilio_id,
        actuacion_id=act.id,
        prioridad=3,
        created_by_user_id=user.id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def test_en_plazo_filtra_por_desde_hasta(app_ctx):
    f1 = date(2026, 4, 10)
    f2 = date(2026, 4, 20)
    a1, _ = _mk_notif_act(fecha=f1, vencimiento=date.today() + timedelta(days=10))
    a2, _ = _mk_notif_act(fecha=f2, vencimiento=date.today() + timedelta(days=10))
    db.session.commit()
    acts = get_pendientes_expediente(
        _filters_plazo(
            omitir_rango_fecha=False,
            desde=date(2026, 4, 15),
            hasta=date(2026, 4, 25),
        )
    )
    ids = {int(a.id) for a in acts}
    assert int(a2.id) in ids
    assert int(a1.id) not in ids


def test_por_vencer_filtra_por_desde_hasta(app_ctx):
    f1 = date(2026, 5, 1)
    f2 = date(2026, 5, 15)
    a1, _ = _mk_notif_act(fecha=f1, vencimiento=date.today() + timedelta(days=2))
    a2, _ = _mk_notif_act(fecha=f2, vencimiento=date.today() + timedelta(days=2))
    db.session.commit()
    acts = get_pendientes_expediente(
        ActuacionesPendientesFilters.model_validate(
            {
                "omitir_rango_fecha": False,
                "source_type": "notificacion",
                "plazo_slice": "por_vencer",
                "desde": date(2026, 5, 10),
                "hasta": date(2026, 5, 20),
            }
        )
    )
    ids = {int(a.id) for a in acts}
    assert int(a2.id) in ids
    assert int(a1.id) not in ids


def test_pendiente_reinspeccion_filtra_por_desde_hasta(app_ctx):
    u = _mk_user()
    f1 = date(2026, 6, 1)
    f2 = date(2026, 6, 15)
    a1, n1 = _mk_notif_act(fecha=f1, vencimiento=date.today() - timedelta(days=1))
    a2, n2 = _mk_notif_act(fecha=f2, vencimiento=date.today() - timedelta(days=1))
    _mk_iniciador_reinspeccion(a1, u)
    _mk_iniciador_reinspeccion(a2, u)
    db.session.commit()
    acts = list_reinspeccion_notificacion_operativas(
        desde=date(2026, 6, 10),
        hasta=date(2026, 6, 20),
    )
    ids = {int(a.id) for a in acts}
    assert int(a2.id) in ids
    assert int(a1.id) not in ids


def test_en_plazo_filtra_por_numero_notificacion(app_ctx):
    num = _unique()
    act_ok, _ = _mk_notif_act(fecha=date(2026, 7, 1), numero=num, vencimiento=date.today() + timedelta(days=8))
    _mk_notif_act(fecha=date(2026, 7, 2), numero=_unique(), vencimiento=date.today() + timedelta(days=8))
    db.session.commit()
    acts = get_pendientes_expediente(_filters_plazo(numero_notificacion=num[1:5]))
    assert {int(a.id) for a in acts} == {int(act_ok.id)}


def test_por_vencer_filtra_por_numero_notificacion(app_ctx):
    num = _unique()
    act_ok, _ = _mk_notif_act(fecha=date(2026, 7, 5), numero=num, vencimiento=date.today() + timedelta(days=2))
    _mk_notif_act(fecha=date(2026, 7, 6), numero=_unique(), vencimiento=date.today() + timedelta(days=2))
    db.session.commit()
    acts = get_pendientes_expediente(
        ActuacionesPendientesFilters.model_validate(
            {
                "omitir_rango_fecha": True,
                "source_type": "notificacion",
                "plazo_slice": "por_vencer",
                "numero_notificacion": num[0:4],
            }
        )
    )
    assert {int(a.id) for a in acts} == {int(act_ok.id)}


def test_pendiente_reinspeccion_filtra_por_numero_notificacion(app_ctx):
    u = _mk_user()
    num = _unique()
    act_ok, _ = _mk_notif_act(fecha=date(2026, 8, 1), numero=num, vencimiento=date.today() - timedelta(days=1))
    act_no, _ = _mk_notif_act(fecha=date(2026, 8, 2), numero=_unique(), vencimiento=date.today() - timedelta(days=1))
    _mk_iniciador_reinspeccion(act_ok, u)
    _mk_iniciador_reinspeccion(act_no, u)
    db.session.commit()
    acts = list_reinspeccion_notificacion_operativas(numero_notificacion=num[1:5])
    assert {int(a.id) for a in acts} == {int(act_ok.id)}


def test_estado_pendiente_iniciador_libre(app_ctx):
    u = _mk_user()
    act, _ = _mk_notif_act(fecha=date(2026, 9, 1), vencimiento=date.today() - timedelta(days=1))
    ini = _mk_iniciador_reinspeccion(act, u)
    db.session.commit()
    ctx = build_estado_operativo_pool_por_iniciador([int(ini.id)])[int(ini.id)]
    assert ctx["estado_operativo_pool"] == "pendiente"


def test_estado_en_pool(app_ctx):
    u = _mk_user()
    act, _ = _mk_notif_act(fecha=date(2026, 9, 2), vencimiento=date.today() - timedelta(days=1))
    ini = _mk_iniciador_reinspeccion(act, u)
    ruta = RutaTrabajo(
        fecha=date(2026, 2, 26),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(200, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    db.session.commit()
    create_ruta_pool_dia_entry(
        fecha=date(2026, 2, 26),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta.id),
    )
    ctx = build_estado_operativo_pool_por_iniciador([int(ini.id)])[int(ini.id)]
    assert ctx["estado_operativo_pool"] == "en_pool"
    assert ctx["pool_status"] == "EN_POOL"
    assert ctx["pool_fecha"] == "2026-02-26"
    assert ctx["ruta_trabajo_id"] == int(ruta.id)
    assert ctx["ruta_numero"] == int(ruta.numero)
    assert ctx["ruta_fecha"] == "2026-02-26"
    assert ctx["ruta_turno"] == "MANIANA"


def test_estado_en_ruta_borrador(app_ctx):
    u = _mk_user()
    act, _ = _mk_notif_act(fecha=date(2026, 9, 3), vencimiento=date.today() - timedelta(days=1))
    ini = _mk_iniciador_reinspeccion(act, u)
    ruta = RutaTrabajo(
        fecha=date.today() + timedelta(days=50),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(200, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G", estado="ACTIVO")
    db.session.commit()
    assign_iniciadores_to_grupo(ruta_id=int(ruta.id), grupo_id=int(grupo.id), iniciador_ids=[int(ini.id)])
    ctx = build_estado_operativo_pool_por_iniciador([int(ini.id)])[int(ini.id)]
    assert ctx["estado_operativo_pool"] == "en_ruta_borrador"
    assert ctx["grupo_id"] == int(grupo.id)
    assert ctx["grupo_nombre"] == "G"
    assert ctx["ruta_numero"] == int(ruta.numero)


def test_estado_en_ruta_publicada(app_ctx):
    u = _mk_user()
    act, _ = _mk_notif_act(fecha=date(2026, 9, 4), vencimiento=date.today() - timedelta(days=1))
    ini = _mk_iniciador_reinspeccion(act, u)
    ruta = RutaTrabajo(
        fecha=date.today() + timedelta(days=60),
        turno="TARDE",
        estado_ruta="PUBLICADA",
        numero=random.randint(200, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        ruta_grupo_id=None,
        iniciador_ruta_id=ini.id,
        estado_ruta_item="ASIGNADO",
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.commit()
    ctx = build_estado_operativo_pool_por_iniciador([int(ini.id)])[int(ini.id)]
    assert ctx["estado_operativo_pool"] == "en_ruta_publicada"


def test_estado_resuelto_iniciador_cumplido(app_ctx):
    u = _mk_user()
    act, _ = _mk_notif_act(fecha=date(2026, 9, 5), vencimiento=date.today() - timedelta(days=1))
    ini = _mk_iniciador_reinspeccion(act, u)
    ini.estado_iniciador = "CUMPLIDO"
    db.session.commit()
    ctx = build_estado_operativo_pool_por_iniciador([int(ini.id)])[int(ini.id)]
    assert ctx["estado_operativo_pool"] == "resuelto"


def test_en_plazo_expediente_marca_no_elegible(app_ctx, client, auth_headers):
    act, _ = _mk_notif_act(fecha=date(2026, 7, 10), vencimiento=date.today() + timedelta(days=10))
    db.session.commit()
    rv = client.get(
        "/actuaciones/pendientes/expediente",
        headers=auth_headers,
        query_string={
            "source_type": "notificacion",
            "omitir_rango_fecha": "true",
            "plazo_slice": "en_plazo",
        },
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    row = next((i for i in items if i["id"] == act.id), None)
    assert row is not None
    assert row["estado_operativo_pool"] == "no_elegible"


def test_pendientes_notificacion_route_expone_estado_en_pool(app_ctx, client, auth_headers):
    u = _mk_user()
    act, _ = _mk_notif_act(fecha=date(2026, 10, 1), vencimiento=date.today() - timedelta(days=1))
    ini = _mk_iniciador_reinspeccion(act, u)
    db.session.commit()
    create_ruta_pool_dia_entry(
        fecha=date.today(),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    rv = client.get("/actuaciones/pendientes-notificacion", headers=auth_headers)
    assert rv.status_code == 200
    row = next((i for i in rv.get_json() if i["id"] == act.id), None)
    assert row is not None
    assert row["estado_operativo_pool"] == "en_pool"


def test_pendientes_notificacion_incluye_en_ruta_borrador(app_ctx, client, auth_headers):
    """OPER-RUTA.6D: iniciador PLANIFICADO en grupo borrador sigue en bandeja."""
    u = _mk_user()
    act, _ = _mk_notif_act(fecha=date(2026, 10, 2), vencimiento=date.today() - timedelta(days=1))
    ini = _mk_iniciador_reinspeccion(act, u)
    ruta = RutaTrabajo(
        fecha=date.today() + timedelta(days=45),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(200, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G1", estado="ACTIVO")
    db.session.commit()
    assign_iniciadores_to_grupo(ruta_id=int(ruta.id), grupo_id=int(grupo.id), iniciador_ids=[int(ini.id)])
    db.session.refresh(ini)
    assert ini.estado_iniciador == "PLANIFICADO"
    acts = list_reinspeccion_notificacion_operativas()
    assert int(act.id) in {int(a.id) for a in acts}
    rv = client.get("/actuaciones/pendientes-notificacion", headers=auth_headers)
    assert rv.status_code == 200
    row = next((i for i in rv.get_json() if i["id"] == act.id), None)
    assert row is not None
    assert row["estado_operativo_pool"] == "en_ruta_borrador"
    assert row.get("grupo_nombre") == "G1"


def test_pendientes_notificacion_excluye_cumplido(app_ctx, client, auth_headers):
    u = _mk_user()
    act, _ = _mk_notif_act(fecha=date(2026, 10, 3), vencimiento=date.today() - timedelta(days=1))
    ini = _mk_iniciador_reinspeccion(act, u)
    ini.estado_iniciador = "CUMPLIDO"
    db.session.commit()
    acts = list_reinspeccion_notificacion_operativas()
    assert int(act.id) not in {int(a.id) for a in acts}
    rv = client.get("/actuaciones/pendientes-notificacion", headers=auth_headers)
    assert rv.status_code == 200
    assert all(i["id"] != act.id for i in rv.get_json())
