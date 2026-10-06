"""V1.1-MEDIA.2A-MIG — upgrade w3x4y5z6a7b8 deduplica ruta_item_archivo antes del índice único.



Aislamiento TEST.1: sin scope_fixture, usuarios ORM ni servicios de negocio; solo SQL mínimo + Alembic.

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



TARGET_REVISION = "w3x4y5z6a7b8"

PRE_W3_REVISION = "v2w3x4y5z6a7"

DUP_SHA = "a" * 64

_STUB_USER_PREFIX = "pytest_w3_migration_"





@pytest.fixture(name="scope_fixture")

def _block_inspector_scope_fixture():

    """Evita que otro import/active fixture de inspector/usuarios se use en este módulo."""

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

            "JWT_SECRET_KEY": "pytest-jwt-migration-sha-dedup-32b",

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

    """FK archivo.uploaded_by_user_id: reutiliza un id existente o inserta stub SQL mínimo."""

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

            "username": f"{_STUB_USER_PREFIX}{suffix}",

            "email": f"w3mig_{suffix}@pytest.local",

        },

    )

    user_id = int(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar())

    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    return user_id





def _insert_ruta_item_stub(conn, *, user_id: int) -> int:

    """Solo para dedup w3: ruta_item mínimo sin grafo operativo (FK relajadas)."""

    ruta_item_id = 90_000_000 + (uuid4().int % 9_000_000)
    ruta_trabajo_id = ruta_item_id
    iniciador_ruta_id = ruta_item_id + 1

    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

    conn.execute(

        text(

            """

            INSERT INTO ruta_item (

              id, ruta_trabajo_id, iniciador_ruta_id, created_by_user_id, estado_ruta_item

            ) VALUES (

              :id, :ruta_trabajo_id, :iniciador_ruta_id, :user_id, 'ASIGNADO'

            )

            """

        ),

        {
            "id": ruta_item_id,
            "ruta_trabajo_id": ruta_trabajo_id,
            "iniciador_ruta_id": iniciador_ruta_id,
            "user_id": user_id,
        },

    )

    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    return ruta_item_id





def _cleanup_migration_rows(conn, *, ruta_item_id: int) -> None:

    conn.execute(

        text("DELETE FROM ruta_item_archivo WHERE ruta_item_id = :rid"),

        {"rid": ruta_item_id},

    )

    conn.execute(text("DELETE FROM archivo WHERE object_key LIKE 'pytest/dedup/%'"))

    conn.execute(text("DELETE FROM ruta_item WHERE id = :rid"), {"rid": ruta_item_id})





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





@pytest.fixture()

def w3_dedup_schema(migration_app):

    """

    HEAD → v2 → datos mínimos → test; siempre restaura HEAD en finally.

    """

    app = migration_app

    ruta_item_id: int | None = None

    with app.app_context():

        _alembic_upgrade()

        _alembic_downgrade(PRE_W3_REVISION)

        with db.engine.begin() as conn:

            user_id = _pick_upload_user_id(conn)

            ruta_item_id = _insert_ruta_item_stub(conn, user_id=user_id)

        ctx = {"app": app, "ruta_item_id": ruta_item_id, "user_id": user_id}

        try:

            yield ctx

        finally:

            _release_db_connections()

            if ruta_item_id is not None:

                try:

                    with db.engine.begin() as conn:

                        _cleanup_migration_rows(conn, ruta_item_id=ruta_item_id)

                except Exception:

                    pass

            _alembic_upgrade()





def test_upgrade_dedup_keeps_ready_relation(w3_dedup_schema) -> None:

    app = w3_dedup_schema["app"]

    ruta_item_id = w3_dedup_schema["ruta_item_id"]

    user_id = w3_dedup_schema["user_id"]

    with app.app_context():

        with db.engine.begin() as conn:

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



        _alembic_upgrade(TARGET_REVISION)



        with db.engine.connect() as conn:

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

        _release_db_connections()





def test_upgrade_dedup_tie_without_ready_keeps_min_link_id(w3_dedup_schema) -> None:

    app = w3_dedup_schema["app"]

    ruta_item_id = w3_dedup_schema["ruta_item_id"]

    user_id = w3_dedup_schema["user_id"]

    with app.app_context():

        with db.engine.begin() as conn:

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



        _alembic_upgrade(TARGET_REVISION)



        with db.engine.connect() as conn:

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

        _release_db_connections()
