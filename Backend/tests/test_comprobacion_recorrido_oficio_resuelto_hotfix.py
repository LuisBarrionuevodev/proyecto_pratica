"""HOTFIX — Recorrido: oficios resueltos tras promoción de tipo iniciador (PR10.2)."""

from __future__ import annotations

from datetime import date

import pytest

from tests.helpers.fixture_isolation import unique_ot_numero, uniq_ruta_numero

from app.database import db
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_resumen_row,
    estado_recorrido_label,
)
from app.domains.actuaciones.services.oficio_editable_service import evaluar_editable_oficio
from app.domains.actuaciones.services.oficio_list_service import oficios_comprobacion_payload
from app.models import (
    Actuaciones,
    Comprobacion,
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
    return unique_ot_numero()


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"rec_hot_{_unique_num()}",
        email=f"rec_hot_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_circuito() -> tuple[Actuaciones, Comprobacion, Domicilio, User]:
    u = _mk_user()
    dom = Domicilio(calle="Hot Rec", numero="1")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=8, motivo="hot recorrido")
    db.session.add(comp)
    db.session.flush()
    db.session.add(
        Expediente(
            comprobacion_id=comp.id,
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 8, 1),
            tipo_expediente="ENVIO_ACTA",
        )
    )
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
    return act, comp, dom, u


def _mk_oficio_con_visita_cerrada(
    *,
    comp: Comprobacion,
    act_ancla: Actuaciones,
    dom: Domicilio,
    u: User,
    tipo_iniciador: str,
    tipo_visita: str,
    resultado: str,
    estado_ejecucion: str = "REALIZADO",
) -> Oficio:
    ofi = Oficio(
        comprobacion_id=comp.id,
        numero_oficio=_unique_num(),
        anio=2026,
        fecha_oficio=date(2026, 8, 2),
    )
    db.session.add(ofi)
    db.session.flush()
    db.session.add(
        Expediente(
            comprobacion_id=comp.id,
            oficio_id=ofi.id,
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 8, 3),
            tipo_expediente="RESPUESTA_OFICIO",
        )
    )
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador=tipo_iniciador,
        estado_iniciador="CUMPLIDO",
        fecha_origen=date(2026, 8, 2),
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
    ot_vis = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=8)
    db.session.add(ot_vis)
    db.session.flush()
    act_vis = Actuaciones(
        fecha=date(2026, 8, 15),
        mes=8,
        anio=2026,
        orden_trabajo_id=ot_vis.id,
        domicilio_id=dom.id,
        tipo=tipo_visita,
        resultado_cumplimiento_oficio=resultado,
    )
    db.session.add(act_vis)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=date(2026, 8, 15),
        turno="TARDE",
        estado_ruta="CERRADA",
        created_by_user_id=u.id,
        numero=uniq_ruta_numero(),
    )
    db.session.add(ruta)
    db.session.flush()
    db.session.add(
        RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            orden_trabajo_id=ot_vis.id,
            estado_ruta_item="FINALIZADO",
            estado_ejecucion=estado_ejecucion,
            actuacion_id=act_vis.id,
            motivo_no_realizado="LOCAL_CERRADO" if estado_ejecucion == "NO_REALIZADO" else None,
            created_by_user_id=u.id,
        )
    )
    db.session.flush()
    return ofi


def test_oficio_sin_ruta_muestra_sin_programada_y_editable(app_ctx) -> None:
    act, comp, _dom, _u = _mk_circuito()
    ofi = Oficio(
        comprobacion_id=comp.id,
        numero_oficio=_unique_num(),
        anio=2026,
        fecha_oficio=date(2026, 8, 2),
    )
    db.session.add(ofi)
    db.session.flush()
    db.session.add(
        Expediente(
            comprobacion_id=comp.id,
            oficio_id=ofi.id,
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 8, 3),
            tipo_expediente="RESPUESTA_OFICIO",
        )
    )
    db.session.commit()

    assert estado_recorrido_label(act) == "Oficio cargado — sin reinspección programada"
    pol = evaluar_editable_oficio(ofi.id)
    assert pol["editable"] is True
    assert pol["estado_operativo"] == "sin_iniciador"


def test_oficio_promovido_verificar_informar_no_sin_programada(app_ctx) -> None:
    act, comp, dom, u = _mk_circuito()
    ofi = _mk_oficio_con_visita_cerrada(
        comp=comp,
        act_ancla=act,
        dom=dom,
        u=u,
        tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
        tipo_visita="VERIFICAR E INFORMAR",
        resultado="CUMPLE",
    )
    db.session.commit()

    assert estado_recorrido_label(act) == "Verificar e informar — visita realizada"
    row = comprobacion_recorrido_resumen_row(act)
    resumen = row.get("oficios_resumen") or []
    assert len(resumen) == 1
    assert resumen[0].get("conclusion") == "Cumple"
    assert resumen[0].get("orden_trabajo_numero")

    pol = evaluar_editable_oficio(ofi.id)
    assert pol["editable"] is False
    assert pol["estado_operativo"] == "cumplido"

    payload = oficios_comprobacion_payload(comp.id)
    item = next(i for i in payload if i["id"] == ofi.id)
    assert item["editable"] is False


