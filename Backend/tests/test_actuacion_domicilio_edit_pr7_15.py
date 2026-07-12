"""PR7.15 — Edición de domicilio en CRUD Actuaciones (solo base de relevamiento)."""

from __future__ import annotations

import random
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
    MSG_ACTAS_DOCUMENTALES,
    MSG_REINSPECCION,
    MSG_SOLO_RELEVAMIENTO,
    puede_editar_domicilio_actuacion,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.models import (
    Actuaciones,
    Comprobacion,
    Contribuyente,
    Domicilio,
    Expediente,
    IniciadorRuta,
    Inspector,
    Notificacion,
    OrdenTrabajo,
    Relevamiento,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
from tests.test_hotfix_reinspeccion_notificacion import _mk_reinspeccion_notificacion_item


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _inspector() -> Inspector:
    ins = Inspector.query.first()
    if ins is None:
        pytest.skip("Se requiere inspector en catálogo")
    return ins


def _rubro() -> Rubro:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere rubro en catálogo")
    return rub


def _setup_relevamiento_cerrado_solo_inspeccion() -> tuple[Actuaciones, Relevamiento, RutaItem, User, Rubro, str]:
    """Relevamiento publicado, cerrado con inspección (sin notificación/comprobación)."""
    from tests.test_completar_trabajo_copy_on_write_pr7_12c import (
        _cerrar_item,
        _crear_relevamiento_san_juan_maipu,
        _setup_ruta_publicada,
    )

    rub = Rubro(nombre=_uniq("Pr715Rub"))
    db.session.add(rub)
    db.session.flush()
    rel = _crear_relevamiento_san_juan_maipu(rubro=rub, angulo="NE", fantasia="Local PR715")
    ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
    assert ini is not None
    item = _setup_ruta_publicada(ini)
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    doc = str(random.randint(10_000_000, 99_999_999))
    c = Contribuyente(apellido="Pr715", nombre="Tit", documento=doc)
    db.session.add(c)
    db.session.flush()
    _cerrar_item(
        item.id,
        {
            "calle": "Maipu",
            "numero": "500",
            "numero_tipo": "NUMERO",
            "rubro_nombre": rub.nombre,
            "doc_nro": doc,
            "contrib_apellido": "Pr715",
            "contrib_nombre": "Tit",
            "acta_inspeccion_num": _unique_num(),
        },
        patch_geocode_hook=False,
    )
    db.session.expunge_all()
    item_db = RutaItem.query.get(item.id)
    assert item_db and item_db.actuacion_id
    act = Actuaciones.query.get(item_db.actuacion_id)
    rel_db = Relevamiento.query.get(rel.id)
    assert act and rel_db
    return act, rel_db, item_db, u, rub, doc


def test_puede_editar_relevamiento_base_sin_actas_derivadas(app_ctx) -> None:
    act, _rel, _item, _u, _rub, _doc = _setup_relevamiento_cerrado_solo_inspeccion()
    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is True
    assert motivo is None


def test_presenter_expone_can_edit_domicilio_relevamiento(app_ctx) -> None:
    act, _rel, _item, _u, _rub, _doc = _setup_relevamiento_cerrado_solo_inspeccion()
    row = actuacion_to_grid_row(act)
    assert row["can_edit_domicilio"] is True
    assert row["domicilio_edit_blocked_reason"] is None


def test_editar_domicilio_relevamiento_dispara_geocode_y_no_toca_relevamiento(app_ctx) -> None:
    act, rel, _item, _u, rub, doc = _setup_relevamiento_cerrado_solo_inspeccion()
    rel_id = int(rel.id)
    act_id = int(act.id)
    dom_relev_id = int(rel.domicilio_id)
    nueva_calle = _uniq("CalleCorr")

    with patch(
        "app.domains.actuaciones.services.update_service.on_domicilio_changed"
    ) as geo_mock:
        actualizar_actuacion(
            act_id,
            {
                "fecha_actuacion": act.fecha.strftime("%d/%m/%Y") if act.fecha else "15/07/2026",
                "tipo_actuacion": act.tipo or "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc, "apellido": "Pr715", "nombre": "Tit"},
                "domicilio": {"calle": nueva_calle, "numero": "501", "numero_tipo": "NUMERO"},
                "inspectores": [],
            },
        )
        assert geo_mock.call_count >= 1

    db.session.expunge_all()
    rel_db = Relevamiento.query.get(rel_id)
    act_db = Actuaciones.query.get(act_id)
    assert rel_db is not None and rel_db.domicilio_id == dom_relev_id
    assert act_db is not None
    dom_act = Domicilio.query.get(act_db.domicilio_id)
    assert dom_act is not None
    assert dom_act.calle == nueva_calle
    assert dom_act.numero == "501"


def test_reinspeccion_notificacion_bloquea_edicion_domicilio(app_ctx) -> None:
    item, act, _ini, u, _noti = _mk_reinspeccion_notificacion_item()
    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is False
    assert motivo == MSG_REINSPECCION

    with pytest.raises(ValueError, match="reinspección"):
        actualizar_actuacion(
            act.id,
            {
                "fecha_actuacion": "10/06/2026",
                "tipo_actuacion": "REINSPECCION",
                "rubro_nombre": Rubro.query.first().nombre,
                "contribuyente": {"doc_nro": "30111222", "apellido": "X", "nombre": "Y"},
                "domicilio": {"calle": "Nueva", "numero": "9"},
                "inspectores": [],
                "acta_inspeccion_num": _unique_num(),
            },
        )
    _ = item, u


def test_reinspeccion_oficio_bloquea_edicion_domicilio(app_ctx) -> None:
    item, act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is False
    assert motivo == MSG_REINSPECCION
    _ = item, u


def _user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u is None:
        pytest.skip("Se requiere usuario activo")
    return u


def test_actuacion_con_notificacion_sin_uso_permite_domicilio(app_ctx) -> None:
    """PR7.15e: notificación recién asociada sin iniciador usado permite editar domicilio."""
    act, _rel, _item, _u, rub, doc = _setup_relevamiento_cerrado_solo_inspeccion()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(noti)
    db.session.flush()
    act.notificacion_id = noti.id
    db.session.commit()

    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is True
    assert motivo is None

    with patch(
        "app.domains.actuaciones.services.update_service.on_domicilio_changed"
    ) as geo_mock:
        actualizar_actuacion(
            act.id,
            {
                "fecha_actuacion": act.fecha.strftime("%d/%m/%Y") if act.fecha else "15/07/2026",
                "tipo_actuacion": act.tipo or "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc, "apellido": "Pr715", "nombre": "Tit"},
                "domicilio": {"calle": "Otra", "numero": "10", "numero_tipo": "NUMERO"},
                "inspectores": [],
            },
        )
        assert geo_mock.call_count >= 1


def test_actuacion_con_notificacion_iniciador_pendiente_sin_ruta_permite(app_ctx) -> None:
    """PR7.15e: iniciador REINSPECCION_NOTIFICACION PENDIENTE sin ruta no bloquea domicilio."""
    act, _rel, _item, _u, _rub, _doc = _setup_relevamiento_cerrado_solo_inspeccion()
    u = _user()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(noti)
    db.session.flush()
    act.notificacion_id = noti.id
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 7, 1),
        anio=2026,
        mes=7,
        domicilio_id=act.domicilio_id,
        notificacion_id=noti.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.commit()

    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is True
    assert motivo is None


