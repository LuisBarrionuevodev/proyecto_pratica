"""MEDIA.2D.1 — migración real y0 → z1: backfill upload_origin en ruta_item_archivo.

Aislamiento TEST.1: SQL mínimo + Alembic; sin scope_fixture de inspector.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import text

from app import create_app
from app.database import db
from app.security.test_database import assert_connected_database_is_test

PRE_2D1_REVISION = "y0z1a2b3c4d5"
TARGET_REVISION = "z1a2b3c4d5e6"
_STUB_OBJECT_PREFIX = "pytest/2d1_upload_origin_mig/"


@pytest.fixture(name="scope_fixture")
def _block_inspector_scope_fixture():
    yield None


@pytest.fixture(scope="module")
def migration_app():
    os.environ.setdefault("MEDIA_STORAGE_PROVIDER", "mock")
    os.environ.setdefault("MEDIA_S3_BUCKET", "digitaliza-media-test")
    os.environ["GEO_POST_COMMIT_ASYNC"] = "false"
    flask_app = create_app(
        {
            "TESTING": True,
            "PROPAGATE_EXCEPTIONS": True,
            "JWT_SECRET_KEY": "pytest-jwt-2d1-upload-origin-mig-32",
            "RATELIMIT_ENABLED": False,
        }
    )
    assert_connected_database_is_test(flask_app)
    yield flask_app


def _release_db_connections() -> None:
    db.session.remove()
    db.engine.dispose()


def _alembic_downgrade(revision: str) -> None:
    _release_db_connections()
    downgrade(revision=revision)
    _release_db_connections()


def _alembic_upgrade(revision: str | None = None) -> None:
    _release_db_connections()
    if revision:
        upgrade(revision=revision)
    else:
        upgrade()
    _release_db_connections()


def _pick_upload_user_id(conn) -> int:
    row = conn.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).fetchone()
    if row is not None:
        return int(row[0])
    suffix = uuid4().hex[:10]
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    conn.execute(
        text(
            """
            INSERT INTO users (username, email, password_hash, role, is_active)
            VALUES (:username, :email, 'x', 'usuario', 1)
            """
        ),
        {
            "username": f"pytest_2d1_mig_{suffix}",
            "email": f"2d1mig_{suffix}@pytest.local",
        },
    )
    user_id = int(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar())
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    return user_id


def _insert_ruta_item_stub(conn, *, user_id: int) -> int:
    ruta_item_id = 91_000_000 + (uuid4().int % 8_000_000)
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    conn.execute(
        text(
            """
            INSERT INTO ruta_item (
              id, ruta_trabajo_id, iniciador_ruta_id, created_by_user_id, estado_ruta_item
            ) VALUES (
              :id, :ruta_trabajo_id, :iniciador_ruta_id, :user_id, 'FINALIZADO'
            )
            """
        ),
        {
            "id": ruta_item_id,
            "ruta_trabajo_id": ruta_item_id,
            "iniciador_ruta_id": ruta_item_id + 1,
            "user_id": user_id,
        },
    )
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    return ruta_item_id


def _insert_archivo(conn, *, status: str, user_id: int, suffix: str) -> int:
    conn.execute(
        text(
            """
            INSERT INTO archivo (
              storage_provider, bucket, object_key, original_filename,
              content_type, byte_size, sha256, status, uploaded_by_user_id
            ) VALUES (
              'mock', 'digitaliza-media-test', :object_key, 'foto.jpg',
              'image/jpeg', 100, :sha256, :status, :user_id
            )
            """
        ),
        {
            "object_key": f"{_STUB_OBJECT_PREFIX}{suffix}/{uuid4().hex}",
            "sha256": uuid4().hex,
            "status": status,
            "user_id": user_id,
        },
    )
    return int(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar())


def _insert_link(conn, *, ruta_item_id: int, archivo_id: int) -> int:
    conn.execute(
        text(
            """
            INSERT INTO ruta_item_archivo (ruta_item_id, archivo_id, categoria, tipo_documento)
            VALUES (:ruta_item_id, :archivo_id, 'FOTO_ACTA', 'ACTA_INSPECCION')
            """
        ),
        {"ruta_item_id": ruta_item_id, "archivo_id": archivo_id},
    )
    return int(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar())


def _cleanup(conn, *, ruta_item_id: int) -> None:
    conn.execute(
        text("DELETE FROM ruta_item_archivo WHERE ruta_item_id = :rid"),
        {"rid": ruta_item_id},
    )
    conn.execute(
        text("DELETE FROM archivo WHERE object_key LIKE :prefix"),
        {"prefix": f"{_STUB_OBJECT_PREFIX}%"},
    )
    conn.execute(text("DELETE FROM ruta_item WHERE id = :rid"), {"rid": ruta_item_id})


def _upload_origin_column_meta(conn) -> tuple[bool, str | None, str | None]:
    """Presente, is_nullable (YES/NO), column_default normalizado."""
    row = conn.execute(
        text(
            """
            SELECT is_nullable AS col_nullable, column_default AS col_default
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'ruta_item_archivo'
              AND column_name = 'upload_origin'
            LIMIT 1
            """
        )
    ).fetchone()
    if row is None:
        return False, None, None
    default = row.col_default
    if default is not None:
        default = str(default).strip("'").strip('"')
    return True, str(row.col_nullable), default


def _upload_origin_column_present(conn) -> bool:
    row = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'ruta_item_archivo'
              AND column_name = 'upload_origin'
            LIMIT 1
            """
        )
    ).fetchone()
    return row is not None


