"""
PR7.11 — Flujo completo multi-establecimiento: Relevamiento → Iniciador → Ruta → Completar.

Cubre ESQUINA multi-rubro, presenters de ruta, publicación y cierre con cambio de domicilio
legal/final sin alterar el relevamiento origen.
"""

from __future__ import annotations

import random
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.rutas_trabajo.presenters.ruta_presenters import (
    iniciador_pendiente_to_row,
    ruta_item_to_min_dict,
)
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import (
    Actuaciones,
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
    """
    Alta de dos relevamientos ESQUINA en el mismo domicilio con distinto establecimiento.

    Retorna (rel_a, rel_b, ini_a, ini_b, rub_a, rub_b, dom).
    """
    ins = _inspector()
    rub_a = Rubro(nombre=_uniq("CarnPr711"))
    rub_b = Rubro(nombre=_uniq("VerdPr711"))
    db.session.add_all([rub_a, rub_b])
    db.session.flush()

    calle = _uniq("SanMartinMaipu")
    rel_a = crear_relevamiento_desde_payload(
        _payload_esquina(
            calle=calle,
            rubro=rub_a.nombre,
            inspector=ins.nombre,
            fecha="2026-07-01",
            nombre_fantasia="El Toro",
            angulo_esquina="NE",
        )
    )
    rel_b = crear_relevamiento_desde_payload(
        _payload_esquina(
            calle=calle,
            rubro=rub_b.nombre,
            inspector=ins.nombre,
            fecha="2026-07-02",
            nombre_fantasia="La Huerta",
            angulo_esquina="SO",
        )
    )

    ini_a = (
        IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel_a.id,
            IniciadorRuta.deleted_at.is_(None),
        )
        .first()
    )
    ini_b = (
        IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel_b.id,
            IniciadorRuta.deleted_at.is_(None),
        )
        .first()
    )
    assert ini_a is not None and ini_b is not None
    dom = db.session.get(Domicilio, rel_a.domicilio_id)
    assert dom is not None
    return rel_a, rel_b, ini_a, ini_b, rub_a, rub_b, dom


def _setup_ruta_borrador_con_iniciadores(
    ini_ids: list[int],
    *,
    fecha: date | None = None,
) -> tuple[RutaTrabajo, int, list[RutaItem]]:
    """Crea ruta BORRADOR, grupo con 2 inspectores, asigna iniciadores y OT por ítem."""
    u = User.query.filter(User.is_active.is_(True)).first()
    if u is None:
        pytest.skip("Se requiere usuario activo")
    ins1, ins2 = _dos_inspectores()
    f = fecha or date(2026, 7, 11)
    ruta = RutaTrabajo(
        fecha=f,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()

    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo PR711", estado="ACTIVO")
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
    db.session.expire_all()
    items_refreshed = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.deleted_at.is_(None),
        )
        .options(
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.relevamiento).joinedload(
                Relevamiento.rubro
            ),
        )
        .order_by(RutaItem.id.asc())
        .all()
    )
    return ruta, grupo.id, items_refreshed


def test_pr711_esquina_dos_relevamientos_dos_iniciadores(app_ctx, require_pr72_migration) -> None:
    try:
        rel_a, rel_b, ini_a, ini_b, rub_a, rub_b, dom = _crear_esquina_multi_establecimiento()

        assert rel_a.id != rel_b.id
        assert rel_a.domicilio_id == rel_b.domicilio_id == dom.id
        assert ini_a.id != ini_b.id
        assert ini_a.relevamiento_id == rel_a.id
        assert ini_b.relevamiento_id == rel_b.id
        assert ini_a.domicilio_id == ini_b.domicilio_id == dom.id

        # domicilio.rubro_id no es fuente operativa en ESQUINA multi-rubro (guard PR7.3).
        assert dom.rubro_id is not None

        assert rel_a.rubro_id == rub_a.id
        assert rel_b.rubro_id == rub_b.id
        assert rel_a.nombre_fantasia == "El Toro"
        assert rel_b.nombre_fantasia == "La Huerta"
    finally:
        db.session.rollback()


def test_pr711_presenter_pool_discriminadores_aunque_domicilio_rubro_distinto(
    app_ctx, require_pr72_migration
) -> None:
    try:
        rel_a, rel_b, ini_a, ini_b, rub_a, rub_b, _dom = _crear_esquina_multi_establecimiento()

        row_a = iniciador_pendiente_to_row(ini_a)
        row_b = iniciador_pendiente_to_row(ini_b)

        assert row_a["rubro_nombre"] == rub_a.nombre
        assert row_a["nombre_fantasia"] == "El Toro"
        assert row_a["angulo_esquina"] == "NE"

        assert row_b["rubro_nombre"] == rub_b.nombre
        assert row_b["nombre_fantasia"] == "La Huerta"
        assert row_b["angulo_esquina"] == "SO"

        assert row_a["rubro_nombre"] != row_b["rubro_nombre"]
    finally:
        db.session.rollback()


