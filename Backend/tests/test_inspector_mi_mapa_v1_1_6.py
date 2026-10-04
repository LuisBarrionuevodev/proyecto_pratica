"""V1.1-INSPECTOR.6 — Mi mapa (scope GET /map/operativo/*)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.usuarios.security.inspector_scope_policy import CROSS_INSPECTOR_ACCESS_DETAIL
from app.domains.usuarios.security.passwords import hash_password
from app.domains.usuarios.security.role_permissions import relevador_may_access
from app.domains.usuarios.services.users_service import create_user_admin
from app.models import (
    Actuaciones,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaGrupo,
    RutaGrupoInspector,
    RutaItem,
    RutaTrabajo,
    Turno,
    User,
)
from app.models.turno import TipoTurno
from tests.helpers.fixture_isolation import uniq_ruta_numero, unique_ot_numero
from tests.indicadores_cierre_fixtures import vincular_cierre_realizado

_QUERY = "desde=2026-07-01&hasta=2026-07-31"


def _suf() -> str:
    return uuid4().hex[:8]


def _mk_turno() -> Turno:
    t = Turno.query.first()
    if t:
        return t
    t = Turno(turno=TipoTurno.MANIANA)
    db.session.add(t)
    db.session.flush()
    return t


def _mk_inspector() -> Inspector:
    turno = _mk_turno()
    ins = Inspector(nombre=f"Insp {_suf()}", legajo=_suf()[:5], turno_id=turno.id)
    db.session.add(ins)
    db.session.flush()
    return ins


def _mk_relevador(inspector: Inspector) -> User:
    u = User(
        username=f"rel_{_suf()}",
        email=f"rel_{_suf()}@t.local",
        password_hash=hash_password("x"),
        role="relevador",
        is_active=True,
        inspector_id=inspector.id,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _set_geocode(dom: Domicilio, *, lat: float = -26.824, lng: float = -65.222) -> None:
    geo = DomicilioGeocode(
        domicilio_id=dom.id,
        geo_status="OK",
        lat=lat,
        lng=lng,
        source="AUTO",
    )
    db.session.add(geo)
    db.session.flush()


def _mk_dom(actor_id: int, tag: str) -> Domicilio:
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=f"Rub {tag}")
        db.session.add(rub)
        db.session.flush()
    dom = Domicilio(calle=f"Calle {tag}", numero="1", rubro_id=rub.id)
    db.session.add(dom)
    db.session.flush()
    _set_geocode(dom)
    return dom


def _mk_ruta_item(
    actor_id: int,
    fecha: date,
    inspector_ids: list[int],
    *,
    estado_ruta_item: str,
    tag: str,
) -> RutaItem:
    dom = _mk_dom(actor_id, tag)
    ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=fecha.year, mes=fecha.month)
    db.session.add(ot)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=fecha,
        anio=fecha.year,
        mes=fecha.month,
        domicilio_id=dom.id,
        created_by_user_id=actor_id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fecha,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        numero=uniq_ruta_numero(),
        created_by_user_id=actor_id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = RutaGrupo(
        ruta_trabajo_id=ruta.id,
        nombre=f"G {tag}",
        created_by_user_id=actor_id,
    )
    db.session.add(grupo)
    db.session.flush()
    for iid in inspector_ids:
        db.session.add(
            RutaGrupoInspector(
                ruta_grupo_id=grupo.id,
                inspector_id=int(iid),
                created_by_user_id=actor_id,
            )
        )
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        ruta_grupo_id=grupo.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item=estado_ruta_item,
        created_by_user_id=actor_id,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _mk_backlog_iniciador(actor_id: int, fecha: date, tag: str) -> IniciadorRuta:
    dom = _mk_dom(actor_id, f"backlog_{tag}")
    ini = IniciadorRuta(
        tipo_iniciador="DENUNCIA",
        estado_iniciador="PENDIENTE",
        fecha_origen=fecha,
        anio=fecha.year,
        mes=fecha.month,
        domicilio_id=dom.id,
        created_by_user_id=actor_id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def _auth(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def _feature_layers(resp) -> set[str]:
    body = resp.get_json()
    layers: set[str] = set()
    for feat in body.get("features") or []:
        layer = (feat.get("properties") or {}).get("map_layer")
        if layer:
            layers.add(str(layer))
    return layers


def _feature_ruta_item_ids(resp) -> set[int]:
    body = resp.get_json()
    ids: set[int] = set()
    for feat in body.get("features") or []:
        rid = (feat.get("properties") or {}).get("ruta_item_id")
        if rid is not None:
            ids.add(int(rid))
    return ids


@pytest.fixture
def map_scope(app):
    with app.app_context():
        admin = User.query.get(
            create_user_admin(
                username=f"adm_{_suf()}",
                email=f"adm_{_suf()}@t.local",
                password="secret123",
                role="admin",
                inspector_id=None,
            )
        )
        usuario = User.query.get(
            create_user_admin(
                username=f"usr_{_suf()}",
                email=f"usr_{_suf()}@t.local",
                password="secret123",
                role="usuario",
                inspector_id=None,
            )
        )
        ins_a = _mk_inspector()
        ins_b = _mk_inspector()
        user_a = _mk_relevador(ins_a)
        user_b = _mk_relevador(ins_b)
        fecha = date(2026, 7, 15)
        item_a_proc = _mk_ruta_item(
            admin.id, fecha, [ins_a.id], estado_ruta_item="EN_PROCESO", tag=f"a_proc_{_suf()}"
        )
        item_a_asig = _mk_ruta_item(
            admin.id, fecha, [ins_a.id], estado_ruta_item="ASIGNADO", tag=f"a_asig_{_suf()}"
        )
        item_b = _mk_ruta_item(
            admin.id, fecha, [ins_b.id], estado_ruta_item="EN_PROCESO", tag=f"b_{_suf()}"
        )
        _mk_backlog_iniciador(admin.id, fecha, _suf())

        dom_c_a = _mk_dom(admin.id, f"cierre_a_{_suf()}")
        act_a = Actuaciones(
            fecha=fecha,
            mes=fecha.month,
            anio=fecha.year,
            domicilio_id=dom_c_a.id,
            orden_trabajo_id=item_a_proc.orden_trabajo_id,
        )
        db.session.add(act_a)
        db.session.flush()
        cierre_a = vincular_cierre_realizado(act_a, fecha, inspector_id=ins_a.id)

        dom_c_b = _mk_dom(admin.id, f"cierre_b_{_suf()}")
        act_b = Actuaciones(
            fecha=fecha,
            mes=fecha.month,
            anio=fecha.year,
            domicilio_id=dom_c_b.id,
            orden_trabajo_id=item_b.orden_trabajo_id,
        )
        db.session.add(act_b)
        db.session.flush()
        cierre_b = vincular_cierre_realizado(act_b, fecha, inspector_id=ins_b.id)

        db.session.commit()
        data = {
            "admin": admin,
            "usuario": usuario,
            "user_a": user_a,
            "user_b": user_b,
            "ins_a": ins_a,
            "ins_b": ins_b,
            "fecha": fecha,
            "item_a_proc": item_a_proc,
            "item_a_asig": item_a_asig,
            "item_b": item_b,
            "cierre_a": cierre_a,
            "cierre_b": cierre_b,
        }
        yield data
        db.session.rollback()


def test_relevador_map_allowlist() -> None:
    assert relevador_may_access("GET", "/map/operativo/pendientes")
    assert relevador_may_access("GET", "/map/operativo/realizados")
    assert not relevador_may_access("GET", "/api/map/operativo/pendientes")
    assert not relevador_may_access("GET", "/map/puntos")
    assert not relevador_may_access("POST", "/api/map/geocode/manual")


@pytest.mark.parametrize("path", ("/map/operativo/pendientes", "/map/operativo/realizados"))
def test_map_operativo_sin_jwt_401(client, path) -> None:
    resp = client.get(f"{path}?{_QUERY}")
    assert resp.status_code == 401


def test_inspector_pendientes_solo_sus_items_sin_cola(client, map_scope) -> None:
    d = map_scope
    resp = client.get(f"/map/operativo/pendientes?{_QUERY}", headers=_auth(d["user_a"].id))
    assert resp.status_code == 200
    layers = _feature_layers(resp)
    assert "iniciador_backlog" not in layers
    ids = _feature_ruta_item_ids(resp)
    assert d["item_a_proc"].id in ids
    assert d["item_a_asig"].id in ids
    assert d["item_b"].id not in ids


def test_inspector_b_no_ve_pendientes_de_a(client, map_scope) -> None:
    d = map_scope
    resp = client.get(f"/map/operativo/pendientes?{_QUERY}", headers=_auth(d["user_b"].id))
    assert resp.status_code == 200
    ids = _feature_ruta_item_ids(resp)
    assert d["item_b"].id in ids
    assert d["item_a_proc"].id not in ids
    assert d["item_a_asig"].id not in ids


def test_inspector_realizados_scope(client, map_scope) -> None:
    d = map_scope
    resp_a = client.get(f"/map/operativo/realizados?{_QUERY}", headers=_auth(d["user_a"].id))
    assert resp_a.status_code == 200
    ids_a = _feature_ruta_item_ids(resp_a)
    assert d["cierre_a"].id in ids_a
    assert d["cierre_b"].id not in ids_a

    resp_b = client.get(f"/map/operativo/realizados?{_QUERY}", headers=_auth(d["user_b"].id))
    ids_b = _feature_ruta_item_ids(resp_b)
    assert d["cierre_b"].id in ids_b
    assert d["cierre_a"].id not in ids_b


@pytest.mark.parametrize("path", ("/map/operativo/pendientes", "/map/operativo/realizados"))
def test_inspector_cross_inspector_id_403(client, map_scope, path) -> None:
    d = map_scope
    resp = client.get(
        f"{path}?{_QUERY}&inspector_id={d['ins_b'].id}",
        headers=_auth(d["user_a"].id),
    )
    assert resp.status_code == 403
    assert resp.get_json()["detail"] == CROSS_INSPECTOR_ACCESS_DETAIL


@pytest.mark.parametrize(
    "path",
    (
        "/map/puntos",
        "/map/points",
        "/map/pendientes",
        "/map/gestion-domicilios",
        "/map/details/1",
        "/api/map/operativo/pendientes",
        "/api/map/operativo/realizados",
    ),
)
def test_inspector_map_rutas_denegadas_403(client, map_scope, path) -> None:
    d = map_scope
    if path.endswith("/1"):
        resp = client.get(path, headers=_auth(d["user_a"].id))
    else:
        resp = client.get(f"{path}?{_QUERY}", headers=_auth(d["user_a"].id))
    assert resp.status_code == 403


def test_inspector_post_geocode_manual_403(client, map_scope) -> None:
    d = map_scope
    resp = client.post(
        "/api/map/geocode/manual",
        headers=_auth(d["user_a"].id),
        json={"domicilio_id": 1, "lat": -26.8, "lng": -65.2},
    )
    assert resp.status_code == 403


def test_admin_pendientes_incluye_cola_global(client, map_scope) -> None:
    d = map_scope
    resp = client.get(f"/map/operativo/pendientes?{_QUERY}", headers=_auth(d["admin"].id))
    assert resp.status_code == 200
    assert "iniciador_backlog" in _feature_layers(resp)


def test_usuario_realizados_puede_filtrar_inspector(client, map_scope) -> None:
    d = map_scope
    resp = client.get(
        f"/map/operativo/realizados?{_QUERY}&inspector_id={d['ins_b'].id}",
        headers=_auth(d["usuario"].id),
    )
    assert resp.status_code == 200
    ids = _feature_ruta_item_ids(resp)
    assert d["cierre_b"].id in ids
    assert d["cierre_a"].id not in ids
