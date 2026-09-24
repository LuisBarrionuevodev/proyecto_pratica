"""
PREDEPLOY-CLEANUP.3K-DIAG — ADMIN-GRAPH auditoría residual administrativo test.
Solo SELECT. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import (
    JUZGADO_TEST_PATTERN,
    JUZGADOS_CANONICOS,
    SQL_TEST_USER_WHERE,
)
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import _validate_delete_order_fk
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.route_residual_diag import BLOCKED_NOTIF_25, FUTURE_EXPEDIENTE_27
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    load_user_fk_columns,
    protection_closure_check,
)

COMP_2289 = 2289
OFICIO_1662 = 1662

USERS_FK_FREE_POST_3J2 = 833

BASELINE_POST_3J2 = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2703,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3685,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8001,
    "actuaciones": 8074,
    "denuncia": 417,
    "relevamiento": 4566,
    "orden_trabajo": 8810,
    "notificacion": 2478,
    "comprobacion": 1530,
    "inspeccion": 898,
    "actuaciones_inspector": 4180,
    "acta_inspeccion_item": 52,
    "clausura": 69,
    "decomiso": 25,
    "relevamiento_relevador": 525,
}

ADMIN_TABLES = ("notificacion", "comprobacion", "expediente", "oficio")

TEST_FILES_OFICIO_SCAN = (
    "tests/test_comprobacion_pendientes_reinspeccion_bandeja.py",
    "tests/test_oficio_expediente_flow.py",
    "tests/test_expediente_from_comprobacion.py",
)


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _count_ids_exist(conn: Connection, table: str, ids: set[int]) -> int:
    if not ids:
        return 0
    found = 0
    for chunk in _chunk_ids(ids, 400):
        ph = ",".join(str(i) for i in chunk)
        found += int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE id IN ({ph})") or 0)
    return found


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts = {t: _count(conn, t) for t in BASELINE_POST_3J2}
    drift = [f"{t}: {counts[t]} != {e}" for t, e in BASELINE_POST_3J2.items() if counts[t] != e]
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": not drift,
        "drift": drift,
        "users_test_fk_free_post_3j2": USERS_FK_FREE_POST_3J2,
    }


def _incoming_fk_edges(conn: Connection, parent_table: str) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT kcu.TABLE_NAME AS child_table, kcu.COLUMN_NAME AS child_column,
               rc.DELETE_RULE AS delete_rule, rc.UPDATE_RULE AS update_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.REFERENCED_TABLE_NAME = :parent
        ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
        """,
        {"parent": parent_table},
    )