def test_actuacion_con_notificacion_iniciador_en_uso_bloquea(app_ctx) -> None:
    """PR7.15e: notificación con iniciador en ejecución bloquea domicilio."""
    act, _rel, _item, _u, rub, doc = _setup_relevamiento_cerrado_solo_inspeccion()
    u = _user()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(noti)
    db.session.flush()
    act.notificacion_id = noti.id
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=date(2026, 7, 1),
        anio=2026,
        mes=7,
        domicilio_id=act.domicilio_id,
        notificacion_id=noti.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.commit()

    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is False
    assert motivo == MSG_ACTAS_DOCUMENTALES

    with pytest.raises(ValueError, match="circuito posterior"):
        actualizar_actuacion(
            act.id,
            {
                "fecha_actuacion": act.fecha.strftime("%d/%m/%Y") if act.fecha else "15/07/2026",
                "tipo_actuacion": act.tipo or "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc, "apellido": "Pr715", "nombre": "Tit"},
                "domicilio": {"calle": "Bloqueada", "numero": "99"},
                "inspectores": [],
            },
        )


def test_actuacion_con_comprobacion_sin_expediente_permite_domicilio(app_ctx) -> None:
    """PR7.15e: comprobación recién cargada sin expediente/oficio permite editar domicilio."""
    act, _rel, _item, _u, rub, doc = _setup_relevamiento_cerrado_solo_inspeccion()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=7, motivo="Control")
    db.session.add(comp)
    db.session.flush()
    act.comprobacion_id = comp.id
    db.session.commit()

    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is True
    assert motivo is None


