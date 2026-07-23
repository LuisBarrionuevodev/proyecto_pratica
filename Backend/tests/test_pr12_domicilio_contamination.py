"""PR12 — Cargar Actuación / Relevamiento / Denuncia / Completar Trabajo sin contaminación por domicilio."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

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
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.denuncias.services.denuncias_service import crear_denuncia_con_iniciador
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
    Contribuyente,
    Domicilio,
    IniciadorRuta,
    Inspector,
    Motivo,
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


def _payload_esquina(*, calle: str, rubro: str, inspector: str, fecha: str):
    return {
        "fecha": fecha,
        "inspector_nombre": inspector,
        "domicilio": {"calle": calle, "numero": "y Maipu", "numero_tipo": "ESQUINA"},
        "rubro_nombre": rubro,
    }


def _setup_ruta_y_publicar(ini_ids: list[int]) -> list[RutaItem]:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u is None:
        pytest.skip("Se requiere usuario activo")
    ins1, ins2 = _dos_inspectores()
    ruta = RutaTrabajo(
        fecha=date(2026, 7, 21),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()

    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo PR12", estado="ACTIVO")
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
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.notificacion),
        )
        .order_by(RutaItem.id.asc())
        .all()
    )


def _cargar_actuacion_manual_esquina(
    *,
    calle: str,
    rubro: Rubro,
    contrib_doc: str,
    acta_notif: str,
) -> Actuaciones:
    ins = _inspector()
    motivo = Motivo.query.first()
    if motivo is None:
        pytest.skip("Se requiere motivo en catálogo")
    payload = {
        "fecha_actuacion": "21/07/2026",
        "orden_trabajo_numero": _unique_num(),
        "tipo_actuacion": "INSPECCION",
        "rubro_nombre": rubro.nombre,
        "contribuyente": {
            "doc_nro": contrib_doc,
            "apellido": "ManualPR12",
            "nombre": "Titular",
        },
        "domicilio": {"calle": calle, "numero": "y Maipu", "numero_tipo": "ESQUINA"},
        "inspectores": [ins.nombre],
        "acta_inspeccion_num": _unique_num(),
        "notificacion": {"acta_num": acta_notif, "motivos": [motivo.nombre]},
    }
    return crear_actuacion_desde_payload(payload)


def test_cargar_actuacion_no_contamina_relevamiento(app_ctx, require_pr72_migration) -> None:
    try:
        ins = _inspector()
        rub_pan = Rubro(nombre=_uniq("PanaderiaPR12"))
        rub_carn = Rubro(nombre=_uniq("CarniceriaPR12"))
        db.session.add_all([rub_pan, rub_carn])
        db.session.flush()

        calle = _uniq("SanMartinMaipuPR12")
        acta_notif = _unique_num()
        act_manual = _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub_pan,
            contrib_doc=str(random.randint(10_000_000, 99_999_999)),
            acta_notif=acta_notif,
        )
        dom_manual_id = act_manual.domicilio_id
        dom_manual = db.session.get(Domicilio, dom_manual_id)
        assert dom_manual is not None
        assert dom_manual.rubro_id == rub_pan.id

        rel = crear_relevamiento_desde_payload(
            _payload_esquina(
                calle=calle,
                rubro=rub_carn.nombre,
                inspector=ins.nombre,
                fecha="2026-07-22",
            )
        )
        ini = IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel.id,
            IniciadorRuta.deleted_at.is_(None),
        ).first()
        assert ini is not None

        items = _setup_ruta_y_publicar([ini.id])
        item = items[0]
        row = ruta_item_completar_trabajo_to_row(item)

        assert row["rubro_nombre"] == rub_carn.nombre
        assert row["rubro_nombre"] != rub_pan.nombre
        assert row.get("acta_notificacion_num") in (None, "")
        assert row.get("doc_nro") in (None, "")

        db.session.refresh(dom_manual)
        assert dom_manual.rubro_id == rub_pan.id
    finally:
        db.session.rollback()


def test_cargar_actuacion_no_contamina_denuncia(app_ctx, require_pr72_migration, monkeypatch) -> None:
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )

        rub_pan = Rubro(nombre=_uniq("PanDenPR12"))
        db.session.add(rub_pan)
        db.session.flush()

        calle = _uniq("DenunciaPR12")
        acta_notif = _unique_num()
        _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub_pan,
            contrib_doc=str(random.randint(10_000_000, 99_999_999)),
            acta_notif=acta_notif,
        )

        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 22),
            domicilio_id=None,
            calle=calle,
            numero="y Maipu",
            interseccion=None,
            motivo="PR12 denuncia misma esquina",
        )
        assert den.domicilio_id is not None

        items = _setup_ruta_y_publicar([ini.id])
        row = ruta_item_completar_trabajo_to_row(items[0])

        assert row.get("rubro_nombre") in (None, "")
        assert row.get("acta_notificacion_num") in (None, "")
        assert row.get("doc_nro") in (None, "")
    finally:
        db.session.rollback()


def test_relevamiento_no_pisa_rubro_actuacion_manual(app_ctx, require_pr72_migration) -> None:
    try:
        ins = _inspector()
        rub_pan = Rubro(nombre=_uniq("PanManualPR12"))
        rub_carn = Rubro(nombre=_uniq("CarnRelPR12"))
        db.session.add_all([rub_pan, rub_carn])
        db.session.flush()

        calle = _uniq("NoPisaPR12")
        act_manual = _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub_pan,
            contrib_doc=str(random.randint(10_000_000, 99_999_999)),
            acta_notif=_unique_num(),
        )
        act_manual_id = act_manual.id
        dom_manual_id = act_manual.domicilio_id
        rub_pan_id = rub_pan.id
        rub_pan_nombre = rub_pan.nombre

        crear_relevamiento_desde_payload(
            _payload_esquina(
                calle=calle,
                rubro=rub_carn.nombre,
                inspector=ins.nombre,
                fecha="2026-07-23",
            )
        )

        db.session.expunge_all()
        act_db = db.session.get(Actuaciones, act_manual_id)
        dom_db = db.session.get(Domicilio, dom_manual_id)
        assert act_db is not None and dom_db is not None
        assert dom_db.rubro_id == rub_pan_id

        ini_map = build_iniciador_ruta_por_actuacion_id([act_db.id])
        row = actuacion_to_grid_row(act_db, iniciador_desde_ruta=ini_map.get(act_db.id))
        assert row["rubro_nombre"] == rub_pan_nombre
    finally:
        db.session.rollback()


def test_completar_trabajo_no_hereda_actas_por_domicilio(app_ctx, require_pr72_migration) -> None:
    try:
        ins = _inspector()
        rub_pan = Rubro(nombre=_uniq("ActasPR12"))
        rub_carn = Rubro(nombre=_uniq("ActasRelPR12"))
        db.session.add_all([rub_pan, rub_carn])
        db.session.flush()

        calle = _uniq("ActasEsquinaPR12")
        acta_notif = _unique_num()
        _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub_pan,
            contrib_doc=str(random.randint(10_000_000, 99_999_999)),
            acta_notif=acta_notif,
        )

        rel = crear_relevamiento_desde_payload(
            _payload_esquina(
                calle=calle,
                rubro=rub_carn.nombre,
                inspector=ins.nombre,
                fecha="2026-07-24",
            )
        )
        ini = IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel.id,
            IniciadorRuta.deleted_at.is_(None),
        ).first()
        assert ini is not None

        items = _setup_ruta_y_publicar([ini.id])
        row = ruta_item_completar_trabajo_to_row(items[0])

        assert row.get("acta_notificacion_num") not in (acta_notif, f"{acta_notif}")
        assert row.get("acta_inspeccion_num") in (None, "")
        assert row.get("acta_comprobacion_num") in (None, "")
    finally:
        db.session.rollback()


def test_historial_dni_agrupa_sin_prefill_operativo(app_ctx, require_pr72_migration, monkeypatch) -> None:
    """Mismo DNI en dos actuaciones: historial puede agrupar; Completar Trabajo no prellena titular."""
    try:
        u = User.query.filter(User.is_active.is_(True)).first()
        if u is None:
            pytest.skip("Se requiere usuario activo")
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )

        doc = str(random.randint(10_000_000, 99_999_999))
        rub = Rubro(nombre=_uniq("HistPR12"))
        db.session.add(rub)
        db.session.flush()

        calle = _uniq("HistDniPR12")
        act_manual = _cargar_actuacion_manual_esquina(
            calle=calle,
            rubro=rub,
            contrib_doc=doc,
            acta_notif=_unique_num(),
        )

        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 25),
            domicilio_id=None,
            calle=calle,
            numero="y Maipu",
            interseccion=None,
            motivo="PR12 historial DNI",
        )
        assert den.domicilio_id is not None

        acts_mismo_doc = (
            Actuaciones.query.join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
            .join(Contribuyente, Domicilio.contribuyente_id == Contribuyente.id)
            .filter(Contribuyente.documento == doc)
            .count()
        )
        assert acts_mismo_doc >= 1

        items = _setup_ruta_y_publicar([ini.id])
        row = ruta_item_completar_trabajo_to_row(items[0])
        assert row.get("doc_nro") in (None, "")
        assert act_manual.domicilio.contribuyente.documento == doc
    finally:
        db.session.rollback()
