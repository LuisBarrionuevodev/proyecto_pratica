"""
PREDEPLOY-CLEANUP.3F.1-DIAG — Forense REINSPECCION_NOTIFICACION + relevamientos 26.
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
    OT_TEST_PATTERN,
    RELEVAMIENTOS_QA_IDS,
    SQL_TEST_USER_WHERE,
)
from app.domains.predeploy_cleanup.manifest_io import entity_ids, load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import TEST_STREET_NAMES, _scalar
from app.domains.predeploy_cleanup.phase2b_route_items_reconcile import FAMILY_PATTERNS
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    load_user_fk_columns,
    protection_closure_check,
)

BASELINE_POST_2C1 = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "actuaciones": 8222,
    "denuncia": 417,
    "relevamiento": 4592,
    "orden_trabajo": 8958,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8194,
}

PROTECTED_COMP_CLOSURE_8 = frozenset({194, 480, 481, 483, 790, 889, 2268, 2497})

SYNC_OBS_RE = re.compile(r"Derivado autom[aá]tico por vencimiento", re.I)
SYNC_REL_OBS_RE = re.compile(r"Derivado autom[aá]tico desde relevamiento", re.I)
UUID_CALLE_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.I)
HOTFIX_CALLE_RE = re.compile(r"HotfixNot|hotfix", re.I)

ORPHAN_NOTIF_RESERVED = "ORPHAN_CONFIRMED_TEST"
ORPHAN_COMP_RESERVED = "ORPHAN_TEST"

TEST_FILES_FOCUS = (
    "test_hotfix_reinspeccion_notificacion.py",
    "test_hotfix_reinspeccion_notificacion_qa.py",
    "test_ruta_publicar_orden_trabajo_pr11_1.py",
    "test_ruta_publicar_orden_trabajo_pr11_1c.py",
    "test_gestion_fix_10a.py",
    "test_gestion_fix_10a_3.py",
    "test_notificacion_prorroga_motor.py",
    "test_oper_ruta_6g_asignacion_ruta_turno.py",
    "test_oper_ruta_6h_pool_ruta_filtro.py",
)


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts = {t: _count(conn, t) for t in BASELINE_POST_2C1}
    drift = [f"{t}: {counts[t]} != {e}" for t, e in BASELINE_POST_2C1.items() if counts[t] != e]
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": not drift,
        "drift": drift,
    }


def _load_frozen_3f(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _frozen_initiators_167(diag3f: dict[str, Any]) -> dict[str, Any]:
    items = diag3f["initiators"]["items"]
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        by_bucket[it["classification"]].append(it)
    ids = {it["iniciador_id"] for it in items}
    return {
        "total": len(ids),
        "ids": sorted(ids),
        "KEEP_SOURCE_INDETERMINATE": by_bucket.get("KEEP_SOURCE_INDETERMINATE", []),
        "SAFE_TEST_WRAPPER": by_bucket.get("SAFE_TEST_WRAPPER", []),
        "INDETERMINATE": by_bucket.get("INDETERMINATE", []),
        "items": items,
    }


def _frozen_notifications_199(diag3f: dict[str, Any]) -> dict[str, Any]:
    nitems = diag3f["notifications_199"]["items"]
    still: set[int] = set()
    orphan: set[int] = set()
    by_id: dict[int, dict[str, Any]] = {}
    for it in nitems:
        nid = it["notificacion_id"]
        by_id[nid] = it
        if it["classification"] == ORPHAN_NOTIF_RESERVED:
            orphan.add(nid)
        else:
            still.add(nid)
    return {
        "all_ids": sorted(by_id.keys()),
        "STILL_REFERENCED": sorted(still),
        "ORPHAN_CONFIRMED_TEST": sorted(orphan),
        "by_id": by_id,
    }


def _load_265_deleted_notif_ids(phase2c1_manifest: Path) -> set[int]:
    manifest = load_manifest(phase2c1_manifest)
    refs = manifest.get("preserve_document_refs", {})
    return {int(x) for x in refs.get("notificacion", [])}


def _load_blocked_148(phase2c1_manifest: Path) -> set[int]:
    manifest = load_manifest(phase2c1_manifest)
    return {int(x) for x in manifest.get("excluded", {}).get("blocked_acts_148", [])}


def _notif_row(conn: Connection, nid: int) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT n.id, n.numero_acta, n.anio, n.mes, n.fecha_notificacion, n.fecha_vencimiento,
                   n.created_at, n.updated_at, n.plazo_dias, n.prorroga_dias
            FROM notificacion n WHERE n.id = :id
            """
        ),
        {"id": nid},
    ).fetchone()
    if not row:
        return {"notificacion_id": nid, "missing": True}
    data = dict(row._mapping)
    acts = _rows(
        conn,
        """
        SELECT a.id, a.tipo, a.fecha, a.orden_trabajo_id, a.domicilio_id,
               a.establecimiento_operativo_id, ot.numero_acta AS ot_numero,
               d.calle, d.numero AS dom_numero, r.nombre AS rubro
        FROM actuaciones a
        LEFT JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
        LEFT JOIN domicilio d ON d.id = a.domicilio_id
        LEFT JOIN rubro r ON r.id = d.rubro_id
        WHERE a.notificacion_id = :nid
        """,
        {"nid": nid},
    )
    motivos = _rows(
        conn,
        """
        SELECT m.id, m.nombre FROM motivo m
        JOIN notificacion_motivo nm ON nm.motivo = m.id
        WHERE nm.notificacion_id = :nid
        """,
        {"nid": nid},
    )
    data["actuaciones_refs"] = acts
    data["motivos"] = motivos
    return data


