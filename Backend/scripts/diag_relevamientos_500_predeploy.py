#!/usr/bin/env python
"""
PREDEPLOY-FIX.1-DIAG — diagnóstico read-only GET /relevamientos 500.
"""
from __future__ import annotations

import json
import os
import traceback
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(BACKEND_ROOT))

OUT = BACKEND_ROOT / "scripts" / "output" / "relevamientos_500_predeploy_diag_20260920.json"


def _baseline(conn) -> dict:
    counts = {}
    for table in (
        "users",
        "relevamiento",
        "relevamiento_relevador",
        "relevador",
        "juzgado_catalogo",
    ):
        counts[table] = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
    alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    db = conn.execute(text("SELECT DATABASE()")).scalar()
    orphans = conn.execute(
        text(
            """
            SELECT COUNT(*) FROM relevamiento_relevador rr
            LEFT JOIN relevador r ON rr.relevador_id = r.id
            WHERE r.id IS NULL
            """
        )
    ).scalar()
    rel2 = conn.execute(text("SELECT COUNT(*) FROM relevador WHERE id = 2")).scalar()
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "relevador_id2_exists": bool(rel2),
        "relevamiento_relevador_orphans": int(orphans or 0),
    }


def _date_validation_analysis() -> dict:
    today = date.today()
    analysis = {"today": today.isoformat(), "scenarios": []}

    # reproduce buggy logic from list_filters.py
    try:
        desde = date(today.year, today.month, 1)
        if today.month == 12:
            hasta = date(today.year, 12, 31)
        else:
            next_month = date(today.year, today.month + 1, 1)
            hasta = date(next_month.year, next_month.month, next_month.day - 1)
        analysis["scenarios"].append(
            {"name": "default_month_range_logic", "ok": True, "desde": str(desde), "hasta": str(hasta)}
        )
    except Exception as exc:
        analysis["scenarios"].append(
            {
                "name": "default_month_range_logic",
                "ok": False,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "buggy_expression": "date(next_month.year, next_month.month, next_month.day - 1)",
                "next_month_day_minus_1": 0,
            }
        )

    from pydantic import ValidationError
    from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters

    cases = [
        ("empty_params", {}),
        ("explicit_jan", {"desde": "2026-01-01", "hasta": "2026-01-31"}),
        ("only_desde", {"desde": "2026-01-01"}),
        ("only_hasta", {"hasta": "2026-01-31"}),
        ("future_empty", {"desde": "2099-01-01", "hasta": "2099-01-31"}),
        ("invalid_date", {"desde": "2026-02-30"}),
        ("desde_gt_hasta", {"desde": "2026-06-01", "hasta": "2026-01-01"}),
    ]
    for name, params in cases:
        entry = {"name": name, "params": params}
        try:
            f = RelevamientosListFilters.model_validate(params)
            entry["ok"] = True
            entry["desde"] = f.desde.isoformat() if f.desde else None
            entry["hasta"] = f.hasta.isoformat() if f.hasta else None
        except ValidationError as exc:
            entry["ok"] = False
            entry["exception_type"] = "ValidationError"
            entry["errors"] = exc.errors()
            entry["errors_json_serializable"] = _errors_json_serializable(exc)
        except Exception as exc:
            entry["ok"] = False
            entry["exception_type"] = type(exc).__name__
            entry["exception_message"] = str(exc)
        analysis["pydantic_cases"] = analysis.get("pydantic_cases", []) + [entry]

    return analysis


def _errors_json_serializable(exc: ValidationError) -> bool:
    try:
        json.dumps(exc.errors(), default=str)
        return True
    except Exception:
        return False


def _query_analysis() -> dict:
    from app.main import create_app
    from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters
    from app.domains.relevamientos.services.list_service import listar_relevamientos_con_filtros
    from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_to_row

    app = create_app()
    result = {}
    with app.app_context():
        filters = RelevamientosListFilters.model_validate(
            {"desde": "2026-01-01", "hasta": "2026-01-31", "page": 1, "page_size": 5}
        )
        try:
            data = listar_relevamientos_con_filtros(filters)
            result["query_succeeds"] = True
            result["row_count"] = len(data["items"])
            result["total"] = data["meta"]["total"]
            if data["items"]:
                try:
                    row = relevamiento_to_row(data["items"][0])
                    json.dumps(row, default=str)
                    result["first_row_mapping_succeeds"] = True
                    result["first_row_id"] = row.get("id")
                except Exception as exc:
                    result["first_row_mapping_succeeds"] = False
                    result["first_row_error"] = f"{type(exc).__name__}: {exc}"
            else:
                result["first_row_mapping_succeeds"] = None

            empty_filters = RelevamientosListFilters.model_validate(
                {"desde": "2099-01-01", "hasta": "2099-01-31"}
            )
            empty_data = listar_relevamientos_con_filtros(empty_filters)
            result["empty_query_succeeds"] = True
            result["empty_total"] = empty_data["meta"]["total"]
        except Exception as exc:
            result["query_succeeds"] = False
            result["query_error"] = f"{type(exc).__name__}: {exc}"
            result["query_traceback"] = traceback.format_exc()
    return result


