"""V1.1-SEGUIMIENTO.1 — seguimiento de reinspección en historiales (solo lectura)."""

from __future__ import annotations

import random
from datetime import date

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_detalle,
    comprobacion_recorrido_resumen_row,
)
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    build_reinspeccion_comprobacion_por_actuacion_id,
    build_seguimiento_notificacion_por_actuacion_id,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.models import (
    Actuaciones,
    Comprobacion,
    Domicilio,
    Expediente,
    IniciadorRuta,
    Notificacion,
    NotificacionResultadoReinspeccion,
    Oficio,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_user() -> User:
    u = User(
        username=f"seg_h_{_unique_num()}",
        email=f"seg_h_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _row_notificacion(act: Actuaciones) -> dict:
    acts = [act]
    plazos, venc, prorroga_dias = build_notificacion_expediente_bandeja_metrics(acts)
    rein = build_reinspeccion_comprobacion_por_actuacion_id(acts)
    seg = build_seguimiento_notificacion_por_actuacion_id(acts)
    counts = build_counts_by_eo_from_actuaciones(acts)
    return actuacion_to_pendiente_expediente_row(
        act,
        plazos_por_notificacion=plazos,
        fecha_vencimiento_por_notificacion=venc,
        prorroga_dias_por_notificacion=prorroga_dias,
        counts_by_eo=counts,
        reinspeccion_comprobacion_por_actuacion_id=rein,
        seguimiento_notificacion_por_actuacion_id=seg,
        expediente_list_channel="notificacion",
    )


def _mk_notificacion_origen(
    *,
    fecha: date = date(2026, 3, 1),
    domicilio_id: int | None = None,
) -> tuple[Actuaciones, Notificacion, User]:
    u = _mk_user()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=fecha.year, mes=fecha.month)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=fecha.year, mes=fecha.month)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=fecha)
    act = Actuaciones(
        fecha=fecha,
        mes=fecha.month,
        anio=fecha.year,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        domicilio_id=domicilio_id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act, noti, u


def _mk_reinspeccion(
    *,
    noti: Notificacion,
    fecha: date = date(2026, 4, 10),
    comprobacion_num: str | None = None,
    vincular_notificacion: bool = True,
    domicilio_id: int | None = None,
) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=fecha.year, mes=fecha.month)
    db.session.add(ot)
    db.session.flush()
    cid = None
    if comprobacion_num is not None:
        comp = Comprobacion(
            numero_acta=comprobacion_num,
            anio=fecha.year,
            mes=fecha.month,
            motivo="rein",
        )
        db.session.add(comp)
        db.session.flush()
        cid = comp.id
    nid = noti.id if vincular_notificacion else None
    act = Actuaciones(
        fecha=fecha,
        mes=fecha.month,
        anio=fecha.year,
        orden_trabajo_id=ot.id,
        notificacion_id=nid,
        comprobacion_id=cid,
        domicilio_id=domicilio_id,
        tipo="REINSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act


def _mk_resultado(
    *,
    noti: Notificacion,
    act_rein: Actuaciones,
    u: User,
    faltas_subsanadas: bool,
) -> NotificacionResultadoReinspeccion:
    row = NotificacionResultadoReinspeccion(
        notificacion_id=noti.id,
        actuacion_id=act_rein.id,
        faltas_subsanadas=faltas_subsanadas,
        fecha_verificacion=act_rein.fecha or date(2026, 4, 10),
        created_by_user_id=u.id,
    )
    db.session.add(row)
    db.session.flush()
    return row


def test_historial_reinspeccion_faltas_subsanadas(app_ctx) -> None:
    try:
        act, noti, u = _mk_notificacion_origen()
        rein = _mk_reinspeccion(noti=noti, comprobacion_num="REIN01")
        _mk_resultado(noti=noti, act_rein=rein, u=u, faltas_subsanadas=True)
        row = _row_notificacion(act)
        seg = row["seguimiento_notificacion"]
        assert seg["estado"] == "FALTAS_SUBSANADAS"
        assert seg["faltas_subsanadas"] is True
        assert seg["actuacion_id"] == rein.id
        assert seg["fecha_reinspeccion"] == "2026-04-10"
        assert seg["acta_comprobacion_num"] == "REIN01"
    finally:
        db.session.rollback()


def test_historial_reinspeccion_faltas_no_subsanadas(app_ctx) -> None:
    try:
        act, noti, u = _mk_notificacion_origen()
        rein = _mk_reinspeccion(noti=noti, comprobacion_num="REIN02")
        _mk_resultado(noti=noti, act_rein=rein, u=u, faltas_subsanadas=False)
        row = _row_notificacion(act)
        seg = row["seguimiento_notificacion"]
        assert seg["estado"] == "FALTAS_NO_SUBSANADAS"
        assert seg["faltas_subsanadas"] is False
        assert seg["actuacion_id"] == rein.id
    finally:
        db.session.rollback()


def test_historial_reinspeccion_sin_resultado_no_infiere(app_ctx) -> None:
    try:
        act, noti, _u = _mk_notificacion_origen()
        rein = _mk_reinspeccion(noti=noti, comprobacion_num="REIN03")
        row = _row_notificacion(act)
        seg = row["seguimiento_notificacion"]
        assert seg["estado"] == "REINSPECCION_REALIZADA_SIN_RESULTADO"
        assert seg["faltas_subsanadas"] is None
        assert seg["actuacion_id"] == rein.id
        assert seg["acta_comprobacion_num"] == "REIN03"
        assert row["comprobacion_posterior_acta_num"] == "REIN03"
    finally:
        db.session.rollback()


def test_historial_sin_reinspeccion_estado_correcto(app_ctx) -> None:
    try:
        act, _noti, _u = _mk_notificacion_origen()
        row = _row_notificacion(act)
        seg = row["seguimiento_notificacion"]
        assert seg["estado"] == "SIN_REINSPECCION"
        assert seg["actuacion_id"] is None
        assert seg["faltas_subsanadas"] is None
        assert seg["fecha_reinspeccion"] is None
        assert row["comprobacion_posterior_acta_num"] is None
    finally:
        db.session.rollback()


def test_historial_dos_notificaciones_mismo_domicilio_no_cruzan(app_ctx) -> None:
    try:
        dom = Domicilio(calle="Seg Cruz", numero="9")
        db.session.add(dom)
        db.session.flush()
        act1, noti1, u1 = _mk_notificacion_origen(domicilio_id=dom.id)
        act2, _noti2, _u2 = _mk_notificacion_origen(domicilio_id=dom.id)
        rein = _mk_reinspeccion(noti=noti1, comprobacion_num="SOLO1", domicilio_id=dom.id)
        _mk_resultado(noti=noti1, act_rein=rein, u=u1, faltas_subsanadas=True)

        seg1 = _row_notificacion(act1)["seguimiento_notificacion"]
        seg2 = _row_notificacion(act2)["seguimiento_notificacion"]
        assert seg1["estado"] == "FALTAS_SUBSANADAS"
        assert seg1["actuacion_id"] == rein.id
        assert seg2["estado"] == "SIN_REINSPECCION"
        assert seg2["actuacion_id"] is None
    finally:
        db.session.rollback()


def test_historial_vinculo_por_iniciador_reinspeccion_notificacion(app_ctx) -> None:
    """Admite circuito IniciadorRuta aunque la visita no copie notificacion_id."""
    try:
        act, noti, u = _mk_notificacion_origen()
        dom = Domicilio(calle="Seg Ini", numero="2")
        db.session.add(dom)
        db.session.flush()
        act.domicilio_id = dom.id
        db.session.flush()
        rein = _mk_reinspeccion(noti=noti, vincular_notificacion=False, comprobacion_num="VIAINI")
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="CUMPLIDO",
            fecha_origen=date(2026, 4, 1),
            anio=2026,
            mes=4,
            domicilio_id=dom.id,
            notificacion_id=noti.id,
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        ruta = RutaTrabajo(
            fecha=date(2026, 4, 10),
            turno="TARDE",
            estado_ruta="CERRADA",
            created_by_user_id=u.id,
            numero=random.randint(2, 32000),
        )
        db.session.add(ruta)
        db.session.flush()
        db.session.add(
            RutaItem(
                ruta_trabajo_id=ruta.id,
                iniciador_ruta_id=ini.id,
                estado_ruta_item="FINALIZADO",
                estado_ejecucion="REALIZADO",
                actuacion_id=rein.id,
                created_by_user_id=u.id,
            )
        )
        db.session.flush()
        _mk_resultado(noti=noti, act_rein=rein, u=u, faltas_subsanadas=False)
        seg = _row_notificacion(act)["seguimiento_notificacion"]
        assert seg["estado"] == "FALTAS_NO_SUBSANADAS"
        assert seg["actuacion_id"] == rein.id
        assert seg["acta_comprobacion_num"] == "VIAINI"
    finally:
        db.session.rollback()


def _mk_actuacion_comprobacion() -> tuple[Actuaciones, Comprobacion, Domicilio, User]:
    u = _mk_user()
    dom = Domicilio(calle="Seg Comp", numero="1")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=7, motivo="seg oficio")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 7, 10),
        mes=7,
        anio=2026,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act, comp, dom, u


