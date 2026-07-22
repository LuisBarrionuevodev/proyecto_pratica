"""
PR7.8 — Rubro correcto y discriminadores de relevamiento en presenters de Ruta de Trabajo.
"""

from __future__ import annotations

import random
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.database import db
from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_to_row,
)
from app.domains.rutas_trabajo.presenters.ruta_presenters import (
    _ruta_item_ubicacion_y_geo,
    iniciador_pendiente_to_row,
    ruta_item_to_min_dict,
)
from app.models import Domicilio, IniciadorRuta, Relevamiento, Rubro, User


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _unique_name(prefix: str) -> str:
    return f"{prefix}{_unique_num()}"


def _ensure_user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u:
        return u
    u = User(
        username=f"pr78_{_unique_num()}",
        email=f"pr78_{_unique_num()}@test.local",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _migration_pr72_aplicada() -> bool:
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("relevamiento")}
    return "nombre_fantasia" in cols and "angulo_esquina" in cols


@pytest.fixture
def require_pr72_migration(app_ctx):
    if not _migration_pr72_aplicada():
        pytest.skip("Requiere migración PR7.2 (revision b7e8f9a0c1d2) aplicada en BD")


def test_pr78_relevamiento_rubro_prioriza_sobre_domicilio(app_ctx, require_pr72_migration) -> None:
    """ESQUINA multi-rubro: rubro del relevamiento, no el último en domicilio."""
    try:
        rub_carn = Rubro(nombre=_unique_name("CarniceriaPr78"))
        rub_verd = Rubro(nombre=_unique_name("VerduleriaPr78"))
        db.session.add_all([rub_carn, rub_verd])
        db.session.flush()

        dom = Domicilio(
            calle=f"EsquinaPr78{_unique_num()}",
            numero="Y Maipu",
            numero_tipo="ESQUINA",
            rubro_id=rub_verd.id,
        )
        db.session.add(dom)
        db.session.flush()

        rel = Relevamiento(
            fecha=date.today(),
            mes=7,
            anio=2026,
            inspector_id=1,
            domicilio_id=dom.id,
            rubro_id=rub_carn.id,
            nombre_fantasia="El Toro",
            angulo_esquina="NE",
        )
        db.session.add(rel)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=7,
            domicilio_id=dom.id,
            relevamiento_id=rel.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        row = iniciador_pendiente_to_row(ini)
        assert row["rubro_nombre"] == rub_carn.nombre
        assert row["domicilio"]["rubro"] == rub_carn.nombre
        assert row["nombre_fantasia"] == "El Toro"
        assert row["angulo_esquina"] == "NE"
    finally:
        db.session.rollback()


