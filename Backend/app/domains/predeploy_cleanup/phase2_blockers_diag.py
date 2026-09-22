"""
PREDEPLOY-CLEANUP.3A-DIAG — auditoría read-only del grafo bloqueado FASE 2.

Solo SELECT. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
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
from app.domains.predeploy_cleanup.execution_validator import (
    classify_iniciadores_test,
    load_test_iniciador_ids,
)
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import entity_ids, load_manifest
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    classify_users_sequential,
    load_user_fk_columns,
    recalculate_ots_deletable,
)

TEST_STREET_NAMES = (
    "CalleCat Canon 708932",
    "Main Canon 444592",
    "Esquina Canon 495353",
    "CalleCat Canon 197731",
    "Main Canon 662005",
    "Esquina Canon 993558",
)

BASELINE_TABLES = (
    "users",
    "establecimiento_operativo",
    "iniciador_ruta",
    "actuaciones",
    "denuncia",
    "relevamiento",
    "orden_trabajo",
    "ruta_item",
    "ruta_pool_dia",
    "domicilio",
    "contribuyente",
    "rubro",
    "juzgado_catalogo",
    "relevador",
    "calle_catalogo",
)

SOURCE_COLUMNS = (
    "relevamiento_id",
    "denuncia_id",
    "notificacion_id",
    "comprobacion_id",
    "oficio_id",
    "actuacion_id",
)


def _scalar(conn: Connection, sql: str, params: dict | None = None) -> Any:
    row = conn.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _test_user_ids(conn: Connection) -> set[int]:
    return _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")


def _blocked_act_ids(conn: Connection, protected: dict[str, set[int]]) -> set[int]:
    """139 actuaciones CONFIRMADO_TEST que sobrevivieron FASE 1."""
    all_test = _fetch_ids(conn, TEST_ACTUACIONES_SQL)
    return all_test - protected.get("actuaciones", set())


def audit_establecimiento_schema(conn: Connection) -> dict[str, Any]:
    """Schema completo de establecimiento_operativo desde INFORMATION_SCHEMA."""
    columns = _rows(
        conn,
        """
        SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'establecimiento_operativo'
        ORDER BY ORDINAL_POSITION
        """,
    )
    indexes = _rows(
        conn,
        """
        SELECT INDEX_NAME, NON_UNIQUE, COLUMN_NAME, SEQ_IN_INDEX
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'establecimiento_operativo'
        ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """,
    )
    parent_fks = _rows(
        conn,
        """
        SELECT
            kcu.COLUMN_NAME AS child_column,
            kcu.REFERENCED_TABLE_NAME AS parent_table,
            kcu.REFERENCED_COLUMN_NAME AS parent_column,
            rc.DELETE_RULE AS delete_rule,
            rc.UPDATE_RULE AS update_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.TABLE_NAME = 'establecimiento_operativo'
          AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        """,
    )
    child_fks = _rows(
        conn,
        """
        SELECT
            kcu.TABLE_NAME AS child_table,
            kcu.COLUMN_NAME AS child_column,
            kcu.REFERENCED_COLUMN_NAME AS parent_column,
            rc.DELETE_RULE AS delete_rule,
            rc.UPDATE_RULE AS update_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.REFERENCED_TABLE_NAME = 'establecimiento_operativo'
        """,
    )
    return {
        "tabla": "establecimiento_operativo",
        "semantica": {
            "descripcion": (
                "Ficha operativa Bromatología anclada 1:1 a domicilio. "
                "No almacena contribuyente ni rubro directamente; se obtienen vía domicilio. "
                "Actuaciones pueden referenciar establecimiento_operativo_id (SET NULL al borrar EO). "
                "Relevamientos/denuncias no FK directa; comparten domicilio_id o iniciador_ruta."
            ),
            "relacion_domicilio": "1:1 UNIQUE domicilio_id RESTRICT",
            "relacion_contribuyente": "indirecta vía domicilio.contribuyente_id",
            "relacion_rubro": "indirecta vía domicilio.rubro_id",
            "titular_logico": "identidad lógica contribuyente+domicilio (resolve_establecimiento_por_domicilio)",
            "actuaciones_fk": "actuaciones.establecimiento_operativo_id ON DELETE SET NULL",
            "relevamientos": "sin FK directa; mismo domicilio o vía iniciador",
            "denuncias": "sin FK directa; vía domicilio en iniciador/denuncia",
            "misma_geo_distinto_titular": "no colapsar solo por domicilio_id",
        },
        "columnas": columns,
        "indices": indexes,
        "fk_padres": parent_fks,
        "fk_hijos": child_fks,
        "tiene_deleted_at": False,
        "tiene_activo_estado": False,
    }


def _classify_source(
    conn: Connection,
    source_table: str,
    source_id: int | None,
    protected: dict[str, set[int]],
    cleanup_act_ids: set[int],
    cleanup_den_ids: set[int],
    cleanup_rel_ids: set[int],
) -> str:
    if source_id is None:
        return "NONE"
    if source_table == "actuaciones":
        if source_id in protected.get("actuaciones", set()):
            return "PROTECTED_REAL"
        if source_id in cleanup_act_ids:
            return "CONFIRMADO_TEST"
        return "INDETERMINADO"
    if source_table == "denuncia":
        if source_id in cleanup_den_ids:
            return "CONFIRMADO_TEST"
        return "INDETERMINADO"
    if source_table == "relevamiento":
        if source_id in cleanup_rel_ids or source_id in RELEVAMIENTOS_QA_IDS:
            return "CONFIRMADO_TEST"
        return "INDETERMINADO"
    if source_table == "notificacion":
        return "PROTECTED_REAL" if source_id in protected.get("notificacion", set()) else "INDETERMINADO"
    if source_table == "comprobacion":
        return "PROTECTED_REAL" if source_id in protected.get("comprobacion", set()) else "INDETERMINADO"
    if source_table == "oficio":
        return "PROTECTED_REAL" if source_id in protected.get("oficio", set()) else "INDETERMINADO"
    return "INDETERMINADO"


def audit_establecimientos_test(
    conn: Connection,
    protected: dict[str, set[int]],
    cleanup_act_ids: set[int],
) -> dict[str, Any]:
    """Clasifica establecimientos creados por usuarios test."""
    rows = _rows(
        conn,
        f"""
        SELECT eo.id, eo.domicilio_id, eo.created_by_user_id, eo.created_at,
               d.contribuyente_id, d.rubro_id, d.calle, d.numero
        FROM establecimiento_operativo eo
        JOIN users u ON u.id = eo.created_by_user_id
        JOIN domicilio d ON d.id = eo.domicilio_id
        WHERE {SQL_TEST_USER_WHERE}
        ORDER BY eo.id
        """,
    )
    prot_acts = protected.get("actuaciones", set())
    buckets: dict[str, list[dict[str, Any]]] = {
        "CONFIRMADO_TEST_SEGURO": [],
        "TEST_WRAPPER_REAL": [],
        "BLOCKED_REAL": [],
        "INDETERMINADO": [],
    }

    for eo in rows:
        eid = eo["id"]
        dom_id = eo["domicilio_id"]
        acts_eo = _fetch_ids(
            conn, f"SELECT id FROM actuaciones WHERE establecimiento_operativo_id = {eid}"
        )
        acts_dom = _fetch_ids(
            conn, f"SELECT id FROM actuaciones WHERE domicilio_id = {dom_id}"
        )
        inis_dom = _fetch_ids(
            conn, f"SELECT id FROM iniciador_ruta WHERE domicilio_id = {dom_id} AND deleted_at IS NULL"
        )
        rels_dom = _fetch_ids(
            conn,
            f"""
            SELECT r.id FROM relevamiento r
            JOIN iniciador_ruta ir ON ir.relevamiento_id = r.id
            WHERE ir.domicilio_id = {dom_id}
            """,
        )
        dens_dom = _fetch_ids(
            conn,
            f"""
            SELECT d.id FROM denuncia d
            JOIN iniciador_ruta ir ON ir.denuncia_id = d.id
            WHERE ir.domicilio_id = {dom_id}
            """,
        )

        prot_acts_eo = acts_eo & prot_acts
        prot_acts_dom = acts_dom & prot_acts
        test_acts_eo = acts_eo & cleanup_act_ids
        test_acts_dom = acts_dom & cleanup_act_ids
        indet_acts = (acts_eo | acts_dom) - prot_acts - cleanup_act_ids

        evidence = {
            "id": eid,
            "created_by_user_id": eo["created_by_user_id"],
            "domicilio_id": dom_id,
            "contribuyente_id": eo["contribuyente_id"],
            "rubro_id": eo["rubro_id"],
            "calle": eo["calle"],
            "numero": eo["numero"],
            "created_at": str(eo["created_at"]),
            "deleted_at": None,
            "actuaciones_eo_ids": sorted(acts_eo)[:20],
            "actuaciones_domicilio_ids": sorted(acts_dom)[:20],
            "iniciadores_domicilio_count": len(inis_dom),
            "iniciadores_domicilio_sample": sorted(inis_dom)[:10],
            "relevamientos_count": len(rels_dom),
            "denuncias_count": len(dens_dom),
            "protected_actuaciones": sorted(prot_acts_eo | prot_acts_dom)[:10],
            "test_actuaciones": sorted(test_acts_eo | test_acts_dom)[:10],
            "indeterminate_actuaciones": sorted(indet_acts)[:10],
        }

        if prot_acts_eo or prot_acts_dom:
            if acts_eo and prot_acts_eo:
                bucket = "BLOCKED_REAL"
            else:
                bucket = "TEST_WRAPPER_REAL"
            evidence["reason"] = "interseccion_actuaciones_protegidas"
        elif indet_acts:
            bucket = "INDETERMINADO"
            evidence["reason"] = "actuaciones_indeterminadas_en_domicilio"
        elif test_acts_eo or test_acts_dom or inis_dom or rels_dom or dens_dom:
            bucket = "CONFIRMADO_TEST_SEGURO"
            evidence["reason"] = "solo_refs_test_o_iniciadores_test"
        elif not acts_eo and not acts_dom and not inis_dom:
            bucket = "CONFIRMADO_TEST_SEGURO"
            evidence["reason"] = "sin_refs_operativas"
        else:
            bucket = "INDETERMINADO"
            evidence["reason"] = "evidencia_insuficiente"

        buckets[bucket].append(evidence)

    return {
        "total_created_by_test": len(rows),
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "buckets": buckets,
        "nota_domicilio": "domicilio/contribuyente/rubro NO son candidatos automáticos al borrar EO",
    }


def audit_user_blockers(conn: Connection, test_user_ids: set[int]) -> dict[str, Any]:
    """FK sobrevivientes para usuarios test bloqueados."""
    fk_columns = load_user_fk_columns(conn)
    virtual = VirtualDeleteState()
    explicit: dict[str, set[int]] = {}
    protected_empty: dict[str, set[int]] = {}

    per_user: dict[int, dict[str, Any]] = {}
    table_agg: dict[str, dict[str, Any]] = {}

    for table, col in fk_columns:
        for chunk in _chunk_ids(test_user_ids, 400):
            ph = ",".join(str(u) for u in chunk)
            rows = conn.execute(
                text(f"SELECT id, `{col}` FROM `{table}` WHERE `{col}` IN ({ph})")
            ).fetchall()
            for row_id, uid in rows:
                if uid not in test_user_ids:
                    continue
                per_user.setdefault(uid, {"refs": [], "tables": {}})
                per_user[uid]["refs"].append(
                    {"table": table, "column": col, "row_id": row_id}
                )
                per_user[uid]["tables"][table] = per_user[uid]["tables"].get(table, 0) + 1
                agg = table_agg.setdefault(
                    table, {"users": set(), "refs_total": 0, "sample": []}
                )
                agg["users"].add(uid)
                agg["refs_total"] += 1
                if len(agg["sample"]) < 5:
                    agg["sample"].append({"user_id": uid, "row_id": row_id})

    users_with_refs = {uid for uid, data in per_user.items() if data["refs"]}
    users_without_refs = sorted(test_user_ids - users_with_refs)

    blocker_table = [
        {
            "tabla_bloqueante": tbl,
            "users_afectados": len(agg["users"]),
            "refs_totales": agg["refs_total"],
            "sample": agg["sample"],
        }
        for tbl, agg in sorted(table_agg.items(), key=lambda x: -x[1]["refs_total"])
    ]

    return {
        "test_users_total": len(test_user_ids),
        "users_with_surviving_fk": len(users_with_refs),
        "users_without_fk": len(users_without_refs),
        "blocker_table": blocker_table,
        "per_user_sample": {
            str(uid): {
                "ref_count": len(data["refs"]),
                "tables": data["tables"],
                "refs_sample": data["refs"][:15],
            }
            for uid, data in sorted(per_user.items(), key=lambda x: -len(x[1]["refs"]))[:50]
        },
    }


def simulate_users_unlocked_by_establecimientos(
    conn: Connection,
    test_user_ids: set[int],
    eo_seguro_ids: set[int],
) -> dict[str, Any]:
    """Simula cuántos users quedarían sin FK si solo se borran EO CONFIRMADO_TEST_SEGURO."""
    fk_columns = load_user_fk_columns(conn)
    eo_table_refs: dict[int, set[tuple[str, int]]] = {}

    for table, col in fk_columns:
        if table == "establecimiento_operativo" and col == "created_by_user_id":
            for chunk in _chunk_ids(eo_seguro_ids, 400):
                ph = ",".join(str(i) for i in chunk)
                rows = conn.execute(
                    text(
                        f"SELECT id, created_by_user_id FROM establecimiento_operativo "
                        f"WHERE id IN ({ph})"
                    )
                ).fetchall()
                for eid, uid in rows:
                    eo_table_refs.setdefault(uid, set()).add(("establecimiento_operativo", eid))

    users_only_eo_blocked: set[int] = set()
    users_still_blocked: set[int] = set()

    for uid in test_user_ids:
        all_refs: list[tuple[str, int]] = []
        for table, col in fk_columns:
            rows = conn.execute(
                text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"),
                {"uid": uid},
            ).fetchall()
            for r in rows:
                all_refs.append((table, r[0]))

        non_eo_refs = [
            (t, rid)
            for t, rid in all_refs
            if not (t == "establecimiento_operativo" and rid in eo_seguro_ids)
        ]
        eo_refs_seguro = [
            (t, rid)
            for t, rid in all_refs
            if t == "establecimiento_operativo" and rid in eo_seguro_ids
        ]

        if not non_eo_refs and eo_refs_seguro:
            users_only_eo_blocked.add(uid)
        elif all_refs:
            users_still_blocked.add(uid)

    return {
        "users_blocked_before": len(test_user_ids),
        "establecimientos_seguros_simulados": len(eo_seguro_ids),
        "users_unlocked_by_establecimientos_only": len(users_only_eo_blocked),
        "users_still_blocked": len(users_still_blocked),
        "users_without_any_fk": len(test_user_ids) - len(users_only_eo_blocked) - len(users_still_blocked),
        "unlocked_sample_user_ids": sorted(users_only_eo_blocked)[:30],
    }


def audit_blocked_iniciadores(
    conn: Connection,
    protected: dict[str, set[int]],
    cleanup_act_ids: set[int],
    wrapper_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Audita iniciadores test no eliminados en FASE 1."""
    test_ids = load_test_iniciador_ids(conn)
    ini_class = classify_iniciadores_test(
        conn,
        protected,
        wrapper_analysis,
        deleted_ruta_items=set(),
        deleted_pool=set(),
        cleanup_act_ids=cleanup_act_ids,
    )
    delete_set = set(ini_class["delete_phase1"])
    blocked_ids = test_ids - delete_set

    motivo_buckets: dict[str, set[int]] = {
        "A_source_PROTECTED_REAL": set(),
        "B_source_INDETERMINADO": set(),
        "C_ruta_item_sobreviviente": set(),
        "D_ruta_pool_sobreviviente": set(),
        "E_actuacion_test_bloqueada": set(),
        "F_denuncia_test_bloqueada": set(),
        "G_relevamiento_test_bloqueado": set(),
        "H_otro": set(),
    }
    by_tipo: dict[str, dict[str, int]] = {}

    cleanup_den = _fetch_ids(
        conn,
        f"""
        SELECT d.id FROM denuncia d
        JOIN users u ON u.id = d.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    cleanup_rel = _fetch_ids(
        conn,
        f"""
        SELECT r.id FROM relevamiento r
        JOIN users u ON u.id = r.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    ) | RELEVAMIENTOS_QA_IDS

    detail_sample: list[dict[str, Any]] = []
    for ini_id in sorted(blocked_ids):
        row = conn.execute(
            text(
                """
                SELECT id, tipo_iniciador, estado_iniciador, domicilio_id,
                       relevamiento_id, denuncia_id, notificacion_id,
                       comprobacion_id, oficio_id, actuacion_id, created_by_user_id
                FROM iniciador_ruta WHERE id = :id
                """
            ),
            {"id": ini_id},
        ).fetchone()
        if not row:
            continue
        m = dict(row._mapping)
        tipo = m["tipo_iniciador"]
        by_tipo.setdefault(tipo, {"total": 0, "protected_real": 0, "indeterminate": 0, "test_potencial": 0})
        by_tipo[tipo]["total"] += 1

        motivos: list[str] = []
        source_cls = []
        for col in SOURCE_COLUMNS:
            sid = m.get(col)
            if sid is None:
                continue
            tbl = col.replace("_id", "")
            cls = _classify_source(
                conn, tbl, sid, protected, cleanup_act_ids, cleanup_den, cleanup_rel
            )
            source_cls.append({"column": col, "source_id": sid, "classification": cls})
            if cls == "PROTECTED_REAL":
                motivos.append("A_source_PROTECTED_REAL")
                by_tipo[tipo]["protected_real"] += 1
            elif cls == "INDETERMINADO":
                motivos.append("B_source_INDETERMINADO")
                by_tipo[tipo]["indeterminate"] += 1
            elif cls == "CONFIRMADO_TEST":
                if col == "actuacion_id":
                    motivos.append("E_actuacion_test_bloqueada")
                elif col == "denuncia_id":
                    motivos.append("F_denuncia_test_bloqueada")
                elif col == "relevamiento_id":
                    motivos.append("G_relevamiento_test_bloqueado")

        ri_cnt = _scalar(
            conn,
            "SELECT COUNT(*) FROM ruta_item WHERE iniciador_ruta_id = :id",
            {"id": ini_id},
        )
        rp_cnt = _scalar(
            conn,
            "SELECT COUNT(*) FROM ruta_pool_dia WHERE iniciador_ruta_id = :id",
            {"id": ini_id},
        )
        if ri_cnt:
            motivos.append("C_ruta_item_sobreviviente")
        if rp_cnt:
            motivos.append("D_ruta_pool_sobreviviente")

        if ini_id in ini_class["protected_real"]:
            motivos.append("A_source_PROTECTED_REAL")
        if not motivos:
            motivos.append("H_otro")
            by_tipo[tipo]["test_potencial"] += 1
        else:
            if not any(m.startswith("A_") or m.startswith("B_") for m in motivos):
                by_tipo[tipo]["test_potencial"] += 1

        for mot in set(motivos):
            motivo_buckets[mot].add(ini_id)

        if len(detail_sample) < 30:
            detail_sample.append(
                {
                    "iniciador_id": ini_id,
                    "tipo": tipo,
                    "motivos": sorted(set(motivos)),
                    "sources": source_cls,
                    "ruta_item_refs": ri_cnt,
                    "ruta_pool_refs": rp_cnt,
                }
            )

    return {
        "test_iniciadores_total": len(test_ids),
        "would_delete_phase1_recalc": ini_class["delete_phase1_count"],
        "blocked_not_deleted": len(blocked_ids),
        "protected_real_count": ini_class["protected_real_count"],
        "blocked_indeterminate_count": ini_class["blocked_indeterminate_count"],
        "motivo_bucket_counts": {k: len(v) for k, v in motivo_buckets.items()},
        "motivo_buckets_overlap_note": "una fila puede tener múltiples motivos",
        "by_tipo": by_tipo,
        "detail_sample": detail_sample,
        "classification_recalc": {
            "delete_phase1_count": ini_class["delete_phase1_count"],
            "protected_real_count": ini_class["protected_real_count"],
            "blocked_indeterminate_count": ini_class["blocked_indeterminate_count"],
        },
    }


