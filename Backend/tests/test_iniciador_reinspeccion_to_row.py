"""Presenter ``iniciador_reinspeccion_to_row``: campos de paridad con tabla Recorrido."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    iniciador_reinspeccion_to_row,
    estado_recorrido_label,
)
from app.models import Actuaciones, Comprobacion, Domicilio, IniciadorRuta, OrdenTrabajo, User


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def test_iniciador_reinspeccion_to_row_incluye_estado_recorrido_y_tipo_visita_resultado(app_ctx) -> None:
    """La fila pendiente debe exponer el mismo criterio de circuito y resultado que Recorrido."""
    try:
        u = User(
            username=f"u_rein_{random.randint(0, 999999)}",
            email=f"rein_{random.randint(0, 999999)}@t.local",
            password_hash="x",
            role="usuario",
            is_active=True,
        )
        db.session.add(u)
        dom = Domicilio(calle=f"CalleRein{random.randint(0, 99999)}", numero="1")
        db.session.add(dom)
        db.session.flush()
        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(ot)
        db.session.flush()
        comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="Falta documentación")
        db.session.add(comp)
        db.session.flush()
        act = Actuaciones(
            fecha=date(2026, 3, 10),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot.id,
            comprobacion_id=comp.id,
            tipo="INSPECCION",
        )
        db.session.add(act)
        db.session.flush()

        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 3, 12),
            anio=2026,
            mes=3,
            domicilio_id=dom.id,
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        row = iniciador_reinspeccion_to_row(ini, act)
        assert row["iniciador_id"] == ini.id
        assert "estado_recorrido" in row
        assert row["estado_recorrido"] == estado_recorrido_label(act)
        assert "tipo_visita_resultado" in row
        assert row.get("comprobacion_motivo") == "Falta documentación"
    finally:
        db.session.rollback()
