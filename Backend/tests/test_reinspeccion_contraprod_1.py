"""V1.1-REINSPECCION-CONTRAPROD.1 — NO_CUMPLE simple cierra; contra reencola."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_resumen_row,
    estado_recorrido_label,
)
from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_to_row,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.actuacion_reencolado_service import (
    iniciador_tiene_intentos_historicos_cerrados,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.oficio_editable_service import evaluar_editable_oficio
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    planificable_iniciadores_base_query,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.models import (
    Actuaciones,
    CatalogContraproducencia,
    CatalogTipoActuacion,
    IniciadorRuta,
    Inspector,
    Oficio,
    RutaItem,
    RutaTrabajo,
)

from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero
from tests.test_completar_trabajo_subtipo_oficio_pr10_2 import _republicar_iniciador_pendiente
from tests.test_reinspeccion_oficio_reencolado import _mk_reinspeccion_oficio_en_ruta_publicada


def _ensure_tipo(nombre: str) -> None:
    if CatalogTipoActuacion.query.filter_by(nombre=nombre).first() is None:
        db.session.add(CatalogTipoActuacion(nombre=nombre))
        db.session.commit()


def _ensure_catalog_contraproducencia(nombre: str) -> None:
    if not CatalogContraproducencia.query.filter_by(nombre=nombre).first():
        db.session.add(CatalogContraproducencia(nombre=nombre))
        db.session.commit()


@pytest.fixture(autouse=True)
def _seed_catalogos_contraprod(app_ctx) -> None:
    for nombre in (
        "INSPECCION",
        "REINSPECCION",
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
    ):
        _ensure_tipo(nombre)
    _ensure_catalog_contraproducencia("LOCAL CERRADO")


def _dos_inspector_ids() -> list[int]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores para publicar ruta")
    return [int(rows[0].id), int(rows[1].id)]


def _attach_inspectores(act: Actuaciones) -> list[int]:
    ids = _dos_inspector_ids()
    act.inspector = [db.session.get(Inspector, i) for i in ids]
    db.session.flush()
    return ids


def _cerrar(item_id: int, user_id: int, payload: dict) -> None:
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(payload),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()


def _ids_oficio_pendientes(act_id: int) -> set[int]:
    filas = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters(omitir_rango_fecha=True)
    )
    return {o.id for a, o, _ini in filas if a.id == act_id}


def _completar_trabajo_row(item_id: int) -> dict:
    item = (
        RutaItem.query.options(
            joinedload(RutaItem.actuacion),
            joinedload(RutaItem.iniciador_ruta),
        )
        .filter(RutaItem.id == item_id)
        .first()
    )
    assert item is not None
    return ruta_item_completar_trabajo_to_row(item)


def test_cumple_cierra_circuito_sin_reencolar(app_ctx) -> None:
    """Cumple: ítem realizado, iniciador CUMPLIDO, oficio no editable, fuera de Pendientes."""
    item, act, ini, u, ofi = _mk_reinspeccion_oficio_en_ruta_publicada()
    _cerrar(
        item.id,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        },
    )

    ini_db = db.session.get(IniciadorRuta, ini.id)
    act_db = db.session.get(Actuaciones, act.id)
    item_db = db.session.get(RutaItem, item.id)
    ofi_db = db.session.get(Oficio, ofi.id)
    assert ini_db is not None and act_db is not None and item_db is not None and ofi_db is not None
    assert item_db.estado_ejecucion == "REALIZADO"
    assert item_db.estado_ruta_item == "FINALIZADO"
    assert act_db.resultado_cumplimiento_oficio == "CUMPLE"
    assert ini_db.estado_iniciador == "CUMPLIDO"
    assert ini_db.cerrado_motivo is None

    assert ofi_db.id not in _ids_oficio_pendientes(act.id)
    pol = evaluar_editable_oficio(ofi.id)
    assert pol["editable"] is False
    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini.id not in planif_ids

    assert estado_recorrido_label(act_db) == "Ratificación de clausura — visita realizada"
    row = comprobacion_recorrido_resumen_row(act_db)
    assert row.get("estado_recorrido") == "Ratificación de clausura — visita realizada"
    assert row.get("resultado_cumplimiento_oficio") == "CUMPLE"
    ct = _completar_trabajo_row(item.id)
    assert ct.get("resultado_cumplimiento_oficio") == "CUMPLE"


def test_no_cumple_simple_cierra_sin_volver_a_pendientes(app_ctx) -> None:
    """NO_CUMPLE simple: resultado visible No cumple; no Pendientes; oficio no editable; no republica."""
    item, act, ini, u, ofi = _mk_reinspeccion_oficio_en_ruta_publicada()
    _cerrar(
        item.id,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "NO_CUMPLE",
        },
    )

    ini_db = db.session.get(IniciadorRuta, ini.id)
    act_db = db.session.get(Actuaciones, act.id)
    item_db = db.session.get(RutaItem, item.id)
    assert ini_db is not None and act_db is not None and item_db is not None
    assert act_db.resultado_cumplimiento_oficio == "NO_CUMPLE"
    assert item_db.estado_ejecucion == "REALIZADO"
    assert item_db.estado_ruta_item == "FINALIZADO"
    assert ini_db.estado_iniciador == "CUMPLIDO"
    assert ini_db.cerrado_motivo is None
    assert iniciador_tiene_intentos_historicos_cerrados(ini.id) is False

    assert ofi.id not in _ids_oficio_pendientes(act.id)
    pol = evaluar_editable_oficio(ofi.id)
    assert pol["editable"] is False
    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini.id not in planif_ids

    assert estado_recorrido_label(act_db) == "Ratificación de clausura — no cumple"
    row = comprobacion_recorrido_resumen_row(act_db)
    assert row.get("estado_recorrido") == "Ratificación de clausura — no cumple"
    assert row.get("resultado_cumplimiento_oficio") == "NO_CUMPLE"
    ct = _completar_trabajo_row(item.id)
    assert ct.get("resultado_cumplimiento_oficio") == "NO_CUMPLE"

    ruta = RutaTrabajo(
        fecha=fecha_ruta_aislada_mismo_anio(2026),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        created_by_user_id=int(u.id),
        numero=uniq_ruta_numero(),
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre=f"G_{uuid4().hex[:6]}", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=_dos_inspector_ids(),
    )
    with pytest.raises(RuntimeError, match="PENDIENTE"):
        assign_iniciadores_to_grupo(
            ruta_id=ruta.id,
            grupo_id=grupo.id,
            iniciador_ids=[ini.id],
        )


def test_historial_no_cumple_simple_muestra_no_cumple_nunca_cumple(app_ctx) -> None:
    """Historial documental: CUMPLIDO técnico + NO_CUMPLE muestra No cumple, oficio no editable."""
    from tests.test_comprobacion_recorrido_oficio_resuelto_hotfix import (
        _mk_circuito,
        _mk_oficio_con_visita_cerrada,
    )

    act, comp, dom, u = _mk_circuito()
    ofi = _mk_oficio_con_visita_cerrada(
        comp=comp,
        act_ancla=act,
        dom=dom,
        u=u,
        tipo_iniciador="RATIFICACION_CLAUSURA_OFICIO",
        tipo_visita="RATIFICACION DE CLAUSURA",
        resultado="NO_CUMPLE",
    )
    db.session.commit()

    assert estado_recorrido_label(act) == "Ratificación de clausura — no cumple"
    row = comprobacion_recorrido_resumen_row(act)
    assert row.get("resultado_cumplimiento_oficio") == "NO_CUMPLE"
    assert row.get("estado_recorrido") == "Ratificación de clausura — no cumple"
    resumen = row.get("oficios_resumen") or []
    assert resumen
    assert resumen[0].get("conclusion") == "No cumple"
    assert resumen[0].get("resultado_cumplimiento_oficio") == "NO_CUMPLE"
    pol = evaluar_editable_oficio(ofi.id)
    assert pol["editable"] is False
    assert pol["estado_operativo"] == "cumplido"


def test_no_cumple_con_contraproducencia_reencola_y_preserva_visita(app_ctx) -> None:
    """NO_CUMPLE + contra: Pendientes, oficio editable, republicar crea actuación nueva."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u, ofi = _mk_reinspeccion_oficio_en_ruta_publicada()
    insp_ids = _attach_inspectores(act)
    db.session.commit()
    act1_id = int(act.id)
    item1_id = int(item.id)
    user_id = int(u.id)

    _cerrar(
        item.id,
        user_id,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "contraproducencia": "LOCAL CERRADO",
        },
    )

    ini_db = db.session.get(IniciadorRuta, ini.id)
    act1 = db.session.get(Actuaciones, act1_id)
    item1 = db.session.get(RutaItem, item1_id)
    assert ini_db is not None and act1 is not None and item1 is not None
    assert ini_db.estado_iniciador == "PENDIENTE"
    assert item1.estado_ejecucion == "NO_REALIZADO"
    assert item1.estado_ruta_item == "FINALIZADO"
    assert act1.contraproducencia == "LOCAL CERRADO"
    assert act1.resultado_cumplimiento_oficio is None
    assert sorted(int(i.id) for i in act1.inspector) == sorted(insp_ids)
    assert iniciador_tiene_intentos_historicos_cerrados(ini.id) is True

    assert ofi.id in _ids_oficio_pendientes(act1_id)
    pol = evaluar_editable_oficio(ofi.id)
    assert pol["editable"] is True
    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini.id in planif_ids

    item2 = _republicar_iniciador_pendiente(
        ini_db,
        user_id,
        fecha=fecha_ruta_aislada_mismo_anio(2026),
    )
    assert item2.actuacion_id is not None
    assert int(item2.actuacion_id) != act1_id

    act1_post = db.session.get(Actuaciones, act1_id)
    item1_post = db.session.get(RutaItem, item1_id)
    act2 = db.session.get(Actuaciones, item2.actuacion_id)
    assert act1_post is not None and item1_post is not None and act2 is not None
    assert item1_post.actuacion_id == act1_id
    assert item1_post.estado_ejecucion == "NO_REALIZADO"
    assert act1_post.contraproducencia == "LOCAL CERRADO"
    assert act1_post.resultado_cumplimiento_oficio is None
    assert sorted(int(i.id) for i in act1_post.inspector) == sorted(insp_ids)
    assert str(act1_post.tipo) == "VERIFICAR E INFORMAR"
    assert act2.contraproducencia in (None, "")
    assert act2.resultado_cumplimiento_oficio is None
