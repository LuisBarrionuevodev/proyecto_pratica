from __future__ import annotations

from app.database import db


class Profile(db.Model):
    """Perfil público editable asociado 1:1 a User."""

    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    nickname = db.Column(db.String(80), nullable=True)
    avatar_key = db.Column(
        db.String(50),
        nullable=False,
        default="avatar1",
        server_default="avatar1",
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

    user = db.relationship("User", back_populates="profile")

    def to_dict(self) -> dict:
        """Serializa perfil para respuestas API."""
        return {
            "nickname": self.nickname,
            "avatar_key": self.avatar_key,
        }

