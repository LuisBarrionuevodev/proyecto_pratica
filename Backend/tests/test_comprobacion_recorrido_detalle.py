"""Presenter ``comprobacion_recorrido_detalle``: campos extendidos para UI de recorrido."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_detalle,
    comprobacion_recorrido_resumen_row,
    estado_recorrido_label,
)
from app.models import Actuaciones, Comprobacion, Contribuyente, Domicilio, Expediente, IniciadorRuta, JuzgadoCatalogo, Oficio, OrdenTrabajo, User


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_actuacion_con_comprobacion() -> tuple[Actuaciones, Comprobacion]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="det recorrido test")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 15),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
    )
    db.session.add(act)
    db.session.flush()
    return act, comp


def test_resultado_final_tipo_visita_none_si_actuacion_solo_reinspeccion_generica(app_ctx) -> None:
    """``tipo_visita`` no debe repetir REINSPECCION genérico como actuación resultante."""
    try:
        act, _comp = _mk_actuacion_con_comprobacion()
        act.tipo = "REINSPECCION"
        db.session.flush()
        d = comprobacion_recorrido_detalle(act)
        assert d["resultado_final"]["tipo_visita"] is None
        assert d["resultado_final"]["tipo_actuacion"] == "REINSPECCION"
    finally:
        db.session.rollback()


def test_comprobacion_recorrido_detalle_incluye_tipo_actuacion_y_origen_iniciador(app_ctx) -> None:
    try:
        act, _comp = _mk_actuacion_con_comprobacion()
        db.session.flush()
        d = comprobacion_recorrido_detalle(act)
        assert "tipo_actuacion" in d["resultado_final"]
        assert "tipo_visita" in d["resultado_final"]
        assert "iniciador" in d["origen"]
        assert d["origen"]["iniciador"] is None or isinstance(d["origen"]["iniciador"], dict)
    finally:
        db.session.rollback()


def test_comprobacion_recorrido_detalle_origen_iniciador_excluye_reinspeccion_oficio(app_ctx) -> None:
    """``origen.iniciador`` debe ser el origen de la actuación (p. ej. DENUNCIA), no REINSPECCION_OFICIO."""
    try:
        u = User(
            username=f"u_rec_{random.randint(0, 999999)}",
            email=f"rec_{random.randint(0, 999999)}@t.local",
            password_hash="x",
            role="usuario",
            is_active=True,
        )
        db.session.add(u)
        dom = Domicilio(calle=f"CalleRec{random.randint(0, 99999)}", numero="1")
        db.session.add(dom)
        db.session.flush()

        act, _comp = _mk_actuacion_con_comprobacion()
        actuacion_id = act.id

        ini_den = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="CUMPLIDO",
            fecha_origen=date(2026, 3, 1),
            anio=2026,
            mes=3,
            domicilio_id=dom.id,
            actuacion_id=actuacion_id,
            created_by_user_id=u.id,
        )
        ini_rein = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 4, 1),
            anio=2026,
            mes=4,
            domicilio_id=dom.id,
            actuacion_id=actuacion_id,
            created_by_user_id=u.id,
        )
        db.session.add_all([ini_den, ini_rein])
        db.session.flush()

        d = comprobacion_recorrido_detalle(act)
        assert d["origen"]["iniciador"] is not None
        assert d["origen"]["iniciador"]["tipo_iniciador"] == "DENUNCIA"
        rein = d["reinspeccion_por_oficio"]
        assert rein is not None
        assert rein["iniciador_id"] == ini_rein.id
        assert rein["tipo_iniciador"] == "REINSPECCION_OFICIO"
        assert rein["documento_pendiente"] == "Reinspección por oficio"
        assert rein.get("ejecucion_reinspeccion") is None
    finally:
        db.session.rollback()


def test_comprobacion_recorrido_detalle_referencia_actuacion_sin_depender_listado(app_ctx) -> None:
    """``referencia_actuacion`` expone titular/domicilio/tipo con la misma fuente que el grid."""
    try:
        doc = f"{random.randint(20000000, 29999999)}"
        c = Contribuyente(apellido="Pérez", nombre="Ana", documento=doc)
        db.session.add(c)
        db.session.flush()
        dom = Domicilio(calle="San Martín", numero="100", contribuyente_id=c.id)
        db.session.add(dom)
        db.session.flush()

        act, _comp = _mk_actuacion_con_comprobacion()
        act.domicilio_id = dom.id
        act.tipo = "INSPECCION"
        db.session.flush()

        d = comprobacion_recorrido_detalle(act)
        ref = d["referencia_actuacion"]
        assert ref["calle"] == "San Martín"
        assert ref["contrib_apellido"] == "Pérez"
        assert ref["contrib_nombre"] == "Ana"
        assert ref["tipo_actuacion"] == "INSPECCION"
    finally:
        db.session.rollback()


def test_referencia_actuacion_incluye_comprobacion_motivo(app_ctx) -> None:
    """``referencia_actuacion`` expone el motivo de la comprobación (misma fuente que la grilla)."""
    try:
        act, comp = _mk_actuacion_con_comprobacion()
        comp.motivo = "Control documental UI"
        db.session.flush()
        d = comprobacion_recorrido_detalle(act)
        assert d["referencia_actuacion"]["comprobacion_motivo"] == "Control documental UI"
    finally:
        db.session.rollback()


def test_estado_recorrido_sin_expediente_envio_es_esperando_expediente(app_ctx) -> None:
    """Sin expediente de envío debe mostrarse «Esperando expediente», no «Esperando oficio»."""
    try:
        act, _comp = _mk_actuacion_con_comprobacion()
        db.session.flush()
        assert estado_recorrido_label(act) == "Esperando expediente"
    finally:
        db.session.rollback()


def test_estado_recorrido_con_expediente_sin_oficio_es_esperando_oficio(app_ctx) -> None:
    try:
        act, comp = _mk_actuacion_con_comprobacion()
        ex = Expediente(
            numero_expediente=_unique_num()[:6],
            anio="2026",
            fecha_expediente=date(2026, 3, 20),
            tipo_expediente="ENVIO_ACTA",
            comprobacion_id=comp.id,
            oficio_id=None,
        )
        db.session.add(ex)
        db.session.flush()
        assert estado_recorrido_label(act) == "Esperando oficio"
    finally:
        db.session.rollback()


def test_comprobacion_recorrido_detalle_oficio_incluye_causa_y_juzgado(app_ctx) -> None:
    try:
        act, comp = _mk_actuacion_con_comprobacion()
        jz = JuzgadoCatalogo(codigo=f"JZ{random.randint(1000, 9999)}", nombre="Juzgado Test Recorrido")
        db.session.add(jz)
        db.session.flush()
        ofi = Oficio(
            numero_oficio="OF-001",
            anio=2026,
            fecha_oficio=date(2026, 4, 1),
            causa="Causa test recorrido",
            comprobacion_id=comp.id,
            juzgado_id=jz.id,
        )
        db.session.add(ofi)
        db.session.flush()
        d = comprobacion_recorrido_detalle(act)
        assert d["oficio"] is not None
        assert d["oficio"]["causa"] == "Causa test recorrido"
        assert d["oficio"]["juzgado_id"] == jz.id
        assert d["oficio"]["juzgado_nombre"] == "Juzgado Test Recorrido"
    finally:
        db.session.rollback()


def test_comprobacion_recorrido_resumen_row_estado_y_sin_expediente_respuesta(app_ctx) -> None:
    """Listado recorrido: ``estado_recorrido`` y campos de expediente de respuesta solo si existen en BD."""
    try:
        act, _comp = _mk_actuacion_con_comprobacion()
        row = comprobacion_recorrido_resumen_row(act)
        assert row["estado_recorrido"] == estado_recorrido_label(act)
        assert "expediente_respuesta_numero" not in row
        assert "expediente_respuesta_anio" not in row
    finally:
        db.session.rollback()