def _mk_oficio_pendiente(*, comp: Comprobacion, act_ancla: Actuaciones, dom: Domicilio, u: User) -> Oficio:
    ofi = Oficio(
        comprobacion_id=comp.id,
        numero_oficio=_unique_num(),
        anio=2026,
        fecha_oficio=date(2026, 7, 1),
    )
    db.session.add(ofi)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 7, 1),
        anio=2026,
        mes=7,
        domicilio_id=dom.id,
        comprobacion_id=comp.id,
        oficio_id=ofi.id,
        actuacion_id=act_ancla.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    return ofi


def _mk_oficio_con_cierre(
    *,
    comp: Comprobacion,
    act_ancla: Actuaciones,
    dom: Domicilio,
    u: User,
    resultado: str | None,
    numero_oficio: str | None = None,
) -> Oficio:
    ofi = Oficio(
        comprobacion_id=comp.id,
        numero_oficio=numero_oficio or _unique_num(),
        anio=2026,
        fecha_oficio=date(2026, 7, 1),
    )
    db.session.add(ofi)
    db.session.flush()
    db.session.add(
        Expediente(
            comprobacion_id=comp.id,
            oficio_id=ofi.id,
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 7, 2),
            tipo_expediente="RESPUESTA_OFICIO",
        )
    )
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="CUMPLIDO",
        fecha_origen=date(2026, 7, 1),
        anio=2026,
        mes=7,
        domicilio_id=dom.id,
        comprobacion_id=comp.id,
        oficio_id=ofi.id,
        actuacion_id=act_ancla.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ot_vis = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(ot_vis)
    db.session.flush()
    act_vis = Actuaciones(
        fecha=date(2026, 7, 14),
        mes=7,
        anio=2026,
        orden_trabajo_id=ot_vis.id,
        domicilio_id=dom.id,
        tipo="VERIFICAR E INFORMAR",
        resultado_cumplimiento_oficio=resultado,
    )
    db.session.add(act_vis)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=date(2026, 7, 14),
        turno="TARDE",
        estado_ruta="CERRADA",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    db.session.add(
        RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            orden_trabajo_id=ot_vis.id,
            estado_ruta_item="FINALIZADO",
            estado_ejecucion="REALIZADO",
            actuacion_id=act_vis.id,
            created_by_user_id=u.id,
        )
    )
    db.session.flush()
    return ofi


