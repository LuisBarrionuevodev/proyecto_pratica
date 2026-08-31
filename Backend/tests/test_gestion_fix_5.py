"""GESTIÓN-FIX.5 — historial inmutable de intentos + reset oficio al reencolar."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_detalle,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import CorregirCierreOficioIn
from app.domains.actuaciones.services.actuacion_reencolado_service import (
    actuacion_bloqueada_por_intento_posterior,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.corregir_cierre_oficio_service import corregir_cierre_oficio
from app.domains.actuaciones.services.list_service import listar_actuaciones_con_filtros
from app.domains.actuaciones.schemas.list_filters import ActuacionesListFilters
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import Actuaciones, CatalogContraproducencia, IniciadorRuta, Inspector, RutaItem, RutaTrabajo

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
from tests.test_completar_trabajo_subtipo_oficio_pr10_2 import (
    _cerrar_segundo_intento_realizado,
    _republicar_iniciador_pendiente,
)


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _ensure_catalog_contraproducencia(nombre: str) -> None:
    if not CatalogContraproducencia.query.filter_by(nombre=nombre).first():
        db.session.add(CatalogContraproducencia(nombre=nombre))
        db.session.commit()


def _dos_inspector_ids() -> list[int]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores para publicar ruta")
    return [int(rows[0].id), int(rows[1].id)]


def test_oficio_local_cerrado_resetea_iniciador_generico(app_ctx) -> None:
    """Primer intento Verificar + LOCAL CERRADO → act histórica + ini REINSPECCION_OFICIO."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(u.id)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "VERIFICAR E INFORMAR"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, act.id)
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert act_db is not None
    assert str(act_db.tipo) == "VERIFICAR E INFORMAR"
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "REINSPECCION_OFICIO"
    assert ini_db.estado_iniciador == "PENDIENTE"


def test_oficio_republicar_crea_actuacion_nueva_sin_mutar_historica(app_ctx) -> None:
    """Republicación tras contra: act1 inmutable, item2 con act2 distinta."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act1, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(u.id)
    act1_id = int(act1.id)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "VERIFICAR E INFORMAR"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    snap = db.session.get(Actuaciones, act1_id)
    assert snap is not None
    hist_fecha, hist_tipo, hist_contra = snap.fecha, str(snap.tipo), snap.contraproducencia

    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    item2 = _republicar_iniciador_pendiente(ini_db, user_id, fecha=date(2026, 7, 1))

    act1_after = db.session.get(Actuaciones, act1_id)
    assert act1_after is not None
    assert act1_after.fecha == hist_fecha
    assert str(act1_after.tipo) == hist_tipo
    assert act1_after.contraproducencia == hist_contra
    assert item2.actuacion_id is not None
    assert int(item2.actuacion_id) != act1_id


def test_oficio_detalle_completar_trabajo_generico_tras_reencolado(app_ctx) -> None:
    """Nuevo RutaItem expone tipo_iniciador REINSPECCION_OFICIO en detalle Completar."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, _act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(u.id)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "VERIFICAR E INFORMAR"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini.id)
    item2 = _republicar_iniciador_pendiente(ini_db, user_id)
    item2_db = (
        RutaItem.query.filter(RutaItem.id == item2.id)
        .options()
        .first()
    )
    assert item2_db is not None
    detalle = ruta_item_completar_trabajo_detalle(
        item2_db,
        inspectores_grupo=[],
        tipo_actuacion_esperado=None,
    )
    assert detalle["row"]["tipo_iniciador"] == "REINSPECCION_OFICIO"


def test_oficio_bloqueo_edicion_tras_segundo_intento(app_ctx) -> None:
    """act1 editable antes del 2.º cierre; bloqueada después; act2 editable."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act1, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(u.id)
    act1_id = int(act1.id)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "VERIFICAR E INFORMAR"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    bloq_antes, _ = actuacion_bloqueada_por_intento_posterior(act1_id)
    assert bloq_antes is False

    ini_db = db.session.get(IniciadorRuta, ini.id)
    item2 = _republicar_iniciador_pendiente(ini_db, user_id)
    bloq_tras_replan, _ = actuacion_bloqueada_por_intento_posterior(act1_id)
    assert bloq_tras_replan is False

    act2 = _cerrar_segundo_intento_realizado(item2, user_id, tipo_iniciador="REINSPECCION_OFICIO")
    assert int(act2.id) != act1_id

    bloq_despues, motivo = actuacion_bloqueada_por_intento_posterior(act1_id)
    assert bloq_despues is True
    assert motivo is not None
    bloq_act2, _ = actuacion_bloqueada_por_intento_posterior(int(act2.id))
    assert bloq_act2 is False

    row1 = actuacion_to_grid_row(db.session.get(Actuaciones, act1_id))
    row2 = actuacion_to_grid_row(act2)
    assert row1.get("actuacion_editable") is False
    assert row2.get("actuacion_editable") is True


def test_oficio_put_y_corregir_bloquean_actuacion_historica(app_ctx) -> None:
    """PUT y corregir-cierre-oficio rechazan act1 cuando existe act2."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act1, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(u.id)
    act1_id = int(act1.id)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "VERIFICAR E INFORMAR"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini.id)
    item2 = _republicar_iniciador_pendiente(ini_db, user_id)
    _cerrar_segundo_intento_realizado(item2, user_id, tipo_iniciador="REINSPECCION_OFICIO")

    with pytest.raises(ValueError, match="intento posterior"):
        actualizar_actuacion(act1_id, {"nombre_local": "bloqueado"})

    with pytest.raises(ValueError, match="intento posterior"):
        corregir_cierre_oficio(
            act1_id,
            CorregirCierreOficioIn.model_validate(
                {"tipo_actuacion": "VERIFICAR E INFORMAR", "contraproducencia": "LOCAL CERRADO"}
            ),
        )


