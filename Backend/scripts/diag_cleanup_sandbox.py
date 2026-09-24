#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.2-DIAG — diagnóstico READ ONLY contra digitaliza_sandbox.
Solo SELECT. No DELETE/UPDATE/TRUNCATE.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"

RUBROS_CANONICOS = frozenset(
    {
        "Comestibles", "Carnicería", "Drugstore", "Kiosco", "Supermercado",
        "Pollería", "Pescadería", "Bar", "Cervecería", "Rotisería", "Cafetería",
        "Verdulería", "Panadería", "Venta de Comidas", "Frutas", "Heladería",
        "Sanguchería", "Restaurante", "Distribuidora", "Panchería", "Pan", "Pollo",
        "Fiambrería", "Confitería", "Dietética", "Elaboración de empanadas",
        "Comedor", "Licorería", "Minimercado",
    }
)
RELEVADORES_CANONICOS = frozenset(
    {
        "Fabian Esquivel", "Oscar Medina", "Juan Saravia", "Biscardi Roberto",
        "Molina Antonio", "Guillermo Gonzalez", "Sergio Castillo", "Cecilia Carrizo",
        "Gutierrez Alvaro", "Walter Peralta",
    }
)
JUZGADOS_CANONICOS = frozenset({f"JF{n}" for n in range(1, 16)})

RUBRO_TEST_PATTERN = re.compile(
    r"(?:"
    r"Pr\d+Rub-|RubStab|Rub10B1_|^RubA_|^RubB_|^rubro-\d+|UniqRub|RubroEO_|RubPool|"
    r"Notif\d+-|Comp\d+-|CarnPr\d+-|VerdPr\d+-|CafePr\d+-|RotiPr\d+-|"
    r"PollNum\d+-|PanPr\d+-|Carn\d+c[A-Z]?-|Notif\d+c-|Comp\d+c-|"
    r"^Rubro \d"
    r")",
    re.IGNORECASE,
)
JUZGADO_TEST_PATTERN = re.compile(
    r"(^JZRB|^JZSO|^JZED|^j_|doc test|Juzgado doc|Jz Rein|Jz Solo|Juz \d|JZCF|^JZ[0-9A-F]{4}$)",
    re.IGNORECASE,
)
USER_TEST_EMAIL = re.compile(r"@t\.local$", re.IGNORECASE)
USER_TEST_USERNAME = re.compile(
    r"^(op_ruta3_|rlist_|edn_|op_ruta4_|op6f_|op6i_|op6j_|op7d_|op1b_|"
    r"pr111_|pr11f_|crudmapa_|stab7_|fix7_|fix10a_|qa_|hotfix_|reenc_|"
    r"relhot_|outd_|rec_of_|rec_|prod_|nr_|ind_|cnt_|ed4b_|rein_b_|reenc_of_|"
    r"id10c_|st4_|hist_|cp_)",
    re.IGNORECASE,
)
OT_TEST_PATTERN = re.compile(r"^[0-9A-F]{5}[A-F]$", re.IGNORECASE)

SQL_TEST_USER_WHERE = """
    (
        email LIKE '%@t.local'
        OR username REGEXP '^(op_ruta3_|rlist_|edn_|op_ruta4_|op6f_|op6i_|op6j_|op7d_|op1b_|pr111_|pr11f_|crudmapa_|stab7_|fix7_|fix10a_|qa_|hotfix_|reenc_|relhot_|outd_|rec_of_|rec_|prod_|nr_|ind_|cnt_|ed4b_|rein_b_|reenc_of_|id10c_|st4_|hist_|cp_)'
    )
    AND NOT (LOWER(username) = 'admin' OR LOWER(email) = 'admin@local')
"""

CREATED_BY_TABLES = [
    "denuncia",
    "relevamiento",
    "iniciador_ruta",
    "ruta_trabajo",
    "ruta_grupo",
    "ruta_grupo_inspector",
    "ruta_item",
    "establecimiento_operativo",
]

BASELINE_TABLES = [
    "users", "rubro", "juzgado_catalogo", "relevador", "inspector",
    "domicilio", "domicilio_geocode", "relevamiento", "denuncia", "actuaciones",
    "inspeccion", "notificacion", "comprobacion", "clausura", "decomiso",
    "iniciador_ruta", "ruta_trabajo", "ruta_grupo", "ruta_item", "ruta_pool_dia",
    "orden_trabajo", "expediente", "oficio",
]


def db_uri() -> str:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")
    return uri


def fetch_all(conn, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params or {})
    return [dict(row._mapping) for row in result]


def fetch_scalar(conn, sql: str, params: dict | None = None) -> Any:
    row = conn.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