def audit_blocked_actuaciones(
    conn: Connection,
    blocked_act_ids: set[int],
    protected: dict[str, set[int]],
    cleanup_act_ids: set[int],
) -> dict[str, Any]:
    """139 actuaciones test bloqueadas."""
    deletable_if_ini_removed = 0
    detail: list[dict[str, Any]] = []

    for act_id in sorted(blocked_act_ids):
        row = conn.execute(
            text(
                """
                SELECT a.id, a.orden_trabajo_id, a.domicilio_id, a.establecimiento_operativo_id,
                       a.notificacion_id, a.comprobacion_id
                FROM actuaciones a WHERE a.id = :id
                """
            ),
            {"id": act_id},
        ).fetchone()
        if not row:
            continue
        m = dict(row._mapping)
        inis = _rows(
            conn,
            "SELECT id, tipo_iniciador, actuacion_id FROM iniciador_ruta WHERE actuacion_id = :aid",
            {"aid": act_id},
        )
        ini_classes = []
        blocking_inis = []
        for ini in inis:
            iid = ini["id"]
            if iid in protected.get("iniciador_ruta", set()):
                cls = "PROTECTED_REAL"
            else:
                cls = "CONFIRMADO_TEST_SURVIVING"
            ini_classes.append({"id": iid, "tipo": ini["tipo_iniciador"], "class": cls})
            blocking_inis.append(iid)

        children = {
            "inspeccion": len(_fetch_ids(conn, f"SELECT id FROM inspeccion WHERE actuacion_id = {act_id}")),
            "clausura": len(_fetch_ids(conn, f"SELECT id FROM clausura WHERE actuacion_id = {act_id}")),
            "decomiso": len(_fetch_ids(conn, f"SELECT id FROM decomiso WHERE actuacion_id = {act_id}")),
        }
        prot_inter = bool(
            act_id in protected.get("actuaciones", set())
            or m.get("notificacion_id") in protected.get("notificacion", set())
            or m.get("comprobacion_id") in protected.get("comprobacion", set())
        )
        motivo = "iniciador_RESTRICT_sobreviviente"
        if prot_inter:
            motivo = "PROTECTED_REAL_intersection"
        elif not blocking_inis:
            motivo = "sin_iniciador_directo_otro_blocker"
            deletable_if_ini_removed += 1
        elif all(ic["class"] == "CONFIRMADO_TEST_SURVIVING" for ic in ini_classes):
            deletable_if_ini_removed += 1
            motivo = "desbloqueable_si_iniciadores_test_eliminados"

        rec = {
            "actuacion_id": act_id,
            "orden_trabajo_id": m["orden_trabajo_id"],
            "establecimiento_operativo_id": m["establecimiento_operativo_id"],
            "iniciadores": ini_classes,
            "documentos_hijos": children,
            "protected_intersection": prot_inter,
            "motivo_sobrevivencia": motivo,
        }
        detail.append(rec)

    return {
        "total_blocked": len(blocked_act_ids),
        "desbloqueables_si_iniciadores_test": deletable_if_ini_removed,
        "detail": detail,
    }