@pytest.fixture()
def schema_pre_2d1(migration_app):
    """HEAD → y0 → filas históricas; restaura HEAD al final."""
    app = migration_app
    ruta_item_id: int | None = None
    link_pending_id: int | None = None
    link_ready_id: int | None = None
    with app.app_context():
        _alembic_upgrade()
        _alembic_downgrade(PRE_2D1_REVISION)
        with db.engine.begin() as conn:
            user_id = _pick_upload_user_id(conn)
            ruta_item_id = _insert_ruta_item_stub(conn, user_id=user_id)
            arch_pending = _insert_archivo(conn, status="PENDING", user_id=user_id, suffix="pending")
            arch_ready = _insert_archivo(conn, status="READY", user_id=user_id, suffix="ready")
            link_pending_id = _insert_link(conn, ruta_item_id=ruta_item_id, archivo_id=arch_pending)
            link_ready_id = _insert_link(conn, ruta_item_id=ruta_item_id, archivo_id=arch_ready)
        ctx = {
            "app": app,
            "ruta_item_id": ruta_item_id,
            "link_pending_id": link_pending_id,
            "link_ready_id": link_ready_id,
            "user_id": user_id,
        }
        try:
            yield ctx
        finally:
            _release_db_connections()
            if ruta_item_id is not None:
                try:
                    with db.engine.begin() as conn:
                        _cleanup(conn, ruta_item_id=ruta_item_id)
                except Exception:
                    pass
            _alembic_upgrade()


def test_pre_revision_sin_columna_upload_origin(schema_pre_2d1) -> None:
    app = schema_pre_2d1["app"]
    with app.app_context():
        with db.engine.connect() as conn:
            assert _upload_origin_column_present(conn) is False


def test_upgrade_y0_to_z1_backfills_completar_trabajo(schema_pre_2d1) -> None:
    app = schema_pre_2d1["app"]
    ruta_item_id = schema_pre_2d1["ruta_item_id"]
    link_pending_id = schema_pre_2d1["link_pending_id"]
    link_ready_id = schema_pre_2d1["link_ready_id"]
    user_id = schema_pre_2d1.get("user_id")

    with app.app_context():
        _alembic_upgrade(TARGET_REVISION)

        with db.engine.begin() as conn:
            present, is_nullable, column_default = _upload_origin_column_meta(conn)
            assert present is True
            assert is_nullable == "NO"
            assert column_default is not None
            assert "COMPLETAR_TRABAJO" in column_default.upper()

            rows = conn.execute(
                text(
                    """
                    SELECT ria.id, ria.upload_origin, a.status AS archivo_status
                    FROM ruta_item_archivo ria
                    JOIN archivo a ON a.id = ria.archivo_id
                    WHERE ria.ruta_item_id = :rid
                    ORDER BY ria.id
                    """
                ),
                {"rid": ruta_item_id},
            ).fetchall()
            assert len(rows) == 2
            by_link = {int(r.id): (str(r.upload_origin), str(r.archivo_status)) for r in rows}
            assert by_link[int(link_pending_id)] == ("COMPLETAR_TRABAJO", "PENDING")
            assert by_link[int(link_ready_id)] == ("COMPLETAR_TRABAJO", "READY")

            assert user_id is not None
            arch_default = _insert_archivo(
                conn, status="READY", user_id=int(user_id), suffix="default_origin"
            )
            conn.execute(
                text(
                    """
                    INSERT INTO ruta_item_archivo (ruta_item_id, archivo_id, categoria, tipo_documento)
                    VALUES (:ruta_item_id, :archivo_id, 'FOTO_INSPECCION', NULL)
                    """
                ),
                {"ruta_item_id": ruta_item_id, "archivo_id": arch_default},
            )
            link_default_id = int(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar())
            origin_default = conn.execute(
                text("SELECT upload_origin FROM ruta_item_archivo WHERE id = :id"),
                {"id": link_default_id},
            ).scalar()
            assert str(origin_default) == "COMPLETAR_TRABAJO"

            arch_mis = _insert_archivo(
                conn, status="READY", user_id=int(user_id), suffix="mis_trabajos"
            )
            conn.execute(
                text(
                    """
                    INSERT INTO ruta_item_archivo (
                      ruta_item_id, archivo_id, categoria, tipo_documento, upload_origin
                    ) VALUES (
                      :ruta_item_id, :archivo_id, 'FOTO_DOCUMENTACION_LOCAL', 'HABILITACION', 'MIS_TRABAJOS'
                    )
                    """
                ),
                {"ruta_item_id": ruta_item_id, "archivo_id": arch_mis},
            )
            link_mis_id = int(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar())
            origin_mis = conn.execute(
                text("SELECT upload_origin FROM ruta_item_archivo WHERE id = :id"),
                {"id": link_mis_id},
            ).scalar()
            assert str(origin_mis) == "MIS_TRABAJOS"

        _release_db_connections()