def _reproduction_http() -> dict:
    from flask_jwt_extended import create_access_token
    from app.main import create_app
    from app.database import db

    app = create_app()
    cases = {}
    with app.app_context():
        admin_id = db.session.execute(
            text("SELECT id FROM users WHERE LOWER(username) = 'admin' LIMIT 1")
        ).scalar()
        token = create_access_token(identity=str(admin_id), additional_claims={"role": "admin"})
        headers = {"Authorization": f"Bearer {token}"}
        client = app.test_client()

        paths = [
            ("no_params", "/relevamientos"),
            ("explicit_range", "/relevamientos?desde=2026-01-01&hasta=2026-01-31"),
            ("future_empty", "/relevamientos?desde=2099-01-01&hasta=2099-01-31"),
            ("invalid_date", "/relevamientos?desde=2026-02-30"),
        ]
        for name, path in paths:
            # capture flask log exception by enabling propagate
            with app.test_request_context(path):
                pass
            r = client.get(path, headers=headers)
            entry = {
                "path": path,
                "status": r.status_code,
                "body_preview": r.get_data(as_text=True)[:500],
            }
            cases[name] = entry
    return cases


def _reproduction_direct() -> dict:
    """Reproduce exception chain in route handler without HTTP layer."""
    from pydantic import ValidationError
    from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters

    original_exc = None
    secondary_exc = None
    original_tb = None
    secondary_tb = None

    try:
        RelevamientosListFilters.model_validate({})
    except ValidationError as e:
        original_exc = {
            "type": "ValidationError",
            "errors": [
                {
                    "type": err.get("type"),
                    "loc": err.get("loc"),
                    "msg": err.get("msg"),
                    "ctx_error_type": type(err.get("ctx", {}).get("error")).__name__
                    if err.get("ctx", {}).get("error")
                    else None,
                    "ctx_error_message": str(err.get("ctx", {}).get("error"))
                    if err.get("ctx", {}).get("error")
                    else None,
                }
                for err in e.errors()
            ],
        }
        original_tb = traceback.format_exc()
        try:
            from flask import jsonify

            jsonify({"detail": "Validation error", "errors": e.errors()})
        except Exception as e2:
            secondary_exc = {"type": type(e2).__name__, "message": str(e2)}
            secondary_tb = traceback.format_exc()

    return {
        "original_exception": original_exc,
        "original_traceback": original_tb,
        "secondary_exception": secondary_exc,
        "secondary_traceback": secondary_tb,
        "why_http_500": (
            "ValidationError handler calls jsonify(e.errors()) which embeds non-JSON-serializable ValueError in ctx; "
            "Flask json encoder raises TypeError, uncaught by route → 500"
            if secondary_exc
            else None
        ),
    }


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    engine = create_engine(uri)

    with engine.connect() as conn:
        baseline = _baseline(conn)

    date_analysis = _date_validation_analysis()
    query_analysis = _query_analysis()
    http_repro = _reproduction_http()
    direct_repro = _reproduction_direct()

    root_cause = {
        "file": "app/domains/relevamientos/schemas/list_filters.py",
        "function": "RelevamientosListFilters.apply_defaults_and_validate_range",
        "trigger": "GET /relevamientos sin query params → default mes actual",
        "original_exception": {
            "type": "ValidationError wrapping ValueError",
            "message": "day is out of range for month",
            "cause": "date(next_month.year, next_month.month, next_month.day - 1) usa día 0",
        },
        "secondary_exception": direct_repro.get("secondary_exception"),
        "why_http_500": direct_repro.get("why_http_500"),
        "fails_always_without_explicit_dates": True,
        "fails_only_september_through_november": (
            "Bug activo cuando today.month != 12; next_month.day-1 == 0"
        ),
    }

    minimal_fix = {
        "primary_fix": {
            "file": "app/domains/relevamientos/schemas/list_filters.py",
            "function": "apply_defaults_and_validate_range",
            "change": (
                "Calcular último día del mes con calendar.monthrange o "
                "date(today.year, today.month + 1, 1) - timedelta(days=1) "
                "en lugar de next_month.day - 1"
            ),
        },
        "secondary_fix": {
            "file": "app/domains/relevamientos/routes/list.py",
            "function": "listar_relevamientos",
            "change": (
                "Usar pydantic_errors_to_cell_map(e) de app.shared.errors "
                "(patrón de actuaciones/denuncias) en lugar de e.errors() crudo"
            ),
        },
        "also_affected": [
            "app/domains/relevamientos/routes/list_operativa.py",
            "app/domains/catalogos/routes/rubros.py",
        ],
    }

    report = {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-FIX.1-DIAG",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "route": {
            "method": "GET",
            "path": "/relevamientos",
            "blueprint": "relevamientos",
            "url_prefix": "/relevamientos",
            "registered_in": "app/main.py",
        },
        "call_graph": [
            "app/main.py → register_blueprint(relevamiento_bp, url_prefix='/relevamientos')",
            "app/domains/relevamientos/routes/__init__.py → Blueprint('relevamientos')",
            "app/domains/relevamientos/routes/list.py → listar_relevamientos()",
            "app/domains/relevamientos/schemas/list_filters.py → RelevamientosListFilters.model_validate()",
            "app/domains/relevamientos/services/list_service.py → listar_relevamientos_con_filtros()",
            "app/domains/relevamientos/presenters/relevamiento_presenter.py → relevamiento_to_row()",
        ],
        "reproduction": {
            "http_cases": http_repro,
            "direct_exception_chain": direct_repro,
        },
        "stack_trace": direct_repro.get("original_traceback"),
        "original_exception": direct_repro.get("original_exception"),
        "secondary_exception": direct_repro.get("secondary_exception"),
        "date_validation_analysis": date_analysis,
        "response_serialization_analysis": {
            "failure_point": "during_validation_before_query",
            "query_never_reached_on_empty_params": True,
            "presenter_ok_when_valid_filters": query_analysis.get("first_row_mapping_succeeds"),
            "error_handler_issue": "e.errors() includes ctx.error ValueError object not JSON-serializable",
            "stable_pattern_elsewhere": "app/shared/errors.py → pydantic_errors_to_cell_map()",
        },
        "query_analysis": query_analysis,
        "relevador_post_cleanup_guard": {
            "relevador_count": baseline["counts"]["relevador"],
            "relevador_id2_exists": baseline["relevador_id2_exists"],
            "orphans": baseline["relevamiento_relevador_orphans"],
            "not_root_cause": True,
            "note": "500 pre-existed before 2E-R; empty-params path fails before DB",
        },
        "trigger_rows": None,
        "data_dependent": False,
        "root_cause": root_cause,
        "minimal_fix_surface": minimal_fix,
        "test_matrix": [
            {"case": "GET /relevamientos sin params", "expected": "200 con rango mes actual"},
            {"case": "GET /relevamientos con desde/hasta válidos", "expected": "200"},
            {"case": "GET /relevamientos rango vacío válido", "expected": "200 items=[]"},
            {"case": "GET /relevamientos fecha inválida", "expected": "422 JSON serializable, no 500"},
            {"case": "GET /relevamientos desde > hasta", "expected": "422"},
            {"case": "default month range en septiembre", "expected": "hasta=2026-09-30"},
            {"case": "default month range en diciembre", "expected": "hasta=YYYY-12-31"},
        ],
        "cleanup_guards": {
            "users": baseline["counts"]["users"],
            "relevador": baseline["counts"]["relevador"],
            "juzgado_catalogo": baseline["counts"]["juzgado_catalogo"],
            "writes_executed": False,
        },
        "error_response_contract": {
            "invalid_filter": "422 con errors serializable (patrón pydantic_errors_to_cell_map)",
            "business_value_error": "400",
            "unexpected": "500 solo para errores no previstos",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"no_params status={http_repro['no_params']['status']}")
    print(f"explicit_range status={http_repro['explicit_range']['status']}")
    print(f"root_cause={root_cause['original_exception']['message']}")


if __name__ == "__main__":
    main()