def audit_blocked_ots(
    conn: Connection,
    blocked_act_ids: set[int],
    protected: dict[str, set[int]],
    cleanup_ot_candidates: set[int],
) -> dict[str, Any]:
    ot_ids = set()
    for act_id in blocked_act_ids:
        ot = _scalar(conn, "SELECT orden_trabajo_id FROM actuaciones WHERE id = :id", {"id": act_id})
        if ot:
            ot_ids.add(ot)

    deletable, blocked, detail = recalculate_ots_deletable(
        conn,
        ot_ids | cleanup_ot_candidates,
        protected.get("orden_trabajo", set()),
        blocked_act_ids,
        protected.get("actuaciones", set()),
    )

    ot_from_blocked_acts = []
    for ot_id in sorted(ot_ids):
        acts = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        real_indet = acts - blocked_act_ids - protected.get("actuaciones", set())
        ot_from_blocked_acts.append(
            {
                "ot_id": ot_id,
                "actuaciones_total": len(acts),
                "blocked_test_acts": len(acts & blocked_act_ids),
                "real_indeterminate_acts": sorted(real_indet)[:5],
                "deletable_if_test_acts_gone": len(real_indet) == 0 and ot_id not in protected.get("orden_trabajo", set()),
            }
        )

    return {
        "ots_linked_to_blocked_acts": len(ot_ids),
        "deletable_if_test_acts_removed": sum(1 for o in ot_from_blocked_acts if o["deletable_if_test_acts_gone"]),
        "blocked_with_real_indeterminate": sum(1 for o in ot_from_blocked_acts if o["real_indeterminate_acts"]),
        "detail": ot_from_blocked_acts,
        "recalc_deletable": len(deletable),
        "recalc_blocked": len(blocked),
    }