def _ini_row(conn: Connection, iid: int) -> dict[str, Any]:
    row = conn.execute(text("SELECT * FROM iniciador_ruta WHERE id = :id"), {"id": iid}).fetchone()
    if not row:
        return {"iniciador_id": iid, "missing": True}
    r = dict(row._mapping)
    r["iniciador_id"] = r.get("id", iid)
    r["ruta_item_refs"] = sorted(_fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}"))
    r["ruta_pool_refs"] = sorted(
        _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}")
    )
    creator = conn.execute(
        text("SELECT id, username, email FROM users WHERE id = :id"),
        {"id": r.get("created_by_user_id")},
    ).fetchone()
    r["created_by"] = dict(creator._mapping) if creator else None
    return r


def _is_test_user(conn: Connection, user_id: int | None) -> bool:
    if not user_id:
        return False
    n = _scalar(
        conn,
        f"SELECT COUNT(*) FROM users u WHERE u.id = :id AND ({SQL_TEST_USER_WHERE})",
        {"id": user_id},
    )
    return bool(n)


def _test_evidence_for_notif(notif: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    numero = notif.get("numero_acta") or ""
    if OT_TEST_PATTERN.match(numero):
        reasons.append("numero_acta_ot_test_pattern")
    for act in notif.get("actuaciones_refs", []):
        calle = act.get("calle") or ""
        if UUID_CALLE_RE.search(calle):
            reasons.append("domicilio_uuid_calle")
        if HOTFIX_CALLE_RE.search(calle):
            reasons.append("hotfix_calle_literal")
        if act.get("ot_numero") and OT_TEST_PATTERN.match(str(act["ot_numero"])):
            reasons.append("ot_test_pattern_on_act")
    for m in notif.get("motivos", []):
        nombre = (m.get("nombre") or "").lower()
        if nombre in ("carnet de sanidad", "desinfeccion", "refacciones"):
            reasons.append(f"motivo_canonico_{nombre[:8]}")
    return reasons


def _timestamp_delta_sec(a: Any, b: Any) -> float | None:
    if not a or not b:
        return None
    try:
        ta = a if hasattr(a, "timestamp") else datetime.fromisoformat(str(a))
        tb = b if hasattr(b, "timestamp") else datetime.fromisoformat(str(b))
        return abs((ta - tb).total_seconds())
    except (TypeError, ValueError):
        return None


def _classify_timestamp_chain(notif: dict, ini: dict, act: dict | None) -> str:
    deltas: list[float] = []
    for pair in (
        (notif.get("created_at"), ini.get("created_at")),
        (notif.get("created_at"), act.get("fecha") if act else None),
        (ini.get("created_at"), act.get("created_at") if act and act.get("created_at") else None),
    ):
        d = _timestamp_delta_sec(pair[0], pair[1])
        if d is not None:
            deltas.append(d)
    if not deltas:
        return "INDETERMINATE"
    min_d = min(deltas)
    if min_d <= 2:
        return "SAME_TEST_FLOW"
    if min_d <= 60:
        return "LIKELY_HISTORICAL"
    return "INDETERMINATE"


def _scan_tests_for_numeros(tests_root: Path, numeros: set[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = defaultdict(list)
    if not numeros:
        return {}
    for tf in TEST_FILES_FOCUS:
        fp = tests_root / tf
        if not fp.is_file():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        for num in numeros:
            if num in content:
                hits[num].append(tf)
    for py in tests_root.glob("test_*.py"):
        if py.name in TEST_FILES_FOCUS:
            continue
        content = py.read_text(encoding="utf-8", errors="ignore")
        for num in numeros:
            if num in content and len(hits[num]) < 3:
                hits[num].append(py.name)
    return dict(hits)


def _classify_notificacion(
    conn: Connection,
    nid: int,
    notif: dict[str, Any],
    prot: dict[str, set[int]],
    orphan_36: set[int],
    from_265_preserved: set[int],
    blocked_148: set[int],
    test_hits: dict[str, list[str]],
) -> dict[str, Any]:
    if nid in prot.get("notificacion", set()):
        bucket = "PROTECTED_REAL_DOCUMENT"
    elif nid in orphan_36:
        bucket = "CONFIRMADO_TEST_DOCUMENT"
    elif nid in from_265_preserved:
        acts = notif.get("actuaciones_refs", [])
        act_ids = {a["id"] for a in acts}
        only_blocked_test = act_ids and act_ids <= blocked_148
        evidence = _test_evidence_for_notif(notif)
        test_num = OT_TEST_PATTERN.match(notif.get("numero_acta") or "")
        if only_blocked_test or test_num or evidence or test_hits.get(notif.get("numero_acta", "")):
            bucket = "CONFIRMADO_TEST_DOCUMENT"
        else:
            bucket = "INDETERMINATE_DOCUMENT"
    else:
        bucket = "INDETERMINATE_DOCUMENT"

    source_act_class = "SOURCE_ACT_INDETERMINATE"
    acts = notif.get("actuaciones_refs", [])
    if acts:
        if all(a["id"] in blocked_148 for a in acts):
            source_act_class = "SOURCE_ACT_CONFIRMED_TEST"
        elif any(a["id"] in prot.get("actuaciones", set()) for a in acts):
            source_act_class = "SOURCE_ACT_PROTECTED_REAL"
    elif nid in from_265_preserved:
        source_act_class = "SOURCE_ACT_ALREADY_DELETED_TEST"

    return {
        "notificacion_id": nid,
        "classification": bucket,
        "source_act_classification": source_act_class,
        "from_265_preserved_set": nid in from_265_preserved,
        "test_evidence": _test_evidence_for_notif(notif),
        "test_file_hits": test_hits.get(notif.get("numero_acta", ""), []),
    }


def _classify_initiator(
    conn: Connection,
    ini: dict[str, Any],
    notif_class: dict[int, dict[str, Any]],
    prot: dict[str, set[int]],
    prev_bucket: str,
) -> str:
    iid = ini["iniciador_id"]
    full = _ini_row(conn, iid)
    obs = (full.get("observaciones") or "") if not full.get("missing") else ""
    is_sync = bool(SYNC_OBS_RE.search(obs))
    creator_test = _is_test_user(conn, full.get("created_by_user_id"))
    nid = (ini.get("source_fk") or {}).get("notificacion_id") or full.get("notificacion_id")
    nclass = notif_class.get(nid, {}).get("classification") if nid else None

    if nid and nclass == "PROTECTED_REAL_DOCUMENT":
        if creator_test or is_sync or prev_bucket == "SAFE_TEST_WRAPPER":
            return "SAFE_WRAPPER_AROUND_REAL"
        return "KEEP_PROTECTED_SOURCE"

    if prev_bucket == "SAFE_TEST_WRAPPER" and (creator_test or is_sync):
        return "SAFE_TEST_INITIATOR"

    if nclass == "CONFIRMADO_TEST_DOCUMENT":
        return "SAFE_TEST_INITIATOR"

    if is_sync and nclass in ("CONFIRMADO_TEST_DOCUMENT", None) and creator_test is False:
        return "SAFE_TEST_INITIATOR"

    if nclass == "REAL_DOCUMENT":
        return "KEEP_REAL_SOURCE"

    if prev_bucket == "INDETERMINATE":
        return "OTHER_INDETERMINATE"

    return "KEEP_INDETERMINATE_SOURCE"


def _build_notif_ini_graph(
    conn: Connection,
    ini_items: list[dict[str, Any]],
    notif_frozen: dict[str, Any],
) -> dict[str, Any]:
    notif_to_ini: dict[int, list[int]] = defaultdict(list)
    ini_to_notif: dict[int, int | None] = {}
    for it in ini_items:
        iid = it["iniciador_id"]
        nid = (it.get("source_fk") or {}).get("notificacion_id")
        ini_to_notif[iid] = nid
        if nid:
            notif_to_ini[nid].append(iid)

    distribution = Counter(len(v) for v in notif_to_ini.values())
    zero_ini = [nid for nid in notif_frozen["all_ids"] if nid not in notif_to_ini]
    one_ini = [nid for nid, inis in notif_to_ini.items() if len(inis) == 1]
    multi_ini = [nid for nid, inis in notif_to_ini.items() if len(inis) > 1]

    total_ini_links = sum(len(v) for v in notif_to_ini.values())
    still_with_ini = len([nid for nid in notif_frozen["STILL_REFERENCED"] if nid in notif_to_ini])

    chains: list[dict[str, Any]] = []
    for nid in sorted(notif_to_ini.keys()):
        inis = notif_to_ini[nid]
        blocked_acts: set[int] = set()
        for iid in inis:
            act = (next(x for x in ini_items if x["iniciador_id"] == iid).get("source_fk") or {}).get(
                "actuacion_id"
            )
            if act:
                blocked_acts.add(act)
        chains.append(
            {
                "notificacion_id": nid,
                "iniciador_ids": inis,
                "iniciador_count": len(inis),
                "blocked_actuacion_ids": sorted(blocked_acts),
                "ruta_items": sorted(
                    {ri for iid in inis for ri in _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE iniciador_ruta_id = {iid}")}
                ),
            }
        )

    return {
        "notif_to_iniciador": {str(k): v for k, v in sorted(notif_to_ini.items())},
        "iniciadores_total_linked": total_ini_links,
        "notificaciones_with_0_iniciadores_in_167_universe": len(zero_ini),
        "notificaciones_with_1_iniciador": len(one_ini),
        "notificaciones_with_gt1_iniciador": len(multi_ini),
        "ini_count_distribution": dict(distribution),
        "reconcile_163_vs_155": {
            "STILL_REFERENCED_notif_count": len(notif_frozen["STILL_REFERENCED"]),
            "STILL_REFERENCED_with_ini_in_167": still_with_ini,
            "iniciadores_linked_to_preserved_notifs": total_ini_links,
            "explanation": (
                "163 notificaciones tienen actuación y/o iniciador refs en DB; "
                "solo un subconjunto está en el universo 167. "
                "155 iniciadores sostienen notifs del set preservado; "
                "no es 1:1 porque varias notifs comparten 0 iniciadores en universo 167, "
                "algunas tienen >1 iniciador, y 36 huérfanas no sostienen iniciadores."
            ),
        },
        "chains": chains,
    }


def _simulate_act_unlock(
    conn: Connection,
    blocked_148: set[int],
    safe_ini: set[int],
) -> dict[str, Any]:
    unlocked: list[int] = []
    still: list[dict[str, Any]] = []
    for aid in sorted(blocked_148):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}")
        remain_ini = inis - safe_ini
        if not remain_ini and not ri and not rp:
            unlocked.append(aid)
        else:
            still.append(
                {
                    "actuacion_id": aid,
                    "remaining_iniciadores": sorted(remain_ini),
                    "ruta_item_refs": sorted(ri),
                    "ruta_pool_refs": sorted(rp),
                }
            )
    return {
        "UNLOCKED_AFTER_2C2A_count": len(unlocked),
        "STILL_BLOCKED_count": len(still),
        "UNLOCKED_ids": unlocked,
        "STILL_BLOCKED_sample": still[:20],
    }


def _simulate_rel_unlock(
    conn: Connection,
    rel_ids: set[int],
    safe_ini: set[int],
) -> dict[str, Any]:
    unlocked: list[int] = []
    still: list[dict[str, Any]] = []
    for rid in sorted(rel_ids):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}")
        remain = inis - safe_ini
        if not remain:
            unlocked.append(rid)
        else:
            still.append({"relevamiento_id": rid, "remaining_iniciadores": sorted(remain)})
    return {
        "UNLOCKED_count": len(unlocked),
        "STILL_BLOCKED_count": len(still),
        "UNLOCKED_ids": unlocked,
        "STILL_BLOCKED": still,
    }


def _ot_simulation(conn: Connection, unlocked_acts: list[int]) -> dict[str, Any]:
    ot_map: dict[int, set[int]] = defaultdict(set)
    for aid in unlocked_acts:
        ot = _scalar(conn, "SELECT orden_trabajo_id FROM actuaciones WHERE id = :id", {"id": aid})
        if ot:
            ot_map[ot].add(aid)
    exclusive: list[int] = []
    shared: list[int] = []
    for ot_id, acts in ot_map.items():
        all_on = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
        if all_on == acts:
            exclusive.append(ot_id)
        else:
            shared.append(ot_id)
    return {
        "EXCLUSIVE_TEST_count": len(exclusive),
        "SHARED_count": len(shared),
        "EXCLUSIVE_OT_ids": exclusive,
        "SHARED_sample": shared[:10],
    }


def _users_sim(conn: Connection) -> dict[str, int]:
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    free = 0
    for uid in test_users:
        refs = sum(
            int(_scalar(conn, f"SELECT COUNT(*) FROM `{t}` WHERE `{c}` = :uid", {"uid": uid}) or 0)
            for t, c in fk_columns
        )
        if refs == 0:
            free += 1
    return {"users_test_fk_free": free, "users_test_still_blocked": len(test_users) - free}


def _protected_regression(conn: Connection, prot: dict[str, set[int]]) -> dict[str, Any]:
    found = {cid: bool(_scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid})) for cid in PROTECTED_COMP_CLOSURE_8}
    in_prot = {cid: cid in prot.get("comprobacion", set()) for cid in PROTECTED_COMP_CLOSURE_8}
    return {
        "closure_8_ids": sorted(PROTECTED_COMP_CLOSURE_8),
        "exist_in_db": found,
        "in_expanded_protected": in_prot,
        "all_protected": all(in_prot.values()) and all(found.values()),
    }


