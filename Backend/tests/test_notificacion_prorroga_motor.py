"""Motor único de prórroga: cadena acumulada sobre vencimiento vigente o fecha expediente."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.database import db
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.actuaciones.services.notificacion_plazo_expediente_edit_service import (
    delete_notificacion_prorroga_expediente,
    recalcular_vencimiento_notificacion_desde_expedientes,
    update_notificacion_prorroga_expediente,
)
from app.domains.actuaciones.services.notificacion_timing_service import (
    aplicar_prorroga_a_vencimiento_acumulado,
    calcular_fecha_vencimiento,
    calcular_fecha_vencimiento_desde_expediente_prorroga,
    calcular_vencimiento_notificacion_con_prorrogas,
    inicializar_timing_notificacion,
)
from app.models import Actuaciones, Contribuyente, Domicilio, Expediente, IniciadorRuta, Notificacion, OrdenTrabajo, User
from tests.helpers.fixture_isolation import unique_ot_numero


def _unique_num() -> str:
    return unique_ot_numero()


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_notificacion_actuacion(
    *,
    fecha_notificacion: date | None = None,
    con_iniciador: bool = False,
) -> tuple[Actuaciones, Notificacion, IniciadorRuta | None]:
    user = User.query.filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
    assert user is not None
    contrib = Contribuyente(apellido="Motor", nombre="Prorroga", documento=_unique_num())
    db.session.add(contrib)
    db.session.flush()
    dom = Domicilio(calle="CalleMotor", numero="1", contribuyente_id=contrib.id)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=6)
    db.session.add(noti)
    db.session.flush()
    fn = fecha_notificacion or date(2026, 6, 1)
    inicializar_timing_notificacion(noti, fecha_notificacion=fn)
    act = Actuaciones(
        fecha=fn,
        mes=fn.month,
        anio=fn.year,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        domicilio_id=dom.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    ini = None
    if con_iniciador:
        ini = IniciadorRuta(
            actuacion_id=act.id,
            notificacion_id=noti.id,
            domicilio_id=dom.id,
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            fecha_origen=fn,
            anio=fn.year,
            mes=fn.month,
            created_by_user_id=int(user.id),
        )
        db.session.add(ini)
        db.session.flush()
    return act, noti, ini


def _alta_prorroga(act: Actuaciones, *, fecha_expediente: str, prorroga_dias: int) -> None:
    complete_expediente_from_actuacion(
        act.id,
        {
            "expediente_numero": _unique_num(),
            "fecha_expediente": fecha_expediente,
            "source_type": "NOTIFICACION",
            "prorroga_dias": prorroga_dias,
        },
    )


def _vencimiento_inicial(fn: date, plazo: int = 5) -> date:
    return calcular_fecha_vencimiento(fn, plazo, 0)


# --- Caso clave del hotfix ---


def test_en_plazo_suma_prorroga_al_vencimiento_actual(app_ctx) -> None:
    """Notificación 2026-06-01 plazo 5 → venc 2026-06-08; prórroga 2026-06-04 +2 → 2026-06-10."""
    try:
        fn = date(2026, 6, 1)
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=fn)
        venc_inicial = _vencimiento_inicial(fn)
        assert venc_inicial == date(2026, 6, 8)
        _alta_prorroga(act, fecha_expediente="2026-06-04", prorroga_dias=2)
        db.session.refresh(noti)
        esperado = aplicar_prorroga_a_vencimiento_acumulado(venc_inicial, date(2026, 6, 4), 2)
        assert esperado == date(2026, 6, 10)
        assert noti.fecha_vencimiento == esperado
        assert noti.fecha_vencimiento != calcular_fecha_vencimiento_desde_expediente_prorroga(date(2026, 6, 4), 2)
    finally:
        db.session.rollback()


def test_plazo_inicial_cinco_no_se_pierde_con_prorroga(app_ctx) -> None:
    try:
        fn = date(2026, 6, 1)
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=fn)
        venc_inicial = _vencimiento_inicial(fn)
        _alta_prorroga(act, fecha_expediente="2026-06-04", prorroga_dias=2)
        db.session.refresh(noti)
        assert noti.fecha_vencimiento > venc_inicial
        assert noti.fecha_vencimiento == date(2026, 6, 10)
    finally:
        db.session.rollback()


def test_vencida_calcula_desde_fecha_expediente(app_ctx) -> None:
    try:
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=date(2020, 1, 2))
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=10)
        db.session.refresh(noti)
        esperado = calcular_fecha_vencimiento_desde_expediente_prorroga(date(2026, 6, 28), 10)
        assert noti.fecha_vencimiento == esperado
        assert noti.fecha_vencimiento != calcular_fecha_vencimiento(noti.fecha_notificacion, noti.plazo_dias, 10)
    finally:
        db.session.rollback()


def test_un_dia_restante_suma_prorroga_desde_vencimiento(app_ctx) -> None:
    try:
        fn = date(2026, 6, 1)
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=fn)
        venc = _vencimiento_inicial(fn)
        _alta_prorroga(act, fecha_expediente="2026-06-07", prorroga_dias=3)
        db.session.refresh(noti)
        assert venc >= date(2026, 6, 7)
        assert noti.fecha_vencimiento == aplicar_prorroga_a_vencimiento_acumulado(venc, date(2026, 6, 7), 3)
    finally:
        db.session.rollback()


# --- Helpers hábiles ---


def test_ejemplo_fijo_expediente_mas_plazo_habiles_vencida() -> None:
    """Caso QA vencida: 2026-05-28 + 3 hábiles AR → 2026-06-02."""
    assert calcular_fecha_vencimiento_desde_expediente_prorroga(date(2026, 5, 28), 3) == date(2026, 6, 2)
    assert calcular_fecha_vencimiento_desde_expediente_prorroga(date(2026, 6, 28), 3) == date(2026, 7, 1)


def test_en_plazo_no_usa_solo_fecha_expediente_mas_plazo(app_ctx) -> None:
    """Con plazo vigente, May 28 + 3 no reemplaza el vencimiento inicial."""
    try:
        fn = date(2026, 6, 1)
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=fn)
        venc_inicial = _vencimiento_inicial(fn)
        _alta_prorroga(act, fecha_expediente="2026-05-28", prorroga_dias=3)
        db.session.refresh(noti)
        assert noti.fecha_vencimiento == aplicar_prorroga_a_vencimiento_acumulado(venc_inicial, date(2026, 5, 28), 3)
        assert noti.fecha_vencimiento != date(2026, 6, 2)
    finally:
        db.session.rollback()


def test_vencida_may28_mas_tres_desde_expediente(app_ctx) -> None:
    try:
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=date(2020, 1, 2))
        _alta_prorroga(act, fecha_expediente="2026-05-28", prorroga_dias=3)
        db.session.refresh(noti)
        ex = (
            Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .first()
        )
        assert ex is not None
        assert ex.fecha_expediente == date(2026, 5, 28)
        assert noti.fecha_vencimiento == date(2026, 6, 2)
    finally:
        db.session.rollback()


def test_alta_vencida_usa_fecha_expediente_jun28(app_ctx) -> None:
    try:
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=date(2020, 1, 2))
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=10)
        db.session.refresh(noti)
        assert noti.fecha_vencimiento == calcular_fecha_vencimiento_desde_expediente_prorroga(date(2026, 6, 28), 10)
    finally:
        db.session.rollback()


def test_alta_pendiente_reinspeccion_vencida_usa_fecha_expediente(app_ctx) -> None:
    try:
        act, noti, ini = _mk_notificacion_actuacion(con_iniciador=True)
        assert ini is not None
        noti.fecha_vencimiento = date.today()
        db.session.add(noti)
        db.session.flush()
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=10)
        db.session.refresh(noti)
        assert noti.fecha_vencimiento == calcular_fecha_vencimiento_desde_expediente_prorroga(date(2026, 6, 28), 10)
    finally:
        db.session.rollback()


def test_created_at_y_updated_at_no_afectan_recalculo(app_ctx) -> None:
    try:
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=date(2020, 1, 2))
        _alta_prorroga(act, fecha_expediente="2026-05-28", prorroga_dias=3)
        ex = (
            Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .first()
        )
        assert ex is not None
        ex.created_at = datetime(2026, 6, 28, 23, 25, 46)
        ex.updated_at = datetime(2026, 6, 28, 23, 26, 10)
        noti.fecha_vencimiento = date(2026, 7, 1)
        db.session.add(ex)
        db.session.add(noti)
        db.session.flush()
        recalcular_vencimiento_notificacion_desde_expedientes(noti)
        assert noti.fecha_vencimiento == date(2026, 6, 2)
    finally:
        db.session.rollback()


def test_patch_fecha_expediente_recalcula_cadena(app_ctx) -> None:
    try:
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=date(2020, 1, 2))
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=3)
        db.session.refresh(noti)
        assert noti.fecha_vencimiento == date(2026, 7, 1)
        ex = (
            Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .first()
        )
        assert ex is not None
        update_notificacion_prorroga_expediente(
            act.id,
            ex.id,
            numero_expediente=ex.numero_expediente,
            fecha_expediente=date(2026, 5, 28),
            plazo_otorgado=3,
        )
        db.session.refresh(noti)
        db.session.refresh(ex)
        assert ex.fecha_expediente == date(2026, 5, 28)
        assert noti.fecha_vencimiento == date(2026, 6, 2)
    finally:
        db.session.rollback()


# --- Múltiples prórrogas en cadena ---


def test_dos_prorrogas_cadena_cronologica(app_ctx) -> None:
    try:
        fn = date(2026, 6, 1)
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=fn)
        _alta_prorroga(act, fecha_expediente="2026-06-10", prorroga_dias=3)
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=10)
        db.session.refresh(noti)
        esperado = calcular_vencimiento_notificacion_con_prorrogas(
            fn,
            noti.plazo_dias,
            [(date(2026, 6, 10), 3), (date(2026, 6, 28), 10)],
        )
        assert noti.fecha_vencimiento == esperado
        assert int(noti.prorroga_dias or 0) == 13
    finally:
        db.session.rollback()


def test_dos_prorrogas_misma_fecha_aplica_ambas_en_orden_id(app_ctx) -> None:
    try:
        fn = date(2026, 6, 1)
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=fn)
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=5)
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=10)
        db.session.refresh(noti)
        exps = (
            Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .order_by(Expediente.id.asc())
            .all()
        )
        assert len(exps) == 2
        esperado = calcular_vencimiento_notificacion_con_prorrogas(
            fn,
            noti.plazo_dias,
            [(exps[0].fecha_expediente, int(exps[0].prorroga_dias_otorgados or 0)), (exps[1].fecha_expediente, int(exps[1].prorroga_dias_otorgados or 0))],
        )
        assert noti.fecha_vencimiento == esperado
        assert noti.fecha_vencimiento != calcular_fecha_vencimiento_desde_expediente_prorroga(date(2026, 6, 28), 10)
    finally:
        db.session.rollback()


def test_borrar_ultima_prorroga_recalcula_cadena(app_ctx) -> None:
    try:
        fn = date(2026, 6, 1)
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=fn)
        _alta_prorroga(act, fecha_expediente="2026-06-10", prorroga_dias=4)
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=10)
        ultimo = (
            Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .order_by(Expediente.id.desc())
            .first()
        )
        assert ultimo is not None
        delete_notificacion_prorroga_expediente(act.id, ultimo.id)
        db.session.refresh(noti)
        esperado = calcular_vencimiento_notificacion_con_prorrogas(fn, noti.plazo_dias, [(date(2026, 6, 10), 4)])
        assert noti.fecha_vencimiento == esperado
        assert int(noti.prorroga_dias or 0) == 4
    finally:
        db.session.rollback()


def test_borrar_prorroga_intermedia_bloqueado(app_ctx) -> None:
    try:
        fn = date(2026, 6, 1)
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=fn)
        _alta_prorroga(act, fecha_expediente="2026-06-04", prorroga_dias=2)
        _alta_prorroga(act, fecha_expediente="2026-06-10", prorroga_dias=3)
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=5)
        exps = (
            Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .order_by(Expediente.id.asc())
            .all()
        )
        assert len(exps) == 3
        with pytest.raises(ValueError, match="último expediente"):
            delete_notificacion_prorroga_expediente(act.id, exps[1].id)
    finally:
        db.session.rollback()


def test_borrar_todas_prorrogas_vuelve_vencimiento_inicial(app_ctx) -> None:
    try:
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=date(2026, 6, 1))
        venc_inicial = calcular_fecha_vencimiento(date(2026, 6, 1), noti.plazo_dias, 0)
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=10)
        ex = (
            Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .first()
        )
        assert ex is not None
        delete_notificacion_prorroga_expediente(act.id, ex.id)
        db.session.refresh(noti)
        assert noti.fecha_vencimiento == venc_inicial
        assert int(noti.prorroga_dias or 0) == 0
    finally:
        db.session.rollback()


def test_editar_fecha_expediente_recalcula_cadena(app_ctx) -> None:
    try:
        fn = date(2026, 6, 1)
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=fn)
        _alta_prorroga(act, fecha_expediente="2026-06-04", prorroga_dias=2)
        ex = (
            Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .first()
        )
        assert ex is not None
        update_notificacion_prorroga_expediente(
            act.id,
            ex.id,
            numero_expediente=ex.numero_expediente,
            fecha_expediente=date(2026, 6, 28),
            plazo_otorgado=10,
        )
        db.session.refresh(noti)
        esperado = calcular_vencimiento_notificacion_con_prorrogas(fn, noti.plazo_dias, [(date(2026, 6, 28), 10)])
        assert noti.fecha_vencimiento == esperado
    finally:
        db.session.rollback()


def test_editar_plazo_otorgado_recalcula_cadena(app_ctx) -> None:
    try:
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=date(2020, 1, 2))
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=5)
        ex = (
            Expediente.query.filter_by(notificacion_id=noti.id, tipo_expediente="PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .first()
        )
        assert ex is not None
        update_notificacion_prorroga_expediente(
            act.id,
            ex.id,
            numero_expediente=ex.numero_expediente,
            fecha_expediente=date(2026, 6, 28),
            plazo_otorgado=10,
        )
        db.session.refresh(noti)
        assert noti.fecha_vencimiento == calcular_fecha_vencimiento_desde_expediente_prorroga(date(2026, 6, 28), 10)
    finally:
        db.session.rollback()


# --- Pendiente reinspección ---


def test_pendiente_reinspeccion_prorroga_suficiente_anula_iniciador(app_ctx) -> None:
    try:
        act, noti, ini = _mk_notificacion_actuacion(con_iniciador=True)
        assert ini is not None
        noti.fecha_vencimiento = date.today()
        db.session.add(noti)
        db.session.flush()
        assert act.id in {a.id for a in list_reinspeccion_notificacion_operativas()}
        _alta_prorroga(act, fecha_expediente=date.today().isoformat(), prorroga_dias=15)
        db.session.refresh(noti)
        db.session.refresh(ini)
        assert noti.fecha_vencimiento > date.today()
        assert ini.estado_iniciador == "ANULADO"
        assert act.id not in {a.id for a in list_reinspeccion_notificacion_operativas()}
    finally:
        db.session.rollback()


def test_pendiente_reinspeccion_prorroga_insuficiente_sigue_pendiente(app_ctx) -> None:
    try:
        act, noti, ini = _mk_notificacion_actuacion(con_iniciador=True)
        assert ini is not None
        noti.fecha_vencimiento = date.today()
        db.session.add(noti)
        db.session.flush()
        _alta_prorroga(act, fecha_expediente=date.today().isoformat(), prorroga_dias=0)
        db.session.refresh(noti)
        db.session.refresh(ini)
        assert noti.fecha_vencimiento <= date.today()
        assert ini.estado_iniciador == "PENDIENTE"
        assert act.id in {a.id for a in list_reinspeccion_notificacion_operativas()}
    finally:
        db.session.rollback()


def test_no_duplica_iniciador_tras_prorroga(app_ctx) -> None:
    try:
        act, noti, ini = _mk_notificacion_actuacion(con_iniciador=True)
        assert ini is not None
        noti.fecha_vencimiento = date.today()
        db.session.add(noti)
        db.session.flush()
        _alta_prorroga(act, fecha_expediente=date.today().isoformat(), prorroga_dias=0)
        before = IniciadorRuta.query.filter_by(
            notificacion_id=noti.id,
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            deleted_at=None,
        ).count()
        sync_iniciadores_reinspeccion_notificacion()
        after = IniciadorRuta.query.filter_by(
            notificacion_id=noti.id,
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            deleted_at=None,
        ).count()
        assert before == after == 1
    finally:
        db.session.rollback()


def test_recalcular_desde_expedientes_funcion_publica(app_ctx) -> None:
    try:
        act, noti, _ = _mk_notificacion_actuacion(fecha_notificacion=date(2020, 1, 2))
        _alta_prorroga(act, fecha_expediente="2026-06-28", prorroga_dias=10)
        noti.fecha_vencimiento = date(2000, 1, 1)
        db.session.add(noti)
        db.session.flush()
        recalcular_vencimiento_notificacion_desde_expedientes(noti)
        assert noti.fecha_vencimiento == calcular_fecha_vencimiento_desde_expediente_prorroga(date(2026, 6, 28), 10)
    finally:
        db.session.rollback()
