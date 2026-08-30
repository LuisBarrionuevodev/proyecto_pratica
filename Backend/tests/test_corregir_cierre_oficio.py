"""GESTIÓN-FIX.2C — corrección de cierre por reinspección de oficio desde Actuaciones."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import CorregirCierreOficioIn
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.corregir_cierre_oficio_service import corregir_cierre_oficio
from app.domains.indicadores.services.indicadores_operativos_queries import (
    BUCKET_RATIFICACION_CLAUSURA,
    BUCKET_RATIFICACION_DECOMISO,
    BUCKET_VERIFICAR_INFORMAR,
    bucket_operativo,
)
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    planificable_iniciadores_base_query,
)
from app.models import Actuaciones, CatalogContraproducencia, IniciadorRuta, Inspeccion, RutaItem

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
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


def _cerrar_item(
    item: RutaItem,
    user_id: int,
    payload: dict,
) -> Actuaciones:
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(payload),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    item_db = db.session.get(RutaItem, item.id)
    assert item_db is not None and item_db.actuacion_id is not None
    act = db.session.get(Actuaciones, item_db.actuacion_id)
    assert act is not None
    return act


def _corregir(act: Actuaciones, body: dict) -> Actuaciones:
    act_id = int(act.id)
    payload = CorregirCierreOficioIn.model_validate(body)
    corregir_cierre_oficio(act_id, payload)
    db.session.expunge_all()
    refreshed = db.session.get(Actuaciones, act_id)
    assert refreshed is not None
    return refreshed


@pytest.mark.parametrize(
    ("contra", "tipo_actuacion", "tipo_iniciador_esperado"),
    [
        ("NO SE RATIFICÓ", "RATIFICACION DE CLAUSURA", "RATIFICACION_CLAUSURA_OFICIO"),
        ("NO PAGÓ TODAVÍA EL DECOMISO", "RATIFICACION DE DECOMISO", "RATIFICACION_DECOMISO_OFICIO"),
    ],
)
def test_ratificacion_contra_a_cumple(
    app_ctx,
    contra: str,
    tipo_actuacion: str,
    tipo_iniciador_esperado: str,
) -> None:
    _ensure_catalog_contraproducencia(contra)
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {"tipo_actuacion": tipo_actuacion, "contraproducencia": contra},
    )
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == tipo_iniciador_esperado
    assert ini_db.estado_iniciador == "PENDIENTE"

    act_corr = _corregir(
        act_cerrada,
        {"tipo_actuacion": tipo_actuacion, "resultado_cumplimiento_oficio": "CUMPLE"},
    )
    assert act_corr.contraproducencia is None
    assert act_corr.resultado_cumplimiento_oficio == "CUMPLE"
    assert str(act_corr.tipo) == tipo_actuacion

    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == tipo_iniciador_esperado
    assert ini_db.estado_iniciador == "CUMPLIDO"

    row = actuacion_to_grid_row(act_corr)
    assert row["resultado_cumplimiento_oficio"] == "CUMPLE"
    assert row.get("contraproducencia") in (None, "")


def test_ratificacion_clausura_cumple_a_no_cumple(app_ctx) -> None:
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        },
    )
    ini.tipo_iniciador = "RATIFICACION_CLAUSURA_OFICIO"
    db.session.commit()

    act_corr = _corregir(
        act_cerrada,
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "NO_CUMPLE",
        },
    )
    assert act_corr.resultado_cumplimiento_oficio == "NO_CUMPLE"
    assert act_corr.contraproducencia is None

    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "RATIFICACION_CLAUSURA_OFICIO"
    assert ini_db.estado_iniciador == "PENDIENTE"


def test_ratificacion_cumple_a_contra(app_ctx) -> None:
    _ensure_catalog_contraproducencia("NO SE RATIFICÓ")
    item, _act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        },
    )
    ini.tipo_iniciador = "RATIFICACION_CLAUSURA_OFICIO"
    db.session.commit()

    act_corr = _corregir(
        act_cerrada,
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "contraproducencia": "NO SE RATIFICÓ",
        },
    )
    assert act_corr.contraproducencia == "NO SE RATIFICÓ"
    assert act_corr.resultado_cumplimiento_oficio is None

    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.estado_iniciador == "PENDIENTE"


def test_verificar_cierre_persiste_realizo_nueva_inspeccion(app_ctx) -> None:
    for rni, expected in ((True, True), (False, False)):
        suf = uuid4().hex[:8]
        item2, _a2, _i2, u2 = _mk_reinspeccion_oficio_item(suf)
        payload: dict = {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": rni,
        }
        if rni:
            payload["acta_inspeccion_num"] = f"{random.randint(1000, 99999)}"
        act_cerrada = _cerrar_item(item2, int(u2.id), payload)
        assert act_cerrada.realizo_nueva_inspeccion is expected
        row = actuacion_to_grid_row(act_cerrada)
        assert row.get("realizo_nueva_inspeccion") is expected


def test_verificar_correccion_no_a_si(app_ctx) -> None:
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": False},
    )
    act_corr = _corregir(
        act_cerrada,
        {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": True},
    )
    assert act_corr.realizo_nueva_inspeccion is True


def test_verificar_true_mas_contra_null_limpia_contra_historica(app_ctx) -> None:
    """GESTIÓN-FIX.2C.2: null explícito limpia contra aunque realizo pase a true."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": False,
            "contraproducencia": "LOCAL CERRADO",
        },
    )
    assert act_cerrada.contraproducencia == "LOCAL CERRADO"

    act_corr = _corregir(
        act_cerrada,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "contraproducencia": None,
        },
    )
    assert act_corr.realizo_nueva_inspeccion is True
    assert act_corr.contraproducencia is None