def run_phase2c2_notification_source_diag(
    conn: Connection,
    *,
    phase2c2_diag_path: Path,
    phase2c1_manifest_path: Path,
    protected_path: Path,
    tests_root: Path,
) -> dict[str, Any]:
    baseline = _baseline_check(conn)
    diag3f = _load_frozen_3f(phase2c2_diag_path)
    frozen_ini = _frozen_initiators_167(diag3f)
    frozen_notif = _frozen_notifications_199(diag3f)
    blocked_148 = _load_blocked_148(phase2c1_manifest_path)
    from_265 = _load_265_deleted_notif_ids(phase2c1_manifest_path)
    rel_26 = {int(x) for x in load_manifest(phase2c1_manifest_path).get("excluded", {}).get("relevamientos_26", [])}

    present_ini = sum(
        1 for iid in frozen_ini["ids"] if _scalar(conn, "SELECT COUNT(*) FROM iniciador_ruta WHERE id = :id", {"id": iid})
    )

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))

    numeros = set()
    notif_details: dict[int, dict[str, Any]] = {}
    for nid in frozen_notif["all_ids"]:
        if nid in frozen_notif["ORPHAN_CONFIRMED_TEST"]:
            continue
        nf = _notif_row(conn, nid)
        notif_details[nid] = nf
        if nf.get("numero_acta"):
            numeros.add(str(nf["numero_acta"]))

    test_hits = _scan_tests_for_numeros(tests_root, numeros)

    notif_class: dict[int, dict[str, Any]] = {}
    for nid in frozen_notif["all_ids"]:
        if nid in frozen_notif["ORPHAN_CONFIRMED_TEST"]:
            notif_class[nid] = {
                "notificacion_id": nid,
                "classification": "CONFIRMADO_TEST_DOCUMENT",
                "source_act_classification": "SOURCE_ACT_ALREADY_DELETED_TEST",
                "reserved_for_2C2C": True,
            }
            continue
        notif_class[nid] = _classify_notificacion(
            conn,
            nid,
            notif_details.get(nid, _notif_row(conn, nid)),
            prot,
            set(frozen_notif["ORPHAN_CONFIRMED_TEST"]),
            from_265,
            blocked_148,
            test_hits,
        )

    admin_analysis = {
        "rule": "created_by_user_id=1 NO implica documento real",
        "sync_service": "sync_iniciadores_reinspeccion_notificacion usa _get_current_user_id() con fallback al primer user activo (admin)",
        "observaciones_pattern": "Derivado automático por vencimiento de notificación",
        "test_helper_pattern": "tests crean notificación+actuación con user hotfix_*@t.local; iniciador test con created_by=test user",
        "iniciadores_admin_creator_in_167": sum(
            1 for it in frozen_ini["items"] if it.get("created_by_user_id") == 1
        ),
        "iniciadores_sync_obs_in_167": 0,
    }
    for it in frozen_ini["items"]:
        full = _ini_row(conn, it["iniciador_id"])
        if SYNC_OBS_RE.search(full.get("observaciones") or ""):
            admin_analysis["iniciadores_sync_obs_in_167"] += 1

    ini_final: list[dict[str, Any]] = []
    bucket_counts: Counter[str] = Counter()
    for it in frozen_ini["items"]:
        cls = _classify_initiator(conn, it, notif_class, prot, it["classification"])
        bucket_counts[cls] += 1
        full = _ini_row(conn, it["iniciador_id"])
        nid = (it.get("source_fk") or {}).get("notificacion_id")
        ini_final.append(
            {
                **it,
                "final_classification": cls,
                "observaciones": full.get("observaciones"),
                "is_sync_derived": bool(SYNC_OBS_RE.search(full.get("observaciones") or "")),
                "created_by_test_user": _is_test_user(conn, full.get("created_by_user_id")),
                "notificacion_classification": notif_class.get(nid, {}).get("classification") if nid else None,
            }
        )

    assert sum(bucket_counts.values()) == 167

    safe_ini = {x["iniciador_id"] for x in ini_final if x["final_classification"] in ("SAFE_TEST_INITIATOR", "SAFE_WRAPPER_AROUND_REAL")}
    safe_ri: set[int] = set()
    safe_rp: set[int] = set()
    for x in ini_final:
        if x["iniciador_id"] in safe_ini:
            safe_ri.update(x.get("ruta_item_refs") or [])
            safe_rp.update(x.get("ruta_pool_refs") or [])

    graph = _build_notif_ini_graph(conn, frozen_ini["items"], frozen_notif)

    acts_unlock = _simulate_act_unlock(conn, blocked_148, safe_ini)
    ot_sim = _ot_simulation(conn, acts_unlock["UNLOCKED_ids"])

    rel_items: list[dict[str, Any]] = []
    rel_ini_ids: set[int] = set()
    for rid in sorted(rel_26):
        inis = sorted(_fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}"))
        rel_ini_ids.update(inis)
        for iid in inis:
            row = _ini_row(conn, iid)
            row["iniciador_id"] = iid
            rel_items.append({**row, "relevamiento_id": rid, "qa_focus": rid in RELEVAMIENTOS_QA_IDS})
    rel_ini_class: Counter[str] = Counter()
    rel_safe_ini: set[int] = set()
    for item in rel_items:
        iid = item["iniciador_id"]
        rid = item["relevamiento_id"]
        prev = next((x for x in frozen_ini["items"] if x["iniciador_id"] == iid), None)
        prev_b = prev["classification"] if prev else "INDETERMINATE"
        fc = _classify_initiator(conn, {"iniciador_id": iid, "source_fk": {}}, notif_class, prot, prev_b)
        rel_user_test = _is_test_user(conn, item.get("created_by_user_id"))
        rel_row = conn.execute(
            text(
                """
                SELECT r.created_by_user_id, u.username
                FROM relevamiento r LEFT JOIN users u ON u.id = r.created_by_user_id
                WHERE r.id = :id
                """
            ),
            {"id": rid},
        ).fetchone()
        rel_creator_test = rel_user_test or (
            rel_row and _is_test_user(conn, rel_row[0])
        )
        sync_rel = bool(SYNC_REL_OBS_RE.search(item.get("observaciones") or ""))
        if rid in rel_26 and (rel_creator_test or sync_rel):
            fc = "SAFE_TEST_INITIATOR"
            rel_safe_ini.add(iid)
        rel_ini_class[fc] += 1

    safe_ini = safe_ini | rel_safe_ini
    rel_unlock = _simulate_rel_unlock(conn, rel_26, safe_ini)

    virtual = VirtualDeleteState()
    virtual.add_explicit("iniciador_ruta", safe_ini)
    if safe_ri:
        virtual.add_explicit("ruta_item", safe_ri)
    if safe_rp:
        virtual.add_explicit("ruta_pool_dia", safe_rp)
    closure = protection_closure_check(virtual, prot)

    users_base = _users_sim(conn)

    notif_bucket = Counter(c["classification"] for c in notif_class.values())

    from_265_count = sum(1 for c in notif_class.values() if c.get("from_265_preserved_set"))

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3F.1-DIAG",
        "mode": "READ_ONLY_FORENSIC",
        "writes_executed": False,
        "baseline": baseline,
        "initiators_167": {
            "present": present_ini,
            "expected": 167,
            "frozen_buckets_3f": {
                "KEEP_SOURCE_INDETERMINATE": len(frozen_ini["KEEP_SOURCE_INDETERMINATE"]),
                "SAFE_TEST_WRAPPER": len(frozen_ini["SAFE_TEST_WRAPPER"]),
                "INDETERMINATE": len(frozen_ini["INDETERMINATE"]),
            },
            "final_classification": dict(bucket_counts),
            "items": ini_final,
        },
        "notifications_source_graph": graph,
        "notifications_199_frozen": {
            "STILL_REFERENCED": frozen_notif["STILL_REFERENCED"],
            "ORPHAN_CONFIRMED_TEST": frozen_notif["ORPHAN_CONFIRMED_TEST"],
            "classification_final": dict(notif_bucket),
            "from_265_deleted_acts_count": from_265_count,
            "details": {str(k): notif_class[k] for k in sorted(notif_class.keys())},
        },
        "test_provenance": {
            "test_files_scanned": list(TEST_FILES_FOCUS),
            "numero_acta_hits": test_hits,
            "helper_documented": {
                "test_hotfix_reinspeccion_notificacion": "_mk_reinspeccion_notificacion_item crea User hotfix_*@t.local, Notificacion, Act INSPECCION, Iniciador REINSPECCION_NOTIFICACION",
                "sync_service": "sync_iniciadores_reinspeccion_notificacion materializa iniciadores con admin fallback y observaciones sync",
            },
        },
        "admin_creator_analysis": admin_analysis,
        "protected_analysis": _protected_regression(conn, prot),
        "notification_classification": dict(notif_bucket),
        "relevamiento_26": {
            "ids": sorted(rel_26),
            "qa_focus": {str(k): k in rel_26 for k in RELEVAMIENTOS_QA_IDS},
            "iniciador_ids": sorted(rel_ini_ids),
            "items": rel_items,
        },
        "relevamiento_initiators": {
            "classification": dict(rel_ini_class),
            "SAFE_TEST_from_relevamiento_universe": sorted(rel_safe_ini),
            "unlock_simulation": rel_unlock,
        },
        "safe_route_wrappers": {
            "SAFE_RUTA_ITEM_2C2A": sorted(safe_ri),
            "SAFE_RUTA_POOL_2C2A": sorted(safe_rp),
        },
        "safe_initiators": {
            "SAFE_INITIATOR_2C2A": sorted(safe_ini),
            "count": len(safe_ini),
        },
        "acts_unlock_simulation": acts_unlock,
        "SAFE_ACTUACIONES_AFTER_2C2A": acts_unlock["UNLOCKED_ids"],
        "relevamientos_unlock_simulation": rel_unlock,
        "SAFE_RELEVAMIENTOS_AFTER_2C2A": rel_unlock["UNLOCKED_ids"],
        "ot_simulation": ot_sim,
        "users_simulation": {
            "baseline_post_2c1": users_base,
            "after_2C2A_note": "incremental exacto en apply; wrappers reducen FK refs",
            "after_2C2B_sim_note": f"si {acts_unlock['UNLOCKED_AFTER_2C2A_count']} acts + {rel_unlock['UNLOCKED_count']} rel unlock",
        },
        "orphan_docs_reserved": {
            "notificaciones_36_ORPHAN_CONFIRMED_TEST": frozen_notif["ORPHAN_CONFIRMED_TEST"],
            "comprobaciones_20_ORPHAN_TEST": "reserved for 2C.2C per 3F diag",
            "excluded_from_2C2A": True,
        },
        "protected_closure": closure,
        "proposed_waves": {
            "2C.2A": {
                "SAFE_INITIATOR_2C2A": len(safe_ini),
                "SAFE_RUTA_ITEM": len(safe_ri),
                "SAFE_RUTA_POOL": len(safe_rp),
                "protected_closure_valid": closure["valid"],
            },
            "2C.2B": {
                "SAFE_ACTUACIONES": acts_unlock["UNLOCKED_AFTER_2C2A_count"],
                "SAFE_RELEVAMIENTOS": rel_unlock["UNLOCKED_count"],
                "SAFE_OT_EXCLUSIVE": ot_sim["EXCLUSIVE_TEST_count"],
            },
            "2C.2C": {
                "notificaciones_orphan": len(frozen_notif["ORPHAN_CONFIRMED_TEST"]),
                "comprobaciones_orphan": 20,
            },
        },
    }


def write_diag_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
