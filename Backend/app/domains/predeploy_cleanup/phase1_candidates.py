"""Construcción de candidatos CONFIRMADO_TEST FASE 1 (solo SELECT)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import (
    JUZGADO_TEST_PATTERN,
    JUZGADOS_CANONICOS,
    RELEVAMIENTOS_QA_IDS,
    RUBRO_TEST_PATTERN,
    RUBROS_CANONICOS,
    SQL_TEST_USER_WHERE,
    TEST_ACTUACIONES_SQL,
)


def _ids(conn: Connection, sql: str) -> list[int]:
    return [row[0] for row in conn.execute(text(sql))]


def build_phase1_cleanup_entities(
    conn: Connection,
    protected: dict[str, set[int]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Construye candidatos CONFIRMADO_TEST para manifest congelado.

    Aplica reglas FASE 1 y excluye IDs ya protegidos.
    """
    prot_act = protected.get("actuaciones", set())
    prot_ot = protected.get("orden_trabajo", set())

    actuaciones = [i for i in _ids(conn, TEST_ACTUACIONES_SQL) if i not in prot_act]

    rutas = _ids(
        conn,
        f"""
        SELECT rt.id FROM ruta_trabajo rt
        JOIN users u ON u.id = rt.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )

    ruta_ids = set(rutas)
    ruta_grupo = _ids(
        conn,
        f"SELECT id FROM ruta_grupo WHERE ruta_trabajo_id IN ({_ph(ruta_ids)})" if ruta_ids else "SELECT 0 WHERE 0",
    )
    ruta_grupo_inspector = _ids(
        conn,
        f"""
        SELECT rgi.id FROM ruta_grupo_inspector rgi
        JOIN ruta_grupo rg ON rg.id = rgi.ruta_grupo_id
        WHERE rg.ruta_trabajo_id IN ({_ph(ruta_ids)})
        """
        if ruta_ids
        else "SELECT 0 WHERE 0",
    )
    ruta_item = _ids(
        conn,
        f"SELECT id FROM ruta_item WHERE ruta_trabajo_id IN ({_ph(ruta_ids)})" if ruta_ids else "SELECT 0 WHERE 0",
    )
    ruta_pool = _ids(
        conn,
        f"SELECT id FROM ruta_pool_dia WHERE ruta_trabajo_id IN ({_ph(ruta_ids)})" if ruta_ids else "SELECT 0 WHERE 0",
    )

    denuncias = _ids(
        conn,
        f"""
        SELECT d.id FROM denuncia d
        JOIN users u ON u.id = d.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )

    rel_created_by = _ids(
        conn,
        f"""
        SELECT r.id FROM relevamiento r
        JOIN users u ON u.id = r.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    relevamientos = sorted(set(rel_created_by) | RELEVAMIENTOS_QA_IDS)

    users = _ids(
        conn,
        f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}",
    )

    # OTs test pattern sin actuación protegida/indeterminada fuera del cleanup set
    ot_candidates = _ids(
        conn,
        """
        SELECT ot.id FROM orden_trabajo ot
        WHERE ot.numero_acta REGEXP '^[0-9A-F]{5}[A-F]$'
        """,
    )
    orden_trabajo: list[int] = []
    for ot_id in ot_candidates:
        if ot_id in prot_ot:
            continue
        acts = _ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        if not acts:
            orden_trabajo.append(ot_id)
            continue
        if all(a in set(actuaciones) for a in acts):
            orden_trabajo.append(ot_id)

    # Juzgados test sin oficios
    juzgados_rows = conn.execute(text("SELECT id, codigo, nombre FROM juzgado_catalogo")).fetchall()
    juzgados: list[int] = []
    for row in juzgados_rows:
        codigo = (row.codigo or "").strip()
        nombre = (row.nombre or "").strip()
        if codigo in JUZGADOS_CANONICOS:
            continue
        if not (JUZGADO_TEST_PATTERN.search(codigo) or JUZGADO_TEST_PATTERN.search(nombre)):
            continue
        of_cnt = conn.execute(
            text("SELECT COUNT(*) FROM oficio WHERE juzgado_id = :jid"),
            {"jid": row.id},
        ).scalar()
        if of_cnt == 0:
            juzgados.append(row.id)

    # Rubros test sin referencias (post simulación fase1 simplificada: sin refs actuales)
    rubros_rows = conn.execute(text("SELECT id, nombre FROM rubro")).fetchall()
    rubros: list[int] = []
    rubros_blocked: list[int] = []
    for row in rubros_rows:
        nombre = row.nombre or ""
        if nombre in RUBROS_CANONICOS:
            continue
        if not RUBRO_TEST_PATTERN.search(nombre):
            continue
        refs = conn.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*) FROM domicilio d WHERE d.rubro_id = :rid)
                  + (SELECT COUNT(*) FROM relevamiento r WHERE r.rubro_id = :rid)
                  + (SELECT COUNT(*) FROM ruta_pool_dia rpd WHERE rpd.rubro_id = :rid)
                """
            ),
            {"rid": row.id},
        ).scalar()
        if refs == 0:
            rubros.append(row.id)
        else:
            rubros_blocked.append(row.id)

    relevador_qa = _ids(
        conn,
        "SELECT id FROM relevador WHERE nombre IN ('Otro Relevador QA', 'Inactivo-05601b8d')",
    )

    return {
        "actuaciones": _entries(actuaciones, "CONFIRMADO_TEST", "fixture_uuid_or_ot_pattern"),
        "ruta_trabajo": _entries(rutas, "CONFIRMADO_TEST", "created_by_test_user"),
        "ruta_grupo": _entries(ruta_grupo, "CONFIRMADO_TEST", "child_of_test_ruta"),
        "ruta_grupo_inspector": _entries(ruta_grupo_inspector, "CONFIRMADO_TEST", "child_of_test_ruta"),
        "ruta_item": _entries(ruta_item, "CONFIRMADO_TEST", "child_of_test_ruta"),
        "ruta_pool_dia": _entries(ruta_pool, "CONFIRMADO_TEST", "child_of_test_ruta"),
        "denuncia": _entries(denuncias, "CONFIRMADO_TEST", "created_by_test_user"),
        "relevamiento": _entries(relevamientos, "CONFIRMADO_TEST", "qa_relevador_or_created_by_test"),
        "users": _entries(users, "CONFIRMADO_TEST", "test_email_or_username_pattern"),
        "orden_trabajo": _entries(orden_trabajo, "CONFIRMADO_TEST", "unique_ot_numero_no_protected_acts"),
        "juzgado_catalogo": _entries(juzgados, "CONFIRMADO_TEST", "fixture_pattern_zero_oficios"),
        "rubro": _entries(rubros, "CONFIRMADO_TEST", "fixture_pattern_zero_refs"),
        "relevador": _entries(relevador_qa, "CONFIRMADO_TEST", "qa_relevador_not_canonical"),
        "_meta": {
            "rubro_becomes_deletable_after_phase1": rubros_blocked,
            "iniciador_ruta": "NOT_INCLUDED_PHASE1",
            "domicilio": "PHASE2_ONLY",
            "contribuyente": "PHASE2_ONLY",
            "expediente": "NOT_INCLUDED_PHASE1",
            "oficio": "NOT_INCLUDED_PHASE1",
        },
    }


def _ph(ids: set[int]) -> str:
    return ",".join(str(i) for i in sorted(ids)) if ids else "0"


def _entries(ids: list[int], clasificacion: str, evidencia: str) -> list[dict[str, Any]]:
    return [
        {"id": i, "clasificacion": clasificacion, "evidencia": evidencia}
        for i in sorted(set(ids))
    ]
