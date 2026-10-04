"""HOTFIX V1.1-ACTA-SEGUIMIENTO.1C — detalle autorizado vs listado."""

from __future__ import annotations

from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.models import Actuaciones
from tests.test_acta_seguimiento_gestion_v1_1b import (
    _cerrar_relevamiento_sin_carnet,
    _put_gestion,
)
from tests.test_acta_seguimiento_v1_1 import (
    _fecha_ruta_aislada_mismo_anio,
    _mk_iniciador_reinspeccion_notificacion,
    _payload_reinspeccion_inspeccion,
    _unique_ot,
)
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401
from tests.test_ruta_publicar_orden_trabajo_pr11_1 import _setup_borrador_con_iniciador
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import RutaItem


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def test_get_gestion_relevamiento_devuelve_telefono_listado_no(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    tel = "381 555-1212"
    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet=tel,
    )
    db.session.expire_all()
    act_id = int(act.id)
    headers = _auth_headers(u.id)

    det = client.get(f"/actuaciones/{act_id}/gestion", headers=headers)
    assert det.status_code == 200
    body = det.get_json()
    assert body["ui_policy"]["mostrar_solicitud_carnet_manipulador"] is True
    assert body["seguimiento"]["telefono_contacto_solicitud_carnet"] == tel
    assert body.get("telefono_contacto_solicitud_carnet") is None

    lst = client.get(
        f"/actuaciones?actuacion_id={act_id}&desde=2026-01-01&hasta=2026-12-31",
        headers=headers,
    )
    assert lst.status_code == 200
    items = lst.get_json()["items"]
    assert len(items) == 1
    row = items[0]
    assert row.get("telefono_contacto_solicitud_carnet") is None
    assert "seguimiento" not in row
    assert "ui_policy" not in row


def test_put_actualiza_telefono_y_get_gestion_lo_refleja(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="381 111-0000",
    )
    act_id = int(act.id)
    headers = _auth_headers(u.id)

    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="381 999-7777",
    )

    det = client.get(f"/actuaciones/{act_id}/gestion", headers=headers)
    assert det.status_code == 200
    assert det.get_json()["seguimiento"]["telefono_contacto_solicitud_carnet"] == "381 999-7777"


def test_get_gestion_reinspeccion_devuelve_subsanacion(app, client, app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
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
    act_id = int(act.id)
    headers = _auth_headers(u.id)

    det = client.get(f"/actuaciones/{act_id}/gestion", headers=headers)
    assert det.status_code == 200
    body = det.get_json()
    assert body["ui_policy"]["mostrar_subsanacion_notificacion"] is True
    assert body["seguimiento"]["faltas_notificacion_subsanadas"] is True

    _put_gestion(act, u, faltas_notificacion_subsanadas=False)
    det2 = client.get(f"/actuaciones/{act_id}/gestion", headers=headers)
    assert det2.get_json()["seguimiento"]["faltas_notificacion_subsanadas"] is False


def test_inspector_ajeno_get_gestion_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    headers = _auth_headers(d["user_a"].id)
    resp = client.get(f"/actuaciones/{d['act_b'].id}/gestion", headers=headers)
    assert resp.status_code == 403
    assert "telefono" not in resp.get_data(as_text=True).lower()
