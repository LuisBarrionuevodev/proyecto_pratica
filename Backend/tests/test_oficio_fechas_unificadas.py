"""Unificación fecha oficio / expediente respuesta (schemas comprobación)."""

from __future__ import annotations

from datetime import date

from app.domains.actuaciones.schemas.comprobacion_documental_in import ComprobacionOficioBloquePatchIn
from app.domains.actuaciones.schemas.oficio_in import OficioCreateIn


def test_oficio_create_in_unifica_fecha_expediente_a_oficio() -> None:
    d = date(2026, 4, 10)
    d2 = date(2026, 5, 1)
    m = OficioCreateIn(
        numero_oficio="1",
        fecha_oficio=d,
        juzgado_id=1,
        causa=None,
        numero_expediente_oficio="123456",
        fecha_expediente_oficio=d2,
    )
    assert m.fecha_expediente_oficio == d


def test_oficio_create_in_omite_fecha_expediente() -> None:
    d = date(2026, 4, 10)
    m = OficioCreateIn(
        numero_oficio="1",
        fecha_oficio=d,
        juzgado_id=1,
        causa=None,
        numero_expediente_oficio="123456",
        fecha_expediente_oficio=None,
    )
    assert m.fecha_expediente_oficio == d


def test_comprobacion_oficio_patch_unifica() -> None:
    fo = date(2026, 6, 1)
    fe = date(2026, 7, 1)
    m = ComprobacionOficioBloquePatchIn(
        numero_oficio="2",
        fecha_oficio=fo,
        juzgado_id=1,
        causa=None,
        numero_expediente_respuesta="654321",
        fecha_expediente_respuesta=fe,
    )
    assert m.fecha_expediente_respuesta == fo


def test_comprobacion_oficio_patch_sin_fecha_expediente() -> None:
    fo = date(2026, 6, 1)
    m = ComprobacionOficioBloquePatchIn(
        numero_oficio="2",
        fecha_oficio=fo,
        juzgado_id=1,
        causa=None,
        numero_expediente_respuesta="654321",
        fecha_expediente_respuesta=None,
    )
    assert m.fecha_expediente_respuesta == fo
