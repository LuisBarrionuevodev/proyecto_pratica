"""Simulación secuencial FASE 1: deletes virtuales, CASCADE closure y users."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import RELEVAMIENTOS_QA_IDS

ENTITY_TABLE: dict[str, str] = {
    "actuaciones": "actuaciones",
    "users": "users",
    "ruta_trabajo": "ruta_trabajo",
    "ruta_grupo": "ruta_grupo",
    "ruta_grupo_inspector": "ruta_grupo_inspector",
    "ruta_item": "ruta_item",
    "ruta_pool_dia": "ruta_pool_dia",
    "denuncia": "denuncia",
    "relevamiento": "relevamiento",
    "orden_trabajo": "orden_trabajo",
    "juzgado_catalogo": "juzgado_catalogo",
    "rubro": "rubro",
    "relevador": "relevador",
    "inspeccion": "inspeccion",
    "notificacion": "notificacion",
    "comprobacion": "comprobacion",
    "oficio": "oficio",
    "expediente": "expediente",
    "iniciador_ruta": "iniciador_ruta",
}

PROTECTED_ENTITIES_CHECK = (
    "actuaciones",
    "orden_trabajo",
    "inspeccion",
    "notificacion",
    "comprobacion",
    "oficio",
    "expediente",
)

SUMMARY_ENTITIES = (
    "users",
    "actuaciones",
    "ruta_trabajo",
    "ruta_item",
    "iniciador_ruta",
    "denuncia",
    "relevamiento",
    "orden_trabajo",
    "relevador",
    "rubro",
    "juzgado_catalogo",
)


@dataclass
class VirtualDeleteState:
    """Estado virtual de filas eliminadas por tabla."""

    explicit: dict[str, set[int]] = field(default_factory=dict)
    cascade: dict[str, set[int]] = field(default_factory=dict)

    def all_deleted(self, table: str) -> set[int]:
        return self.explicit.get(table, set()) | self.cascade.get(table, set())

    def add_explicit(self, table: str, ids: set[int]) -> None:
        if ids:
            self.explicit.setdefault(table, set()).update(ids)

    def add_cascade(self, table: str, ids: set[int]) -> None:
        if ids:
            self.cascade.setdefault(table, set()).update(ids)


def _chunk_ids(ids: set[int], size: int = 400) -> list[list[int]]:
    s = sorted(ids)
    return [s[i : i + size] for i in range(0, len(s), size)]


def _fetch_ids(conn: Connection, sql: str, params: dict | None = None) -> set[int]:
    return {row[0] for row in conn.execute(text(sql), params or {})}


def _table_for_entity(entity: str) -> str:
    return ENTITY_TABLE.get(entity, entity)


def _entity_for_table(table: str) -> str | None:
    for ent, tbl in ENTITY_TABLE.items():
        if tbl == table:
            return ent
    return None


def load_user_fk_columns(conn: Connection) -> list[tuple[str, str]]:
    rows = conn.execute(
        text(
            """
            SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE kcu
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.REFERENCED_TABLE_NAME = 'users'
              AND kcu.REFERENCED_COLUMN_NAME = 'id'
            """
        )
    ).fetchall()
    return [(r[0], r[1]) for r in rows if r[0] != "users"]


def cascade_children_of_actuaciones(conn: Connection, act_ids: set[int]) -> dict[str, set[int]]:
    """Hijos CASCADE al borrar actuaciones (por FK real)."""
    if not act_ids:
        return {}
    result: dict[str, set[int]] = {}
    for chunk in _chunk_ids(act_ids):
        ph = ",".join(str(i) for i in chunk)
        result.setdefault("inspeccion", set()).update(
            _fetch_ids(conn, f"SELECT id FROM inspeccion WHERE actuacion_id IN ({ph})")
        )
        result.setdefault("clausura", set()).update(
            _fetch_ids(conn, f"SELECT id FROM clausura WHERE actuacion_id IN ({ph})")
        )
        result.setdefault("decomiso", set()).update(
            _fetch_ids(conn, f"SELECT id FROM decomiso WHERE actuacion_id IN ({ph})")
        )
        result.setdefault("actuaciones_inspector", set()).update(
            _fetch_ids(
                conn,
                f"SELECT actuaciones_id FROM actuaciones_inspector WHERE actuaciones_id IN ({ph})",
            )
        )
    insp = result.get("inspeccion", set())
    if insp:
        for chunk in _chunk_ids(insp):
            ph = ",".join(str(i) for i in chunk)
            # PK compuesta: usar acta_inspeccion_id (= inspeccion.id) como proxy
            result.setdefault("acta_inspeccion_item", set()).update(
                _fetch_ids(
                    conn,
                    f"SELECT DISTINCT acta_inspeccion_id FROM acta_inspeccion_item WHERE acta_inspeccion_id IN ({ph})",
                )
            )
    return result


def cascade_children_of_relevamiento(conn: Connection, rel_ids: set[int]) -> dict[str, set[int]]:
    if not rel_ids:
        return {}
    result: dict[str, set[int]] = {}
    for chunk in _chunk_ids(rel_ids):
        ph = ",".join(str(i) for i in chunk)
        result.setdefault("relevamiento_relevador", set()).update(
            _fetch_ids(
                conn,
                f"SELECT relevamiento_id FROM relevamiento_relevador WHERE relevamiento_id IN ({ph})",
            )
        )
    return result


def _row_will_be_deleted(
    table: str,
    row_id: int,
    virtual: VirtualDeleteState,
    explicit_by_entity: dict[str, set[int]],
) -> bool:
    if row_id in virtual.all_deleted(table):
        return True
    ent = _entity_for_table(table)
    if ent and row_id in explicit_by_entity.get(ent, set()):
        return True
    return False


def _row_is_protected(
    table: str,
    row_id: int,
    protected_all: dict[str, set[int]],
) -> bool:
    ent = _entity_for_table(table)
    if ent and row_id in protected_all.get(ent, set()):
        return True
    return False


def _surviving_user_ids_for_fk(
    conn: Connection,
    table: str,
    col: str,
    user_candidates: set[int],
    virtual: VirtualDeleteState,
    explicit_by_entity: dict[str, set[int]],
    protected_all: dict[str, set[int]],
) -> tuple[set[int], list[dict]]:
    """Usuarios con al menos una FK sobreviviente en (table, col). Batch."""
    if not user_candidates:
        return set(), []
    deleted = virtual.all_deleted(table)
    ent = _entity_for_table(table)
    planned = explicit_by_entity.get(ent or "", set()) if ent else set()
    prot = protected_all.get(ent or "", set()) if ent else set()

    blocked_users: set[int] = set()
    samples: list[dict] = []
    for user_chunk in _chunk_ids(user_candidates, 500):
        ph_users = ",".join(str(u) for u in user_chunk)
        try:
            rows = conn.execute(
                text(f"SELECT id, `{col}` FROM `{table}` WHERE `{col}` IN ({ph_users})")
            ).fetchall()
        except Exception:
            continue
        for row_id, uid in rows:
            if uid not in user_candidates:
                continue
            if row_id in deleted or row_id in planned:
                continue
            blocked_users.add(uid)
            if len(samples) < 50:
                cls = "PROTECTED" if row_id in prot else "SURVIVING_INDETERMINATE_OR_REAL"
                samples.append(
                    {
                        "user_id": uid,
                        "table": table,
                        "blocking_row_id": row_id,
                        "blocker_class": cls,
                    }
                )
    return blocked_users, samples


def classify_users_sequential(
    conn: Connection,
    user_candidates: set[int],
    protected_user_ids: set[int],
    virtual: VirtualDeleteState,
    explicit_by_entity: dict[str, set[int]],
    protected_all: dict[str, set[int]],
    users_before: int,
) -> dict[str, Any]:
    """
    Clasifica usuarios test tras simular deletes previos a users.

    A: DELETABLE_NOW — sin FK en DB
    B: DELETABLE_AFTER_PLANNED_DELETES — FK solo a filas que desaparecen en fase
    C: BLOCKED_BY_SURVIVING_REAL_OR_INDETERMINATE_DATA
    D: PROTECTED
    """
    fk_columns = load_user_fk_columns(conn)
    protected_users = sorted(user_candidates & protected_user_ids)
    active_candidates = user_candidates - set(protected_users)

    blocked_by_surviving: set[int] = set()
    blocked_samples: list[dict] = []
    for table, col in fk_columns:
        batch_blocked, samples = _surviving_user_ids_for_fk(
            conn, table, col, active_candidates, virtual, explicit_by_entity, protected_all
        )
        blocked_by_surviving.update(batch_blocked)
        blocked_samples.extend(samples)

    deletable_after_set = active_candidates - blocked_by_surviving

    users_with_any_fk: set[int] = set()
    for table, col in fk_columns:
        for user_chunk in _chunk_ids(deletable_after_set, 500):
            ph_users = ",".join(str(u) for u in user_chunk)
            rows = conn.execute(
                text(
                    f"SELECT DISTINCT `{col}` FROM `{table}` WHERE `{col}` IN ({ph_users})"
                )
            ).fetchall()
            users_with_any_fk.update(r[0] for r in rows if r[0] in deletable_after_set)
    deletable_now = sorted(deletable_after_set - users_with_any_fk)

    blocked_only_by_planned = deletable_after_set - set(deletable_now)
    indeterminate_users = users_before - len(user_candidates) - len(protected_user_ids)

    return {
        "users_before": users_before,
        "cleanup_candidates": len(user_candidates),
        "deletable_before_phase1": len(deletable_now),
        "blocked_before_phase1": len(user_candidates) - len(deletable_now) - len(protected_users),
        "blocked_only_by_rows_deleted_in_phase1": len(blocked_only_by_planned),
        "blocked_by_rows_surviving_phase1": len(blocked_by_surviving),
        "deletable_after_phase1_dependencies_removed": len(deletable_after_set),
        "blocked_after_phase1": len(blocked_by_surviving),
        "protected_users": protected_users,
        "indeterminate_users": max(0, indeterminate_users),
        "deletable_now_ids": deletable_now,
        "deletable_after_ids": sorted(deletable_after_set),
        "blocked_after_sample": blocked_samples[:50],
        "users_after_exact": users_before - len(deletable_after_set),
    }


def classify_user_blockers(
    conn: Connection,
    uid: int,
    fk_columns: list[tuple[str, str]],
    virtual: VirtualDeleteState,
    explicit_by_entity: dict[str, set[int]],
    protected_all: dict[str, set[int]],
) -> list[dict]:
    """FK bloqueantes que sobreviven la fase (un usuario). Usado en tests."""
    blocked, samples = _surviving_user_ids_for_fk(
        conn,
        fk_columns[0][0],
        fk_columns[0][1],
        {uid},
        virtual,
        explicit_by_entity,
        protected_all,
    )
    return samples if uid in blocked else []


def recalculate_ots_deletable(
    conn: Connection,
    ot_candidates: set[int],
    protected_ot: set[int],
    cleanup_act_ids: set[int],
    protected_act_ids: set[int],
) -> tuple[set[int], set[int], list[dict]]:
    """OT eliminable solo si todas sus actuaciones ∈ cleanup."""
    deletable: set[int] = set()
    blocked: set[int] = set()
    detail: list[dict] = []
    for ot_id in sorted(ot_candidates):
        if ot_id in protected_ot:
            blocked.add(ot_id)
            detail.append({"ot_id": ot_id, "status": "BLOCKED_PROTECTED"})
            continue
        acts = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        if not acts:
            deletable.add(ot_id)
            detail.append({"ot_id": ot_id, "status": "DELETE_PHASE1", "reason": "sin_actuaciones"})
            continue
        prot_acts = acts & protected_act_ids
        indet_acts = acts - cleanup_act_ids - protected_act_ids
        if prot_acts or indet_acts:
            blocked.add(ot_id)
            detail.append(
                {
                    "ot_id": ot_id,
                    "status": "BLOCKED",
                    "protected_actuaciones": sorted(prot_acts)[:5],
                    "indeterminate_actuaciones": sorted(indet_acts)[:5],
                }
            )
        elif acts <= cleanup_act_ids:
            deletable.add(ot_id)
            detail.append({"ot_id": ot_id, "status": "DELETE_PHASE1", "actuaciones": len(acts)})
    return deletable, blocked, detail


def recalculate_juzgados(
    conn: Connection,
    juz_candidates: set[int],
    protected_oficios: set[int],
    deleted_oficios: set[int],
) -> tuple[set[int], set[int]]:
    """Juzgado deletable si oficio_refs sobrevivientes = 0."""
    deletable: set[int] = set()
    blocked: set[int] = set()
    for jid in juz_candidates:
        oficios = _fetch_ids(conn, f"SELECT id FROM oficio WHERE juzgado_id = {jid}")
        surviving = oficios - deleted_oficios
        protected_surviving = surviving & protected_oficios
        if surviving:
            blocked.add(jid)
        elif protected_surviving:
            blocked.add(jid)
        else:
            deletable.add(jid)
    return deletable, blocked


def recalculate_relevadores(
    conn: Connection,
    relevador_candidates: set[int],
    deleted_relevamientos: set[int],
    protected_names: set[str],
) -> tuple[set[int], set[int], list[dict]]:
    """Relevador deletable si refs relevamiento_relevador = 0 tras deletes."""
    deletable: set[int] = set()
    blocked: set[int] = set()
    detail: list[dict] = []
    for rid in relevador_candidates:
        row = conn.execute(
            text("SELECT nombre FROM relevador WHERE id = :id"), {"id": rid}
        ).fetchone()
        nombre = (row[0] if row else "") or ""
        if nombre in protected_names:
            blocked.add(rid)
            detail.append({"relevador_id": rid, "nombre": nombre, "status": "PROTECTED"})
            continue
        refs = _fetch_ids(
            conn,
            f"SELECT relevamiento_id FROM relevamiento_relevador WHERE relevador_id = {rid}",
        )
        surviving_refs = refs - deleted_relevamientos
        if surviving_refs:
            blocked.add(rid)
            detail.append(
                {
                    "relevador_id": rid,
                    "nombre": nombre,
                    "status": "BLOCKED",
                    "surviving_refs": sorted(surviving_refs)[:5],
                }
            )
        else:
            deletable.add(rid)
            detail.append({"relevador_id": rid, "nombre": nombre, "status": "DELETABLE_AT_END"})
    return deletable, blocked, detail


def analyze_actuacion_documents(
    conn: Connection,
    cleanup_act_ids: set[int],
    protected_all: dict[str, set[int]],
) -> dict[str, Any]:
    """
    Documentos no-CASCADE ligados a actuaciones test.

    notificacion/comprobacion: FK en actuaciones → SET NULL al borrar actuación.
    """
    if not cleanup_act_ids:
        return {"notificacion": [], "comprobacion": [], "orden_trabajo_orphans": []}
    sample = sorted(cleanup_act_ids)[:500]
    ph = ",".join(str(i) for i in sample)
    rows = conn.execute(
        text(
            f"""
            SELECT a.id, a.notificacion_id, a.comprobacion_id, a.orden_trabajo_id
            FROM actuaciones a
            WHERE a.id IN ({ph})
            """
        )
    ).fetchall()
    notif_analysis: list[dict] = []
    comp_analysis: list[dict] = []
    for row in rows:
        act_id, notif_id, comp_id, ot_id = row
        if notif_id:
            prot = notif_id in protected_all.get("notificacion", set())
            notif_analysis.append(
                {
                    "actuacion_id": act_id,
                    "notificacion_id": notif_id,
                    "outcome": "SURVIVES_ORPHAN" if not prot else "PROTECTED_SURVIVES",
                    "protected": prot,
                }
            )
        if comp_id:
            prot = comp_id in protected_all.get("comprobacion", set())
            comp_analysis.append(
                {
                    "actuacion_id": act_id,
                    "comprobacion_id": comp_id,
                    "outcome": "SURVIVES_ORPHAN" if not prot else "PROTECTED_SURVIVES",
                    "protected": prot,
                }
            )
    return {
        "notificacion": notif_analysis[:30],
        "comprobacion": comp_analysis[:30],
        "note": "Borrar actuación NO borra notificacion/comprobacion (FK en actuaciones, SET NULL)",
    }


def validate_actuaciones_cascade(
    conn: Connection,
    cleanup_act_ids: set[int],
    protected_all: dict[str, set[int]],
) -> tuple[set[int], list[dict]]:
    """Retira actuaciones cuyo CASCADE alcanzaría filas protegidas."""
    if not cleanup_act_ids:
        return set(), []
    casc = cascade_children_of_actuaciones(conn, cleanup_act_ids)
    invalid: set[int] = set()
    conflicts: list[dict] = []

    prot_insp = protected_all.get("inspeccion", set())
    if prot_insp & casc.get("inspeccion", set()):
        for chunk in _chunk_ids(prot_insp & casc.get("inspeccion", set())):
            ph = ",".join(str(i) for i in chunk)
            rows = conn.execute(
                text(f"SELECT actuacion_id FROM inspeccion WHERE id IN ({ph})")
            ).fetchall()
            invalid.update(r[0] for r in rows)

    for tbl in ("clausura", "decomiso"):
        ent = _entity_for_table(tbl) or tbl
        prot = protected_all.get(ent, set())
        hit = casc.get(tbl, set()) & prot
        if hit:
            for chunk in _chunk_ids(hit):
                ph = ",".join(str(i) for i in chunk)
                rows = conn.execute(
                    text(f"SELECT actuacion_id FROM `{tbl}` WHERE id IN ({ph})")
                ).fetchall()
                invalid.update(r[0] for r in rows)

    invalid &= cleanup_act_ids
    for act_id in sorted(invalid):
        conflicts.append(
            {
                "actuacion_id": act_id,
                "status": "CONFLICT_REMOVED_FROM_CLEANUP",
            }
        )
    return invalid, conflicts


def classify_iniciadores(
    conn: Connection,
    wrapper_analysis: dict[str, Any],
    deleted_ruta_items: set[int],
    protected_act_ids: set[int],
) -> dict[str, Any]:
    """Clasificación definitiva iniciadores en wrappers 64."""
    candidatos = set(wrapper_analysis.get("iniciadores_candidato_test", []))
    proteger = set(wrapper_analysis.get("iniciadores_proteger", []))
    deletable: list[int] = []
    blocked: list[int] = []
    for ini_id in sorted(candidatos):
        row = conn.execute(
            text(
                """
                SELECT id, actuacion_id, relevamiento_id, denuncia_id,
                       notificacion_id, comprobacion_id, oficio_id
                FROM iniciador_ruta WHERE id = :id
                """
            ),
            {"id": ini_id},
        ).fetchone()
        if not row:
            continue
        m = row._mapping
        if m.get("actuacion_id") in protected_act_ids:
            blocked.append(ini_id)
            continue
        if m.get("notificacion_id") in protected_act_ids:
            blocked.append(ini_id)
            continue
        if m.get("comprobacion_id"):
            comp_id = m["comprobacion_id"]
            acts = _fetch_ids(
                conn, f"SELECT id FROM actuaciones WHERE comprobacion_id = {comp_id}"
            )
            if acts & protected_act_ids:
                blocked.append(ini_id)
                continue
        deletable.append(ini_id)
    return {
        "deletable_phase1": sorted(deletable),
        "blocked_or_protected": sorted(set(proteger) | set(blocked)),
        "deletable_count": len(deletable),
        "protected_count": len(proteger),
        "blocked_count": len(blocked),
    }


def protection_closure_check(
    virtual: VirtualDeleteState,
    protected_all: dict[str, set[int]],
) -> dict[str, Any]:
    """Intersección explicit+cascade vs protected por entidad."""
    report: dict[str, Any] = {}
    conflicts: list[dict] = []
    for entity in PROTECTED_ENTITIES_CHECK:
        table = _table_for_entity(entity)
        explicit = virtual.explicit.get(table, set())
        cascade = virtual.cascade.get(table, set())
        prot = protected_all.get(entity, set())
        inter_explicit = explicit & prot
        inter_cascade = cascade & prot
        inter_all = (explicit | cascade) & prot
        report[entity] = {
            "planned_explicit_ids": len(explicit),
            "planned_cascade_ids": len(cascade),
            "protected_ids": len(prot),
            "intersection_explicit": len(inter_explicit),
            "intersection_cascade": len(inter_cascade),
            "intersection_total": len(inter_all),
            "sample_intersection": sorted(inter_all)[:10],
        }
        if inter_all:
            conflicts.append(
                {
                    "entity": entity,
                    "intersection": sorted(inter_all)[:20],
                    "status": "DRY_RUN_INVALID",
                }
            )
    return {"by_entity": report, "conflicts": conflicts, "valid": len(conflicts) == 0}


def protected_negative_assertions(
    virtual: VirtualDeleteState,
    protected_all: dict[str, set[int]],
    all_actuation_ids: set[int],
    cleanup_act_candidates: set[int],
) -> dict[str, Any]:
    """Assert: ningún protected/indeterminado eliminado."""
    checks: dict[str, int] = {}
    for entity in PROTECTED_ENTITIES_CHECK:
        table = _table_for_entity(entity)
        deleted = virtual.all_deleted(table)
        prot = protected_all.get(entity, set())
        checks[f"protected_{entity}_deleted"] = len(deleted & prot)

    prot_acts = protected_all.get("actuaciones", set())
    indet_acts = all_actuation_ids - prot_acts - cleanup_act_candidates
    deleted_acts = virtual.explicit.get("actuaciones", set())
    checks["indeterminate_actuaciones_deleted"] = len(indet_acts & deleted_acts)
    checks["domicilios_deleted"] = len(virtual.all_deleted("domicilio"))
    checks["contribuyentes_deleted"] = len(virtual.all_deleted("contribuyente"))

    invalid = [k for k, v in checks.items() if v > 0]
    return {
        "checks": checks,
        "valid": len(invalid) == 0,
        "invalid_keys": invalid,
        "status": "DRY_RUN_VALID" if not invalid else "DRY_RUN_INVALID_ABORT",
    }


def simulate_phase1_v3(
    conn: Connection,
    cleanup: dict[str, set[int]],
    protected_all: dict[str, set[int]],
    wrapper_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Simulación secuencial FASE 1 v3 con validación FK ejecutable.

    Orden: rutas → iniciador_ruta test → actuaciones → denuncia/relevamiento → resto.
    """
    from app.domains.predeploy_cleanup.execution_validator import (
        audit_source_with_iniciadores,
        build_delete_order,
        classify_iniciadores_test,
        filter_actuaciones_blocked_by_iniciador,
        filter_parents_blocked_by_iniciador,
        load_fk_edges,
        load_iniciador_ruta_incoming_fks,
        load_iniciador_ruta_outgoing_fks,
        validate_execution_plan,
    )

    wrapper_analysis = wrapper_analysis or {
        "iniciadores_candidato_test": [],
        "iniciadores_proteger": [],
    }
    edges = load_fk_edges(conn)
    delete_order = build_delete_order(edges)
    virtual = VirtualDeleteState()
    explicit_by_entity: dict[str, set[int]] = {}

    # --- 1. Rutas ---
    for ent in (
        "ruta_grupo_inspector",
        "ruta_item",
        "ruta_pool_dia",
        "ruta_grupo",
        "ruta_trabajo",
    ):
        ids = set(cleanup.get(ent, set())) - protected_all.get(ent, set())
        explicit_by_entity[ent] = ids
        virtual.add_explicit(_table_for_entity(ent), ids)

    # --- 2. Iniciadores test (tras rutas) ---
    cleanup_act_candidates = set(cleanup.get("actuaciones", set())) - protected_all.get(
        "actuaciones", set()
    )
    ini_classification = classify_iniciadores_test(
        conn,
        protected_all,
        wrapper_analysis,
        explicit_by_entity.get("ruta_item", set()),
        explicit_by_entity.get("ruta_pool_dia", set()),
        cleanup_act_candidates,
    )
    ini_delete = set(ini_classification["delete_phase1"])
    explicit_by_entity["iniciador_ruta"] = ini_delete
    virtual.add_explicit("iniciador_ruta", ini_delete)

    # --- 3. Actuaciones (cascade + iniciador RESTRICT) ---
    cleanup_acts = set(cleanup.get("actuaciones", set())) - protected_all.get("actuaciones", set())
    invalid_acts, act_conflicts = validate_actuaciones_cascade(conn, cleanup_acts, protected_all)
    cleanup_acts -= invalid_acts
    acts_del, acts_blocked_ini, acts_ini_detail = filter_actuaciones_blocked_by_iniciador(
        conn, cleanup_acts, ini_delete
    )
    cleanup_acts = acts_del
    explicit_by_entity["actuaciones"] = cleanup_acts
    virtual.add_explicit("actuaciones", cleanup_acts)
    act_cascade = cascade_children_of_actuaciones(conn, cleanup_acts)
    for tbl, ids in act_cascade.items():
        virtual.add_cascade(tbl, ids)

    # --- 4. Denuncia / relevamiento (tras iniciadores) ---
    den_cand = set(cleanup.get("denuncia", set())) - protected_all.get("denuncia", set())
    den_del, den_blocked, den_detail = filter_parents_blocked_by_iniciador(
        conn, "denuncia", "denuncia_id", den_cand, ini_delete
    )
    explicit_by_entity["denuncia"] = den_del
    virtual.add_explicit("denuncia", den_del)

    rel_cand = set(cleanup.get("relevamiento", set())) - protected_all.get("relevamiento", set())
    rel_del, rel_blocked, rel_detail = filter_parents_blocked_by_iniciador(
        conn, "relevamiento", "relevamiento_id", rel_cand, ini_delete
    )
    explicit_by_entity["relevamiento"] = rel_del
    virtual.add_explicit("relevamiento", rel_del)
    for tbl, ids in cascade_children_of_relevamiento(conn, rel_del).items():
        virtual.add_cascade(tbl, ids)

    # --- 5. OT ---
    ot_cand = set(cleanup.get("orden_trabajo", set()))
    ot_del, ot_blocked, ot_detail = recalculate_ots_deletable(
        conn,
        ot_cand,
        protected_all.get("orden_trabajo", set()),
        cleanup_acts,
        protected_all.get("actuaciones", set()),
    )
    explicit_by_entity["orden_trabajo"] = ot_del
    virtual.add_explicit("orden_trabajo", ot_del)

    # --- 6. Juzgados, rubros, relevadores ---
    juz_cand = set(cleanup.get("juzgado_catalogo", set()))
    juz_del, juz_blocked = recalculate_juzgados(
        conn, juz_cand, protected_all.get("oficio", set()), virtual.all_deleted("oficio")
    )
    explicit_by_entity["juzgado_catalogo"] = juz_del
    virtual.add_explicit("juzgado_catalogo", juz_del)

    rubro_ids = set(cleanup.get("rubro", set())) - protected_all.get("rubro", set())
    explicit_by_entity["rubro"] = rubro_ids
    virtual.add_explicit("rubro", rubro_ids)

    from app.domains.predeploy_cleanup.constants import RELEVADORES_CANONICOS

    rev_del, rev_blocked, rev_detail = recalculate_relevadores(
        conn,
        set(cleanup.get("relevador", set())),
        rel_del,
        RELEVADORES_CANONICOS,
    )
    explicit_by_entity["relevador"] = rev_del
    virtual.add_explicit("relevador", rev_del)

    # --- 7. Users (recalculado tras plan final) ---
    users_before = conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    user_candidates = set(cleanup.get("users", set()))
    user_audit = classify_users_sequential(
        conn,
        user_candidates,
        protected_all.get("users", set()),
        virtual,
        explicit_by_entity,
        protected_all,
        users_before,
    )
    users_to_delete = set(user_audit["deletable_after_ids"])
    explicit_by_entity["users"] = users_to_delete
    virtual.add_explicit("users", users_to_delete)

    # --- 8. Validación FK ejecutable ---
    exec_validation = validate_execution_plan(conn, explicit_by_entity, virtual, edges)
    if not exec_validation["valid"]:
        for entity, adjusted in exec_validation["adjusted_explicit"].items():
            explicit_by_entity[entity] = adjusted
            table = _table_for_entity(entity)
            virtual.explicit[table] = adjusted

    # Re-validar tras ajuste
    exec_validation_final = validate_execution_plan(conn, explicit_by_entity, virtual, edges)

    closure = protection_closure_check(virtual, protected_all)
    all_act_ids = _fetch_ids(conn, "SELECT id FROM actuaciones")
    assertions = protected_negative_assertions(
        virtual, protected_all, all_act_ids, set(cleanup.get("actuaciones", set()))
    )

    den_audit = audit_source_with_iniciadores(
        conn, "denuncia", "denuncia_id", den_cand, ini_delete,
        set(ini_classification["protected_real"]),
    )
    rel_audit = audit_source_with_iniciadores(
        conn, "relevamiento", "relevamiento_id", rel_cand, ini_delete,
        set(ini_classification["protected_real"]),
    )

    doc_analysis = analyze_actuacion_documents(conn, cleanup_acts, protected_all)

    counts_before: dict[str, int] = {}
    for ent in SUMMARY_ENTITIES:
        table = _table_for_entity(ent)
        counts_before[ent] = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar() or 0

    counts_after: dict[str, int] = {}
    executability_rows: list[dict] = []
    summary_rows: list[dict] = []

    entity_blocked_map = {
        "users": user_audit["blocked_after_phase1"],
        "orden_trabajo": len(ot_blocked),
        "juzgado_catalogo": len(juz_blocked),
        "relevador": len(rev_blocked),
        "actuaciones": len(acts_blocked_ini),
        "denuncia": len(den_blocked),
        "relevamiento": len(rel_blocked),
        "iniciador_ruta": ini_classification["blocked_indeterminate_count"]
        + ini_classification["protected_real_count"],
    }

    candidate_map = {
        "users": len(cleanup.get("users", set())),
        "actuaciones": len(cleanup.get("actuaciones", set())),
        "ruta_trabajo": len(cleanup.get("ruta_trabajo", set())),
        "ruta_item": len(cleanup.get("ruta_item", set())),
        "iniciador_ruta": ini_classification["test_candidates_total"],
        "denuncia": len(cleanup.get("denuncia", set())),
        "relevamiento": len(cleanup.get("relevamiento", set())),
        "orden_trabajo": len(cleanup.get("orden_trabajo", set())),
        "relevador": len(cleanup.get("relevador", set())),
        "rubro": len(cleanup.get("rubro", set())),
        "juzgado_catalogo": len(cleanup.get("juzgado_catalogo", set())),
    }

    block_reason = {
        "users": "establecimiento_operativo_y_refs_sobrevivientes",
        "actuaciones": "iniciador_RESTRICT_sobreviviente",
        "denuncia": "iniciador_RESTRICT_sobreviviente",
        "relevamiento": "iniciador_RESTRICT_sobreviviente",
        "iniciador_ruta": "flujo_real_o_refs_indeterminadas",
        "orden_trabajo": "actuacion_protected_o_indeterminada",
    }

    for ent in SUMMARY_ENTITIES:
        table = _table_for_entity(ent)
        exp = len(virtual.explicit.get(table, set()))
        cas = len(virtual.cascade.get(table, set()))
        blocked_cnt = entity_blocked_map.get(ent, 0)
        before = counts_before[ent]
        after = before - exp - cas
        counts_after[ent] = after
        summary_rows.append(
            {
                "entidad": ent,
                "antes": before,
                "delete_explicito": exp,
                "delete_cascade": cas,
                "bloqueados": blocked_cnt,
                "despues": after,
            }
        )
        executability_rows.append(
            {
                "entidad": ent,
                "candidatos": candidate_map.get(ent, before),
                "delete_final": exp,
                "blocked": candidate_map.get(ent, before) - exp if ent in candidate_map else blocked_cnt,
                "motivo_principal": block_reason.get(ent, "fk_surviving_child"),
            }
        )

    explicit_plan = {k: sorted(v) for k, v in explicit_by_entity.items()}
    cascade_plan = {k: sorted(v) for k, v in virtual.cascade.items()}

    return {
        "version": "cleanup_phase1_dry_run_v3",
        "delete_order": delete_order,
        "iniciador_ruta_fks_outgoing": load_iniciador_ruta_outgoing_fks(conn),
        "iniciador_ruta_fks_incoming": load_iniciador_ruta_incoming_fks(conn),
        "explicit_deletes": {
            k: {"count": len(v), "ids_sample": v[:20]} for k, v in explicit_plan.items()
        },
        "cascade_deletes": {
            k: {"count": len(v), "ids_sample": v[:20]} for k, v in cascade_plan.items()
        },
        "blocked_by_surviving_fk": exec_validation_final["blocked_by_surviving_fk"],
        "execution_validation": exec_validation_final,
        "deletable_now": user_audit["deletable_before_phase1"],
        "deletable_after_dependencies": user_audit["deletable_after_phase1_dependencies_removed"],
        "blocked_after_phase1": user_audit["blocked_after_phase1"],
        "user_audit": user_audit,
        "iniciador_classification": ini_classification,
        "iniciador_wrapper_incorporated": {
            "deletable_from_wrappers_64": wrapper_analysis.get("iniciadores_candidato_test", []),
            "protected_from_wrappers_64": wrapper_analysis.get("iniciadores_proteger", []),
        },
        "denuncia_audit": den_audit,
        "relevamiento_audit": rel_audit,
        "actuaciones_blocked_by_iniciador": {
            "count": len(acts_blocked_ini),
            "sample": acts_ini_detail[:15],
        },
        "executability_table": executability_rows,
        "protection_closure": closure,
        "protected_assertions": assertions,
        "actuaciones_removed_from_cleanup": sorted(invalid_acts | acts_blocked_ini),
        "actuaciones_cascade_conflicts": act_conflicts[:20],
        "actuaciones_final_cleanup_count": len(cleanup_acts),
        "orden_trabajo_recalc": {
            "candidates": len(ot_cand),
            "deletable": len(ot_del),
            "blocked": len(ot_blocked),
            "sample_detail": ot_detail[:15],
        },
        "juzgado_recalc": {"deletable": len(juz_del), "blocked": len(juz_blocked)},
        "relevador_recalc": {
            "deletable": len(rev_del),
            "blocked": len(rev_blocked),
            "detail": rev_detail,
        },
        "document_orphan_analysis": doc_analysis,
        "summary_table": summary_rows,
        "counts_before": counts_before,
        "counts_after_exact": counts_after,
        "virtual_state": {
            "explicit": {k: len(v) for k, v in virtual.explicit.items()},
            "cascade": {k: len(v) for k, v in virtual.cascade.items()},
        },
        "dry_run_valid": (
            closure["valid"]
            and assertions["valid"]
            and exec_validation_final["valid"]
        ),
        "v2_contradiction_explanation": (
            "v2 planificaba DELETE de relevamiento/denuncia sin eliminar antes los "
            "iniciador_ruta que los referencian (FK RESTRICT). iniciador_ruta DELETE=0 "
            "porque no estaba en cleanup manifest; v3 inserta iniciadores test eliminables "
            "después de ruta_item/ruta_pool y antes de sources."
        ),
    }


