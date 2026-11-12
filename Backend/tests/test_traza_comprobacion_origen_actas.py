"""V1.1-TRAZA-COMPROBACION.1 — proyección read-only ``origen_actas`` desde la ancla."""

from __future__ import annotations

import random
from datetime import date

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_detalle,
    comprobacion_recorrido_resumen_row,
)
from app.domains.actuaciones.presenters.origen_actas_presenter import (
    actuacion_ancla_origen,
    origen_actas_desde_ancla,
    origen_actas_desde_iniciador,
)
from app.domains.actuaciones.services.comprobacion_documental_service import (
    get_comprobacion_documental_for_actuacion,
)
from app.models import (
    Actuaciones,
    Clausura,
    Comprobacion,
    Decomiso,
    Domicilio,
    Expediente,
    IniciadorRuta,
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
        username=f"traza_{_unique_num()}",
        email=f"traza_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_ancla(*, con_decomiso: bool = False, con_clausura: bool = False, kilos: float = 12.5) -> tuple[
    Actuaciones, Comprobacion, Domicilio, User, Decomiso | None, Clausura | None
]:
    u = _mk_user()
    dom = Domicilio(calle="Traza Orig", numero="1")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=8, motivo="traza origen")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 8, 10),
        mes=8,
        anio=2026,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    dec = None
    cla = None
    if con_decomiso:
        dec = Decomiso(
            numero_acta=_unique_num(),
            anio=2026,
            mes=8,
            actuacion_id=act.id,
            cantidad=kilos,
        )
        db.session.add(dec)
    if con_clausura:
        cla = Clausura(
            numero_acta=_unique_num(),
            anio=2026,
            mes=8,
            actuacion_id=act.id,
        )
        db.session.add(cla)
    db.session.flush()
    return act, comp, dom, u, dec, cla


