"""Filtro backend ``plazo_slice`` en pendientes/expediente (rama NOTIFICACION)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import (
    _dias_restantes_desde_vencimiento,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.expediente_completion_service import (
    complete_expediente_from_actuacion,
)
from app.domains.actuaciones.services.notificacion_timing_service import (
    inicializar_timing_notificacion,
)
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    get_pendientes_expediente,
)
from app.domains.actuaciones.utils.notificacion_plazo_slice import (
    dias_restantes_notificacion_act,
)
from app.models import Actuaciones, Notificacion, OrdenTrabajo
from tests.helpers.fixture_isolation import unique_ot_numero
from app.shared.utils.business_days_ar import contar_dias_habiles_inclusive


def _unique_num() -> str:
    return unique_ot_numero()


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _fecha_con_dias_habiles_restantes(n: int) -> date:
    """Primera fecha de vencimiento con ``contar_dias_habiles_inclusive(hoy, fecha) == n``."""
    hoy = date.today()
    if n <= 0:
        return hoy - timedelta(days=1)
    cursor = hoy
    for _ in range(120):
        if contar_dias_habiles_inclusive(hoy, cursor) == n:
            return cursor
        cursor += timedelta(days=1)
    raise RuntimeError(f"No se encontró fecha para n={n}")


def _mk_notificacion_act(*, dias_restantes: int) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=6)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 6, 1))
    noti.fecha_vencimiento = _fecha_con_dias_habiles_restantes(dias_restantes)
    act = Actuaciones(
        fecha=date(2026, 6, 1),
        mes=6,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def _filters_notificacion(**extra) -> ActuacionesPendientesFilters:
    base = {
        "omitir_rango_fecha": True,
        "source_type": "notificacion",
    }
    base.update(extra)
    return ActuacionesPendientesFilters.model_validate(base)


def _dias_por_act(acts: list[Actuaciones]) -> dict[int, int | None]:
    _, venc_map, _ = build_notificacion_expediente_bandeja_metrics(acts)
    return {int(a.id): dias_restantes_notificacion_act(a, venc_map) for a in acts}


def test_plazo_slice_en_plazo_solo_dias_mayor_igual_cinco(app_ctx) -> None:
    a_en = _mk_notificacion_act(dias_restantes=8)
    a_pv = _mk_notificacion_act(dias_restantes=3)
    a_cero = _mk_notificacion_act(dias_restantes=0)
    acts = get_pendientes_expediente(_filters_notificacion(plazo_slice="en_plazo"))
    ids = {int(a.id) for a in acts}
    assert a_en.id in ids
    assert a_pv.id not in ids
    assert a_cero.id not in ids
    dias = _dias_por_act(acts)
    assert all(d is not None and d >= 5 for d in dias.values())


def test_plazo_slice_por_vencer_solo_uno_a_cuatro(app_ctx) -> None:
    a_en = _mk_notificacion_act(dias_restantes=10)
    a_pv = _mk_notificacion_act(dias_restantes=2)
    acts = get_pendientes_expediente(_filters_notificacion(plazo_slice="por_vencer"))
    ids = {int(a.id) for a in acts}
    assert a_pv.id in ids
    assert a_en.id not in ids
    dias = _dias_por_act(acts)
    assert all(d is not None and 1 <= d <= 4 for d in dias.values())


def test_plazo_slice_total_sin_filtro_adicional(app_ctx) -> None:
    a_en = _mk_notificacion_act(dias_restantes=10)
    a_pv = _mk_notificacion_act(dias_restantes=2)
    a_cero = _mk_notificacion_act(dias_restantes=0)
    sin = get_pendientes_expediente(_filters_notificacion())
    con_total = get_pendientes_expediente(_filters_notificacion(plazo_slice="total"))
    assert {a.id for a in sin} == {a.id for a in con_total}
    ids = {a.id for a in con_total}
    assert {a_en.id, a_pv.id, a_cero.id}.issubset(ids)


def test_sin_plazo_slice_mantiene_comportamiento(app_ctx) -> None:
    a_en = _mk_notificacion_act(dias_restantes=7)
    acts = get_pendientes_expediente(_filters_notificacion())
    assert a_en.id in {a.id for a in acts}


def test_plazo_slice_ignorado_en_comprobacion(app_ctx) -> None:
    from tests.test_pendientes_expediente_bandeja_notificacion import _mk_actuacion_solo_comprobacion

    act, _comp = _mk_actuacion_solo_comprobacion()
    fl = ActuacionesPendientesFilters.model_validate(
        {
            "omitir_rango_fecha": True,
            "source_type": "comprobacion",
            "plazo_slice": "en_plazo",
        }
    )
    acts = get_pendientes_expediente(fl)
    assert act.id in {a.id for a in acts}


def test_prorroga_recalculada_afecta_slice(app_ctx) -> None:
    act = _mk_notificacion_act(dias_restantes=2)
    assert act.id in {a.id for a in get_pendientes_expediente(_filters_notificacion(plazo_slice="por_vencer"))}
    complete_expediente_from_actuacion(
        act.id,
        {
            "expediente_numero": _unique_num(),
            "fecha_expediente": date.today(),
            "prorroga_dias": 10,
            "source_type": "NOTIFICACION",
        },
    )
    db.session.expire_all()
    noti = db.session.get(Notificacion, act.notificacion_id)
    assert noti is not None
    d = _dias_restantes_desde_vencimiento(noti.fecha_vencimiento)
    assert d is not None and d >= 5
    assert act.id in {a.id for a in get_pendientes_expediente(_filters_notificacion(plazo_slice="en_plazo"))}
    assert act.id not in {a.id for a in get_pendientes_expediente(_filters_notificacion(plazo_slice="por_vencer"))}
