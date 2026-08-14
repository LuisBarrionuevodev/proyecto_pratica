"""OPER-RUTA.4 — Comprobaciones: filtros fecha/número + estado pool/ruta read-only."""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.notificacion_estado_operativo_pool_service import (
    build_estado_operativo_pool_por_iniciador,
)
from app.domains.actuaciones.services.pendientes_service import (
    get_pendientes_expediente,
    get_pendientes_oficio,
)
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.models import (
    Actuaciones,
    Comprobacion,
    Domicilio,
    Expediente,
    IniciadorRuta,
    JuzgadoCatalogo,
    Oficio,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)


def _unique() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"op_ruta4_{_unique()}",
        email=f"op_ruta4_{_unique()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_comp_sin_expediente(*, fecha: date, numero: str | None = None) -> Actuaciones:
    dom = Domicilio(calle=f"Calle{_unique()}", numero="10")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique(), anio=fecha.year, mes=fecha.month)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=numero or _unique(), anio=fecha.year, mes=fecha.month, motivo="test")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=fecha.month,
        anio=fecha.year,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def _mk_comp_pendiente_oficio(*, fecha: date, numero: str | None = None) -> Actuaciones:
    act = _mk_comp_sin_expediente(fecha=fecha, numero=numero)
    ex_env = Expediente(
        numero_expediente=_unique()[:6],
        anio=str(fecha.year),
        fecha_expediente=fecha + timedelta(days=1),
        tipo_expediente="ENVIO_ACTA",
        comprobacion_id=act.comprobacion_id,
        oficio_id=None,
    )
    db.session.add(ex_env)
    db.session.flush()
    return act


def _mk_reinspeccion_circuito(
    *,
    fecha: date,
    numero: str | None = None,
    user: User | None = None,
    with_iniciador: bool = True,
) -> tuple[Actuaciones, IniciadorRuta | None]:
    jz = JuzgadoCatalogo(codigo=f"JZ4{_unique()}"[:32], nombre=f"Jz {_unique()}")
    db.session.add(jz)
    db.session.flush()
    act = _mk_comp_pendiente_oficio(fecha=fecha, numero=numero)
    ofi = Oficio(
        numero_oficio=_unique()[:8],
        anio=fecha.year,
        fecha_oficio=fecha + timedelta(days=2),
        causa="causa test",
        juzgado_id=jz.id,
        comprobacion_id=act.comprobacion_id,
    )
    db.session.add(ofi)
    db.session.flush()
    ex_resp = Expediente(
        numero_expediente=_unique()[:6],
        anio=str(fecha.year),
        fecha_expediente=fecha + timedelta(days=3),
        tipo_expediente="RESPUESTA_OFICIO",
        comprobacion_id=act.comprobacion_id,
        oficio_id=ofi.id,
    )
    db.session.add(ex_resp)
    db.session.flush()
    ini = None
    if with_iniciador:
        u = user or _mk_user()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=fecha,
            anio=fecha.year,
            mes=fecha.month,
            domicilio_id=act.domicilio_id,
            actuacion_id=act.id,
            oficio_id=ofi.id,
            prioridad=3,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
    return act, ini


def _filters(**extra) -> ActuacionesPendientesFilters:
    base = {"omitir_rango_fecha": True, "source_type": "comprobacion"}
    base.update(extra)
    return ActuacionesPendientesFilters.model_validate(base)


def test_expediente_filtra_por_desde_hasta(app_ctx):
    f1 = date(2026, 4, 10)
    f2 = date(2026, 4, 20)
    a1 = _mk_comp_sin_expediente(fecha=f1)
    a2 = _mk_comp_sin_expediente(fecha=f2)
    db.session.commit()
    acts = get_pendientes_expediente(
        _filters(
            omitir_rango_fecha=False,
            desde=date(2026, 4, 15),
            hasta=date(2026, 4, 25),
        )
    )
    ids = {int(a.id) for a in acts}
    assert int(a2.id) in ids
    assert int(a1.id) not in ids


def test_oficio_filtra_por_desde_hasta(app_ctx):
    f1 = date(2026, 5, 1)
    f2 = date(2026, 5, 15)
    a1 = _mk_comp_pendiente_oficio(fecha=f1)
    a2 = _mk_comp_pendiente_oficio(fecha=f2)
    db.session.commit()
    acts = get_pendientes_oficio(
        ActuacionesPendientesFilters.model_validate(
            {
                "omitir_rango_fecha": False,
                "desde": date(2026, 5, 10),
                "hasta": date(2026, 5, 20),
            }
        )
    )
    ids = {int(a.id) for a in acts}
    assert int(a2.id) in ids
    assert int(a1.id) not in ids


def test_reinspeccion_filtra_por_desde_hasta(app_ctx):
    f1 = date(2026, 6, 1)
    f2 = date(2026, 6, 15)
    a1, _ = _mk_reinspeccion_circuito(fecha=f1)
    a2, _ = _mk_reinspeccion_circuito(fecha=f2)
    db.session.commit()
    filas = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate(
            {
                "omitir_rango_fecha": False,
                "desde": date(2026, 6, 10),
                "hasta": date(2026, 6, 20),
            }
        )
    )
    ids = {int(f[0].id) for f in filas}
    assert int(a2.id) in ids
    assert int(a1.id) not in ids


