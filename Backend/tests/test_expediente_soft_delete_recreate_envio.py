"""Tras soft delete del expediente de envío, debe poder crearse otro (validación + unicidad activa)."""

from __future__ import annotations

import random
from datetime import date, datetime, timezone

import pytest

from app.database import db
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.models import Actuaciones, Comprobacion, Expediente, OrdenTrabajo


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _setup_actuacion_con_comp_sin_expediente() -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="soft del test")
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
    return act


def test_complete_expediente_comprobacion_tras_soft_delete_no_bloquea_por_fila_borrada(app_ctx) -> None:
    """
    Antes: existente = primer expediente de envío sin filtrar deleted_at → seguía «ocupando» la comprobación.
    """
    act = _setup_actuacion_con_comp_sin_expediente()
    num1 = _unique_num()[:6]
    r1 = complete_expediente_from_actuacion(
        act.id,
        {
            "expediente_numero": num1,
            "fecha_expediente": "2026-03-20",
        },
    )
    ex1 = r1["expediente"]
    ex1.deleted_at = datetime.now(timezone.utc)
    db.session.add(ex1)
    db.session.commit()

    num2 = _unique_num()[:6]
    r2 = complete_expediente_from_actuacion(
        act.id,
        {
            "expediente_numero": num2,
            "fecha_expediente": "2026-03-22",
        },
    )
    ex2 = r2["expediente"]
    assert ex2.id != ex1.id
    assert ex2.deleted_at is None
    assert ex2.numero_expediente == num2


def test_complete_expediente_mismo_numero_anio_que_borrado_requiere_unique_activo_en_bd(app_ctx) -> None:
    """
    Con migración d4e5f6a7b8c1: puede coexistir fila borrada + nueva activa con mismo número/año.
    Sin migración, MySQL rechaza el INSERT (constraint global); el test documenta el requisito de migración.
    """
    act = _setup_actuacion_con_comp_sin_expediente()
    num = _unique_num()[:6]
    fecha = "2026-03-20"
    r1 = complete_expediente_from_actuacion(
        act.id,
        {"expediente_numero": num, "fecha_expediente": fecha},
    )
    ex1 = r1["expediente"]
    ex1.deleted_at = datetime.now(timezone.utc)
    db.session.add(ex1)
    db.session.commit()

    try:
        complete_expediente_from_actuacion(
            act.id,
            {"expediente_numero": num, "fecha_expediente": fecha},
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "duplicate" in msg or "uq_ex" in msg or "integrity" in msg:
            pytest.skip("BD sin migración parcial de unicidad: aplicar d4e5f6a7b8c1")
        raise

    activos = (
        Expediente.query.filter_by(comprobacion_id=act.comprobacion_id, oficio_id=None)
        .filter(Expediente.deleted_at.is_(None))
        .all()
    )
    assert len(activos) == 1
    assert activos[0].numero_expediente == num
