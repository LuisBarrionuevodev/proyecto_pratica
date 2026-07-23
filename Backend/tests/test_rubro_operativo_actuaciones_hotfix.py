"""HOTFIX — Rubro operativo en Actuaciones y Completar Trabajo (ESQUINA multi-rubro)."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

from unittest.mock import patch

import pytest
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    build_iniciador_ruta_por_actuacion_id,
)
from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_to_row,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import (
    Actuaciones,
    Denuncia,
    Domicilio,
    IniciadorRuta,
    Inspector,
    Relevamiento,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _migration_pr72_aplicada() -> bool:
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("relevamiento")}
    return "nombre_fantasia" in cols and "angulo_esquina" in cols


@pytest.fixture
def require_pr72_migration(app_ctx):
    if not _migration_pr72_aplicada():
        pytest.skip("Requiere migración PR7.2 (revision b7e8f9a0c1d2) aplicada en BD")


def _inspector() -> Inspector:
    ins = Inspector.query.first()
    if ins is None:
        pytest.skip("Se requiere al menos un inspector en catálogo")
    return ins


def _dos_inspectores() -> tuple[Inspector, Inspector]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores para publicar ruta")
    return rows[0], rows[1]


def _payload_esquina(
    *,
    calle: str,
    rubro: str,
    inspector: str,
    fecha: str,
    nombre_fantasia: str | None = None,
    angulo_esquina: str | None = None,
):
    dom = {"calle": calle, "numero": "y Maipu", "numero_tipo": "ESQUINA"}
    out = {
        "fecha": fecha,
        "inspector_nombre": inspector,
        "domicilio": dom,
        "rubro_nombre": rubro,
    }
    if nombre_fantasia is not None:
        out["nombre_fantasia"] = nombre_fantasia
    if angulo_esquina is not None:
        out["angulo_esquina"] = angulo_esquina
    return out


def _crear_esquina_multi_establecimiento():
    ins = _inspector()
    rub_a = Rubro(nombre=_uniq("PanaderiaHotfix"))
    rub_b = Rubro(nombre=_uniq("CarniceriaHotfix"))
    db.session.add_all([rub_a, rub_b])
    db.session.flush()

    calle = _uniq("SanMartinMaipuHotfix")
    rel_a = crear_relevamiento_desde_payload(
        _payload_esquina(
            calle=calle,
            rubro=rub_a.nombre,
            inspector=ins.nombre,
            fecha="2026-07-01",
            nombre_fantasia="Panadería NE",
            angulo_esquina="NE",
        )
    )
    rel_b = crear_relevamiento_desde_payload(
        _payload_esquina(
            calle=calle,
            rubro=rub_b.nombre,
            inspector=ins.nombre,
            fecha="2026-07-02",
            nombre_fantasia="Carnicería SO",
            angulo_esquina="SO",
        )
    )

    ini_a = IniciadorRuta.query.filter(
        IniciadorRuta.relevamiento_id == rel_a.id,
        IniciadorRuta.deleted_at.is_(None),
    ).first()
    ini_b = IniciadorRuta.query.filter(
        IniciadorRuta.relevamiento_id == rel_b.id,
        IniciadorRuta.deleted_at.is_(None),
    ).first()
    assert ini_a is not None and ini_b is not None
    dom = db.session.get(Domicilio, rel_a.domicilio_id)
    assert dom is not None
    return rel_a, rel_b, ini_a, ini_b, rub_a, rub_b, dom


def _setup_ruta_y_publicar(ini_ids: list[int]) -> list[RutaItem]:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u is None:
        pytest.skip("Se requiere usuario activo")
    ins1, ins2 = _dos_inspectores()
    ruta = RutaTrabajo(
        fecha=date(2026, 7, 11),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()

    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo Hotfix Rubro", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=ini_ids,
    )
    for item in items:
        set_orden_trabajo_on_item(
            ruta_id=ruta.id,
            item_id=item.id,
            numero_orden_trabajo=_unique_num(),
        )
    db.session.commit()
    publicar_ruta_trabajo(ruta_id=ruta.id)
    return (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.deleted_at.is_(None),
        )
        .options(
            joinedload(RutaItem.iniciador_ruta)
            .joinedload(IniciadorRuta.relevamiento)
            .joinedload(Relevamiento.rubro),
            joinedload(RutaItem.actuacion)
            .joinedload(Actuaciones.domicilio)
            .joinedload(Domicilio.rubro),
        )
        .order_by(RutaItem.id.asc())
        .all()
    )


def test_actuacion_grid_rubro_por_relevamiento_esquina_compartida(
    app_ctx, require_pr72_migration
) -> None:
    try:
        _rel_a, _rel_b, ini_a, ini_b, rub_a, rub_b, dom = _crear_esquina_multi_establecimiento()
        items = _setup_ruta_y_publicar([ini_a.id, ini_b.id])
        assert len(items) == 2

        by_ini = {it.iniciador_ruta_id: it for it in items}
        act_a = by_ini[ini_a.id].actuacion
        act_b = by_ini[ini_b.id].actuacion
        assert act_a is not None and act_b is not None
        assert act_a.domicilio_id == dom.id
        assert act_b.domicilio_id == dom.id

        ini_map = build_iniciador_ruta_por_actuacion_id([act_a.id, act_b.id])
        row_a = actuacion_to_grid_row(act_a, iniciador_desde_ruta=ini_map.get(act_a.id))
        row_b = actuacion_to_grid_row(act_b, iniciador_desde_ruta=ini_map.get(act_b.id))

        assert row_a["rubro_nombre"] == rub_a.nombre
        assert row_b["rubro_nombre"] == rub_b.nombre
        assert row_a["rubro_nombre"] != row_b["rubro_nombre"]
    finally:
        db.session.rollback()


def test_completar_trabajo_rubro_por_item_esquina_compartida(
    app_ctx, require_pr72_migration
) -> None:
    try:
        _rel_a, _rel_b, ini_a, ini_b, rub_a, rub_b, _dom = _crear_esquina_multi_establecimiento()
        items = _setup_ruta_y_publicar([ini_a.id, ini_b.id])
        by_ini = {it.iniciador_ruta_id: it for it in items}

        row_a = ruta_item_completar_trabajo_to_row(by_ini[ini_a.id])
        row_b = ruta_item_completar_trabajo_to_row(by_ini[ini_b.id])

        assert row_a["rubro_nombre"] == rub_a.nombre
        assert row_b["rubro_nombre"] == rub_b.nombre
    finally:
        db.session.rollback()


def test_domicilio_rubro_distinto_no_pisa_relevamiento(app_ctx, require_pr72_migration) -> None:
    """domicilio.rubro_id puede apuntar al otro establecimiento; no debe ganar sobre relevamiento."""
    try:
        rub_carn = Rubro(nombre=_uniq("CarnDomicilioHotfix"))
        rub_pan = Rubro(nombre=_uniq("PanRelevHotfix"))
        db.session.add_all([rub_carn, rub_pan])
        db.session.flush()

        dom = Domicilio(
            calle=_uniq("EsquinaRubroHotfix"),
            numero="y Maipu",
            numero_tipo="ESQUINA",
            rubro_id=rub_carn.id,
        )
        db.session.add(dom)
        db.session.flush()

        ins = _inspector()
        rel = crear_relevamiento_desde_payload(
            _payload_esquina(
                calle=dom.calle,
                rubro=rub_pan.nombre,
                inspector=ins.nombre,
                fecha="2026-07-03",
                angulo_esquina="NE",
            )
        )
        ini = IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel.id,
            IniciadorRuta.deleted_at.is_(None),
        ).first()
        assert ini is not None

        items = _setup_ruta_y_publicar([ini.id])
        act = items[0].actuacion
        assert act is not None

        row = actuacion_to_grid_row(
            act,
            iniciador_desde_ruta=items[0].iniciador_ruta,
        )
        assert row["rubro_nombre"] == rub_pan.nombre
        assert row["rubro_nombre"] != rub_carn.nombre
    finally:
        db.session.rollback()


def _mk_denuncia_en_domicilio(dom: Domicilio, u: User) -> IniciadorRuta:
    den = Denuncia(
        fecha=date(2026, 7, 5),
        anio=2026,
        mes=7,
        domicilio_id=dom.id,
        motivo="rubro hotfix",
        created_by_user_id=u.id,
    )
    db.session.add(den)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="DENUNCIA",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 7, 5),
        anio=2026,
        mes=7,
        domicilio_id=dom.id,
        denuncia_id=den.id,
        prioridad=1,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def test_denuncia_no_hereda_rubro_domicilio_compartido(app_ctx) -> None:
    try:
        rub_dom = Rubro(nombre=_uniq("RubDenHotfix"))
        db.session.add(rub_dom)
        db.session.flush()

        dom = Domicilio(calle=_uniq("DenHotfix"), numero="50", rubro_id=rub_dom.id)
        db.session.add(dom)
        db.session.flush()

        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")

        ini = _mk_denuncia_en_domicilio(dom, u)
        items = _setup_ruta_y_publicar([ini.id])
        act = items[0].actuacion
        assert act is not None

        row = actuacion_to_grid_row(
            act,
            iniciador_desde_ruta=items[0].iniciador_ruta,
        )
        ct_row = ruta_item_completar_trabajo_to_row(items[0])
        assert row["rubro_nombre"] is None
        assert ct_row["rubro_nombre"] is None
    finally:
        db.session.rollback()


def test_denuncia_esquina_compartida_no_hereda_rubros_relevamiento(
    app_ctx, require_pr72_migration
) -> None:
    try:
        _rel_a, _rel_b, ini_a, ini_b, rub_a, rub_b, dom = _crear_esquina_multi_establecimiento()
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        ini_den = _mk_denuncia_en_domicilio(dom, u)

        items = _setup_ruta_y_publicar([ini_a.id, ini_b.id, ini_den.id])
        by_ini = {it.iniciador_ruta_id: it for it in items}
        item_den = by_ini[ini_den.id]
        act_den = item_den.actuacion
        assert act_den is not None

        row_den = actuacion_to_grid_row(act_den, iniciador_desde_ruta=item_den.iniciador_ruta)
        ct_den = ruta_item_completar_trabajo_to_row(item_den)
        row_a = actuacion_to_grid_row(
            by_ini[ini_a.id].actuacion,
            iniciador_desde_ruta=by_ini[ini_a.id].iniciador_ruta,
        )
        row_b = actuacion_to_grid_row(
            by_ini[ini_b.id].actuacion,
            iniciador_desde_ruta=by_ini[ini_b.id].iniciador_ruta,
        )

        assert row_den["rubro_nombre"] is None
        assert ct_den["rubro_nombre"] is None
        assert row_a["rubro_nombre"] == rub_a.nombre
        assert row_b["rubro_nombre"] == rub_b.nombre
    finally:
        db.session.rollback()


def test_denuncia_completada_muestra_rubro_constatado(app_ctx, require_pr72_migration) -> None:
    try:
        _rel_a, _rel_b, _ini_a, _ini_b, rub_a, rub_b, dom = _crear_esquina_multi_establecimiento()
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        rub_verd = Rubro(nombre=_uniq("VerduleriaDenHotfix"))
        db.session.add(rub_verd)
        db.session.flush()
        rub_verd_nombre = rub_verd.nombre
        rub_a_nombre = rub_a.nombre
        rub_b_nombre = rub_b.nombre

        ini_den = _mk_denuncia_en_domicilio(dom, u)
        items = _setup_ruta_y_publicar([ini_den.id])
        item_den = items[0]
        assert item_den.actuacion_id is not None

        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "rubro_nombre": rub_verd_nombre,
                "acta_inspeccion_num": _unique_num(),
            }
        )
        with patch(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
        ):
            cerrar_completar_trabajo_por_ruta_item(
                ruta_item_id=item_den.id,
                payload=payload,
                ejecutado_por_user_id=u.id,
            )

        db.session.expunge_all()
        act_db = (
            Actuaciones.query.filter_by(id=item_den.actuacion_id)
            .options(joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro))
            .first()
        )
        item_db = db.session.get(RutaItem, item_den.id)
        ini_db = db.session.get(IniciadorRuta, ini_den.id)
        assert act_db is not None and item_db is not None and ini_db is not None
        assert item_db.estado_ejecucion == "REALIZADO"

        row = actuacion_to_grid_row(act_db, iniciador_desde_ruta=ini_db)
        assert row["rubro_nombre"] == rub_verd_nombre
        assert row["rubro_nombre"] != rub_a_nombre
        assert row["rubro_nombre"] != rub_b_nombre
    finally:
        db.session.rollback()
