"""GESTIÓN-FIX.10B.1.5 — Idempotencia de actas_a_quitar solo en PUT transaccional."""

from __future__ import annotations

import random
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.actas_quitar_canal_actas_service import (
    quitar_acta_canal_actas,
    quitar_actas_de_actuacion_en_sesion,
)
from app.domains.actuaciones.services.actuacion_reencolado_service import MSG_CONTRA_CON_ACTAS
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.models import Actuaciones, CatalogContraproducencia, Domicilio, Inspeccion, Inspector

from tests.test_gestion_fix_3 import _fila_realizado_a_contra
from tests.test_gestion_fix_8 import (
    _cerrar_rn_realizado,
    _fila_put_rn_contra,
    _ot_numerica,
    _prep_ot_numerica_unica,
)
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada
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


def _fila_put_local_cerrado_quitar_acta(
    *,
    act_id: int,
    ot: str,
    fecha: str,
    insp1: str,
    insp2: str,
    calle: str,
    numero: str,
    rubro_nombre: str,
    actas_a_quitar: list[str] | None = None,
) -> dict:
    row: dict = {
        "id": act_id,
        "orden_trabajo_numero": ot,
        "fecha_actuacion": fecha,
        "tipo_actuacion": "INSPECCION",
        "inspector1": insp1,
        "inspector2": insp2,
        "calle": calle,
        "numero": numero,
        "rubro_nombre": rubro_nombre,
        "limpiar_contribuyente": True,
        "contraproducencia": "LOCAL CERRADO",
        "actas_a_quitar": actas_a_quitar if actas_a_quitar is not None else ["INSPECCION"],
    }
    return row


def _payload_put_local_cerrado(
    *,
    act_id: int,
    ot: str,
    fecha: str,
    insp1: str,
    insp2: str,
    calle: str,
    numero: str,
    rubro_nombre: str,
    actas_a_quitar: list[str] | None = None,
) -> dict:
    return map_actuacion_row(
        ActuacionGridRowIn.model_validate(
            _fila_put_local_cerrado_quitar_acta(
                act_id=act_id,
                ot=ot,
                fecha=fecha,
                insp1=insp1,
                insp2=insp2,
                calle=calle,
                numero=numero,
                rubro_nombre=rubro_nombre,
                actas_a_quitar=actas_a_quitar,
            )
        )
    )