def test_recorrido_oficio_pendiente_sin_resultado(app_ctx) -> None:
    try:
        act, comp, dom, u = _mk_actuacion_comprobacion()
        ofi = _mk_oficio_pendiente(comp=comp, act_ancla=act, dom=dom, u=u)
        row = comprobacion_recorrido_resumen_row(act)
        resumen = row["oficios_resumen"]
        assert len(resumen) == 1
        item = resumen[0]
        assert item["id"] == ofi.id
        assert item["estado_iniciador"] == "PENDIENTE"
        assert item["resultado"] is None
        assert item["resultado_cumplimiento_oficio"] is None
        assert item["ejecucion_reinspeccion"] is None
        d = comprobacion_recorrido_detalle(act)
        assert d["oficios_resumen"][0]["estado_iniciador"] == "PENDIENTE"
        assert d["oficios_resumen"][0]["resultado"] is None
    finally:
        db.session.rollback()


def test_recorrido_reinspeccion_oficio_cumple(app_ctx) -> None:
    try:
        act, comp, dom, u = _mk_actuacion_comprobacion()
        _mk_oficio_con_cierre(comp=comp, act_ancla=act, dom=dom, u=u, resultado="CUMPLE")
        item = comprobacion_recorrido_resumen_row(act)["oficios_resumen"][0]
        assert item["resultado"] == "CUMPLE"
        assert item["resultado_cumplimiento_oficio"] == "CUMPLE"
        assert item["conclusion"] == "Cumple"
        assert item["ejecucion_reinspeccion"] is not None
    finally:
        db.session.rollback()