def test_pr78_relevamiento_nombre_fantasia_vacio_es_null(app_ctx, require_pr72_migration) -> None:
    try:
        rub = Rubro(nombre=_unique_name("RubPr78"))
        db.session.add(rub)
        db.session.flush()

        dom = Domicilio(calle=f"NFPr78{_unique_num()}", numero="10", rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()

        rel = Relevamiento(
            fecha=date.today(),
            mes=7,
            anio=2026,
            inspector_id=1,
            domicilio_id=dom.id,
            rubro_id=rub.id,
            nombre_fantasia="   ",
            angulo_esquina=None,
        )
        db.session.add(rel)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=7,
            domicilio_id=dom.id,
            relevamiento_id=rel.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        row = iniciador_pendiente_to_row(ini)
        assert row["nombre_fantasia"] is None
        assert row["angulo_esquina"] is None
    finally:
        db.session.rollback()


def test_pr78_denuncia_sigue_usando_domicilio_rubro(app_ctx) -> None:
    try:
        rub_dom = Rubro(nombre=_unique_name("RubDomPr78"))
        rub_rel = Rubro(nombre=_unique_name("RubRelPr78"))
        db.session.add_all([rub_dom, rub_rel])
        db.session.flush()

        dom = Domicilio(calle=f"DenPr78{_unique_num()}", numero="20", rubro_id=rub_dom.id)
        db.session.add(dom)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=7,
            domicilio_id=dom.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        row = iniciador_pendiente_to_row(ini)
        assert row["rubro_nombre"] == rub_dom.nombre
        assert row["nombre_fantasia"] is None
        assert row["angulo_esquina"] is None
    finally:
        db.session.rollback()


def test_pr78_relevamiento_sin_relacion_cargada_fallback_domicilio(app_ctx) -> None:
    """Sin relevamiento cargado: no rompe; usa rubro del domicilio."""
    try:
        rub = Rubro(nombre=_unique_name("RubFallbackPr78"))
        db.session.add(rub)
        db.session.flush()

        dom = Domicilio(calle=f"FbPr78{_unique_num()}", numero="30", rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=7,
            domicilio_id=dom.id,
            relevamiento_id=None,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        row = iniciador_pendiente_to_row(ini)
        assert row["rubro_nombre"] == rub.nombre
        assert row["nombre_fantasia"] is None
        assert row["angulo_esquina"] is None
    finally:
        db.session.rollback()


def test_pr78_ruta_item_ubicacion_rubro_y_discriminadores(app_ctx, require_pr72_migration) -> None:
    try:
        rub_carn = Rubro(nombre=_unique_name("CarnItemPr78"))
        rub_verd = Rubro(nombre=_unique_name("VerdItemPr78"))
        db.session.add_all([rub_carn, rub_verd])
        db.session.flush()

        dom = Domicilio(
            calle=f"ItemPr78{_unique_num()}",
            numero="Y Salta",
            numero_tipo="ESQUINA",
            rubro_id=rub_verd.id,
        )
        db.session.add(dom)
        db.session.flush()

        rel = Relevamiento(
            fecha=date.today(),
            mes=7,
            anio=2026,
            inspector_id=1,
            domicilio_id=dom.id,
            rubro_id=rub_carn.id,
            nombre_fantasia="La Vaquita",
            angulo_esquina="SO",
        )
        db.session.add(rel)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PLANIFICADO",
            fecha_origen=date.today(),
            anio=2026,
            mes=7,
            domicilio_id=dom.id,
            relevamiento_id=rel.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        item = MagicMock()
        item.id = 501
        item.ruta_trabajo_id = 1
        item.ruta_grupo_id = 2
        item.iniciador_ruta_id = ini.id
        item.orden_trabajo_id = None
        item.actuacion_id = None
        item.orden_trabajo = None
        item.estado_ruta_item = "ASIGNADO"
        item.deleted_at = None
        item.iniciador_ruta = ini

        ubic = _ruta_item_ubicacion_y_geo(item)
        assert ubic["rubro_nombre"] == rub_carn.nombre
        assert ubic["nombre_fantasia"] == "La Vaquita"
        assert ubic["angulo_esquina"] == "SO"

        d = ruta_item_to_min_dict(item)
        assert d["rubro_nombre"] == rub_carn.nombre
        assert d["nombre_fantasia"] == "La Vaquita"
        assert d["angulo_esquina"] == "SO"
    finally:
        db.session.rollback()


def test_pr78_completar_trabajo_presenter_sin_fantasia_ni_angulo() -> None:
    """Completar Trabajo no debe exponer discriminadores de relevamiento (PR7.8)."""
    act = MagicMock()
    act.id = 1
    act.domicilio = None
    act.inspector = []
    act.orden_trabajo = None
    act.tipo = "INSPECCION"
    act.contraproducencia = None
    act.nombre_local = None
    act.establecimiento_operativo_id = None

    ini = MagicMock()
    ini.tipo_iniciador = "RELEVAMIENTO"
    ini.estado_iniciador = "EN_EJECUCION"
    rel = MagicMock()
    rel.rubro = MagicMock(nombre="Carniceria")
    rel.nombre_fantasia = "El Toro"
    rel.angulo_esquina = "NE"
    ini.relevamiento = rel

    item = MagicMock()
    item.id = 99
    item.ruta_trabajo_id = 1
    item.ruta_grupo_id = 2
    item.iniciador_ruta_id = 10
    item.iniciador_ruta = ini
    item.actuacion = act
    item.ruta_grupo = None
    item.estado_ruta_item = "EN_CURSO"
    item.observaciones_ejecucion = None

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.domains.actuaciones.presenters.completar_trabajo_presenters.actuacion_to_grid_row",
            lambda _act, **_: {
                "rubro_nombre": "Verduleria",
                "calle": "Maipu",
                "numero": "500",
                "fecha_actuacion": "2026-07-01",
                "orden_trabajo_numero": "OT-1",
                "tipo_actuacion": "INSPECCION",
                "domicilio_id": 5,
            },
        )
        row = ruta_item_completar_trabajo_to_row(item)

    assert "nombre_fantasia" not in row
    assert "angulo_esquina" not in row
    assert row["rubro_nombre"] == "Carniceria"
