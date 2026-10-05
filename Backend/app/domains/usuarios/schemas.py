from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


RoleType = Literal["admin", "usuario", "relevador", "relevamiento"]


class LoginRequest(BaseModel):
    """Body esperado para login."""

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=255)


class PasswordResetRequest(BaseModel):
    """Body esperado para solicitar código de recuperación."""

    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Body esperado para confirmar código y cambiar contraseña."""

    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=6, max_length=255)
    new_password2: str = Field(min_length=6, max_length=255)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("El código debe tener 6 dígitos.")
        return value

    @model_validator(mode="after")
    def validate_password_match(self) -> "PasswordResetConfirmRequest":
        if self.new_password != self.new_password2:
            raise ValueError("Las contraseñas no coinciden.")
        return self


class AdminUserCreateRequest(BaseModel):
    """Body esperado para crear usuario desde admin."""

    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=255)
    role: RoleType
    inspector_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_inspector_for_role(self) -> "AdminUserCreateRequest":
        if self.role == "relevador" and self.inspector_id is None:
            raise ValueError("El rol Inspector requiere inspector_id.")
        if self.role not in ("relevador",) and self.inspector_id is not None:
            raise ValueError("inspector_id solo aplica al rol Inspector.")
        return self


class AdminUserUpdateRequest(BaseModel):
    """Body esperado para actualización parcial de usuarios (admin)."""

    username: Optional[str] = Field(default=None, min_length=3, max_length=80)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=255)
    role: Optional[RoleType] = None
    is_active: Optional[bool] = None
    inspector_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_has_values(self) -> "AdminUserUpdateRequest":
        if (
            self.username is None
            and self.email is None
            and self.password is None
            and self.role is None
            and self.is_active is None
            and "inspector_id" not in self.model_fields_set
        ):
            raise ValueError("Debe enviar al menos un campo para actualizar.")
        return self


class ProfileUpdateRequest(BaseModel):
    """Body esperado para actualizar perfil del usuario autenticado."""

    nickname: Optional[str] = Field(default=None, max_length=80)
    avatar_key: Optional[str] = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_has_values(self) -> "ProfileUpdateRequest":
        if self.nickname is None and self.avatar_key is None:
            raise ValueError("Debe enviar nickname o avatar_key.")
        return self


class ChangePasswordRequest(BaseModel):
    """Body esperado para cambio de contraseña del perfil autenticado."""

    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=6, max_length=255)
    new_password2: str = Field(min_length=6, max_length=255)

    @model_validator(mode="after")
    def validate_password_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.new_password2:
            raise ValueError("Las contraseñas no coinciden.")
        return self

