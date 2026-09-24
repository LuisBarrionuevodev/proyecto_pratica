#!/usr/bin/env python
"""
ACT-HIST.6 / LEGACY-DOC.3 — Sandbox migration + QA operativo.

Uso:
  cd Backend
  python scripts/act_hist_6_sandbox_migration_qa.py

NO ejecuta pytest contra sandbox.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
BACKUP_DIR = REPO_ROOT / "backups"
OUTPUT_PATH = BACKEND_ROOT / "scripts/output/act_hist_6_sandbox_migration_qa_20260921.json"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TIPOS_INI_OFICIO = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)

COUNT_TABLES = (
    "actuaciones",
    "comprobacion",
    "expediente",
    "oficio",
    "iniciador_ruta",
    "ruta_item",
    "orden_trabajo",
    "domicilio",
)

EXPECTED_REVISION_BEFORE = "m8n9o0p1q2r3"
EXPECTED_REVISION_AFTER = "n9o0p1q2r3s4"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _engine():
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    test_uri = (os.getenv("TEST_DATABASE_URL") or "").strip()
    if not uri or "sandbox" not in uri.lower():
        raise RuntimeError(f"SQLALCHEMY_DATABASE_URI debe apuntar a sandbox, got: {uri}")
    if test_uri and uri == test_uri:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI no puede ser digitaliza_test")
    if "digitaliza_test" in uri.lower():
        raise RuntimeError("Abort: apunta a digitaliza_test")
    return create_engine(uri), uri


def _table_counts(conn) -> dict[str, int]:
    out: dict[str, int] = {}
    for t in COUNT_TABLES:
        out[t] = int(conn.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar() or 0)
    return out


def _classify_oficios_dry_run(conn) -> dict[str, Any]:
    tipos_sql = ", ".join(f"'{t}'" for t in TIPOS_INI_OFICIO)
    total_physical = int(conn.execute(text("SELECT COUNT(*) FROM oficio")).scalar() or 0)
    total_active = int(
        conn.execute(text("SELECT COUNT(*) FROM oficio WHERE deleted_at IS NULL")).scalar() or 0
    )
    total_soft_deleted = total_physical - total_active

    counts = {"MATERIALIZADO": 0, "PENDIENTE_DOMICILIO": 0, "PENDIENTE_MATERIALIZACION": 0}
    violations: list[dict[str, Any]] = []
    rows = conn.execute(
        text("SELECT id, comprobacion_id FROM oficio WHERE deleted_at IS NULL")
    ).fetchall()

    for row in rows:
        oficio_id = int(row.id)
        comprobacion_id = row.comprobacion_id
        has_ini = conn.execute(
            text(
                f"""
                SELECT 1 FROM iniciador_ruta i
                WHERE i.oficio_id = :oid
                  AND i.deleted_at IS NULL
                  AND i.tipo_iniciador IN ({tipos_sql})
                LIMIT 1
                """
            ),
            {"oid": oficio_id},
        ).first()
        act_row = conn.execute(
            text(
                """
                SELECT a.domicilio_id
                FROM actuaciones a
                WHERE a.comprobacion_id = :cid
                ORDER BY a.id DESC
                LIMIT 1
                """
            ),
            {"cid": comprobacion_id},
        ).first()
        domicilio_id = act_row.domicilio_id if act_row else None

        if has_ini:
            estado = "MATERIALIZADO"
        elif domicilio_id is None:
            estado = "PENDIENTE_DOMICILIO"
        else:
            estado = "PENDIENTE_MATERIALIZACION"
        counts[estado] += 1

        # invariant pre-migration (expected classification logic)
        if estado == "MATERIALIZADO" and not has_ini:
            violations.append({"oficio_id": oficio_id, "rule": "MATERIALIZADO sin iniciador"})
        if estado == "PENDIENTE_DOMICILIO" and (has_ini or domicilio_id is not None):
            violations.append({"oficio_id": oficio_id, "rule": "PENDIENTE_DOMICILIO inválido"})
        if estado == "PENDIENTE_MATERIALIZACION" and (has_ini or domicilio_id is None):
            violations.append({"oficio_id": oficio_id, "rule": "PENDIENTE_MATERIALIZACION inválido"})

    classified = sum(counts.values())
    return {
        "total_oficios_physical": total_physical,
        "total_oficios_active": total_active,
        "total_oficios_soft_deleted": total_soft_deleted,
        "classification_universe": classified,
        "materializado": counts["MATERIALIZADO"],
        "pendiente_domicilio": counts["PENDIENTE_DOMICILIO"],
        "pendiente_materializacion": counts["PENDIENTE_MATERIALIZACION"],
        "excluded": total_soft_deleted,
        "sum_matches_universe": classified == total_active,
        "pre_migration_invariant_violations": violations,
    }


def _comprobaciones_sin_expediente_legacy(conn) -> int:
    return int(
        conn.execute(
            text(
                """
                SELECT COUNT(*) FROM comprobacion c
                WHERE c.deleted_at IS NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM expediente e
                    WHERE e.comprobacion_id = c.id
                      AND e.oficio_id IS NULL
                      AND e.deleted_at IS NULL
                  )
                """
            )
        ).scalar()
        or 0
    )


def _backfill_invariant_violations_post(conn) -> list[dict[str, Any]]:
    tipos_sql = ", ".join(f"'{t}'" for t in TIPOS_INI_OFICIO)
    violations: list[dict[str, Any]] = []
    rows = conn.execute(
        text(
            """
            SELECT o.id, o.comprobacion_id, o.iniciador_materializacion_estado
            FROM oficio o
            WHERE o.deleted_at IS NULL
            """
        )
    ).fetchall()
    for row in rows:
        oid = int(row.id)
        estado = str(row.iniciador_materializacion_estado or "")
        has_ini = conn.execute(
            text(
                f"""
                SELECT 1 FROM iniciador_ruta i
                WHERE i.oficio_id = :oid
                  AND i.deleted_at IS NULL
                  AND i.tipo_iniciador IN ({tipos_sql})
                LIMIT 1
                """
            ),
            {"oid": oid},
        ).first()
        act_row = conn.execute(
            text(
                """
                SELECT a.domicilio_id FROM actuaciones a
                WHERE a.comprobacion_id = :cid
                ORDER BY a.id DESC LIMIT 1
                """
            ),
            {"cid": row.comprobacion_id},
        ).first()
        dom = act_row.domicilio_id if act_row else None

        if estado == "MATERIALIZADO" and not has_ini:
            violations.append({"oficio_id": oid, "estado": estado, "issue": "sin iniciador"})
        if estado == "PENDIENTE_DOMICILIO" and (has_ini or dom is not None):
            violations.append({"oficio_id": oid, "estado": estado, "issue": "debe no tener ini y sin dom"})
        if estado == "PENDIENTE_MATERIALIZACION" and (has_ini or dom is None):
            violations.append({"oficio_id": oid, "estado": estado, "issue": "debe no tener ini y con dom"})
    return violations


def _backfill_counts_post(conn) -> dict[str, int]:
    out: dict[str, int] = {}
    for estado in ("MATERIALIZADO", "PENDIENTE_DOMICILIO", "PENDIENTE_MATERIALIZACION"):
        out[estado] = int(
            conn.execute(
                text(
                    "SELECT COUNT(*) FROM oficio WHERE deleted_at IS NULL "
                    "AND iniciador_materializacion_estado = :e"
                ),
                {"e": estado},
            ).scalar()
            or 0
        )
    return out


def _create_backup(uri: str) -> dict[str, Any]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"digitaliza_sandbox_pre_act_hist_6_{ts}.sql"
    # Parse mysql URL mysql+pymysql://user:pass@host:port/db
    from sqlalchemy.engine.url import make_url

    u = make_url(uri)
    user = u.username or "root"
    password = u.password or ""
    host = u.host or "localhost"
    port = str(u.port or 3306)
    database = u.database or "digitaliza_sandbox"

    cmd = [
        "mysqldump",
        f"-h{host}",
        f"-P{port}",
        f"-u{user}",
        "--single-transaction",
        "--routines",
        "--triggers",
        database,
    ]
    env = os.environ.copy()
    if password:
        env["MYSQL_PWD"] = password

    with open(path, "wb") as f:
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"mysqldump failed: {proc.stderr.decode(errors='replace')}")
    size = path.stat().st_size
    return {
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "absolute_path": str(path),
        "timestamp": ts,
        "bytes": size,
        "restore_command": f'mysql -h {host} -P {port} -u {user} {database} < "{path}"',
    }


def _run_migration() -> str:
    env = os.environ.copy()
    env["FLASK_APP"] = "app:create_app"
    proc = subprocess.run(
        ["flask", "db", "upgrade"],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(f"flask db upgrade failed:\n{out}")
    return out.strip()


def _schema_postcheck(conn) -> dict[str, Any]:
    insp = inspect(conn)
    comp_cols = {c["name"] for c in insp.get_columns("comprobacion")}
    ofi_cols = {c["name"] for c in insp.get_columns("oficio")}
    fks = insp.get_foreign_keys("comprobacion")
    fk_user = any(
        fk.get("referred_table") == "users"
        and "sin_expediente_envio_declarado_by_user_id" in (fk.get("constrained_columns") or [])
        for fk in fks
    )
    return {
        "comprobacion.sin_expediente_envio": "sin_expediente_envio" in comp_cols,
        "comprobacion.sin_expediente_envio_declarado_at": "sin_expediente_envio_declarado_at" in comp_cols,
        "comprobacion.sin_expediente_envio_declarado_by_user_id": "sin_expediente_envio_declarado_by_user_id"
        in comp_cols,
        "oficio.iniciador_materializacion_estado": "iniciador_materializacion_estado" in ofi_cols,
        "fk_sin_expediente_declarado_user": fk_user,
    }


def _run_qa_flow(report: dict[str, Any]) -> None:
    """QA controlado vía service layer (sin datos históricos reales masivos)."""
    from app import create_app
    from app.database import db
    from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
    from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
    from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
    from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
    from app.domains.actuaciones.services.declarar_sin_expediente_envio_service import (
        declarar_sin_expediente_envio,
    )
    from app.domains.actuaciones.services.delete_service import eliminar_actuacion
    from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
    from app.domains.actuaciones.services.pendientes_service import (
        get_pendientes_expediente,
        get_pendientes_oficio,
    )
    from app.domains.actuaciones.presenters.comprobacion_actas_presenters import estado_recorrido_label
    from app.models import Actuaciones, CatalogMotivoComprobacion, Comprobacion, Expediente, IniciadorRuta, JuzgadoCatalogo, Oficio, User
    from app.models.inspector import Inspector
    from tests.helpers.service_actor import jwt_request_context

    app = create_app({"TESTING": False, "RATELIMIT_ENABLED": False})
    qa_ids: dict[str, Any] = {"created": [], "soft_deleted": []}

    def _unique_acta() -> str:
        return f"{random.randint(800000, 899999):06d}"

    with app.app_context():
        insp_row = Inspector.query.first()
        motivo_row = CatalogMotivoComprobacion.query.first()
        if insp_row is None or motivo_row is None:
            raise RuntimeError("Faltan inspector o motivo comprobación en sandbox")

        actor = User.query.filter_by(is_active=True).order_by(User.id.asc()).first()
        if actor is None:
            raise RuntimeError("No hay usuario activo para QA")

        with jwt_request_context(app, int(actor.id)):
            row = ActuacionGridRowIn.model_validate(
                {
                    "carga_solo_comprobacion": True,
                    "fecha_actuacion": str(date.today()),
                    "inspectores": [str(insp_row.nombre)],
                    "contrib_apellido": "QA-ACT-HIST-6",
                    "contrib_nombre": "Sandbox",
                    "acta_comprobacion_num": _unique_acta(),
                    "comprobacion_motivo": str(motivo_row.nombre),
                }
            )
            payload = map_actuacion_row(row)
            act = crear_actuacion_desde_payload(payload, actor_user_id=int(actor.id))
            db.session.commit()
            qa_ids["actuacion_id"] = act.id
            qa_ids["comprobacion_id"] = act.comprobacion_id
            qa_ids["created"].append({"type": "actuacion", "id": act.id})

            fl = ActuacionesPendientesFilters.model_validate(
                {"desde": "2020-01-01", "hasta": "2030-12-31", "source_type": "comprobacion"}
            )
            assert act.id in [a.id for a in get_pendientes_expediente(fl)]

            decl = declarar_sin_expediente_envio(act.id, actor_user_id=int(actor.id))
            comp = decl["comprobacion"]
            db.session.refresh(comp)

            exp_env_count = (
                Expediente.query.filter_by(comprobacion_id=comp.id, deleted_at=None)
                .filter(Expediente.oficio_id.is_(None))
                .count()
            )

            report["declaration_qa"] = {
                "actuacion_id": act.id,
                "comprobacion_id": comp.id,
                "actor_user_id": int(actor.id),
                "sin_expediente_envio": bool(comp.sin_expediente_envio),
                "declarado_at": comp.sin_expediente_envio_declarado_at.isoformat()
                if comp.sin_expediente_envio_declarado_at
                else None,
                "declarado_by_user_id": comp.sin_expediente_envio_declarado_by_user_id,
                "fake_expediente_created": exp_env_count > 0,
                "in_pendiente_expediente_after": act.id
                not in [a.id for a in get_pendientes_expediente(fl)],
                "in_pendiente_oficio_after": act.id in [a.id for a in get_pendientes_oficio(fl)],
            }

            assert comp.sin_expediente_envio is True
            assert comp.sin_expediente_envio_declarado_at is not None
            assert comp.sin_expediente_envio_declarado_by_user_id == int(actor.id)
            assert exp_env_count == 0

            jz = JuzgadoCatalogo.query.order_by(JuzgadoCatalogo.id.asc()).first()
            if jz is None:
                raise RuntimeError("No hay juzgado en catálogo")

            oficio_payload = {
                "numero_oficio": f"QA6{random.randint(1000,9999)}",
                "fecha_oficio": date.today(),
                "juzgado_id": int(jz.id),
                "numero_expediente_oficio": _unique_acta()[:6],
                "fecha_expediente_oficio": date.today(),
            }
            result = complete_oficio_from_actuacion(
                act.id, oficio_payload, actor_user_id=int(actor.id)
            )
            ofi = result["oficio"]
            ex_resp = result["expediente_respuesta_oficio"]
            ini_count = IniciadorRuta.query.filter_by(actuacion_id=act.id, deleted_at=None).count()

            db.session.refresh(act)
            label = estado_recorrido_label(act)

            report["oficio_qa"] = {
                "oficio_id": ofi.id,
                "expediente_respuesta_id": ex_resp.id,
                "iniciador_id": result.get("iniciador_ruta").id if result.get("iniciador_ruta") else None,
                "iniciador_count": ini_count,
                "materializacion_estado": str(ofi.iniciador_materializacion_estado),
                "estado_recorrido_label": label,
                "domicilio_id": act.domicilio_id,
            }
            assert ini_count == 0
            assert str(ofi.iniciador_materializacion_estado) == "PENDIENTE_DOMICILIO"
            assert "pendiente domicilio operativo" in label.lower()

            qa_ids["created"].extend(
                [
                    {"type": "oficio", "id": ofi.id},
                    {"type": "expediente_respuesta", "id": ex_resp.id},
                ]
            )

            # Cleanup: delete actuación QA
            eliminar_actuacion(int(act.id))
            db.session.commit()
            qa_ids["cleanup_actuacion_id"] = act.id

            # report soft-deleted comprobacion if any
            comp_after = Comprobacion.query.get(int(comp.id))
            if comp_after and comp_after.deleted_at is not None:
                qa_ids["soft_deleted"].append({"type": "comprobacion", "id": comp.id})

    report["cleanup"] = qa_ids


def _http_smoke() -> dict[str, Any]:
    import urllib.error
    import urllib.request

    base = "http://127.0.0.1:5000"
    endpoints = [
        "/actuaciones/pendientes/oficio",
        "/actuaciones/pendientes/expediente",
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio",
        "/actuaciones/comprobacion/recorrido",
    ]
    results: dict[str, Any] = {}
    for ep in endpoints:
        try:
            req = urllib.request.Request(f"{base}{ep}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                results[ep] = resp.status
        except urllib.error.HTTPError as e:
            results[ep] = e.code
        except Exception as e:
            results[ep] = f"error:{e}"
    return results


def main() -> int:
    report: dict[str, Any] = {
        "artifact": "ACT-HIST.6-SANDBOX-MIGRATION-QA",
        "generated_at": _utc_now(),
        "status": "FAIL",
    }

    engine, uri = _engine()
    report["database"] = uri.split("/")[-1]

    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT DATABASE()")).scalar()
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        report["alembic_before"] = rev
        if db_name != "digitaliza_sandbox":
            raise RuntimeError(f"DATABASE()={db_name}, expected digitaliza_sandbox")
        if rev != EXPECTED_REVISION_BEFORE:
            raise RuntimeError(f"alembic={rev}, expected {EXPECTED_REVISION_BEFORE}")

        report["counts_before"] = _table_counts(conn)
        report["dry_run"] = _classify_oficios_dry_run(conn)
        report["comprobaciones_sin_expediente_legacy"] = _comprobaciones_sin_expediente_legacy(conn)

        if report["dry_run"]["pre_migration_invariant_violations"]:
            raise RuntimeError("Violaciones pre-migration en clasificación dry-run")
        if not report["dry_run"]["sum_matches_universe"]:
            raise RuntimeError("Suma clasificación != oficios activos")

    report["backup"] = _create_backup(uri)
    migration_out = _run_migration()
    report["migration_output"] = migration_out

    with engine.connect() as conn:
        rev_after = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        report["alembic_after"] = rev_after
        if rev_after != EXPECTED_REVISION_AFTER:
            raise RuntimeError(f"alembic after={rev_after}")

        report["schema_postcheck"] = _schema_postcheck(conn)
        report["counts_after"] = _table_counts(conn)
        drift = {
            k: report["counts_after"][k] - report["counts_before"][k] for k in COUNT_TABLES
        }
        report["counts_drift"] = drift

        report["backfill_post"] = _backfill_counts_post(conn)
        violations = _backfill_invariant_violations_post(conn)
        report["backfill_invariant_violations"] = violations

        sin_exp_false = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM comprobacion
                WHERE deleted_at IS NULL AND sin_expediente_envio = 0
                """
            )
        ).scalar()
        sin_exp_true = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM comprobacion
                WHERE deleted_at IS NULL AND sin_expediente_envio = 1
                """
            )
        ).scalar()
        report["comprobacion_sin_expediente_post_migration"] = {
            "false_count": int(sin_exp_false or 0),
            "true_count": int(sin_exp_true or 0),
            "note": "Tras migration todas las legacy deben tener sin_expediente_envio=false (true_count=0)",
        }

        if violations:
            raise RuntimeError(f"Backfill invariant violations: {len(violations)}")
        for t in COUNT_TABLES:
            if drift[t] != 0:
                raise RuntimeError(f"Drift post-migration in {t}: {drift[t]}")

    # QA service-layer (después de validar drift migration-only)
    counts_before_qa = report["counts_after"].copy()
    _run_qa_flow(report)
    with engine.connect() as conn:
        counts_after_qa = _table_counts(conn)
    report["counts_after_qa"] = counts_after_qa
    report["qa_operational_drift"] = {
        k: counts_after_qa[k] - counts_before_qa[k] for k in COUNT_TABLES
    }

    report["manual_ui"] = {
        "pendiente_expediente": "validated via service + declaration_qa",
        "pendiente_oficio": "validated via service + oficio_qa",
        "recorrido": "estado_recorrido_label in oficio_qa",
        "act_hist_toggle": "code unchanged — Frontend/CargarActuacionNuevaModal.tsx (ACT-HIST.2)",
        "http_smoke": _http_smoke(),
    }

    report["status"] = "PASS"
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