def test_expediente_filtra_por_numero_comprobacion(app_ctx):
    num = _unique()
    act_ok = _mk_comp_sin_expediente(fecha=date(2026, 7, 1), numero=num)
    _mk_comp_sin_expediente(fecha=date(2026, 7, 2), numero=_unique())
    db.session.commit()
    acts = get_pendientes_expediente(_filters(numero_comprobacion=num[1:5]))
    assert {int(a.id) for a in acts} == {int(act_ok.id)}


def test_oficio_filtra_por_numero_comprobacion(app_ctx):
    num = _unique()
    act_ok = _mk_comp_pendiente_oficio(fecha=date(2026, 7, 5), numero=num)
    _mk_comp_pendiente_oficio(fecha=date(2026, 7, 6), numero=_unique())
    db.session.commit()
    acts = get_pendientes_oficio(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "numero_comprobacion": num[0:4]}
        )
    )
    assert {int(a.id) for a in acts} == {int(act_ok.id)}


def test_reinspeccion_filtra_por_numero_comprobacion(app_ctx, client, auth_headers):
    num = _unique()
    act_ok, _ = _mk_reinspeccion_circuito(fecha=date(2026, 8, 1), numero=num)
    _mk_reinspeccion_circuito(fecha=date(2026, 8, 2), numero=_unique())
    db.session.commit()
    rv = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio",
        headers=auth_headers,
        query_string={"omitir_rango_fecha": "true", "numero_comprobacion": num[1:5]},
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    assert {int(i["id"]) for i in items} == {int(act_ok.id)}


def test_expediente_route_marca_no_elegible(app_ctx, client, auth_headers):
    act = _mk_comp_sin_expediente(fecha=date(2026, 7, 10))
    db.session.commit()
    rv = client.get(
        "/actuaciones/pendientes/expediente",
        headers=auth_headers,
        query_string={"source_type": "comprobacion", "omitir_rango_fecha": "true"},
    )
    assert rv.status_code == 200
    row = next((i for i in rv.get_json()["items"] if i["id"] == act.id), None)
    assert row is not None
    assert row["estado_operativo_pool"] == "no_elegible"


def test_oficio_sin_iniciador_marca_no_elegible(app_ctx, client, auth_headers):
    act = _mk_comp_pendiente_oficio(fecha=date(2026, 7, 11))
    db.session.commit()
    rv = client.get(
        "/actuaciones/pendientes/oficio",
        headers=auth_headers,
        query_string={"omitir_rango_fecha": "true"},
    )
    assert rv.status_code == 200
    row = next((i for i in rv.get_json()["items"] if i["id"] == act.id), None)
    assert row is not None
    assert row["estado_operativo_pool"] == "no_elegible"


def test_reinspeccion_con_iniciador_libre_pendiente(app_ctx, client, auth_headers):
    act, ini = _mk_reinspeccion_circuito(fecha=date(2026, 8, 5))
    db.session.commit()
    rv = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio",
        headers=auth_headers,
        query_string={"omitir_rango_fecha": "true"},
    )
    assert rv.status_code == 200
    row = next((i for i in rv.get_json()["items"] if i["id"] == act.id), None)
    assert row is not None
    assert int(row["iniciador_id"]) == int(ini.id)
    assert row["estado_operativo_pool"] == "pendiente"


def test_reinspeccion_en_pool(app_ctx, client, auth_headers):
    u = _mk_user()
    act, ini = _mk_reinspeccion_circuito(fecha=date(2026, 9, 1), user=u)
    db.session.commit()
    create_ruta_pool_dia_entry(
        fecha=date.today() + timedelta(days=120),
        turno_id=None,
        usuario_id=u.id,
        iniciador_ruta_id=int(ini.id),
    )
    ctx = build_estado_operativo_pool_por_iniciador([int(ini.id)])[int(ini.id)]
    assert ctx["estado_operativo_pool"] == "en_pool"


def test_reinspeccion_en_ruta_borrador(app_ctx):
    u = _mk_user()
    act, ini = _mk_reinspeccion_circuito(fecha=date(2026, 9, 2), user=u)
    ruta = RutaTrabajo(
        fecha=date.today() + timedelta(days=130),
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


def test_reinspeccion_en_ruta_publicada(app_ctx):
    u = _mk_user()
    act, ini = _mk_reinspeccion_circuito(fecha=date(2026, 9, 3), user=u)
    ruta = RutaTrabajo(
        fecha=date.today() + timedelta(days=140),
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


def test_reinspeccion_resuelto(app_ctx, client, auth_headers):
    u = _mk_user()
    act, ini = _mk_reinspeccion_circuito(fecha=date(2026, 9, 4), user=u)
    ini.estado_iniciador = "CUMPLIDO"
    db.session.commit()
    ctx = build_estado_operativo_pool_por_iniciador([int(ini.id)])[int(ini.id)]
    assert ctx["estado_operativo_pool"] == "resuelto"
