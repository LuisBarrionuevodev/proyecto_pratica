"""
GESTIÓN-PERF.1-A2 — filtros específicos en listado de actuaciones.
"""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.schemas.list_filters import ActuacionesListFilters
from app.domains.actuaciones.services.list_service import listar_actuaciones_con_filtros
from app.models import (
    Actuaciones,
    Clausura,
    Comprobacion,
    Contribuyente,
    Decomiso,
    Domicilio,
    Inspeccion,
    Inspector,
    Notificacion,
    OrdenTrabajo,
    Rubro,
    Turno,
    actuaciones_inspector,
)
from app.models.turno import TipoTurno


def _unique_ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _unique_suffix() -> str:
    return _unique_ot_num()


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_turno() -> Turno:
    turno = Turno.query.first()
    if turno is None:
        turno = Turno(turno=TipoTurno.MANIANA)
        db.session.add(turno)
        db.session.flush()
    return turno


def _mk_contrib_dom(
    *,
    documento: str,
    apellido: str = "Pérez",
    nombre: str = "Juan",
    razon_social: str | None = None,
    calle: str = "San Martín",
) -> Domicilio:
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=f"Rubro {_unique_suffix()}")
        db.session.add(rub)
        db.session.flush()
    contrib = Contribuyente(
        apellido=apellido,
        nombre=nombre,
        documento=documento,
        razon_social=razon_social,
    )
    db.session.add(contrib)
    db.session.flush()
    dom = Domicilio(calle=calle, numero="100", rubro_id=rub.id, contribuyente_id=contrib.id)
    db.session.add(dom)
    db.session.flush()
    return dom


def _mk_act(
    *,
    ot_num: str | None = None,
    dom: Domicilio | None = None,
    fecha: date | None = None,
    tipo: str | None = None,
) -> Actuaciones:
    num = ot_num or _unique_ot_num()
    ot = OrdenTrabajo(numero_acta=num, anio=2026, mes=5)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha or date(2026, 5, 10),
        mes=5,
        anio=2026,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id if dom else None,
        tipo=tipo,
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_b1_ot_equivalente_a_q_legacy(app_ctx) -> None:
    """B1 — orden_trabajo encuentra la misma actuación que q numérico legacy."""
    try:
        num = _unique_ot_num()
        dom = _mk_contrib_dom(documento=f"{random.randint(10_000_000, 99_999_999)}")
        act = _mk_act(ot_num=num, dom=dom)
        raw = str(int(num))
        r_q = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"q": raw})
        )
        r_ot = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"orden_trabajo": raw})
        )
        assert any(i.id == act.id for i in r_q["items"])
        assert r_ot["meta"]["total"] == 1
        assert r_ot["items"][0].id == act.id
    finally:
        db.session.rollback()


def test_b2_documento_prefijo(app_ctx) -> None:
    try:
        doc = f"{random.randint(10_000_000, 99_999_999)}"
        dom = _mk_contrib_dom(documento=doc, calle=f"CalleDoc{_unique_suffix()}")
        act = _mk_act(dom=dom)
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"documento_q": doc[:6]})
        )
        assert r["meta"]["total"] >= 1
        assert any(i.id == act.id for i in r["items"])
    finally:
        db.session.rollback()


def test_b3_razon_social(app_ctx) -> None:
    try:
        rs = f"Empresa Perf1A {_unique_suffix()}"
        dom = _mk_contrib_dom(
            documento=f"{random.randint(10_000_000, 99_999_999)}",
            razon_social=rs,
            calle=f"CalleRS{_unique_suffix()}",
        )
        act = _mk_act(dom=dom)
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"contribuyente_q": "Empresa Perf1A"})
        )
        assert any(i.id == act.id for i in r["items"])
    finally:
        db.session.rollback()


def test_b4_domicilio_calle(app_ctx) -> None:
    try:
        calle = f"AvSanMartin{_unique_suffix()}"
        dom = _mk_contrib_dom(
            documento=f"{random.randint(10_000_000, 99_999_999)}",
            calle=calle,
        )
        act = _mk_act(dom=dom)
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"calle_q": "SanMartin"})
        )
        assert any(i.id == act.id for i in r["items"])
    finally:
        db.session.rollback()


def test_b5_acta_inspeccion(app_ctx) -> None:
    try:
        num = _unique_ot_num()
        act = _mk_act()
        insp = Inspeccion(numero_acta=num, anio=2026, mes=5, actuacion_id=act.id)
        db.session.add(insp)
        db.session.flush()
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"acta_inspeccion": str(int(num))})
        )
        assert r["meta"]["total"] == 1
        assert r["items"][0].id == act.id
    finally:
        db.session.rollback()


def test_b6_acta_notificacion(app_ctx) -> None:
    try:
        num = _unique_ot_num()
        notif = Notificacion(numero_acta=num, anio=2026, mes=5)
        db.session.add(notif)
        db.session.flush()
        act = _mk_act()
        act.notificacion_id = notif.id
        db.session.flush()
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"acta_notificacion": str(int(num))})
        )
        assert r["meta"]["total"] == 1
        assert r["items"][0].id == act.id
    finally:
        db.session.rollback()


