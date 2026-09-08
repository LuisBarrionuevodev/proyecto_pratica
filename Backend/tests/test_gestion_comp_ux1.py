"""GESTIÓN-COMP-UX.1 — filtros por tab (expediente envío, oficio/expediente por fila reinspección)."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
from app.domains.actuaciones.services.pendientes_service import get_pendientes_oficio
from app.models import Expediente

from tests.test_comprobacion_oper_ruta_4 import (
    _mk_comp_pendiente_oficio,
    _mk_reinspeccion_circuito,
    _unique,
)
from tests.test_perfect_cf1_numero_comprobacion_sql import (
    _circuito_con_envio,
    _payload_oficio,
    _rein_row_keys_from_filas,
)


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def test_oficio_filtra_por_expediente_envio_sin_respuesta(app_ctx) -> None:
    """Solo expediente de envío (`oficio_id` NULL); respuesta de otro circuito no matchea."""
    num_env = _unique()[:6]
    num_resp = _unique()[:6]
    act_ok = _mk_comp_pendiente_oficio(fecha=date(2026, 10, 1))
    ex_ok = (
        Expediente.query.filter_by(comprobacion_id=act_ok.comprobacion_id, oficio_id=None)
        .filter(Expediente.deleted_at.is_(None))
        .first()
    )
    assert ex_ok is not None
    ex_ok.numero_expediente = num_env
    act_other = _mk_comp_pendiente_oficio(fecha=date(2026, 10, 2))
    db.session.commit()

    base = get_pendientes_oficio(ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True}))
    base_ids = {int(a.id) for a in base}
    assert int(act_ok.id) in base_ids
    assert int(act_other.id) in base_ids

    matched = get_pendientes_oficio(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "expediente_envio_numero": num_env[0:4]}
        )
    )
    assert {int(a.id) for a in matched} == {int(act_ok.id)}

    not_matched_resp = get_pendientes_oficio(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "expediente_envio_numero": num_resp}
        )
    )
    assert int(act_ok.id) not in {int(a.id) for a in not_matched_resp}


def test_oficio_expediente_envio_ids_estables_sin_filtro(app_ctx) -> None:
    a1 = _mk_comp_pendiente_oficio(fecha=date(2026, 10, 3))
    a2 = _mk_comp_pendiente_oficio(fecha=date(2026, 10, 4))
    db.session.commit()
    base = get_pendientes_oficio(ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True}))
    base_ids = {int(a.id) for a in base}
    filtered = get_pendientes_oficio(
        ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True, "expediente_envio_numero": ""})
    )
    assert {int(a.id) for a in filtered} == base_ids
    assert int(a1.id) in base_ids
    assert int(a2.id) in base_ids


def test_reinspeccion_multi_oficio_filtros_por_fila(app_ctx) -> None:
    """C1 con O1/R1 e O2/R2: filtros scoped a oficio/expediente respuesta de cada fila."""
    num = f"UX{_unique()[2:]}"
    act, jz = _circuito_con_envio(num)
    db.session.commit()
    num_o1 = f"OF1{_unique()[:4]}"
    num_o2 = f"OF2{_unique()[:4]}"
    exp_r1 = _unique()[:6]
    exp_r2 = _unique()[:6]
    r1 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(jz.id, numero=num_o1, fecha=date(2026, 10, 5), num_exp=exp_r1),
    )
    r2 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(jz.id, numero=num_o2, fecha=date(2026, 10, 6), num_exp=exp_r2),
    )
    db.session.commit()

    base_filas = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
    )
    act_id = int(act.id)
    base_keys = {k for k in _rein_row_keys_from_filas(base_filas) if k[0] == act_id}
    assert len(base_keys) == 2
    k1 = (act_id, int(r1["oficio"].id), int(r1["iniciador_ruta"].id))
    k2 = (act_id, int(r2["oficio"].id), int(r2["iniciador_ruta"].id))
    assert k1 in base_keys
    assert k2 in base_keys

    def keys_for_act(filas) -> set[tuple[int, int, int]]:
        return {k for k in _rein_row_keys_from_filas(filas) if k[0] == act_id}

    by_comp = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "numero_comprobacion": num[2:6]}
        )
    )
    assert keys_for_act(by_comp) == base_keys

    by_o1 = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "numero_oficio": num_o1[0:5]}
        )
    )
    assert keys_for_act(by_o1) == {k1}

    by_o2 = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "numero_oficio": num_o2[0:5]}
        )
    )
    assert keys_for_act(by_o2) == {k2}

    by_r1 = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "expediente_respuesta_numero": exp_r1[0:4]}
        )
    )
    assert keys_for_act(by_r1) == {k1}

    by_r2 = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "expediente_respuesta_numero": exp_r2[0:4]}
        )
    )
    assert keys_for_act(by_r2) == {k2}

    combined = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate(
            {
                "omitir_rango_fecha": True,
                "numero_comprobacion": num[2:6],
                "numero_oficio": num_o2[0:5],
                "expediente_respuesta_numero": exp_r2[0:4],
            }
        )
    )
    assert keys_for_act(combined) == {k2}


def test_reinspeccion_sin_filtro_keys_estables(app_ctx) -> None:
    act, ini = _mk_reinspeccion_circuito(fecha=date(2026, 10, 7))
    db.session.commit()
    filas = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
    )
    keys = _rein_row_keys_from_filas(filas)
    assert ini is not None
    assert (int(act.id), int(ini.oficio_id), int(ini.id)) in keys
