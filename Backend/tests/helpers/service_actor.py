"""
Helpers de auditoría explícita para tests post PREDEPLOY-FIX.2.

NO usar first-active user. Siempre pasar actor_user_id explícito.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from flask import Flask
from flask_jwt_extended import create_access_token, verify_jwt_in_request


@contextmanager
def geocode_job_app_ctx(app: Flask, actor_user_id: int) -> Iterator[Flask]:
    """
    App context + JWT + tabla geocode_post_commit_job aislada (fixtures geo/rel_map).

    Parámetros:
        app: Flask app.
        actor_user_id: id de usuario activo para el JWT.

    Yields:
        Flask app con contexto listo para relevamientos/actuaciones.
    """
    from sqlalchemy import inspect

    from app.database import db
    from app.models import GeocodePostCommitJob

    with jwt_request_context(app, actor_user_id):
        if not inspect(db.engine).has_table("geocode_post_commit_job"):
            GeocodePostCommitJob.__table__.create(bind=db.engine, checkfirst=True)
        GeocodePostCommitJob.query.delete()
        db.session.commit()
        yield app
        db.session.rollback()


@contextmanager
def jwt_request_context(app: Flask, actor_user_id: int) -> Iterator[int]:
    """
    Contexto JWT para tests que invocan services vía resolve_actor_user_id sin param explícito.

    Parámetros:
        app: Flask app.
        actor_user_id: id de usuario activo para el JWT.

    Yields:
        actor_user_id validado.
    """
    with app.app_context():
        token = create_access_token(identity=str(actor_user_id))
        with app.test_request_context(
            "/", headers={"Authorization": f"Bearer {token}"}
        ):
            verify_jwt_in_request()
            yield int(actor_user_id)
