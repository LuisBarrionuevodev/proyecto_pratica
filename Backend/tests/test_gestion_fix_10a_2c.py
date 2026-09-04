"""GESTIÓN-FIX.10A.2-C — Completar Trabajo: sync domicilio RELEVAMIENTO + DIRECCION INCORRECTA."""

from __future__ import annotations

import random
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_efectivo_para_iniciador,
)
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    get_iniciadores_pendientes_para_ruta,
)
from app.models import Actuaciones, Domicilio, IniciadorRuta, Relevamiento, Rubro, RutaItem, User

from tests.test_gestion_fix_8 import _ensure_catalog_contraproducencia


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _migration_pr72_aplicada() -> bool:
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("relevamiento")}
    return "nombre_fantasia" in cols and "angulo_esquina" in cols


@pytest.fixture
def require_pr72_migration(app_ctx):
    if not _migration_pr72_aplicada():
        pytest.skip("Requiere migración PR7.2 aplicada en BD")


def _setup_relevamiento_en_ruta_antes_cierre() -> tuple[
    int, Actuaciones, Relevamiento, IniciadorRuta, str, str, int, int
]:
    """
    Relevamiento publicado listo para Completar Trabajo.

    Retorna: item_id, act, rel, ini, rub_nombre, doc, dom_a_id, ruta_borrador_id.
    """
    from tests.test_completar_trabajo_copy_on_write_pr7_12c import (
        _crear_relevamiento_san_juan_maipu,
        _setup_ruta_publicada,
    )
    from tests.test_hotfix_reencolado_planificacion import _fecha_ruta_aislada, _uniq_ruta_numero

    rub = Rubro(nombre=_uniq("Fix102cRub"))
    db.session.add(rub)
    db.session.flush()
    rub_nombre = rub.nombre
    rel = _crear_relevamiento_san_juan_maipu(rubro=rub, angulo="NE", fantasia="Local Fix102c")
    ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
    assert ini is not None
    item = _setup_ruta_publicada(ini)
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    doc = str(random.randint(10_000_000, 99_999_999))
    dom_a_id = int(rel.domicilio_id)

    fecha_ruta = _fecha_ruta_aislada(2026)
    fecha_borrador = fecha_ruta + timedelta(days=9)
    from app.models import RutaTrabajo

    ruta_borrador = RutaTrabajo(
        fecha=fecha_borrador,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        created_by_user_id=u.id,
        numero=_uniq_ruta_numero(),
    )
    db.session.add(ruta_borrador)
    db.session.commit()

    item_id = int(item.id)
    rel_id = int(rel.id)
    ini_id = int(ini.id)
    ruta_borrador_id = int(ruta_borrador.id)
    db.session.expunge_all()
    item_db = RutaItem.query.get(item_id)
    assert item_db and item_db.actuacion_id
    act = Actuaciones.query.get(item_db.actuacion_id)
    rel_db = Relevamiento.query.get(rel_id)
    ini_db = IniciadorRuta.query.get(ini_id)
    assert act and rel_db and ini_db
    return item_id, act, rel_db, ini_db, rub_nombre, doc, dom_a_id, ruta_borrador_id


def _cerrar_direccion_incorrecta(
    item_id: int,
    *,
    rubro_nombre: str,
    doc: str,
    nueva_calle: str,
    nuevo_numero: str = "750",
    numero_tipo: str | None = None,
) -> None:
    _ensure_catalog_contraproducencia("DIRECCION INCORRECTA")
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    payload_data: dict = {
            "contraproducencia": "DIRECCION INCORRECTA",
            "tipo_actuacion": "INSPECCION",
            "calle": nueva_calle,
            "numero": nuevo_numero,
            "rubro_nombre": rubro_nombre,
            "doc_nro": doc,
            "contrib_apellido": "Fix102c",
            "contrib_nombre": "Tit",
        }
    if numero_tipo is not None:
        payload_data["numero_tipo"] = numero_tipo
    else:
        payload_data["numero_tipo"] = "NUMERO"
    payload = CompletarTrabajoCierreCompletoIn.model_validate(payload_data)
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )


def test_c1_cierre_sincroniza_act_rel_ini(app_ctx, require_pr72_migration) -> None:
    item_id, act, rel, ini, rub_nombre, doc, dom_a_id, _rb = _setup_relevamiento_en_ruta_antes_cierre()
    act_id = int(act.id)
    rel_id = int(rel.id)
    ini_id = int(ini.id)
    nueva_calle = _uniq("CalleCierreB")

    _cerrar_direccion_incorrecta(item_id, rubro_nombre=rub_nombre, doc=doc, nueva_calle=nueva_calle)

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act_id)
    rel_db = Relevamiento.query.get(rel_id)
    ini_db = IniciadorRuta.query.get(ini_id)
    assert act_db and rel_db and ini_db
    dom_b_id = int(act_db.domicilio_id)
    assert dom_b_id != dom_a_id
    assert int(rel_db.domicilio_id) == dom_b_id
    assert int(ini_db.domicilio_id) == dom_b_id
    assert ini_db.estado_iniciador == "PENDIENTE"
    dom_b = Domicilio.query.get(dom_b_id)
    assert dom_b is not None
    assert dom_b.calle == nueva_calle


def test_c2_resolver_efectivo_devuelve_b(app_ctx, require_pr72_migration) -> None:
    item_id, act, rel, ini, rub_nombre, doc, dom_a_id, _rb = _setup_relevamiento_en_ruta_antes_cierre()
    ini_id = int(ini.id)
    act_id = int(act.id)
    nueva_calle = _uniq("CalleCierreB2")

    _cerrar_direccion_incorrecta(item_id, rubro_nombre=rub_nombre, doc=doc, nueva_calle=nueva_calle)

    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini_id)
    act_db = Actuaciones.query.get(act_id)
    assert ini_db and act_db
    eff = resolve_domicilio_efectivo_para_iniciador(ini_db)
    assert eff.domicilio_id == int(act_db.domicilio_id)
    assert eff.domicilio_id != dom_a_id


def test_c3_persistencia_nueva_sesion(app_ctx, require_pr72_migration) -> None:
    item_id, act, rel, ini, rub_nombre, doc, dom_a_id, _rb = _setup_relevamiento_en_ruta_antes_cierre()
    act_id = int(act.id)
    rel_id = int(rel.id)
    ini_id = int(ini.id)
    nueva_calle = _uniq("CalleCierreB3")

    _cerrar_direccion_incorrecta(item_id, rubro_nombre=rub_nombre, doc=doc, nueva_calle=nueva_calle)
    db.session.commit()
    db.session.remove()

    act_db = Actuaciones.query.get(act_id)
    rel_db = Relevamiento.query.get(rel_id)
    ini_db = IniciadorRuta.query.get(ini_id)
    assert act_db and rel_db and ini_db
    dom_b_id = int(act_db.domicilio_id)
    assert dom_b_id != dom_a_id
    assert int(rel_db.domicilio_id) == dom_b_id
    assert int(ini_db.domicilio_id) == dom_b_id


def test_c4_pool_muestra_domicilio_b(app_ctx, require_pr72_migration) -> None:
    item_id, act, _rel, ini, rub_nombre, doc, _dom_a_id, ruta_borrador_id = (
        _setup_relevamiento_en_ruta_antes_cierre()
    )
    act_id = int(act.id)
    ini_id = int(ini.id)
    nueva_calle = _uniq("PoolCierreB")

    _cerrar_direccion_incorrecta(item_id, rubro_nombre=rub_nombre, doc=doc, nueva_calle=nueva_calle)

    db.session.expunge_all()
    dom_b = Domicilio.query.get(Actuaciones.query.get(act_id).domicilio_id)
    assert dom_b is not None
    if not dom_b.distrito_id:
        pytest.skip("Domicilio sin distrito; pool filtrado por distrito no aplica")

    items, total = get_iniciadores_pendientes_para_ruta(
        ruta_id=ruta_borrador_id,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        distrito=dom_b.distrito_id,
        q=nueva_calle,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=50,
    )
    assert total >= 1
    assert ini_id in {i.id for i in items}
    match = next(i for i in items if i.id == ini_id)
    assert match.calle == nueva_calle


