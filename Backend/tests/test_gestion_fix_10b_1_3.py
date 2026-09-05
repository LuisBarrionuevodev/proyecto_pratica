"""GESTIÓN-FIX.10B.1.3 — PUT transaccional actas_a_quitar al pasar a contraproducencia."""

from __future__ import annotations

import random
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.actuacion_reencolado_service import MSG_CONTRA_CON_ACTAS
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.models import Actuaciones, CatalogContraproducencia, Domicilio, Inspeccion, Inspector

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
) -> dict:
    return {
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
        "actas_a_quitar": ["INSPECCION"],
    }


def test_t1_put_atomico_quita_acta_contra_y_contrib(app_ctx) -> None:
    """Caso QA: REALIZADO + acta + contrib → LOCAL CERRADO en un solo PUT."""
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

    act_realizado = db.session.get(Actuaciones, act_id)
    assert act_realizado is not None
    assert act_realizado.establecimiento_operativo_id is not None
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is not None

    row = ActuacionGridRowIn.model_validate(
        _fila_put_local_cerrado_quitar_acta(
            act_id=act_id,
            ot=ot_num,
            fecha=fecha,
            insp1=insp1,
            insp2=insp2,
            calle=dom.calle or "San Martín",
            numero=dom.numero or "100",
            rubro_nombre=dom.rubro.nombre if dom.rubro else "Bar",
        )
    )
    payload = map_actuacion_row(row)
    assert payload.get("actas_a_quitar") == ["INSPECCION"]
    assert payload.get("contribuyente") is None
    assert payload.get("tipo_actuacion") == "INSPECCION"

    actualizar_actuacion(act_id, payload)
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    dom_db = db.session.get(Domicilio, act_db.domicilio_id) if act_db else None
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.tipo == "INSPECCION"
    assert act_db.inspeccion is None
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None
    assert act_db.establecimiento_operativo_id is None
    assert dom_db is not None
    assert dom_db.contribuyente_id is None


def test_t3_rollback_restaura_inspeccion_si_put_falla_tras_quitar(app_ctx) -> None:
    """Si el PUT falla después de quitar actas en sesión, no debe persistir el borrado."""
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
    payload = map_actuacion_row(
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
            )
        )
    )

    with patch(
        "app.domains.actuaciones.services.update_service.procesar_establecimiento_contraproducencia_desde_put",
        side_effect=ValueError("fallo simulado post-quitar"),
    ):
        with pytest.raises(ValueError, match="fallo simulado"):
            actualizar_actuacion(act_id, dict(payload))
        db.session.rollback()

    db.session.expunge_all()
    ins_db = Inspeccion.query.filter_by(actuacion_id=act_id).first()
    assert ins_db is not None
    assert str(ins_db.numero_acta) == acta_num
    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert (act_db.contraproducencia or "").strip() == ""


def test_t4_reintento_tras_rollback_no_falla_por_acta_ausente(app_ctx) -> None:
    """Segundo PUT tras rollback completo no debe chocar con acta ya eliminada."""
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
    payload = map_actuacion_row(
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
            )
        )
    )

    with patch(
        "app.domains.actuaciones.services.update_service.procesar_establecimiento_contraproducencia_desde_put",
        side_effect=ValueError("fallo simulado primer intento"),
    ):
        with pytest.raises(ValueError, match="fallo simulado"):
            actualizar_actuacion(act_id, dict(payload))
        db.session.rollback()

    db.session.expunge_all()
    payload_reintento = map_actuacion_row(
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
            )
        )
    )
    actualizar_actuacion(act_id, payload_reintento)
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None


def test_t6_contra_sin_quitar_actas_sigue_bloqueado(app_ctx) -> None:
    """Sin actas_a_quitar, LOCAL CERRADO con acta persistida sigue rechazado."""
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


def test_t7_local_cerrado_a_realizado_sigue_funcionando(app_ctx) -> None:
    """Camino inverso: limpiar contra y cargar acta no se altera por 10B.1.3."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _ruta_id, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    insp1, insp2 = _dos_inspectores()

    act = db.session.get(Actuaciones, act_id)
    dom = db.session.get(Domicilio, dom_id)
    assert act is not None and dom is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"tipo_actuacion": "INSPECCION", "contraproducencia": "LOCAL CERRADO"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    acta_num = f"{random.randint(100000, 999999):06d}"
    row_limpia = ActuacionGridRowIn.model_validate(
        {
            "id": act_id,
            "orden_trabajo_numero": ot_num,
            "fecha_actuacion": fecha,
            "tipo_actuacion": "INSPECCION",
            "calle": dom.calle or "San Martín",
            "numero": dom.numero or "100",
            "rubro_nombre": dom.rubro.nombre if dom.rubro else "Bar",
            "doc_nro": "30123456",
            "contrib_apellido": "Titular",
            "contrib_nombre": "Prueba",
            "inspector1": insp1,
            "inspector2": insp2,
            "acta_inspeccion_num": acta_num,
            "limpiar_contraproducencia": True,
            "contraproducencia": None,
        }
    )
    actualizar_actuacion(act_id, map_actuacion_row(row_limpia))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert (act_db.contraproducencia or "").strip() == ""
    assert act_db.inspeccion is not None
    assert str(act_db.inspeccion.numero_acta) == acta_num
