"""GESTIÓN-FIX.10A.2-B — Sincronización domicilio corregido al pendiente (RELEVAMIENTO + DIRECCION INCORRECTA)."""

from __future__ import annotations

import random
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_efectivo_para_iniciador,
)
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    get_iniciadores_pendientes_para_ruta,
)
from app.models import Actuaciones, Domicilio, IniciadorRuta, Relevamiento, Rubro, RutaItem, User

from tests.test_gestion_fix_5 import _republicar_iniciador_generico
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


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _migration_pr72_aplicada() -> bool:
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("relevamiento")}
    return "nombre_fantasia" in cols and "angulo_esquina" in cols


@pytest.fixture
def require_pr72_migration(app_ctx):
    if not _migration_pr72_aplicada():
        pytest.skip("Requiere migración PR7.2 aplicada en BD")


def _setup_relevamiento_direccion_incorrecta_pendiente(
    *,
    contra: str = "DIRECCION INCORRECTA",
) -> tuple[Actuaciones, Relevamiento, IniciadorRuta, Rubro, str, int, int]:
    """
    Relevamiento publicado, cerrado con contraproducencia reencolable, iniciador PENDIENTE.

    Retorna: act, rel, ini, rub, doc, dom_id_inicial, ruta_borrador_id.
    """
    from tests.test_completar_trabajo_copy_on_write_pr7_12c import (
        _cerrar_item,
        _crear_relevamiento_san_juan_maipu,
        _setup_ruta_publicada,
    )
    from tests.test_hotfix_reencolado_planificacion import _fecha_ruta_aislada, _uniq_ruta_numero

    _ensure_catalog_contraproducencia(contra)
    rub = Rubro(nombre=_uniq("Fix102bRub"))
    db.session.add(rub)
    db.session.flush()
    rel = _crear_relevamiento_san_juan_maipu(rubro=rub, angulo="NE", fantasia="Local Fix102b")
    ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
    assert ini is not None
    item = _setup_ruta_publicada(ini)
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    doc = str(random.randint(10_000_000, 99_999_999))
    dom_id_inicial = int(rel.domicilio_id)
    dom_ini = db.session.get(Domicilio, dom_id_inicial)
    assert dom_ini is not None

    close_payload: dict = {
        "contraproducencia": contra,
        "tipo_actuacion": "INSPECCION",
        "calle": dom_ini.calle,
        "numero": dom_ini.numero,
        "numero_tipo": dom_ini.numero_tipo or "ESQUINA",
        "rubro_nombre": rub.nombre,
        "doc_nro": doc,
        "contrib_apellido": "Fix102b",
        "contrib_nombre": "Tit",
    }
    if contra == "DIRECCION INCORRECTA":
        pass
    else:
        close_payload.pop("calle", None)
        close_payload.pop("numero", None)
        close_payload.pop("numero_tipo", None)

    _cerrar_item(
        item.id,
        close_payload,
        patch_geocode_hook=False,
    )
    db.session.expunge_all()
    item_db = RutaItem.query.get(item.id)
    assert item_db and item_db.actuacion_id
    act = Actuaciones.query.get(item_db.actuacion_id)
    rel_db = Relevamiento.query.get(rel.id)
    ini_db = IniciadorRuta.query.get(ini.id)
    assert act and rel_db and ini_db
    assert ini_db.estado_iniciador == "PENDIENTE"

    fecha_ruta = _fecha_ruta_aislada(2026)
    fecha_borrador = fecha_ruta + timedelta(days=7)
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

    return act, rel_db, ini_db, rub, doc, dom_id_inicial, int(ruta_borrador.id)


def _put_cambio_domicilio(
    act: Actuaciones,
    *,
    rub: Rubro,
    doc: str,
    nueva_calle: str,
    nuevo_numero: str = "501",
) -> None:
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "15/07/2026"
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ):
        actualizar_actuacion(
            int(act.id),
            {
                "fecha_actuacion": fecha,
                "tipo_actuacion": act.tipo or "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc, "apellido": "Fix102b", "nombre": "Tit"},
                "domicilio": {
                    "calle": nueva_calle,
                    "numero": nuevo_numero,
                    "numero_tipo": "NUMERO",
                },
                "inspectores": [],
            },
        )


def test_t1_sincroniza_act_relevamiento_iniciador_tras_put(
    app_ctx, require_pr72_migration
) -> None:
    act, rel, ini, rub, doc, dom_a_id, _rb = _setup_relevamiento_direccion_incorrecta_pendiente()
    act_id = int(act.id)
    rel_id = int(rel.id)
    ini_id = int(ini.id)
    nueva_calle = _uniq("CalleB")

    _put_cambio_domicilio(act, rub=rub, doc=doc, nueva_calle=nueva_calle)

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act_id)
    rel_db = Relevamiento.query.get(rel_id)
    ini_db = IniciadorRuta.query.get(ini_id)
    assert act_db and rel_db and ini_db
    dom_b_id = int(act_db.domicilio_id)
    assert dom_b_id != dom_a_id
    assert int(rel_db.domicilio_id) == dom_b_id
    assert int(ini_db.domicilio_id) == dom_b_id
    dom_b = Domicilio.query.get(dom_b_id)
    assert dom_b is not None
    assert dom_b.calle == nueva_calle