def test_c6_local_cerrado_no_sincroniza_rel(app_ctx, require_pr72_migration) -> None:
    item_id, act, rel, _ini, rub_nombre, doc, dom_a_id, _rb = _setup_relevamiento_en_ruta_antes_cierre()
    rel_id = int(rel.id)
    act_id = int(act.id)
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    rel_db = Relevamiento.query.get(rel_id)
    act_db = Actuaciones.query.get(act_id)
    assert rel_db and act_db
    assert int(rel_db.domicilio_id) == dom_a_id


def test_c7_direccion_incorrecta_sin_cambio_id_no_sincroniza(app_ctx, require_pr72_migration) -> None:
    """Sin cambio real de domicilio_id, el helper de cierre no muta relevamiento."""
    from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
        _sincronizar_domicilio_relevamiento_direccion_incorrecta_en_cierre,
    )

    item_id, act, rel, ini, rub_nombre, doc, dom_a_id, _rb = _setup_relevamiento_en_ruta_antes_cierre()
    rel_id = int(rel.id)
    act_dom_id = int(act.domicilio_id)
    rel_dom_antes = int(rel.domicilio_id)

    aplicado = _sincronizar_domicilio_relevamiento_direccion_incorrecta_en_cierre(
        act,
        ini,
        domicilio_id_anterior=act_dom_id,
        contraproducencia="DIRECCION INCORRECTA",
    )

    assert aplicado is False
    rel_db = Relevamiento.query.get(rel_id)
    assert rel_db is not None
    assert int(rel_db.domicilio_id) == rel_dom_antes
    assert rel_dom_antes == dom_a_id or rel_dom_antes != act_dom_id


def test_c8_complemento_fix_10a_2b_b_a_c(app_ctx, require_pr72_migration) -> None:
    item_id, act, rel, ini, rub_nombre, doc, dom_a_id, _rb = _setup_relevamiento_en_ruta_antes_cierre()
    act_id = int(act.id)
    rel_id = int(rel.id)
    ini_id = int(ini.id)
    calle_b = _uniq("CalleBFix2c")
    calle_c = _uniq("CalleCFix2c")

    _cerrar_direccion_incorrecta(item_id, rubro_nombre=rub_nombre, doc=doc, nueva_calle=calle_b)
    db.session.expunge_all()

    act_db = Actuaciones.query.get(act_id)
    assert act_db is not None
    dom_b_id = int(act_db.domicilio_id)
    assert dom_b_id != dom_a_id

    fecha = act_db.fecha.strftime("%d/%m/%Y") if act_db.fecha else "15/07/2026"
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ):
        actualizar_actuacion(
            act_id,
            {
                "fecha_actuacion": fecha,
                "tipo_actuacion": act_db.tipo or "INSPECCION",
                "rubro_nombre": rub_nombre,
                "contribuyente": {"doc_nro": doc, "apellido": "Fix102c", "nombre": "Tit"},
                "domicilio": {
                    "calle": calle_c,
                    "numero": "901",
                    "numero_tipo": "NUMERO",
                },
                "inspectores": [],
            },
        )

    db.session.expunge_all()
    act_final = Actuaciones.query.get(act_id)
    rel_final = Relevamiento.query.get(rel_id)
    ini_final = IniciadorRuta.query.get(ini_id)
    assert act_final and rel_final and ini_final
    dom_c_id = int(act_final.domicilio_id)
    assert dom_c_id != dom_b_id
    assert int(rel_final.domicilio_id) == dom_c_id
    assert int(ini_final.domicilio_id) == dom_c_id
    eff = resolve_domicilio_efectivo_para_iniciador(ini_final)
    assert eff.domicilio_id == dom_c_id
