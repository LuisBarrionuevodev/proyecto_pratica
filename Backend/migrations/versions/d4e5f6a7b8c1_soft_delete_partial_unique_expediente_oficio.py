"""expediente/oficio: unicidad numero+año (y causa+año) solo para filas activas (deleted_at IS NULL).

Soft delete deja la fila en BD; el unique global impedía crear otro expediente/oficio con la misma
clave natural. Se reemplaza por columnas generadas STORED + índice único (MySQL 8+).

Revision ID: d4e5f6a7b8c1
Revises: c9d8e7f6a5b4
Create Date: 2026-05-06

"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect, text

revision = "d4e5f6a7b8c1"
down_revision = "c9d8e7f6a5b4"
branch_labels = None
depends_on = None


def _require_mysql(bind) -> None:
    dialect = bind.dialect.name
    if dialect not in ("mysql", "mysqldb", "mariadb"):
        raise RuntimeError(
            "Esta migración usa columnas GENERATED STORED (MySQL/MariaDB). "
            f"Dialecto actual: {dialect}."
        )


def _check_no_duplicate_expedientes_activos(bind) -> None:
    row = bind.execute(
        text(
            """
            SELECT numero_expediente, anio, COUNT(*) AS c
            FROM expediente
            WHERE deleted_at IS NULL
            GROUP BY numero_expediente, anio
            HAVING c > 1
            LIMIT 1
            """
        )
    ).fetchone()
    if row:
        raise RuntimeError(
            "Hay expedientes activos duplicados (mismo numero_expediente + anio). "
            "Corregir datos antes de aplicar la migración."
        )


def _check_no_duplicate_oficios_activos(bind) -> None:
    row = bind.execute(
        text(
            """
            SELECT numero_oficio, anio, COUNT(*) AS c
            FROM oficio
            WHERE deleted_at IS NULL
            GROUP BY numero_oficio, anio
            HAVING c > 1
            LIMIT 1
            """
        )
    ).fetchone()
    if row:
        raise RuntimeError(
            "Hay oficios activos duplicados (mismo numero_oficio + anio). "
            "Corregir datos antes de aplicar la migración."
        )
    row2 = bind.execute(
        text(
            """
            SELECT causa, anio, COUNT(*) AS c
            FROM oficio
            WHERE deleted_at IS NULL AND causa IS NOT NULL AND TRIM(causa) <> ''
            GROUP BY causa, anio
            HAVING c > 1
            LIMIT 1
            """
        )
    ).fetchone()
    if row2:
        raise RuntimeError(
            "Hay oficios activos con causa duplicada para el mismo año. "
            "Corregir datos antes de aplicar la migración."
        )


def upgrade() -> None:
    bind = op.get_bind()
    _require_mysql(bind)
    _check_no_duplicate_expedientes_activos(bind)
    _check_no_duplicate_oficios_activos(bind)

    insp = inspect(bind)
    exp_cols = {c["name"] for c in insp.get_columns("expediente")}
    if "uq_num_anio_activo" not in exp_cols:
        op.drop_constraint("uq_ex_numero_anio", "expediente", type_="unique")
        op.execute(
            text(
                """
                ALTER TABLE expediente
                ADD COLUMN uq_num_anio_activo VARCHAR(191)
                GENERATED ALWAYS AS (
                  CASE
                    WHEN deleted_at IS NULL THEN CONCAT(numero_expediente, '/', anio)
                    ELSE NULL
                  END
                ) STORED
                """
            )
        )
        op.create_index(
            "uq_expediente_num_anio_activo",
            "expediente",
            ["uq_num_anio_activo"],
            unique=True,
        )

    insp = inspect(bind)
    ofi_cols = {c["name"] for c in insp.get_columns("oficio")}
    if "uq_oficio_num_anio_activo" not in ofi_cols:
        op.drop_constraint("uq_of_numero_anio", "oficio", type_="unique")
        op.drop_constraint("uq_of_causa_anio", "oficio", type_="unique")

        op.execute(
            text(
                """
                ALTER TABLE oficio
                ADD COLUMN uq_oficio_num_anio_activo VARCHAR(191)
                GENERATED ALWAYS AS (
                  CASE
                    WHEN deleted_at IS NULL THEN CONCAT(numero_oficio, '/', anio)
                    ELSE NULL
                  END
                ) STORED
                """
            )
        )
        op.execute(
            text(
                """
                ALTER TABLE oficio
                ADD COLUMN uq_oficio_causa_anio_activo VARCHAR(320)
                GENERATED ALWAYS AS (
                  CASE
                    WHEN deleted_at IS NULL AND causa IS NOT NULL AND TRIM(causa) <> ''
                      THEN CONCAT(TRIM(causa), '|', anio)
                    ELSE NULL
                  END
                ) STORED
                """
            )
        )
        op.create_index(
            "uq_oficio_num_anio_activo",
            "oficio",
            ["uq_oficio_num_anio_activo"],
            unique=True,
        )
        op.create_index(
            "uq_oficio_causa_anio_activo",
            "oficio",
            ["uq_oficio_causa_anio_activo"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    _require_mysql(bind)

    insp = inspect(bind)
    ofi_cols = {c["name"] for c in insp.get_columns("oficio")}
    if "uq_oficio_num_anio_activo" in ofi_cols:
        op.drop_index("uq_oficio_causa_anio_activo", table_name="oficio")
        op.drop_index("uq_oficio_num_anio_activo", table_name="oficio")
        op.drop_column("oficio", "uq_oficio_causa_anio_activo")
        op.drop_column("oficio", "uq_oficio_num_anio_activo")
        op.create_unique_constraint("uq_of_numero_anio", "oficio", ["numero_oficio", "anio"])
        op.create_unique_constraint("uq_of_causa_anio", "oficio", ["causa", "anio"])

    insp = inspect(bind)
    exp_cols = {c["name"] for c in insp.get_columns("expediente")}
    if "uq_num_anio_activo" in exp_cols:
        op.drop_index("uq_expediente_num_anio_activo", table_name="expediente")
        op.drop_column("expediente", "uq_num_anio_activo")
        op.create_unique_constraint("uq_ex_numero_anio", "expediente", ["numero_expediente", "anio"])