def test_b7_acta_comprobacion(app_ctx) -> None:
    try:
        num = _unique_ot_num()
        comp = Comprobacion(numero_acta=num, anio=2026, mes=5)
        db.session.add(comp)
        db.session.flush()
        act = _mk_act()
        act.comprobacion_id = comp.id
        db.session.flush()
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"acta_comprobacion": str(int(num))})
        )
        assert r["meta"]["total"] == 1
        assert r["items"][0].id == act.id
    finally:
        db.session.rollback()


def test_b8_acta_clausura(app_ctx) -> None:
    try:
        num = _unique_ot_num()
        act = _mk_act()
        cl = Clausura(numero_acta=num, anio=2026, mes=5, actuacion_id=act.id)
        db.session.add(cl)
        db.session.flush()
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"acta_clausura": str(int(num))})
        )
        assert r["meta"]["total"] == 1
        assert r["items"][0].id == act.id
    finally:
        db.session.rollback()


def test_b9_acta_decomiso(app_ctx) -> None:
    try:
        num = _unique_ot_num()
        act = _mk_act()
        dec = Decomiso(numero_acta=num, anio=2026, mes=5, actuacion_id=act.id, cantidad=1)
        db.session.add(dec)
        db.session.flush()
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"acta_decomiso": str(int(num))})
        )
        assert r["meta"]["total"] == 1
        assert r["items"][0].id == act.id
    finally:
        db.session.rollback()


def test_b10_inspector_sin_duplicar(app_ctx) -> None:
    try:
        act = _mk_act()
        turno = _mk_turno()
        ins1 = Inspector(nombre=f"InspA {_unique_suffix()}", legajo=_unique_ot_num()[:5], turno_id=turno.id)
        ins2 = Inspector(nombre=f"InspB {_unique_suffix()}", legajo=_unique_ot_num()[:5], turno_id=turno.id)
        db.session.add_all([ins1, ins2])
        db.session.flush()
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id, inspector_id=ins1.id
            )
        )
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id, inspector_id=ins2.id
            )
        )
        db.session.flush()
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"inspector_id": ins1.id})
        )
        assert r["meta"]["total"] == 1
        assert len(r["items"]) == 1
        assert r["items"][0].id == act.id
    finally:
        db.session.rollback()


def test_b11_combinacion_fecha_inspector_tipo_acta(app_ctx) -> None:
    try:
        num = _unique_ot_num()
        comp = Comprobacion(numero_acta=num, anio=2026, mes=5)
        db.session.add(comp)
        db.session.flush()
        act = _mk_act(fecha=date(2026, 6, 15), tipo="INSPECCION")
        act.comprobacion_id = comp.id
        db.session.flush()
        turno = _mk_turno()
        ins = Inspector(nombre=f"InspC {_unique_suffix()}", legajo=_unique_ot_num()[:5], turno_id=turno.id)
        db.session.add(ins)
        db.session.flush()
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id, inspector_id=ins.id
            )
        )
        db.session.flush()
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate(
                {
                    "desde": "2026-06-01",
                    "hasta": "2026-06-30",
                    "inspector_id": ins.id,
                    "tipo": "INSPECCION",
                    "acta_comprobacion": str(int(num)),
                }
            )
        )
        assert r["meta"]["total"] == 1
        assert r["items"][0].id == act.id
    finally:
        db.session.rollback()


def test_b12_paginacion_sin_solapamiento(app_ctx) -> None:
    try:
        doc = f"{random.randint(10_000_000, 99_999_999)}"
        ids = []
        for _ in range(3):
            dom = _mk_contrib_dom(documento=doc, calle=f"Pag{_unique_suffix()}")
            ids.append(_mk_act(dom=dom).id)
        p1 = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate(
                {"documento_q": doc, "page": 1, "page_size": 2}
            )
        )
        p2 = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate(
                {"documento_q": doc, "page": 2, "page_size": 2}
            )
        )
        assert p1["meta"]["total"] == 3
        assert len(p1["items"]) == 2
        assert len(p2["items"]) == 1
        all_ids = [i.id for i in p1["items"]] + [i.id for i in p2["items"]]
        assert len(set(all_ids)) == 3
        assert set(all_ids) == set(ids)
    finally:
        db.session.rollback()


def test_b13_total_coincide_con_ids_unicos(app_ctx) -> None:
    try:
        calle = f"TotalUnique{_unique_suffix()}"
        for _ in range(2):
            dom = _mk_contrib_dom(
                documento=f"{random.randint(10_000_000, 99_999_999)}",
                calle=calle,
            )
            _mk_act(dom=dom)
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"calle_q": "TotalUnique"})
        )
        assert r["meta"]["total"] == len(r["items"]) or r["meta"]["total"] >= 2
        assert r["meta"]["total"] == 2
    finally:
        db.session.rollback()


def test_b14_q_legacy_sigue_funcionando(app_ctx) -> None:
    try:
        calle = f"LegacyQ{_unique_suffix()}"
        dom = _mk_contrib_dom(
            documento=f"{random.randint(10_000_000, 99_999_999)}",
            calle=calle,
        )
        act = _mk_act(dom=dom)
        r = listar_actuaciones_con_filtros(
            ActuacionesListFilters.model_validate({"q": "LegacyQ"})
        )
        assert any(i.id == act.id for i in r["items"])
    finally:
        db.session.rollback()
