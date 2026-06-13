"""
STAB-6 — búsqueda liviana de actuaciones y órdenes.
"""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.schemas.list_filters import ActuacionesListFilters
from app.domains.actuaciones.services.list_service import listar_actuaciones_con_filtros
from app.domains.actuaciones.services.search_service import (
    buscar_actuaciones_liviano,
    buscar_ordenes_liviano,
)
from app.models import Actuaciones, Contribuyente, Domicilio, OrdenTrabajo, Rubro


def _unique_ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_actuacion_con_domicilio(
    *,
    ot_num: str,
    calle: str,
    rubro_nombre: str,
    apellido: str,
    fecha: date | None = None,
) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=ot_num, anio=2024, mes=1)
    db.session.add(ot)
    db.session.flush()
    rub = Rubro(nombre=rubro_nombre)
    db.session.add(rub)
    db.session.flush()
    doc = f"{random.randint(10_000_000, 99_999_999)}"
    contrib = Contribuyente(apellido=apellido, nombre="Test", documento=doc)
    db.session.add(contrib)
    db.session.flush()
    dom = Domicilio(calle=calle, numero="100", rubro_id=rub.id, contribuyente_id=contrib.id)
    db.session.add(dom)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha or date(2024, 1, 15),
        mes=1,
        anio=2024,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_buscar_actuaciones_por_domicilio_respeta_limit(app_ctx) -> None:
    try:
        suffix = _unique_ot_num()
        act = _mk_actuacion_con_domicilio(
            ot_num=suffix,
            calle=f"CalleUnicaStab6{suffix}",
            rubro_nombre=f"Almacén STAB6 {suffix}",
            apellido="Pérez",
        )
        needle = f"CalleUnicaStab6{suffix}"
        items = buscar_actuaciones_liviano(needle, limit=5)
        assert len(items) <= 5
        assert any(i["id"] == act.id for i in items)
        assert all("label" in i and "id" in i for i in items)
        assert all(len(i.keys()) <= 10 for i in items)
    finally:
        db.session.rollback()


def test_buscar_actuaciones_q_corto_valueerror(app_ctx) -> None:
    with pytest.raises(ValueError, match="2 caracteres"):
        buscar_actuaciones_liviano("a")


def test_buscar_ordenes_por_numero(app_ctx) -> None:
    try:
        num = _unique_ot_num()
        ot = OrdenTrabajo(numero_acta=num, anio=2025, mes=3)
        db.session.add(ot)
        db.session.flush()
        items = buscar_ordenes_liviano(str(int(num)), limit=10)
        assert any(i["numero_acta"] == num for i in items)
        assert all("label" in i for i in items)
    finally:
        db.session.rollback()


def test_listar_sin_fechas_cuando_orden_trabajo(app_ctx) -> None:
    """OT fuera del mes corriente debe encontrarse sin fechas."""
    try:
        num = _unique_ot_num()
        ot = OrdenTrabajo(numero_acta=num, anio=2020, mes=6)
        db.session.add(ot)
        db.session.flush()
        act = Actuaciones(fecha=date(2020, 6, 10), mes=6, anio=2020, orden_trabajo_id=ot.id)
        db.session.add(act)
        db.session.flush()
        filters = ActuacionesListFilters.model_validate({"orden_trabajo": str(int(num))})
        assert filters.desde is None
        assert filters.hasta is None
        result = listar_actuaciones_con_filtros(filters)
        assert result["meta"]["total"] == 1
        assert result["items"][0].id == act.id
    finally:
        db.session.rollback()


def test_search_route_q_vacio_422(client, auth_headers) -> None:
    resp = client.get("/actuaciones/search?q=a", headers=auth_headers)
    assert resp.status_code == 422


def test_search_route_encuentra_por_ot(client, auth_headers, app) -> None:
    with app.app_context():
        try:
            num = _unique_ot_num()
            rubro = f"Rubro Ruta {num}"
            _mk_actuacion_con_domicilio(
                ot_num=num,
                calle=f"RutaSearch{num}",
                rubro_nombre=rubro,
                apellido="García",
            )
            db.session.commit()
            resp = client.get(f"/actuaciones/search?q={int(num)}", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.get_json()
            assert "items" in data
            assert len(data["items"]) >= 1
            assert all("label" in it for it in data["items"])
        finally:
            db.session.rollback()