def test_recorrido_reinspeccion_oficio_no_cumple(app_ctx) -> None:
    try:
        act, comp, dom, u = _mk_actuacion_comprobacion()
        _mk_oficio_con_cierre(comp=comp, act_ancla=act, dom=dom, u=u, resultado="NO_CUMPLE")
        item = comprobacion_recorrido_resumen_row(act)["oficios_resumen"][0]
        assert item["resultado"] == "NO_CUMPLE"
        assert item["conclusion"] == "No cumple"
    finally:
        db.session.rollback()


def test_recorrido_varios_oficios_resultados_separados(app_ctx) -> None:
    try:
        act, comp, dom, u = _mk_actuacion_comprobacion()
        num1 = _unique_num()
        num2 = _unique_num()
        _mk_oficio_con_cierre(
            comp=comp, act_ancla=act, dom=dom, u=u, resultado="CUMPLE", numero_oficio=num1
        )
        _mk_oficio_con_cierre(
            comp=comp, act_ancla=act, dom=dom, u=u, resultado="NO_CUMPLE", numero_oficio=num2
        )
        items = comprobacion_recorrido_resumen_row(act)["oficios_resumen"]
        assert len(items) == 2
        by_num = {str(i["numero_oficio"]): i for i in items}
        assert by_num[num1]["resultado"] == "CUMPLE"
        assert by_num[num2]["resultado"] == "NO_CUMPLE"
        assert by_num[num1]["conclusion"] != by_num[num2]["conclusion"]
        detalle_items = comprobacion_recorrido_detalle(act)["oficios_resumen"]
        assert len(detalle_items) == 2
    finally:
        db.session.rollback()


def test_recorrido_reinspeccion_sin_resultado_no_inventa_cumple(app_ctx) -> None:
    try:
        act, comp, dom, u = _mk_actuacion_comprobacion()
        _mk_oficio_con_cierre(comp=comp, act_ancla=act, dom=dom, u=u, resultado=None)
        item = comprobacion_recorrido_resumen_row(act)["oficios_resumen"][0]
        assert item["estado_iniciador"] == "CUMPLIDO"
        assert item["resultado"] is None
        assert item["conclusion"] is None
        assert item["ejecucion_reinspeccion"] is not None
    finally:
        db.session.rollback()
