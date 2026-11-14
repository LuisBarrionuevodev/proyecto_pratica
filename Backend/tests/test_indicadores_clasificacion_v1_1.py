"""
V1.1-INDICADORES-CLASIFICACION.1: cargas manuales + denuncias en Inspección.
"""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.domains.indicadores.services.indicadores_no_realizadas_service import (
    build_indicadores_no_realizadas,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    count_cierres_realizados,
)
from app.domains.indicadores.services.indicadores_productividad_service import (
    build_indicadores_productividad,
)
from app.models import (
    Actuaciones,
    Contribuyente,
    Distrito,
    Domicilio,
    Inspector,
    OrdenTrabajo,
    Rubro,
    Turno,
    actuaciones_inspector,
)
from app.models.turno import TipoTurno
from tests.helpers.fixture_isolation import unique_ot_numero
from tests.indicadores_cierre_fixtures import (
    vincular_cierre_no_realizado,
    vincular_cierre_realizado,
)

_DESDE = date(2098, 3, 1)
_HASTA = date(2098, 3, 31)
_FECHA = date(2098, 3, 12)


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{unique_ot_numero()}"


def _mk_inspector() -> Inspector:
    turno = Turno.query.first()
    if turno is None:
        turno = Turno(turno=TipoTurno.MANIANA)
        db.session.add(turno)
        db.session.flush()
    ins = Inspector(
        nombre=_unique_name("InspClf"),
        legajo=unique_ot_numero()[:5],
        turno_id=turno.id,
    )
    db.session.add(ins)
    db.session.flush()
    return ins


def _mk_domicilio(*, distrito_id: int | None = None) -> Domicilio:
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=_unique_name("RubClf"))
        db.session.add(rub)
        db.session.flush()
    c = Contribuyente(
        apellido="Clf",
        nombre="T",
        documento=str(random.randint(10_000_000, 99_999_999)),
    )
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(
        calle=_unique_name("CalleClf"),
        numero="1",
        rubro_id=rub.id,
        contribuyente_id=c.id,
        distrito_id=distrito_id,
    )
    db.session.add(dom)
    db.session.flush()
    return dom


def _mk_manual(
    fecha: date,
    *,
    inspector_id: int | None = None,
    domicilio_id: int | None = None,
    orden_trabajo_id: int | None = None,
    contraproducencia: str | None = None,
) -> Actuaciones:
    if orden_trabajo_id is None:
        ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=fecha.year, mes=fecha.month)
        db.session.add(ot)
        db.session.flush()
        orden_trabajo_id = ot.id
    act = Actuaciones(
        fecha=fecha,
        mes=fecha.month,
        anio=fecha.year,
        tipo="INSPECCION",
        orden_trabajo_id=orden_trabajo_id,
        domicilio_id=domicilio_id,
        contraproducencia=contraproducencia,
    )
    db.session.add(act)
    db.session.flush()
    if inspector_id is not None:
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id,
                inspector_id=inspector_id,
            )
        )
    return act


def _find_insp(inspector_id: int, rows):
    return next((r for r in rows if r.inspector_id == inspector_id), None)


def test_manual_exitosa_aparece_en_periodo_con_inspectores(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        ins_b = _mk_inspector()
        dom = _mk_domicilio()
        antes_ej = build_indicadores_ejecutivo(_DESDE, _HASTA)
        act = _mk_manual(_FECHA, inspector_id=ins.id, domicilio_id=dom.id)
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id,
                inspector_id=ins_b.id,
            )
        )
        db.session.flush()

        ej = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert ej.kpis.actuaciones_realizadas == antes_ej.kpis.actuaciones_realizadas + 1
        assert ej.kpis.inspecciones_realizadas == antes_ej.kpis.inspecciones_realizadas + 1

        prod = build_indicadores_productividad(_DESDE, _HASTA)
        row_a = _find_insp(ins.id, prod.inspectores_realizadas)
        row_b = _find_insp(ins_b.id, prod.inspectores_realizadas)
        assert row_a is not None and row_b is not None
        assert row_a.inspecciones >= 1
        assert row_b.inspecciones >= 1
        assert row_a.total_realizadas == (
            row_a.inspecciones
            + row_a.reinspecciones_oficio
            + row_a.reinspecciones_notificacion
        )
    finally:
        db.session.rollback()