def simulate_phase1(
    conn: Connection,
    cleanup: dict[str, set[int]],
    protected_all: dict[str, set[int]],
    wrapper_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Simulación secuencial completa FASE 1 (v3 con FK ejecutable)."""
    return simulate_phase1_v3(conn, cleanup, protected_all, wrapper_analysis)


def _simulate_phase1_v2_legacy(
    conn: Connection,
    cleanup: dict[str, set[int]],
    protected_all: dict[str, set[int]],
    wrapper_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Simulación v2 legacy (sin validación iniciador RESTRICT)."""
    virtual = VirtualDeleteState()
    explicit_by_entity: dict[str, set[int]] = {}

    # --- Rutas (antes de actuaciones/users) ---
    for ent in (
        "ruta_grupo_inspector",
        "ruta_item",
        "ruta_pool_dia",
        "ruta_grupo",
        "ruta_trabajo",
    ):
        ids = set(cleanup.get(ent, set())) - protected_all.get(ent, set())
        explicit_by_entity[ent] = ids
        virtual.add_explicit(_table_for_entity(ent), ids)

    # --- Actuaciones con validación CASCADE ---
    cleanup_acts = set(cleanup.get("actuaciones", set())) - protected_all.get("actuaciones", set())
    invalid_acts, act_conflicts = validate_actuaciones_cascade(conn, cleanup_acts, protected_all)
    cleanup_acts -= invalid_acts
    explicit_by_entity["actuaciones"] = cleanup_acts
    virtual.add_explicit("actuaciones", cleanup_acts)
    act_cascade = cascade_children_of_actuaciones(conn, cleanup_acts)
    for tbl, ids in act_cascade.items():
        virtual.add_cascade(tbl, ids)

    # --- Denuncia / relevamiento ---
    denuncia_ids = set(cleanup.get("denuncia", set())) - protected_all.get("denuncia", set())
    explicit_by_entity["denuncia"] = denuncia_ids
    virtual.add_explicit("denuncia", denuncia_ids)

    rel_ids = set(cleanup.get("relevamiento", set())) - protected_all.get("relevamiento", set())
    explicit_by_entity["relevamiento"] = rel_ids
    virtual.add_explicit("relevamiento", rel_ids)
    for tbl, ids in cascade_children_of_relevamiento(conn, rel_ids).items():
        virtual.add_cascade(tbl, ids)

    # --- OT recalculadas ---
    ot_cand = set(cleanup.get("orden_trabajo", set()))
    ot_del, ot_blocked, ot_detail = recalculate_ots_deletable(
        conn,
        ot_cand,
        protected_all.get("orden_trabajo", set()),
        cleanup_acts,
        protected_all.get("actuaciones", set()),
    )
    explicit_by_entity["orden_trabajo"] = ot_del
    virtual.add_explicit("orden_trabajo", ot_del)

    # --- Juzgados: oficios sobrevivientes ---
    juz_cand = set(cleanup.get("juzgado_catalogo", set()))
    deleted_oficios = virtual.all_deleted("oficio")
    juz_del, juz_blocked = recalculate_juzgados(
        conn, juz_cand, protected_all.get("oficio", set()), deleted_oficios
    )
    explicit_by_entity["juzgado_catalogo"] = juz_del
    virtual.add_explicit("juzgado_catalogo", juz_del)

    # --- Rubros FASE1 conservador (solo sin refs actuales en manifest) ---
    rubro_ids = set(cleanup.get("rubro", set())) - protected_all.get("rubro", set())
    explicit_by_entity["rubro"] = rubro_ids
    virtual.add_explicit("rubro", rubro_ids)

    # --- Relevadores ---
    from app.domains.predeploy_cleanup.constants import RELEVADORES_CANONICOS

    rel_del = explicit_by_entity["relevamiento"]
    rev_del, rev_blocked, rev_detail = recalculate_relevadores(
        conn,
        set(cleanup.get("relevador", set())),
        rel_del,
        RELEVADORES_CANONICOS,
    )
    explicit_by_entity["relevador"] = rev_del
    virtual.add_explicit("relevador", rev_del)

    # --- Users al final ---
    users_before = conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    user_candidates = set(cleanup.get("users", set()))
    user_audit = classify_users_sequential(
        conn,
        user_candidates,
        protected_all.get("users", set()),
        virtual,
        explicit_by_entity,
        protected_all,
        users_before,
    )
    users_to_delete = set(user_audit["deletable_after_ids"])
    explicit_by_entity["users"] = users_to_delete
    virtual.add_explicit("users", users_to_delete)

    closure = protection_closure_check(virtual, protected_all)
    all_act_ids = _fetch_ids(conn, "SELECT id FROM actuaciones")
    assertions = protected_negative_assertions(
        virtual, protected_all, all_act_ids, set(cleanup.get("actuaciones", set()))
    )

    doc_analysis = analyze_actuacion_documents(conn, cleanup_acts, protected_all)

    iniciador_report: dict[str, Any] = {}
    if wrapper_analysis:
        iniciador_report = classify_iniciadores(
            conn,
            wrapper_analysis,
            explicit_by_entity.get("ruta_item", set()),
            protected_all.get("actuaciones", set()),
        )

    counts_before: dict[str, int] = {}
    for ent in SUMMARY_ENTITIES:
        table = _table_for_entity(ent)
        counts_before[ent] = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar() or 0

    counts_after: dict[str, int] = {}
    summary_rows: list[dict] = []
    for ent in SUMMARY_ENTITIES:
        table = _table_for_entity(ent)
        exp = len(virtual.explicit.get(table, set()))
        cas = len(virtual.cascade.get(table, set()))
        blocked_cnt = 0
        if ent == "users":
            blocked_cnt = user_audit["blocked_after_phase1"]
        elif ent == "orden_trabajo":
            blocked_cnt = len(ot_blocked)
        elif ent == "juzgado_catalogo":
            blocked_cnt = len(juz_blocked)
        elif ent == "relevador":
            blocked_cnt = len(rev_blocked)
        before = counts_before[ent]
        removed = exp + cas
        after = before - removed
        counts_after[ent] = after
        summary_rows.append(
            {
                "entidad": ent,
                "antes": before,
                "delete_explicito": exp,
                "delete_cascade": cas,
                "bloqueados": blocked_cnt,
                "despues": after,
            }
        )

    explicit_plan = {k: sorted(v) for k, v in explicit_by_entity.items()}
    cascade_plan = {k: sorted(v) for k, v in virtual.cascade.items()}

    return {
        "explicit_deletes": {
            k: {"count": len(v), "ids_sample": v[:20]} for k, v in explicit_plan.items()
        },
        "cascade_deletes": {
            k: {"count": len(v), "ids_sample": v[:20]} for k, v in cascade_plan.items()
        },
        "deletable_now": user_audit["deletable_before_phase1"],
        "deletable_after_dependencies": user_audit["deletable_after_phase1_dependencies_removed"],
        "blocked_after_phase1": user_audit["blocked_after_phase1"],
        "user_audit": user_audit,
        "protection_closure": closure,
        "protected_assertions": assertions,
        "actuaciones_removed_from_cleanup": sorted(invalid_acts),
        "actuaciones_cascade_conflicts": act_conflicts[:20],
        "actuaciones_final_cleanup_count": len(cleanup_acts),
        "orden_trabajo_recalc": {
            "candidates": len(ot_cand),
            "deletable": len(ot_del),
            "blocked": len(ot_blocked),
            "sample_detail": ot_detail[:15],
        },
        "juzgado_recalc": {"deletable": len(juz_del), "blocked": len(juz_blocked)},
        "relevador_recalc": {
            "deletable": len(rev_del),
            "blocked": len(rev_blocked),
            "detail": rev_detail,
        },
        "document_orphan_analysis": doc_analysis,
        "iniciador_classification": iniciador_report,
        "indeterminate_actuaciones_deleted": assertions["checks"]["indeterminate_actuaciones_deleted"],
        "summary_table": summary_rows,
        "counts_before": counts_before,
        "counts_after_exact": counts_after,
        "virtual_state": {
            "explicit": {k: len(v) for k, v in virtual.explicit.items()},
            "cascade": {k: len(v) for k, v in virtual.cascade.items()},
        },
        "dry_run_valid": closure["valid"] and assertions["valid"],
    }