def test_pr711_ruta_publicar_y_presenter_conservan_origen(app_ctx, require_pr72_migration) -> None:
    try:
        rel_a, rel_b, ini_a, ini_b, rub_a, rub_b, dom = _crear_esquina_multi_establecimiento()
        ruta, _gid, items = _setup_ruta_borrador_con_iniciadores([ini_a.id, ini_b.id])

        publicar_ruta_trabajo(ruta_id=ruta.id)

        items_db = (
            RutaItem.query.filter(
                RutaItem.ruta_trabajo_id == ruta.id,
                RutaItem.deleted_at.is_(None),
            )
            .options(
                joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.relevamiento).joinedload(
                    Relevamiento.rubro
                ),
                joinedload(RutaItem.actuacion),
            )
            .order_by(RutaItem.id.asc())
            .all()
        )
        assert len(items_db) == 2

        by_ini = {it.iniciador_ruta_id: it for it in items_db}
        item_a = by_ini[ini_a.id]
        item_b = by_ini[ini_b.id]

        assert item_a.actuacion_id is not None
        assert item_b.actuacion_id is not None
        assert item_a.iniciador_ruta.relevamiento_id == rel_a.id
        assert item_b.iniciador_ruta.relevamiento_id == rel_b.id
        assert item_a.actuacion.domicilio_id == dom.id
        assert item_b.actuacion.domicilio_id == dom.id

        pres_a = ruta_item_to_min_dict(item_a)
        pres_b = ruta_item_to_min_dict(item_b)
        assert pres_a["rubro_nombre"] == rub_a.nombre
        assert pres_a["nombre_fantasia"] == "El Toro"
        assert pres_a["angulo_esquina"] == "NE"
        assert pres_b["rubro_nombre"] == rub_b.nombre
        assert pres_b["nombre_fantasia"] == "La Huerta"
        assert pres_b["angulo_esquina"] == "SO"
    finally:
        db.session.rollback()


def test_pr711_completar_trabajo_cambia_domicilio_relevamiento_intacto(
    app_ctx, require_pr72_migration
) -> None:
    try:
        rel_a, _rel_b, ini_a, _ini_b, rub_a, _rub_b, dom_esquina = _crear_esquina_multi_establecimiento()
        ruta, _gid, items = _setup_ruta_borrador_con_iniciadores([ini_a.id])
        publicar_ruta_trabajo(ruta_id=ruta.id)

        item = (
            RutaItem.query.filter(
                RutaItem.ruta_trabajo_id == ruta.id,
                RutaItem.iniciador_ruta_id == ini_a.id,
            )
            .first()
        )
        assert item is not None
        u = User.query.filter(User.is_active.is_(True)).first()
        assert u is not None

        calle_final = _uniq("Maipu")
        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "calle": calle_final,
                "numero": "500",
                "numero_tipo": "NUMERO",
                "rubro_nombre": rub_a.nombre,
            }
        )
        snap_rel_dom_id = rel_a.domicilio_id
        snap_rel_rubro = rel_a.rubro_id
        snap_fantasia = rel_a.nombre_fantasia
        snap_angulo = rel_a.angulo_esquina

        with patch(
            "app.domains.actuaciones.services.completar_trabajo_cierre_service.on_domicilio_changed"
        ):
            cerrar_completar_trabajo_por_ruta_item(
                ruta_item_id=item.id,
                payload=payload,
                ejecutado_por_user_id=u.id,
            )

        db.session.expunge_all()
        rel_db = db.session.get(Relevamiento, rel_a.id)
        act_db = (
            Actuaciones.query.filter_by(id=item.actuacion_id)
            .options(joinedload(Actuaciones.domicilio))
            .first()
        )
        ini_db = db.session.get(IniciadorRuta, ini_a.id)

        assert rel_db is not None and act_db is not None and ini_db is not None
        assert rel_db.domicilio_id == snap_rel_dom_id
        assert rel_db.rubro_id == snap_rel_rubro
        assert rel_db.nombre_fantasia == snap_fantasia
        assert rel_db.angulo_esquina == snap_angulo

        assert act_db.domicilio is not None
        assert act_db.domicilio.numero == "500"
        assert calle_final in (act_db.domicilio.calle or "")
        assert ini_db.domicilio_id == act_db.domicilio_id

        assert "nombre_fantasia" not in payload.model_dump(exclude_none=True)
        assert "angulo_esquina" not in payload.model_dump(exclude_none=True)
    finally:
        db.session.rollback()


def test_pr711_numero_recambio_rubro_distingue_y_duplicado_bloquea(
    app_ctx, require_pr72_migration
) -> None:
    ins = _inspector()
    rub_carn = Rubro(nombre=_uniq("CarnNum711"))
    rub_poll = Rubro(nombre=_uniq("PollNum711"))
    db.session.add_all([rub_carn, rub_poll])
    db.session.flush()
    calle = _uniq("SanMartin234")
    try:
        p1 = {
            "fecha": "2026-07-05",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": calle, "numero": "234"},
            "rubro_nombre": rub_carn.nombre,
        }
        r1 = crear_relevamiento_desde_payload(p1)
        r2 = crear_relevamiento_desde_payload(
            {**p1, "fecha": "2026-07-06", "rubro_nombre": rub_poll.nombre}
        )
        assert r1.domicilio_id == r2.domicilio_id

        ini1 = IniciadorRuta.query.filter_by(relevamiento_id=r1.id, deleted_at=None).first()
        ini2 = IniciadorRuta.query.filter_by(relevamiento_id=r2.id, deleted_at=None).first()
        assert ini1 is not None and ini2 is not None

        row1 = iniciador_pendiente_to_row(ini1)
        row2 = iniciador_pendiente_to_row(ini2)
        assert row1["rubro_nombre"] == rub_carn.nombre
        assert row2["rubro_nombre"] == rub_poll.nombre

        with pytest.raises(ValueError, match="establecimiento en el mismo domicilio"):
            crear_relevamiento_desde_payload({**p1, "fecha": "2026-07-07"})
    finally:
        db.session.rollback()
