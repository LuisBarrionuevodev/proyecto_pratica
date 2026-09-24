"""
GESTIÓN-PERF.1-BP1.1 — Nº notificación SQL operativa + canonicalidad.
"""

from __future__ import annotations

import time

import pytest

from app.database import db
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
)
from app.domains.actuaciones.services.pendientes_service import get_pendientes_expediente
from app.models import Actuaciones, Notificacion
from app.utils.actas import acta_6


def _ids(acts) -> list[int]:
    return [int(a.id) for a in acts]


def _filters_en_plazo(**extra) -> ActuacionesPendientesFilters:
    return ActuacionesPendientesFilters.model_validate(
        {
            "source_type": "notificacion",
            "omitir_rango_fecha": True,
            "plazo_slice": "en_plazo",
            **extra,
        }
    )


def _filters_por_vencer(**extra) -> ActuacionesPendientesFilters:
    return ActuacionesPendientesFilters.model_validate(
        {
            "source_type": "notificacion",
            "omitir_rango_fecha": True,
            "plazo_slice": "por_vencer",
            **extra,
        }
    )


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app({"TESTING": True})
    with app.app_context():
        yield app


class TestPerf1Bp11NumeroNotificacionSql:
    """B1–B5 — Nº notificación en SQL, sin filtro documental operativo."""

    def test_b5_sin_filtro_identico_a_bp1(self, app_ctx):
        a = get_pendientes_expediente(_filters_en_plazo())
        b = get_pendientes_expediente(_filters_en_plazo(numero_notificacion=None))
        assert _ids(a) == _ids(b)

    def test_b10_mismo_numero_acta_por_notificacion_id(self, app_ctx):
        rows = (
            db.session.query(Actuaciones.notificacion_id, Notificacion.numero_acta)
            .join(Notificacion, Notificacion.id == Actuaciones.notificacion_id)
            .filter(Actuaciones.notificacion_id.isnot(None))
            .limit(200)
            .all()
        )
        by_noti: dict[int, set[str]] = {}
        for nid, num in rows:
            by_noti.setdefault(int(nid), set()).add(str(num))
        assert all(len(nums) == 1 for nums in by_noti.values())

    def test_b1_numero_en_plazo_coincide_con_subconjunto_manual(self, app_ctx):
        base = get_pendientes_expediente(_filters_en_plazo())
        if not base:
            pytest.skip("sin filas en plazo")
        noti_id = int(base[0].notificacion_id)
        noti = Notificacion.query.get(noti_id)
        assert noti is not None
        short = noti.numero_acta.lstrip("0") or noti.numero_acta
        filtered = get_pendientes_expediente(_filters_en_plazo(numero_notificacion=short))
        manual = [a for a in base if int(a.notificacion_id) == noti_id]
        assert _ids(filtered) == _ids(manual)

    def test_b2_numero_por_vencer_igual_subconjunto(self, app_ctx):
        base = get_pendientes_expediente(_filters_por_vencer())
        if not base:
            pytest.skip("sin filas por vencer")
        noti = Notificacion.query.get(int(base[0].notificacion_id))
        assert noti is not None
        filtered = get_pendientes_expediente(
            _filters_por_vencer(numero_notificacion=noti.numero_acta)
        )
        manual = [a for a in base if int(a.notificacion_id) == int(noti.id)]
        assert _ids(filtered) == _ids(manual)

    def test_b3_numero_reinspeccion_subconjunto(self, app_ctx):
        base = list_reinspeccion_notificacion_operativas()
        if not base:
            pytest.skip("sin reinspección")
        noti = Notificacion.query.get(int(base[0].notificacion_id))
        assert noti is not None
        short = noti.numero_acta.lstrip("0") or noti.numero_acta
        filtered = list_reinspeccion_notificacion_operativas(numero_notificacion=short)
        manual = [a for a in base if int(a.notificacion_id) == int(noti.id)]
        assert _ids(filtered) == _ids(manual)
        assert all(
            a.notificacion.numero_acta == acta_6(short) for a in filtered if a.notificacion
        )

    def test_b4_canonicalidad_no_cambia_actuacion_elegida(self, app_ctx):
        base = get_pendientes_expediente(_filters_en_plazo())
        if not base:
            pytest.skip("sin filas en plazo")
        sample = base[0]
        noti = Notificacion.query.get(int(sample.notificacion_id))
        assert noti is not None
        filtered = get_pendientes_expediente(
            _filters_en_plazo(numero_notificacion=noti.numero_acta)
        )
        assert len(filtered) == 1
        assert int(filtered[0].id) == int(sample.id)

    def test_numero_operativo_rapido_no_documental(self, app_ctx):
        base = get_pendientes_expediente(_filters_en_plazo())
        if not base:
            pytest.skip("sin filas en plazo")
        noti = Notificacion.query.get(int(base[0].notificacion_id))
        assert noti is not None
        t0 = time.perf_counter()
        get_pendientes_expediente(_filters_en_plazo(numero_notificacion=noti.numero_acta))
        ms = (time.perf_counter() - t0) * 1000
        assert ms < 2000, f"filtro numero operativo demasiado lento: {ms:.0f}ms"
