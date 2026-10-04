"""HOTFIX V1.1-ACTA-SEGUIMIENTO.1E — PUT HTTP persiste seguimiento en Gestión."""

from __future__ import annotations

from flask_jwt_extended import create_access_token

from app.database import db
from tests.test_acta_seguimiento_gestion_1c import _auth_headers
from tests.test_acta_seguimiento_gestion_v1_1b import (
    _cerrar_denuncia_sin_carnet,
    _cerrar_relevamiento_sin_carnet,
)
from tests.test_acta_seguimiento_v1_1 import (
    _fecha_ruta_aislada_mismo_anio,
    _mk_iniciador_reinspeccion_notificacion,
    _payload_reinspeccion_inspeccion,
    _unique_ot,
)
from tests.test_inspeccion_checklist import _legacy_put_row_dict
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_ruta_publicar_orden_trabajo_pr11_1 import _setup_borrador_con_iniciador
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import Actuaciones, RutaItem


def _put_http(client, act: Actuaciones, user_id: int, **extra) -> object:
    """PUT HTTP mínimo válido para canal actas + campos de seguimiento."""
    db.session.expire_all()
    act_reload = Actuaciones.query.get(int(act.id))
    assert act_reload is not None
    body = _legacy_put_row_dict(act_reload, **extra)
    # Gestión: PUT mínimo (como _put_gestion en 1b); evita validación/bloqueos de grilla completa.
    body.pop("tipo_actuacion", None)
    body.pop("rubro_nombre", None)
    insp = act_reload.inspeccion
    if insp is not None and insp.numero_acta:
        num = str(insp.numero_acta).strip()
        if num.isdigit():
            body["acta_inspeccion_num"] = num.zfill(6)
    if act_reload.contraproducencia:
        body["contraproducencia"] = act_reload.contraproducencia
    headers = _auth_headers(user_id)
    return client.put(f"/actuaciones/{int(act_reload.id)}", headers=headers, json=body)


def test_put_http_relevamiento_cambia_telefono_y_get_gestion(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    tel = "381 444-5555"
    resp = _put_http(
        client,
        act,
        u.id,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet=tel,
    )
    assert resp.status_code == 200, resp.get_json()
    det = client.get(f"/actuaciones/{act.id}/gestion", headers=_auth_headers(u.id))
    assert det.status_code == 200
    assert det.get_json()["seguimiento"]["telefono_contacto_solicitud_carnet"] == tel


def test_put_http_denuncia_cambia_telefono(app, client, app_ctx) -> None:
    act, u = _cerrar_denuncia_sin_carnet()
    tel = "381 777-1212"
    resp = _put_http(
        client,
        act,
        u.id,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet=tel,
    )
    assert resp.status_code == 200
    det = client.get(f"/actuaciones/{act.id}/gestion", headers=_auth_headers(u.id))
    assert det.get_json()["seguimiento"]["telefono_contacto_solicitud_carnet"] == tel


def test_put_http_si_a_no_limpia_telefono(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    _put_http(
        client,
        act,
        u.id,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="381 111-0000",
    )
    resp = _put_http(client, act, u.id, solicita_carnet_manipulador=False)
    assert resp.status_code == 200
    det = client.get(f"/actuaciones/{act.id}/gestion", headers=_auth_headers(u.id))
    seg = det.get_json()["seguimiento"]
    assert seg["solicita_carnet_manipulador"] is False
    assert seg["telefono_contacto_solicitud_carnet"] is None


def test_put_http_reinspeccion_cambia_subsanacion(app, client, app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
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
    resp = _put_http(client, act, u.id, faltas_notificacion_subsanadas=True)
    assert resp.status_code == 200, resp.get_json()
    det = client.get(f"/actuaciones/{act.id}/gestion", headers=_auth_headers(u.id))
    assert det.get_json()["seguimiento"]["faltas_notificacion_subsanadas"] is True


def test_put_http_origen_invalido_seguimiento_422(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    resp = _put_http(client, act, u.id, faltas_notificacion_subsanadas=True)
    assert resp.status_code == 422


def test_put_http_inspector_ajeno_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    act_b = d["act_b"]
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    body = _legacy_put_row_dict(
        act_b,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="381 000-0000",
    )
    resp = client.put(f"/actuaciones/{act_b.id}", headers=headers, json=body)
    assert resp.status_code == 403