def test_manual_contraproducencia_cuenta_no_realizada(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        antes_nr = build_indicadores_no_realizadas(_DESDE, _HASTA)
        _mk_manual(
            _FECHA,
            inspector_id=ins.id,
            domicilio_id=dom.id,
            contraproducencia="LOCAL_CERRADO",
        )
        db.session.flush()

        nr = build_indicadores_no_realizadas(_DESDE, _HASTA)
        assert nr.por_tipo.inspeccion == antes_nr.por_tipo.inspeccion + 1
        local_antes = next(
            (i.cantidad for i in antes_nr.contraproducencias_resumen if i.bucket == "local_cerrado"),
            0,
        )
        local_desp = next(
            (i.cantidad for i in nr.contraproducencias_resumen if i.bucket == "local_cerrado"),
            0,
        )
        assert local_desp == local_antes + 1

        prod = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_insp(ins.id, prod.inspectores_no_realizadas)
        assert row is not None
        assert row.local_cerrado >= 1
        assert _find_insp(ins.id, prod.inspectores_realizadas) is None
    finally:
        db.session.rollback()


def test_manual_misma_ot_con_cierre_ruta_cuenta_una_vez(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        act = _mk_manual(_FECHA, inspector_id=ins.id, domicilio_id=dom.id)
        db.session.flush()

        ej_manual = build_indicadores_ejecutivo(_DESDE, _HASTA, inspector_id=ins.id)
        assert ej_manual.kpis.actuaciones_realizadas == 1
        assert count_cierres_realizados(_DESDE, _HASTA, inspector_id=ins.id) == 0

        vincular_cierre_realizado(act, _FECHA, inspector_id=ins.id)
        db.session.flush()

        ej = build_indicadores_ejecutivo(_DESDE, _HASTA, inspector_id=ins.id)
        assert count_cierres_realizados(_DESDE, _HASTA, inspector_id=ins.id) == 1
        assert ej.kpis.actuaciones_realizadas == 1
        assert ej.kpis.inspecciones_realizadas == 1

        prod = build_indicadores_productividad(_DESDE, _HASTA, inspector_id=ins.id)
        row = _find_insp(ins.id, prod.inspectores_realizadas)
        assert row is not None
        assert row.total_realizadas == 1
        assert row.inspecciones == 1
    finally:
        db.session.rollback()


def test_inspeccion_y_reinspeccion_ot_distintas_mismo_domicilio(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        act_a = _mk_manual(_FECHA, inspector_id=ins.id, domicilio_id=dom.id)
        act_b = _mk_manual(_FECHA, inspector_id=ins.id, domicilio_id=dom.id)
        vincular_cierre_realizado(act_a, _FECHA, inspector_id=ins.id, tipo_iniciador="RELEVAMIENTO")
        vincular_cierre_realizado(
            act_b, _FECHA, inspector_id=ins.id, tipo_iniciador="REINSPECCION_NOTIFICACION"
        )
        db.session.flush()

        prod = build_indicadores_productividad(_DESDE, _HASTA, inspector_id=ins.id)
        row = _find_insp(ins.id, prod.inspectores_realizadas)
        assert row is not None
        assert row.inspecciones == 1
        assert row.reinspecciones_notificacion == 1
        assert row.total_realizadas == 2
    finally:
        db.session.rollback()


def test_denuncia_realizada_suma_en_inspeccion_sin_doblar_total(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        act = _mk_manual(_FECHA, inspector_id=ins.id, domicilio_id=dom.id)
        vincular_cierre_realizado(
            act, _FECHA, inspector_id=ins.id, tipo_iniciador="DENUNCIA"
        )
        db.session.flush()
        prod = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_insp(ins.id, prod.inspectores_realizadas)
        assert row is not None
        assert row.inspecciones >= 1
        assert row.denuncias == 0
        assert row.otras == 0
        visible = (
            row.inspecciones
            + row.reinspecciones_oficio
            + row.reinspecciones_notificacion
        )
        assert row.total_realizadas == visible
        assert row.total_realizadas == row.inspecciones
        ej = build_indicadores_ejecutivo(_DESDE, _HASTA)
        # La card usa el mismo bucket: +1, no +2.
        assert ej.kpis.inspecciones_realizadas >= 1
    finally:
        db.session.rollback()


def test_card_denuncia_realizada_incrementa_inspecciones_en_uno(app_ctx) -> None:
    """Una denuncia realizada suma 1 a la card, no 2."""
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        actas_antes = antes.kpis.actas_labradas
        act = _mk_manual(_FECHA, inspector_id=ins.id, domicilio_id=dom.id)
        vincular_cierre_realizado(
            act, _FECHA, inspector_id=ins.id, tipo_iniciador="DENUNCIA"
        )
        db.session.flush()
        ej = build_indicadores_ejecutivo(_DESDE, _HASTA)
        ej_ins = build_indicadores_ejecutivo(_DESDE, _HASTA, inspector_id=ins.id)
        assert ej.kpis.inspecciones_realizadas == antes.kpis.inspecciones_realizadas + 1
        assert ej.kpis.actuaciones_realizadas == antes.kpis.actuaciones_realizadas + 1
        assert ej.kpis.actas_labradas == actas_antes
        assert ej_ins.kpis.inspecciones_realizadas == 1
        prod = build_indicadores_productividad(_DESDE, _HASTA, inspector_id=ins.id)
        row = _find_insp(ins.id, prod.inspectores_realizadas)
        assert row is not None
        assert row.inspecciones == 1
        assert row.inspecciones == ej_ins.kpis.inspecciones_realizadas
    finally:
        db.session.rollback()


def test_card_manual_inspeccion_respeta_filtro_inspector(app_ctx) -> None:
    try:
        ins_a = _mk_inspector()
        ins_b = _mk_inspector()
        dom = _mk_domicilio()
        _mk_manual(_FECHA, inspector_id=ins_a.id, domicilio_id=dom.id)
        db.session.flush()
        ej_a = build_indicadores_ejecutivo(_DESDE, _HASTA, inspector_id=ins_a.id)
        ej_b = build_indicadores_ejecutivo(_DESDE, _HASTA, inspector_id=ins_b.id)
        assert ej_a.kpis.inspecciones_realizadas == 1
        assert ej_b.kpis.inspecciones_realizadas == 0
    finally:
        db.session.rollback()


def test_card_denuncia_no_realizada_no_incrementa_inspecciones(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        act = _mk_manual(_FECHA, inspector_id=ins.id, domicilio_id=dom.id)
        vincular_cierre_no_realizado(
            act,
            _FECHA,
            tipo_iniciador="DENUNCIA",
            inspector_id=ins.id,
            contraproducencia="LOCAL_CERRADO",
        )
        db.session.flush()
        ej = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert ej.kpis.inspecciones_realizadas == antes.kpis.inspecciones_realizadas
        assert ej.kpis.actuaciones_realizadas == antes.kpis.actuaciones_realizadas
    finally:
        db.session.rollback()


def test_filtros_inspector_y_distrito_en_manual(app_ctx) -> None:
    try:
        distritos = Distrito.query.limit(2).all()
        if len(distritos) < 2:
            pytest.skip("Se requieren al menos 2 distritos.")
        d_a, d_b = distritos[0], distritos[1]
        ins_a = _mk_inspector()
        ins_b = _mk_inspector()
        dom_a = _mk_domicilio(distrito_id=d_a.id)
        dom_b = _mk_domicilio(distrito_id=d_b.id)
        _mk_manual(_FECHA, inspector_id=ins_a.id, domicilio_id=dom_a.id)
        _mk_manual(_FECHA, inspector_id=ins_b.id, domicilio_id=dom_b.id)
        db.session.flush()

        prod_a = build_indicadores_productividad(
            _DESDE, _HASTA, inspector_id=ins_a.id, distrito_id=d_a.id
        )
        ids_a = {r.inspector_id for r in prod_a.inspectores_realizadas}
        assert ins_a.id in ids_a
        assert ins_b.id not in ids_a

        ej_b = build_indicadores_ejecutivo(_DESDE, _HASTA, distrito_id=d_b.id)
        ej_a = build_indicadores_ejecutivo(_DESDE, _HASTA, distrito_id=d_a.id)
        assert ej_a.kpis.actuaciones_realizadas >= 1
        assert ej_b.kpis.actuaciones_realizadas >= 1
        prod_b = build_indicadores_productividad(_DESDE, _HASTA, distrito_id=d_b.id)
        assert _find_insp(ins_b.id, prod_b.inspectores_realizadas) is not None
        assert _find_insp(ins_a.id, prod_b.inspectores_realizadas) is None
    finally:
        db.session.rollback()


def test_otras_contraproducencia_intacta_y_kilos_ratificados_sin_manual(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        antes_ej = build_indicadores_ejecutivo(_DESDE, _HASTA)
        antes_nr = build_indicadores_no_realizadas(_DESDE, _HASTA)
        otras_antes = next(
            (i.cantidad for i in antes_nr.contraproducencias_resumen if i.bucket == "otras"),
            0,
        )
        _mk_manual(
            _FECHA,
            inspector_id=ins.id,
            domicilio_id=dom.id,
            contraproducencia="OTRO",
        )
        db.session.flush()
        nr = build_indicadores_no_realizadas(_DESDE, _HASTA)
        otras_desp = next(
            (i.cantidad for i in nr.contraproducencias_resumen if i.bucket == "otras"),
            0,
        )
        assert otras_desp == otras_antes + 1
        labels = {i.label for i in nr.contraproducencias_resumen}
        assert "Otras" in labels

        ej = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert ej.kpis.kilos_ratificados == antes_ej.kpis.kilos_ratificados
        prod = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_insp(ins.id, prod.inspectores_no_realizadas)
        assert row is not None
        assert row.otras >= 1
    finally:
        db.session.rollback()


def test_manual_fuera_de_periodo_no_cuenta(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        _mk_manual(date(2098, 4, 2), inspector_id=ins.id, domicilio_id=dom.id)
        db.session.flush()
        despues = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert despues.kpis.actuaciones_realizadas == antes.kpis.actuaciones_realizadas
    finally:
        db.session.rollback()
