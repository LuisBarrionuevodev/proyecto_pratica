"""GESTIÓN-FIX.10B.1 — REALIZADO → Editar → LOCAL CERRADO vincula EO como Completar Trabajo."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.establecimientos.services.historial_actuaciones_establecimiento_service import (
    list_actuaciones_por_establecimiento_operativo,
)
from app.domains.establecimientos.services.resolve_establecimiento_por_domicilio import (
    resolve_establecimiento_por_domicilio,
)
from app.models import (
    Actuaciones,
    CatalogContraproducencia,
    Contribuyente,
    Domicilio,
    EstablecimientoOperativo,
    IniciadorRuta,
    Inspector,
    Rubro,
    RutaItem,
    User,
)

from tests.test_gestion_fix_3 import _fila_realizado_a_contra
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _ensure_catalog_contraproducencia(nombre: str) -> None:
    if not CatalogContraproducencia.query.filter_by(nombre=nombre).first():
        db.session.add(CatalogContraproducencia(nombre=nombre))
        db.session.commit()


def _dos_inspectores() -> tuple[str, str]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    return rows[0].nombre, rows[1].nombre


def _cerrar_realizado_con_acta(*, item_id: int, user_id: int, acta: str) -> None:
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": acta,
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()


def _put_realizado_a_local_cerrado(
    *,
    act_id: int,
    ot: str,
    fecha: str,
    insp1: str,
    insp2: str,
    actas_a_quitar: list[str] | None = None,
) -> None:
    row_dict = _fila_realizado_a_contra(
        act_id=act_id,
        ot=ot,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        include_domicilio=False,
    )
    if actas_a_quitar:
        row_dict["actas_a_quitar"] = actas_a_quitar
    row = ActuacionGridRowIn.model_validate(row_dict)
    actualizar_actuacion(act_id, map_actuacion_row(row))
    db.session.expunge_all()


def test_realizado_quitar_acta_local_cerrado_vincula_eo_canonico(app_ctx) -> None:
    """Caso principal: REALIZADO + acta → quitar → LOCAL CERRADO → EO canónico."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    act_realizado = db.session.get(Actuaciones, act_id)
    assert act_realizado is not None
    eo_directo = resolve_establecimiento_por_domicilio(int(dom_id), created_by_user_id=user_id)
    assert eo_directo is not None

    # Simula el gap del PUT previo: EO ausente pese a domicilio válido.
    act_realizado.establecimiento_operativo_id = None
    db.session.commit()
    db.session.expunge_all()

    _put_realizado_a_local_cerrado(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        actas_a_quitar=["INSPECCION"],
    )

    act_db = db.session.get(Actuaciones, act_id)
    item_db = db.session.get(RutaItem, item_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.establecimiento_operativo_id == eo_directo
    assert act_db.domicilio_id == dom_id
    assert act_db.inspeccion is None

    assert item_db is not None
    assert item_db.estado_ruta_item == "FINALIZADO"
    assert item_db.estado_ejecucion == "NO_REALIZADO"
    assert item_db.motivo_no_realizado == "LOCAL_CERRADO"

    assert ini_db is not None
    assert ini_db.estado_iniciador == "PENDIENTE"

    acts, total = list_actuaciones_por_establecimiento_operativo(
        int(act_db.establecimiento_operativo_id),
        page=1,
        page_size=50,
    )
    assert total >= 1
    assert act_id in {int(a.id) for a in acts}


def test_realizado_a_local_cerrado_reutiliza_eo_previo(app_ctx) -> None:
    """Si ya existía EO canónico, el PUT lo reutiliza (no duplica ficha)."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    eo_previo = resolve_establecimiento_por_domicilio(int(dom_id), created_by_user_id=user_id)
    assert eo_previo is not None
    act.establecimiento_operativo_id = eo_previo
    db.session.commit()

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    act_realizado = db.session.get(Actuaciones, act_id)
    assert act_realizado is not None
    act_realizado.establecimiento_operativo_id = None
    db.session.commit()
    db.session.expunge_all()

    count_antes = EstablecimientoOperativo.query.count()

    _put_realizado_a_local_cerrado(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        actas_a_quitar=["INSPECCION"],
    )

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.establecimiento_operativo_id == eo_previo
    assert EstablecimientoOperativo.query.count() == count_antes


def test_realizado_a_local_cerrado_cow_mismo_eo_canonico(app_ctx) -> None:
    """Dos forks COW misma identidad lógica → mismo EO tras PUT LOCAL CERRADO."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    dom_origen = db.session.get(Domicilio, dom_id)
    assert dom_origen is not None
    rub_b = Rubro(nombre=f"Rub10B1_{suf}")
    db.session.add(rub_b)
    db.session.flush()
    dom_fork = Domicilio(
        calle=dom_origen.calle,
        numero=dom_origen.numero,
        contribuyente_id=dom_origen.contribuyente_id,
        rubro_id=rub_b.id,
    )
    db.session.add(dom_fork)
    db.session.flush()

    eo_canon_fork = resolve_establecimiento_por_domicilio(int(dom_fork.id), created_by_user_id=user_id)
    assert eo_canon_fork is not None

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(
        item_id=item_id,
        user_id=user_id,
        acta=f"{random.randint(100000, 999999):06d}",
    )

    act_realizado = db.session.get(Actuaciones, act_id)
    assert act_realizado is not None
    act_realizado.establecimiento_operativo_id = None
    db.session.commit()
    db.session.expunge_all()

    _put_realizado_a_local_cerrado(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        actas_a_quitar=["INSPECCION"],
    )

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.establecimiento_operativo_id == eo_canon_fork


def test_local_cerrado_directo_sigue_vinculando_eo(app_ctx) -> None:
    """Regresión: LOCAL CERRADO directo en Completar Trabajo no se rompe."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.establecimiento_operativo_id is not None
    eo_esperado = resolve_establecimiento_por_domicilio(int(dom_id), created_by_user_id=user_id)
    assert act_db.establecimiento_operativo_id == eo_esperado

    acts, total = list_actuaciones_por_establecimiento_operativo(
        int(act_db.establecimiento_operativo_id),
        page=1,
        page_size=50,
    )
    assert total >= 1
    assert act_id in {int(a.id) for a in acts}
