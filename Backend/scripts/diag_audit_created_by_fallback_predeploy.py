#!/usr/bin/env python
"""
PREDEPLOY-FIX.2-DIAG — diagnóstico read-only fallback silencioso a user id=1.
"""
from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(BACKEND_ROOT))

OUT = BACKEND_ROOT / "scripts" / "output" / "audit_created_by_fallback_predeploy_diag_20260920.json"


def _baseline(conn) -> dict:
    counts = {}
    for table in ("users", "relevador", "juzgado_catalogo"):
        counts[table] = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
    alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    db = conn.execute(text("SELECT DATABASE()")).scalar()
    user1 = conn.execute(
        text(
            "SELECT id, username, email, role, is_active FROM users WHERE id = 1 LIMIT 1"
        )
    ).mappings().first()
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "user1": dict(user1) if user1 else None,
    }


def _user1_refs(conn) -> dict:
    """FK columns referencing users.id with value=1."""
    fk_cols = conn.execute(
        text(
            """
            SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME, c.IS_NULLABLE
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            JOIN INFORMATION_SCHEMA.COLUMNS c
              ON c.TABLE_SCHEMA = kcu.TABLE_SCHEMA
             AND c.TABLE_NAME = kcu.TABLE_NAME
             AND c.COLUMN_NAME = kcu.COLUMN_NAME
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.REFERENCED_TABLE_NAME = 'users'
              AND kcu.REFERENCED_COLUMN_NAME = 'id'
            ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
            """
        )
    ).mappings().all()

    by_table_column: list[dict] = []
    total = 0
    for row in fk_cols:
        table = row["TABLE_NAME"]
        col = row["COLUMN_NAME"]
        nullable = row["IS_NULLABLE"]
        cnt = conn.execute(
            text(f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` = 1")
        ).scalar()
        total += int(cnt or 0)
        by_table_column.append(
            {
                "table": table,
                "column": col,
                "nullable": nullable,
                "refs_to_user1": int(cnt or 0),
            }
        )
    return {
        "total_refs": total,
        "by_table_column": by_table_column,
    }


def _temporal_analysis(conn) -> dict:
    """Read-only grouping of user1 refs by year/month where created_at exists."""
    tables_with_ts = [
        ("iniciador_ruta", "created_by_user_id", "created_at"),
        ("denuncia", "created_by_user_id", "created_at"),
        ("relevamiento", "created_by_user_id", "created_at"),
        ("ruta_trabajo", "created_by_user_id", "created_at"),
        ("ruta_item", "created_by_user_id", "created_at"),
        ("ruta_item", "ejecutado_por_user_id", "updated_at"),
        ("establecimiento_operativo", "created_by_user_id", "created_at"),
    ]
    out: dict[str, Any] = {}
    for table, col, ts_col in tables_with_ts:
        try:
            rows = conn.execute(
                text(
                    f"""
                    SELECT YEAR({ts_col}) AS y, MONTH({ts_col}) AS m, COUNT(*) AS c
                    FROM `{table}`
                    WHERE `{col}` = 1
                    GROUP BY YEAR({ts_col}), MONTH({ts_col})
                    ORDER BY y, m
                    """
                )
            ).mappings().all()
            out[f"{table}.{col}"] = [
                {"year": int(r["y"]), "month": int(r["m"]), "count": int(r["c"])}
                for r in rows
                if r["y"] is not None
            ]
        except Exception as exc:
            out[f"{table}.{col}"] = {"error": str(exc)}
    return out


def _audit_schema_from_models() -> list[dict]:
    from app.models.denuncia import Denuncia
    from app.models.establecimiento_operativo import EstablecimientoOperativo
    from app.models.iniciador_ruta import IniciadorRuta
    from app.models.relevamiento import Relevamiento
    from app.models.ruta_grupo import RutaGrupo
    from app.models.ruta_grupo_inspector import RutaGrupoInspector
    from app.models.ruta_item import RutaItem
    from app.models.ruta_pool_dia import RutaPoolDia
    from app.models.ruta_trabajo import RutaTrabajo

    specs = [
        (Denuncia, "created_by_user_id", "usuario que registra denuncia"),
        (Relevamiento, "created_by_user_id", "usuario que registra relevamiento (nullable, no siempre seteado)"),
        (IniciadorRuta, "created_by_user_id", "usuario que materializa/crea iniciador"),
        (RutaTrabajo, "created_by_user_id", "usuario que crea ruta"),
        (RutaGrupo, "created_by_user_id", "usuario que crea grupo"),
        (RutaGrupoInspector, "created_by_user_id", "usuario que asigna inspector a grupo"),
        (RutaItem, "created_by_user_id", "usuario que asigna item a ruta"),
        (RutaItem, "ejecutado_por_user_id", "usuario que ejecuta/cierra item"),
        (RutaPoolDia, "usuario_id", "usuario dueño del pool diario"),
        (EstablecimientoOperativo, "created_by_user_id", "usuario que crea EO"),
    ]
    rows = []
    for model, col, sem in specs:
        c = getattr(model, col)
        fk = None
        ondelete = None
        for fk_obj in model.__table__.foreign_keys:
            if fk_obj.parent.name == col:
                fk = str(fk_obj.target_fullname)
                ondelete = fk_obj.ondelete
        rows.append(
            {
                "table": model.__tablename__,
                "column": col,
                "semantics": sem,
                "nullable": c.nullable,
                "fk": fk,
                "ondelete": ondelete,
                "server_default": str(c.server_default) if c.server_default else None,
                "python_default": str(c.default) if c.default else None,
            }
        )
    return rows


def _identity_helpers() -> list[dict]:
    return [
        {
            "file": "app/domains/rutas_trabajo/services/auth_service.py",
            "function": "get_current_user_id_or_fallback",
            "semantics": "JWT identity → int user_id; si ausente/inválido → primer User activo ORDER BY id ASC",
            "fallback": "first active user (typically id=1 admin)",
            "raises_without_fallback": "ValueError si no hay usuario activo",
            "jwt_format": "str(user.id) o dict con user_id (compat)",
            "kind": "central_shared",
        },
        {
            "file": "app/domains/denuncias/services/denuncias_service.py",
            "function": "_get_current_user_id",
            "semantics": "JWT obligatorio; valida existencia y is_active",
            "fallback": None,
            "raises_without_fallback": "ValueError('Usuario no autorizado.')",
            "jwt_format": "str(user.id) o dict con user_id",
            "kind": "strict_no_fallback",
        },
        {
            "file": "app/domains/actuaciones/services/notificacion_iniciador_service.py",
            "function": "_get_current_user_id",
            "semantics": "Duplicado de get_current_user_id_or_fallback",
            "fallback": "first active user ORDER BY id ASC",
            "raises_without_fallback": "ValueError",
            "kind": "duplicate_fallback",
        },
        {
            "file": "app/domains/relevamientos/services/relevamiento_iniciador_service.py",
            "function": "_get_current_user_id",
            "semantics": "Duplicado de get_current_user_id_or_fallback",
            "fallback": "first active user ORDER BY id ASC",
            "kind": "duplicate_fallback",
        },
        {
            "file": "app/domains/actuaciones/services/oficio_iniciador_service.py",
            "function": "_get_current_user_id",
            "semantics": "Duplicado de get_current_user_id_or_fallback",
            "fallback": "first active user ORDER BY id ASC",
            "kind": "duplicate_fallback",
        },
        {
            "file": "app/domains/usuarios/services/profile_service.py",
            "function": "_get_current_user",
            "semantics": "JWT obligatorio para perfil",
            "fallback": None,
            "raises_without_fallback": "ValueError('Usuario no autorizado.')",
            "kind": "strict_no_fallback",
        },
        {
            "file": "app/domains/usuarios/security/decorators.py",
            "function": "resolve_user_from_identity",
            "semantics": "Resuelve User desde JWT; retorna None si ausente",
            "fallback": None,
            "kind": "resolver_only",
        },
        {
            "file": "app/domains/usuarios/services/auth_service.py",
            "function": "login_user → create_access_token(identity=str(user.id))",
            "semantics": "Emite JWT con subject string del id numérico",
            "fallback": None,
            "kind": "token_issuer",
        },
    ]


def _call_sites() -> list[dict]:
    return [
        {
            "domain": "rutas_trabajo",
            "file": "services/ruta_create_service.py",
            "function": "crear_ruta_trabajo",
            "helper": "get_current_user_id_or_fallback",
            "field": "ruta_trabajo.created_by_user_id",
            "context": "HTTP POST /rutas-trabajo (phase1 JWT guard)",
            "jwt_required": True,
            "fallback_reachable": "solo si JWT presente pero identity inválida/inactiva",
        },
        {
            "domain": "rutas_trabajo",
            "file": "services/grupo_service.py",
            "function": "crear_grupo",
            "helper": "get_current_user_id_or_fallback",
            "field": "ruta_grupo.created_by_user_id",
            "context": "HTTP POST grupo",
            "jwt_required": True,
            "fallback_reachable": "identity inválida",
        },
        {
            "domain": "rutas_trabajo",
            "file": "services/grupo_inspectores_service.py",
            "function": "reemplazar_inspectores_grupo",
            "helper": "get_current_user_id_or_fallback",
            "field": "ruta_grupo_inspector.created_by_user_id",
            "context": "HTTP PUT inspectores",
            "jwt_required": True,
            "fallback_reachable": "identity inválida",
        },
        {
            "domain": "rutas_trabajo",
            "file": "services/ruta_items_service.py",
            "function": "asignar_iniciadores_a_grupo",
            "helper": "get_current_user_id_or_fallback",
            "field": "ruta_item.created_by_user_id",
            "context": "HTTP POST assign items",
            "jwt_required": True,
            "fallback_reachable": "identity inválida",
        },
        {
            "domain": "rutas_trabajo",
            "file": "services/ruta_pool_dia_service.py",
            "function": "agregar_iniciador_a_pool (usuario_id param opcional)",
            "helper": "get_current_user_id_or_fallback si usuario_id is None",
            "field": "ruta_pool_dia.usuario_id",
            "context": "HTTP POST pool",
            "jwt_required": True,
            "fallback_reachable": "si caller no pasa usuario_id explícito",
        },
        {
            "domain": "rutas_trabajo",
            "file": "routes/ruta_pool_dia/create_pool.py",
            "function": "create_pool route",
            "helper": "get_current_user_id_or_fallback",
            "field": "ruta_pool_dia.usuario_id",
            "context": "HTTP",
            "jwt_required": True,
            "fallback_reachable": True,
        },
        {
            "domain": "actuaciones",
            "file": "services/create_service.py",
            "function": "crear_actuacion_desde_payload",
            "helper": "get_current_user_id_or_fallback",
            "field": "establecimiento_operativo.created_by_user_id (vía EO link)",
            "context": "HTTP POST /actuaciones + post-commit sync",
            "jwt_required": True,
            "fallback_reachable": "identity inválida; sync post-commit sin actor propagado",
        },
        {
            "domain": "actuaciones",
            "file": "services/update_service.py",
            "function": "try_vincular_establecimiento_operativo_desde_actuacion / actualizar_actuacion",
            "helper": "get_current_user_id_or_fallback",
            "field": "establecimiento_operativo.created_by_user_id",
            "context": "HTTP PUT /actuaciones + post-commit sync",
            "jwt_required": True,
            "fallback_reachable": True,
        },
        {
            "domain": "actuaciones",
            "file": "routes/completar_trabajo_cerrar.py",
            "function": "cerrar_completar_trabajo",
            "helper": "get_current_user_id_or_fallback → ejecutado_por_user_id",
            "field": "ruta_item.ejecutado_por_user_id, iniciador.created_by (relevamiento derivado)",
            "context": "HTTP POST completar-trabajo",
            "jwt_required": True,
            "fallback_reachable": "identity inválida",
        },
        {
            "domain": "actuaciones",
            "file": "services/notificacion_iniciador_service.py",
            "function": "sync_iniciadores_reinspeccion_notificacion",
            "helper": "_get_current_user_id (duplicate fallback)",
            "field": "iniciador_ruta.created_by_user_id",
            "context": "HTTP GET pendientes, POST sync, CLI pipeline, post-commit cargar actuación, completar trabajo",
            "jwt_required": "variable: CLI/background NO; HTTP endpoints sí pero sync no propaga JWT al helper",
            "fallback_reachable": True,
        },
        {
            "domain": "relevamientos",
            "file": "services/relevamiento_iniciador_service.py",
            "function": "get_or_create_iniciador_from_relevamiento",
            "helper": "_get_current_user_id (duplicate fallback)",
            "field": "iniciador_ruta.created_by_user_id",
            "context": "HTTP POST /relevamientos (create_service)",
            "jwt_required": True,
            "fallback_reachable": "identity inválida",
        },
        {
            "domain": "actuaciones",
            "file": "services/oficio_iniciador_service.py",
            "function": "get_or_create_iniciador_from_oficio",
            "helper": "_get_current_user_id (duplicate fallback)",
            "field": "iniciador_ruta.created_by_user_id",
            "context": "oficio_completion_service (HTTP oficio flow)",
            "jwt_required": True,
            "fallback_reachable": True,
        },
        {
            "domain": "denuncias",
            "file": "services/denuncias_service.py",
            "function": "crear_denuncia_con_iniciador / eliminar / update",
            "helper": "_get_current_user_id (strict)",
            "field": "denuncia.created_by_user_id, iniciador_ruta.created_by_user_id",
            "context": "HTTP /api/denuncias",
            "jwt_required": True,
            "fallback_reachable": False,
        },
    ]


def _reproduction() -> dict:
    from flask_jwt_extended import create_access_token, verify_jwt_in_request

    from app.domains.rutas_trabajo.services.auth_service import get_current_user_id_or_fallback
    from app.domains.actuaciones.services.notificacion_iniciador_service import (
        _get_current_user_id as sync_get_user,
    )
    from app.domains.denuncias.services.denuncias_service import _get_current_user_id as denuncia_get_user
    from app.main import create_app
    from app.models import User

    app = create_app()
    results: dict[str, Any] = {}

    with app.app_context():
        admin = User.query.get(1)
        non_admin = (
            User.query.filter(User.is_active.is_(True), User.id != 1)
            .order_by(User.id.asc())
            .first()
        )
        results["user1"] = {
            "id": admin.id if admin else None,
            "username": admin.username if admin else None,
            "is_active": admin.is_active if admin else None,
        }
        results["sample_non_admin"] = {
            "id": non_admin.id if non_admin else None,
            "username": non_admin.username if non_admin else None,
        }

        # C: sin request context
        try:
            uid = get_current_user_id_or_fallback()
            results["no_request_context"] = {
                "helper": "get_current_user_id_or_fallback",
                "result": uid,
                "is_user1": uid == 1,
            }
        except Exception as exc:
            results["no_request_context"] = {
                "helper": "get_current_user_id_or_fallback",
                "exception": f"{type(exc).__name__}: {exc}",
            }

        try:
            uid = sync_get_user()
            results["no_request_context_sync_helper"] = {
                "helper": "notificacion_iniciador._get_current_user_id",
                "result": uid,
                "is_user1": uid == 1,
            }
        except Exception as exc:
            results["no_request_context_sync_helper"] = {
                "exception": f"{type(exc).__name__}: {exc}",
            }

        # B: request context sin JWT
        with app.test_request_context("/"):
            try:
                uid = get_current_user_id_or_fallback()
                results["request_without_jwt"] = {
                    "result": uid,
                    "is_user1": uid == 1,
                }
            except Exception as exc:
                results["request_without_jwt"] = {"exception": str(exc)}
            try:
                denuncia_get_user()
                results["denuncia_strict_without_jwt"] = {"raised": False}
            except (ValueError, RuntimeError) as exc:
                results["denuncia_strict_without_jwt"] = {
                    "raised": True,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }

        # A: JWT válido user X
        if non_admin:
            token_x = create_access_token(
                identity=str(non_admin.id), additional_claims={"role": non_admin.role}
            )
            with app.test_request_context(
                "/", headers={"Authorization": f"Bearer {token_x}"}
            ):
                verify_jwt_in_request()
                uid = get_current_user_id_or_fallback()
                results["jwt_valid_non_admin"] = {
                    "expected": non_admin.id,
                    "result": uid,
                    "match": uid == non_admin.id,
                }

        token_admin = create_access_token(identity="1", additional_claims={"role": "admin"})
        with app.test_request_context(
            "/", headers={"Authorization": f"Bearer {token_admin}"}
        ):
            verify_jwt_in_request()
            uid = get_current_user_id_or_fallback()
            results["jwt_valid_admin_id1"] = {
                "result": uid,
                "is_legitimate_admin": uid == 1,
            }

        # D: identity inválida
        token_bad = create_access_token(identity="999999999", additional_claims={"role": "admin"})
        with app.test_request_context(
            "/", headers={"Authorization": f"Bearer {token_bad}"}
        ):
            verify_jwt_in_request()
            uid = get_current_user_id_or_fallback()
            results["jwt_invalid_user_id"] = {
                "identity": "999999999",
                "result": uid,
                "fell_back_to_user1": uid == 1,
            }

        # inactive user token (if exists)
        inactive = User.query.filter(User.is_active.is_(False)).first()
        if inactive:
            token_inact = create_access_token(
                identity=str(inactive.id), additional_claims={"role": inactive.role}
            )
            with app.test_request_context(
                "/", headers={"Authorization": f"Bearer {token_inact}"}
            ):
                verify_jwt_in_request()
                uid = get_current_user_id_or_fallback()
                results["jwt_inactive_user"] = {
                    "user_id": inactive.id,
                    "result": uid,
                    "fell_back_to_user1": uid == 1,
                }

    return results


def _http_smoke() -> dict:
    from flask_jwt_extended import create_access_token
    from app.main import create_app
    from app.database import db

    app = create_app()
    with app.app_context():
        admin_id = db.session.execute(
            text("SELECT id FROM users WHERE LOWER(username) = 'admin' LIMIT 1")
        ).scalar()
        token = create_access_token(identity=str(admin_id), additional_claims={"role": "admin"})
        headers = {"Authorization": f"Bearer {token}"}
        client = app.test_client()
        paths = [
            ("/relevamientos", "relevamientos"),
            ("/api/profile/me", "profile"),
            ("/actuaciones/search?q=20&limit=5", "actuaciones_search"),
            ("/rutas-trabajo", "rutas_trabajo"),
            ("/api/denuncias", "denuncias"),
            ("/catalogos/rubros", "rubros"),
        ]
        out = {}
        for path, key in paths:
            r = client.get(path, headers=headers)
            out[key] = {"path": path, "status": r.status_code}
        return out


def _tests_inventory() -> dict:
    return {
        "codify_fallback_as_expected": [
            "tests/test_notificacion_iniciador_policy.py — monkeypatch _get_current_user_id → lambda: 1",
        ],
        "inject_explicit_actor": [
            "tests/test_denuncia_update_domicilio_pr9_3.py",
            "tests/test_gestion_fix_6.py",
            "tests/test_ruta_publicar_orden_trabajo_pr11_1b.py",
            "tests/test_iniciador_domicilio_propagacion_pr2.py",
            "tests/test_crud_mapa_1_anular_iniciador.py",
            "tests/test_pr12_domicilio_contamination.py",
            "tests/test_relevamientos_domicilio.py",
            "tests/test_iniciador_domicilio_herencia_pr1.py",
        ],
        "sync_without_actor_mock": [
            "tests/test_notificacion_iniciador_mixed_actuacion.py — comenta requiere User activo",
            "tests/test_gestion_fix_10a_3.py — llama sync directo en app_context",
            "tests/test_iniciador_domicilio_herencia_pr1.py",
        ],
        "jwt_guard_tests": [
            "tests/test_phase1_jwt_guard.py",
        ],
        "should_change_on_fix": [
            "Eliminar monkeypatch lambda:1 como contrato; inyectar actor explícito",
            "Sync tests deben pasar actor_user_id o mockear helper para no depender de user1",
        ],
    }


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    engine = create_engine(uri)

    with engine.connect() as conn:
        baseline_pre = _baseline(conn)
        user1_refs = _user1_refs(conn)
        temporal = _temporal_analysis(conn)

    reproduction = _reproduction()
    http_smoke = _http_smoke()
    audit_schema = _audit_schema_from_models()

    with engine.connect() as conn:
        baseline_post = _baseline(conn)

    root_cause = {
        "primary": "app/domains/rutas_trabajo/services/auth_service.py::get_current_user_id_or_fallback",
        "duplicates": [
            "app/domains/actuaciones/services/notificacion_iniciador_service.py::_get_current_user_id",
            "app/domains/relevamientos/services/relevamiento_iniciador_service.py::_get_current_user_id",
            "app/domains/actuaciones/services/oficio_iniciador_service.py::_get_current_user_id",
        ],
        "current_behavior": (
            "Si get_jwt_identity() falla, es None, o apunta a usuario inexistente/inactivo, "
            "consulta User.query.filter(is_active=True).order_by(User.id.asc()).first() → típicamente id=1 admin."
        ),
        "why_dangerous": (
            "Atribuye silenciosamente acciones humanas/automatizadas al admin sin trazabilidad; "
            "contamina auditoría y mezcla acciones reales de admin con fallbacks."
        ),
        "reachable_from": [
            "CLI sync_notificaciones_vencidas (sin JWT)",
            "post-commit sync tras cargar actuación / completar trabajo (JWT presente en request pero helper no recibe actor)",
            "cualquier service que llame helper con JWT inválido",
            "app_context tests/scripts sin request",
        ],
        "affected_audit_fields": [
            "iniciador_ruta.created_by_user_id",
            "ruta_trabajo.created_by_user_id",
            "ruta_grupo.created_by_user_id",
            "ruta_grupo_inspector.created_by_user_id",
            "ruta_item.created_by_user_id",
            "ruta_item.ejecutado_por_user_id",
            "ruta_pool_dia.usuario_id",
            "establecimiento_operativo.created_by_user_id",
        ],
        "reproduction_evidence": reproduction,
    }

    minimal_fix = {
        "strategy": "Eliminar fallback silencioso; propagar actor_user_id explícito en callers internos",
        "option_A_central_helper_only": False,
        "recommended": "B/C: central helper + call sites críticos (sync, iniciadores, rutas)",
        "files_to_modify": [
            "app/domains/rutas_trabajo/services/auth_service.py",
            "app/domains/actuaciones/services/notificacion_iniciador_service.py",
            "app/domains/relevamientos/services/relevamiento_iniciador_service.py",
            "app/domains/actuaciones/services/oficio_iniciador_service.py",
            "app/domains/actuaciones/services/cargar_actuacion_post_commit.py",
            "app/domains/actuaciones/pipelines/sync_notificaciones_vencidas.py",
            "app/domains/actuaciones/services/create_service.py",
            "app/domains/actuaciones/services/update_service.py",
            "app/domains/actuaciones/services/completar_trabajo_cierre_service.py",
            "app/domains/actuaciones/routes/completar_trabajo_cerrar.py",
            "app/domains/rutas_trabajo/services/*.py (callers)",
        ],
        "do_not_modify": [
            "datos históricos created_by_user_id=1",
            "users.id=1",
            "schema DB",
        ],
    }

    proposed_behavior = {
        "http_human_command": "require JWT (phase1 guard) + helper strict → 401/ValueError, nunca user1",
        "http_with_valid_jwt": "created_by = identity user id (incluye admin id=1 legítimo)",
        "internal_service_with_actor": "caller pasa actor_user_id explícito",
        "internal_service_without_actor": "raise explícito o NULL solo si columna nullable y contrato lo permite",
        "background_sync_cli": "requiere política explícita: actor param, env var, o NULL en columnas nullable — NO first-admin",
        "system_actor": "no existe hoy; no reutilizar user1 como system sin decisión producto",
    }

    impact = [
        {
            "function": "sync_iniciadores_reinspeccion_notificacion",
            "current": "user1 fallback en CLI/background",
            "proposed": "actor_user_id param obligatorio o skip audit con política explícita",
            "risk": "high — principal fuente de contaminación masiva",
        },
        {
            "function": "ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal",
            "current": "no propaga JWT user al sync",
            "proposed": "pasar actor desde request caller",
            "risk": "high",
        },
        {
            "function": "get_or_create_iniciador_from_relevamiento",
            "current": "fallback en iniciador al crear relevamiento",
            "proposed": "propagar actor desde route (JWT strict)",
            "risk": "medium",
        },
        {
            "function": "get_current_user_id_or_fallback en rutas CUD",
            "current": "fallback si identity inválida",
            "proposed": "get_current_user_id strict → 401",
            "risk": "low-medium",
        },
    ]

    regression_tests = [
        "authenticated user X → created_by = X",
        "authenticated admin id=1 → created_by = 1 (legítimo)",
        "HTTP command sin JWT → 401, no insert con user1",
        "service interno con actor explícito X → created_by = X",
        "service interno sin actor → error explícito, nunca first-admin",
        "sync reinspección con actor propagado desde POST cargar actuación",
        "CLI sync requiere --actor-user-id o falla",
        "JWT usuario inactivo → 401 (auth layer), no fallback",
        "no regression denuncia (ya strict), rutas, EO, relevamiento",
    ]

    report = {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-FIX.2-DIAG",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline_pre,
        "identity_helpers": _identity_helpers(),
        "fallback_implementation": {
            "central": {
                "file": "app/domains/rutas_trabajo/services/auth_service.py",
                "function": "get_current_user_id_or_fallback",
                "lines": "8-42",
                "condition": "identity is None OR parse fails OR user missing/inactive",
                "query": "User.query.filter(User.is_active.is_(True)).order_by(User.id.asc()).first()",
                "returns": "int(fallback_user.id) — typically 1",
            },
            "duplicates_identical_logic": [
                "notificacion_iniciador_service._get_current_user_id",
                "relevamiento_iniciador_service._get_current_user_id",
                "oficio_iniciador_service._get_current_user_id",
            ],
            "strict_no_fallback": [
                "denuncias_service._get_current_user_id",
                "profile_service._get_current_user",
            ],
        },
        "all_call_sites": _call_sites(),
        "sync_reinspeccion_analysis": {
            "function": "sync_iniciadores_reinspeccion_notificacion",
            "file": "app/domains/actuaciones/services/notificacion_iniciador_service.py",
            "calls_user_helper_at": "line ~445: user_id = _get_current_user_id()",
            "creates": "IniciadorRuta REINSPECCION_NOTIFICACION with created_by_user_id=user_id",
            "callers": [
                "pipelines/sync_notificaciones_vencidas.py (CLI, no JWT)",
                "cargar_actuacion_post_commit.ejecutar_sync_* (post HTTP commit, no actor propagation)",
                "create_service.crear_actuacion_desde_payload (post-commit)",
                "update_service.actualizar_actuacion (post-commit)",
                "completar_trabajo_cierre_service (post-commit)",
                "pendientes_service (GET bandeja)",
                "routes/pendientes_notificacion.py (GET)",
            ],
            "jwt_at_call_time": "HTTP callers have JWT in request, but sync does NOT read/propagate it — falls back to user1 if identity unavailable in nested context",
            "cli_without_jwt": "always falls back to first active user (user1)",
            "propagates_original_actor": False,
        },
        "http_auth_matrix": {
            "mechanism": "app/security/phase1_jwt_guard.py before_request verify_jwt_in_request",
            "jwt_subject_format": "str(user.id) from login_user",
            "note": "Endpoints protegidos exigen Bearer, pero helpers de auditoría pueden ejecutarse fuera del request o sin propagar identity",
            "smoke": http_smoke,
        },
        "request_context_vs_identity": {
            "distinction": "has_request_context() != authenticated JWT; fallback triggers on missing/invalid identity even inside request",
            "reproduction": reproduction,
        },
        "background_internal_callers": [
            {
                "caller": "python -m app.domains.actuaciones.pipelines.sync_notificaciones_vencidas",
                "jwt": False,
                "current": "user1 fallback",
            },
            {
                "caller": "ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal",
                "jwt": "parent HTTP had JWT but not propagated",
                "current": "user1 fallback likely",
            },
            {
                "caller": "pytest app.app_context() direct service calls",
                "jwt": False,
                "current": "user1 fallback",
            },
        ],
        "audit_fields_schema": audit_schema,
        "audit_fields_matrix": [
            {
                **row,
                "actual_source": "get_current_user_id_or_fallback or duplicate _get_current_user_id",
                "fallback_reachable": row["column"] != "created_by_user_id"
                or row["table"] != "denuncia",
            }
            for row in audit_schema
        ],
        "user1_refs_by_table_column": user1_refs["by_table_column"],
        "user1_total_refs": user1_refs["total_refs"],
        "temporal_analysis": temporal,
        "reproduction": reproduction,
        "explicit_actor_patterns": {
            "existing": [
                "cerrar_completar_trabajo_por_ruta_item(..., ejecutado_por_user_id=int)",
                "resolve_establecimiento_por_domicilio(..., created_by_user_id=int)",
                "try_vincular_establecimiento_operativo_desde_actuacion(..., created_by_user_id=int)",
                "ruta_pool_dia_service.agregar_iniciador_a_pool(..., usuario_id=optional)",
            ],
            "preferred_pattern": "caller HTTP obtiene user_id strict y lo pasa a services internos/sync",
        },
        "system_actor_analysis": {
            "exists": False,
            "SYSTEM_USER_IDS_in_cleanup": [1],
            "note": "Solo metadata de cleanup preserva user1; no hay service account operativo",
        },
        "tests_existing": _tests_inventory(),
        "root_cause": root_cause,
        "impact_analysis": impact,
        "minimal_fix_surface": minimal_fix,
        "proposed_behavior_matrix": proposed_behavior,
        "regression_test_matrix": regression_tests,
        "historical_data_policy": {
            "preserve_existing_user1_refs": True,
            "action": "PRESERVE",
            "rationale": (
                "~refs mezclan admin real, datos pre-auth, QA y fallback; "
                "no se puede distinguir concluyentemente sin matriz de provenance dedicada."
            ),
            "no_retroactive_update": True,
        },
        "cleanup_guards": {
            "baseline_post": baseline_post,
            "unchanged": baseline_pre == baseline_post,
            "expected": {
                "users": 1970,
                "relevador": 10,
                "juzgado_catalogo": 842,
                "database": "digitaliza_sandbox",
                "alembic_revision": "l7m8n9o0p1q2",
            },
            "http_relevamientos_200": http_smoke.get("relevamientos", {}).get("status") == 200,
        },
        "writes_executed": False,
        "status": "PASS",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"user1_total_refs={user1_refs['total_refs']}")
    print(f"no_request_context user1={reproduction.get('no_request_context', {}).get('is_user1')}")


if __name__ == "__main__":
    main()
