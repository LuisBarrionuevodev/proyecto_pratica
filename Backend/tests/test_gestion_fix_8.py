"""GESTIÓN-FIX.8 — Reinspección por Notificación: reversibilidad REALIZADO ⇄ CONTRAPRODUCENCIA."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.actuacion_reencolado_service import (
    MSG_CONTRA_CON_ACTAS,
    actuacion_bloqueada_por_intento_posterior,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.oficio_circuito_service import (
    actuacion_tiene_actas_visita_reinspeccion_notificacion,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    planificable_iniciadores_base_query,
)
from app.models import (
    Actuaciones,
    CatalogContraproducencia,
    IniciadorRuta,
    Inspeccion,
    Notificacion,
    RutaItem,
    actuaciones_inspector,
)

from tests.test_gestion_fix_5 import _republicar_iniciador_generico
from tests.test_hotfix_reinspeccion_notificacion import _mk_reinspeccion_notificacion_item


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


def _prep_ot_numerica_unica(act_id: int) -> Actuaciones:
    from app.models import OrdenTrabajo

    act = db.session.get(Actuaciones, act_id)
    assert act is not None and act.orden_trabajo is not None
    ot = act.orden_trabajo
    if not str(ot.numero_acta or "").isdigit():
        for _ in range(30):
            cand = f"{random.randint(100000, 999999):06d}"
            clash = OrdenTrabajo.query.filter(
                OrdenTrabajo.numero_acta == cand,
                OrdenTrabajo.anio == ot.anio,
                OrdenTrabajo.id != ot.id,
            ).first()
            if clash is None:
                ot.numero_acta = cand
                db.session.commit()
                break
        else:
            pytest.skip("No se pudo asignar OT numérica única para el test")
    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    return act_db


def _ot_numerica(act: Actuaciones) -> str:
    raw = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    return str(raw).zfill(6) if str(raw).isdigit() else "000001"


def _dos_inspectores() -> tuple[str, str]:
    from app.models import Inspector

    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    return rows[0].nombre, rows[1].nombre


def _cerrar_rn_realizado(
    *,
    item_id: int,
    user_id: int,
    acta_inspeccion: str | None = None,
    acta_comprobacion: str | None = None,
) -> None:
    body: dict = {"tipo_actuacion": "REINSPECCION"}
    if acta_inspeccion:
        body["acta_inspeccion_num"] = acta_inspeccion
    if acta_comprobacion:
        body["acta_comprobacion_num"] = acta_comprobacion
        body["comprobacion_motivo"] = "Motivo prueba FIX8"
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(body),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()


def _fila_put_rn_contra(
    *,
    act_id: int,
    ot: str,
    fecha: str,
    insp1: str,
    insp2: str,
    actas_a_quitar: list[str] | None = None,
) -> dict:
    row: dict = {
        "id": act_id,
        "orden_trabajo_numero": ot,
        "fecha_actuacion": fecha,
        "tipo_actuacion": "REINSPECCION",
        "inspector1": insp1,
        "inspector2": insp2,
        "acta_inspeccion_num": None,
        "acta_comprobacion_num": None,
        "contraproducencia": "LOCAL CERRADO",
    }
    if actas_a_quitar:
        row["actas_a_quitar"] = actas_a_quitar
    return row


def test_n1_rn_realizado_quitar_inspeccion_a_contra_ok(app_ctx) -> None:
    """N1: REALIZADO + Inspección → quitar → LOCAL CERRADO."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u, _noti = _mk_reinspeccion_notificacion_item()
    insp1, insp2 = _dos_inspectores()
    acta = f"{random.randint(100000, 999999):06d}"
    _cerrar_rn_realizado(item_id=int(item.id), user_id=int(u.id), acta_inspeccion=acta)

    act_db = _prep_ot_numerica_unica(int(act.id))
    ot = _ot_numerica(act_db)
    fecha = act_db.fecha.strftime("%d/%m/%Y")

    row = ActuacionGridRowIn.model_validate(
        _fila_put_rn_contra(
            act_id=int(act.id),
            ot=ot,
            fecha=fecha,
            insp1=insp1,
            insp2=insp2,
            actas_a_quitar=["INSPECCION"],
        )
    )
    actualizar_actuacion(int(act.id), map_actuacion_row(row))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act.id)
    item_db = db.session.get(RutaItem, item.id)
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.inspeccion is None
    assert item_db is not None and item_db.estado_ejecucion == "NO_REALIZADO"
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert ini_db.tipo_iniciador == "REINSPECCION_NOTIFICACION"


