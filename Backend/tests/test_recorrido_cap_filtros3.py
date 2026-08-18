"""FILTROS-3: cap de Recorrido no debe ocultar coincidencias con búsqueda específica."""

from __future__ import annotations

from datetime import date
from secrets import token_hex

import pytest

from app.database import db
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    RECORRIDO_CAP_SIN_BUSQUEDA,
    list_comprobacion_recorrido,
)
from app.models import (
    Actuaciones,
    Comprobacion,
    Contribuyente,
    Domicilio,
    Expediente,
    Oficio,
    OrdenTrabajo,
)


def _unique_num() -> str:
    return token_hex(3)


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_minimal_comp_act(*, numero_acta: str | None = None) -> Actuaciones:
    """Actuación con comprobación mínima (sin domicilio)."""
    n = numero_acta or _unique_num()
    ot = OrdenTrabajo(numero_acta=_unique_num(), mes=1, anio=2026)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=n, mes=1, anio=2026, motivo="filtros3")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 1, 1),
        mes=1,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act


def _mk_comp_con_domicilio(*, calle: str, apellido: str) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), mes=2, anio=2026)
    db.session.add(ot)
    db.session.flush()
    contrib = Contribuyente(apellido=apellido, nombre="Filtro", documento=_unique_num())
    db.session.add(contrib)
    db.session.flush()
    dom = Domicilio(
        calle=calle,
        numero="100",
        cp="4000",
        ciudad="Tucumán",
        provincia="Tucumán",
        pais="Argentina",
        contribuyente_id=contrib.id,
        distrito_id=1,
    )
    db.session.add(dom)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), mes=2, anio=2026, motivo="filtros3 dom")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 2, 1),
        mes=2,
        anio=2026,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act


def _seed_recientes(cantidad: int) -> None:
    """Actuaciones más nuevas (id mayor) que empujan al target fuera del top N por id DESC."""
    for _ in range(cantidad):
        _mk_minimal_comp_act()


def test_recorrido_busqueda_expediente_ignora_cap_previo(app_ctx) -> None:
    """Con búsqueda específica no aplica limit antes del filtro (target fuera del top 3)."""
    try:
        target = _mk_minimal_comp_act(numero_acta="f3exp1")
        db.session.add(
            Expediente(
                comprobacion_id=int(target.comprobacion_id),
                numero_expediente="999001",
                anio="2026",
                fecha_expediente=date(2026, 1, 5),
                tipo_expediente="RESPUESTA_OFICIO",
            )
        )
        db.session.flush()
        _seed_recientes(12)

        fl = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        found = list_comprobacion_recorrido(fl, expediente_numero="999001", limit=3)
        assert target.id in {a.id for a in found}
    finally:
        db.session.rollback()


def test_recorrido_busqueda_oficio_ignora_cap_previo(app_ctx) -> None:
    try:
        target = _mk_minimal_comp_act(numero_acta="f3ofi1")
        db.session.add(
            Oficio(
                comprobacion_id=int(target.comprobacion_id),
                numero_oficio="OFI-F3-999",
                anio=2026,
                fecha_oficio=date(2026, 1, 6),
            )
        )
        db.session.flush()
        _seed_recientes(12)

        fl = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        found = list_comprobacion_recorrido(fl, oficio_numero="OFI-F3-999", limit=3)
        assert target.id in {a.id for a in found}
    finally:
        db.session.rollback()


def test_recorrido_busqueda_acta_ignora_cap_previo(app_ctx) -> None:
    try:
        target = _mk_minimal_comp_act(numero_acta="f3act1")
        _seed_recientes(12)

        fl = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        found = list_comprobacion_recorrido(fl, acta_comprobacion="f3act1", limit=3)
        assert target.id in {a.id for a in found}
        assert len(found) == 1
    finally:
        db.session.rollback()


def test_recorrido_busqueda_calle_ignora_cap_previo(app_ctx) -> None:
    try:
        target = _mk_comp_con_domicilio(calle="CalleUnicaFiltros3", apellido="Zapata")
        _seed_recientes(12)

        fl = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        found = list_comprobacion_recorrido(fl, calle_q="CalleUnicaFiltros3", limit=3)
        assert target.id in {a.id for a in found}
    finally:
        db.session.rollback()


def test_recorrido_sin_busqueda_mantiene_cap(app_ctx) -> None:
    try:
        _seed_recientes(15)
        fl = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        found = list_comprobacion_recorrido(fl, limit=7)
        assert len(found) <= 7
        assert len(found) == 7
    finally:
        db.session.rollback()


def test_recorrido_cap_default_es_500() -> None:
    assert RECORRIDO_CAP_SIN_BUSQUEDA == 500


def test_recorrido_multi_oficio_no_duplica_por_expediente(app_ctx) -> None:
    """Una actuación con dos oficios/expedientes debe aparecer una sola vez."""
    try:
        act = _mk_minimal_comp_act(numero_acta="f3mul1")
        cid = int(act.comprobacion_id)
        ofi1 = Oficio(
            comprobacion_id=cid,
            numero_oficio="MO1",
            anio=2026,
            fecha_oficio=date(2026, 3, 1),
        )
        ofi2 = Oficio(
            comprobacion_id=cid,
            numero_oficio="MO2",
            anio=2026,
            fecha_oficio=date(2026, 3, 2),
        )
        db.session.add_all([ofi1, ofi2])
        db.session.flush()
        db.session.add_all(
            [
                Expediente(
                    comprobacion_id=cid,
                    oficio_id=ofi1.id,
                    numero_expediente="888001",
                    anio="2026",
                    fecha_expediente=date(2026, 3, 3),
                    tipo_expediente="RESPUESTA_OFICIO",
                ),
                Expediente(
                    comprobacion_id=cid,
                    oficio_id=ofi2.id,
                    numero_expediente="888002",
                    anio="2026",
                    fecha_expediente=date(2026, 3, 4),
                    tipo_expediente="RESPUESTA_OFICIO",
                ),
            ]
        )
        db.session.flush()

        fl = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        by_exp2 = list_comprobacion_recorrido(fl, expediente_numero="888002")
        ids = [a.id for a in by_exp2]
        assert ids.count(act.id) == 1
    finally:
        db.session.rollback()