def test_actuacion_con_comprobacion_con_expediente_bloquea(app_ctx) -> None:
    """PR7.15e: comprobación con expediente de envío bloquea domicilio."""
    act, _rel, _item, _u, _rub, _doc = _setup_relevamiento_cerrado_solo_inspeccion()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=7, motivo="Control")
    db.session.add(comp)
    db.session.flush()
    act.comprobacion_id = comp.id
    exp = Expediente(
        numero_expediente="123456",
        fecha_expediente=date(2026, 7, 1),
        anio="2026",
        tipo_expediente="ENVIO_ACTA",
        comprobacion_id=comp.id,
    )
    db.session.add(exp)
    db.session.commit()

    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is False
    assert motivo == MSG_ACTAS_DOCUMENTALES


def test_actuacion_con_comprobacion_iniciador_en_ruta_bloquea(app_ctx) -> None:
    """PR7.15e: comprobación con iniciador derivado en ruta bloquea domicilio."""
    act, _rel, _item, _u, _rub, _doc = _setup_relevamiento_cerrado_solo_inspeccion()
    u = _user()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=7, motivo="Control")
    db.session.add(comp)
    db.session.flush()
    act.comprobacion_id = comp.id
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="PLANIFICADO",
        fecha_origen=date(2026, 7, 1),
        anio=2026,
        mes=7,
        domicilio_id=act.domicilio_id,
        comprobacion_id=comp.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=date(2026, 7, 10),
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
        estado_ruta_item="ASIGNADO",
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.commit()

    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is False
    assert motivo == MSG_ACTAS_DOCUMENTALES


def test_actuacion_directa_crud_permite_editar_domicilio(app_ctx) -> None:
    rub = _rubro()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(ot)
    db.session.flush()
    dom = Domicilio(calle="Mendoza", numero="500", rubro_id=rub.id)
    db.session.add(dom)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 7, 1),
        mes=7,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.commit()

    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is True
    assert motivo is None


def test_editar_calle_y_numero_mendoza_a_catamarca(app_ctx) -> None:
    act, _rel, _item, _u, rub, doc = _setup_relevamiento_cerrado_solo_inspeccion()
    act_id = int(act.id)

    with patch(
        "app.domains.actuaciones.services.update_service.on_domicilio_changed"
    ) as geo_mock:
        actualizar_actuacion(
            act_id,
            {
                "fecha_actuacion": act.fecha.strftime("%d/%m/%Y") if act.fecha else "15/07/2026",
                "tipo_actuacion": act.tipo or "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc, "apellido": "Pr715", "nombre": "Tit"},
                "domicilio": {"calle": "Catamarca", "numero": "500", "numero_tipo": "NUMERO"},
                "inspectores": [],
            },
        )
        assert geo_mock.call_count >= 1

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act_id)
    assert act_db is not None
    dom_act = Domicilio.query.get(act_db.domicilio_id)
    assert dom_act is not None
    assert dom_act.calle == "Catamarca"
    assert dom_act.numero == "500"


