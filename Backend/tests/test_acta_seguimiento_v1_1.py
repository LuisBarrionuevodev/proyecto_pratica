"""V1.1-ACTA-SEGUIMIENTO.1 / 1A — solicitud carnet y subsanación por origen."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Notificacion,
    NotificacionResultadoReinspeccion,
    OrdenTrabajo,
    RutaItem,
    Rubro,
    User,
)
from app.models.solicitud_carnet_manipulador import SolicitudCarnetManipulador
from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _fecha_ruta_aislada_mismo_anio,
    _mk_iniciador_reinspeccion_notificacion,
    _setup_borrador_con_iniciador,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo


def _suf() -> str:
    return uuid4().hex[:8]


def _unique_ot() -> str:
    return uuid4().hex[:6].upper()


def _mk_user() -> User:
    u = User(
        username=f"u_seg_{_suf()}",
        email=f"seg_{_suf()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_relevamiento_item_en_proceso() -> tuple[RutaItem, User, Domicilio]:
    u = _mk_user()
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=f"RubSeg {_suf()}")
        db.session.add(rub)
        db.session.flush()
    dom = Domicilio(calle=f"SegRel {_suf()}", numero="10", rubro_id=rub.id)
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 6, 1),
        anio=2026,
        mes=6,
        domicilio_id=dom.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta, item = _setup_borrador_con_iniciador(ini, actor_user_id=u.id)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    db.session.expire_all()
    item_db = RutaItem.query.get(item.id)
    assert item_db is not None
    return item_db, u, dom


def _mk_denuncia_item_en_proceso() -> tuple[RutaItem, User, Domicilio]:
    u = _mk_user()
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=f"RubSeg {_suf()}")
        db.session.add(rub)
        db.session.flush()
    dom = Domicilio(calle=f"SegDen {_suf()}", numero="11", rubro_id=rub.id)
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="DENUNCIA",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 6, 1),
        anio=2026,
        mes=6,
        domicilio_id=dom.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta, item = _setup_borrador_con_iniciador(ini, actor_user_id=u.id)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    db.session.expire_all()
    item_db = RutaItem.query.get(item.id)
    assert item_db is not None
    return item_db, u, dom


def _payload_relevamiento_inspeccion(
    *,
    acta: str,
    solicita: bool | None = None,
    telefono: str | None = None,
    doc: str = "20123456789",
) -> dict:
    body: dict = {
        "acta_inspeccion_num": acta,
        "doc_nro": doc,
        "contrib_apellido": "Apellido",
        "contrib_nombre": "Nombre",
    }
    if solicita is not None:
        body["solicita_carnet_manipulador"] = solicita
    if telefono is not None:
        body["telefono_contacto_solicitud_carnet"] = telefono
    return body


def _payload_reinspeccion_inspeccion(
    *,
    acta: str,
    subsanadas: bool | None = None,
) -> dict:
    body: dict = {"acta_inspeccion_num": acta}
    if subsanadas is not None:
        body["faltas_notificacion_subsanadas"] = subsanadas
    return body


def test_relevamiento_si_con_telefono_crea_solicitud(app_ctx) -> None:
    item, u, _dom = _mk_relevamiento_item_en_proceso()
    acta = _unique_ot()
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            _payload_relevamiento_inspeccion(
                acta=acta, solicita=True, telefono="351 555-0100"
            )
        ),
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    act = Actuaciones.query.get(item.actuacion_id)
    assert act and act.inspeccion
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.solicita_carnet is True
    assert sol.telefono_contacto == "351 555-0100"
    assert sol.contribuyente_id is not None


def test_relevamiento_si_sin_telefono_422(app_ctx) -> None:
    item, u, _dom = _mk_relevamiento_item_en_proceso()
    with pytest.raises(ValidationError):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                _payload_relevamiento_inspeccion(acta=_unique_ot(), solicita=True)
            ),
            ejecutado_por_user_id=u.id,
        )


def test_relevamiento_no_crea_solicitud_sin_telefono(app_ctx) -> None:
    item, u, _dom = _mk_relevamiento_item_en_proceso()
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            _payload_relevamiento_inspeccion(acta=_unique_ot(), solicita=False)
        ),
        ejecutado_por_user_id=u.id,
    )
    act = Actuaciones.query.get(item.actuacion_id)
    assert act and act.inspeccion
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.solicita_carnet is False
    assert sol.telefono_contacto is None


def test_denuncia_si_con_telefono_crea_solicitud(app_ctx) -> None:
    item, u, _dom = _mk_denuncia_item_en_proceso()
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            _payload_relevamiento_inspeccion(
                acta=_unique_ot(), solicita=True, telefono="351 444-9999"
            )
        ),
        ejecutado_por_user_id=u.id,
    )
    act = Actuaciones.query.get(item.actuacion_id)
    assert act and act.inspeccion
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.solicita_carnet is True
    assert sol.telefono_contacto == "351 444-9999"


def test_denuncia_si_sin_telefono_422(app_ctx) -> None:
    item, u, _dom = _mk_denuncia_item_en_proceso()
    with pytest.raises(ValidationError):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                _payload_relevamiento_inspeccion(acta=_unique_ot(), solicita=True)
            ),
            ejecutado_por_user_id=u.id,
        )


def test_denuncia_no_crea_solicitud_sin_telefono(app_ctx) -> None:
    item, u, _dom = _mk_denuncia_item_en_proceso()
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            _payload_relevamiento_inspeccion(acta=_unique_ot(), solicita=False)
        ),
        ejecutado_por_user_id=u.id,
    )
    act = Actuaciones.query.get(item.actuacion_id)
    assert act and act.inspeccion
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.solicita_carnet is False
    assert sol.telefono_contacto is None


def test_reinspeccion_notificacion_campos_carnet_422(app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ruta, item = _setup_borrador_con_iniciador(ini, actor_user_id=u.id, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    item_db = RutaItem.query.get(item.id)
    assert item_db
    with pytest.raises(ValidationError):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_db.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "acta_inspeccion_num": _unique_ot(),
                    "faltas_notificacion_subsanadas": True,
                    "solicita_carnet_manipulador": True,
                    "telefono_contacto_solicitud_carnet": "123",
                }
            ),
            ejecutado_por_user_id=u.id,
        )


def test_reinspeccion_notificacion_si_crea_resultado(app_ctx) -> None:
    ini, _act_base, noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ruta, item = _setup_borrador_con_iniciador(ini, actor_user_id=u.id, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    item_db = RutaItem.query.get(item.id)
    assert item_db
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_db.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            _payload_reinspeccion_inspeccion(acta=_unique_ot(), subsanadas=True)
        ),
        ejecutado_por_user_id=u.id,
    )
    act = Actuaciones.query.get(item_db.actuacion_id)
    assert act
    res = NotificacionResultadoReinspeccion.query.filter_by(actuacion_id=act.id).one()
    assert res.notificacion_id == noti.id
    assert res.faltas_subsanadas is True


def test_reinspeccion_notificacion_no_crea_resultado_false(app_ctx) -> None:
    ini, _act_base, noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ruta, item = _setup_borrador_con_iniciador(ini, actor_user_id=u.id, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    item_db = RutaItem.query.get(item.id)
    assert item_db
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_db.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            _payload_reinspeccion_inspeccion(acta=_unique_ot(), subsanadas=False)
        ),
        ejecutado_por_user_id=u.id,
    )
    act = Actuaciones.query.get(item_db.actuacion_id)
    assert act
    res = NotificacionResultadoReinspeccion.query.filter_by(actuacion_id=act.id).one()
    assert res.faltas_subsanadas is False


def test_reinspeccion_sin_respuesta_subsanacion_422(app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ruta, item = _setup_borrador_con_iniciador(ini, actor_user_id=u.id, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    item_db = RutaItem.query.get(item.id)
    assert item_db
    with pytest.raises(ValidationError):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_db.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                _payload_reinspeccion_inspeccion(acta=_unique_ot())
            ),
            ejecutado_por_user_id=u.id,
        )


def test_dos_reinspecciones_conservan_dos_resultados(app_ctx) -> None:
    ini, act_base, noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)

    def _cerrar_iniciador(ini_row: IniciadorRuta, subs: bool) -> int:
        ruta, item = _setup_borrador_con_iniciador(
            ini_row, actor_user_id=u.id, fecha_ruta=fecha, numero_ot=_unique_ot()
        )
        publicar_ruta_trabajo(ruta_id=ruta.id)
        item_db = RutaItem.query.get(item.id)
        assert item_db is not None
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_db.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                _payload_reinspeccion_inspeccion(acta=_unique_ot(), subsanadas=subs)
            ),
            ejecutado_por_user_id=u.id,
        )
        act = Actuaciones.query.get(item_db.actuacion_id)
        assert act is not None
        return int(act.id)

    act_id_1 = _cerrar_iniciador(ini, False)
    ini2 = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 6, 2),
        anio=2026,
        mes=6,
        domicilio_id=ini.domicilio_id,
        notificacion_id=noti.id,
        actuacion_id=act_base.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini2)
    db.session.flush()
    act_id_2 = _cerrar_iniciador(ini2, True)

    rows = (
        NotificacionResultadoReinspeccion.query.filter_by(notificacion_id=noti.id)
        .order_by(NotificacionResultadoReinspeccion.id.asc())
        .all()
    )
    assert len(rows) == 2
    by_act = {int(r.actuacion_id): r for r in rows}
    assert by_act[act_id_1].faltas_subsanadas is False
    assert by_act[act_id_2].faltas_subsanadas is True


def test_rechaza_notificacion_id_en_payload(app_ctx) -> None:
    with pytest.raises(ValidationError):
        CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "REINSPECCION",
                "acta_inspeccion_num": "123456",
                "notificacion_id": 99,
            }
        )


def test_rechaza_contribuyente_id_en_payload(app_ctx) -> None:
    with pytest.raises(ValidationError):
        CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": "123456",
                "contribuyente_id": 1,
            }
        )
