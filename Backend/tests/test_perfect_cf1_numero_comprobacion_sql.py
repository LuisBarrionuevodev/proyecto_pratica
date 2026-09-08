"""PERF.1-CF1 — Nº Comprobación operativa filtrado en SQL (expediente / oficio / reinspección)."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
from app.domains.actuaciones.services.pendientes_service import (
    get_pendientes_expediente,
    get_pendientes_oficio,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.models import (
    Actuaciones,
    JuzgadoCatalogo,
    User,
)

from tests.test_comprobacion_oper_ruta_4 import (
    _filters,
    _mk_comp_pendiente_oficio,
    _mk_comp_sin_expediente,
    _mk_reinspeccion_circuito,
    _unique,
)


def _legacy_python_filter_comprobacion(
    acts: list,
    numero_comprobacion: str,
) -> list:
    """Réplica del filtro Python pre-CF1 para regresión de identidad."""
    q = numero_comprobacion.replace(" ", "").lower()
    counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
    out: list = []
    for act in acts:
        row = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
        num = (row.get("acta_comprobacion_num") or "").replace(" ", "").lower()
        if q in num:
            out.append(act)
    return out


def _rein_row_keys_from_filas(filas) -> set[tuple[int, int, int]]:
    keys: set[tuple[int, int, int]] = set()
    for act, ofi, ini in filas:
        keys.add(
            (
                int(act.id),
                int(ofi.id),
                int(ini.id) if ini is not None else 0,
            )
        )
    return keys


def _rein_row_keys_from_route_items(items: list[dict]) -> set[tuple[int, int, int]]:
    return {
        (
            int(i["id"]),
            int(i.get("oficio_id") or 0),
            int(i.get("iniciador_id") or 0),
        )
        for i in items
    }


def _mk_user() -> User:
    u = User(
        username=f"cf1_{_unique()}",
        email=f"cf1_{_unique()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _payload_oficio(juzgado_id: int, *, numero: str, fecha: date, num_exp: str) -> dict:
    return {
        "numero_oficio": numero,
        "fecha_oficio": fecha,
        "juzgado_id": juzgado_id,
        "numero_expediente_oficio": num_exp,
        "fecha_expediente_oficio": fecha,
    }


def _circuito_con_envio(numero_acta: str) -> tuple:
    jz = JuzgadoCatalogo(codigo=f"JZCF{_unique()}"[:32], nombre=f"Jz CF1 {_unique()}")
    db.session.add(jz)
    db.session.flush()
    act = _mk_comp_pendiente_oficio(fecha=date(2026, 9, 1), numero=numero_acta)
    return act, jz


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def test_expediente_sin_filtro_ids_estables(app_ctx) -> None:
    a1 = _mk_comp_sin_expediente(fecha=date(2026, 9, 2))
    a2 = _mk_comp_sin_expediente(fecha=date(2026, 9, 3))
    db.session.commit()
    base = get_pendientes_expediente(_filters())
    assert {int(a.id) for a in base} >= {int(a1.id), int(a2.id)}


def test_expediente_fragmento_coincide_con_legacy(app_ctx) -> None:
    num = _unique()
    act_ok = _mk_comp_sin_expediente(fecha=date(2026, 9, 4), numero=num)
    _mk_comp_sin_expediente(fecha=date(2026, 9, 5), numero=_unique())
    db.session.commit()
    fragment = num[1:5]
    base = get_pendientes_expediente(_filters())
    legacy = _legacy_python_filter_comprobacion(base, fragment)
    new = get_pendientes_expediente(_filters(numero_comprobacion=fragment))
    assert {int(a.id) for a in new} == {int(a.id) for a in legacy}
    assert {int(a.id) for a in new} == {int(act_ok.id)}


def test_oficio_fragmento_coincide_con_legacy(app_ctx) -> None:
    num = _unique()
    act_ok = _mk_comp_pendiente_oficio(fecha=date(2026, 9, 6), numero=num)
    _mk_comp_pendiente_oficio(fecha=date(2026, 9, 7), numero=_unique())
    db.session.commit()
    fragment = num[0:4]
    base = get_pendientes_oficio(ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True}))
    legacy = _legacy_python_filter_comprobacion(base, fragment)
    new = get_pendientes_oficio(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "numero_comprobacion": fragment}
        )
    )
    assert {int(a.id) for a in new} == {int(a.id) for a in legacy}
    assert {int(a.id) for a in new} == {int(act_ok.id)}


def test_reinspeccion_claves_completas_coinciden_con_legacy(app_ctx, client, auth_headers) -> None:
    num = _unique()
    act_ok, ini_ok = _mk_reinspeccion_circuito(fecha=date(2026, 9, 8), numero=num)
    _mk_reinspeccion_circuito(fecha=date(2026, 9, 9), numero=_unique())
    db.session.commit()
    fragment = num[1:5]
    base_filas = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
    )
    legacy_keys: set[tuple[int, int, int]] = set()
    for act, ofi, ini in base_filas:
        comp_num = (getattr(act.comprobacion, "numero_acta", None) or "").replace(" ", "").lower()
        if fragment in comp_num:
            legacy_keys.add((int(act.id), int(ofi.id), int(ini.id) if ini else 0))

    new_filas = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "numero_comprobacion": fragment}
        )
    )
    new_keys = _rein_row_keys_from_filas(new_filas)
    assert new_keys == legacy_keys
    assert ini_ok is not None
    assert (int(act_ok.id), int(ini_ok.oficio_id), int(ini_ok.id)) in new_keys

    rv = client.get(
        "/actuaciones/comprobacion/pendientes-reinspeccion-oficio",
        headers=auth_headers,
        query_string={"omitir_rango_fecha": "true", "numero_comprobacion": fragment},
    )
    assert rv.status_code == 200
    assert _rein_row_keys_from_route_items(rv.get_json()["items"]) == new_keys


def test_reinspeccion_multi_oficio_dos_filas_mismo_numero(app_ctx) -> None:
    """Comprobación C + 2 oficios elegibles → 2 filas al filtrar por fragmento de C."""
    num = f"AB{_unique()[2:]}"
    act, jz = _circuito_con_envio(num)
    db.session.commit()
    num1, num2 = f"O1{_unique()[:3]}", f"O2{_unique()[:3]}"
    r1 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(jz.id, numero=num1, fecha=date(2026, 9, 10), num_exp=_unique()[:6]),
    )
    r2 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(jz.id, numero=num2, fecha=date(2026, 9, 11), num_exp=_unique()[:6]),
    )
    db.session.commit()

    filas = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "numero_comprobacion": num[2:6]}
        )
    )
    keys = _rein_row_keys_from_filas(filas)
    assert len(keys) == 2
    assert (int(act.id), int(r1["oficio"].id), int(r1["iniciador_ruta"].id)) in keys
    assert (int(act.id), int(r2["oficio"].id), int(r2["iniciador_ruta"].id)) in keys


@pytest.mark.parametrize(
    "stored_suffix,query_suffix,should_match",
    [
        ("FULL", "FULL", True),
        ("MID", "MID", True),
        ("NOM", "999", False),
        ("SPC", "12 34", True),
        ("CAS", "abcd", True),
    ],
)
def test_expediente_normalizacion_sql(
    app_ctx, stored_suffix: str, query_suffix: str, should_match: bool
) -> None:
    base_num = _unique()
    if stored_suffix == "FULL":
        stored = base_num
        query = base_num
    elif stored_suffix == "MID":
        stored = base_num
        query = base_num[1:5]
    elif stored_suffix == "NOM":
        stored = base_num
        query = "999999"
    elif stored_suffix == "SPC":
        stored = f"{base_num[:2]} {base_num[2:5]}"
        query = base_num[0:4]
    else:  # CAS
        stored = f"AbCd{base_num[4:]}"
        query = f"abcd{base_num[4:6]}"

    act = _mk_comp_sin_expediente(fecha=date(2026, 9, 12), numero=stored)
    decoy = _mk_comp_sin_expediente(fecha=date(2026, 9, 13), numero=_unique())
    db.session.commit()
    acts = get_pendientes_expediente(_filters(numero_comprobacion=query))
    ids = {int(a.id) for a in acts}
    if should_match:
        assert int(act.id) in ids
        assert int(decoy.id) not in ids
    else:
        assert int(act.id) not in ids


def test_apply_numero_comprobacion_sql_en_query_sin_postfiltro(app_ctx) -> None:
    """El filtro queda en SQL: el acta creada matchea; el decoy no."""
    num = _unique()
    act_ok = _mk_comp_sin_expediente(fecha=date(2026, 9, 14), numero=num)
    decoy = _mk_comp_sin_expediente(fecha=date(2026, 9, 15), numero=_unique())
    db.session.commit()
    con_filtro = get_pendientes_expediente(_filters(numero_comprobacion=num[2:5]))
    ids = {int(a.id) for a in con_filtro}
    assert int(act_ok.id) in ids
    assert int(decoy.id) not in ids