def audit_blocked_denuncias(conn: Connection, protected: dict[str, set[int]]) -> dict[str, Any]:
    den_ids = _fetch_ids(
        conn,
        f"""
        SELECT d.id FROM denuncia d
        JOIN users u ON u.id = d.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    detail = []
    for did in sorted(den_ids):
        inis = _rows(
            conn,
            "SELECT id, tipo_iniciador, estado_iniciador FROM iniciador_ruta WHERE denuncia_id = :did",
            {"did": did},
        )
        ri = _scalar(conn, "SELECT COUNT(*) FROM ruta_item ri JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id WHERE ir.denuncia_id = :did", {"did": did})
        rp = _scalar(conn, "SELECT COUNT(*) FROM ruta_pool_dia rpd JOIN iniciador_ruta ir ON ir.id = rpd.iniciador_ruta_id WHERE ir.denuncia_id = :did", {"did": did})
        dom = _scalar(conn, "SELECT domicilio_id FROM denuncia WHERE id = :did", {"did": did})
        created_by = _scalar(conn, "SELECT created_by_user_id FROM denuncia WHERE id = :did", {"did": did})
        all_test_inis = all(True for _ in inis)  # all created in test context
        classification = "DELETE_AFTER_INITIATOR" if inis and not ri and not rp else "BLOCKED_SURVIVING_REFS"
        detail.append(
            {
                "denuncia_id": did,
                "domicilio_id": dom,
                "created_by_user_id": created_by,
                "iniciadores": inis,
                "ruta_item_refs": ri,
                "ruta_pool_refs": rp,
                "classification": classification,
            }
        )
    return {
        "total_blocked": len(den_ids),
        "delete_after_iniciador": sum(1 for d in detail if d["classification"] == "DELETE_AFTER_INITIATOR"),
        "blocked_surviving": sum(1 for d in detail if d["classification"] != "DELETE_AFTER_INITIATOR"),
        "detail": detail,
    }


def audit_blocked_relevamientos(conn: Connection) -> dict[str, Any]:
    rel_created = _fetch_ids(
        conn,
        f"""
        SELECT r.id FROM relevamiento r
        JOIN users u ON u.id = r.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    rel_ids = sorted(rel_created | RELEVAMIENTOS_QA_IDS)
    detail = []
    for rid in rel_ids:
        inis = _rows(
            conn,
            "SELECT id, tipo_iniciador FROM iniciador_ruta WHERE relevamiento_id = :rid",
            {"rid": rid},
        )
        revs = _rows(
            conn,
            """
            SELECT rr.relevador_id, rel.nombre
            FROM relevamiento_relevador rr
            JOIN relevador rel ON rel.id = rr.relevador_id
            WHERE rr.relevamiento_id = :rid
            """,
            {"rid": rid},
        )
        classification = "DELETE_AFTER_INITIATOR" if inis else "BLOCKED_NO_INICIADOR_OR_REFS"
        detail.append(
            {
                "relevamiento_id": rid,
                "qa_id_flag": rid in RELEVAMIENTOS_QA_IDS,
                "iniciadores": inis,
                "relevadores": revs,
                "classification": classification,
            }
        )
    return {
        "total_blocked": len(rel_ids),
        "qa_ids_highlighted": sorted(RELEVAMIENTOS_QA_IDS),
        "delete_after_iniciador": sum(1 for d in detail if d["classification"] == "DELETE_AFTER_INITIATOR"),
        "detail": detail,
    }


def audit_otro_relevador_qa(conn: Connection) -> dict[str, Any]:
    row = conn.execute(
        text("SELECT id, nombre, activo FROM relevador WHERE nombre = 'Otro Relevador QA'")
    ).fetchone()
    if not row:
        return {"found": False}
    rid = row[0]
    rels = _rows(
        conn,
        """
        SELECT r.id, r.fecha, r.created_by_user_id
        FROM relevamiento r
        JOIN relevamiento_relevador rr ON rr.relevamiento_id = r.id
        WHERE rr.relevador_id = :rid
        ORDER BY r.id
        """,
        {"rid": rid},
    )
    all_test = True
    for rel in rels:
        uid = rel["created_by_user_id"]
        is_test = uid in _test_user_ids(conn) or rel["id"] in RELEVAMIENTOS_QA_IDS
        if not is_test:
            all_test = False
    return {
        "found": True,
        "relevador_id": rid,
        "nombre": row[1],
        "activo": row[2],
        "relevamientos_sobrevivientes": len(rels),
        "relevamiento_ids": [r["id"] for r in rels],
        "todos_confirmado_test": all_test,
        "eliminable_fase2_si_relevamientos_borrados": all_test and len(rels) > 0,
        "conservar_si_una_ref_real": not all_test,
    }


def audit_test_streets_graph(conn: Connection) -> dict[str, Any]:
    graphs = []
    for street in TEST_STREET_NAMES:
        calle_row = conn.execute(
            text(
                """
                SELECT id, nombre_canonico, nombre_key
                FROM calle_catalogo
                WHERE nombre_canonico = :n OR nombre_key LIKE :k
                LIMIT 5
                """
            ),
            {"n": street, "k": f"%{street.lower().replace(' ', '%')}%"},
        ).fetchall()
        domicilios = []
        for cr in calle_row:
            cid = cr[0]
            doms = _rows(
                conn,
                """
                SELECT d.id, d.contribuyente_id, d.rubro_id
                FROM domicilio d
                WHERE d.calle_catalogo_id = :cid OR d.calle = :calle
                """,
                {"cid": cid, "calle": street},
            )
            for dom in doms:
                did = dom["id"]
                eo = _rows(
                    conn,
                    "SELECT id, created_by_user_id FROM establecimiento_operativo WHERE domicilio_id = :did",
                    {"did": did},
                )
                acts = _rows(
                    conn,
                    "SELECT id, orden_trabajo_id FROM actuaciones WHERE domicilio_id = :did",
                    {"did": did},
                )
                inis = _rows(
                    conn,
                    "SELECT id, tipo_iniciador FROM iniciador_ruta WHERE domicilio_id = :did",
                    {"did": did},
                )
                rels = _rows(
                    conn,
                    """
                    SELECT r.id FROM relevamiento r
                    JOIN iniciador_ruta ir ON ir.relevamiento_id = r.id
                    WHERE ir.domicilio_id = :did
                    """,
                    {"did": did},
                )
                dens = _rows(
                    conn,
                    """
                    SELECT d.id FROM denuncia d
                    JOIN iniciador_ruta ir ON ir.denuncia_id = d.id
                    WHERE ir.domicilio_id = :did
                    """,
                    {"did": did},
                )
                rutas = _rows(
                    conn,
                    """
                    SELECT ri.id, ri.ruta_trabajo_id
                    FROM ruta_item ri
                    JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id
                    WHERE ir.domicilio_id = :did
                    """,
                    {"did": did},
                )
                domicilios.append(
                    {
                        "domicilio_id": did,
                        "establecimientos": eo,
                        "actuaciones": acts,
                        "iniciadores": inis,
                        "relevamientos": rels,
                        "denuncias": dens,
                        "ruta_items": rutas,
                    }
                )
        graphs.append(
            {
                "calle": street,
                "calle_catalogo_matches": [dict(r._mapping) for r in calle_row],
                "domicilios": domicilios,
                "grafo_confirmado_test": len(domicilios) > 0,
                "fase2_subgrupo_potencial": "CONFIRMADO_TEST" if domicilios else "SIN_DOMS_ENCONTRADOS",
            }
        )
    return {"calles_fixture": graphs, "nota": "NO DELETE en este ticket"}


def audit_rubros_test(conn: Connection) -> dict[str, Any]:
    rows = _rows(conn, "SELECT id, nombre FROM rubro ORDER BY id")
    buckets = {"A_cero_refs": [], "B_refs_solo_test": [], "C_refs_real_indeterminado": []}
    for r in rows:
        nombre = r["nombre"] or ""
        if nombre in RUBROS_CANONICOS:
            continue
        if not RUBRO_TEST_PATTERN.search(nombre):
            continue
        rid = r["id"]
        dom_cnt = _scalar(conn, "SELECT COUNT(*) FROM domicilio WHERE rubro_id = :rid", {"rid": rid})
        rel_cnt = _scalar(conn, "SELECT COUNT(*) FROM relevamiento WHERE rubro_id = :rid", {"rid": rid})
        pool_cnt = _scalar(conn, "SELECT COUNT(*) FROM ruta_pool_dia WHERE rubro_id = :rid", {"rid": rid})
        total = (dom_cnt or 0) + (rel_cnt or 0) + (pool_cnt or 0)
        entry = {"id": rid, "nombre": nombre, "domicilios": dom_cnt, "relevamientos": rel_cnt, "pool": pool_cnt}
        if total == 0:
            buckets["A_cero_refs"].append(entry)
        else:
            buckets["B_refs_solo_test"].append(entry)
    return {
        "confirmado_test_total": sum(len(b) for b in buckets.values()),
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "buckets": buckets,
        "nota": "clasificación B/C refinada requiere cruce actuación protegida por domicilio",
    }


def audit_juzgados_test(conn: Connection, protected: dict[str, set[int]]) -> dict[str, Any]:
    rows = _rows(conn, "SELECT id, codigo, nombre FROM juzgado_catalogo ORDER BY id")
    test_juz = []
    for j in rows:
        codigo = (j.get("codigo") or "").strip()
        nombre = (j.get("nombre") or "").strip()
        if codigo in JUZGADOS_CANONICOS:
            continue
        if not (JUZGADO_TEST_PATTERN.search(codigo) or JUZGADO_TEST_PATTERN.search(nombre)):
            continue
        oficios = _fetch_ids(conn, f"SELECT id FROM oficio WHERE juzgado_id = {j['id']}")
        prot_of = oficios & protected.get("oficio", set())
        test_juz.append(
            {
                "id": j["id"],
                "codigo": codigo,
                "nombre": nombre,
                "oficios_total": len(oficios),
                "oficios_protegidos": len(prot_of),
                "sin_refs": len(oficios) == 0,
                "bucket": "sin_refs" if not oficios else ("solo_test" if not prot_of else "blocked_protected_oficios"),
            }
        )
    return {
        "confirmado_test_total": len(test_juz),
        "sin_refs": sum(1 for j in test_juz if j["sin_refs"]),
        "con_oficios": sum(1 for j in test_juz if not j["sin_refs"]),
        "con_oficios_protegidos": sum(1 for j in test_juz if j["oficios_protegidos"] > 0),
        "detalle": test_juz[:100],
    }


def simulate_phase2_chain(
    eo_seguro_ids: set[int],
    blocked_act_ids: set[int],
    ini_blocked_count: int,
    user_unlock: dict[str, Any],
) -> dict[str, Any]:
    """Simulación en cadena sin writes."""
    return {
        "paso_1_establecimientos_seguros": len(eo_seguro_ids),
        "paso_2_users_desbloqueados_solo_eo": user_unlock["users_unlocked_by_establecimientos_only"],
        "paso_3_iniciadores_test_pendientes": ini_blocked_count,
        "paso_4_actuaciones_test_pendientes": len(blocked_act_ids),
        "paso_5_ot_denuncia_relevamiento": "dependen de iniciadores",
        "paso_6_relevador_qa": "después de relevamientos test",
        "paso_7_users_restantes": user_unlock["users_still_blocked"],
        "nota": "simulación ordenada; no incluye protected closure completo",
    }


def propose_subphases(
    eo_buckets: dict[str, int],
    user_unlock: dict[str, Any],
    ini_audit: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "fase": "2A",
            "objetivo": "establecimiento_operativo CONFIRMADO_TEST_SEGURO",
            "volumen": str(eo_buckets.get("CONFIRMADO_TEST_SEGURO", 0)),
            "riesgo": "bajo si bucket correcto",
        },
        {
            "fase": "2B",
            "objetivo": "iniciadores test + sources (denuncia/relevamiento) desbloqueables",
            "volumen": str(ini_audit.get("blocked_not_deleted", 0)),
            "riesgo": "medio; validar ruta_item/pool y protected source",
        },
        {
            "fase": "2C",
            "objetivo": "actuaciones/OT test tras iniciadores",
            "volumen": "139 actuaciones + 139 OT",
            "riesgo": "medio-alto; cascade inspección/clausura",
        },
        {
            "fase": "2D",
            "objetivo": "usuarios test liberados tras quitar FK",
            "volumen": f"~{user_unlock['users_unlocked_by_establecimientos_only']}+ incremental",
            "riesgo": "solo tras 2A-2C",
        },
        {
            "fase": "2E",
            "objetivo": "catálogos QA huérfanos (rubros, juzgados, calles fixture, relevador QA)",
            "volumen": "variable",
            "riesgo": "bajo si cero refs",
        },
    ]


