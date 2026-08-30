"""GESTIÓN-FIX.4 — Relevamiento: titular persistido visible; PUT contrib-only."""

from __future__ import annotations

import random
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.actas_quitar_canal_actas_service import quitar_acta_canal_actas
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.rutas_trabajo.utils.rubro_operativo import titular_operativo_visible_para_iniciador
from app.models import Actuaciones, Domicilio, IniciadorRuta, Inspector

from tests.test_gestion_fix_3 import _ensure_catalog_contraproducencia
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_relevamiento_no_permite_inspeccion_presenter_muestra_contrib(app_ctx) -> None:
    """NO PERMITE INSPECCIÓN + contrib informado → presenter devuelve titular."""
    _ensure_catalog_contraproducencia("NO PERMITE INSPECCION")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _rb, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "contraproducencia": "NO PERMITE INSPECCION",
                "tipo_actuacion": "INSPECCION",
                "acta_comprobacion_num": f"{random.randint(100000, 999999):06d}",
                "comprobacion_motivo": "Falta de Higiene",
                "contrib_apellido": "Pérez",
                "contrib_nombre": "Juan",
                "doc_nro": "30000000",
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act = db.session.get(Actuaciones, act_id)
    ini = db.session.get(IniciadorRuta, ini_id)
    assert act is not None and ini is not None
    assert act.domicilio is not None and act.domicilio.contribuyente_id is not None
    assert titular_operativo_visible_para_iniciador(ini, act=act) is True

    row = actuacion_to_grid_row(act, iniciador_desde_ruta=ini)
    assert row.get("contrib_apellido") == "Pérez"
    assert row.get("contrib_nombre") == "Juan"
    assert str(row.get("doc_nro") or "").replace(".", "") == "30000000"


def test_relevamiento_realizado_a_contra_titular_sigue_visible(app_ctx) -> None:
    """REALIZADO → CONTRAPRODUCENCIA con contrib previamente informado → titular visible."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _rb, dom_id = _mk_relevamiento_en_ruta_publicada(suf)

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    insp1 = inspectores[0].nombre
    insp2 = inspectores[1].nombre

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
                "contrib_apellido": "Titular",
                "contrib_nombre": "Visible",
                "doc_nro": "30111222",
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"
    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    calle = dom.calle
    numero = dom.numero
    rubro_nombre = dom.rubro.nombre if dom.rubro else "Bar"

    quitar_acta_canal_actas(act_id, "INSPECCION")
    db.session.expunge_all()

    row_contra = ActuacionGridRowIn.model_validate(
        {
            "id": act_id,
            "orden_trabajo_numero": ot_num,
            "fecha_actuacion": fecha,
            "tipo_actuacion": "INSPECCION",
            "inspector1": insp1,
            "inspector2": insp2,
            "calle": calle,
            "numero": numero,
            "rubro_nombre": rubro_nombre,
            "doc_nro": "30111222",
            "contrib_apellido": "Titular",
            "contrib_nombre": "Visible",
            "contraproducencia": "LOCAL CERRADO",
        }
    )
    actualizar_actuacion(act_id, map_actuacion_row(row_contra))
    db.session.expunge_all()

    act = db.session.get(Actuaciones, act_id)
    ini = db.session.get(IniciadorRuta, ini_id)
    assert act is not None and ini is not None
    row = actuacion_to_grid_row(act, iniciador_desde_ruta=ini)
    assert row.get("contrib_apellido") == "Titular"
    assert row.get("contrib_nombre") == "Visible"
    assert str(row.get("doc_nro") or "").replace(".", "") == "30111222"


def test_put_solo_contribuyente_sin_cambio_domicilio(app_ctx) -> None:
    """PUT solo contribuyente (sin calle/número) persiste y GET lo devuelve."""
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _rb, dom_id = _mk_relevamiento_en_ruta_publicada(suf)

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    insp1 = inspectores[0].nombre
    insp2 = inspectores[1].nombre

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"
    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    calle = dom.calle
    numero = dom.numero

    row_in = ActuacionGridRowIn.model_validate(
        {
            "id": act_id,
            "orden_trabajo_numero": ot_num,
            "fecha_actuacion": fecha,
            "tipo_actuacion": "INSPECCION",
            "inspector1": insp1,
            "inspector2": insp2,
            "doc_nro": "39998877",
            "contrib_apellido": "García",
            "contrib_nombre": "Ana",
            "razon_social": "Panadería García SRL",
        }
    )
    actualizar_actuacion(act_id, map_actuacion_row(row_in))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert act_db is not None and ini_db is not None
    assert act_db.domicilio is not None
    assert act_db.domicilio.calle == calle
    assert act_db.domicilio.numero == numero
    c = act_db.domicilio.contribuyente
    assert c is not None
    assert c.apellido == "García"
    assert c.nombre == "Ana"
    assert str(c.documento).replace(".", "") == "39998877"

    grid = actuacion_to_grid_row(act_db, iniciador_desde_ruta=ini_db)
    assert grid.get("contrib_apellido") == "García"
    assert grid.get("contrib_nombre") == "Ana"
    assert grid.get("razon_social") == "Panadería García SRL"
    assert str(grid.get("doc_nro") or "").replace(".", "") == "39998877"


def test_relevamiento_sin_contrib_no_inventa_titular(app_ctx) -> None:
    """Sin contribuyente informado en visita no realizada → no expone titular heredado."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _rb, dom_id = _mk_relevamiento_en_ruta_publicada(suf)

    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    dom.contribuyente_id = None
    db.session.commit()

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act = db.session.get(Actuaciones, act_id)
    ini = db.session.get(IniciadorRuta, ini_id)
    assert act is not None and ini is not None
    assert act.domicilio is not None
    assert act.domicilio.contribuyente_id is None

    row = actuacion_to_grid_row(act, iniciador_desde_ruta=ini)
    assert row.get("contrib_apellido") in (None, "")
    assert row.get("contrib_nombre") in (None, "")
    assert row.get("doc_nro") in (None, "")
