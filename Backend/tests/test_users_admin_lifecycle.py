"""Ciclo de vida admin de usuarios: listado filtrado, inactivar/reactivar y guards."""

from __future__ import annotations

import random
from unittest.mock import patch

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.usuarios.security.passwords import hash_password
from app.domains.usuarios.services.auth_service import login_user
from app.domains.usuarios.services.users_service import (
    create_user_admin,
    deactivate_user_admin,
    list_users_admin,
    reactivate_user_admin,
)
from app.models.user import User


def _unique_suffix() -> str:
    return f"{random.randint(0, 999999):06d}"


def _admin_headers(app, user_id: int) -> dict[str, str]:
    with app.app_context():
        token = create_access_token(identity=str(user_id), additional_claims={"role": "admin"})
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _create_user(
    *,
    username: str | None = None,
    email: str | None = None,
    role: str = "usuario",
    is_active: bool = True,
    password: str = "secret123",
) -> User:
    suffix = _unique_suffix()
    user = User(
        username=username or f"u1_{suffix}",
        email=email or f"u1_{suffix}@test.local",
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.session.add(user)
    db.session.flush()
    return user


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app({"TESTING": True, "RATELIMIT_ENABLED": False})
    with app.app_context():
        yield app
        db.session.rollback()


def test_create_user_admin_active_by_default(app_ctx) -> None:
    suffix = _unique_suffix()
    user_id = create_user_admin(
        username=f"create_{suffix}",
        email=f"create_{suffix}@test.local",
        password="secret123",
        role="usuario",
    )
    user = User.query.get(user_id)
    assert user is not None
    assert user.is_active is True


def test_list_users_admin_filters(app_ctx) -> None:
    active = _create_user(username=f"act_{_unique_suffix()}", email=f"act_{_unique_suffix()}@test.local")
    inactive = _create_user(
        username=f"ina_{_unique_suffix()}",
        email=f"ina_{_unique_suffix()}@test.local",
        is_active=False,
    )
    db.session.commit()

    active_ids = {u["id"] for u in list_users_admin("activos")}
    inactive_ids = {u["id"] for u in list_users_admin("inactivos")}
    all_ids = {u["id"] for u in list_users_admin("todos")}

    assert active.id in active_ids
    assert inactive.id not in active_ids
    assert inactive.id in inactive_ids
    assert active.id not in inactive_ids
    assert active.id in all_ids
    assert inactive.id in all_ids


def test_deactivate_does_not_delete_row(app_ctx) -> None:
    admin = _create_user(role="admin")
    target = _create_user()
    db.session.commit()

    deactivate_user_admin(target.id, actor_user_id=admin.id)
    still_there = User.query.get(target.id)
    assert still_there is not None
    assert still_there.is_active is False


def test_reactivate_returns_user_to_active_list(app_ctx) -> None:
    admin = _create_user(role="admin")
    target = _create_user(is_active=False)
    db.session.commit()

    reactivate_user_admin(target.id)
    db.session.refresh(target)

    assert target.is_active is True
    active_ids = {u["id"] for u in list_users_admin("activos")}
    assert target.id in active_ids


def test_login_inactive_user_fails_with_clear_message(app_ctx) -> None:
    suffix = _unique_suffix()
    password = "secret123"
    user = _create_user(
        username=f"inactive_{suffix}",
        email=f"inactive_{suffix}@test.local",
        is_active=False,
        password=password,
    )
    db.session.commit()

    with pytest.raises(ValueError, match="Usuario inactivo. Contacte al administrador."):
        login_user(username=user.username, password=password)


def test_cannot_deactivate_self(app_ctx) -> None:
    admin = _create_user(role="admin")
    db.session.commit()

    with pytest.raises(ValueError, match="propio usuario"):
        deactivate_user_admin(admin.id, actor_user_id=admin.id)


def test_cannot_deactivate_last_active_admin(app_ctx) -> None:
    solo_admin = _create_user(role="admin")
    actor = _create_user(role="usuario")
    db.session.commit()

    with patch(
        "app.domains.usuarios.services.users_service._count_other_active_admins",
        return_value=0,
    ):
        with pytest.raises(ValueError, match="último administrador"):
            deactivate_user_admin(solo_admin.id, actor_user_id=actor.id)


def test_get_users_estado_query_params(app_ctx) -> None:
    admin = _create_user(role="admin")
    active = _create_user()
    inactive = _create_user(is_active=False)
    db.session.commit()

    client = app_ctx.test_client()
    headers = _admin_headers(app_ctx, admin.id)

    r_active = client.get("/api/admin/users?estado=activos", headers=headers)
    assert r_active.status_code == 200
    active_ids = {u["id"] for u in r_active.get_json()}
    assert active.id in active_ids
    assert inactive.id not in active_ids

    r_inactive = client.get("/api/admin/users?estado=inactivos", headers=headers)
    assert r_inactive.status_code == 200
    inactive_ids = {u["id"] for u in r_inactive.get_json()}
    assert inactive.id in inactive_ids
    assert active.id not in inactive_ids

    r_all = client.get("/api/admin/users?estado=todos", headers=headers)
    assert r_all.status_code == 200
    all_ids = {u["id"] for u in r_all.get_json()}
    assert active.id in all_ids
    assert inactive.id in all_ids


def test_patch_inactivar_and_reactivar_routes(app_ctx) -> None:
    admin = _create_user(role="admin")
    target = _create_user()
    db.session.commit()

    client = app_ctx.test_client()
    headers = _admin_headers(app_ctx, admin.id)

    r_off = client.patch(f"/api/admin/users/{target.id}/inactivar", headers=headers)
    assert r_off.status_code == 200
    db.session.refresh(target)
    assert target.is_active is False

    r_on = client.patch(f"/api/admin/users/{target.id}/reactivar", headers=headers)
    assert r_on.status_code == 200
    db.session.refresh(target)
    assert target.is_active is True


def test_delete_legacy_delegates_to_inactivate(app_ctx) -> None:
    admin = _create_user(role="admin")
    target = _create_user()
    db.session.commit()

    client = app_ctx.test_client()
    headers = _admin_headers(app_ctx, admin.id)

    r = client.delete(f"/api/admin/users/{target.id}", headers=headers)
    assert r.status_code == 200
    db.session.refresh(target)
    assert target.is_active is False
    assert User.query.get(target.id) is not None


def test_inactivar_self_returns_409(app_ctx) -> None:
    admin = _create_user(role="admin")
    db.session.commit()

    client = app_ctx.test_client()
    headers = _admin_headers(app_ctx, admin.id)
    r = client.patch(f"/api/admin/users/{admin.id}/inactivar", headers=headers)
    assert r.status_code == 409
    assert "propio usuario" in (r.get_json() or {}).get("detail", "")


def test_inactivar_idempotent_when_already_inactive(app_ctx) -> None:
    admin = _create_user(role="admin")
    target = _create_user(is_active=False)
    db.session.commit()

    client = app_ctx.test_client()
    headers = _admin_headers(app_ctx, admin.id)
    r = client.patch(f"/api/admin/users/{target.id}/inactivar", headers=headers)
    assert r.status_code == 200
    db.session.refresh(target)
    assert target.is_active is False
