"""
GET /actuaciones/<id>/notificacion/expedientes-prorroga — trazabilidad de prórrogas.
"""

from __future__ import annotations

import random
from datetime import date

from app.database import db
from app.domains.actuaciones.services.expediente_completion_service import (
    complete_expediente_from_actuacion,
)
from app.domains.actuaciones.services.notificacion_timing_service import (
    inicializar_timing_notificacion,
)
from app.models import Actuaciones, Notificacion, OrdenTrabajo


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_actuacion_solo_notificacion() -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
    db.session.add(noti)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_get_prorroga_expedientes_sin_jwt_401(client):
    resp = client.get("/actuaciones/1/notificacion/expedientes-prorroga")
    assert resp.status_code == 401


def test_get_prorroga_expedientes_404(client, auth_headers):
    resp = client.get("/actuaciones/999999999/notificacion/expedientes-prorroga", headers=auth_headers)
    assert resp.status_code == 404
    assert "no encontrada" in (resp.get_json() or {}).get("detail", "").lower()


def test_get_prorroga_expedientes_sin_notificacion_400(app, client, auth_headers):
    from app.models import Comprobacion

    with app.app_context():
        try:
            ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
            db.session.add(ot)
            db.session.flush()
            comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="x")
            db.session.add(comp)
            db.session.flush()
            act = Actuaciones(
                fecha=date(2026, 3, 1),
                mes=3,
                anio=2026,
                orden_trabajo_id=ot.id,
                comprobacion_id=comp.id,
            )
            db.session.add(act)
            db.session.flush()
            aid = act.id
            db.session.commit()

            resp = client.get(
                f"/actuaciones/{aid}/notificacion/expedientes-prorroga",
                headers=auth_headers,
            )
            assert resp.status_code == 400
        finally:
            db.session.rollback()


def test_get_prorroga_expedientes_lista_y_consolidado(app, client, auth_headers):
    with app.app_context():
        try:
            act = _mk_actuacion_solo_notificacion()
            nid = act.notificacion_id
            db.session.commit()

            complete_expediente_from_actuacion(
                act.id,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 10),
                    "prorroga_dias": 2,
                },
            )
            complete_expediente_from_actuacion(
                act.id,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 12),
                    "prorroga_dias": 1,
                },
            )

            resp = client.get(
                f"/actuaciones/{act.id}/notificacion/expedientes-prorroga",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            body = resp.get_json()
            assert body is not None
            assert body["actuacion_id"] == act.id
            assert body["notificacion_id"] == nid
            assert body["plazos_otorgados"] == 2
            assert len(body["items"]) == 2
            assert body["consolidado"]["prorroga_dias"] == 3
            assert body["consolidado"]["plazo_dias"] is not None
            assert body["items"][0]["prorroga_dias_solicitada"] is None
            assert body["items"][0]["numero_expediente"] is not None
            assert body["items"][0]["anio"] == "2026"
            assert body["items"][0]["fecha_expediente"] == "2026-03-10"
            assert body["items"][1]["fecha_expediente"] == "2026-03-12"
        finally:
            db.session.rollback()