def test_n2_rn_quitar_inspeccion_y_comprobacion_a_contra_ok(app_ctx) -> None:
    """N2: REALIZADO + Inspección + Comprobación → quitar ambas → LOCAL CERRADO."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u, _noti = _mk_reinspeccion_notificacion_item()
    insp1, insp2 = _dos_inspectores()
    _cerrar_rn_realizado(
        item_id=int(item.id),
        user_id=int(u.id),
        acta_inspeccion=f"{random.randint(100000, 999999):06d}",
        acta_comprobacion=f"{random.randint(100000, 999999):06d}",
    )

    act_db = _prep_ot_numerica_unica(int(act.id))
    row = ActuacionGridRowIn.model_validate(
        _fila_put_rn_contra(
            act_id=int(act.id),
            ot=_ot_numerica(act_db),
            fecha=act_db.fecha.strftime("%d/%m/%Y"),
            insp1=insp1,
            insp2=insp2,
            actas_a_quitar=["INSPECCION", "COMPROBACION"],
        )
    )
    actualizar_actuacion(int(act.id), map_actuacion_row(row))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.comprobacion_id is None
    assert act_db.inspeccion is None


def test_n3_rn_solo_notificacion_origen_a_contra_ok(app_ctx) -> None:
    """N3: notificación origen no cuenta como acta de visita."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u, noti = _mk_reinspeccion_notificacion_item()
    insp1, insp2 = _dos_inspectores()
    _cerrar_rn_realizado(
        item_id=int(item.id),
        user_id=int(u.id),
        acta_inspeccion=f"{random.randint(100000, 999999):06d}",
    )

    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    assert act_db.notificacion_id == noti.id

    ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
    if ins:
        db.session.delete(ins)
        db.session.commit()
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    assert act_db.notificacion_id == noti.id
    assert not actuacion_tiene_actas_visita_reinspeccion_notificacion(act_db)

    act_db = _prep_ot_numerica_unica(int(act.id))
    row = ActuacionGridRowIn.model_validate(
        _fila_put_rn_contra(
            act_id=int(act.id),
            ot=_ot_numerica(act_db),
            fecha=act_db.fecha.strftime("%d/%m/%Y"),
            insp1=insp1,
            insp2=insp2,
        )
    )
    actualizar_actuacion(int(act.id), map_actuacion_row(row))
    db.session.expunge_all()

    noti_db = db.session.get(Notificacion, noti.id)
    act_db = db.session.get(Actuaciones, act.id)
    assert noti_db is not None and noti_db.deleted_at is None
    assert act_db is not None and act_db.notificacion_id == noti.id
    assert act_db.contraproducencia == "LOCAL CERRADO"


def test_n4_rn_contra_sin_quitar_actas_falla(app_ctx) -> None:
    """N4: REALIZADO + Inspección → LOCAL CERRADO sin quitar → 400."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, _ini, u, _noti = _mk_reinspeccion_notificacion_item()
    insp1, insp2 = _dos_inspectores()
    _cerrar_rn_realizado(
        item_id=int(item.id),
        user_id=int(u.id),
        acta_inspeccion=f"{random.randint(100000, 999999):06d}",
    )

    act_db = _prep_ot_numerica_unica(int(act.id))
    row = ActuacionGridRowIn.model_validate(
        _fila_put_rn_contra(
            act_id=int(act.id),
            ot=_ot_numerica(act_db),
            fecha=act_db.fecha.strftime("%d/%m/%Y"),
            insp1=insp1,
            insp2=insp2,
        )
    )
    with pytest.raises(ValueError, match=MSG_CONTRA_CON_ACTAS):
        actualizar_actuacion(int(act.id), map_actuacion_row(row))


def test_n5_rn_contra_a_realizado_ok(app_ctx) -> None:
    """N5: LOCAL CERRADO → limpiar contra → cargar Inspección."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u, _noti = _mk_reinspeccion_notificacion_item()
    insp1, insp2 = _dos_inspectores()
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=int(item.id),
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"tipo_actuacion": "REINSPECCION", "contraproducencia": "LOCAL CERRADO"}
        ),
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()

    act_db = _prep_ot_numerica_unica(int(act.id))
    acta = f"{random.randint(100000, 999999):06d}"
    row = ActuacionGridRowIn.model_validate(
        {
            "id": int(act.id),
            "orden_trabajo_numero": _ot_numerica(act_db),
            "fecha_actuacion": act_db.fecha.strftime("%d/%m/%Y"),
            "tipo_actuacion": "REINSPECCION",
            "inspector1": insp1,
            "inspector2": insp2,
            "acta_inspeccion_num": acta,
            "limpiar_contraproducencia": True,
            "contraproducencia": None,
        }
    )
    actualizar_actuacion(int(act.id), map_actuacion_row(row))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act.id)
    item_db = db.session.get(RutaItem, item.id)
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert act_db is not None and act_db.contraproducencia is None
    assert act_db.inspeccion is not None
    assert item_db is not None and item_db.estado_ejecucion == "REALIZADO"
    assert ini_db is not None and ini_db.estado_iniciador == "CUMPLIDO"


