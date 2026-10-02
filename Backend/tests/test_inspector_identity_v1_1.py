"""V1.1-INSPECTOR.1 — vínculo cuenta Inspector y helpers de identidad."""

from __future__ import annotations

import random
from unittest.mock import patch

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import inspect

from app.database import db
from app.domains.usuarios.security.inspector_identity import (
    InspectorIdentityError,
    get_current_inspector_id,
)
from app.domains.usuarios.security.passwords import hash_password
from app.domains.usuarios.services.auth_service import login_user
from app.domains.usuarios.services.users_service import create_user_admin, update_user_admin
from app.models import Inspector, Turno, User


def _suffix() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_turno() -> Turno:
    t = Turno.query.first()
    if t:
        return t
    from app.models.turno import TipoTurno

    t = Turno(turno=TipoTurno.MANIANA)
    db.session.add(t)
    db.session.flush()
    return t


def _mk_inspector() -> Inspector:
    turno = _mk_turno()
    ins = Inspector(nombre=f"Insp {_suffix()}", legajo=_suffix()[:5], turno_id=turno.id)
    db.session.add(ins)
    db.session.flush()
    return ins


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app({"TESTING": True, "RATELIMIT_ENABLED": False})
    with app.app_context():
        yield app
        db.session.rollback()


def test_users_inspector_id_unique_index(app_ctx) -> None:
    insp = inspect(db.engine)
    cols = {c["name"]: c for c in insp.get_columns("users")}
    assert "inspector_id" in cols
    uniques = {u["name"] for u in insp.get_unique_constraints("users")}
    assert "uq_users_inspector_id" in uniques or any(
        "inspector_id" in (u.get("column_names") or []) for u in insp.get_unique_constraints("users")
    )


def test_create_inspector_role_requires_inspector_id(app_ctx) -> None:
    with pytest.raises(ValueError, match="inspector activo"):
        create_user_admin(
            username=f"insp_{_suffix()}",
            email=f"insp_{_suffix()}@test.local",
            password="secret123",
            role="relevador",
            inspector_id=None,
        )


def test_create_inspector_with_valid_link(app_ctx) -> None:
    ins = _mk_inspector()
    db.session.commit()
    uid = create_user_admin(
        username=f"insp_{_suffix()}",
        email=f"insp_{_suffix()}@test.local",
        password="secret123",
        role="relevador",
        inspector_id=ins.id,
    )
    user = User.query.get(uid)
    assert user is not None
    assert user.inspector_id == ins.id


def test_duplicate_inspector_link_rejected(app_ctx) -> None:
    ins = _mk_inspector()
    db.session.commit()
    create_user_admin(
        username=f"a_{_suffix()}",
        email=f"a_{_suffix()}@test.local",
        password="secret123",
        role="relevador",
        inspector_id=ins.id,
    )
    with pytest.raises(ValueError, match="vinculado"):
        create_user_admin(
            username=f"b_{_suffix()}",
            email=f"b_{_suffix()}@test.local",
            password="secret123",
            role="relevador",
            inspector_id=ins.id,
        )


def test_admin_without_inspector_link_ok(app_ctx) -> None:
    uid = create_user_admin(
        username=f"adm_{_suffix()}",
        email=f"adm_{_suffix()}@test.local",
        password="secret123",
        role="admin",
        inspector_id=None,
    )
    user = User.query.get(uid)
    assert user.inspector_id is None


def test_role_change_clears_inspector_link(app_ctx) -> None:
    ins = _mk_inspector()
    db.session.commit()
    uid = create_user_admin(
        username=f"r_{_suffix()}",
        email=f"r_{_suffix()}@test.local",
        password="secret123",
        role="relevador",
        inspector_id=ins.id,
    )
    update_user_admin(uid, role="usuario", inspector_id_provided=False)
    user = User.query.get(uid)
    assert user.role == "usuario"
    assert user.inspector_id is None


def test_get_current_inspector_id_linked(app_ctx) -> None:
    ins = _mk_inspector()
    user = User(
        username=f"jwt_{_suffix()}",
        email=f"jwt_{_suffix()}@test.local",
        password_hash=hash_password("x"),
        role="relevador",
        is_active=True,
        inspector_id=ins.id,
    )
    db.session.add(user)
    db.session.commit()

    with patch(
        "app.domains.usuarios.security.inspector_identity.resolve_user_from_identity",
        return_value=user,
    ):
        assert get_current_inspector_id() == ins.id


def test_get_current_inspector_id_rejects_wrong_role(app_ctx) -> None:
    user = User(
        username=f"u_{_suffix()}",
        email=f"u_{_suffix()}@test.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    with patch(
        "app.domains.usuarios.security.inspector_identity.resolve_user_from_identity",
        return_value=user,
    ):
        with pytest.raises(InspectorIdentityError) as exc:
            get_current_inspector_id()
        assert exc.value.status_code == 403


def test_login_payload_include_inspector(app_ctx) -> None:
    ins = _mk_inspector()
    password = "secret123"
    user = User(
        username=f"login_{_suffix()}",
        email=f"login_{_suffix()}@test.local",
        password_hash=hash_password(password),
        role="relevador",
        is_active=True,
        inspector_id=ins.id,
    )
    db.session.add(user)
    db.session.commit()

    payload = login_user(username=user.username, password=password)
    assert payload["user"]["inspector_id"] == ins.id
    assert payload["user"]["inspector_nombre"] == ins.nombre


def test_list_users_admin_includes_inspector_fields(app_ctx) -> None:
    from app.domains.usuarios.services.users_service import list_users_admin

    ins = _mk_inspector()
    db.session.commit()
    uid = create_user_admin(
        username=f"lst_{_suffix()}",
        email=f"lst_{_suffix()}@test.local",
        password="secret123",
        role="relevador",
        inspector_id=ins.id,
    )
    rows = list_users_admin("activos")
    row = next(r for r in rows if r["id"] == uid)
    assert row["inspector_id"] == ins.id
    assert row["inspector_nombre"] == ins.nombre
