"""
STAB-2 — Varios oficios pueden compartir la misma causa en un mismo año.

La clave natural sigue siendo (numero_oficio, anio).
"""

from __future__ import annotations

import random
from datetime import date, datetime, timezone

import pytest

from app import create_app
from app.database import db
from app.domains.actuaciones.attach.oficio import attach_oficio
from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.models import (
    Actuaciones,
    Comprobacion,
    Domicilio,
    DomicilioGeocode,
    JuzgadoCatalogo,
    OrdenTrabajo,
)


def _uniq_num() -> str:
    return str(random.randint(100000, 999999))


def _num_oficio() -> str:
    return f"OF{_uniq_num()[:6]}"


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_comprobacion() -> Comprobacion:
    c = Comprobacion(
        numero_acta=_uniq_num(),
        anio=2026,
        mes=3,
        motivo="test stab2 causa multiples",
    )
    db.session.add(c)
    db.session.flush()
    return c


def _actuacion_comprobacion() -> tuple[Actuaciones, JuzgadoCatalogo]:
    ot = OrdenTrabajo(numero_acta=_uniq_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    dom = Domicilio(calle="STAB2", numero="1", distrito_id=None)
    db.session.add(dom)
    db.session.flush()
    geo = DomicilioGeocode(domicilio_id=dom.id, lat=-34.6, lng=-58.38, geo_status="OK")
    db.session.add(geo)
    db.session.flush()
    comp = _mk_comprobacion()
    act = Actuaciones(
        fecha=date(2026, 3, 15),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    j = JuzgadoCatalogo(codigo=f"j_{_uniq_num()[:8]}", nombre=f"Juz {_uniq_num()[:8]}")
    db.session.add(j)
    db.session.flush()
    return act, j


def test_crea_oficio_causa_nueva_ok(app_ctx) -> None:
    try:
        c = _mk_comprobacion()
        num = _num_oficio()
        o = attach_oficio(
            {"numero": num, "anio": 2026, "causa": "123"},
            comprobacion_id=c.id,
        )
        assert o is not None
        assert o.causa == "123"
    finally:
        db.session.rollback()


def test_misma_causa_mismo_anio_distinto_numero_ok(app_ctx) -> None:
    try:
        c = _mk_comprobacion()
        num1, num2 = _num_oficio(), _num_oficio()
        o1 = attach_oficio(
            {"numero": num1, "anio": 2026, "causa": "123"},
            comprobacion_id=c.id,
        )
        o2 = attach_oficio(
            {"numero": num2, "anio": 2026, "causa": "123"},
            comprobacion_id=c.id,
        )
        db.session.flush()
        assert o1.id != o2.id
        assert o1.causa == o2.causa == "123"
    finally:
        db.session.rollback()


def test_misma_causa_distintas_comprobaciones_ok(app_ctx) -> None:
    try:
        c1 = _mk_comprobacion()
        c2 = _mk_comprobacion()
        num1, num2 = _num_oficio(), _num_oficio()
        o1 = attach_oficio(
            {"numero": num1, "anio": 2026, "causa": "123"},
            comprobacion_id=c1.id,
        )
        o2 = attach_oficio(
            {"numero": num2, "anio": 2026, "causa": "123"},
            comprobacion_id=c2.id,
        )
        db.session.flush()
        assert o1.comprobacion_id != o2.comprobacion_id
        assert o1.causa == o2.causa == "123"
    finally:
        db.session.rollback()


def test_misma_causa_distinto_anio_ok(app_ctx) -> None:
    try:
        c1 = _mk_comprobacion()
        c2 = _mk_comprobacion()
        num1, num2 = _num_oficio(), _num_oficio()
        attach_oficio(
            {"numero": num1, "anio": 2026, "causa": "888"},
            comprobacion_id=c1.id,
        )
        o2 = attach_oficio(
            {"numero": num2, "anio": 2027, "causa": "888"},
            comprobacion_id=c2.id,
        )
        db.session.flush()
        assert o2.anio == 2027
        assert o2.causa == "888"
    finally:
        db.session.rollback()


def test_reintento_mismo_oficio_misma_causa_idempotente(app_ctx) -> None:
    try:
        c = _mk_comprobacion()
        num = _num_oficio()
        o1 = attach_oficio(
            {"numero": num, "anio": 2026, "causa": "123"},
            comprobacion_id=c.id,
        )
        db.session.flush()
        o2 = attach_oficio(
            {"numero": num, "anio": 2026, "causa": "123"},
            comprobacion_id=c.id,
        )
        assert o1.id == o2.id
        assert o2.causa == "123"
    finally:
        db.session.rollback()


def test_mismo_numero_anio_causa_distinta_bloquea(app_ctx) -> None:
    try:
        c = _mk_comprobacion()
        num = _num_oficio()
        attach_oficio(
            {"numero": num, "anio": 2026, "causa": "123"},
            comprobacion_id=c.id,
        )
        db.session.flush()
        with pytest.raises(ValueError, match='ya existe con otra causa'):
            attach_oficio(
                {"numero": num, "anio": 2026, "causa": "999"},
                comprobacion_id=c.id,
            )
    finally:
        db.session.rollback()


def test_multiples_oficios_causa_null_mismo_anio_ok(app_ctx) -> None:
    try:
        c = _mk_comprobacion()
        o1 = attach_oficio(
            {"numero": _uniq_num(), "anio": 2026, "causa": None},
            comprobacion_id=c.id,
        )
        o2 = attach_oficio(
            {"numero": _uniq_num(), "anio": 2026, "causa": None},
            comprobacion_id=c.id,
        )
        db.session.flush()
        assert o1.id != o2.id
        assert o1.causa is None
        assert o2.causa is None
    finally:
        db.session.rollback()


def test_complete_oficio_misma_causa_genera_expediente_e_iniciador_propios(app_ctx) -> None:
    act, juz = _actuacion_comprobacion()
    db.session.commit()
    complete_expediente_from_actuacion(
        act.id,
        {"expediente_numero": _uniq_num()[:6], "fecha_expediente": "2026-03-18"},
    )

    causa = "123"
    num1, num2 = _num_oficio(), _num_oficio()
    payload_base = {
        "juzgado_id": juz.id,
        "fecha_oficio": date(2026, 4, 1),
        "fecha_expediente_oficio": date(2026, 4, 1),
        "causa": causa,
    }
    r1 = complete_oficio_from_actuacion(
        act.id,
        {
            **payload_base,
            "numero_oficio": num1,
            "numero_expediente_oficio": _uniq_num()[:6],
        },
    )
    r2 = complete_oficio_from_actuacion(
        act.id,
        {
            **payload_base,
            "numero_oficio": num2,
            "numero_expediente_oficio": _uniq_num()[:6],
            "fecha_oficio": date(2026, 5, 2),
            "fecha_expediente_oficio": date(2026, 5, 2),
        },
    )

    assert r1["oficio"].causa == r2["oficio"].causa == causa
    assert r1["oficio"].id != r2["oficio"].id
    assert r1["expediente_respuesta_oficio"].id != r2["expediente_respuesta_oficio"].id
    assert r1["iniciador_ruta"].id != r2["iniciador_ruta"].id


def test_oficio_soft_delete_no_bloquea_nuevo_mismo_numero(app_ctx) -> None:
    try:
        c = _mk_comprobacion()
        num = _num_oficio()
        o1 = attach_oficio(
            {"numero": num, "anio": 2026, "causa": "123"},
            comprobacion_id=c.id,
        )
        db.session.flush()
        o1.deleted_at = datetime.now(timezone.utc)
        db.session.add(o1)
        db.session.flush()

        o2 = attach_oficio(
            {"numero": num, "anio": 2026, "causa": "123"},
            comprobacion_id=c.id,
        )
        assert o2.id == o1.id
        assert o2.deleted_at is None
    finally:
        db.session.rollback()