def _assert_estado_local_cerrado_limpio(act_id: int, dom_id: int) -> None:
    act_db = db.session.get(Actuaciones, act_id)
    dom_db = db.session.get(Domicilio, dom_id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.tipo == "INSPECCION"
    assert act_db.inspeccion is None
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None
    assert act_db.establecimiento_operativo_id is None
    assert dom_db is not None
    assert dom_db.contribuyente_id is None


def test_t1_happy_path_put_quita_acta_contra_y_contrib(app_ctx) -> None:
    """T1: REALIZADO + acta + contrib → LOCAL CERRADO en un PUT."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()
    acta_num = f"{random.randint(100000, 999999):06d}"

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(item_id=item_id, user_id=user_id, acta=acta_num)

    payload = _payload_put_local_cerrado(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=dom.calle or "San Martín",
        numero=dom.numero or "100",
        rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
    )
    actualizar_actuacion(act_id, payload)
    db.session.expunge_all()
    _assert_estado_local_cerrado_limpio(act_id, dom_id)


def test_t2_put_repetido_idempotente(app_ctx) -> None:
    """T2: segundo PUT idéntico devuelve éxito sin error por acta ausente."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()
    acta_num = f"{random.randint(100000, 999999):06d}"

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(item_id=item_id, user_id=user_id, acta=acta_num)

    kwargs = {
        "act_id": act_id,
        "ot": ot_num,
        "fecha": fecha,
        "insp1": insp1,
        "insp2": insp2,
        "calle": dom.calle or "San Martín",
        "numero": dom.numero or "100",
        "rubro_nombre": dom.rubro.nombre if dom.rubro else "Bar",
    }
    payload = _payload_put_local_cerrado(**kwargs)
    actualizar_actuacion(act_id, payload)
    db.session.expunge_all()
    _assert_estado_local_cerrado_limpio(act_id, dom_id)

    payload_retry = _payload_put_local_cerrado(**kwargs)
    actualizar_actuacion(act_id, payload_retry)
    db.session.expunge_all()
    _assert_estado_local_cerrado_limpio(act_id, dom_id)


def test_t3_estado_intermedio_completa_clear_contrib(app_ctx) -> None:
    """T3: contra + sin inspección + contrib/EO presentes → PUT completa la corrección."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()
    acta_num = f"{random.randint(100000, 999999):06d}"

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(item_id=item_id, user_id=user_id, acta=acta_num)

    act_mid = db.session.get(Actuaciones, act_id)
    dom_mid = db.session.get(Domicilio, dom_id)
    assert act_mid is not None and dom_mid is not None
    assert act_mid.establecimiento_operativo_id is not None
    assert dom_mid.contribuyente_id is not None

    quitar_acta_canal_actas(act_id, "INSPECCION")
    act_mid = db.session.get(Actuaciones, act_id)
    assert act_mid is not None
    act_mid.contraproducencia = "LOCAL CERRADO"
    db.session.commit()
    db.session.expunge_all()

    act_before = db.session.get(Actuaciones, act_id)
    dom_before = db.session.get(Domicilio, dom_id)
    assert act_before is not None and dom_before is not None
    assert act_before.contraproducencia == "LOCAL CERRADO"
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None
    assert dom_before.contribuyente_id is not None
    assert act_before.establecimiento_operativo_id is not None

    payload = _payload_put_local_cerrado(
        act_id=act_id,
        ot=ot_num,
        fecha=fecha,
        insp1=insp1,
        insp2=insp2,
        calle=dom.calle or "San Martín",
        numero=dom.numero or "100",
        rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
    )
    actualizar_actuacion(act_id, payload)
    db.session.expunge_all()
    _assert_estado_local_cerrado_limpio(act_id, dom_id)


def test_t4_post_explicito_sigue_fallando_sin_acta(app_ctx) -> None:
    """T4: POST /quitar-acta conserva error 400 si la inspección ya no existe."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    acta_num = f"{random.randint(100000, 999999):06d}"

    _cerrar_realizado_con_acta(item_id=item_id, user_id=user_id, acta=acta_num)
    quitar_acta_canal_actas(act_id, "INSPECCION")
    db.session.expunge_all()

    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None
    with pytest.raises(ValueError, match="No hay acta de inspección vinculada"):
        quitar_acta_canal_actas(act_id, "INSPECCION")


def test_t5_tipo_desconocido_sigue_fallando(app_ctx) -> None:
    """T5: tipo inválido no usa tolerancia (ni en schema ni en service)."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()
    acta_num = f"{random.randint(100000, 999999):06d}"

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    _cerrar_realizado_con_acta(item_id=item_id, user_id=user_id, acta=acta_num)

    with pytest.raises(Exception, match="inválido"):
        ActuacionGridRowIn.model_validate(
            _fila_put_local_cerrado_quitar_acta(
                act_id=act_id,
                ot=ot_num,
                fecha=fecha,
                insp1=insp1,
                insp2=insp2,
                calle=dom.calle or "San Martín",
                numero=dom.numero or "100",
                rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
                actas_a_quitar=["ACTA_INVENTADA"],
            )
        )

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    with pytest.raises(ValueError, match="inválido"):
        quitar_actas_de_actuacion_en_sesion(
            act_db,
            ["ACTA_INVENTADA"],
            tolerar_ausentes=True,
        )


def test_t6_rn_put_repetido_idempotente(app_ctx) -> None:
    """T6: RN — segundo PUT con actas_a_quitar ya ausentes no falla."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, _ini, u, _noti = _mk_reinspeccion_notificacion_item()
    insp1, insp2 = _dos_inspectores()
    acta = f"{random.randint(100000, 999999):06d}"
    _cerrar_rn_realizado(item_id=int(item.id), user_id=int(u.id), acta_inspeccion=acta)

    act_db = _prep_ot_numerica_unica(int(act.id))
    row_kwargs = {
        "act_id": int(act.id),
        "ot": _ot_numerica(act_db),
        "fecha": act_db.fecha.strftime("%d/%m/%Y"),
        "insp1": insp1,
        "insp2": insp2,
        "actas_a_quitar": ["INSPECCION"],
    }
    payload = map_actuacion_row(
        ActuacionGridRowIn.model_validate(_fila_put_rn_contra(**row_kwargs))
    )
    actualizar_actuacion(int(act.id), payload)
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.inspeccion is None

    payload_retry = map_actuacion_row(
        ActuacionGridRowIn.model_validate(_fila_put_rn_contra(**row_kwargs))
    )
    actualizar_actuacion(int(act.id), payload_retry)
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.inspeccion is None


def test_t7_contra_sin_quitar_actas_sigue_bloqueado(app_ctx) -> None:
    """T7: MSG_CONTRA_CON_ACTAS intacto si la inspección sigue presente."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
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

    row = ActuacionGridRowIn.model_validate(
        _fila_realizado_a_contra(
            act_id=act_id,
            ot=ot_num,
            fecha=fecha,
            insp1=insp1,
            insp2=insp2,
        )
    )
    with pytest.raises(ValueError, match=MSG_CONTRA_CON_ACTAS):
        actualizar_actuacion(act_id, map_actuacion_row(row))
