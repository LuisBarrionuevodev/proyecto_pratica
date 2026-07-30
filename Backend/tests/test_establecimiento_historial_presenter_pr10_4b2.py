"""Presenter historial actuaciones por ficha operativa (PR10.4b.2 / PR10.4b.3)."""

from __future__ import annotations

import random
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from app.database import db
from app.domains.establecimientos.presenters.establecimiento_operativo_presenters import (
    actuacion_historial_row,
    actuacion_historial_rows,
)
from app.models import Actuaciones, Domicilio, EstablecimientoOperativo, Inspeccion, OrdenTrabajo, User


def _unique_ot() -> str:
    return f"{random.randint(0, 999999):06d}"


def test_actuacion_historial_rows_incluye_actas_tramites(app) -> None:
    with app.app_context():
        u = User(
            username=f"u_hist_{random.randint(0, 999999)}",
            email=f"hist_{random.randint(0, 999999)}@t.local",
            password_hash="x",
            role="usuario",
            is_active=True,
        )
        db.session.add(u)
        db.session.flush()

        dom = Domicilio(calle=f"CalleHist{random.randint(0, 99999)}", numero="10")
        db.session.add(dom)
        db.session.flush()

        eo = EstablecimientoOperativo(domicilio_id=dom.id, created_by_user_id=u.id)
        db.session.add(eo)
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_ot(), anio=2026, mes=3)
        db.session.add(ot)
        db.session.flush()

        act = Actuaciones(
            fecha=date(2026, 3, 15),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot.id,
            establecimiento_operativo_id=eo.id,
            tipo="INSPECCION",
        )
        db.session.add(act)
        db.session.flush()

        ins_num = f"{random.randint(0, 999999):06d}"
        ins = Inspeccion(actuacion_id=act.id, numero_acta=ins_num, anio=2026, mes=3)
        db.session.add(ins)
        db.session.commit()

        act_loaded = Actuaciones.query.filter_by(id=act.id).first()
        rows = actuacion_historial_rows([act_loaded])
        assert len(rows) == 1
        row = rows[0]
        assert row["tipo_actuacion"] == "INSPECCION"
        assert row["actas"]["inspeccion"]["texto"] == f"{ins_num}/2026"
        assert "Insp." in (row["actas_tramites_texto"] or "")
        assert "contraproducencia" in row
        assert "inspectores_texto" in row
        assert "nombre_local" not in row


def test_inspectores_historial_texto_concatena_nombres() -> None:
    act = SimpleNamespace(
        inspector=[
            SimpleNamespace(id=1, nombre="Zacarme Ariel"),
            SimpleNamespace(id=2, nombre="Villafañe Angel Antonio"),
        ]
    )
    from app.domains.establecimientos.presenters.historial_contribuyente_presenters import (
        inspectores_historial_texto,
    )

    assert inspectores_historial_texto(act) == "Zacarme Ariel, Villafañe Angel Antonio"
    assert inspectores_historial_texto(SimpleNamespace(inspector=[])) is None


def test_actuacion_historial_row_contraproducencia_desde_ruta_item(app) -> None:
    """NO_REALIZADO: motivo_no_realizado en ruta_item cuando act.contraproducencia es null."""
    with app.app_context():
        u = User(
            username=f"u_cp_{random.randint(0, 999999)}",
            email=f"cp_{random.randint(0, 999999)}@t.local",
            password_hash="x",
            role="usuario",
            is_active=True,
        )
        db.session.add(u)
        db.session.flush()

        dom = Domicilio(calle=f"CalleCp{random.randint(0, 99999)}", numero="20")
        db.session.add(dom)
        db.session.flush()

        eo = EstablecimientoOperativo(domicilio_id=dom.id, created_by_user_id=u.id)
        db.session.add(eo)
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_ot(), anio=2026, mes=3)
        db.session.add(ot)
        db.session.flush()

        act = Actuaciones(
            fecha=date(2026, 3, 16),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot.id,
            establecimiento_operativo_id=eo.id,
            tipo="REINSPECCION",
            contraproducencia=None,
        )
        db.session.add(act)
        db.session.commit()

        act_loaded = Actuaciones.query.filter_by(id=act.id).first()
        fake_ri = SimpleNamespace(motivo_no_realizado="LOCAL_CERRADO")
        row = actuacion_historial_row(act_loaded, ruta_item=fake_ri)
        assert row["contraproducencia"] == "LOCAL CERRADO"

        with patch(
            "app.domains.establecimientos.presenters.establecimiento_operativo_presenters._load_ruta_items_by_actuacion_id",
            return_value={int(act.id): fake_ri},
        ):
            rows = actuacion_historial_rows([act_loaded])
        assert rows[0]["contraproducencia"] == "LOCAL CERRADO"
