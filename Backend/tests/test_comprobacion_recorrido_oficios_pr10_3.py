"""PR10.3 — Recorrido de comprobación: oficios_resumen con OT y conclusión por oficio."""

from __future__ import annotations

import random
from datetime import date, datetime, timezone

import pytest

from app.database import db
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_detalle,
    comprobacion_recorrido_resumen_row,
)
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
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"rec_of_{_unique_num()}",
        email=f"rec_of_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_actuacion_comprobacion() -> tuple[Actuaciones, Comprobacion, Domicilio, User]:
    u = _mk_user()
    dom = Domicilio(calle="Rec Of", numero="1")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=7, motivo="rec oficios")
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


def _mk_oficio_con_cierre(
    *,
    comp: Comprobacion,
    act_ancla: Actuaciones,
    dom: Domicilio,
    u: User,
    numero_oficio: str,
    numero_exp: str,
    ot_visita: str,
    resultado: str,
    fecha_cierre: date,
) -> Oficio:
    ofi = Oficio(
        comprobacion_id=comp.id,
        numero_oficio=numero_oficio,
        anio=2026,
        fecha_oficio=date(2026, 7, 1),
    )
    db.session.add(ofi)
    db.session.flush()
    db.session.add(
        Expediente(
            comprobacion_id=comp.id,
            oficio_id=ofi.id,
            numero_expediente=numero_exp,
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
    ot_vis = OrdenTrabajo(numero_acta=ot_visita, anio=2026, mes=7)
    db.session.add(ot_vis)
    db.session.flush()
    act_vis = Actuaciones(
        fecha=fecha_cierre,
        mes=fecha_cierre.month,
        anio=fecha_cierre.year,
        orden_trabajo_id=ot_vis.id,
        domicilio_id=dom.id,
        tipo="VERIFICAR E INFORMAR",
        resultado_cumplimiento_oficio=resultado,
    )
    db.session.add(act_vis)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fecha_cierre,
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


def test_recorrido_dos_oficios_conclusion_y_ot_propias(app_ctx) -> None:
    try:
        act, comp, dom, u = _mk_actuacion_comprobacion()
        num_of1 = _unique_num()
        num_of2 = _unique_num()
        num_exp1 = _unique_num()
        num_exp2 = _unique_num()
        ot1 = _unique_num()
        ot2 = _unique_num()
        _mk_oficio_con_cierre(
            comp=comp,
            act_ancla=act,
            dom=dom,
            u=u,
            numero_oficio=num_of1,
            numero_exp=num_exp1,
            ot_visita=ot1,
            resultado="CUMPLE",
            fecha_cierre=date(2026, 7, 14),
        )
        _mk_oficio_con_cierre(
            comp=comp,
            act_ancla=act,
            dom=dom,
            u=u,
            numero_oficio=num_of2,
            numero_exp=num_exp2,
            ot_visita=ot2,
            resultado="NO_CUMPLE",
            fecha_cierre=date(2026, 7, 15),
        )
        db.session.commit()

        row = comprobacion_recorrido_resumen_row(act)
        resumen = row.get("oficios_resumen") or []
        assert len(resumen) == 2
        assert resumen[0]["oficio_texto"] == f"{num_of1}/2026"
        assert resumen[0]["expediente_texto"] == f"{num_exp1}/2026"
        assert resumen[0]["orden_trabajo"] == ot1
        assert resumen[0]["resultado"] == "CUMPLE"
        assert resumen[0]["conclusion"] == "Cumple"
        assert resumen[0]["fecha_conclusion"] == "2026-07-14"

        assert resumen[1]["oficio_texto"] == f"{num_of2}/2026"
        assert resumen[1]["expediente_texto"] == f"{num_exp2}/2026"
        assert resumen[1]["orden_trabajo"] == ot2
        assert resumen[1]["resultado"] == "NO_CUMPLE"
        assert resumen[1]["conclusion"] == "No cumple"
        assert resumen[1]["fecha_conclusion"] == "2026-07-15"

        assert resumen[0]["resultado"] != resumen[1]["resultado"]

        det = comprobacion_recorrido_detalle(act)
        det_resumen = det.get("oficios_resumen") or []
        assert len(det_resumen) == 2
        assert det_resumen[1]["orden_trabajo"] == ot2

        payload = oficios_comprobacion_payload(int(comp.id), actuacion_ancla_id=int(act.id))
        assert len(payload) == 2
        assert payload[0]["ejecucion_reinspeccion"] is not None
        assert payload[1]["resultado"] == "NO_CUMPLE"
    finally:
        db.session.rollback()


def test_recorrido_excluye_oficio_soft_deleted(app_ctx) -> None:
    try:
        act, comp, dom, u = _mk_actuacion_comprobacion()
        num_activo = _unique_num()
        num_borrado = _unique_num()
        ofi_activo = _mk_oficio_con_cierre(
            comp=comp,
            act_ancla=act,
            dom=dom,
            u=u,
            numero_oficio=num_activo,
            numero_exp=_unique_num(),
            ot_visita=_unique_num(),
            resultado="CUMPLE",
            fecha_cierre=date(2026, 7, 16),
        )
        ofi_borrado = Oficio(
            comprobacion_id=comp.id,
            numero_oficio=num_borrado,
            anio=2026,
            fecha_oficio=date(2026, 7, 1),
            deleted_at=datetime.now(timezone.utc),
        )
        db.session.add(ofi_borrado)
        db.session.flush()
        db.session.add(
            Expediente(
                comprobacion_id=comp.id,
                oficio_id=ofi_borrado.id,
                numero_expediente=_unique_num(),
                anio="2026",
                fecha_expediente=date(2026, 7, 2),
                tipo_expediente="RESPUESTA_OFICIO",
            )
        )
        db.session.commit()

        row = comprobacion_recorrido_resumen_row(act)
        resumen = row.get("oficios_resumen") or []
        assert len(resumen) == 1
        assert resumen[0]["oficio_texto"] == f"{num_activo}/2026"
        assert ofi_activo.id == resumen[0]["id"]
    finally:
        db.session.rollback()
