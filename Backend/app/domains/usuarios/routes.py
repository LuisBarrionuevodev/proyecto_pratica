from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from app.domains.usuarios.schemas import (
    AdminUserCreateRequest,
    AdminUserUpdateRequest,
    ChangePasswordRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    ProfileUpdateRequest,
)
from app.domains.usuarios.security.decorators import require_role
from app.domains.usuarios.services.auth_service import login_user
from app.domains.usuarios.services.password_reset_service import (
    confirm_password_reset,
    request_password_reset,
)
from app.domains.usuarios.services.profile_service import (
    change_my_password,
    get_my_profile,
    update_my_profile,
)
from app.domains.usuarios.services.users_service import (
    create_user_admin,
    deactivate_user_admin,
    list_users_admin,
    update_user_admin,
)
from app.shared.errors import pydantic_errors_to_cell_map

usuarios_api = Blueprint("usuarios_api", __name__)


@usuarios_api.post("/api/auth/login")
def auth_login():
    """
    Login con username + password.

    Body:
        {"username": str, "password": str}
    """
    data = request.get_json(silent=True) or {}
    try:
        body = LoginRequest.model_validate(data)
        payload = login_user(username=body.username, password=body.password)
        return jsonify(payload), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400


@usuarios_api.post("/api/auth/password-reset/request")
def auth_password_reset_request():
    """
    Solicita envío de código de recuperación.

    Siempre responde OK para no filtrar existencia de email.
    """
    data = request.get_json(silent=True) or {}
    try:
        body = PasswordResetRequest.model_validate(data)
        payload = request_password_reset(body.email)
        return jsonify(payload), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422


@usuarios_api.post("/api/auth/password-reset/confirm")
def auth_password_reset_confirm():
    """
    Confirma código de recuperación y define nueva contraseña.
    """
    data = request.get_json(silent=True) or {}
    try:
        body = PasswordResetConfirmRequest.model_validate(data)
        confirm_password_reset(
            email=body.email,
            code=body.code,
            new_password=body.new_password,
        )
        return jsonify({"ok": True}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400


@usuarios_api.get("/api/profile/me")
@jwt_required()
def profile_me_get():
    """
    Obtiene datos del usuario autenticado y su perfil.
    """
    try:
        payload = get_my_profile()
        return jsonify(payload), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 401


@usuarios_api.patch("/api/profile/me")
@jwt_required()
def profile_me_patch():
    """
    Actualiza nickname/avatar_key del perfil autenticado.
    """
    data = request.get_json(silent=True) or {}
    try:
        body = ProfileUpdateRequest.model_validate(data)
        profile = update_my_profile(nickname=body.nickname, avatar_key=body.avatar_key)
        return jsonify({"ok": True, "profile": profile}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400


@usuarios_api.post("/api/profile/change-password")
@jwt_required()
def profile_change_password():
    """
    Cambia contraseña del usuario autenticado.
    """
    data = request.get_json(silent=True) or {}
    try:
        body = ChangePasswordRequest.model_validate(data)
        change_my_password(
            current_password=body.current_password,
            new_password=body.new_password,
        )
        return jsonify({"ok": True}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400


@usuarios_api.get("/api/admin/users")
@require_role("admin")
def admin_users_list():
    """
    Lista usuarios para panel de administración.
    """
    return jsonify(list_users_admin()), 200


@usuarios_api.post("/api/admin/users")
@require_role("admin")
def admin_users_create():
    """
    Crea un usuario desde administración.
    """
    data = request.get_json(silent=True) or {}
    try:
        body = AdminUserCreateRequest.model_validate(data)
        new_id = create_user_admin(
            username=body.username,
            email=body.email,
            password=body.password,
            role=body.role,
        )
        return jsonify({"ok": True, "id": new_id}), 201
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 409


@usuarios_api.put("/api/admin/users/<int:user_id>")
@require_role("admin")
def admin_users_update(user_id: int):
    """
    Actualiza datos de un usuario desde administración.
    """
    data = request.get_json(silent=True) or {}
    try:
        body = AdminUserUpdateRequest.model_validate(data)
        update_user_admin(
            user_id,
            username=body.username,
            email=body.email,
            password=body.password,
            role=body.role,
            is_active=body.is_active,
        )
        return jsonify({"ok": True}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        message = str(e)
        status = 404 if "no encontrado" in message.lower() else 409
        return jsonify({"detail": message}), status


@usuarios_api.delete("/api/admin/users/<int:user_id>")
@require_role("admin")
def admin_users_delete(user_id: int):
    """
    Desactiva (soft delete) un usuario.
    """
    try:
        deactivate_user_admin(user_id)
        return jsonify({"ok": True}), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 404

