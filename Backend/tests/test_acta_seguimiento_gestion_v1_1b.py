"""V1.1-ACTA-SEGUIMIENTO.1B — seguimiento en CRUD Gestión de Actuaciones."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token
from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    build_actuacion_grid_batch_maps,
    build_iniciador_ruta_por_actuacion_id,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.actuaciones_actuacion_inspector_scope import (
    assert_inspector_puede_acceder_actuacion,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.usuarios.security.inspector_scope_policy import InspectorScopeError
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    NotificacionResultadoReinspeccion,
    Rubro,
    RutaItem,
    User,
)
from app.models.solicitud_carnet_manipulador import SolicitudCarnetManipulador
from tests.test_acta_seguimiento_v1_1 import (
    _mk_denuncia_item_en_proceso,
    _mk_relevamiento_item_en_proceso,
    _payload_reinspeccion_inspeccion,
    _payload_relevamiento_inspeccion,
    _unique_ot,
)
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401 — pytest fixture
from tests.test_inspeccion_checklist import _legacy_put_row_dict
from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _fecha_ruta_aislada_mismo_anio,
    _mk_iniciador_reinspeccion_notificacion,
    _setup_borrador_con_iniciador,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from tests.helpers.service_actor import jwt_request_context


def _suf() -> str:
    return uuid4().hex[:8]


def _cerrar_relevamiento_sin_carnet() -> tuple[Actuaciones, User]:
    item, u, _dom = _mk_relevamiento_item_en_proceso()
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            _payload_relevamiento_inspeccion(
                acta=_unique_ot(), solicita=False
            )
        ),
        ejecutado_por_user_id=u.id,
    )
    act = Actuaciones.query.get(item.actuacion_id)
    assert act is not None
    return act, u


def _cerrar_denuncia_sin_carnet() -> tuple[Actuaciones, User]:
    item, u, _dom = _mk_denuncia_item_en_proceso()
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            _payload_relevamiento_inspeccion(
                acta=_unique_ot(), solicita=False
            )
        ),
        ejecutado_por_user_id=u.id,
    )
    act = Actuaciones.query.get(item.actuacion_id)
    assert act is not None
    return act, u


def _put_gestion(act: Actuaciones, u: User, **extra) -> Actuaciones:
    """PUT mínimo: solo campos de seguimiento (evita validación de grilla completa)."""
    return actualizar_actuacion(int(act.id), dict(extra), actor_user_id=u.id)


def test_gestion_relevamiento_crea_solicitud_si_no_existia(app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    sol_prev = SolicitudCarnetManipulador.query.filter_by(
        inspeccion_id=act.inspeccion.id
    ).one()
    db.session.delete(sol_prev)
    db.session.flush()
    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="351 111-2222",
    )
    sol2 = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol2.solicita_carnet is True
    assert sol2.telefono_contacto == "351 111-2222"


def test_gestion_denuncia_crea_solicitud_si_no_existia(app_ctx) -> None:
    act, u = _cerrar_denuncia_sin_carnet()
    sol_prev = SolicitudCarnetManipulador.query.filter_by(
        inspeccion_id=act.inspeccion.id
    ).one()
    db.session.delete(sol_prev)
    db.session.flush()
    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="351 333-4444",
    )
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.solicita_carnet is True


def test_gestion_actualizar_solicitud_deja_auditoria(app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.updated_at is None
    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="351 000-0001",
    )
    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="351 000-0002",
    )
    db.session.expire_all()
    sol2 = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol2.updated_at is not None
    assert sol2.updated_by_user_id == u.id


def test_gestion_carnet_si_sin_telefono_422(app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    with pytest.raises(ValidationError):
        _put_gestion(act, u, solicita_carnet_manipulador=True)


def test_gestion_carnet_no_telefono_null(app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="351 555-1212",
    )
    _put_gestion(act, u, solicita_carnet_manipulador=False)
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.solicita_carnet is False
    assert sol.telefono_contacto is None


def test_gestion_reinspeccion_crea_o_actualiza_resultado_propio(app_ctx) -> None:
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
    _put_gestion(act, u, faltas_notificacion_subsanadas=True)
    res = NotificacionResultadoReinspeccion.query.filter_by(actuacion_id=act.id).one()
    assert res.faltas_subsanadas is True
    assert res.notificacion_id == noti.id


def test_gestion_dos_reinspecciones_no_se_afectan(app_ctx) -> None:
    ini, act_base, noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)

    def _cerrar(ini_row: IniciadorRuta, subs: bool) -> Actuaciones:
        ruta, item = _setup_borrador_con_iniciador(
            ini_row, actor_user_id=u.id, fecha_ruta=fecha, numero_ot=_unique_ot()
        )
        publicar_ruta_trabajo(ruta_id=ruta.id)
        item_db = RutaItem.query.get(item.id)
        assert item_db
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_db.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                _payload_reinspeccion_inspeccion(acta=_unique_ot(), subsanadas=subs)
            ),
            ejecutado_por_user_id=u.id,
        )
        act = Actuaciones.query.get(item_db.actuacion_id)
        assert act
        return act

    act1 = _cerrar(ini, False)
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
    act2 = _cerrar(ini2, True)
    _put_gestion(act1, u, faltas_notificacion_subsanadas=True)
    res1 = NotificacionResultadoReinspeccion.query.filter_by(actuacion_id=act1.id).one()
    res2 = NotificacionResultadoReinspeccion.query.filter_by(actuacion_id=act2.id).one()
    assert res1.faltas_subsanadas is True
    assert res2.faltas_subsanadas is True


def test_gestion_origen_incompatible_422_subsanacion_en_relevamiento(app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    with pytest.raises(ValidationError):
        _put_gestion(act, u, faltas_notificacion_subsanadas=True)


def test_gestion_origen_incompatible_422_carnet_en_reinspeccion(app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ruta, item = _setup_borrador_con_iniciador(ini, actor_user_id=u.id, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    item_db = RutaItem.query.get(item.id)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_db.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            _payload_reinspeccion_inspeccion(acta=_unique_ot(), subsanadas=True)
        ),
        ejecutado_por_user_id=u.id,
    )
    act = Actuaciones.query.get(item_db.actuacion_id)
    assert act
    with pytest.raises(ValidationError):
        _put_gestion(
            act,
            u,
            solicita_carnet_manipulador=True,
            telefono_contacto_solicitud_carnet="123",
        )


def test_grid_listado_no_expone_telefono(app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="351 999-8888",
    )
    db.session.expire_all()
    act = Actuaciones.query.get(act.id)
    ini_map = build_iniciador_ruta_por_actuacion_id([int(act.id)])
    batch = build_actuacion_grid_batch_maps([act], ini_map)
    row = actuacion_to_grid_row(
        act,
        iniciador_desde_ruta=ini_map.get(int(act.id)),
        batch=batch,
        expose_telefono_solicitud_carnet=False,
    )
    assert row.get("solicita_carnet_manipulador") is True
    assert row.get("telefono_contacto_solicitud_carnet") is None


def test_inspector_no_puede_editar_actuacion_ajena(app, scope_fixture) -> None:
    d = scope_fixture
    act_b = d["act_b"]
    with jwt_request_context(app, d["user_a"].id):
        with pytest.raises(InspectorScopeError) as exc:
            assert_inspector_puede_acceder_actuacion(int(act_b.id))
        assert exc.value.status_code == 403


def test_inspector_put_actuacion_ajena_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    act_b = d["act_b"]
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    body = _legacy_put_row_dict(act_b)
    body.pop("tipo_actuacion", None)
    resp = client.put(f"/actuaciones/{act_b.id}", headers=headers, json=body)
    assert resp.status_code == 403
