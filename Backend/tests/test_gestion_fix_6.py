"""GESTIÓN-FIX.6 — Rubro Denuncia, actas Verificar visibles, historial NO_REALIZADO."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import CorregirCierreOficioIn
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
    puede_editar_domicilio_actuacion,
    puede_editar_rubro_actuacion,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.corregir_cierre_oficio_service import corregir_cierre_oficio
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.denuncias.services.denuncias_service import crear_denuncia_con_iniciador
from app.domains.establecimientos.services.historial_actuaciones_establecimiento_service import (
    list_actuaciones_por_establecimiento_operativo,
)
from app.models import Actuaciones, CatalogContraproducencia, IniciadorRuta, Inspeccion, Notificacion, Rubro

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
from tests.test_gestion_fix_3 import _ensure_catalog_contraproducencia
from tests.test_gestion_fix_5 import _republicar_iniciador_generico
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada
from tests.test_rubro_operativo_actuaciones_hotfix import _setup_ruta_y_publicar, _uniq


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


@pytest.fixture
def mock_user_denuncia(monkeypatch):
    from app.models import User

    u = User.query.filter(User.is_active.is_(True)).first()
    if u is None:
        pytest.skip("Se requiere usuario activo")
    monkeypatch.setattr(
        "app.domains.denuncias.services.denuncias_service._get_current_user_id",
        lambda: int(u.id),
    )
    return u


def _mk_denuncia_en_ruta_publicada(suf: str) -> tuple[int, int, int, int]:
    """Retorna item_id, act_id, ini_id, user_id."""
    from app.models import User

    den, ini = crear_denuncia_con_iniciador(
        fecha=date(2026, 8, 20),
        domicilio_id=None,
        calle=_uniq(f"DenFix6_{suf}"),
        numero="100",
        interseccion=None,
        motivo=f"Denuncia FIX6 {suf}",
    )
    db.session.flush()
    items = _setup_ruta_y_publicar([ini.id])
    item = items[0]
    assert item.actuacion_id is not None
    user = User.query.filter(User.is_active.is_(True)).first()
    assert user is not None
    return int(item.id), int(item.actuacion_id), int(ini.id), int(user.id)


def test_denuncia_local_cerrado_can_edit_rubro_true(app_ctx, mock_user_denuncia) -> None:
    """A1 — Denuncia LOCAL CERRADO sin intento posterior: can_edit_rubro."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id = _mk_denuncia_en_ruta_publicada(suf)

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act = db.session.get(Actuaciones, act_id)
    ini = db.session.get(IniciadorRuta, ini_id)
    assert act is not None and ini is not None

    puede_dom, _ = puede_editar_domicilio_actuacion(act, ini)
    puede_rubro, _ = puede_editar_rubro_actuacion(act, ini)
    assert puede_dom is False
    assert puede_rubro is True

    row = actuacion_to_grid_row(act, iniciador_desde_ruta=ini)
    assert row["can_edit_domicilio"] is False
    assert row["can_edit_rubro"] is True


def test_denuncia_put_solo_rubro_persiste(app_ctx, mock_user_denuncia) -> None:
    """A2 — PUT con solo rubro en Denuncia corregible."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id = _mk_denuncia_en_ruta_publicada(suf)

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act = db.session.get(Actuaciones, act_id)
    ini = db.session.get(IniciadorRuta, ini_id)
    assert act is not None and ini is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "20/08/2026"
    from app.models import Inspector

    insp = Inspector.query.first()
    assert insp is not None

    rub = Rubro(nombre=_uniq("RubDenFix6"))
    db.session.add(rub)
    db.session.commit()
    rub_nombre = rub.nombre

    row_in = ActuacionGridRowIn.model_validate(
        {
            "id": act_id,
            "orden_trabajo_numero": ot_num,
            "fecha_actuacion": fecha,
            "tipo_actuacion": "INSPECCION",
            "contraproducencia": "LOCAL CERRADO",
            "rubro_nombre": rub_nombre,
            "inspector1": insp.nombre,
        }
    )
    actualizar_actuacion(act_id, map_actuacion_row(row_in))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert act_db is not None and ini_db is not None
    assert act_db.domicilio is not None
    assert act_db.domicilio.rubro is not None
    assert act_db.domicilio.rubro.nombre == rub_nombre
    row = actuacion_to_grid_row(act_db, iniciador_desde_ruta=ini_db)
    assert row.get("can_edit_rubro") is True


def test_denuncia_intento_posterior_can_edit_rubro_false(app_ctx, mock_user_denuncia) -> None:
    """A3 — Denuncia histórica con intento posterior: rubro bloqueado."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id = _mk_denuncia_en_ruta_publicada(suf)

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
    item2 = _republicar_iniciador_generico(ini_db, user_id, date(2098, 5, 10))
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item2.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act = db.session.get(Actuaciones, act_id)
    ini = db.session.get(IniciadorRuta, ini_id)
    assert act is not None and ini is not None

    puede_rubro, _ = puede_editar_rubro_actuacion(act, ini)
    assert puede_rubro is False

    row = actuacion_to_grid_row(act, iniciador_desde_ruta=ini)
    assert row.get("actuacion_editable") is False
    assert row.get("can_edit_rubro") is False


