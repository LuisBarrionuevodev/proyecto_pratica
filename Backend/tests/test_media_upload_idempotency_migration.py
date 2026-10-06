"""V1.1-MEDIA.2A-MIG — upgrade w3x4y5z6a7b8 deduplica ruta_item_archivo antes del índice único."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text

from app import create_app
from app.database import db
from app.security.test_database import assert_connected_database_is_test
from tests.test_inspector_scope_v1_1_2 import _mk_iniciador, _mk_ruta_items_for_inspectors, _mk_inspector, _mk_admin_user

PREV_REVISION = "v2w3x4y5z6a7"
TARGET_REVISION = "w3x4y5z6a7b8"
DUP_SHA = "a" * 64


@pytest.fixture()
def migration_app():
    os.environ.setdefault("MEDIA_STORAGE_PROVIDER", "mock")
    os.environ.setdefault("MEDIA_S3_BUCKET", "digitaliza-media-test")
    os.environ["GEO_POST_COMMIT_ASYNC"] = "false"
    flask_app = create_app(
        {
            "TESTING": True,
            "PROPAGATE_EXCEPTIONS": True,
            "JWT_SECRET_KEY": "pytest-jwt-migration-sha-dedup-32b",
            "RATELIMIT_ENABLED": False,
        }
    )
    assert_connected_database_is_test(flask_app)
    yield flask_app


@pytest.fixture()
def schema_at_prev_revision(migration_app):
    """Deja la DB en la revisión anterior a content_sha256 y restaura HEAD al final."""
    with migration_app.app_context():
        downgrade(revision=PREV_REVISION)
        yield migration_app
        upgrade()


def _insert_archivo(
    conn,
    *,
    status: str,
    sha256: str,
    user_id: int,
    object_key_suffix: str,
) -> int:
    conn.execute(
        text(
            """
            INSERT INTO archivo (
              storage_provider, bucket, object_key, original_filename,
              content_type, byte_size, sha256, status, uploaded_by_user_id
            ) VALUES (
              'mock', 'digitaliza-media-test', :object_key, 'dup.pdf',
              'application/pdf', 100, :sha256, :status, :user_id
            )
            """
        ),
        {
            "object_key": f"pytest/dedup/{object_key_suffix}/{uuid4().hex}",
            "sha256": sha256,
            "status": status,
            "user_id": user_id,
        },
    )
    return int(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar())


def _insert_link(conn, *, ruta_item_id: int, archivo_id: int, categoria: str = "FOTO_ACTA") -> int:
    conn.execute(
        text(
            """
            INSERT INTO ruta_item_archivo (ruta_item_id, archivo_id, categoria, tipo_documento)
            VALUES (:ruta_item_id, :archivo_id, :categoria, 'ACTA_INSPECCION')
            """
        ),
        {
            "ruta_item_id": ruta_item_id,
            "archivo_id": archivo_id,
            "categoria": categoria,
        },
    )
    return int(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar())


def _seed_ruta_item_id() -> tuple[int, int]:
    admin = _mk_admin_user()
    ins_a, ins_b = _mk_inspector(), _mk_inspector()
    ini_a = _mk_iniciador(admin.id)
    ini_b = _mk_iniciador(admin.id)
    item_a, _ = _mk_ruta_items_for_inspectors(admin.id, ins_a, ins_b, ini_a, ini_b)
    db.session.commit()
    return int(item_a.id), int(admin.id)


def _unique_index_present(conn) -> bool:
    rows = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = 'ruta_item_archivo'
              AND index_name = 'uq_ruta_item_archivo_item_cat_sha'
              AND non_unique = 0
            LIMIT 1
            """
        )
    ).fetchone()
    return rows is not None


def test_upgrade_dedup_keeps_ready_relation(schema_at_prev_revision) -> None:
    app = schema_at_prev_revision
    with app.app_context():
        ruta_item_id, user_id = _seed_ruta_item_id()
        engine = db.engine
        with engine.begin() as conn:
            pending_archivo_id = _insert_archivo(
                conn,
                status="PENDING",
                sha256=DUP_SHA,
                user_id=user_id,
                object_key_suffix="pending",
            )
            ready_archivo_id = _insert_archivo(
                conn,
                status="READY",
                sha256=DUP_SHA,
                user_id=user_id,
                object_key_suffix="ready",
            )
            link_pending_id = _insert_link(
                conn, ruta_item_id=ruta_item_id, archivo_id=pending_archivo_id
            )
            link_ready_id = _insert_link(
                conn, ruta_item_id=ruta_item_id, archivo_id=ready_archivo_id
            )

        upgrade(revision=TARGET_REVISION)

        with engine.connect() as conn:
            assert _unique_index_present(conn)
            links = conn.execute(
                text(
                    """
                    SELECT id, archivo_id
                    FROM ruta_item_archivo
                    WHERE ruta_item_id = :rid AND categoria = 'FOTO_ACTA' AND content_sha256 = :sha
                    """
                ),
                {"rid": ruta_item_id, "sha": DUP_SHA},
            ).fetchall()
            assert len(links) == 1
            assert int(links[0].archivo_id) == ready_archivo_id
            assert int(links[0].id) == link_ready_id
            assert int(links[0].id) != link_pending_id

            archivos = conn.execute(
                text("SELECT id FROM archivo WHERE id IN (:a, :b)"),
                {"a": pending_archivo_id, "b": ready_archivo_id},
            ).fetchall()
            assert len(archivos) == 2


def test_upgrade_dedup_tie_without_ready_keeps_min_link_id(schema_at_prev_revision) -> None:
    app = schema_at_prev_revision
    with app.app_context():
        ruta_item_id, user_id = _seed_ruta_item_id()
        engine = db.engine
        with engine.begin() as conn:
            arch_lo = _insert_archivo(
                conn,
                status="PENDING",
                sha256=DUP_SHA,
                user_id=user_id,
                object_key_suffix="lo",
            )
            arch_hi = _insert_archivo(
                conn,
                status="PENDING",
                sha256=DUP_SHA,
                user_id=user_id,
                object_key_suffix="hi",
            )
            link_lo = _insert_link(conn, ruta_item_id=ruta_item_id, archivo_id=arch_lo)
            link_hi = _insert_link(conn, ruta_item_id=ruta_item_id, archivo_id=arch_hi)
            assert link_lo < link_hi

        upgrade(revision=TARGET_REVISION)

        with engine.connect() as conn:
            links = conn.execute(
                text(
                    """
                    SELECT id, archivo_id
                    FROM ruta_item_archivo
                    WHERE ruta_item_id = :rid AND categoria = 'FOTO_ACTA' AND content_sha256 = :sha
                    """
                ),
                {"rid": ruta_item_id, "sha": DUP_SHA},
            ).fetchall()
            assert len(links) == 1
            assert int(links[0].id) == link_lo
            assert int(links[0].archivo_id) == arch_lo

            archivos = conn.execute(
                text("SELECT id FROM archivo WHERE id IN (:a, :b)"),
                {"a": arch_lo, "b": arch_hi},
            ).fetchall()
            assert len(archivos) == 2