def test_t2_resolver_efectivo_devuelve_domicilio_b(app_ctx, require_pr72_migration) -> None:
    act, rel, ini, rub, doc, dom_a_id, _rb = _setup_relevamiento_direccion_incorrecta_pendiente()
    act_id = int(act.id)
    ini_id = int(ini.id)
    nueva_calle = _uniq("CalleB2")

    _put_cambio_domicilio(act, rub=rub, doc=doc, nueva_calle=nueva_calle)

    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini_id)
    assert ini_db is not None
    eff = resolve_domicilio_efectivo_para_iniciador(ini_db)
    act_db = Actuaciones.query.get(act_id)
    assert act_db is not None
    assert eff.domicilio_id == int(act_db.domicilio_id)
    assert eff.domicilio_id != dom_a_id


def test_t3_persistencia_nueva_sesion(app_ctx, require_pr72_migration) -> None:
    act, rel, ini, rub, doc, dom_a_id, _rb = _setup_relevamiento_direccion_incorrecta_pendiente()
    act_id = int(act.id)
    rel_id = int(rel.id)
    ini_id = int(ini.id)
    nueva_calle = _uniq("CalleB3")

    _put_cambio_domicilio(act, rub=rub, doc=doc, nueva_calle=nueva_calle)
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


def test_t4_pool_muestra_domicilio_b(app_ctx, require_pr72_migration) -> None:
    act, rel, ini, rub, doc, _dom_a_id, ruta_borrador_id = (
        _setup_relevamiento_direccion_incorrecta_pendiente()
    )
    act_id = int(act.id)
    ini_id = int(ini.id)
    nueva_calle = _uniq("PoolCalleB")

    _put_cambio_domicilio(act, rub=rub, doc=doc, nueva_calle=nueva_calle)

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


def test_t6_local_cerrado_no_propaga(app_ctx, require_pr72_migration) -> None:
    act, rel, _ini, rub, doc, dom_a_id, _rb = _setup_relevamiento_direccion_incorrecta_pendiente(
        contra="LOCAL CERRADO"
    )
    rel_id = int(rel.id)
    act_id = int(act.id)
    rel_dom_antes = int(Relevamiento.query.get(rel_id).domicilio_id)
    nueva_calle = _uniq("LcNoProp")

    _put_cambio_domicilio(act, rub=rub, doc=doc, nueva_calle=nueva_calle)

    db.session.expunge_all()
    rel_db = Relevamiento.query.get(rel_id)
    act_db = Actuaciones.query.get(act_id)
    assert rel_db and act_db
    assert int(rel_db.domicilio_id) == rel_dom_antes
    assert int(act_db.domicilio_id) != dom_a_id


def test_t7_sin_cambio_domicilio_no_propaga(app_ctx, require_pr72_migration) -> None:
    act, rel, ini, rub, doc, _dom_a_id, _rb = _setup_relevamiento_direccion_incorrecta_pendiente()
    rel_id = int(rel.id)
    ini_id = int(ini.id)
    act_id = int(act.id)
    rel_dom_antes = int(rel.domicilio_id)
    act_dom_antes = int(act.domicilio_id)
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "15/07/2026"
    acta_nueva = _unique_num()

    actualizar_actuacion(
        act_id,
        {
            "fecha_actuacion": fecha,
            "tipo_actuacion": act.tipo or "INSPECCION",
            "rubro_nombre": rub.nombre,
            "contribuyente": {"doc_nro": doc, "apellido": "Fix102b", "nombre": "Tit"},
            "acta_inspeccion_num": acta_nueva,
            "inspectores": [],
        },
    )

    db.session.expunge_all()
    rel_db = Relevamiento.query.get(rel_id)
    ini_db = IniciadorRuta.query.get(ini_id)
    act_db = Actuaciones.query.get(act_id)
    assert rel_db and ini_db and act_db
    assert int(rel_db.domicilio_id) == rel_dom_antes
    assert int(act_db.domicilio_id) == act_dom_antes


def test_t8_posterior_real_bloquea_edicion(app_ctx, require_pr72_migration) -> None:
    from app.models import Inspector

    act, _rel, ini, rub, doc, _dom_a_id, _rb = _setup_relevamiento_direccion_incorrecta_pendiente()
    act_id = int(act.id)
    user_id = int(ini.created_by_user_id)
    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores")

    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None
    item2 = _republicar_iniciador_generico(ini_db, user_id, date(2099, 6, 1))
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=int(item2.id),
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": _unique_num(),
                "inspectores": [i.nombre for i in inspectores[:2]],
            }
        ),
        ejecutado_por_user_id=user_id,
    )

    with pytest.raises(ValueError, match="intento posterior"):
        _put_cambio_domicilio(
            db.session.get(Actuaciones, act_id),
            rub=rub,
            doc=doc,
            nueva_calle=_uniq("BloqPosterior"),
        )
