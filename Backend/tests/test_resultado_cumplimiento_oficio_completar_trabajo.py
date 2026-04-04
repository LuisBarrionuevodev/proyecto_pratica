"""Etapa 1: resultado_cumplimiento_oficio (REINSPECCION_OFICIO) en Completar trabajo."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import CompletarTrabajoCierreCompletoIn
from app.domains.actuaciones.services.completar_trabajo_cierre_service import _persist_resultado_cumplimiento_oficio
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import ContrapBucket


def test_schema_acepta_cumple_y_no_cumple(app) -> None:
    with app.app_context():
        a = CompletarTrabajoCierreCompletoIn(resultado_cumplimiento_oficio="CUMPLE")
        b = CompletarTrabajoCierreCompletoIn(resultado_cumplimiento_oficio="NO_CUMPLE")
    assert a.resultado_cumplimiento_oficio == "CUMPLE"
    assert b.resultado_cumplimiento_oficio == "NO_CUMPLE"


def test_schema_rechaza_valor_invalido(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            CompletarTrabajoCierreCompletoIn(resultado_cumplimiento_oficio="OTRO")


def test_schema_rechaza_resultado_con_contraproducencia(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                contraproducencia="LOCAL CERRADO",
                resultado_cumplimiento_oficio="CUMPLE",
            )
    assert "resultado_cumplimiento_oficio" in str(exc.value) or "contraproducencia" in str(exc.value).lower()


def test_persist_cumple_reinspeccion_oficio(app) -> None:
    act = SimpleNamespace(resultado_cumplimiento_oficio=None)
    ini = SimpleNamespace(tipo_iniciador="REINSPECCION_OFICIO")
    with app.app_context():
        p = CompletarTrabajoCierreCompletoIn(resultado_cumplimiento_oficio="CUMPLE")
        _persist_resultado_cumplimiento_oficio(act, ini, p, bucket=ContrapBucket.NONE)
    assert act.resultado_cumplimiento_oficio == "CUMPLE"


def test_persist_rechaza_si_no_es_reinspeccion_oficio(app) -> None:
    act = SimpleNamespace(resultado_cumplimiento_oficio=None)
    ini = SimpleNamespace(tipo_iniciador="RELEVAMIENTO")
    with app.app_context():
        p = CompletarTrabajoCierreCompletoIn(resultado_cumplimiento_oficio="CUMPLE")
        with pytest.raises(ValueError, match="solo aplica a REINSPECCION_OFICIO"):
            _persist_resultado_cumplimiento_oficio(act, ini, p, bucket=ContrapBucket.NONE)


def test_persist_rechaza_si_visita_no_realizada(app) -> None:
    act = SimpleNamespace(resultado_cumplimiento_oficio=None)
    ini = SimpleNamespace(tipo_iniciador="REINSPECCION_OFICIO")
    with app.app_context():
        p = CompletarTrabajoCierreCompletoIn(resultado_cumplimiento_oficio="NO_CUMPLE")
        with pytest.raises(ValueError, match="visita está realizada"):
            _persist_resultado_cumplimiento_oficio(act, ini, p, bucket=ContrapBucket.REINGRESO_PRIORIDAD_ALTA)


def test_persist_no_toca_columna_si_none(app) -> None:
    sentinel = object()
    act = SimpleNamespace(resultado_cumplimiento_oficio=sentinel)
    ini = SimpleNamespace(tipo_iniciador="REINSPECCION_OFICIO")
    with app.app_context():
        p = CompletarTrabajoCierreCompletoIn()
        _persist_resultado_cumplimiento_oficio(act, ini, p, bucket=ContrapBucket.NONE)
    assert act.resultado_cumplimiento_oficio is sentinel


def test_grid_row_expone_resultado_cumplimiento_oficio(app) -> None:
    """Lectura mínima vía presenter (sin persistir en DB)."""
    from datetime import date

    with app.app_context():
        act = SimpleNamespace(
            id=1,
            fecha=date(2026, 1, 1),
            mes=1,
            anio=2026,
            tipo="REINSPECCION",
            contraproducencia=None,
            resultado_cumplimiento_oficio="NO_CUMPLE",
            nombre_local=None,
            orden_trabajo=None,
            domicilio=None,
            inspector=[],
            notificacion_id=None,
            comprobacion_id=None,
            notificacion=None,
            comprobacion=None,
        )
        row = actuacion_to_grid_row(act)  # type: ignore[arg-type]
    assert row.get("resultado_cumplimiento_oficio") == "NO_CUMPLE"
