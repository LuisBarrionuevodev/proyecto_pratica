"""
PREDEPLOY-CLEANUP.3A.2-DIAG — forense actuaciones estructuradas (solo SELECT).
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
    RUBRO_TEST_PATTERN,
    RUBROS_CANONICOS,
    SQL_TEST_USER_WHERE,
    TEST_ACTUACIONES_SQL,
)
from app.domains.predeploy_cleanup.manifest_io import entity_ids, load_manifest
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import _chunk_ids, _fetch_ids, load_user_fk_columns

DOM_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.I)
CONTRIB_FIXTURE = re.compile(r"(test|qa|fixture|uuid|fix\d|stab|denfix|st4_|legacy)", re.I)
CALLE_FIXTURE = re.compile(
    r"(DenFix|St4_|Stab|Legacy|EO_|Fix6|Fix7|Fix10|uuid|^[0-9a-f]{8}-)", re.I
)

USER_PREFIX_PATTERNS = [
    "fix7", "stab7", "fix10a", "fix10b", "est_op", "u_fix7", "u_est_op", "u1_",
    "create_", "qa_", "hotfix_", "stab_", "hist_", "cp_", "op_ruta", "op6f", "op6i",
    "op6j", "op7d", "pr111", "pr11f", "crudmapa", "reenc_", "relhot", "outd", "rec_of",
    "rec_", "prod_", "nr_", "ind_", "cnt_", "ed4b", "rein_b", "reenc_of", "id10c",
    "st4_", "rlist_", "edn_", "op1b", "pool_", "asig1", "golden_", "f22_", "pr93",
    "pr2_", "m4f_", "uhf_", "stab10_", "cf1_", "edp_", "pend_ind", "real_", "op6h",
    "op7b", "op6g",
]

TESTS_ROOT = Path(__file__).resolve().parents[3] / "tests"


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _scalar(conn: Connection, sql: str, params: dict | None = None) -> Any:
    row = conn.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


def load_frozen_universe(prior_path: Path) -> dict[str, Any]:
    data = json.loads(prior_path.read_text(encoding="utf-8"))
    eo_ids: list[int] = []
    act_ids: list[int] = []
    act_to_eo: dict[int, int] = {}
    for r in data["eo_783"]["records"]:
        if r["classification_final"] != "REAL_OPERATIVO":
            continue
        eo_ids.append(r["eo_id"])
        for a in r["direct_actuaciones"]:
            act_ids.append(a["actuacion_id"])
            act_to_eo[a["actuacion_id"]] = r["eo_id"]
    return {
        "eo_ids": sorted(set(eo_ids)),
        "act_ids": sorted(set(act_ids)),
        "act_to_eo": act_to_eo,
        "eo_count": len(set(eo_ids)),
        "act_count": len(set(act_ids)),
        "prior_label": "OPERATIVO_ESTRUCTURADO_INDETERMINADO",
    }


def scan_test_sources() -> dict[str, Any]:
    """Escanea tests/ buscando prefijos y suites relevantes."""
    pattern_hits: dict[str, list[dict[str, str]]] = defaultdict(list)
    suite_keywords = {
        "fix7": ["fix7", "FIX.7", "identidad_logica", "establecimiento_operativo"],
        "stab7": ["stab7", "domicilio_edit"],
        "fix10b": ["fix10b", "establecimiento_operativo", "eo_"],
        "fix6": ["fix6", "DenFix6", "historial"],
        "est_op": ["est_op", "u_est_op", "resolve_establecimiento"],
        "titular": ["titular", "TECH-PR12", "ownership", "COW"],
    }
    suite_files: dict[str, list[str]] = defaultdict(list)

    for py in TESTS_ROOT.rglob("*.py"):
        rel = str(py.relative_to(TESTS_ROOT.parent))
        try:
            content = py.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for prefix in USER_PREFIX_PATTERNS:
            if prefix in content:
                pattern_hits[prefix].append({"file": rel, "match": "literal_prefix"})
        for sk, kws in suite_keywords.items():
            if any(kw in content for kw in kws):
                suite_files[sk].append(rel)

    sandbox_commit_files = []
    for py in TESTS_ROOT.rglob("*.py"):
        try:
            content = py.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "digitaliza_sandbox" in content or (
            "SQLALCHEMY_DATABASE_URI" in content and "commit" in content
        ):
            if "digitaliza_sandbox" in content:
                sandbox_commit_files.append(str(py.relative_to(TESTS_ROOT.parent)))

    return {
        "pattern_hits": {k: v[:20] for k, v in pattern_hits.items()},
        "suite_files": {k: sorted(set(v))[:30] for k, v in suite_files.items()},
        "sandbox_uri_tests_sample": sorted(set(sandbox_commit_files))[:40],
    }


def _user_pattern(username: str, email: str) -> str:
    u = (username or "").lower()
    e = (email or "").lower()
    for p in USER_PREFIX_PATTERNS:
        if u.startswith(p) or p in u:
            return p
    if e.endswith("@t.local"):
        return "@t.local"
    if e.endswith("@test.local"):
        return "@test.local"
    return "other"


def _graph_signature(g: dict[str, Any]) -> str:
    return "|".join(
        [
            str(g.get("tipo") or ""),
            "I" if g.get("has_inspeccion") else "-",
            "N" if g.get("has_notificacion") else "-",
            "C" if g.get("has_comprobacion") else "-",
            str(g.get("ini_tipo") or ""),
            str(g.get("rubro_cls") or ""),
            str(g.get("dom_cls") or ""),
            str(g.get("user_pat") or ""),
        ]
    )


def _classify_act(
    act: dict[str, Any],
    prot: dict[str, set[int]],
    test_act_ids: set[int],
    blocked_139: set[int],
    reasons: list[str],
) -> str:
    aid = act["actuacion_id"]
    if aid in prot.get("actuaciones", set()):
        reasons.append("protected_manifest_actuacion")
        return "CONFIRMADO_REAL"
    ot_id = act.get("orden_trabajo_id")
    if ot_id and ot_id in prot.get("orden_trabajo", set()):
        reasons.append("protected_manifest_ot")
        return "CONFIRMADO_REAL"
    if act.get("notificacion_id") in prot.get("notificacion", set()):
        reasons.append("protected_manifest_notificacion")
        return "CONFIRMADO_REAL"
    if act.get("comprobacion_id") in prot.get("comprobacion", set()):
        reasons.append("protected_manifest_comprobacion")
        return "CONFIRMADO_REAL"
    if act.get("inspeccion_id") in prot.get("inspeccion", set()):
        reasons.append("protected_manifest_inspeccion")
        return "CONFIRMADO_REAL"

    if aid in test_act_ids or aid in blocked_139:
        reasons.append("known_test_act_pattern_or_blocked_139")
        return "CONFIRMADO_TEST"

    ot_num = (act.get("numero_acta") or "").strip()
    calle = (act.get("calle") or "").strip()
    if OT_TEST_PATTERN.match(ot_num):
        reasons.append("ot_fixture_pattern")
        return "CONFIRMADO_TEST"
    if DOM_UUID.match(calle) or CALLE_FIXTURE.search(calle):
        reasons.append("domicilio_fixture_calle")
        return "CONFIRMADO_TEST"
    if CONTRIB_FIXTURE.search(act.get("contrib_apellido") or "") or CONTRIB_FIXTURE.search(
        act.get("contrib_nombre") or ""
    ):
        reasons.append("contribuyente_fixture")
        return "CONFIRMADO_TEST"
    if act.get("rubro_nombre") and RUBRO_TEST_PATTERN.search(act["rubro_nombre"]):
        reasons.append("rubro_qa")
        return "CONFIRMADO_TEST"

    up = act.get("user_pattern", "other")
    if up not in ("other",) and (
        act.get("eo_user_is_test") or act.get("ruta_user_is_test")
    ):
        if act.get("batch_same_second"):
            reasons.append("test_user_batch_timestamp")
            return "CONFIRMADO_TEST"
        if act.get("graph_complete_test_route"):
            reasons.append("test_user_full_route_graph")
            return "CONFIRMADO_TEST"
        reasons.append("test_user_structured_graph")
        return "CONFIRMADO_TEST"

    if act.get("evidence_real_positive"):
        return "CONFIRMADO_REAL"

    return "INDETERMINADO"


def run_structured_acts_forensic(
    conn: Connection,
    prior_eo_path: Path,
    protected_path: Path,
) -> dict[str, Any]:
    universe = load_frozen_universe(prior_eo_path)
    act_ids = set(universe["act_ids"])
    eo_ids = set(universe["eo_ids"])

    existing_acts = set()
    missing_acts = []
    for chunk in _chunk_ids(act_ids, 400):
        ph = ",".join(str(i) for i in chunk)
        found = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE id IN ({ph})")
        missing_acts.extend(set(chunk) - found)
        existing_acts.update(found)

    prot_manifest = load_manifest(protected_path)
    prot = expand_protected_indirect(conn, load_protected_sets(prot_manifest))
    test_act_ids = _fetch_ids(conn, TEST_ACTUACIONES_SQL)
    blocked_139 = test_act_ids - prot.get("actuaciones", set())

    # OT whitelist from manifest
    prot_ot_nums = set()
    for item in prot_manifest.get("entities", {}).get("orden_trabajo", []):
        if isinstance(item, dict):
            prot_ot_nums.add(item.get("numero_db") or item.get("numero_normalizado"))

    act_rows: dict[int, dict] = {}
    for chunk in _chunk_ids(existing_acts, 200):
        ph = ",".join(str(i) for i in chunk)
        for r in _rows(
            conn,
            f"""
            SELECT a.id AS actuacion_id, a.fecha, a.tipo, a.created_at AS act_created_at,
                   a.orden_trabajo_id, a.domicilio_id, a.establecimiento_operativo_id,
                   a.notificacion_id, a.comprobacion_id,
                   ot.numero_acta, ot.created_at AS ot_created_at,
                   eo.created_at AS eo_created_at, eo.created_by_user_id AS eo_user_id,
                   eu.username AS eo_username, eu.email AS eo_email,
                   d.calle, d.numero, d.esquina_raw, d.calle_catalogo_id, d.distrito_id,
                   r.nombre AS rubro_nombre,
                   c.apellido AS contrib_apellido, c.nombre AS contrib_nombre, c.documento AS contrib_documento,
                   (SELECT i.id FROM inspeccion i WHERE i.actuacion_id = a.id LIMIT 1) AS inspeccion_id,
                   (SELECT i.numero_acta FROM inspeccion i WHERE i.actuacion_id = a.id LIMIT 1) AS inspeccion_numero,
                   (SELECT n.numero_acta FROM notificacion n WHERE n.id = a.notificacion_id) AS notificacion_numero,
                   (SELECT comp.numero_acta FROM comprobacion comp WHERE comp.id = a.comprobacion_id) AS comprobacion_numero,
                   (SELECT COUNT(*) FROM clausura cl WHERE cl.actuacion_id = a.id) AS clausura_count,
                   (SELECT COUNT(*) FROM decomiso de WHERE de.actuacion_id = a.id) AS decomiso_count,
                   (SELECT COUNT(*) FROM actuaciones_inspector ai WHERE ai.actuaciones_id = a.id) AS inspector_count
            FROM actuaciones a
            LEFT JOIN orden_trabajo ot ON ot.id = a.orden_trabajo_id
            LEFT JOIN establecimiento_operativo eo ON eo.id = a.establecimiento_operativo_id
            LEFT JOIN users eu ON eu.id = eo.created_by_user_id
            LEFT JOIN domicilio d ON d.id = a.domicilio_id
            LEFT JOIN rubro r ON r.id = d.rubro_id
            LEFT JOIN contribuyente c ON c.id = d.contribuyente_id
            WHERE a.id IN ({ph})
            """,
        ):
            act_rows[r["actuacion_id"]] = r

    test_user_ids = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    test_source_scan = scan_test_sources()

    # Graph extensions: iniciador, ruta, users
    for aid, row in act_rows.items():
        inis = _rows(
            conn,
            """
            SELECT ir.id, ir.tipo_iniciador, ir.created_by_user_id, ir.created_at,
                   u.username, u.email
            FROM iniciador_ruta ir
            LEFT JOIN users u ON u.id = ir.created_by_user_id
            WHERE ir.actuacion_id = :aid OR (
                ir.domicilio_id = :dom AND ir.deleted_at IS NULL
            )
            LIMIT 5
            """,
            {"aid": aid, "dom": row.get("domicilio_id")},
        )
        ri = _rows(
            conn,
            """
            SELECT ri.id, ri.ruta_trabajo_id, rt.created_by_user_id, rt.created_at,
                   u.username, u.email
            FROM ruta_item ri
            JOIN ruta_trabajo rt ON rt.id = ri.ruta_trabajo_id
            LEFT JOIN users u ON u.id = rt.created_by_user_id
            WHERE ri.actuacion_id = :aid OR ri.iniciador_ruta_id IN (
                SELECT ir.id FROM iniciador_ruta ir WHERE ir.actuacion_id = :aid
            )
            LIMIT 3
            """,
            {"aid": aid},
        )
        row["iniciadores"] = inis
        row["ruta_items"] = ri
        row["user_pattern"] = _user_pattern(row.get("eo_username") or "", row.get("eo_email") or "")
        row["eo_user_is_test"] = bool(
            row.get("eo_user_id") and row["eo_user_id"] in test_user_ids
        )
        row["ruta_user_is_test"] = any(
            ri_row.get("created_by_user_id") in test_user_ids for ri_row in ri
        )
        eo_ts = row.get("eo_created_at")
        act_ts = row.get("act_created_at")
        row["batch_same_second"] = False
        if eo_ts and act_ts:
            try:
                eo_dt = eo_ts if isinstance(eo_ts, datetime) else datetime.fromisoformat(str(eo_ts))
                act_dt = act_ts if isinstance(act_ts, datetime) else datetime.fromisoformat(str(act_ts))
                row["batch_same_second"] = abs((eo_dt - act_dt).total_seconds()) <= 2
            except (TypeError, ValueError):
                pass
        row["graph_complete_test_route"] = bool(inis and ri and row["eo_user_is_test"])
        row["has_inspeccion"] = bool(row.get("inspeccion_id"))
        row["has_notificacion"] = bool(row.get("notificacion_id"))
        row["has_comprobacion"] = bool(row.get("comprobacion_id"))
        row["rubro_cls"] = (
            "canonico"
            if (row.get("rubro_nombre") or "") in RUBROS_CANONICOS
            else ("qa" if RUBRO_TEST_PATTERN.search(row.get("rubro_nombre") or "") else "indet")
        )
        calle = row.get("calle") or ""
        row["dom_cls"] = (
            "fixture"
            if DOM_UUID.match(calle) or CALLE_FIXTURE.search(calle)
            else "indet"
        )
        row["ini_tipo"] = inis[0]["tipo_iniciador"] if inis else None
        row["ot_whitelist"] = (row.get("numero_acta") or "") in prot_ot_nums
        row["evidence_real_positive"] = row["ot_whitelist"]

    # Classify each act
    classified: list[dict[str, Any]] = []
    cls_counter = Counter()
    sig_counter = Counter()
    user_pat_agg: dict[str, dict[str, int]] = defaultdict(lambda: {"eo": 0, "acts": 0})
    timestamp_batches: dict[str, list[int]] = defaultdict(list)

    for aid in sorted(existing_acts):
        row = act_rows[aid]
        reasons: list[str] = []
        cls = _classify_act(row, prot, test_act_ids, blocked_139, reasons)
        cls_counter[cls] += 1
        sig = _graph_signature(row)
        sig_counter[sig] += 1

        up = row["user_pattern"]
        user_pat_agg[up]["acts"] += 1
        if row.get("establecimiento_operativo_id"):
            user_pat_agg[up]["eo"] += 1

        if row.get("batch_same_second") and row.get("eo_user_id"):
            batch_key = f"{row['eo_user_id']}|{str(row.get('eo_created_at'))[:19]}"
            timestamp_batches[batch_key].append(aid)

        ot_cls = "INDETERMINADO"
        if row.get("ot_whitelist"):
            ot_cls = "REAL_ADMIN_XLSX"
        elif OT_TEST_PATTERN.match((row.get("numero_acta") or "")):
            ot_cls = "TEST_HELPER"
        elif row["eo_user_is_test"]:
            ot_cls = "TEST_HELPER"

        classified.append(
            {
                "actuacion_id": aid,
                "establecimiento_operativo_id": row.get("establecimiento_operativo_id"),
                "domicilio_id": row.get("domicilio_id"),
                "fecha": str(row.get("fecha")),
                "created_at": str(row.get("act_created_at")),
                "tipo": row.get("tipo"),
                "orden_trabajo_id": row.get("orden_trabajo_id"),
                "numero_acta": row.get("numero_acta"),
                "eo_created_by": {
                    "user_id": row.get("eo_user_id"),
                    "username": row.get("eo_username"),
                    "email": row.get("eo_email"),
                    "pattern": up,
                },
                "child_docs": {
                    "inspeccion_id": row.get("inspeccion_id"),
                    "inspeccion_numero": row.get("inspeccion_numero"),
                    "notificacion_id": row.get("notificacion_id"),
                    "notificacion_numero": row.get("notificacion_numero"),
                    "comprobacion_id": row.get("comprobacion_id"),
                    "comprobacion_numero": row.get("comprobacion_numero"),
                    "clausura": row.get("clausura_count"),
                    "decomiso": row.get("decomiso_count"),
                    "inspectores": row.get("inspector_count"),
                },
                "domicilio": {
                    "calle": row.get("calle"),
                    "numero": row.get("numero"),
                    "esquina_raw": row.get("esquina_raw"),
                    "calle_catalogo_id": row.get("calle_catalogo_id"),
                    "distrito_id": row.get("distrito_id"),
                    "classification": row.get("dom_cls"),
                },
                "contribuyente": {
                    "apellido": row.get("contrib_apellido"),
                    "nombre": row.get("contrib_nombre"),
                    "documento": row.get("contrib_documento"),
                },
                "rubro": {"nombre": row.get("rubro_nombre"), "classification": row.get("rubro_cls")},
                "graph": {
                    "iniciadores": row.get("iniciadores"),
                    "ruta_items": row.get("ruta_items"),
                    "signature": sig,
                    "batch_same_second": row.get("batch_same_second"),
                },
                "ot_analysis": ot_cls,
                "classification": cls,
                "classification_reasons": reasons,
            }
        )

    # Families by user pattern + signature
    families: dict[str, dict[str, Any]] = {}
    for rec in classified:
        up = rec["eo_created_by"]["pattern"]
        sig = rec["graph"]["signature"]
        fam_key = f"{up}::{sig}"
        if fam_key not in families:
            test_files = []
            if up in test_source_scan["pattern_hits"]:
                test_files = [h["file"] for h in test_source_scan["pattern_hits"][up][:5]]
            elif up == "@t.local":
                test_files = test_source_scan["suite_files"].get("fix7", [])[:3]
            families[fam_key] = {
                "family_id": fam_key,
                "user_pattern": up,
                "graph_signature": sig,
                "count": 0,
                "test_source_files": test_files,
                "classification_mix": Counter(),
            }
        families[fam_key]["count"] += 1
        families[fam_key]["classification_mix"][rec["classification"]] += 1

    for fam in families.values():
        fam["classification_mix"] = dict(fam["classification_mix"])

    # Compare with 139 blocked
    blocked_sigs = Counter()
    for bid in blocked_139:
        if bid in act_rows:
            blocked_sigs[_graph_signature(act_rows[bid])] += 1
    universe_sigs = Counter(r["graph"]["signature"] for r in classified)
    sig_overlap = set(universe_sigs) & set(blocked_sigs)

    # EO impact
    eo_by_act_cls: dict[int, str] = {}
    for rec in classified:
        eoid = rec.get("establecimiento_operativo_id")
        if eoid:
            eo_by_act_cls.setdefault(eoid, rec["classification"])

    acts_by_eo: dict[int, list[str]] = defaultdict(list)
    for rec in classified:
        eoid = rec.get("establecimiento_operativo_id")
        if eoid:
            acts_by_eo[eoid].append(rec["classification"])

    eo_confirmed_safe = []
    eo_blocked = []
    eo_indet = []
    for eoid in eo_ids:
        clss = acts_by_eo.get(eoid, [])
        if not clss:
            eo_indet.append(eoid)
        elif all(c == "CONFIRMADO_TEST" for c in clss):
            eo_confirmed_safe.append(eoid)
        elif any(c == "CONFIRMADO_REAL" for c in clss):
            eo_blocked.append(eoid)
        else:
            eo_indet.append(eoid)

    # User unlock: 139 current safe + new from this diag
    prior_safe_path = prior_eo_path
    prior_data = json.loads(prior_safe_path.read_text(encoding="utf-8"))
    prior_safe = set(prior_data["safe_candidates"]["fase2a_eo_only"])
    new_safe = set(eo_confirmed_safe)
    all_safe = prior_safe | new_safe
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    users_unlocked = set()
    users_still = set()
    for uid in test_users:
        refs = []
        for table, col in fk_columns:
            rows = conn.execute(
                text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}
            ).fetchall()
            refs.extend((table, r[0]) for r in rows)
        non_safe_eo = [
            (t, rid)
            for t, rid in refs
            if not (t == "establecimiento_operativo" and rid in all_safe)
        ]
        safe_eo_only = [
            (t, rid) for t, rid in refs if t == "establecimiento_operativo" and rid in all_safe
        ]
        if safe_eo_only and not non_safe_eo:
            users_unlocked.add(uid)
        elif refs:
            users_still.add(uid)

    protected_conflicts = [
        r for r in classified if r["classification"] == "CONFIRMADO_REAL"
    ]

    large_batches = [
        {"batch_key": k, "act_count": len(v), "sample": v[:10]}
        for k, v in timestamp_batches.items()
        if len(v) >= 3
    ]
    large_batches.sort(key=lambda x: -x["act_count"])

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3A.2-DIAG",
        "mode": "READ_ONLY_SELECT",
        "writes_executed": False,
        "universe": {
            **universe,
            "missing_act_ids": sorted(missing_acts),
            "existing_act_ids": len(existing_acts),
            "note": "261 EO REAL_OPERATIVO del diag 3A.1; 274 actuaciones directas únicas",
        },
        "test_source_files": test_source_scan,
        "user_patterns": dict(
            sorted(user_pat_agg.items(), key=lambda x: -x[1]["acts"])
        ),
        "timestamp_batches": {
            "batches_3plus": large_batches[:30],
            "total_batch_keys": len(timestamp_batches),
        },
        "ot_analysis": {
            "REAL_ADMIN_XLSX": sum(1 for r in classified if r["ot_analysis"] == "REAL_ADMIN_XLSX"),
            "TEST_HELPER": sum(1 for r in classified if r["ot_analysis"] == "TEST_HELPER"),
            "INDETERMINADO": sum(1 for r in classified if r["ot_analysis"] == "INDETERMINADO"),
        },
        "graph_signatures": {
            "top_signatures": sig_counter.most_common(15),
            "overlap_with_blocked_139_signatures": list(sig_overlap),
        },
        "comparison_blocked_139": {
            "blocked_139_count": len(blocked_139),
            "overlap_act_ids": sorted(existing_acts & blocked_139),
            "shared_signatures": list(sig_overlap),
        },
        "classification": {
            "CONFIRMADO_TEST": cls_counter.get("CONFIRMADO_TEST", 0),
            "CONFIRMADO_REAL": cls_counter.get("CONFIRMADO_REAL", 0),
            "INDETERMINADO": cls_counter.get("INDETERMINADO", 0),
            "sum": sum(cls_counter.values()),
        },
        "families": sorted(families.values(), key=lambda x: -x["count"])[:50],
        "acts": classified,
        "eo_impact": {
            "EO_CONFIRMED_TEST_SAFE": len(eo_confirmed_safe),
            "EO_BLOCKED_REAL": len(eo_blocked),
            "EO_INDETERMINATE": len(eo_indet),
            "eo_confirmed_test_safe_ids": eo_confirmed_safe[:100],
            "new_safe_vs_prior_139": len(new_safe - prior_safe),
        },
        "user_unlock_simulation": {
            "prior_safe_eo": len(prior_safe),
            "new_safe_from_this_diag": len(new_safe),
            "combined_safe_eo": len(all_safe),
            "users_unlocked_combined": len(users_unlocked),
            "users_still_blocked": len(users_still),
            "additional_users_vs_prior_133": len(users_unlocked) - 133,
        },
        "protected_conflicts": protected_conflicts,
    }


def write_report(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return path