def test_n6_rn_contra_a_realizado_bloqueado_si_act_b_posterior(app_ctx) -> None:
    """N6: FIX.5 bloquea corrección si existe Act B posterior."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u, _noti = _mk_reinspeccion_notificacion_item()
    user_id = int(u.id)
    insp1, insp2 = _dos_inspectores()
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=int(item.id),
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"tipo_actuacion": "REINSPECCION", "contraproducencia": "LOCAL CERRADO"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    _republicar_iniciador_generico(ini_db, user_id, date(2098, 8, 1))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    assert actuacion_bloqueada_por_intento_posterior(int(act.id))

    row = ActuacionGridRowIn.model_validate(
        {
            "id": int(act.id),
            "orden_trabajo_numero": _ot_numerica(act_db),
            "fecha_actuacion": act_db.fecha.strftime("%d/%m/%Y"),
            "tipo_actuacion": "REINSPECCION",
            "inspector1": insp1,
            "inspector2": insp2,
            "acta_inspeccion_num": f"{random.randint(100000, 999999):06d}",
            "limpiar_contraproducencia": True,
        }
    )
    with pytest.raises(ValueError):
        actualizar_actuacion(int(act.id), map_actuacion_row(row))


def test_n7_replanificacion_crea_actuacion_nueva(app_ctx) -> None:
    """N7: tras N1, replanificar crea Act B distinta."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u, _noti = _mk_reinspeccion_notificacion_item()
    user_id = int(u.id)
    insp1, insp2 = _dos_inspectores()
    _cerrar_rn_realizado(
        item_id=int(item.id),
        user_id=int(u.id),
        acta_inspeccion=f"{random.randint(100000, 999999):06d}",
    )
    act_db = _prep_ot_numerica_unica(int(act.id))
    row = ActuacionGridRowIn.model_validate(
        _fila_put_rn_contra(
            act_id=int(act.id),
            ot=_ot_numerica(act_db),
            fecha=act_db.fecha.strftime("%d/%m/%Y"),
            insp1=insp1,
            insp2=insp2,
            actas_a_quitar=["INSPECCION"],
        )
    )
    actualizar_actuacion(int(act.id), map_actuacion_row(row))
    db.session.expunge_all()

    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    item2 = _republicar_iniciador_generico(ini_db, user_id, date(2098, 9, 1))
    assert item2.actuacion_id is not None
    assert int(item2.actuacion_id) != int(act.id)
    ini_ref = db.session.get(IniciadorRuta, ini.id)
    assert ini_ref is not None and ini_ref.tipo_iniciador == "REINSPECCION_NOTIFICACION"


def test_n8_inspectores_se_conservan_en_correccion(app_ctx) -> None:
    """N8: corrección REALIZADO→CONTRA no borra inspectores de Act A."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, _ini, u, _noti = _mk_reinspeccion_notificacion_item()
    from app.models import Inspector

    ins_rows = Inspector.query.limit(2).all()
    if len(ins_rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores")
    for ins_row in ins_rows:
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id,
                inspector_id=ins_row.id,
            )
        )
    db.session.commit()

    _cerrar_rn_realizado(
        item_id=int(item.id),
        user_id=int(u.id),
        acta_inspeccion=f"{random.randint(100000, 999999):06d}",
    )
    act_db = _prep_ot_numerica_unica(int(act.id))
    from sqlalchemy import func, select

    count_antes = db.session.scalar(
        select(func.count())
        .select_from(actuaciones_inspector)
        .where(actuaciones_inspector.c.actuaciones_id == act.id)
    )
    assert count_antes is not None and count_antes >= 2

    row = ActuacionGridRowIn.model_validate(
        _fila_put_rn_contra(
            act_id=int(act.id),
            ot=_ot_numerica(act_db),
            fecha=act_db.fecha.strftime("%d/%m/%Y"),
            insp1=ins_rows[0].nombre,
            insp2=ins_rows[1].nombre,
            actas_a_quitar=["INSPECCION"],
        )
    )
    actualizar_actuacion(int(act.id), map_actuacion_row(row))
    count_despues = db.session.scalar(
        select(func.count())
        .select_from(actuaciones_inspector)
        .where(actuaciones_inspector.c.actuaciones_id == act.id)
    )
    assert count_despues == count_antes


def test_n9_presenter_no_muestra_notif_origen_como_acta(app_ctx) -> None:
    """N9: acta_notificacion_num vacío; origen en trámite."""
    item, act, ini, u, noti = _mk_reinspeccion_notificacion_item()
    _cerrar_rn_realizado(
        item_id=int(item.id),
        user_id=int(u.id),
        acta_inspeccion=f"{random.randint(100000, 999999):06d}",
    )
    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    grid = actuacion_to_grid_row(act_db, iniciador_desde_ruta=db.session.get(IniciadorRuta, ini.id))
    assert grid.get("acta_notificacion_num") in (None, "")
    origen = grid.get("origen_reinspeccion_notificacion") or {}
    assert str(origen.get("notificacion_acta_numero")) == str(noti.numero_acta)
    assert grid.get("notificacion_editable") is False