def test_verificar_correccion_si_a_no_sin_actas(app_ctx) -> None:
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
        },
    )
    act_id = int(act_cerrada.id)
    insp = Inspeccion.query.filter_by(actuacion_id=act_id).first()
    if insp:
        db.session.delete(insp)
    db.session.commit()
    db.session.expunge_all()
    act_cerrada = db.session.get(Actuaciones, act_id)
    assert act_cerrada is not None

    act_corr = _corregir(
        act_cerrada,
        {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": False},
    )
    assert act_corr.realizo_nueva_inspeccion is False


def test_verificar_si_a_no_con_actas_rechazado(app_ctx) -> None:
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
        },
    )
    with pytest.raises(ValueError, match="quitar las actas"):
        _corregir(
            act_cerrada,
            {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": False},
        )


def test_clausura_cumple_a_verificar_no(app_ctx) -> None:
    """Clausura CUMPLE → Verificar NO_INSPECCION sincroniza act.tipo e ini.tipo_iniciador."""
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        },
    )
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "RATIFICACION_CLAUSURA_OFICIO"

    act_corr = _corregir(
        act_cerrada,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": False,
            "contraproducencia": None,
        },
    )
    assert str(act_corr.tipo) == "VERIFICAR E INFORMAR"
    assert act_corr.resultado_cumplimiento_oficio is None
    assert act_corr.realizo_nueva_inspeccion is False
    assert act_corr.contraproducencia is None

    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "VERIFICAR_INFORMAR_OFICIO"
    assert ini_db.id == ini.id


