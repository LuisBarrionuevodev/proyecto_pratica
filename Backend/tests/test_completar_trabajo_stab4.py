"""STAB-4: Completar trabajo — NO_HUBO rechazado, tipo iniciador, NO_CUMPLE reencola."""

from __future__ import annotations

import random
from datetime import date
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
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import normalize_contraproducencia
from app.domains.actuaciones.utils.contraproducencia_por_tipo_iniciador import (
    contraproducencia_permitida_en_completar_trabajo,
)
from app.models import (
    Actuaciones,
    CatalogContraproducencia,
    Contribuyente,
    Domicilio,
    IniciadorRuta,
    Oficio,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)


def test_normalize_rechaza_no_hubo() -> None:
    with pytest.raises(ValueError, match="NO_HUBO"):
        normalize_contraproducencia("NO_HUBO")


def test_contraproducencia_por_tipo_reinspeccion_sin_rubro_correctivo() -> None:
    assert contraproducencia_permitida_en_completar_trabajo("REINSPECCION_OFICIO", "LOCAL CERRADO")
    assert contraproducencia_permitida_en_completar_trabajo(
        "REINSPECCION_OFICIO",
        "NO SE RATIFICÓ",
        tipo_actuacion="RATIFICACION DE CLAUSURA",
    )
    assert not contraproducencia_permitida_en_completar_trabajo(
        "REINSPECCION_OFICIO",
        "NO SE RATIFICÓ",
        tipo_actuacion="RATIFICACION DE DECOMISO",
    )
    assert contraproducencia_permitida_en_completar_trabajo(
        "REINSPECCION_OFICIO",
        "NO PAGÓ TODAVÍA EL DECOMISO",
        tipo_actuacion="RATIFICACION DE DECOMISO",
    )
    assert not contraproducencia_permitida_en_completar_trabajo(
        "REINSPECCION_OFICIO", "NO ES EL RUBRO"
    )
    assert not contraproducencia_permitida_en_completar_trabajo(
        "REINSPECCION_NOTIFICACION", "NO SE RATIFICÓ"
    )
    assert not contraproducencia_permitida_en_completar_trabajo("REINSPECCION_OFICIO", "NO_HUBO")


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_user(suf: str) -> User:
    u = User(
        username=f"u_st4_{suf}",
        email=f"st4_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_reinspeccion_oficio_item(suf: str) -> tuple[RutaItem, Actuaciones, IniciadorRuta, User]:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    u = _mk_user(suf)
    doc = str(random.randint(10_000_000, 40_000_000))
    c = Contribuyente(apellido="ST4", nombre="Tit", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(calle=f"St4_{suf}", numero="1", rubro_id=rub.id, contribuyente_id=c.id)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    ofi = Oficio(
        numero_oficio=str(random.randint(1000, 99999)),
        anio=2026,
        causa=f"CAUSA_ST4_{suf}",
    )
    db.session.add(ofi)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 6, 10),
        mes=6,
        anio=2026,
        tipo="REINSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=date(2026, 6, 10),
        anio=2026,
        mes=6,
        domicilio_id=dom.id,
        oficio_id=ofi.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=date(2026, 6, 10),
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item="EN_PROCESO",
        actuacion_id=act.id,
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    db.session.commit()
    return item, act, ini, u


def test_cierre_rechaza_no_hubo_en_completar_trabajo(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    payload = CompletarTrabajoCierreCompletoIn.model_validate({"contraproducencia": "NO_HUBO"})
    with pytest.raises(ValueError, match="NO_HUBO"):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )


def test_no_cumple_reencola_iniciador_a_pendiente(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "NO_CUMPLE",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    act_db = Actuaciones.query.get(act.id)
    item_db = RutaItem.query.get(item.id)
    assert item_db is not None and item_db.estado_ejecucion == "REALIZADO"
    assert act_db is not None and act_db.resultado_cumplimiento_oficio == "NO_CUMPLE"
    assert ini_db is not None
    assert ini_db.estado_iniciador == "PENDIENTE"
    assert ini_db.cerrado_motivo == "OFICIO_NO_CUMPLE"
    assert int(ini_db.prioridad or 0) >= 5


def test_no_cumple_no_mezcla_con_contraproducencia(app_ctx) -> None:
    with pytest.raises(Exception) as exc:
        CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "contraproducencia": "LOCAL CERRADO",
                "resultado_cumplimiento_oficio": "NO_CUMPLE",
            }
        )
    assert "resultado_cumplimiento_oficio" in str(exc.value) or "contraproducencia" in str(exc.value).lower()


def _ensure_catalog_contraproducencia(app, nombre: str) -> None:
    if not CatalogContraproducencia.query.filter_by(nombre=nombre).first():
        db.session.add(CatalogContraproducencia(nombre=nombre))
        db.session.commit()


def test_no_se_ratifico_reencola_iniciador(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
    _ensure_catalog_contraproducencia(app_ctx, "NO SE RATIFICÓ")
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "contraproducencia": "NO SE RATIFICÓ",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    act_db = Actuaciones.query.get(act.id)
    item_db = RutaItem.query.get(item.id)
    assert item_db is not None and item_db.estado_ejecucion == "NO_REALIZADO"
    assert act_db is not None and act_db.contraproducencia == "NO SE RATIFICÓ"
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert int(ini_db.prioridad or 0) >= 5


def test_no_pago_decomiso_reencola_iniciador(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
    _ensure_catalog_contraproducencia(app_ctx, "NO PAGÓ TODAVÍA EL DECOMISO")
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "RATIFICACION DE DECOMISO",
            "contraproducencia": "NO PAGÓ TODAVÍA EL DECOMISO",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    act_db = Actuaciones.query.get(act.id)
    assert act_db is not None and act_db.contraproducencia == "NO PAGÓ TODAVÍA EL DECOMISO"
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
