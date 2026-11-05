"""P0 V1.1-ACT-IDENTIDAD.1 — preservar contribuyente_id en PUT ordinarios de Gestión."""

from __future__ import annotations

from app.database import db
from app.models import Actuaciones, CatalogTipoActuacion, Contribuyente
from app.models.solicitud_carnet_manipulador import SolicitudCarnetManipulador
from tests.test_acta_seguimiento_gestion_1c import _auth_headers
from tests.test_acta_seguimiento_gestion_v1_1b import _cerrar_relevamiento_sin_carnet
from tests.test_inspeccion_checklist import _legacy_put_row_dict, _resolve_rubro_nombre
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401


def _put_gestion_http(client, act: Actuaciones, user_id: int, **extra) -> object:
    """PUT HTTP con domicilio como el modal, sin identidad salvo que `extra` la mande."""
    db.session.expire_all()
    act_reload = Actuaciones.query.get(int(act.id))
    assert act_reload is not None
    body = _legacy_put_row_dict(act_reload)
    tipo_cat = CatalogTipoActuacion.query.first()
    if tipo_cat is not None:
        body["tipo_actuacion"] = str(tipo_cat.nombre)
    else:
        body.pop("tipo_actuacion", None)
    body["rubro_nombre"] = _resolve_rubro_nombre()
    dom = act_reload.domicilio
    if dom is not None:
        if dom.calle:
            body["calle"] = dom.calle
        if dom.numero:
            body["numero"] = dom.numero
    insp = act_reload.inspeccion
    if insp is not None and insp.numero_acta:
        num = str(insp.numero_acta).strip()
        if num.isdigit():
            body["acta_inspeccion_num"] = num.zfill(6)
    for key in (
        "doc_nro",
        "contrib_apellido",
        "contrib_nombre",
        "razon_social",
        "limpiar_contribuyente",
    ):
        body.pop(key, None)
    body.update(extra)
    headers = _auth_headers(user_id)
    return client.put(f"/actuaciones/{int(act_reload.id)}", headers=headers, json=body)


def _contribuyente_id(act: Actuaciones) -> int | None:
    db.session.refresh(act)
    dom = act.domicilio
    return int(dom.contribuyente_id) if dom is not None and dom.contribuyente_id else None


def test_put_solo_observaciones_conserva_contribuyente(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None

    resp = _put_gestion_http(client, act, u.id, observaciones_ejecucion="nota de visita")
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) == cid
    errors = (resp.get_json() or {}).get("errors") if isinstance(resp.get_json(), dict) else None
    assert not errors or "doc_nro" not in errors


def test_put_solo_rubro_conserva_contribuyente(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None
    rubro = act.domicilio.rubro.nombre if act.domicilio and act.domicilio.rubro else "Bar"

    resp = _put_gestion_http(client, act, u.id, rubro_nombre=rubro)
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) == cid


def test_put_identidad_incompleta_sin_limpiar_no_desvincula(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None

    resp = _put_gestion_http(
        client,
        act,
        u.id,
        doc_nro=None,
        contrib_apellido=None,
        contrib_nombre=None,
        razon_social=None,
    )
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) == cid


def test_put_cambia_solo_apellido_conserva_resto(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None
    contrib = db.session.get(Contribuyente, cid)
    assert contrib is not None
    doc = contrib.documento
    nombre = contrib.nombre

    resp = _put_gestion_http(
        client,
        act,
        u.id,
        doc_nro=doc,
        contrib_apellido="Chávez",
        contrib_nombre=nombre,
        razon_social=contrib.razon_social,
    )
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) == cid
    db.session.expire_all()
    contrib2 = db.session.get(Contribuyente, cid)
    assert contrib2 is not None
    assert contrib2.apellido == "Chávez"
    assert contrib2.nombre == nombre
    assert contrib2.documento == doc


def test_put_sin_cambios_conserva_contribuyente(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None

    resp = _put_gestion_http(client, act, u.id)
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) == cid


def test_put_solo_acta_inspeccion_conserva_contribuyente(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None
    insp = act.inspeccion
    assert insp is not None and insp.numero_acta
    num = str(insp.numero_acta).strip()
    alt = str((int(num) + 1) % 1000000).zfill(6) if num.isdigit() else "000201"

    resp = _put_gestion_http(client, act, u.id, acta_inspeccion_num=alt)
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) == cid


def test_put_solo_carnet_conserva_contribuyente(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None

    resp = _put_gestion_http(
        client,
        act,
        u.id,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="3515551234",
    )
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) == cid


def test_put_limpiar_contribuyente_true_422_y_conserva_vinculo(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None

    resp = _put_gestion_http(client, act, u.id, limpiar_contribuyente=True)
    assert resp.status_code == 422, resp.get_json()
    errors = resp.get_json()["errors"]
    assert "limpiar_contribuyente" in errors
    assert "desvinculación" in errors["limpiar_contribuyente"].lower()
    assert _contribuyente_id(act) == cid


def test_put_solo_flag_limpiar_contribuyente_422_sin_mutar(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None

    resp = client.put(
        f"/actuaciones/{int(act.id)}",
        headers=_auth_headers(u.id),
        json={"limpiar_contribuyente": True},
    )
    assert resp.status_code == 422, resp.get_json()
    errors = resp.get_json()["errors"]
    assert "limpiar_contribuyente" in errors
    assert _contribuyente_id(act) == cid


def test_put_sin_contribuyente_cambios_comunes_200(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    dom = act.domicilio
    assert dom is not None
    dom.contribuyente_id = None
    db.session.flush()
    db.session.commit()
    assert _contribuyente_id(act) is None

    resp = _put_gestion_http(client, act, u.id, observaciones_ejecucion="sin titular")
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) is None


def test_regresion_seguimiento_sin_contribuyente_sin_carnet_no_422(
    app, client, app_ctx
) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.solicita_carnet is False
    act.domicilio.contribuyente_id = None
    db.session.flush()
    db.session.commit()

    resp = _put_gestion_http(client, act, u.id, observaciones_ejecucion="otra")
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json() or {}
    errors = body.get("errors") if isinstance(body, dict) else None
    assert not errors or "solicita_carnet_manipulador" not in errors
    assert not errors or "doc_nro" not in errors
