"""V1.1-COMP-MOTIVOS.1 — upgrade/downgrade Alembic preserva el texto histórico.

Aislamiento: SQL mínimo + Alembic; restaura HEAD al final.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import bindparam, text

from app import create_app
from app.database import db
from app.security.test_database import assert_connected_database_is_test

PRE_REVISION = "c4d5e6f7a8b9"
TARGET_REVISION = "d5e6f7a8b9c0"
_ANIO = 2099


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
            "JWT_SECRET_KEY": "pytest-jwt-comp-motivos-1-mig-32b",
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


def _acta(prefix: str) -> str:
    return f"{prefix}{uuid4().hex[:4]}"[:6]


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = :name
            LIMIT 1
            """
        ),
        {"name": name},
    ).fetchone()
    return row is not None


def _stmt_in_ids(sql: str):
    return text(sql).bindparams(bindparam("ids", expanding=True))


def _cleanup(conn, ids: list[int]) -> None:
    if not ids:
        return
    if _table_exists(conn, "comprobacion_motivo"):
        conn.execute(
            _stmt_in_ids("DELETE FROM comprobacion_motivo WHERE comprobacion_id IN :ids"),
            {"ids": ids},
        )
    conn.execute(
        _stmt_in_ids("DELETE FROM comprobacion WHERE id IN :ids"),
        {"ids": ids},
    )


def _insert_comp(conn, *, numero: str, motivo: str | None) -> int:
    conn.execute(
        text(
            """
            INSERT INTO comprobacion (numero_acta, anio, mes, motivo)
            VALUES (:numero, :anio, 11, :motivo)
            """
        ),
        {"numero": numero, "anio": _ANIO, "motivo": motivo},
    )
    row = conn.execute(
        text(
            """
            SELECT id FROM comprobacion
            WHERE numero_acta = :numero AND anio = :anio
            """
        ),
        {"numero": numero, "anio": _ANIO},
    ).fetchone()
    assert row is not None
    return int(row[0])


@pytest.fixture()
def schema_pre_motivos_1(migration_app):
    """HEAD → pre-revisión → filas históricas; restaura HEAD al final."""
    app = migration_app
    ids: list[int] = []
    catalog_nombre: str | None = None
    with app.app_context():
        try:
            _alembic_upgrade()
            _alembic_downgrade(PRE_REVISION)
            with db.engine.begin() as conn:
                cat = conn.execute(
                    text(
                        """
                        SELECT nombre FROM catalog_motivo_comprobacion
                        ORDER BY id ASC LIMIT 1
                        """
                    )
                ).fetchone()
                if cat is None:
                    conn.execute(
                        text(
                            """
                            INSERT INTO catalog_motivo_comprobacion (nombre)
                            VALUES ('Incumplimiento')
                            """
                        )
                    )
                    catalog_nombre = "Incumplimiento"
                else:
                    catalog_nombre = str(cat[0])
                ids.append(_insert_comp(conn, numero=_acta("c1"), motivo=catalog_nombre))
                ids.append(_insert_comp(conn, numero=_acta("c2"), motivo=None))
                ids.append(_insert_comp(conn, numero=_acta("c3"), motivo=""))
                ids.append(_insert_comp(conn, numero=_acta("c4"), motivo="PENDIENTE"))
                ids.append(_insert_comp(conn, numero=_acta("c5"), motivo="No catalogo CM1"))
            yield {"app": app, "ids": ids, "catalog_nombre": catalog_nombre}
        finally:
            _release_db_connections()
            try:
                with db.engine.begin() as conn:
                    _cleanup(conn, ids)
            except Exception:
                pass
            _alembic_upgrade()


def test_pre_revision_sin_tabla_comprobacion_motivo(schema_pre_motivos_1) -> None:
    app = schema_pre_motivos_1["app"]
    with app.app_context():
        with db.engine.connect() as conn:
            assert _table_exists(conn, "comprobacion_motivo") is False


def test_upgrade_backfill_exacto_y_preserva_historico(schema_pre_motivos_1) -> None:
    app = schema_pre_motivos_1["app"]
    ids = schema_pre_motivos_1["ids"]
    catalog_nombre = schema_pre_motivos_1["catalog_nombre"]
    id_ok, id_null, id_empty, id_pend, id_unk = ids

    with app.app_context():
        _alembic_upgrade(TARGET_REVISION)
        with db.engine.connect() as conn:
            assert _table_exists(conn, "comprobacion_motivo") is True
            rows = conn.execute(
                _stmt_in_ids(
                    """
                    SELECT comprobacion_id, catalog_motivo_comprobacion_id
                    FROM comprobacion_motivo
                    WHERE comprobacion_id IN :ids
                    """
                ),
                {"ids": ids},
            ).fetchall()
            linked = {int(r[0]) for r in rows}
            assert linked == {id_ok}
            assert len(rows) == 1

            textos = {
                int(r[0]): r[1]
                for r in conn.execute(
                    _stmt_in_ids("SELECT id, motivo FROM comprobacion WHERE id IN :ids"),
                    {"ids": ids},
                ).fetchall()
            }
            assert textos[id_ok] == catalog_nombre
            assert textos[id_null] is None
            assert textos[id_empty] in ("", None)
            assert textos[id_pend] == "PENDIENTE"
            assert textos[id_unk] == "No catalogo CM1"


def test_downgrade_preserva_texto_historico(schema_pre_motivos_1) -> None:
    app = schema_pre_motivos_1["app"]
    ids = schema_pre_motivos_1["ids"]
    catalog_nombre = schema_pre_motivos_1["catalog_nombre"]
    id_ok, id_null, id_empty, id_pend, id_unk = ids

    with app.app_context():
        _alembic_upgrade(TARGET_REVISION)
        _alembic_downgrade(PRE_REVISION)
        with db.engine.connect() as conn:
            assert _table_exists(conn, "comprobacion_motivo") is False
            textos = {
                int(r[0]): r[1]
                for r in conn.execute(
                    _stmt_in_ids("SELECT id, motivo FROM comprobacion WHERE id IN :ids"),
                    {"ids": ids},
                ).fetchall()
            }
            assert textos[id_ok] == catalog_nombre
            assert textos[id_null] is None
            assert textos[id_empty] in ("", None)
            assert textos[id_pend] == "PENDIENTE"
            assert textos[id_unk] == "No catalogo CM1"