def test_relevamiento_can_edit_rubro_regression(app_ctx) -> None:
    """A4 — Relevamiento mantiene can_edit_rubro."""
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, _user_id, _rb, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    act = db.session.get(Actuaciones, act_id)
    ini = db.session.get(IniciadorRuta, ini_id)
    assert act is not None and ini is not None

    puede_rubro, _ = puede_editar_rubro_actuacion(act, ini)
    assert puede_rubro is True

    row = actuacion_to_grid_row(act, iniciador_desde_ruta=ini)
    assert row.get("can_edit_rubro") is True


def test_verificar_si_a_contra_con_actas_a_quitar_notificacion(app_ctx) -> None:
    """B — Verificar SI→CONTRA con INSPECCION+NOTIFICACION en actas_a_quitar."""
    from app.models import Motivo

    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    motivo = Motivo.query.first()
    if motivo is None:
        pytest.skip("Se requiere motivo en catálogo")
    motivo_nombre = motivo.nombre

    item, act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    acta_insp = f"{random.randint(1000, 99999)}"
    acta_notif = f"{random.randint(1000, 99999)}"
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": acta_insp,
                "acta_notificacion_num": acta_notif,
                "notificacion_motivo_1": motivo_nombre,
            }
        ),
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_id = int(act.id)

    corregir_cierre_oficio(
        act_id,
        CorregirCierreOficioIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "contraproducencia": "LOCAL CERRADO",
                "realizo_nueva_inspeccion": None,
                "actas_a_quitar": ["INSPECCION", "NOTIFICACION"],
            }
        ),
    )
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.realizo_nueva_inspeccion is None
    assert (act_db.contraproducencia or "").strip().upper() == "LOCAL CERRADO"
    assert Inspeccion.query.filter_by(actuacion_id=act_id).first() is None
    assert act_db.notificacion_id is None


def test_verificar_si_a_no_con_actas_a_quitar_ok(app_ctx) -> None:
    """B — Verificar SI→NO tras quitar actas."""
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
    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.realizo_nueva_inspeccion is False
    assert act_db.contraproducencia is None


def test_local_cerrado_vincula_establecimiento_operativo(app_ctx) -> None:
    """C — NO_REALIZADO recibe establecimiento_operativo_id al cerrar."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _rb, dom_id = _mk_relevamiento_en_ruta_publicada(suf)

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    assert act.establecimiento_operativo_id is not None
    assert act.domicilio_id == dom_id

    acts, total = list_actuaciones_por_establecimiento_operativo(
        int(act.establecimiento_operativo_id),
        page=1,
        page_size=50,
    )
    assert total >= 1
    assert act_id in {int(a.id) for a in acts}


def test_historial_multiintento_tres_actuaciones(app_ctx) -> None:
    """C — FIX.5: A/B LOCAL CERRADO + C REALIZADO en historial (relevamiento)."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    suf = uuid4().hex[:8]
    try:
        item_id, act_a_id, ini_id, user_id, _rb, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    except Exception as exc:
        if "Duplicate entry" in str(exc):
            pytest.skip("Colisión OT en BD compartida")
        raise

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
    item_b = _republicar_iniciador_generico(ini_db, user_id, date(2098, 6, 1))
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_b.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    act_b_id = int(item_b.actuacion_id or 0)
    db.session.expunge_all()

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    item_c = _republicar_iniciador_generico(ini_db, user_id, date(2098, 6, 15))
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_c.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    act_c_id = int(item_c.actuacion_id or 0)
    db.session.expunge_all()

    act_c = db.session.get(Actuaciones, act_c_id)
    assert act_c is not None
    eo_id = act_c.establecimiento_operativo_id
    assert eo_id is not None

    act_a = db.session.get(Actuaciones, act_a_id)
    act_b = db.session.get(Actuaciones, act_b_id)
    assert act_a is not None and act_b is not None
    assert act_a.establecimiento_operativo_id == eo_id
    assert act_b.establecimiento_operativo_id == eo_id

    acts, total = list_actuaciones_por_establecimiento_operativo(int(eo_id), page=1, page_size=50)
    ids = {int(a.id) for a in acts}
    assert total >= 3
    assert {act_a_id, act_b_id, act_c_id}.issubset(ids)