def test_actuacion_directa_crud_cambia_calle_y_geocode(app_ctx) -> None:
    rub = _rubro()
    doc = str(random.randint(10_000_000, 99_999_999))
    c = Contribuyente(apellido="Crud", nombre="Dir", documento=doc)
    db.session.add(c)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(ot)
    db.session.flush()
    dom = Domicilio(calle="Mendoza", numero="500", rubro_id=rub.id, contribuyente_id=c.id)
    db.session.add(dom)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 7, 1),
        mes=7,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.commit()
    act_id = int(act.id)

    with patch(
        "app.domains.actuaciones.services.update_service.on_domicilio_changed"
    ) as geo_mock:
        actualizar_actuacion(
            act_id,
            {
                "fecha_actuacion": "01/07/2026",
                "tipo_actuacion": "INSPECCION",
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": doc, "apellido": "Crud", "nombre": "Dir"},
                "domicilio": {"calle": "Catamarca", "numero": "500", "numero_tipo": "NUMERO"},
                "inspectores": [],
            },
        )
        assert geo_mock.call_count >= 1

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act_id)
    dom_act = Domicilio.query.get(act_db.domicilio_id) if act_db else None
    assert dom_act is not None
    assert dom_act.calle == "Catamarca"
    assert dom_act.numero == "500"


def test_actuacion_editable_sin_payload_domicilio_no_falla(app_ctx) -> None:
    """PR7.15c: PUT sin domicilio (sin cambio geo) no debe exigir calle/número."""
    rub = _rubro()
    doc = str(random.randint(10_000_000, 99_999_999))
    c = Contribuyente(apellido="SinDom", nombre="Payload", documento=doc)
    db.session.add(c)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(ot)
    db.session.flush()
    dom = Domicilio(calle="Mendoza", numero="500", rubro_id=rub.id, contribuyente_id=c.id)
    db.session.add(dom)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 7, 1),
        mes=7,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.commit()
    act_id = int(act.id)
    dom_id = int(dom.id)

    actualizar_actuacion(
        act_id,
        {
            "fecha_actuacion": "01/07/2026",
            "tipo_actuacion": "INSPECCION",
            "rubro_nombre": rub.nombre,
            "contribuyente": {"doc_nro": doc, "apellido": "SinDom", "nombre": "Payload"},
            "nombre_local": "Local actualizado",
            "inspectores": [],
        },
    )

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act_id)
    dom_db = Domicilio.query.get(dom_id)
    assert act_db is not None
    assert act_db.nombre_local == "Local actualizado"
    assert dom_db is not None
    assert dom_db.calle == "Mendoza"
    assert dom_db.numero == "500"


def test_grid_row_update_sin_domicilio_geo_no_exige_calle_numero(app_ctx) -> None:
    """PR7.15d: edición con id y tipo sin calle/número en fila no falla validación grilla."""
    from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn

    row = ActuacionGridRowIn.model_validate(
        {
            "id": 99,
            "orden_trabajo_numero": "123456",
            "fecha_actuacion": "2026-07-01",
            "tipo_actuacion": "INSPECCION",
            "rubro_nombre": "Carnicería",
            "doc_nro": "30123456",
            "inspector1": "Inspector A",
            "nombre_local": "Solo nombre local",
        }
    )
    assert row.id == 99
    assert row.calle is None
    assert row.numero is None


def test_actuacion_con_notificacion_sin_uso_permite_editar_otros_campos(app_ctx) -> None:
    """PR7.15d/e: notificación sin uso posterior permite editar domicilio u otros campos."""
    act, _rel, _item, _u, rub, doc = _setup_relevamiento_cerrado_solo_inspeccion()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=7)
    db.session.add(noti)
    db.session.flush()
    act.notificacion_id = noti.id
    db.session.commit()
    act_id = int(act.id)
    dom_id = int(act.domicilio_id)

    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is True
    assert motivo is None

    actualizar_actuacion(
        act_id,
        {
            "fecha_actuacion": act.fecha.strftime("%d/%m/%Y") if act.fecha else "15/07/2026",
            "tipo_actuacion": act.tipo or "INSPECCION",
            "rubro_nombre": rub.nombre,
            "contribuyente": {"doc_nro": doc, "apellido": "Pr715", "nombre": "Tit"},
            "nombre_local": "Local con notificación sin uso",
            "inspectores": [],
        },
    )

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act_id)
    dom_db = Domicilio.query.get(dom_id)
    assert act_db is not None
    assert act_db.nombre_local == "Local con notificación sin uso"
    assert dom_db is not None
    assert dom_db.calle == "Maipu"