def _outgoing_fk_edges(conn: Connection, child_table: str) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT kcu.REFERENCED_TABLE_NAME AS parent_table,
               kcu.COLUMN_NAME AS child_column,
               kcu.REFERENCED_COLUMN_NAME AS parent_column,
               rc.DELETE_RULE AS delete_rule, rc.UPDATE_RULE AS update_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.TABLE_NAME = :child
          AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY kcu.REFERENCED_TABLE_NAME, kcu.COLUMN_NAME
        """,
        {"child": child_table},
    )


def _fk_graph_admin(conn: Connection) -> dict[str, Any]:
    return {
        tbl: {
            "incoming": _incoming_fk_edges(conn, tbl),
            "outgoing": _outgoing_fk_edges(conn, tbl),
        }
        for tbl in ADMIN_TABLES
    }


def _surviving_refs(conn: Connection, parent_table: str, pk_id: int) -> dict[str, Any]:
    by_fk: dict[str, dict[str, Any]] = {}
    total = 0
    for edge in _incoming_fk_edges(conn, parent_table):
        tbl, col = edge["child_table"], edge["child_column"]
        n = int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :id", {"id": pk_id}) or 0)
        if n:
            key = f"{tbl}.{col}"
            by_fk[key] = {"count": n, "delete_rule": edge["delete_rule"]}
            total += n
    return {"total_refs": total, "by_fk": by_fk}


def _cascade_on_delete(conn: Connection, parent_table: str, ids: set[int]) -> dict[str, Any]:
    cascades: dict[str, int] = {}
    set_nulls: dict[str, int] = {}
    restrict_refs: dict[str, int] = {}
    for edge in _incoming_fk_edges(conn, parent_table):
        tbl, col = edge["child_table"], edge["child_column"]
        total = 0
        for chunk in _chunk_ids(ids, 300):
            ph = ",".join(str(i) for i in chunk)
            total += int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN ({ph})") or 0)
        if not total:
            continue
        key = f"{parent_table}->{tbl}.{col}"
        if edge["delete_rule"] == "CASCADE":
            cascades[key] = total
        elif edge["delete_rule"] == "SET NULL":
            set_nulls[key] = total
        else:
            restrict_refs[key] = total
    return {
        "cascade_physical": cascades,
        "set_null_physical": set_nulls,
        "restrict_physical": restrict_refs,
        "cascade_total": sum(cascades.values()),
        "set_null_total": sum(set_nulls.values()),
        "restrict_total": sum(restrict_refs.values()),
    }


def _xlsx_protected_ids(protected_manifest: dict[str, Any]) -> dict[str, set[int]]:
    out: dict[str, set[int]] = defaultdict(set)
    for entity, items in protected_manifest.get("entities", {}).items():
        for item in items:
            if isinstance(item, dict) and item.get("id") is not None:
                if item.get("evidence") == "REAL_ADMIN_XLSX" or item.get("match_status"):
                    out[entity].add(int(item["id"]))
    return dict(out)


def _xlsx_match(entity: str, doc_id: int | None, xlsx_ids: dict[str, set[int]]) -> str:
    if doc_id is None:
        return "N/A"
    return "MATCH_XLSX_DIRECT" if doc_id in xlsx_ids.get(entity, set()) else "NO_MATCH_XLSX"


def _protected_match(entity: str, doc_id: int | None, prot: dict[str, set[int]]) -> bool:
    if doc_id is None:
        return False
    return doc_id in prot.get(entity, set())


def _cross_node(
    entity: str,
    doc_id: int | None,
    xlsx_ids: dict[str, set[int]],
    prot: dict[str, set[int]],
) -> str:
    if _protected_match(entity, doc_id, prot):
        return "MATCH_PROTECTED_CLOSURE"
    return _xlsx_match(entity, doc_id, xlsx_ids)


def _load_source_119(apply_2c2b_path: Path) -> set[int]:
    data = json.loads(apply_2c2b_path.read_text(encoding="utf-8"))
    return {int(x) for x in data.get("preserved", {}).get("source_notificaciones_119", [])}


def _notif_exp_mapping(conn: Connection) -> list[dict[str, Any]]:
    mapping: list[dict[str, Any]] = []
    for nid in BLOCKED_NOTIF_25:
        notif = conn.execute(
            text(
                """
                SELECT n.id, n.numero_acta, n.anio, n.mes, n.fecha_notificacion,
                       n.created_at, n.updated_at
                FROM notificacion n WHERE n.id = :id
                """
            ),
            {"id": nid},
        ).fetchone()
        exps = _rows(
            conn,
            """
            SELECT e.id, e.numero_expediente, e.anio, e.fecha_expediente, e.tipo_expediente,
                   e.comprobacion_id, e.notificacion_id, e.oficio_id, e.created_at, e.updated_at
            FROM expediente e WHERE e.notificacion_id = :nid
            """,
            {"nid": nid},
        )
        mapping.append(
            {
                "notificacion_id": nid,
                "notificacion_exists": bool(notif),
                "notificacion": dict(notif._mapping) if notif else None,
                "expedientes": exps,
                "expediente_count": len(exps),
            }
        )
    return mapping


def _union_find_components(edges: list[tuple[str, int, str, int]]) -> dict[int, dict[str, set[int]]]:
    """edges: (entity_a, id_a, entity_b, id_b) bidirectional."""
    parent: dict[tuple[str, int], tuple[str, int]] = {}

    def find(n: tuple[str, int]) -> tuple[str, int]:
        if n not in parent:
            parent[n] = n
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def union(a: tuple[str, int], b: tuple[str, int]) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for ea, ia, eb, ib in edges:
        union((ea, ia), (eb, ib))

    components: dict[tuple[str, int], dict[str, set[int]]] = defaultdict(
        lambda: {
            "notificacion_ids": set(),
            "comprobacion_ids": set(),
            "expediente_ids": set(),
            "oficio_ids": set(),
            "other": set(),
        }
    )
    for ea, ia, eb, ib in edges:
        for ent, eid in ((ea, ia), (eb, ib)):
            root = find((ent, eid))
            key = f"{ent}:{eid}"
            bucket = components[root]
            if ent == "notificacion":
                bucket["notificacion_ids"].add(eid)
            elif ent == "comprobacion":
                bucket["comprobacion_ids"].add(eid)
            elif ent == "expediente":
                bucket["expediente_ids"].add(eid)
            elif ent == "oficio":
                bucket["oficio_ids"].add(eid)
            else:
                bucket["other"].add(key)

    # Seed isolated nodes from universe
    universe: list[tuple[str, int]] = []
    for nid in BLOCKED_NOTIF_25:
        universe.append(("notificacion", nid))
    universe.append(("comprobacion", COMP_2289))
    for eid in FUTURE_EXPEDIENTE_27:
        universe.append(("expediente", eid))
    universe.append(("oficio", OFICIO_1662))

    for ent, eid in universe:
        root = find((ent, eid))
        bucket = components[root]
        if ent == "notificacion":
            bucket["notificacion_ids"].add(eid)
        elif ent == "comprobacion":
            bucket["comprobacion_ids"].add(eid)
        elif ent == "expediente":
            bucket["expediente_ids"].add(eid)
        elif ent == "oficio":
            bucket["oficio_ids"].add(eid)

    out: dict[int, dict[str, Any]] = {}
    for idx, (_root, bucket) in enumerate(
        sorted(components.items(), key=lambda x: min(x[1]["notificacion_ids"] or x[1]["comprobacion_ids"] or {0})), 1
    ):
        out[idx] = {
            "component_id": f"ADMIN-COMP-{idx:02d}",
            "notificacion_ids": sorted(bucket["notificacion_ids"]),
            "comprobacion_ids": sorted(bucket["comprobacion_ids"]),
            "expediente_ids": sorted(bucket["expediente_ids"]),
            "oficio_ids": sorted(bucket["oficio_ids"]),
            "other_entities": sorted(bucket["other"]),
        }
    return out


def _build_graph_edges(conn: Connection) -> tuple[list[tuple[str, int, str, int]], list[dict[str, Any]]]:
    edges: list[tuple[str, int, str, int]] = []
    edge_log: list[dict[str, Any]] = []

    # notificacion -> expediente via expediente.notificacion_id
    for nid in BLOCKED_NOTIF_25:
        for row in _rows(
            conn,
            "SELECT id FROM expediente WHERE notificacion_id = :nid",
            {"nid": nid},
        ):
            eid = int(row["id"])
            edges.append(("notificacion", nid, "expediente", eid))
            edge_log.append(
                {
                    "from": {"entity": "notificacion", "id": nid},
                    "to": {"entity": "expediente", "id": eid},
                    "fk": "expediente.notificacion_id",
                    "delete_rule": "RESTRICT",
                }
            )

    # comprobacion <-> expediente
    for row in _rows(
        conn,
        "SELECT id, comprobacion_id, oficio_id, notificacion_id FROM expediente WHERE comprobacion_id = :cid",
        {"cid": COMP_2289},
    ):
        eid = int(row["id"])
        edges.append(("comprobacion", COMP_2289, "expediente", eid))
        edge_log.append(
            {
                "from": {"entity": "comprobacion", "id": COMP_2289},
                "to": {"entity": "expediente", "id": eid},
                "fk": "expediente.comprobacion_id",
                "delete_rule": "RESTRICT",
            }
        )
        if row["oficio_id"]:
            oid = int(row["oficio_id"])
            edges.append(("expediente", eid, "oficio", oid))
            edge_log.append(
                {
                    "from": {"entity": "expediente", "id": eid},
                    "to": {"entity": "oficio", "id": oid},
                    "fk": "expediente.oficio_id",
                    "delete_rule": "RESTRICT",
                }
            )

    # oficio -> comprobacion
    of_row = conn.execute(
        text("SELECT id, comprobacion_id FROM oficio WHERE id = :id"),
        {"id": OFICIO_1662},
    ).fetchone()
    if of_row and of_row.comprobacion_id:
        edges.append(("oficio", OFICIO_1662, "comprobacion", int(of_row.comprobacion_id)))
        edge_log.append(
            {
                "from": {"entity": "oficio", "id": OFICIO_1662},
                "to": {"entity": "comprobacion", "id": int(of_row.comprobacion_id)},
                "fk": "oficio.comprobacion_id",
                "delete_rule": "RESTRICT",
            }
        )

    return edges, edge_log


def _comp2289_graph(conn: Connection) -> dict[str, Any]:
    comp = conn.execute(
        text("SELECT id, numero_acta, anio, mes, created_at FROM comprobacion WHERE id = :id"),
        {"id": COMP_2289},
    ).fetchone()
    exps = _rows(
        conn,
        """
        SELECT id, numero_expediente, anio, fecha_expediente, tipo_expediente,
               comprobacion_id, notificacion_id, oficio_id, created_at
        FROM expediente WHERE comprobacion_id = :cid OR id IN (3103, 3104)
        ORDER BY id
        """,
        {"cid": COMP_2289},
    )
    oficio = _rows(
        conn,
        "SELECT id, numero_oficio, anio, fecha_oficio, causa, juzgado_id, comprobacion_id FROM oficio WHERE id = :id",
        {"id": OFICIO_1662},
    )
    of_by_comp = _rows(
        conn,
        "SELECT id, numero_oficio, comprobacion_id FROM oficio WHERE comprobacion_id = :cid",
        {"cid": COMP_2289},
    )
    exp_by_oficio = _rows(
        conn,
        "SELECT id, numero_expediente, oficio_id, comprobacion_id FROM expediente WHERE oficio_id = :oid",
        {"oid": OFICIO_1662},
    )
    ini_comp = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE comprobacion_id = {COMP_2289}"))
    ini_of = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE oficio_id = {OFICIO_1662}"))
    act_comp = sorted(_fetch_ids(conn, f"SELECT id FROM actuaciones WHERE comprobacion_id = {COMP_2289}"))

    exp_3103 = next((e for e in exps if e["id"] == 3103), None)
    exp_3104 = next((e for e in exps if e["id"] == 3104), None)
    of_1662 = oficio[0] if oficio else None

    logical_diagram = [
        f"comprobacion {COMP_2289}",
        "  | expediente.comprobacion_id (RESTRICT)",
        f"  +-> expediente 3103 ({exp_3103['tipo_expediente'] if exp_3103 else '?'}) numero={exp_3103['numero_expediente'] if exp_3103 else '?'}",
        f"  +-> expediente 3104 ({exp_3104['tipo_expediente'] if exp_3104 else '?'}) numero={exp_3104['numero_expediente'] if exp_3104 else '?'}",
        f"        | expediente.oficio_id (RESTRICT)",
        f"        +-> oficio {OFICIO_1662} ({of_1662['numero_oficio'] if of_1662 else '?'})",
        f"              | oficio.comprobacion_id (RESTRICT) -> comprobacion {COMP_2289}",
        f"              | oficio.juzgado_id -> juzgado {of_1662['juzgado_id'] if of_1662 else '?'}",
    ]

    return {
        "comprobacion": dict(comp._mapping) if comp else None,
        "expedientes": exps,
        "oficio_1662": of_1662,
        "oficios_by_comprobacion": of_by_comp,
        "expedientes_by_oficio": exp_by_oficio,
        "surviving_refs": {
            "actuaciones_to_comprobacion": act_comp,
            "iniciador_ruta_to_comprobacion": ini_comp,
            "iniciador_ruta_to_oficio": ini_of,
        },
        "relationships": {
            "exp_3103_refs_comprobacion": bool(exp_3103 and exp_3103["comprobacion_id"] == COMP_2289),
            "exp_3103_refs_oficio": bool(exp_3103 and exp_3103.get("oficio_id")),
            "exp_3104_refs_comprobacion": bool(exp_3104 and exp_3104["comprobacion_id"] == COMP_2289),
            "exp_3104_refs_oficio": bool(exp_3104 and exp_3104.get("oficio_id") == OFICIO_1662),
            "oficio_refs_comprobacion": bool(of_1662 and of_1662["comprobacion_id"] == COMP_2289),
            "expediente_refs_oficio_direct": [e["id"] for e in exp_by_oficio],
            "both_expedientes_share_comprobacion": True,
        },
        "logical_diagram": logical_diagram,
    }


def _oficio1662_detail(conn: Connection) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT o.id, o.numero_oficio, o.anio, o.fecha_oficio, o.causa,
                   o.juzgado_id, o.comprobacion_id, o.deleted_at
            FROM oficio o WHERE o.id = :id
            """
        ),
        {"id": OFICIO_1662},
    ).fetchone()
    if not row:
        return {"exists": False}
    data = dict(row._mapping)
    juzgado = None
    if data.get("juzgado_id"):
        jz = conn.execute(
            text("SELECT id, codigo, nombre FROM juzgado_catalogo WHERE id = :id"),
            {"id": data["juzgado_id"]},
        ).fetchone()
        juzgado = dict(jz._mapping) if jz else None
    exp_refs = _rows(conn, "SELECT id, numero_expediente, tipo_expediente FROM expediente WHERE oficio_id = :oid", {"oid": OFICIO_1662})
    return {
        "exists": True,
        **data,
        "juzgado": juzgado,
        "expediente_refs": exp_refs,
        "incoming_fk": _surviving_refs(conn, "oficio", OFICIO_1662),
    }


