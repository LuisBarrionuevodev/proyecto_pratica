"""V1.1-INSPECTOR.2 — política de scope y helpers de consulta."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.actuaciones.schemas.list_filters import ActuacionesListFilters
from app.domains.usuarios.security.inspector_scope_policy import (
    CROSS_INSPECTOR_ACCESS_DETAIL,
    InspectorScopeError,
    resolve_effective_inspector_id,
)
from app.domains.usuarios.security.passwords import hash_password
from app.domains.usuarios.services.inspector_query_scope import (
    scope_actuaciones_to_inspector,
    scope_ruta_items_to_inspector,
)
from app.domains.usuarios.services.users_service import create_user_admin
from app.models import (
    Actuaciones,
    Domicilio,
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
    actuaciones_inspector,
)
from app.models.turno import TipoTurno
from tests.helpers.service_actor import jwt_request_context


def _suffix() -> str:
    return uuid4().hex[:10]


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
    ins = Inspector(nombre=f"Insp {_suffix()}", legajo=_suffix()[:6], turno_id=turno.id)
    db.session.add(ins)
    db.session.flush()
    return ins


def _mk_relevador_user(inspector: Inspector) -> User:
    user = User(
        username=f"rel_{_suffix()}",
        email=f"rel_{_suffix()}@t.local",
        password_hash=hash_password("secret"),
        role="relevador",
        is_active=True,
        inspector_id=inspector.id,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _mk_admin_user() -> User:
    uid = create_user_admin(
        username=f"adm_{_suffix()}",
        email=f"adm_{_suffix()}@t.local",
        password="secret123",
        role="admin",
        inspector_id=None,
    )
    return User.query.get(uid)


def _mk_usuario_user() -> User:
    uid = create_user_admin(
        username=f"usr_{_suffix()}",
        email=f"usr_{_suffix()}@t.local",
        password="secret123",
        role="usuario",
        inspector_id=None,
    )
    return User.query.get(uid)


def _mk_iniciador(actor_id: int) -> IniciadorRuta:
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=f"Rub {_suffix()}")
        db.session.add(rub)
        db.session.flush()
    dom = Domicilio(calle=f"Calle {_suffix()}", numero="1", rubro_id=rub.id)
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 6, 1),
        anio=2026,
        mes=6,
        domicilio_id=dom.id,
        created_by_user_id=actor_id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def _mk_ruta_items_for_inspectors(
    actor_id: int,
    ins_a: Inspector,
    ins_b: Inspector,
    ini_a: IniciadorRuta,
    ini_b: IniciadorRuta,
) -> tuple[RutaItem, RutaItem]:
    ruta = RutaTrabajo(
        fecha=date(2026, 6, 10),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(1000, 99999),
        created_by_user_id=actor_id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo_a = RutaGrupo(
        ruta_trabajo_id=ruta.id,
        nombre=f"GA {_suffix()}",
        created_by_user_id=actor_id,
    )
    grupo_b = RutaGrupo(
        ruta_trabajo_id=ruta.id,
        nombre=f"GB {_suffix()}",
        created_by_user_id=actor_id,
    )
    db.session.add_all([grupo_a, grupo_b])
    db.session.flush()
    db.session.add(
        RutaGrupoInspector(
            ruta_grupo_id=grupo_a.id,
            inspector_id=ins_a.id,
            created_by_user_id=actor_id,
        )
    )
    db.session.add(
        RutaGrupoInspector(
            ruta_grupo_id=grupo_b.id,
            inspector_id=ins_b.id,
            created_by_user_id=actor_id,
        )
    )
    item_a = RutaItem(
        ruta_trabajo_id=ruta.id,
        ruta_grupo_id=grupo_a.id,
        iniciador_ruta_id=ini_a.id,
        created_by_user_id=actor_id,
    )
    item_b = RutaItem(
        ruta_trabajo_id=ruta.id,
        ruta_grupo_id=grupo_b.id,
        iniciador_ruta_id=ini_b.id,
        created_by_user_id=actor_id,
    )
    db.session.add_all([item_a, item_b])
    db.session.flush()
    return item_a, item_b


def _mk_actuacion_for_inspector(inspector: Inspector) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_suffix()[:6], anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 6, 15),
        mes=6,
        anio=2026,
        orden_trabajo_id=ot.id,
    )
    db.session.add(act)
    db.session.flush()
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=act.id,
            inspector_id=inspector.id,
        )
    )
    db.session.flush()
    return act


@pytest.fixture
def scope_fixture(app):
    """Inspectores A/B, usuarios y datos de ruta/actuación."""
    with app.app_context():
        admin = _mk_admin_user()
        ins_a = _mk_inspector()
        ins_b = _mk_inspector()
        user_a = _mk_relevador_user(ins_a)
        user_b = _mk_relevador_user(ins_b)
        usuario = _mk_usuario_user()
        ini_a = _mk_iniciador(admin.id)
        ini_b = _mk_iniciador(admin.id)
        item_a, item_b = _mk_ruta_items_for_inspectors(
            admin.id, ins_a, ins_b, ini_a, ini_b
        )
        act_a = _mk_actuacion_for_inspector(ins_a)
        act_b = _mk_actuacion_for_inspector(ins_b)
        db.session.commit()
        data = {
            "admin": admin,
            "usuario": usuario,
            "user_a": user_a,
            "user_b": user_b,
            "ins_a": ins_a,
            "ins_b": ins_b,
            "item_a": item_a,
            "item_b": item_b,
            "act_a": act_a,
            "act_b": act_b,
        }
        yield data
        db.session.rollback()


def test_inspector_a_resolves_own_id(scope_fixture) -> None:
    d = scope_fixture
    assert resolve_effective_inspector_id(None, user=d["user_a"]) == d["ins_a"].id
    assert resolve_effective_inspector_id(d["ins_a"].id, user=d["user_a"]) == d["ins_a"].id


def test_inspector_a_cross_access_forbidden(scope_fixture) -> None:
    d = scope_fixture
    with pytest.raises(InspectorScopeError) as exc:
        resolve_effective_inspector_id(d["ins_b"].id, user=d["user_a"])
    assert exc.value.status_code == 403
    assert str(exc.value) == CROSS_INSPECTOR_ACCESS_DETAIL


def test_inspector_b_cannot_scope_a_data_via_policy(scope_fixture) -> None:
    d = scope_fixture
    with pytest.raises(InspectorScopeError):
        resolve_effective_inspector_id(d["ins_a"].id, user=d["user_b"])


def test_admin_resolves_any_or_none(scope_fixture) -> None:
    d = scope_fixture
    assert resolve_effective_inspector_id(None, user=d["admin"]) is None
    assert resolve_effective_inspector_id(d["ins_a"].id, user=d["admin"]) == d["ins_a"].id
    assert resolve_effective_inspector_id(d["ins_b"].id, user=d["admin"]) == d["ins_b"].id


def test_usuario_keeps_global_filter(scope_fixture) -> None:
    d = scope_fixture
    assert resolve_effective_inspector_id(None, user=d["usuario"]) is None
    assert resolve_effective_inspector_id(d["ins_a"].id, user=d["usuario"]) == d["ins_a"].id


def test_no_user_raises_401(app) -> None:
    with app.app_context():
        with pytest.raises(InspectorScopeError) as exc:
            resolve_effective_inspector_id(None, user=None)
        assert exc.value.status_code == 401


def test_relevador_without_link_raises_403(app) -> None:
    with app.app_context():
        user = User(
            username=f"bad_{_suffix()}",
            email=f"bad_{_suffix()}@t.local",
            password_hash="x",
            role="relevador",
            is_active=True,
            inspector_id=None,
        )
        db.session.add(user)
        db.session.commit()
        with pytest.raises(InspectorScopeError) as exc:
            resolve_effective_inspector_id(None, user=user)
        assert exc.value.status_code == 403


def test_scope_ruta_items_to_inspector(scope_fixture) -> None:
    d = scope_fixture
    base = RutaItem.query.filter(RutaItem.deleted_at.is_(None))
    ids_a = {r.id for r in scope_ruta_items_to_inspector(base, d["ins_a"].id).all()}
    ids_b = {r.id for r in scope_ruta_items_to_inspector(base, d["ins_b"].id).all()}
    assert d["item_a"].id in ids_a
    assert d["item_b"].id not in ids_a
    assert d["item_b"].id in ids_b
    assert d["item_a"].id not in ids_b


def test_scope_actuaciones_to_inspector(scope_fixture) -> None:
    d = scope_fixture
    base = Actuaciones.query
    ids_a = {r.id for r in scope_actuaciones_to_inspector(base, d["ins_a"].id).all()}
    ids_b = {r.id for r in scope_actuaciones_to_inspector(base, d["ins_b"].id).all()}
    assert d["act_a"].id in ids_a
    assert d["act_b"].id not in ids_a
    assert d["act_b"].id in ids_b
    assert d["act_a"].id not in ids_b


def test_actuaciones_list_route_inspector_cross_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(
        f"/actuaciones?inspector_id={d['ins_b'].id}&desde=2026-01-01&hasta=2026-12-31",
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.get_json()["detail"] == CROSS_INSPECTOR_ACCESS_DETAIL


def test_actuaciones_list_route_inspector_defaults_to_self(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(
        "/actuaciones?desde=2026-06-01&hasta=2026-06-30",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    ids = {item["id"] for item in body["items"]}
    assert d["act_a"].id in ids
    assert d["act_b"].id not in ids


def test_indicadores_route_inspector_cross_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(
        f"/api/indicadores/ejecutivo?desde=2026-06-01&hasta=2026-06-30"
        f"&inspector_id={d['ins_b'].id}",
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.get_json()["detail"] == CROSS_INSPECTOR_ACCESS_DETAIL


def test_resolve_effective_inspector_id_with_jwt_context(app, scope_fixture) -> None:
    d = scope_fixture
    with jwt_request_context(app, d["user_a"].id):
        assert resolve_effective_inspector_id(None) == d["ins_a"].id


def test_list_filters_receive_scoped_inspector_via_adapter(app, scope_fixture) -> None:
    d = scope_fixture
    from app.domains.actuaciones.services.list_inspector_scope import (
        resolve_actuaciones_list_inspector_id,
    )

    with jwt_request_context(app, d["user_a"].id):
        scoped = resolve_actuaciones_list_inspector_id(None)
    filters = ActuacionesListFilters.model_validate(
        {"desde": "2026-06-01", "hasta": "2026-06-30", "inspector_id": scoped}
    )
    assert filters.inspector_id == d["ins_a"].id