def test_oficio_en_ruta_publicada_no_editable(app_ctx) -> None:
    act, comp, dom, u = _mk_circuito()
    ofi = Oficio(
        comprobacion_id=comp.id,
        numero_oficio=_unique_num(),
        anio=2026,
        fecha_oficio=date(2026, 8, 2),
    )
    db.session.add(ofi)
    db.session.flush()
    db.session.add(
        Expediente(
            comprobacion_id=comp.id,
            oficio_id=ofi.id,
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 8, 3),
            tipo_expediente="RESPUESTA_OFICIO",
        )
    )
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 8, 2),
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
    ruta = RutaTrabajo(
        fecha=date(2026, 8, 12),
        turno="TARDE",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=uniq_ruta_numero(),
    )
    db.session.add(ruta)
    db.session.flush()
    db.session.add(
        RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            estado_ruta_item="EN_PROCESO",
            estado_ejecucion=None,
            created_by_user_id=u.id,
        )
    )
    db.session.commit()

    assert estado_recorrido_label(act) == "Inspección programada — en curso"
    pol = evaluar_editable_oficio(ofi.id)
    assert pol["editable"] is False
    assert pol["estado_operativo"] == "en_ruta"


def test_oficio_visita_no_realizada(app_ctx) -> None:
    act, comp, dom, u = _mk_circuito()
    ofi = _mk_oficio_con_visita_cerrada(
        comp=comp,
        act_ancla=act,
        dom=dom,
        u=u,
        tipo_iniciador="REINSPECCION_OFICIO",
        tipo_visita="REINSPECCION",
        resultado="NO_CUMPLE",
        estado_ejecucion="NO_REALIZADO",
    )
    db.session.commit()

    assert estado_recorrido_label(act) == "Visita no realizada"
    pol = evaluar_editable_oficio(ofi.id)
    assert pol["editable"] is False


def test_ratificacion_clausura_resuelto_no_editable(app_ctx) -> None:
    act, comp, dom, u = _mk_circuito()
    ofi = _mk_oficio_con_visita_cerrada(
        comp=comp,
        act_ancla=act,
        dom=dom,
        u=u,
        tipo_iniciador="RATIFICACION_CLAUSURA_OFICIO",
        tipo_visita="RATIFICACION DE CLAUSURA",
        resultado="CUMPLE",
    )
    db.session.commit()

    assert estado_recorrido_label(act) == "Ratificación de clausura — visita realizada"
    pol = evaluar_editable_oficio(ofi.id)
    assert pol["editable"] is False


def test_dos_oficios_visita_resumen_distinto(app_ctx) -> None:
    act, comp, dom, u = _mk_circuito()
    ofi_a = _mk_oficio_con_visita_cerrada(
        comp=comp,
        act_ancla=act,
        dom=dom,
        u=u,
        tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
        tipo_visita="VERIFICAR E INFORMAR",
        resultado="CUMPLE",
    )
    ofi_b = _mk_oficio_con_visita_cerrada(
        comp=comp,
        act_ancla=act,
        dom=dom,
        u=u,
        tipo_iniciador="RATIFICACION_CLAUSURA_OFICIO",
        tipo_visita="RATIFICACION DE CLAUSURA",
        resultado="CUMPLE",
    )
    db.session.commit()

    row = comprobacion_recorrido_resumen_row(act)
    resumen = {int(i["id"]): i for i in (row.get("oficios_resumen") or [])}
    assert "Verificar e informar" in (resumen[ofi_a.id].get("visita_resumen_texto") or "")
    assert "Realizada" in (resumen[ofi_a.id].get("visita_resumen_texto") or "")
    assert "Ratificación de clausura" in (resumen[ofi_b.id].get("visita_resumen_texto") or "")


def test_oficio_no_realizado_y_otro_realizado_visibles(app_ctx) -> None:
    act, comp, dom, u = _mk_circuito()
    _mk_oficio_con_visita_cerrada(
        comp=comp,
        act_ancla=act,
        dom=dom,
        u=u,
        tipo_iniciador="REINSPECCION_OFICIO",
        tipo_visita="REINSPECCION",
        resultado="NO_CUMPLE",
        estado_ejecucion="NO_REALIZADO",
    )
    _mk_oficio_con_visita_cerrada(
        comp=comp,
        act_ancla=act,
        dom=dom,
        u=u,
        tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
        tipo_visita="VERIFICAR E INFORMAR",
        resultado="CUMPLE",
    )
    db.session.commit()

    row = comprobacion_recorrido_resumen_row(act)
    textos = [i.get("visita_resumen_texto") or "" for i in (row.get("oficios_resumen") or [])]
    assert any("No realizada" in t and "Local cerrado" in t for t in textos)
    assert any("Verificar e informar" in t and "Realizada" in t for t in textos)


def test_dos_oficios_uno_resuelto_otro_pendiente(app_ctx) -> None:
    act, comp, dom, u = _mk_circuito()
    ofi_a = _mk_oficio_con_visita_cerrada(
        comp=comp,
        act_ancla=act,
        dom=dom,
        u=u,
        tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
        tipo_visita="VERIFICAR E INFORMAR",
        resultado="CUMPLE",
    )
    ofi_b = Oficio(
        comprobacion_id=comp.id,
        numero_oficio=_unique_num(),
        anio=2026,
        fecha_oficio=date(2026, 8, 4),
    )
    db.session.add(ofi_b)
    db.session.flush()
    db.session.add(
        Expediente(
            comprobacion_id=comp.id,
            oficio_id=ofi_b.id,
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 8, 5),
            tipo_expediente="RESPUESTA_OFICIO",
        )
    )
    db.session.commit()

    row = comprobacion_recorrido_resumen_row(act)
    resumen = {int(i["id"]): i for i in (row.get("oficios_resumen") or [])}
    assert resumen[ofi_a.id]["conclusion"] == "Cumple"
    assert resumen[ofi_b.id]["estado_iniciador"] is None

    pol_a = evaluar_editable_oficio(ofi_a.id)
    pol_b = evaluar_editable_oficio(ofi_b.id)
    assert pol_a["editable"] is False
    assert pol_b["editable"] is True

    assert estado_recorrido_label(act) != "Oficio cargado — sin reinspección programada"
