"""GESTIÓN-FIX.3 — reversibilidad operativa y corrección transaccional Verificar."""

from __future__ import annotations

import random
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import CorregirCierreOficioIn
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.corregir_cierre_oficio_service import corregir_cierre_oficio
from app.domains.actuaciones.services.actas_quitar_canal_actas_service import quitar_acta_canal_actas
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    planificable_iniciadores_base_query,
)
from app.models import Actuaciones, CatalogContraproducencia, IniciadorRuta, Inspeccion, RutaItem

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
from tests.test_hotfix_reinspeccion_notificacion import _mk_reinspeccion_notificacion_item
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


def _fila_realizado_a_contra(
    *,
    act_id: int,
    ot: str,
    fecha: str,
    insp1: str,
    insp2: str,
    calle: str = "San Martín",
    numero: str = "100",
    rubro_nombre: str = "Bar",
    doc_nro: str = "30123456",
    contrib_apellido: str = "Titular",
    contrib_nombre: str = "Prueba",
    tipo_actuacion: str = "INSPECCION",
    include_domicilio: bool = True,
) -> dict:
    row: dict = {
        "id": act_id,
        "orden_trabajo_numero": ot,
        "fecha_actuacion": fecha,
        "tipo_actuacion": tipo_actuacion,
        "inspector1": insp1,
        "inspector2": insp2,
        "acta_inspeccion_num": None,
        "contraproducencia": "LOCAL CERRADO",
    }
    if include_domicilio:
        row.update(
            {
                "calle": calle,
                "numero": numero,
                "rubro_nombre": rubro_nombre,
                "doc_nro": doc_nro,
                "contrib_apellido": contrib_apellido,
                "contrib_nombre": contrib_nombre,
            }
        )
    return row


