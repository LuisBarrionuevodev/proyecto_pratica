"""
GESTIÓN-PERF.1-BP1 — filtros operativos Calle + OT en bandeja notificaciones.
"""

from __future__ import annotations

import pytest

from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
)
from app.domains.actuaciones.services.pendientes_service import get_pendientes_expediente


def _ids(acts) -> list[int]:
    return [int(a.id) for a in acts]


def _noti_ids(acts) -> list[int]:
    return sorted({int(a.notificacion_id) for a in acts if a.notificacion_id is not None})


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


class TestPerf1Bp1PoblacionSinFiltro:
    """BP1-T1, T2, T7, T9 — sin filtro nuevo: misma población y orden."""

    def test_bp1_t1_en_plazo_sin_filtro_ids_iguales(self, app_ctx):
        f = _filters_en_plazo()
        a = get_pendientes_expediente(f)
        b = get_pendientes_expediente(_filters_en_plazo(calle_q=None, orden_trabajo=None))
        assert _ids(a) == _ids(b)
        assert len(a) == len(b)

    def test_bp1_t2_por_vencer_sin_filtro_ids_iguales(self, app_ctx):
        f = _filters_por_vencer()
        a = get_pendientes_expediente(f)
        b = get_pendientes_expediente(_filters_por_vencer())
        assert _ids(a) == _ids(b)

    def test_bp1_t3_reinspeccion_sin_filtro_ids_iguales(self, app_ctx):
        a = list_reinspeccion_notificacion_operativas()
        b = list_reinspeccion_notificacion_operativas(calle_q=None, orden_trabajo=None)
        assert _ids(a) == _ids(b)

    def test_bp1_t7_filtros_vacios_no_alteran_en_plazo(self, app_ctx):
        base = get_pendientes_expediente(_filters_en_plazo())
        with_empty = get_pendientes_expediente(
            _filters_en_plazo(calle_q="", orden_trabajo="")
        )
        assert _ids(base) == _ids(with_empty)

    def test_bp1_t9_orden_identico_sin_filtro_nuevo(self, app_ctx):
        a = get_pendientes_expediente(_filters_en_plazo())
        b = get_pendientes_expediente(_filters_en_plazo())
        assert _ids(a) == _ids(b)


class TestPerf1Bp1Filtros:
    """BP1-T4, T5, T6, T8 — filtros Calle / OT."""

    def test_bp1_t4_calle_solo_subconjunto_operativo(self, app_ctx):
        base = get_pendientes_expediente(_filters_en_plazo())
        filtered = get_pendientes_expediente(_filters_en_plazo(calle_q="san martin"))
        base_ids = set(_ids(base))
        assert set(_ids(filtered)).issubset(base_ids)
        for act in filtered:
            calle = (act.domicilio.calle if act.domicilio else "") or ""
            assert "san martin" in calle.lower()

    def test_bp1_t5_ot_exacta_normalizada(self, app_ctx):
        base = get_pendientes_expediente(_filters_en_plazo())
        if not base:
            pytest.skip("sin filas en plazo para probar OT")
        sample = base[0]
        ot_num = sample.orden_trabajo.numero_acta if sample.orden_trabajo else None
        assert ot_num
        short = ot_num.lstrip("0") or ot_num
        filtered = get_pendientes_expediente(_filters_en_plazo(orden_trabajo=short))
        assert all(
            a.orden_trabajo_id == sample.orden_trabajo_id for a in filtered
        )
        assert int(sample.id) in _ids(filtered)

    def test_bp1_t6_calle_y_ot_combinados(self, app_ctx):
        base = get_pendientes_expediente(_filters_en_plazo())
        if not base:
            pytest.skip("sin filas en plazo")
        sample = next(
            (a for a in base if a.domicilio and a.domicilio.calle and a.orden_trabajo),
            None,
        )
        if not sample:
            pytest.skip("sin fila con domicilio y OT")
        calle_term = sample.domicilio.calle.split()[0].lower()
        ot_num = sample.orden_trabajo.numero_acta
        filtered = get_pendientes_expediente(
            _filters_en_plazo(calle_q=calle_term, orden_trabajo=ot_num)
        )
        assert int(sample.id) in _ids(filtered)
        for act in filtered:
            assert calle_term in ((act.domicilio.calle if act.domicilio else "") or "").lower()
            assert act.orden_trabajo_id == sample.orden_trabajo_id

    def test_bp1_t8_dedupe_una_actuacion_por_notificacion(self, app_ctx):
        acts = get_pendientes_expediente(_filters_en_plazo(calle_q="a"))
        assert len(_noti_ids(acts)) == len({a.notificacion_id for a in acts if a.notificacion_id})

    def test_bp1_t4_reinspeccion_calle_subconjunto(self, app_ctx):
        base = list_reinspeccion_notificacion_operativas()
        filtered = list_reinspeccion_notificacion_operativas(calle_q="san martin")
        assert set(_ids(filtered)).issubset(set(_ids(base)))

    def test_bp1_t5_reinspeccion_ot_inexistente_vacio(self, app_ctx):
        out = list_reinspeccion_notificacion_operativas(orden_trabajo="999999")
        assert out == []