def classify_user(row: dict) -> str:
    email = (row.get("email") or "").strip()
    username = (row.get("username") or "").strip()
    if username.lower() == "admin" or email.lower() == "admin@local":
        return "REAL"
    if USER_TEST_EMAIL.search(email) or USER_TEST_USERNAME.match(username):
        return "CONFIRMADO_TEST"
    if email.endswith("@example.com") or "test" in username.lower():
        return "PROBABLE_TEST"
    return "INDETERMINADO"


def main() -> None:
    uri = db_uri()
    db_name = unquote(uri.rsplit("/", 1)[-1].split("?", 1)[0])
    engine = create_engine(uri)
    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "database": db_name,
        "mode": "READ_ONLY_SELECT",
        "writes_executed": False,
    }

    with engine.connect() as conn:
        report["database_confirmed"] = fetch_scalar(conn, "SELECT DATABASE()")
        report["alembic_version"] = fetch_scalar(
            conn, "SELECT version_num FROM alembic_version LIMIT 1"
        )

        # 1. Baseline counts
        baseline = {}
        for tbl in BASELINE_TABLES:
            try:
                baseline[tbl] = fetch_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}`")
            except Exception as e:
                baseline[tbl] = f"ERROR: {e}"
        report["baseline_counts"] = baseline

        # 3. Users audit
        users = fetch_all(
            conn,
            "SELECT id, username, email, created_at FROM users ORDER BY id",
        )
        user_class: dict[int, str] = {}
        for u in users:
            user_class[u["id"]] = classify_user(u)

        confirmed_test_user_ids = [
            u["id"] for u in users if user_class[u["id"]] == "CONFIRMADO_TEST"
        ]
        probable_test_user_ids = [
            u["id"] for u in users if user_class[u["id"]] == "PROBABLE_TEST"
        ]

        user_deps: list[dict] = []
        for u in users:
            if user_class[u["id"]] not in ("CONFIRMADO_TEST", "PROBABLE_TEST"):
                continue
            deps = {}
            for tbl in CREATED_BY_TABLES:
                try:
                    cnt = fetch_scalar(
                        conn,
                        f"SELECT COUNT(*) FROM `{tbl}` WHERE created_by_user_id = :uid",
                        {"uid": u["id"]},
                    )
                    if cnt:
                        deps[tbl] = cnt
                except Exception:
                    pass
            user_deps.append(
                {
                    "id": u["id"],
                    "username": u["username"],
                    "email": u["email"],
                    "created_at": str(u.get("created_at")),
                    "clasificacion": user_class[u["id"]],
                    "dependencias_created_by": deps,
                }
            )

        report["usuarios"] = {
            "total": len(users),
            "confirmado_test": len(confirmed_test_user_ids),
            "probable_test": len(probable_test_user_ids),
            "real_admin": sum(
                1 for u in users if user_class[u["id"]] == "REAL"
            ),
            "indeterminado": sum(
                1 for u in users if user_class[u["id"]] == "INDETERMINADO"
            ),
            "detalle": user_deps[:200],
            "detalle_truncated": len(user_deps) > 200,
        }

        # 4. created_by aggregate for confirmed test users
        created_by_agg = []
        for tbl in CREATED_BY_TABLES:
            rows = fetch_all(
                conn,
                f"""
                SELECT t.created_by_user_id AS user_id, COUNT(*) AS cnt
                FROM `{tbl}` t
                JOIN users u ON u.id = t.created_by_user_id
                WHERE {SQL_TEST_USER_WHERE}
                GROUP BY t.created_by_user_id
                ORDER BY cnt DESC
                LIMIT 50
                """,
            )
            total = fetch_scalar(
                conn,
                f"""
                SELECT COUNT(*) FROM `{tbl}` t
                JOIN users u ON u.id = t.created_by_user_id
                WHERE {SQL_TEST_USER_WHERE}
                """,
            )
            created_by_agg.append({"entidad": tbl, "total_filas": total, "top_usuarios": rows})
        report["trazabilidad_created_by_test"] = created_by_agg

        # 14. Rubros
        rubros = fetch_all(conn, "SELECT id, nombre FROM rubro ORDER BY id")
        rubro_class: dict[int, dict] = {}
        for r in rubros:
            nombre = r["nombre"] or ""
            if nombre in RUBROS_CANONICOS:
                cls = "REAL"
            elif RUBRO_TEST_PATTERN.search(nombre):
                cls = "CONFIRMADO_TEST"
            else:
                cls = "INDETERMINADO"
            dom_cnt = fetch_scalar(
                conn, "SELECT COUNT(*) FROM domicilio WHERE rubro_id = :rid", {"rid": r["id"]}
            )
            rel_cnt = fetch_scalar(
                conn, "SELECT COUNT(*) FROM relevamiento WHERE rubro_id = :rid", {"rid": r["id"]}
            )
            pool_cnt = 0
            try:
                pool_cnt = fetch_scalar(
                    conn,
                    "SELECT COUNT(*) FROM ruta_pool_dia WHERE rubro_id = :rid",
                    {"rid": r["id"]},
                )
            except Exception:
                pass
            rubro_class[r["id"]] = {
                "id": r["id"],
                "nombre": nombre,
                "clasificacion": cls,
                "domicilios": dom_cnt,
                "relevamientos": rel_cnt,
                "ruta_pool_dia": pool_cnt,
            }

        rubros_test = [v for v in rubro_class.values() if v["clasificacion"] == "CONFIRMADO_TEST"]
        rubros_test_sin_refs = [
            v for v in rubros_test
            if v["domicilios"] == 0 and v["relevamientos"] == 0 and v["ruta_pool_dia"] == 0
        ]
        rubros_test_con_refs = [v for v in rubros_test if v not in rubros_test_sin_refs]

        report["rubros"] = {
            "total": len(rubros),
            "canonicos_presentes": sum(
                1 for v in rubro_class.values() if v["clasificacion"] == "REAL"
            ),
            "confirmado_test": len(rubros_test),
            "test_sin_referencias_A": len(rubros_test_sin_refs),
            "test_con_referencias_B": len(rubros_test_con_refs),
            "indeterminado": sum(
                1 for v in rubro_class.values() if v["clasificacion"] == "INDETERMINADO"
            ),
            "muestra_test": rubros_test[:50],
            "muestra_indeterminado": [
                v for v in rubro_class.values() if v["clasificacion"] == "INDETERMINADO"
            ][:30],
        }

        test_rubro_ids = {v["id"] for v in rubros_test}
        confirmed_test_rubro_ids = test_rubro_ids

        # 15. Juzgados
        juzgados = fetch_all(
            conn, "SELECT id, codigo, nombre FROM juzgado_catalogo ORDER BY id"
        )
        juzgado_detail = []
        for j in juzgados:
            codigo = (j.get("codigo") or "").strip()
            nombre = (j.get("nombre") or "").strip()
            if codigo in JUZGADOS_CANONICOS:
                cls = "REAL"
            elif JUZGADO_TEST_PATTERN.search(codigo) or JUZGADO_TEST_PATTERN.search(nombre):
                cls = "CONFIRMADO_TEST"
            else:
                cls = "INDETERMINADO"
            of_cnt = fetch_scalar(
                conn, "SELECT COUNT(*) FROM oficio WHERE juzgado_id = :jid", {"jid": j["id"]}
            )
            juzgado_detail.append(
                {
                    "id": j["id"],
                    "codigo": codigo,
                    "nombre": nombre,
                    "clasificacion": cls,
                    "oficios": of_cnt,
                    "bucket": (
                        "A_sin_oficios" if of_cnt == 0
                        else "B_solo_oficios_test_pendiente_revision"
                        if cls == "CONFIRMADO_TEST"
                        else "C_revisar"
                    ),
                }
            )
        report["juzgados"] = {
            "total": len(juzgados),
            "canonicos": sum(1 for j in juzgado_detail if j["clasificacion"] == "REAL"),
            "confirmado_test": sum(
                1 for j in juzgado_detail if j["clasificacion"] == "CONFIRMADO_TEST"
            ),
            "indeterminado": sum(
                1 for j in juzgado_detail if j["clasificacion"] == "INDETERMINADO"
            ),
            "detalle_test": [j for j in juzgado_detail if j["clasificacion"] == "CONFIRMADO_TEST"],
        }

        # 16. Relevadores
        relevadores = fetch_all(
            conn, "SELECT id, nombre, activo FROM relevador ORDER BY id"
        )
        rel_detail = []
        for rel in relevadores:
            nombre = rel["nombre"] or ""
            if nombre in RELEVADORES_CANONICOS:
                cls = "REAL"
            elif re.search(r"(QA|Inactivo-|test)", nombre, re.I):
                cls = "CONFIRMADO_TEST" if "QA" in nombre or "Inactivo" in nombre else "PROBABLE_TEST"
            else:
                cls = "INDETERMINADO"
            rel_cnt = fetch_scalar(
                conn,
                "SELECT COUNT(*) FROM relevamiento_relevador WHERE relevador_id = :rid",
                {"rid": rel["id"]},
            )
            rel_detail.append(
                {
                    "id": rel["id"],
                    "nombre": nombre,
                    "activo": rel.get("activo"),
                    "clasificacion": cls,
                    "relevamientos_junction": rel_cnt,
                }
            )
        otro_qa = next((r for r in rel_detail if r["nombre"] == "Otro Relevador QA"), None)
        if otro_qa:
            otro_qa["relevamientos_ids"] = [
                row["relevamiento_id"]
                for row in fetch_all(
                    conn,
                    """
                    SELECT rr.relevamiento_id
                    FROM relevamiento_relevador rr
                    WHERE rr.relevador_id = :rid
                    ORDER BY rr.relevamiento_id
                    """,
                    {"rid": otro_qa["id"]},
                )
            ]
        report["relevadores"] = {
            "total": len(relevadores),
            "canonicos": sum(1 for r in rel_detail if r["clasificacion"] == "REAL"),
            "qa_test": [r for r in rel_detail if r["clasificacion"] in ("CONFIRMADO_TEST", "PROBABLE_TEST")],
            "indeterminado": [r for r in rel_detail if r["clasificacion"] == "INDETERMINADO"],
            "otro_relevador_qa": otro_qa,
        }

        # 17. Inspectores
        inspector_count = fetch_scalar(conn, "SELECT COUNT(*) FROM inspector")
        report["inspectores"] = {
            "total": inspector_count,
            "nota": "24 canónicos esperados; no limpiar sin evidencia nueva",
        }

        # 5. Rutas test
        rutas_confirmado_cnt = fetch_scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM ruta_trabajo rt
            JOIN users u ON u.id = rt.created_by_user_id
            WHERE {SQL_TEST_USER_WHERE}
            """,
        )
        rutas_fecha_artificial_cnt = fetch_scalar(
            conn, "SELECT COUNT(*) FROM ruta_trabajo WHERE fecha >= '2080-01-01'"
        )
        rutas_hijos = fetch_all(
            conn,
            f"""
            SELECT
                COUNT(DISTINCT rt.id) AS rutas,
                COUNT(DISTINCT rg.id) AS grupos,
                COUNT(DISTINCT rgi.id) AS grupo_inspector,
                COUNT(DISTINCT ri.id) AS items,
                COUNT(DISTINCT rpd.id) AS pool_dia
            FROM ruta_trabajo rt
            JOIN users u ON u.id = rt.created_by_user_id
            LEFT JOIN ruta_grupo rg ON rg.ruta_trabajo_id = rt.id
            LEFT JOIN ruta_grupo_inspector rgi ON rgi.ruta_grupo_id = rg.id
            LEFT JOIN ruta_item ri ON ri.ruta_trabajo_id = rt.id
            LEFT JOIN ruta_pool_dia rpd ON rpd.ruta_trabajo_id = rt.id
            WHERE {SQL_TEST_USER_WHERE}
            """,
        )
        rutas_muestra = fetch_all(
            conn,
            f"""
            SELECT rt.id, rt.fecha, rt.turno, rt.numero, rt.estado_ruta, rt.created_by_user_id
            FROM ruta_trabajo rt
            JOIN users u ON u.id = rt.created_by_user_id
            WHERE {SQL_TEST_USER_WHERE}
            ORDER BY rt.id DESC
            LIMIT 20
            """,
        )
        report["rutas_test"] = {
            "confirmado_test_by_created_by": rutas_confirmado_cnt,
            "probable_test_fecha_2080_plus": rutas_fecha_artificial_cnt,
            "hijos_agregados": rutas_hijos[0] if rutas_hijos else {},
            "muestra": [{**r, "fecha": str(r["fecha"])} for r in rutas_muestra],
        }
        test_ruta_ids_count = rutas_confirmado_cnt or 0

        # 6. OTs test
        ot_test_stats = fetch_all(
            conn,
            """
            SELECT
                COUNT(*) AS total_pattern,
                SUM(CASE WHEN EXISTS (
                    SELECT 1 FROM actuaciones a WHERE a.orden_trabajo_id = ot.id
                ) THEN 1 ELSE 0 END) AS con_actuaciones,
                SUM(CASE WHEN EXISTS (
                    SELECT 1 FROM ruta_item ri WHERE ri.orden_trabajo_id = ot.id
                ) THEN 1 ELSE 0 END) AS con_ruta_item
            FROM orden_trabajo ot
            WHERE ot.numero_acta REGEXP '^[0-9A-F]{5}[A-F]$'
            """,
        )
        ot_detail = fetch_all(
            conn,
            """
            SELECT ot.id, ot.numero_acta, ot.anio,
                (SELECT COUNT(*) FROM actuaciones a WHERE a.orden_trabajo_id = ot.id) AS actuaciones,
                (SELECT COUNT(*) FROM ruta_item ri WHERE ri.orden_trabajo_id = ot.id) AS ruta_items
            FROM orden_trabajo ot
            WHERE ot.numero_acta REGEXP '^[0-9A-F]{5}[A-F]$'
            ORDER BY ot.id DESC
            LIMIT 50
            """,
        )
        ot_sin_actuaciones_cnt = fetch_scalar(
            conn,
            """
            SELECT COUNT(*) FROM orden_trabajo ot
            WHERE ot.numero_acta REGEXP '^[0-9A-F]{5}[A-F]$'
              AND NOT EXISTS (
                SELECT 1 FROM actuaciones a WHERE a.orden_trabajo_id = ot.id
              )
            """,
        )
        report["ordenes_trabajo_test"] = {
            "confirmado_test_pattern_unique_ot_numero": ot_test_stats[0] if ot_test_stats else {},
            "candidatos_delete_solo_refs_test": ot_sin_actuaciones_cnt,
            "detalle_muestra": ot_detail,
        }

        # 7. Iniciadores
        ini_by_tipo = fetch_all(
            conn,
            f"""
            SELECT ir.tipo_iniciador, COUNT(*) AS cnt
            FROM iniciador_ruta ir
            JOIN users u ON u.id = ir.created_by_user_id
            WHERE {SQL_TEST_USER_WHERE}
            GROUP BY ir.tipo_iniciador
            """,
        )
        ini_tot = fetch_scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM iniciador_ruta ir
            JOIN users u ON u.id = ir.created_by_user_id
            WHERE {SQL_TEST_USER_WHERE}
            """,
        )
        ini_muestra = fetch_all(
            conn,
            f"""
            SELECT ir.id, ir.tipo_iniciador, ir.estado_iniciador,
                   ir.relevamiento_id, ir.denuncia_id, ir.notificacion_id,
                   ir.comprobacion_id, ir.oficio_id, ir.created_by_user_id,
                   (SELECT COUNT(*) FROM ruta_item ri WHERE ri.iniciador_ruta_id = ir.id) AS ruta_items,
                   (SELECT COUNT(*) FROM ruta_pool_dia rpd WHERE rpd.iniciador_ruta_id = ir.id) AS pool_dia
            FROM iniciador_ruta ir
            JOIN users u ON u.id = ir.created_by_user_id
            WHERE {SQL_TEST_USER_WHERE}
            ORDER BY ir.id DESC
            LIMIT 30
            """,
        )
        report["iniciadores_test"] = {
            "confirmado_test_by_created_by": ini_tot,
            "por_tipo": ini_by_tipo,
            "muestra": ini_muestra,
        }

        # 8. Relevamientos — especial 4811, 4812, 4816
        special_ids = [4811, 4812, 4816]
        special_rels = []
        for sid in special_ids:
            rel = fetch_all(
                conn,
                """
                SELECT r.id, r.domicilio_id, r.rubro_id, r.created_by_user_id, r.created_at,
                       d.calle, d.numero
                FROM relevamiento r
                LEFT JOIN domicilio d ON d.id = r.domicilio_id
                WHERE r.id = :sid
                """,
                {"sid": sid},
            )
            if not rel:
                special_rels.append({"id": sid, "exists": False})
                continue
            r = rel[0]
            relevadores_names = fetch_all(
                conn,
                """
                SELECT rel.nombre FROM relevamiento_relevador rr
                JOIN relevador rel ON rel.id = rr.relevador_id
                WHERE rr.relevamiento_id = :sid
                """,
                {"sid": sid},
            )
            ini = fetch_all(
                conn,
                "SELECT id, tipo_iniciador, estado_iniciador FROM iniciador_ruta WHERE relevamiento_id = :sid",
                {"sid": sid},
            )
            items = fetch_all(
                conn,
                """
                SELECT ri.id, ri.ruta_trabajo_id FROM ruta_item ri
                JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id
                WHERE ir.relevamiento_id = :sid
                """,
                {"sid": sid},
            )
            pools = fetch_all(
                conn,
                """
                SELECT rpd.id, rpd.ruta_trabajo_id FROM ruta_pool_dia rpd
                JOIN iniciador_ruta ir ON ir.id = rpd.iniciador_ruta_id
                WHERE ir.relevamiento_id = :sid
                """,
                {"sid": sid},
            )
            cls = "CONFIRMADO_TEST" if r["created_by_user_id"] in confirmed_test_user_ids else "PROBABLE_TEST"
            if r.get("rubro_id") in confirmed_test_rubro_ids:
                cls = "CONFIRMADO_TEST"
            special_rels.append(
                {
                    "id": sid,
                    "exists": True,
                    "clasificacion": cls,
                    "created_by_user_id": r["created_by_user_id"],
                    "domicilio_id": r["domicilio_id"],
                    "calle": r.get("calle"),
                    "rubro_id": r["rubro_id"],
                    "relevadores": [x["nombre"] for x in relevadores_names],
                    "iniciadores": ini,
                    "ruta_items": items,
                    "ruta_pool_dia": pools,
                }
            )

        rels_test_cnt = fetch_scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM relevamiento r
            JOIN users u ON u.id = r.created_by_user_id
            WHERE {SQL_TEST_USER_WHERE}
            """,
        )

        report["relevamientos"] = {
            "por_created_by_test": rels_test_cnt,
            "especiales_4811_4812_4816": special_rels,
        }

        # 9. Denuncias test
        denuncias_test_cnt = fetch_scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM denuncia d
            JOIN users u ON u.id = d.created_by_user_id
            WHERE {SQL_TEST_USER_WHERE}
            """,
        )
        denuncias_test = fetch_all(
            conn,
            f"""
            SELECT d.id, d.domicilio_id, d.motivo, d.created_by_user_id, d.created_at,
                   dom.calle, dom.numero
            FROM denuncia d
            JOIN users u ON u.id = d.created_by_user_id
            LEFT JOIN domicilio dom ON dom.id = d.domicilio_id
            WHERE {SQL_TEST_USER_WHERE}
            ORDER BY d.id DESC
            LIMIT 30
            """,
        )
        report["denuncias_test"] = {
            "confirmado_test": denuncias_test_cnt,
            "muestra": denuncias_test,
        }

        # 10-11. Actuaciones test — strong evidence only
        actuaciones_fixture = fetch_all(
            conn,
            """
            SELECT a.id, a.tipo, a.fecha, a.domicilio_id, a.orden_trabajo_id,
                   d.calle, d.numero, ot.numero_acta AS ot_numero
            FROM actuaciones a
            LEFT JOIN domicilio d ON d.id = a.domicilio_id
            LEFT JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
            WHERE (
                d.calle REGEXP '^[0-9a-f]{8}-[0-9a-f]{4}-'
                OR ot.numero_acta REGEXP '^[0-9A-F]{5}[A-F]$'
                OR a.id = 11450
            )
            ORDER BY a.id
            LIMIT 80
            """,
        )
        actuaciones_confirmado_total = fetch_scalar(
            conn,
            """
            SELECT COUNT(*) FROM actuaciones a
            LEFT JOIN domicilio d ON d.id = a.domicilio_id
            LEFT JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
            WHERE d.calle REGEXP '^[0-9a-f]{8}-[0-9a-f]{4}-'
               OR ot.numero_acta REGEXP '^[0-9A-F]{5}[A-F]$'
               OR a.id = 11450
            """,
        )
        act_detail = []
        for act in actuaciones_fixture:
            act_id = act["id"]
            act_links = fetch_all(
                conn,
                "SELECT notificacion_id, comprobacion_id FROM actuaciones WHERE id = :aid",
                {"aid": act_id},
            )
            notif_id = act_links[0]["notificacion_id"] if act_links else None
            comp_id = act_links[0]["comprobacion_id"] if act_links else None
            insp_id = fetch_scalar(
                conn, "SELECT id FROM inspeccion WHERE actuacion_id = :aid LIMIT 1", {"aid": act_id}
            )
            hijos = {
                "inspeccion": 1 if insp_id else 0,
                "acta_inspeccion_item": (
                    fetch_scalar(
                        conn,
                        "SELECT COUNT(*) FROM acta_inspeccion_item WHERE acta_inspeccion_id = :iid",
                        {"iid": insp_id},
                    )
                    if insp_id
                    else 0
                ),
                "notificacion": 1 if notif_id else 0,
                "notificacion_motivo": (
                    fetch_scalar(
                        conn,
                        "SELECT COUNT(*) FROM notificacion_motivo WHERE notificacion_id = :nid",
                        {"nid": notif_id},
                    )
                    if notif_id
                    else 0
                ),
                "comprobacion": 1 if comp_id else 0,
                "clausura": fetch_scalar(
                    conn, "SELECT COUNT(*) FROM clausura WHERE actuacion_id = :aid", {"aid": act_id}
                ),
                "decomiso": fetch_scalar(
                    conn, "SELECT COUNT(*) FROM decomiso WHERE actuacion_id = :aid", {"aid": act_id}
                ),
                "actuaciones_inspector": fetch_scalar(
                    conn,
                    "SELECT COUNT(*) FROM actuaciones_inspector WHERE actuaciones_id = :aid",
                    {"aid": act_id},
                ),
            }
            evidencia = []
            if act.get("calle") and re.match(r"^[0-9a-f]{8}-", act["calle"] or "", re.I):
                evidencia.append("calle_uuid_fixture")
            if act.get("ot_numero") and OT_TEST_PATTERN.match(act["ot_numero"] or ""):
                evidencia.append("ot_unique_ot_numero_pattern")
            if act_id == 11450:
                evidencia.append("qa_habilitacion_persistence_test")
            act_detail.append(
                {
                    **act,
                    "fecha": str(act.get("fecha")),
                    "clasificacion": "CONFIRMADO_TEST" if evidencia else "PROBABLE_TEST",
                    "evidencia": evidencia,
                    "hijos": hijos,
                }
            )
        report["actuaciones_test"] = {
            "candidatas_evidencia_fuerte_total": actuaciones_confirmado_total,
            "detalle_muestra": act_detail,
            "confirmado_en_muestra": sum(
                1 for a in act_detail if a["clasificacion"] == "CONFIRMADO_TEST"
            ),
        }

        confirmed_act_ids_count = actuaciones_confirmado_total or 0

        # 12. Domicilios linked to test rubros
        if confirmed_test_rubro_ids:
            ph = ",".join(str(i) for i in confirmed_test_rubro_ids)
            doms_test_rubro = fetch_scalar(
                conn, f"SELECT COUNT(*) FROM domicilio WHERE rubro_id IN ({ph})"
            )
            dom_sample = fetch_all(
                conn,
                f"""
                SELECT d.id, d.calle, d.numero, d.rubro_id,
                    (SELECT COUNT(*) FROM actuaciones a WHERE a.domicilio_id = d.id) AS actuaciones,
                    (SELECT COUNT(*) FROM relevamiento r WHERE r.domicilio_id = d.id) AS relevamientos,
                    (SELECT COUNT(*) FROM denuncia dn WHERE dn.domicilio_id = d.id) AS denuncias
                FROM domicilio d
                WHERE d.rubro_id IN ({ph})
                ORDER BY d.id
                LIMIT 20
                """,
            )
            dom_only_test = fetch_scalar(
                conn,
                f"""
                SELECT COUNT(*) FROM domicilio d
                WHERE d.rubro_id IN ({ph})
                  AND NOT EXISTS (
                    SELECT 1 FROM actuaciones a
                    JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
                    WHERE a.domicilio_id = d.id
                      AND NOT ot.numero_acta REGEXP '^[0-9A-F]{{5}}[A-F]$'
                  )
                  AND (d.calle REGEXP '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-' OR d.calle IS NULL)
                """,
            )
        else:
            doms_test_rubro = 0
            dom_sample = []
            dom_only_test = 0

        report["domicilios_test"] = {
            "con_rubro_confirmado_test": doms_test_rubro,
            "muestra": dom_sample,
            "candidatos_solo_refs_test_aprox": dom_only_test,
            "nota": "requiere grafo completo por domicilio antes de borrar",
        }

        # 13. Contribuyentes — fixture patterns
        contrib_test = fetch_all(
            conn,
            """
            SELECT c.id, c.apellido, c.nombre, c.documento,
                (SELECT COUNT(*) FROM domicilio d WHERE d.contribuyente_id = c.id) AS domicilios
            FROM contribuyente c
            WHERE c.apellido REGEXP '^[0-9a-f]{8}-'
               OR c.nombre REGEXP '^[0-9a-f]{8}-'
               OR c.documento REGEXP '^TEST'
               OR c.apellido LIKE 'ApellidoTest%'
               OR c.nombre LIKE 'NombreTest%'
            ORDER BY c.id
            LIMIT 100
            """,
        )
        report["contribuyentes_test"] = {
            "candidatos_fixture": len(contrib_test),
            "detalle": contrib_test,
        }

        # 19. Expedientes / oficios
        if confirmed_test_user_ids:
            exp_test = 0
        else:
            exp_test = 0
        exp_of = fetch_all(
            conn,
            """
            SELECT o.id AS oficio_id, o.numero_oficio, o.juzgado_id, jc.codigo AS juzgado_codigo,
                   (SELECT COUNT(*) FROM expediente e WHERE e.oficio_id = o.id) AS expedientes
            FROM oficio o
            JOIN juzgado_catalogo jc ON jc.id = o.juzgado_id
            WHERE jc.codigo NOT IN (
                'JF1','JF2','JF3','JF4','JF5','JF6','JF7','JF8','JF9','JF10',
                'JF11','JF12','JF13','JF14','JF15'
              )
            LIMIT 50
            """,
        )
        report["expedientes_oficios"] = {
            "oficios_juzgado_no_canonico_muestra": exp_of,
            "nota": "revisar trazabilidad antes de borrar",
        }

        # 20-21. FK graph from information_schema
        fk_rows = fetch_all(
            conn,
            """
            SELECT
                kcu.TABLE_NAME AS child_table,
                kcu.COLUMN_NAME AS child_column,
                kcu.REFERENCED_TABLE_NAME AS parent_table,
                kcu.REFERENCED_COLUMN_NAME AS parent_column,
                rc.UPDATE_RULE,
                rc.DELETE_RULE
            FROM information_schema.KEY_COLUMN_USAGE kcu
            JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
              ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
             AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY kcu.REFERENCED_TABLE_NAME, kcu.TABLE_NAME
            """,
        )
        cleanup_relevant_parents = {
            "users", "rubro", "juzgado_catalogo", "relevador", "inspector",
            "domicilio", "contribuyente", "orden_trabajo", "actuaciones",
            "iniciador_ruta", "ruta_trabajo", "ruta_grupo", "relevamiento", "denuncia",
            "inspeccion", "notificacion", "comprobacion",
        }
        fk_relevant = [
            r for r in fk_rows
            if r["parent_table"] in cleanup_relevant_parents
            or r["child_table"] in cleanup_relevant_parents
        ]
        report["fk_inventory"] = {
            "total_fks": len(fk_rows),
            "cleanup_relevant": fk_relevant,
        }

        # 22. Soft delete columns
        soft_cols = fetch_all(
            conn,
            """
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND (
                COLUMN_NAME IN ('deleted_at', 'activo', 'is_active')
                OR COLUMN_NAME LIKE '%estado%'
              )
            ORDER BY TABLE_NAME, COLUMN_NAME
            """,
        )
        report["soft_delete_columns"] = soft_cols

        # 23. Post-cleanup estimates
        post = {}
        for tbl in BASELINE_TABLES:
            cur = baseline.get(tbl, 0)
            if not isinstance(cur, int):
                post[tbl] = {"actual": cur}
                continue
            elim = 0
            indet = 0
            if tbl == "users":
                elim = len(confirmed_test_user_ids)
                indet = len(users) - elim - 1  # minus admin
            elif tbl == "rubro":
                elim = len(rubros_test_sin_refs)
                indet = baseline["rubro"] - len(RUBROS_CANONICOS) - elim if isinstance(baseline.get("rubro"), int) else 0
            elif tbl == "juzgado_catalogo":
                elim = sum(
                    1 for j in juzgado_detail
                    if j["clasificacion"] == "CONFIRMADO_TEST" and j["oficios"] == 0
                )
            elif tbl == "relevamiento":
                elim = rels_test_cnt
            elif tbl == "denuncia":
                elim = denuncias_test_cnt if isinstance(denuncias_test_cnt, int) else 0
            elif tbl == "actuaciones":
                elim = confirmed_act_ids_count if isinstance(confirmed_act_ids_count, int) else 0
            elif tbl == "ruta_trabajo":
                elim = test_ruta_ids_count if isinstance(test_ruta_ids_count, int) else 0
            elif tbl == "orden_trabajo":
                elim = ot_sin_actuaciones_cnt if isinstance(ot_sin_actuaciones_cnt, int) else 0
            elif tbl == "domicilio":
                elim = dom_only_test if isinstance(dom_only_test, int) else 0
            post[tbl] = {
                "actual": cur,
                "confirmado_test_a_eliminar": elim,
                "estimado_post_cleanup": max(0, cur - elim),
                "indeterminado_conservado": indet if indet else "ver sección",
            }
        report["post_cleanup_estimates"] = post

        # Summary counts for manifest proposal
        report["manifest_proposal"] = {
            "archivo": f"cleanup_manifest_{datetime.now().strftime('%Y%m%d')}.json",
            "entidades": {
                "users": confirmed_test_user_ids[:5000],
                "rubros_sin_refs": [r["id"] for r in rubros_test_sin_refs],
                "rubros_con_refs_revisar": [r["id"] for r in rubros_test_con_refs],
                "juzgados_test_sin_oficios": [
                    j["id"] for j in juzgado_detail
                    if j["clasificacion"] == "CONFIRMADO_TEST" and j["oficios"] == 0
                ],
                "rutas_trabajo_count": test_ruta_ids_count,
                "actuaciones_count": confirmed_act_ids_count,
                "relevamientos_especiales": special_ids,
            },
            "nota": "IDs congelados tras auditoría; cleanup futuro usa manifest, no regex en caliente",
        }

        report["future_script_design"] = {
            "path": "scripts/cleanup_test_contamination.py",
            "flags": ["--dry-run (default)", "--apply"],
            "pre_apply": [
                "backup completo digitaliza_sandbox",
                "guardar baseline counts",
                "generar manifest JSON",
                "dry-run inmediatamente anterior",
            ],
            "guardas_negativas": [
                "rubros canónicos", "relevadores canónicos", "inspectores canónicos",
                "JF1-JF15", "admin/admin@local", "calles canónicas", "distritos",
            ],
        }

        report["post_cleanup_validation"] = [
            "sin FK huérfanas",
            "catálogos canónicos presentes (rubros 29, relevadores 10, inspectores 24, juzgados 15, items 6)",
            "actuaciones reales conservadas",
            "admin existe",
            "endpoints catálogo y mapa OK",
        ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"cleanup_diag_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "database": report["database_confirmed"],
        "alembic": report["alembic_version"],
        "output": str(out_path),
        "baseline": report["baseline_counts"],
        "usuarios_confirmado_test": report["usuarios"]["confirmado_test"],
        "rubros_confirmado_test": report["rubros"]["confirmado_test"],
        "actuaciones_confirmado_test": confirmed_act_ids_count,
    }, indent=2))


if __name__ == "__main__":
    main()