def test_realizado_a_contra_reencola_y_entra_al_pool(app_ctx) -> None:
    """Inspección normal: REALIZADO → LOCAL CERRADO sincroniza capas y pool."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _ruta_borrador_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    from app.models import Inspector

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    insp1_nombre = inspectores[0].nombre
    insp2_nombre = inspectores[1].nombre

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "contraproducencia": "LOCAL CERRADO",
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act_pre = db.session.get(Actuaciones, act_id)
    assert act_pre is not None
    acta_num = f"{random.randint(100000, 999999):06d}"
    row_limpia = ActuacionGridRowIn.model_validate(
        {
            "id": act_id,
            "orden_trabajo_numero": ot_num,
            "fecha_actuacion": fecha,
            "tipo_actuacion": "INSPECCION",
            "calle": "San Martín",
            "numero": "100",
            "rubro_nombre": "Bar",
            "doc_nro": "30123456",
            "contrib_apellido": "Titular",
            "contrib_nombre": "Prueba",
            "inspector1": insp1_nombre,
            "inspector2": insp2_nombre,
            "acta_inspeccion_num": acta_num,
            "limpiar_contraproducencia": True,
            "contraproducencia": None,
        }
    )
    actualizar_actuacion(act_id, map_actuacion_row(row_limpia))
    db.session.expunge_all()

    ini_mid = db.session.get(IniciadorRuta, ini_id)
    assert ini_mid is not None and ini_mid.estado_iniciador == "CUMPLIDO"
    planif_mid = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id not in planif_mid

    quitar_acta_canal_actas(act_id, "INSPECCION")
    db.session.expunge_all()

    row_contra = ActuacionGridRowIn.model_validate(
        _fila_realizado_a_contra(
            act_id=act_id,
            ot=ot_num,
            fecha=fecha,
            insp1=insp1_nombre,
            insp2=insp2_nombre,
        )
    )
    actualizar_actuacion(act_id, map_actuacion_row(row_contra))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    item_db = db.session.get(RutaItem, item_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.inspeccion is None
    assert item_db is not None
    assert item_db.estado_ejecucion == "NO_REALIZADO"
    assert item_db.estado_ruta_item == "FINALIZADO"
    assert item_db.motivo_no_realizado == "LOCAL_CERRADO"
    assert ini_db is not None
    assert ini_db.estado_iniciador == "PENDIENTE"
    planif = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id in planif


def test_realizado_a_contra_con_actas_rechazado(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _ruta_borrador_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    from app.models import Inspector

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    insp1_nombre = inspectores[0].nombre
    insp2_nombre = inspectores[1].nombre

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"tipo_actuacion": "INSPECCION", "acta_inspeccion_num": f"{random.randint(1000, 99999)}"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    row_contra = ActuacionGridRowIn.model_validate(
        _fila_realizado_a_contra(
            act_id=act_id,
            ot=ot_num,
            fecha=fecha,
            insp1=insp1_nombre,
            insp2=insp2_nombre,
        )
    )
    with pytest.raises(ValueError, match="quitar las actas"):
        actualizar_actuacion(act_id, map_actuacion_row(row_contra))


def test_verificar_si_a_no_con_actas_a_quitar_transaccional(app_ctx) -> None:
    item, act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
            }
        ),
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_id = int(act.id)
    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None and act_db.inspeccion is not None

    corregir_cierre_oficio(
        act_id,
        CorregirCierreOficioIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": False,
                "contraproducencia": None,
                "actas_a_quitar": ["INSPECCION"],
            }
        ),
    )
    db.session.expunge_all()
    act_corr = db.session.get(Actuaciones, act_id)
    assert act_corr is not None
    assert act_corr.realizo_nueva_inspeccion is False
    assert act_corr.contraproducencia is None
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None


def test_verificar_si_a_contra_con_actas_a_quitar_reencola(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
            }
        ),
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_id = int(act.id)
    ini_id = int(ini.id)
    item_id = int(item.id)

    corregir_cierre_oficio(
        act_id,
        CorregirCierreOficioIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": None,
                "contraproducencia": "LOCAL CERRADO",
                "actas_a_quitar": ["INSPECCION"],
            }
        ),
    )
    db.session.expunge_all()

    act_corr = db.session.get(Actuaciones, act_id)
    item_db = db.session.get(RutaItem, item_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert act_corr is not None
    assert act_corr.contraproducencia == "LOCAL CERRADO"
    assert act_corr.realizo_nueva_inspeccion is None
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None
    assert item_db is not None
    assert item_db.estado_ejecucion == "NO_REALIZADO"
    assert ini_db is not None
    assert ini_db.estado_iniciador == "PENDIENTE"
    planif = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id in planif


def test_verificar_actas_a_quitar_rollback_si_transicion_invalida(app_ctx) -> None:
    item, act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
            }
        ),
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_id = int(act.id)

    with pytest.raises(ValueError, match="no pueden informarse simultáneamente"):
        corregir_cierre_oficio(
            act_id,
            CorregirCierreOficioIn.model_validate(
                {
                    "tipo_actuacion": "VERIFICAR E INFORMAR",
                    "realizo_nueva_inspeccion": True,
                    "contraproducencia": "LOCAL CERRADO",
                    "actas_a_quitar": ["INSPECCION"],
                }
            ),
        )

    db.session.expunge_all()
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is not None
    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None and act_db.realizo_nueva_inspeccion is True


def _cerrar_realizado_y_volver_a_contra(
    *,
    item_id: int,
    act_id: int,
    ini_id: int,
    user_id: int,
    tipo_actuacion: str,
    insp1: str,
    insp2: str,
    contra: str = "LOCAL CERRADO",
    omit_domicilio_fields: bool = False,
    notificacion_previa_num: str | None = None,
) -> None:
    """Helper: contra inicial → realizado con acta → quitar acta → contra (reencolado)."""
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"
    dom = act.domicilio
    calle = (dom.calle if dom else None) or "San Martín"
    numero = (dom.numero if dom else None) or "100"
    rubro_nombre = dom.rubro.nombre if dom and dom.rubro else "Bar"
    doc_nro = dom.contribuyente.documento if dom and dom.contribuyente else "30123456"
    contrib_apellido = dom.contribuyente.apellido if dom and dom.contribuyente else "Titular"
    contrib_nombre = dom.contribuyente.nombre if dom and dom.contribuyente else "Prueba"

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"tipo_actuacion": tipo_actuacion, "contraproducencia": contra}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    acta_num = f"{random.randint(100000, 999999):06d}"
    row_limpia_data: dict = {
        "id": act_id,
        "orden_trabajo_numero": ot_num,
        "fecha_actuacion": fecha,
        "tipo_actuacion": tipo_actuacion,
        "inspector1": insp1,
        "inspector2": insp2,
        "acta_inspeccion_num": acta_num,
        "limpiar_contraproducencia": True,
        "contraproducencia": None,
    }
    if not omit_domicilio_fields:
        row_limpia_data.update(
            {
                "calle": calle,
                "numero": numero,
                "rubro_nombre": rubro_nombre,
                "doc_nro": doc_nro,
                "contrib_apellido": contrib_apellido,
                "contrib_nombre": contrib_nombre,
            }
        )
    if notificacion_previa_num:
        row_limpia_data["notificacion_previa_num"] = notificacion_previa_num
    row_limpia = ActuacionGridRowIn.model_validate(row_limpia_data)
    actualizar_actuacion(act_id, map_actuacion_row(row_limpia))
    db.session.expunge_all()

    ini_mid = db.session.get(IniciadorRuta, ini_id)
    assert ini_mid is not None and ini_mid.estado_iniciador == "CUMPLIDO"
    planif_mid = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id not in planif_mid

    quitar_acta_canal_actas(act_id, "INSPECCION")
    db.session.expunge_all()

    row_contra = ActuacionGridRowIn.model_validate(
        _fila_realizado_a_contra(
            act_id=act_id,
            ot=ot_num,
            fecha=fecha,
            insp1=insp1,
            insp2=insp2,
            calle=calle,
            numero=numero,
            rubro_nombre=rubro_nombre,
            doc_nro=doc_nro,
            contrib_apellido=contrib_apellido,
            contrib_nombre=contrib_nombre,
            tipo_actuacion=tipo_actuacion,
            include_domicilio=not omit_domicilio_fields,
        )
    )
    if contra != "LOCAL CERRADO":
        row_data = _fila_realizado_a_contra(
            act_id=act_id,
            ot=ot_num,
            fecha=fecha,
            insp1=insp1,
            insp2=insp2,
            calle=calle,
            numero=numero,
            rubro_nombre=rubro_nombre,
            doc_nro=doc_nro,
            contrib_apellido=contrib_apellido,
            contrib_nombre=contrib_nombre,
            tipo_actuacion=tipo_actuacion,
            include_domicilio=not omit_domicilio_fields,
        )
        row_data["contraproducencia"] = contra
        row_contra = ActuacionGridRowIn.model_validate(row_data)

    actualizar_actuacion(act_id, map_actuacion_row(row_contra))
    db.session.expunge_all()


def test_relevamiento_realizado_a_contra_reencola_pool(app_ctx) -> None:
    """Relevamiento: REALIZADO → LOCAL CERRADO vuelve al pool."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _ruta_borrador_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)

    from app.models import Inspector

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")

    _cerrar_realizado_y_volver_a_contra(
        item_id=item_id,
        act_id=act_id,
        ini_id=ini_id,
        user_id=user_id,
        tipo_actuacion="INSPECCION",
        insp1=inspectores[0].nombre,
        insp2=inspectores[1].nombre,
    )

    act_db = db.session.get(Actuaciones, act_id)
    item_db = db.session.get(RutaItem, item_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert act_db is not None and act_db.contraproducencia == "LOCAL CERRADO"
    assert item_db is not None and item_db.estado_ejecucion == "NO_REALIZADO"
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    planif = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id in planif


def test_reinspeccion_notificacion_realizado_a_contra_reencola_pool(app_ctx) -> None:
    """Reinspección Notificación: REALIZADO → LOCAL CERRADO vuelve al pool."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u, noti = _mk_reinspeccion_notificacion_item()
    if act.orden_trabajo is not None:
        act.orden_trabajo.numero_acta = f"{random.randint(100000, 999999):06d}"
    noti.numero_acta = f"{random.randint(100000, 999999):06d}"
    db.session.commit()

    from app.models import Inspector

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")

    _cerrar_realizado_y_volver_a_contra(
        item_id=int(item.id),
        act_id=int(act.id),
        ini_id=int(ini.id),
        user_id=int(u.id),
        tipo_actuacion="REINSPECCION",
        insp1=inspectores[0].nombre,
        insp2=inspectores[1].nombre,
        omit_domicilio_fields=True,
        notificacion_previa_num=noti.numero_acta,
    )

    act_db = db.session.get(Actuaciones, act.id)
    item_db = db.session.get(RutaItem, item.id)
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert act_db is not None and act_db.contraproducencia == "LOCAL CERRADO"
    assert item_db is not None and item_db.estado_ejecucion == "NO_REALIZADO"
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    planif = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini.id in planif


def test_cambio_entre_contras_actualiza_motivo_sin_duplicar_reencolado(app_ctx) -> None:
    """Contra A → Contra B mantiene iniciador PENDIENTE y actualiza motivo_no_realizado."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    _ensure_catalog_contraproducencia("CLIMA")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _ruta_borrador_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)

    from app.models import Inspector

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    insp1 = inspectores[0].nombre
    insp2 = inspectores[1].nombre

    _cerrar_realizado_y_volver_a_contra(
        item_id=item_id,
        act_id=act_id,
        ini_id=ini_id,
        user_id=user_id,
        tipo_actuacion="INSPECCION",
        insp1=insp1,
        insp2=insp2,
        contra="LOCAL CERRADO",
    )

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    row_cli = ActuacionGridRowIn.model_validate(
        {
            **_fila_realizado_a_contra(
                act_id=act_id, ot=ot_num, fecha=fecha, insp1=insp1, insp2=insp2
            ),
            "contraproducencia": "CLIMA",
        }
    )
    actualizar_actuacion(act_id, map_actuacion_row(row_cli))
    db.session.expunge_all()

    item_db = db.session.get(RutaItem, item_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None and act_db.contraproducencia == "CLIMA"
    assert item_db is not None and item_db.motivo_no_realizado == "INCLEMENCIA_TIEMPO"
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    planif = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id in planif
