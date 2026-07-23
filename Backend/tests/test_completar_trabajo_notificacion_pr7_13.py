"""
PR7.13 — Notificación alineada a Comprobación: domicilio real/legal de actuación,
sin domicilios parciales, nomenclatura en canal Actuaciones, iniciador derivado alineado.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.mappers.completar_trabajo_cierre_mapper import (
    map_completar_trabajo_cierre_to_aplicar_payload,
)
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_pendiente_expediente_row,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.actuaciones.services.update_service import aplicar_payload_actuacion
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import on_domicilio_changed
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
    Notificacion,
    OrdenTrabajo,
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
        pytest.skip("Requiere migración PR7.2 aplicada en BD")


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


def _crear_relevamiento_san_juan_maipu(*, rubro: Rubro, angulo: str, fantasia: str) -> Relevamiento:
    ins = _inspector()
    return crear_relevamiento_desde_payload(
        {
            "fecha": "2026-07-15",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": _uniq("SanJuanMaipu"), "numero": "y Maipu", "numero_tipo": "ESQUINA"},
            "rubro_nombre": rubro.nombre,
            "nombre_fantasia": fantasia,
            "angulo_esquina": angulo,
        }
    )


def _setup_ruta_publicada(ini: IniciadorRuta) -> RutaItem:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u is None:
        pytest.skip("Se requiere usuario activo")
    ins1, ins2 = _dos_inspectores()
    ruta = RutaTrabajo(
        fecha=date(2026, 7, 15),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo PR713", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini.id],
    )
    for item in items:
        set_orden_trabajo_on_item(
            ruta_id=ruta.id,
            item_id=item.id,
            numero_orden_trabajo=_unique_num(),
        )
    publicar_ruta_trabajo(ruta_id=ruta.id)
    item = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    assert item is not None
    return item


def _cerrar_item(item_id: int, payload: dict) -> None:
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed",
        wraps=on_domicilio_changed,
    ) as geo_hook:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(payload),
            ejecutado_por_user_id=u.id,
        )
        assert geo_hook.call_count == 0


def test_pr713_mapper_no_incluye_domicilio_parcial_solo_calle() -> None:
    """Si el cierre trae calle + numero_tipo sin número, no debe mandar domicilio parcial."""
    act = Actuaciones()
    act.domicilio = Domicilio(calle="San Juan", numero="y Maipu", numero_tipo="ESQUINA")
    ini = IniciadorRuta()
    row = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "calle": "Mendoza",
            "numero_tipo": "NUMERO",
            "rubro_nombre": "Panadería",
        }
    )
    payload = map_completar_trabajo_cierre_to_aplicar_payload(row, act=act, ini=ini)
    assert "domicilio" not in payload


def test_pr713_completar_notificacion_mendoza_500_y_iniciador_derivado(
    app_ctx, require_pr72_migration
) -> None:
    """ESQUINA→Mendoza 500 + Notificación: actuación, presenter e iniciador usan domicilio completo."""
    try:
        rub = Rubro(nombre=_uniq("Notif713"))
        db.session.add(rub)
        db.session.flush()
        rel = _crear_relevamiento_san_juan_maipu(rubro=rub, angulo="NE", fantasia="Local713")
        dom_esquina_id = rel.domicilio_id
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
        assert ini
        item = _setup_ruta_publicada(ini)

        motivo = Motivo.query.first()
        if motivo is None:
            pytest.skip("Se requiere al menos un motivo en catálogo")
        acta_notif = _unique_num()
        _cerrar_item(
            item.id,
            {
                "calle": "Mendoza",
                "numero": "500",
                "numero_tipo": "NUMERO",
                "rubro_nombre": rub.nombre,
                "acta_notificacion_num": acta_notif,
                "notificacion_motivo_1": motivo.nombre,
            },
        )

        act_id = int(item.actuacion_id)
        db.session.expunge_all()
        act = (
            Actuaciones.query.filter_by(id=act_id)
            .options(joinedload(Actuaciones.domicilio), joinedload(Actuaciones.notificacion))
            .first()
        )
        assert act and act.domicilio and act.notificacion_id
        assert act.domicilio.calle == "Mendoza"
        assert act.domicilio.numero == "500"
        assert act.domicilio.numero_tipo == "NUMERO"
        assert act.domicilio_id != dom_esquina_id

        row = actuacion_to_pendiente_expediente_row(
            act, expediente_list_channel="notificacion"
        )
        assert row["calle"] == "Mendoza"
        assert row["numero"] == "500"
        assert row["numero_mostrar"] == "500"

        noti = db.session.get(Notificacion, act.notificacion_id)
        assert noti is not None
        noti.fecha_vencimiento = date.today() - timedelta(days=1)
        db.session.add(noti)
        db.session.commit()

        sync_iniciadores_reinspeccion_notificacion()

        ini_der = (
            IniciadorRuta.query.filter(
                IniciadorRuta.notificacion_id == noti.id,
                IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
                IniciadorRuta.deleted_at.is_(None),
            )
            .first()
        )
        assert ini_der is not None
        assert ini_der.domicilio_id == act.domicilio_id
        dom_der = db.session.get(Domicilio, ini_der.domicilio_id)
        assert dom_der is not None
        assert dom_der.calle == "Mendoza"
        assert dom_der.numero == "500"
        assert "San Juan" not in (dom_der.calle or "")

        parciales = (
            Domicilio.query.filter(
                Domicilio.calle == "Mendoza",
                Domicilio.numero.is_(None),
                Domicilio.deleted_at.is_(None),
            )
            .count()
        )
        assert parciales == 0
    finally:
        db.session.rollback()


def test_pr713_comprobacion_sigue_mendoza_500(app_ctx, require_pr72_migration) -> None:
    """Regresión: comprobación en la misma visita conserva Mendoza 500."""
    try:
        rub = Rubro(nombre=_uniq("Comp713"))
        db.session.add(rub)
        db.session.flush()
        rel = _crear_relevamiento_san_juan_maipu(rubro=rub, angulo="SO", fantasia="Kiosco713")
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
        assert ini
        item = _setup_ruta_publicada(ini)

        _cerrar_item(
            item.id,
            {
                "calle": "Mendoza",
                "numero": "500",
                "numero_tipo": "NUMERO",
                "rubro_nombre": rub.nombre,
                "acta_comprobacion_num": _unique_num(),
                "comprobacion_motivo": "reinspeccion pr713",
            },
        )

        act = (
            Actuaciones.query.filter_by(id=int(item.actuacion_id))
            .options(joinedload(Actuaciones.domicilio))
            .first()
        )
        assert act and act.domicilio
        assert act.domicilio.calle == "Mendoza"
        assert act.domicilio.numero == "500"
    finally:
        db.session.rollback()


def test_pr713_update_actuacion_con_notificacion_sin_uso_permite_cambio_domicilio(app_ctx) -> None:
    """PR7.15e: notificación asociada sin uso posterior permite mutar domicilio desde CRUD."""
    try:
        contrib = Contribuyente(apellido="Norm", nombre="Test", documento=_unique_num())
        db.session.add(contrib)
        db.session.flush()
        dom = Domicilio(calle="mendoza", numero="500", numero_tipo="NUMERO", contribuyente_id=contrib.id)
        db.session.add(dom)
        db.session.flush()
        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=7)
        db.session.add(ot)
        db.session.flush()
        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=7)
        db.session.add(noti)
        db.session.flush()
        act = Actuaciones(
            fecha=date(2026, 7, 15),
            mes=7,
            anio=2026,
            orden_trabajo_id=ot.id,
            domicilio_id=dom.id,
            notificacion_id=noti.id,
            tipo="INSPECCION",
        )
        db.session.add(act)
        db.session.flush()

        rub = Rubro.query.first()
        if rub is None:
            rub = Rubro(nombre=_uniq("Rub713"))
            db.session.add(rub)
            db.session.flush()

        from app.domains.actuaciones.services.update_service import aplicar_payload_actuacion

        aplicar_payload_actuacion(
            act,
            {
                "domicilio": {
                    "calle": "San Juan",
                    "numero": "1000",
                    "numero_tipo": "NUMERO",
                },
                "contribuyente": {
                    "doc_nro": contrib.documento,
                    "apellido": contrib.apellido,
                    "nombre": contrib.nombre,
                },
                "rubro_nombre": rub.nombre,
            },
            ejecutar_resolver_previas=False,
        )
        db.session.flush()
        dom_db = Domicilio.query.get(act.domicilio_id)
        assert dom_db is not None
        assert dom_db.calle == "San Juan"
        assert dom_db.numero == "1000"
    finally:
        db.session.rollback()