def _classify_juzgado(juzgado: dict[str, Any] | None) -> dict[str, Any]:
    if not juzgado:
        return {"classification": "INDETERMINATE", "reason": "no_juzgado"}
    nombre = str(juzgado.get("nombre") or "")
    codigo = str(juzgado.get("codigo") or "")
    is_canonical = codigo in JUZGADOS_CANONICOS or nombre in JUZGADOS_CANONICOS
    is_test = bool(JUZGADO_TEST_PATTERN.search(nombre) or JUZGADO_TEST_PATTERN.search(codigo))
    if is_canonical and not is_test:
        cls = "CANONICAL_REAL"
    elif is_test and not is_canonical:
        cls = "CONFIRMADO_TEST"
    elif is_canonical and is_test:
        cls = "MIXED"
    else:
        cls = "INDETERMINATE"
    return {
        "juzgado_id": juzgado.get("id"),
        "nombre": nombre,
        "codigo": codigo,
        "classification": cls,
        "is_canonical": is_canonical,
        "matches_test_pattern": is_test,
        "policy": "NO_DELETE juzgado en esta fase",
    }


def _scan_tests_for_oficio(backend_root: Path) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    patterns = [re.compile(r"OF8430", re.I), re.compile(r"8430B[02]", re.I), re.compile(r"Jz Solo Env", re.I)]
    for rel in TEST_FILES_OFICIO_SCAN:
        path = backend_root / rel
        if not path.is_file():
            continue
        text_content = path.read_text(encoding="utf-8", errors="replace")
        for pat in patterns:
            if pat.search(text_content):
                hits.append({"file": rel, "pattern": pat.pattern})
    return {"test_file_hits": hits, "oficio_8430_in_tests": any(h["pattern"] == "OF8430" for h in hits)}