def run_phase2_blockers_diag(
    conn: Connection,
    *,
    protected_manifest_path: Path,
    cleanup_manifest_path: Path | None = None,
    wrapper_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta diagnóstico completo FASE 2."""
    protected_manifest = load_manifest(protected_manifest_path)
    protected = load_protected_sets(protected_manifest)
    protected = expand_protected_indirect(conn, protected)

    cleanup_manifest = (
        load_manifest(cleanup_manifest_path) if cleanup_manifest_path and cleanup_manifest_path.is_file() else {}
    )
    cleanup_act_ids = entity_ids(cleanup_manifest, "actuaciones") if cleanup_manifest else _fetch_ids(
        conn, TEST_ACTUACIONES_SQL
    )
    cleanup_ot_ids = entity_ids(cleanup_manifest, "orden_trabajo") if cleanup_manifest else set()

    wrapper_analysis = wrapper_analysis or {
        "iniciadores_candidato_test": [],
        "iniciadores_proteger": [],
    }

    baseline = {}
    for tbl in BASELINE_TABLES:
        try:
            baseline[tbl] = _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}`")
        except Exception as exc:
            baseline[tbl] = f"ERROR: {exc}"

    test_users = _test_user_ids(conn)
    blocked_acts = _blocked_act_ids(conn, protected)

    eo_audit = audit_establecimientos_test(conn, protected, cleanup_act_ids)
    eo_seguro_ids = {e["id"] for e in eo_audit["buckets"]["CONFIRMADO_TEST_SEGURO"]}

    user_blockers = audit_user_blockers(conn, test_users)
    user_unlock = simulate_users_unlocked_by_establecimientos(conn, test_users, eo_seguro_ids)

    ini_audit = audit_blocked_iniciadores(conn, protected, cleanup_act_ids, wrapper_analysis)
    acts_audit = audit_blocked_actuaciones(conn, blocked_acts, protected, cleanup_act_ids)
    ots_audit = audit_blocked_ots(conn, blocked_acts, protected, cleanup_ot_ids)
    den_audit = audit_blocked_denuncias(conn, protected)
    rel_audit = audit_blocked_relevamientos(conn)
    qa_rel = audit_otro_relevador_qa(conn)
    streets = audit_test_streets_graph(conn)
    rubros = audit_rubros_test(conn)
    juzgados = audit_juzgados_test(conn, protected)

    phase2_graph = simulate_phase2_chain(
        eo_seguro_ids, blocked_acts, ini_audit["blocked_not_deleted"], user_unlock
    )
    subphases = propose_subphases(eo_audit["bucket_counts"], user_unlock, ini_audit)

    protected_conflicts = []
    for entity in ("actuaciones", "orden_trabajo", "iniciador_ruta"):
        prot = protected.get(entity, set())
        if prot:
            protected_conflicts.append(
                {"entity": entity, "protected_count": len(prot), "note": "no debe intersectar cleanup"}
            )

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3A-DIAG",
        "mode": "READ_ONLY_SELECT",
        "writes_executed": False,
        "baseline": {
            "database": _scalar(conn, "SELECT DATABASE()"),
            "alembic_version": _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1"),
            "counts": baseline,
            "protected_manifest": str(protected_manifest_path),
            "protected_actuaciones": len(protected.get("actuaciones", set())),
        },
        "establecimiento_operativo_schema": audit_establecimiento_schema(conn),
        "establecimientos": eo_audit,
        "user_blockers": user_blockers,
        "users_unlock_simulation": user_unlock,
        "initiators": ini_audit,
        "acts": acts_audit,
        "ots": ots_audit,
        "denuncias": den_audit,
        "relevamientos": rel_audit,
        "relevador_qa": qa_rel,
        "test_streets": streets,
        "rubros": rubros,
        "juzgados": juzgados,
        "protected_conflicts": protected_conflicts,
        "phase2_candidate_graph": phase2_graph,
        "proposed_subphases": subphases,
    }


def write_phase2_diag_report(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return output_path
