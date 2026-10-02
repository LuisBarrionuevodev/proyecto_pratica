from __future__ import annotations

from app.database import db


class User(db.Model):
    """Usuario autenticable del sistema."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("admin", "usuario", "relevador", name="user_role_enum"),
        nullable=False,
        default="usuario",
        server_default="usuario",
    )
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.text("1"),
        index=True,
    )
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    inspector_id = db.Column(
        db.Integer,
        db.ForeignKey("inspector.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )

    profile = db.relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    password_reset_codes = db.relationship(
        "PasswordResetCode",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    inspector = db.relationship(
        "Inspector",
        back_populates="linked_user",
        uselist=False,
    )

    def to_admin_dict(self) -> dict:
        """Serializa el usuario para endpoints de administración."""
        from app.domains.usuarios.services.inspector_link_service import resolve_inspector_nombre

        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "inspector_id": self.inspector_id,
            "inspector_nombre": resolve_inspector_nombre(self),
        }