def _classify_expediente(
    conn: Connection,
    eid: int,
    prot: dict[str, set[int]],
    xlsx_ids: dict[str, set[int]],
    notif_link: int | None,
    source_119: set[int],
) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT e.id, e.numero_expediente, e.anio, e.fecha_expediente, e.tipo_expediente,
                   e.comprobacion_id, e.notificacion_id, e.oficio_id, e.created_at
            FROM expediente e WHERE e.id = :id
            """
        ),
        {"id": eid},
    ).fetchone()
    if not row:
        return {"expediente_id": eid, "classification": "MISSING"}
    data = dict(row._mapping)
    incoming = _surviving_refs(conn, "expediente", eid)
    xlsx_status = _cross_node("expediente", eid, xlsx_ids, prot)
    external_refs = {
        k: v
        for k, v in incoming["by_fk"].items()
        if not (
            k.startswith("expediente.")
            or (k == "expediente.notificacion_id" and notif_link)
        )
    }
    # Filter: only count refs outside our admin universe
    universe_exp = set(FUTURE_EXPEDIENTE_27)
    universe_of = {OFICIO_1662}
    external_blockers: list[str] = []
    for fk_key, meta in incoming["by_fk"].items():
        if fk_key.startswith("oficio.") and meta.get("count"):
            external_blockers.append(fk_key)
        if fk_key.startswith("iniciador_ruta.") and meta.get("count"):
            external_blockers.append(fk_key)

    reasons: list[str] = []
    if xlsx_status == "MATCH_XLSX_DIRECT":
        classification = "PROTECTED_REAL_EXPEDIENTE"
        reasons.append("xlsx_direct_match")
    elif xlsx_status == "MATCH_PROTECTED_CLOSURE":
        classification = "PROTECTED_REAL_EXPEDIENTE"
        reasons.append("protected_closure")
    elif eid in {3103, 3104}:
        classification = "CONFIRMADO_TEST_EXPEDIENTE"
        reasons.append("comp_2289_chain_8430_pattern")
    elif notif_link and notif_link in source_119:
        classification = "CONFIRMADO_TEST_EXPEDIENTE"
        reasons.append("linked_source_119_orphan_notif")
    elif notif_link:
        classification = "CONFIRMADO_TEST_EXPEDIENTE"
        reasons.append("linked_orphan_test_notif_no_actuacion")
    elif external_blockers:
        classification = "INDETERMINATE_EXPEDIENTE"
        reasons.append(f"external_refs={external_blockers}")
    else:
        classification = "CONFIRMADO_TEST_EXPEDIENTE"
        reasons.append("admin_graph_candidate_no_real_evidence")

    return {
        "expediente_id": eid,
        **data,
        "xlsx_cross": xlsx_status,
        "incoming_refs": incoming,
        "external_blockers": external_blockers,
        "linked_notificacion_id": notif_link,
        "classification": classification,
        "classification_reasons": reasons,
    }


def _classify_oficio(
    oficio_detail: dict[str, Any],
    prot: dict[str, set[int]],
    xlsx_ids: dict[str, set[int]],
    test_scan: dict[str, Any],
) -> dict[str, Any]:
    if not oficio_detail.get("exists"):
        return {"classification": "MISSING"}
    oid = int(oficio_detail["id"])
    xlsx_status = _cross_node("oficio", oid, xlsx_ids, prot)
    reasons: list[str] = []
    if xlsx_status == "MATCH_XLSX_DIRECT":
        classification = "PROTECTED_REAL_OFICIO"
        reasons.append("xlsx_direct")
    elif xlsx_status == "MATCH_PROTECTED_CLOSURE":
        classification = "PROTECTED_REAL_OFICIO"
        reasons.append("protected_closure")
    elif oficio_detail.get("numero_oficio") == "OF8430" and test_scan.get("oficio_8430_in_tests"):
        classification = "CONFIRMADO_TEST_OFICIO"
        reasons.append("OF8430_test_suite_pattern")
    elif oficio_detail.get("numero_oficio") == "OF8430":
        classification = "CONFIRMADO_TEST_OFICIO"
        reasons.append("OF8430_comp2289_chain")
    else:
        classification = "INDETERMINATE_OFICIO"
        reasons.append("needs_review")
    return {
        "oficio_id": oid,
        "xlsx_cross": xlsx_status,
        "classification": classification,
        "classification_reasons": reasons,
    }


def _timestamp_correlation(mapping: list[dict[str, Any]], comp_graph: dict[str, Any]) -> dict[str, Any]:
    windows = Counter()
    samples: list[dict[str, Any]] = []
    for m in mapping:
        nid = m["notificacion_id"]
        n_created = m.get("notificacion", {}).get("created_at") if m.get("notificacion") else None
        for exp in m.get("expedientes", []):
            e_created = exp.get("created_at")
            if n_created and e_created:
                try:
                    delta = abs((e_created - n_created).total_seconds())
                except TypeError:
                    continue
                if delta == 0:
                    windows["same_second"] += 1
                    bucket = "same_second"
                elif delta <= 2:
                    windows["<=2_sec"] += 1
                    bucket = "<=2_sec"
                elif delta <= 60:
                    windows["<=1_min"] += 1
                    bucket = "<=1_min"
                else:
                    windows["mucho_anterior"] += 1
                    bucket = "mucho_anterior"
                samples.append(
                    {
                        "notificacion_id": nid,
                        "expediente_id": exp["id"],
                        "delta_seconds": delta,
                        "window": bucket,
                    }
                )
    comp_created = comp_graph.get("comprobacion", {}).get("created_at") if comp_graph.get("comprobacion") else None
    comp_samples: list[dict[str, Any]] = []
    for exp in comp_graph.get("expedientes", []):
        e_created = exp.get("created_at")
        if comp_created and e_created:
            try:
                delta = abs((e_created - comp_created).total_seconds())
            except TypeError:
                continue
            comp_samples.append({"expediente_id": exp["id"], "delta_seconds": delta})
    return {
        "notif_exp_pairs": samples,
        "window_counts": dict(windows),
        "comp_exp_pairs": comp_samples,
        "note": "timestamps secondary evidence only",
    }


def _derive_delete_topology(
    simple_components: list[dict[str, Any]],
    comp_b: dict[str, Any],
) -> dict[str, Any]:
    """FK-based delete order per component."""
    simple_order = ["expediente", "notificacion"]
    comp_b_order = ["expediente", "oficio", "comprobacion"]
    fk_edges = [
        ("expediente", "notificacion", "expediente.notificacion_id RESTRICT -> delete expediente first"),
        ("expediente", "comprobacion", "expediente.comprobacion_id RESTRICT -> delete expediente first"),
        ("expediente", "oficio", "expediente.oficio_id RESTRICT -> delete expediente before oficio"),
        ("oficio", "comprobacion", "oficio.comprobacion_id RESTRICT -> delete oficio before comprobacion"),
    ]
    return {
        "simple_components": {
            "order": simple_order,
            "per_component": [
                {
                    "component_id": c["component_id"],
                    "delete_order": simple_order,
                    "entities": {
                        "expediente": c["expediente_ids"],
                        "notificacion": c["notificacion_ids"],
                    },
                }
                for c in simple_components
            ],
        },
        "component_2289": {
            "order": comp_b_order,
            "expediente_ids": [3103, 3104],
            "oficio_ids": [OFICIO_1662],
            "comprobacion_ids": [COMP_2289],
            "note": "expediente 3104 before 3103 optional; both before oficio; oficio before comprobacion",
        },
        "fk_rationale": fk_edges,
    }


def _simulate_component_safe(
    conn: Connection,
    component: dict[str, Any],
    prot: dict[str, set[int]],
    exp_class: dict[int, str],
    notif_source_119: set[int],
) -> dict[str, Any]:
    nids = component.get("notificacion_ids", [])
    eids = component.get("expediente_ids", [])
    if not nids:
        return {"status": "N/A", "reason": "not_simple_notif_component"}
    all_test_exp = all(exp_class.get(e, "").startswith("CONFIRMADO_TEST") for e in eids)
    any_protected = any(
        nid in prot.get("notificacion", set()) or eid in prot.get("expediente", set())
        for nid in nids
        for eid in eids
    )
    ext_refs = False
    for eid in eids:
        refs = _surviving_refs(conn, "expediente", eid)
        for fk_key in refs["by_fk"]:
            if fk_key.startswith("iniciador_ruta.") or (
                fk_key.startswith("oficio.") and "oficio_id" not in fk_key
            ):
                ext_refs = True
    for nid in nids:
        act = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE notificacion_id = {nid}")
        ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE notificacion_id = {nid}")
        if act or ini:
            ext_refs = True
    if any_protected:
        status = "BLOCKED_SIMPLE_COMPONENT"
        reason = "protected_intersection"
    elif not all_test_exp:
        status = "BLOCKED_SIMPLE_COMPONENT"
        reason = "expediente_not_all_confirmed_test"
    elif ext_refs:
        status = "BLOCKED_SIMPLE_COMPONENT"
        reason = "external_surviving_refs"
    else:
        status = "SAFE_SIMPLE_COMPONENT"
        reason = "orphan_test_notif_plus_test_expediente"
    return {
        "component_id": component["component_id"],
        "notificacion_ids": nids,
        "expediente_ids": eids,
        "in_source_119": [n for n in nids if n in notif_source_119],
        "status": status,
        "reason": reason,
    }


def _users_simulation(
    conn: Connection,
    safe_exp: set[int],
    safe_notif: set[int],
    safe_comp: set[int],
    safe_oficio: set[int],
    label: str,
) -> dict[str, Any]:
    fk_columns = load_user_fk_columns(conn)
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    deleted_entities: dict[str, set[int]] = {
        "expediente": safe_exp,
        "notificacion": safe_notif,
        "comprobacion": safe_comp,
        "oficio": safe_oficio,
    }
    free_after = 0
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                if table in deleted_entities and r[0] in deleted_entities[table]:
                    continue
                blocked = True
                break
            if blocked:
                break
        if not blocked:
            free_after += 1
    baseline = USERS_FK_FREE_POST_3J2
    return {
        "simulation": label,
        "users_test_fk_free_baseline": baseline,
        "users_test_fk_free_after": free_after,
        "users_additionally_unlocked": free_after - baseline,
        "policy": "NO_DELETE users",
    }


def _postcount_wave(
    conn: Connection,
    wave_name: str,
    deletes: dict[str, set[int]],
    baseline_counts: dict[str, int],
) -> dict[str, Any]:
    result: dict[str, Any] = {"wave": wave_name, "tables": {}}
    for table, ids in deletes.items():
        if not ids:
            continue
        casc = _cascade_on_delete(conn, table, ids)
        before = baseline_counts.get(table, _count(conn, table))
        result["tables"][table] = {
            "before": before,
            "explicit_delete": len(ids),
            "cascade": casc,
            "after": before - len(ids),
        }
    return result


def run_admin_graph_diag(
    conn: Connection,
    *,
    protected_path: Path,
    apply_2c2b_path: Path,
    manifest_paths: list[Path],
    phase2c2c_manifest_path: Path | None = None,
    backend_root: Path | None = None,
) -> dict[str, Any]:
    """Orquestador diagnóstico ADMIN-GRAPH."""
    baseline = _baseline_check(conn)
    prot_manifest = load_manifest(protected_path)
    prot = expand_protected_indirect(conn, load_protected_sets(prot_manifest))
    xlsx_ids = _xlsx_protected_ids(prot_manifest)
    source_119 = _load_source_119(apply_2c2b_path)

    # §1-4 existence
    notif_exist = _count_ids_exist(conn, "notificacion", set(BLOCKED_NOTIF_25))
    comp_exist = bool(_scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": COMP_2289}))
    exp_exist = _count_ids_exist(conn, "expediente", set(FUTURE_EXPEDIENTE_27))
    of_exist = bool(
        _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = :id AND numero_oficio = 'OF8430'", {"id": OFICIO_1662})
    )

    candidate_universe = {
        "notificaciones_blocked_25": {
            "ids": list(BLOCKED_NOTIF_25),
            "exist_count": notif_exist,
            "expected": 25,
            "ok": notif_exist == 25,
        },
        "comprobacion_2289": {"id": COMP_2289, "exists": comp_exist},
        "expedientes_27": {
            "ids": list(FUTURE_EXPEDIENTE_27),
            "exist_count": exp_exist,
            "expected": 27,
            "ok": exp_exist == 27,
            "duplicate_check": len(FUTURE_EXPEDIENTE_27) == len(set(FUTURE_EXPEDIENTE_27)),
        },
        "oficio_1662": {"id": OFICIO_1662, "exists": of_exist, "expected_numero": "OF8430"},
    }

    fk_graph = _fk_graph_admin(conn)
    graph_edges, edge_log = _build_graph_edges(conn)
    connected_components = _union_find_components(graph_edges)
    simple_components = [c for c in connected_components.values() if c["notificacion_ids"] and not c["comprobacion_ids"]]
    comp_b_components = [c for c in connected_components.values() if COMP_2289 in c["comprobacion_ids"]]

    notification_exp_mapping = _notif_exp_mapping(conn)
    comp2289_graph = _comp2289_graph(conn)
    oficio1662 = _oficio1662_detail(conn)
    juzgado_analysis = _classify_juzgado(oficio1662.get("juzgado"))

    # XLSX + protected cross per node
    xlsx_cross: dict[str, list[dict[str, Any]]] = {e: [] for e in ADMIN_TABLES}
    protected_cross: dict[str, Any] = {}
    all_nodes: list[tuple[str, int]] = []
    for nid in BLOCKED_NOTIF_25:
        all_nodes.append(("notificacion", nid))
    all_nodes.append(("comprobacion", COMP_2289))
    for eid in FUTURE_EXPEDIENTE_27:
        all_nodes.append(("expediente", eid))
    all_nodes.append(("oficio", OFICIO_1662))

    for entity, doc_id in all_nodes:
        status = _cross_node(entity, doc_id, xlsx_ids, prot)
        xlsx_cross[entity].append({"id": doc_id, "status": status})
    for entity in ADMIN_TABLES:
        ids_in_universe = {doc_id for ent, doc_id in all_nodes if ent == entity}
        prot_ids = prot.get(entity, set())
        inter = sorted(ids_in_universe & prot_ids)
        xlsx_direct = sorted(ids_in_universe & xlsx_ids.get(entity, set()))
        protected_cross[entity] = {
            "universe_count": len(ids_in_universe),
            "protected_intersection": inter,
            "protected_intersection_count": len(inter),
            "xlsx_direct_intersection": xlsx_direct,
            "xlsx_direct_count": len(xlsx_direct),
        }

    # notif -> expediente link map for expediente classification
    notif_by_exp: dict[int, int] = {}
    for m in notification_exp_mapping:
        for exp in m.get("expedientes", []):
            notif_by_exp[int(exp["id"])] = m["notificacion_id"]

    expediente_classification = [
        _classify_expediente(conn, eid, prot, xlsx_ids, notif_by_exp.get(eid), source_119)
        for eid in FUTURE_EXPEDIENTE_27
    ]
    exp_class_map = {e["expediente_id"]: e["classification"] for e in expediente_classification}

    test_scan = _scan_tests_for_oficio(backend_root or Path("."))
    oficio_classification = _classify_oficio(oficio1662, prot, xlsx_ids, test_scan)

    # source_119 analysis for 25 notifs
    source_119_members = sorted(set(BLOCKED_NOTIF_25) & source_119)
    source_119_detail: list[dict[str, Any]] = []
    for nid in BLOCKED_NOTIF_25:
        act = sorted(_fetch_ids(conn, f"SELECT id FROM actuaciones WHERE notificacion_id = {nid}"))
        ini = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE notificacion_id = {nid}"))
        exp_refs = _rows(conn, "SELECT id FROM expediente WHERE notificacion_id = :nid", {"nid": nid})
        other = _surviving_refs(conn, "notificacion", nid)
        blockers = []
        if act:
            blockers.append(f"actuaciones:{act}")
        if ini:
            blockers.append(f"iniciador_ruta:{ini}")
        if exp_refs:
            blockers.append(f"expediente:{[r['id'] for r in exp_refs]}")
        for k, v in other["by_fk"].items():
            if k != "expediente.notificacion_id" and v.get("count"):
                blockers.append(f"{k}:{v['count']}")
        source_119_detail.append(
            {
                "notificacion_id": nid,
                "in_source_119": nid in source_119,
                "actuaciones_refs": act,
                "iniciador_ruta_refs": ini,
                "expediente_refs": [r["id"] for r in exp_refs],
                "only_blocker_is_expediente": (
                    not act and not ini and len(exp_refs) == 1
                    and other["total_refs"] == 1
                ),
                "surviving_blockers": blockers,
            }
        )

    # component simulations
    simple_sim = [
        _simulate_component_safe(conn, c, prot, exp_class_map, source_119) for c in simple_components
    ]
    safe_simple = [s for s in simple_sim if s["status"] == "SAFE_SIMPLE_COMPONENT"]
    blocked_simple = [s for s in simple_sim if s["status"] != "SAFE_SIMPLE_COMPONENT"]

    comp_b_exp_test = all(
        exp_class_map.get(e, "").startswith("CONFIRMADO_TEST") for e in [3103, 3104]
    )
    comp_b_of_test = oficio_classification["classification"] == "CONFIRMADO_TEST_OFICIO"
    comp_b_prot = bool(
        {COMP_2289} & prot.get("comprobacion", set())
        or {OFICIO_1662} & prot.get("oficio", set())
        or {3103, 3104} & prot.get("expediente", set())
    )
    act_comp = comp2289_graph["surviving_refs"]["actuaciones_to_comprobacion"]
    ini_comp = comp2289_graph["surviving_refs"]["iniciador_ruta_to_comprobacion"]
    ini_of = comp2289_graph["surviving_refs"]["iniciador_ruta_to_oficio"]
    if comp_b_prot:
        comp_b_status = "PROTECTED"
    elif act_comp or ini_comp or ini_of:
        comp_b_status = "BLOCKED"
    elif comp_b_exp_test and comp_b_of_test:
        comp_b_status = "ALL_CONFIRMED_TEST_SAFE"
    elif comp_b_exp_test or comp_b_of_test:
        comp_b_status = "MIXED"
    else:
        comp_b_status = "INDETERMINATE"

    component_classification = {
        "simple_components": simple_sim,
        "safe_simple_count": len(safe_simple),
        "blocked_simple_count": len(blocked_simple),
        "component_2289": {
            "status": comp_b_status,
            "expedientes_classification": {e: exp_class_map.get(e) for e in [3103, 3104]},
            "oficio_classification": oficio_classification["classification"],
            "surviving_non_admin_refs": {
                "actuaciones": act_comp,
                "iniciador_comprobacion": ini_comp,
                "iniciador_oficio": ini_of,
            },
        },
    }

    safe_notif = sorted({n for s in safe_simple for n in s["notificacion_ids"]})
    safe_exp_simple = sorted({e for s in safe_simple for e in s["expediente_ids"]})
    safe_exp_b = [3103, 3104] if comp_b_status == "ALL_CONFIRMED_TEST_SAFE" else []
    safe_oficio = [OFICIO_1662] if comp_b_status == "ALL_CONFIRMED_TEST_SAFE" else []
    safe_comp = [COMP_2289] if comp_b_status == "ALL_CONFIRMED_TEST_SAFE" else []

    safe_sets = {
        "SAFE_ADMIN_NOTIFICACION": safe_notif,
        "SAFE_ADMIN_EXPEDIENTE": sorted(set(safe_exp_simple) | set(safe_exp_b)),
        "SAFE_ADMIN_OFICIO": safe_oficio,
        "SAFE_ADMIN_COMPROBACION": safe_comp,
    }
    blocked_sets = {
        "KEEP_ADMIN_NOTIFICACION": sorted(set(BLOCKED_NOTIF_25) - set(safe_notif)),
        "KEEP_ADMIN_EXPEDIENTE": sorted(set(FUTURE_EXPEDIENTE_27) - set(safe_sets["SAFE_ADMIN_EXPEDIENTE"])),
        "KEEP_ADMIN_OFICIO": [OFICIO_1662] if OFICIO_1662 not in safe_oficio else [],
        "KEEP_ADMIN_COMPROBACION": [COMP_2289] if COMP_2289 not in safe_comp else [],
        "blocked_simple_reasons": blocked_simple,
        "component_2289_reason": comp_b_status,
    }

    delete_topology = _derive_delete_topology(simple_components, comp2289_graph)

    # cascade simulation for safe sets
    cascade_simulation: dict[str, Any] = {}
    for entity, ids in safe_sets.items():
        table = entity.replace("SAFE_ADMIN_", "").lower()
        if ids and table in ADMIN_TABLES:
            cascade_simulation[table] = _cascade_on_delete(conn, table, set(ids))

    virtual = VirtualDeleteState()
    for table, key in [
        ("expediente", "SAFE_ADMIN_EXPEDIENTE"),
        ("notificacion", "SAFE_ADMIN_NOTIFICACION"),
        ("oficio", "SAFE_ADMIN_OFICIO"),
        ("comprobacion", "SAFE_ADMIN_COMPROBACION"),
    ]:
        virtual.add_explicit(table, set(safe_sets[key]))
    protected_closure = protection_closure_check(virtual, prot)

    known = _load_known_test_ids_from_manifests(manifest_paths)
    known_test_guards = _known_test_guard(conn, known)

    users_sim = {
        "after_admin_a_simple": _users_simulation(
            conn,
            set(safe_exp_simple),
            set(safe_notif),
            set(),
            set(),
            "ADMIN-A",
        ),
        "after_admin_b_comp2289": _users_simulation(
            conn,
            set(safe_exp_simple) | set(safe_exp_b),
            set(safe_notif),
            set(safe_comp),
            set(safe_oficio),
            "ADMIN-A+B",
        ),
    }

    # catalog effects
    jz_id = oficio1662.get("juzgado_id")
    jz_fk_count = 0
    if jz_id:
        jz_fk_count = int(
            _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE juzgado_id = :jz", {"jz": jz_id}) or 0
        )
    catalog_effects = {
        "juzgado_oficio_1662": {
            "juzgado_id": jz_id,
            "classification": juzgado_analysis.get("classification"),
            "oficio_refs_to_juzgado": jz_fk_count,
            "fk_free_if_oficio_deleted": jz_fk_count <= 1 if jz_id else None,
            "policy": "NO_DELETE juzgado",
        },
        "note": "catalog impact metadata for phase 2E only",
    }

    baseline_counts = baseline["counts"]
    proposed_waves = {
        "ADMIN-A": {
            "description": "simple notificacion+expediente components",
            "delete_order": ["expediente", "notificacion"],
            "entities": {
                "expediente": safe_exp_simple,
                "notificacion": safe_notif,
            },
            "enabled": len(safe_simple) > 0,
        },
        "ADMIN-B": {
            "description": "comprobacion 2289 + expedientes 3103/3104 + oficio 1662",
            "delete_order": ["expediente", "oficio", "comprobacion"],
            "entities": {
                "expediente": safe_exp_b,
                "oficio": safe_oficio,
                "comprobacion": safe_comp,
            },
            "enabled": comp_b_status == "ALL_CONFIRMED_TEST_SAFE",
        },
        "ADMIN-C": {
            "description": "released orphan docs after admin cleanup",
            "entities": {
                "notificacion": sorted(set(BLOCKED_NOTIF_25) - set(safe_notif)) if comp_b_status == "ALL_CONFIRMED_TEST_SAFE" else [],
                "comprobacion": [COMP_2289] if comp_b_status == "ALL_CONFIRMED_TEST_SAFE" else [],
            },
            "enabled": False,
            "note": "requires ADMIN-A and ADMIN-B complete; docs already orphan",
        },
    }

    postcount_simulation = {
        "ADMIN-A": _postcount_wave(
            conn,
            "ADMIN-A",
            {"expediente": set(safe_exp_simple), "notificacion": set(safe_notif)},
            baseline_counts,
        ),
        "ADMIN-B": _postcount_wave(
            conn,
            "ADMIN-B",
            {
                "expediente": set(safe_exp_b),
                "oficio": set(safe_oficio),
                "comprobacion": set(safe_comp),
            },
            baseline_counts,
        ),
    }

    test_provenance = {
        "source_119": {
            "expected_15_of_25": 15,
            "actual_count": len(source_119_members),
            "members": source_119_members,
            "per_notificacion": source_119_detail,
        },
        "oficio_test_scan": test_scan,
        "expediente_patterns_8430": [e for e in expediente_classification if "8430" in str(e.get("numero_expediente", ""))],
    }

    timestamp_analysis = _timestamp_correlation(notification_exp_mapping, comp2289_graph)

    # expediente incoming refs audit
    expediente_other_refs = []
    for eid in FUTURE_EXPEDIENTE_27:
        refs = _surviving_refs(conn, "expediente", eid)
        expediente_other_refs.append({"expediente_id": eid, "incoming": refs})

    oficio_other_refs = {
        "oficio_id": OFICIO_1662,
        "incoming": _surviving_refs(conn, "oficio", OFICIO_1662),
        "iniciador_ruta": sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE oficio_id = {OFICIO_1662}")),
    }

    effect_on_docs = {
        "notificaciones_released_after_admin_a": safe_notif,
        "notificaciones_still_blocked": blocked_sets["KEEP_ADMIN_NOTIFICACION"],
        "comprobacion_2289_released_after_admin_b": COMP_2289 if comp_b_status == "ALL_CONFIRMED_TEST_SAFE" else None,
        "topology": "expediente first, then notificacion/oficio/comprobacion per FK RESTRICT",
    }

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3K-DIAG",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "candidate_universe": candidate_universe,
        "fk_graph": fk_graph,
        "graph_edges": edge_log,
        "connected_components": {
            "count": len(connected_components),
            "components": list(connected_components.values()),
            "simple_notif_exp_count": len(simple_components),
            "comp_2289_component_count": len(comp_b_components),
        },
        "notification_exp_mapping": notification_exp_mapping,
        "comp2289_graph": comp2289_graph,
        "oficio1662": oficio1662,
        "juzgado_analysis": juzgado_analysis,
        "xlsx_cross": xlsx_cross,
        "protected_cross": protected_cross,
        "test_provenance": test_provenance,
        "timestamp_analysis": timestamp_analysis,
        "expediente_classification": expediente_classification,
        "oficio_classification": oficio_classification,
        "component_classification": component_classification,
        "safe_sets": safe_sets,
        "blocked_sets": blocked_sets,
        "delete_topology": delete_topology,
        "cascade_simulation": cascade_simulation,
        "protected_closure": {
            "intersection_total": protected_closure.get("by_entity", {}),
            "valid": protected_closure.get("valid"),
            "conflicts": protected_closure.get("conflicts", []),
        },
        "users_simulation": users_sim,
        "catalog_effects": catalog_effects,
        "known_test_guards": known_test_guards,
        "proposed_waves": proposed_waves,
        "postcount_simulation": postcount_simulation,
        "expediente_other_refs": expediente_other_refs,
        "oficio_other_refs": oficio_other_refs,
        "effect_on_orphan_documents": effect_on_docs,
        "protected_manifest_path": str(protected_path.resolve()),
        "source_119_path": str(apply_2c2b_path.resolve()),
    }


def write_diag_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