def _mk_oficio_visita(
    *,
    comp: Comprobacion,
    act_ancla: Actuaciones,
    dom: Domicilio,
    u: User,
    tipo_iniciador: str,
    tipo_visita: str,
    realizo_nueva_inspeccion: bool | None = None,
    decomiso_visita_kilos: float | None = None,
) -> tuple[Oficio, Actuaciones, IniciadorRuta]:
    ofi = Oficio(
        comprobacion_id=comp.id,
        numero_oficio=_unique_num(),
        anio=2026,
        fecha_oficio=date(2026, 8, 20),
    )
    db.session.add(ofi)
    db.session.flush()
    db.session.add(
        Expediente(
            comprobacion_id=comp.id,
            oficio_id=ofi.id,
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 8, 21),
            tipo_expediente="RESPUESTA_OFICIO",
        )
    )
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador=tipo_iniciador,
        estado_iniciador="CUMPLIDO",
        fecha_origen=date(2026, 8, 20),
        anio=2026,
        mes=8,
        domicilio_id=dom.id,
        comprobacion_id=comp.id,
        oficio_id=ofi.id,
        actuacion_id=act_ancla.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ot_vis = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=9)
    db.session.add(ot_vis)
    db.session.flush()
    act_vis = Actuaciones(
        fecha=date(2026, 9, 5),
        mes=9,
        anio=2026,
        orden_trabajo_id=ot_vis.id,
        domicilio_id=dom.id,
        tipo=tipo_visita,
        realizo_nueva_inspeccion=realizo_nueva_inspeccion,
    )
    db.session.add(act_vis)
    db.session.flush()
    if decomiso_visita_kilos is not None:
        db.session.add(
            Decomiso(
                numero_acta=_unique_num(),
                anio=2026,
                mes=9,
                actuacion_id=act_vis.id,
                cantidad=decomiso_visita_kilos,
            )
        )
        db.session.flush()
    ruta = RutaTrabajo(
        fecha=date(2026, 9, 5),
        turno="MANIANA",
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
    return ofi, act_vis, ini


def _assert_keys(payload: dict) -> None:
    assert set(payload.keys()) == {
        "actuacion_origen_id",
        "acta_decomiso_num",
        "decomiso_kilos_total",
        "acta_clausura_num",
    }


def test_ancla_con_decomiso_proyecta_numero_y_kilos(app_ctx) -> None:
    try:
        act, _comp, _dom, _u, dec, _cla = _mk_ancla(con_decomiso=True, kilos=7.25)
        payload = origen_actas_desde_ancla(act)
        _assert_keys(payload)
        assert payload["actuacion_origen_id"] == act.id
        assert payload["acta_decomiso_num"] == dec.numero_acta
        assert payload["decomiso_kilos_total"] == 7.25
        assert payload["acta_clausura_num"] is None
        row = comprobacion_recorrido_resumen_row(act)
        assert row["origen_actas"]["acta_decomiso_num"] == dec.numero_acta
        assert row["origen_actas"]["decomiso_kilos_total"] == 7.25
    finally:
        db.session.rollback()


def test_ancla_con_clausura_proyecta_numero(app_ctx) -> None:
    try:
        act, _comp, _dom, _u, _dec, cla = _mk_ancla(con_clausura=True)
        payload = origen_actas_desde_ancla(act)
        assert payload["actuacion_origen_id"] == act.id
        assert payload["acta_clausura_num"] == cla.numero_acta
        assert payload["acta_decomiso_num"] is None
        assert payload["decomiso_kilos_total"] is None
    finally:
        db.session.rollback()


def test_ancla_con_ambos_proyecta_ambos(app_ctx) -> None:
    try:
        act, _comp, _dom, _u, dec, cla = _mk_ancla(con_decomiso=True, con_clausura=True, kilos=3)
        payload = origen_actas_desde_ancla(act)
        assert payload["acta_decomiso_num"] == dec.numero_acta
        assert payload["decomiso_kilos_total"] == 3.0
        assert payload["acta_clausura_num"] == cla.numero_acta
        detalle = comprobacion_recorrido_detalle(act)
        assert detalle["origen_actas"]["acta_decomiso_num"] == dec.numero_acta
        assert detalle["origen_actas"]["acta_clausura_num"] == cla.numero_acta
    finally:
        db.session.rollback()


def test_mascara_ratificacion_decomiso_oculta_clausura(app_ctx) -> None:
    try:
        act, _comp, _dom, _u, dec, cla = _mk_ancla(con_decomiso=True, con_clausura=True, kilos=4)
        masked = origen_actas_desde_ancla(act, tipo_final="RATIFICACION DE DECOMISO")
        assert masked["acta_decomiso_num"] == dec.numero_acta
        assert masked["decomiso_kilos_total"] == 4.0
        assert masked["acta_clausura_num"] is None
        assert cla.numero_acta is not None
    finally:
        db.session.rollback()


def test_mascara_ratificacion_clausura_oculta_decomiso(app_ctx) -> None:
    try:
        act, _comp, _dom, _u, dec, cla = _mk_ancla(con_decomiso=True, con_clausura=True, kilos=4)
        masked = origen_actas_desde_ancla(act, tipo_final="RATIFICACION DE CLAUSURA")
        assert masked["acta_clausura_num"] == cla.numero_acta
        assert masked["acta_decomiso_num"] is None
        assert masked["decomiso_kilos_total"] is None
        assert dec.numero_acta is not None
    finally:
        db.session.rollback()


def test_verificar_informar_sin_nueva_inspeccion_muestra_antecedentes(app_ctx) -> None:
    try:
        act, comp, dom, u, dec, cla = _mk_ancla(con_decomiso=True, con_clausura=True, kilos=9.5)
        ofi, act_vis, ini = _mk_oficio_visita(
            comp=comp,
            act_ancla=act,
            dom=dom,
            u=u,
            tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
            tipo_visita="VERIFICAR E INFORMAR",
            realizo_nueva_inspeccion=False,
        )
        payload = origen_actas_desde_iniciador(ini, tipo_actuacion_visita=act_vis.tipo)
        assert payload["actuacion_origen_id"] == act.id
        assert payload["acta_decomiso_num"] == dec.numero_acta
        assert payload["decomiso_kilos_total"] == 9.5
        assert payload["acta_clausura_num"] == cla.numero_acta
        row = comprobacion_recorrido_resumen_row(act)
        item = next(i for i in row["oficios_resumen"] if i["id"] == ofi.id)
        assert item["origen_actas"]["actuacion_origen_id"] == act.id
        assert item["origen_actas"]["decomiso_kilos_total"] == 9.5
        ejec = item.get("ejecucion_reinspeccion") or {}
        assert ejec.get("actuacion_id") == act_vis.id
        assert "decomiso_kilos_total" not in ejec
    finally:
        db.session.rollback()


def test_verificar_informar_con_decomiso_propio_no_pisa_origen(app_ctx) -> None:
    try:
        act, comp, dom, u, dec, _cla = _mk_ancla(con_decomiso=True, kilos=11)
        ofi, act_vis, ini = _mk_oficio_visita(
            comp=comp,
            act_ancla=act,
            dom=dom,
            u=u,
            tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
            tipo_visita="VERIFICAR E INFORMAR",
            realizo_nueva_inspeccion=True,
            decomiso_visita_kilos=99.9,
        )
        payload = origen_actas_desde_iniciador(ini, tipo_actuacion_visita=act_vis.tipo)
        assert payload["actuacion_origen_id"] == act.id
        assert payload["acta_decomiso_num"] == dec.numero_acta
        assert payload["decomiso_kilos_total"] == 11.0
        assert payload["decomiso_kilos_total"] != 99.9
        detalle = comprobacion_recorrido_detalle(act)
        assert detalle["origen_actas"]["decomiso_kilos_total"] == 11.0
        item = next(i for i in detalle["oficios_resumen"] if i["id"] == ofi.id)
        assert item["origen_actas"]["decomiso_kilos_total"] == 11.0
        assert item["ejecucion_reinspeccion"]["actuacion_id"] == act_vis.id
        assert actuacion_ancla_origen(act_vis).id == act.id
        doc = get_comprobacion_documental_for_actuacion(act.id)
        assert doc["origen_actas"]["decomiso_kilos_total"] == 11.0
        assert doc["origen_actas"]["actuacion_origen_id"] == act.id
    finally:
        db.session.rollback()


def test_ratificacion_sin_decomiso_ni_clausura_campos_vacios(app_ctx) -> None:
    try:
        act, comp, dom, u, _dec, _cla = _mk_ancla()
        ofi, act_vis, ini = _mk_oficio_visita(
            comp=comp,
            act_ancla=act,
            dom=dom,
            u=u,
            tipo_iniciador="RATIFICACION_DECOMISO_OFICIO",
            tipo_visita="RATIFICACION DE DECOMISO",
        )
        payload = origen_actas_desde_iniciador(ini, tipo_actuacion_visita=act_vis.tipo)
        assert payload["actuacion_origen_id"] == act.id
        assert payload["acta_decomiso_num"] is None
        assert payload["decomiso_kilos_total"] is None
        assert payload["acta_clausura_num"] is None
        row = comprobacion_recorrido_resumen_row(act)
        item = next(i for i in row["oficios_resumen"] if i["id"] == ofi.id)
        assert item["origen_actas"]["acta_decomiso_num"] is None
        assert item["origen_actas"]["decomiso_kilos_total"] is None
    finally:
        db.session.rollback()


def test_dos_oficios_leen_la_misma_ancla(app_ctx) -> None:
    try:
        act, comp, dom, u, dec, cla = _mk_ancla(con_decomiso=True, con_clausura=True, kilos=5)
        ofi_dec, _vis_d, _ini_d = _mk_oficio_visita(
            comp=comp,
            act_ancla=act,
            dom=dom,
            u=u,
            tipo_iniciador="RATIFICACION_DECOMISO_OFICIO",
            tipo_visita="RATIFICACION DE DECOMISO",
        )
        ofi_cla, _vis_c, _ini_c = _mk_oficio_visita(
            comp=comp,
            act_ancla=act,
            dom=dom,
            u=u,
            tipo_iniciador="RATIFICACION_CLAUSURA_OFICIO",
            tipo_visita="RATIFICACION DE CLAUSURA",
        )
        row = comprobacion_recorrido_resumen_row(act)
        assert row["origen_actas"]["actuacion_origen_id"] == act.id
        assert row["origen_actas"]["acta_decomiso_num"] == dec.numero_acta
        assert row["origen_actas"]["acta_clausura_num"] == cla.numero_acta
        by_id = {i["id"]: i for i in row["oficios_resumen"]}
        orig_dec = by_id[ofi_dec.id]["origen_actas"]
        orig_cla = by_id[ofi_cla.id]["origen_actas"]
        assert orig_dec["actuacion_origen_id"] == act.id
        assert orig_cla["actuacion_origen_id"] == act.id
        assert orig_dec["acta_decomiso_num"] == dec.numero_acta
        assert orig_dec["decomiso_kilos_total"] == 5.0
        assert orig_dec["acta_clausura_num"] is None
        assert orig_cla["acta_clausura_num"] == cla.numero_acta
        assert orig_cla["acta_decomiso_num"] is None
        assert orig_cla["decomiso_kilos_total"] is None
    finally:
        db.session.rollback()


def test_reinspeccion_generica_pendiente_datos_disponibles_sin_afirmar(app_ctx) -> None:
    try:
        act, comp, dom, u, dec, cla = _mk_ancla(con_decomiso=True, con_clausura=True, kilos=2)
        ofi = Oficio(
            comprobacion_id=comp.id,
            numero_oficio=_unique_num(),
            anio=2026,
            fecha_oficio=date(2026, 8, 22),
        )
        db.session.add(ofi)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 8, 22),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            comprobacion_id=comp.id,
            oficio_id=ofi.id,
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        payload = origen_actas_desde_iniciador(ini)
        assert payload["actuacion_origen_id"] == act.id
        assert payload["acta_decomiso_num"] == dec.numero_acta
        assert payload["acta_clausura_num"] == cla.numero_acta
        row = comprobacion_recorrido_resumen_row(act)
        item = next(i for i in row["oficios_resumen"] if i["id"] == ofi.id)
        assert item["origen_actas"]["acta_decomiso_num"] == dec.numero_acta
        assert item["tipo_iniciador"] == "REINSPECCION_OFICIO"
    finally:
        db.session.rollback()


def test_grid_visita_origen_actas_no_usa_decomiso_de_visita(app_ctx) -> None:
    try:
        act, comp, dom, u, dec, _cla = _mk_ancla(con_decomiso=True, kilos=11)
        _ofi, act_vis, _ini = _mk_oficio_visita(
            comp=comp,
            act_ancla=act,
            dom=dom,
            u=u,
            tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
            tipo_visita="VERIFICAR E INFORMAR",
            realizo_nueva_inspeccion=True,
            decomiso_visita_kilos=99.9,
        )
        grid = actuacion_to_grid_row(act_vis)
        orig = grid.get("origen_actas")
        assert orig is not None
        assert orig["actuacion_origen_id"] == act.id
        assert orig["acta_decomiso_num"] == dec.numero_acta
        assert orig["decomiso_kilos_total"] == 11.0
        grid_ancla = actuacion_to_grid_row(act)
        assert grid_ancla.get("origen_actas") is None
    finally:
        db.session.rollback()