def test_clausura_cumple_a_verificar_contra_reencola_pool(app_ctx) -> None:
    """Clausura CUMPLE → Verificar CONTRAPRODUCENCIA: mismo iniciador vuelve al pool."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        },
    )
    ini_id = ini.id
    act_corr = _corregir(
        act_cerrada,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "contraproducencia": "LOCAL CERRADO",
        },
    )
    assert act_corr.contraproducencia == "LOCAL CERRADO"
    assert act_corr.realizo_nueva_inspeccion is None

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    assert ini_db.estado_iniciador == "PENDIENTE"
    planif = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id in planif


@pytest.mark.parametrize(
    ("origen", "destino", "payload", "tipo_ini_esperado"),
    [
        (
            {"tipo_actuacion": "RATIFICACION DE CLAUSURA", "resultado_cumplimiento_oficio": "CUMPLE"},
            "RATIFICACION DE DECOMISO",
            {"tipo_actuacion": "RATIFICACION DE DECOMISO", "resultado_cumplimiento_oficio": "CUMPLE"},
            "RATIFICACION_DECOMISO_OFICIO",
        ),
        (
            {"tipo_actuacion": "RATIFICACION DE DECOMISO", "resultado_cumplimiento_oficio": "CUMPLE"},
            "RATIFICACION DE CLAUSURA",
            {"tipo_actuacion": "RATIFICACION DE CLAUSURA", "resultado_cumplimiento_oficio": "CUMPLE"},
            "RATIFICACION_CLAUSURA_OFICIO",
        ),
        (
            {"tipo_actuacion": "RATIFICACION DE DECOMISO", "resultado_cumplimiento_oficio": "CUMPLE"},
            "VERIFICAR E INFORMAR",
            {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": False},
            "VERIFICAR_INFORMAR_OFICIO",
        ),
        (
            {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": False},
            "RATIFICACION DE CLAUSURA",
            {"tipo_actuacion": "RATIFICACION DE CLAUSURA", "resultado_cumplimiento_oficio": "CUMPLE"},
            "RATIFICACION_CLAUSURA_OFICIO",
        ),
    ],
)
def test_transicion_subtipo_oficio_sync_iniciador(
    app_ctx,
    origen: dict,
    destino: str,
    payload: dict,
    tipo_ini_esperado: str,
) -> None:
    item, _act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(item, int(u.id), origen)
    ini_id = ini.id

    act_corr = _corregir(act_cerrada, payload)
    assert str(act_corr.tipo) == destino

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == tipo_ini_esperado
    assert ini_db.id == ini_id


def test_kpi_bucket_cambia_al_transicionar_clausura_a_verificar(app_ctx) -> None:
    item, _act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        },
    )
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert bucket_operativo(ini_db.tipo_iniciador, str(act_cerrada.tipo)) == BUCKET_RATIFICACION_CLAUSURA

    act_corr = _corregir(
        act_cerrada,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": False,
        },
    )
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert bucket_operativo(ini_db.tipo_iniciador, str(act_corr.tipo)) == BUCKET_VERIFICAR_INFORMAR


def test_verificar_si_a_clausura_sin_quitar_actas_rechazado(app_ctx) -> None:
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
        },
    )
    with pytest.raises(ValueError, match="quitar las actas"):
        _corregir(
            act_cerrada,
            {
                "tipo_actuacion": "RATIFICACION DE CLAUSURA",
                "resultado_cumplimiento_oficio": "CUMPLE",
            },
        )


def test_verificar_si_a_clausura_con_actas_a_quitar_ok(app_ctx) -> None:
    item, _act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
        },
    )
    act_corr = _corregir(
        act_cerrada,
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
            "actas_a_quitar": ["INSPECCION"],
        },
    )
    assert str(act_corr.tipo) == "RATIFICACION DE CLAUSURA"
    assert act_corr.resultado_cumplimiento_oficio == "CUMPLE"
    assert act_corr.realizo_nueva_inspeccion is None
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "RATIFICACION_CLAUSURA_OFICIO"


def test_correccion_rechaza_circuito_notificacion(app_ctx) -> None:
    _item, act, _ini, _u, _noti = _mk_reinspeccion_notificacion_item()
    with pytest.raises(ValueError, match="circuito de reinspección por oficio"):
        _corregir(
            act,
            {
                "tipo_actuacion": act.tipo or "REINSPECCION",
                "resultado_cumplimiento_oficio": "CUMPLE",
            },
        )


def test_kpi_bucket_ratificacion_clausura_tras_correccion(app_ctx) -> None:
    _ensure_catalog_contraproducencia("NO SE RATIFICÓ")
    item, _act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "contraproducencia": "NO SE RATIFICÓ",
        },
    )
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    tipo_ini = ini_db.tipo_iniciador
    b1 = bucket_operativo(tipo_ini, str(act_cerrada.tipo))
    assert b1 == BUCKET_RATIFICACION_CLAUSURA

    act_corr = _corregir(
        act_cerrada,
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        },
    )
    b2 = bucket_operativo(tipo_ini, str(act_corr.tipo))
    assert b2 == BUCKET_RATIFICACION_CLAUSURA


def _cerrar_verificar_contra(suf: str) -> Actuaciones:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    return _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": None,
            "contraproducencia": "LOCAL CERRADO",
        },
    )


def test_verificar_contra_a_no(app_ctx) -> None:
    act = _cerrar_verificar_contra(uuid4().hex[:8])
    assert act.contraproducencia == "LOCAL CERRADO"
    assert act.realizo_nueva_inspeccion is None

    act_corr = _corregir(
        act,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": False,
            "contraproducencia": None,
        },
    )
    assert act_corr.contraproducencia is None
    assert act_corr.realizo_nueva_inspeccion is False


def test_verificar_contra_a_si(app_ctx) -> None:
    act = _cerrar_verificar_contra(uuid4().hex[:8])
    act_corr = _corregir(
        act,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "contraproducencia": None,
        },
    )
    assert act_corr.contraproducencia is None
    assert act_corr.realizo_nueva_inspeccion is True


def test_verificar_no_a_contra(app_ctx) -> None:
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    act = _cerrar_item(
        item,
        int(u.id),
        {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": False},
    )
    act_corr = _corregir(
        act,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": None,
            "contraproducencia": "LOCAL CERRADO",
        },
    )
    assert act_corr.contraproducencia == "LOCAL CERRADO"
    assert act_corr.realizo_nueva_inspeccion is None


def test_verificar_si_a_contra_sin_actas(app_ctx) -> None:
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    act = _cerrar_item(
        item,
        int(u.id),
        {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": True},
    )
    act_corr = _corregir(
        act,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": None,
            "contraproducencia": "LOCAL CERRADO",
        },
    )
    assert act_corr.contraproducencia == "LOCAL CERRADO"
    assert act_corr.realizo_nueva_inspeccion is None


def test_verificar_si_a_contra_con_actas_rechazado(app_ctx) -> None:
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
        },
    )
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    with pytest.raises(ValueError, match="contraproducencia"):
        _corregir(
            act,
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": None,
                "contraproducencia": "LOCAL CERRADO",
            },
        )


def test_verificar_false_a_true(app_ctx) -> None:
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act = _cerrar_item(
        item,
        int(u.id),
        {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": False},
    )
    act_corr = _corregir(
        act,
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": True,
            "contraproducencia": None,
        },
    )
    assert act_corr.realizo_nueva_inspeccion is True
    assert act_corr.contraproducencia is None


def test_verificar_payload_hibrido_rechazado(app_ctx) -> None:
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act = _cerrar_item(
        item,
        int(u.id),
        {"tipo_actuacion": "VERIFICAR E INFORMAR", "realizo_nueva_inspeccion": False},
    )
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    with pytest.raises(ValueError, match="no pueden informarse simultáneamente"):
        _corregir(
            act,
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": False,
                "contraproducencia": "LOCAL CERRADO",
            },
        )
    with pytest.raises(ValueError, match="no pueden informarse simultáneamente"):
        _corregir(
            act,
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "contraproducencia": "LOCAL CERRADO",
            },
        )
