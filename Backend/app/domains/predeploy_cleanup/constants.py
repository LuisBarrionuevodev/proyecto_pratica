"""Constantes compartidas para cleanup FASE 1 predeploy."""

from __future__ import annotations

import re

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

RELEVAMIENTOS_QA_IDS = frozenset({4811, 4812, 4816, 4860, 4861})

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

OT_TEST_PATTERN = re.compile(r"^[0-9A-F]{5}[A-F]$", re.IGNORECASE)

SQL_TEST_USER_WHERE = """
    (
        email LIKE '%@t.local'
        OR email LIKE '%@test.local'
        OR username REGEXP '^(op_ruta3_|rlist_|edn_|op_ruta4_|op6f_|op6i_|op6j_|op7d_|op1b_|pr111_|pr11f_|crudmapa_|stab7_|fix7_|fix10a_|qa_|hotfix_|reenc_|relhot_|outd_|rec_of_|rec_|prod_|nr_|ind_|cnt_|ed4b_|rein_b_|reenc_of_|id10c_|st4_|hist_|cp_|cdoc_|u1_|create_|act_|ina_|est_op_|inactive_)'
    )
    AND NOT (LOWER(username) = 'admin' OR LOWER(email) = 'admin@local')
"""

TEST_ACTUACIONES_SQL = """
    SELECT a.id
    FROM actuaciones a
    LEFT JOIN domicilio d ON d.id = a.domicilio_id
    LEFT JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
    WHERE d.calle REGEXP '^[0-9a-f]{8}-[0-9a-f]{4}-'
       OR ot.numero_acta REGEXP '^[0-9A-F]{5}[A-F]$'
       OR a.id = 11450
"""

CRITICAL_PROTECTED_ENTITIES = frozenset(
    {
        "actuaciones",
        "orden_trabajo",
        "inspeccion",
        "notificacion",
        "comprobacion",
        "oficio",
        "expediente",
    }
)

PHASE1_NO_AUTO_DELETE = frozenset({"domicilio", "contribuyente", "domicilio_geocode"})

ROUTE_ENTITIES_NO_AUTO_PROTECT = frozenset(
    {"ruta_trabajo", "ruta_grupo", "ruta_grupo_inspector", "ruta_item", "ruta_pool_dia"}
)