def test_oficio_ambas_actuaciones_en_listado(app_ctx) -> None:
    """GET listado incluye act1 (con contra) y act2 tras segundo intento."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act1, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(u.id)
    act1_id = int(act1.id)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "VERIFICAR E INFORMAR"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini.id)
    item2 = _republicar_iniciador_pendiente(ini_db, user_id, fecha=date(2026, 8, 1))
    act2 = _cerrar_segundo_intento_realizado(item2, user_id, tipo_iniciador="REINSPECCION_OFICIO")

    result = listar_actuaciones_con_filtros(
        ActuacionesListFilters.model_validate(
            {"desde": date(2020, 1, 1), "hasta": date(2030, 12, 31), "page_size": 500}
        )
    )
    ids = {int(a.id) for a in result["items"]}
    assert act1_id in ids
    assert int(act2.id) in ids
    act1_row = next(a for a in result["items"] if int(a.id) == act1_id)
    assert act1_row.contraproducencia == "LOCAL CERRADO"


def test_oficio_no_cumple_sin_contra_no_resetea_generico(app_ctx) -> None:
    """NO_CUMPLE con visita realizada mantiene iniciador promovido (sin reset FIX.5)."""
    item, _act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    user_id = int(u.id)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "RATIFICACION DE CLAUSURA",
                "resultado_cumplimiento_oficio": "NO_CUMPLE",
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "RATIFICACION_CLAUSURA_OFICIO"
    assert ini_db.estado_iniciador == "PENDIENTE"


def _republicar_iniciador_generico(ini: IniciadorRuta, user_id: int, fecha: date) -> RutaItem:
    """Republica un iniciador PENDIENTE en ruta nueva (helper transversal)."""
    ruta = RutaTrabajo(
        fecha=fecha,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        created_by_user_id=user_id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre=f"G_{uuid4().hex[:6]}", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=_dos_inspector_ids(),
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini.id],
    )
    item = items[0]
    set_orden_trabajo_on_item(
        ruta_id=ruta.id,
        item_id=item.id,
        numero_orden_trabajo=_unique_num(),
    )
    db.session.commit()
    ruta_id = int(ruta.id)
    publicar_ruta_trabajo(ruta_id=ruta_id)
    db.session.expunge_all()
    refreshed = RutaItem.query.filter(RutaItem.ruta_trabajo_id == ruta_id).first()
    assert refreshed is not None
    return refreshed


def test_relevamiento_dos_actuaciones_tras_reencolado(app_ctx) -> None:
    """Relevamiento: act1 histórica + act2 nueva al replanificar."""
    from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada

    suf = uuid4().hex[:8]
    item_id, act1_id, ini_id, user_id, _, _ = _mk_relevamiento_en_ruta_publicada(suf)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    item2 = _republicar_iniciador_generico(ini_db, user_id, date(2098, 3, 10))
    assert item2.actuacion_id is not None
    assert int(item2.actuacion_id) != int(act1_id)


def test_reinspeccion_notificacion_dos_actuaciones_tras_reencolado(app_ctx) -> None:
    """Reinspección notificación: act1 != act2; ini.tipo sin cambiar."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    from tests.test_notificacion_oper_ruta_3 import _mk_iniciador_reinspeccion, _mk_notif_act, _mk_user
    from tests.test_oper_ruta_6f_replanificacion import uniq_ruta_numero

    u = _mk_user()
    user_id = int(u.id)
    act, _ = _mk_notif_act(fecha=date(2026, 11, 1))
    ini = _mk_iniciador_reinspeccion(act, u)
    ruta = RutaTrabajo(
        fecha=date(2026, 11, 5),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=uniq_ruta_numero(),
        created_by_user_id=user_id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G1", estado="ACTIVO")
    replace_grupo_inspectores(ruta_id=ruta.id, grupo_id=grupo.id, inspector_ids=_dos_inspector_ids())
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini.id],
    )
    item = items[0]
    set_orden_trabajo_on_item(
        ruta_id=ruta.id,
        item_id=item.id,
        numero_orden_trabajo=_unique_num(),
    )
    db.session.commit()
    ini_id = int(ini.id)
    publicar_ruta_trabajo(ruta_id=int(ruta.id))
    db.session.expunge_all()
    item_db = RutaItem.query.filter(RutaItem.iniciador_ruta_id == ini_id).order_by(RutaItem.id.desc()).first()
    assert item_db is not None
    act1_id = int(item_db.actuacion_id or 0)
    assert act1_id
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_db.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "REINSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    assert ini_db.estado_iniciador == "PENDIENTE"
    assert ini_db.tipo_iniciador == "REINSPECCION_NOTIFICACION"
    item2 = _republicar_iniciador_generico(ini_db, user_id, date(2026, 11, 20))
    assert int(item2.actuacion_id or 0) != act1_id
