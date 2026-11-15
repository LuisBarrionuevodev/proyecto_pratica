"""V1.1-ESTABLECIMIENTOS-VINCULACION-UX.1 — contrato estructurado de DOCUMENTO_AJENO."""

from __future__ import annotations

from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
    CorreccionEstablecimientoIn,
)
from app.domains.establecimientos.services.correccion_establecimiento_apply_service import (
    aplicar_correccion_establecimiento,
)
from app.domains.establecimientos.services.correccion_establecimiento_preview_service import (
    preview_correccion_establecimiento,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
)
from app.models import User
from tests.test_correccion_establecimiento_edicion_1 import _contrib, _dom, _eo, _user


def _body_doc(documento: str, *, confirmado: bool = False) -> CorreccionEstablecimientoIn:
    payload = {"contribuyente": {"documento": documento}}
    if confirmado:
        payload["confirmado"] = True
    return CorreccionEstablecimientoIn.model_validate(payload)


def test_preview_documento_ajeno_unico_ofrece_vinculacion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Destino", nombre="Unico")
    origen = _contrib(apellido="Origen", nombre="Ficha")
    d = _dom(origen)
    eo = _eo(d, actor)
    prev_doc = origen.documento
    db.session.commit()

    prev = preview_correccion_establecimiento(eo.id, _body_doc(dest.documento), actor=actor)
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "DOCUMENTO_AJENO"
    assert prev["conflicto"]["ofrece_vinculacion"] is True
    db.session.refresh(d)
    db.session.refresh(origen)
    assert d.contribuyente_id == origen.id
    assert origen.documento == prev_doc


def test_preview_documento_duplicado_normalizado_no_ofrece(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    digits = f"{int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000}"
    doc_dot = f"20.{digits}"
    doc_plain = f"20{digits}"
    assert len(doc_dot) == 11
    _contrib(doc=doc_dot)
    _contrib(doc=doc_plain)
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()

    prev = preview_correccion_establecimiento(eo.id, _body_doc(doc_plain), actor=actor)
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "DOCUMENTO_AMBIGUO"
    assert prev["conflicto"]["ofrece_vinculacion"] is False
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id


def test_preview_documento_propio_no_ofrece_vinculacion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Mismo")
    d = _dom(c)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate(
            {"contribuyente": {"documento": c.documento, "apellido": "MismoNuevo"}}
        ),
        actor=actor,
    )
    assert prev["puede_aplicar"] is True
    assert prev.get("conflicto") in (None, {})
    assert (prev.get("conflicto") or {}).get("ofrece_vinculacion") is not True


def test_preview_documento_nuevo_libre_no_ofrece(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    nuevo = str(int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000)
    db.session.commit()
    prev = preview_correccion_establecimiento(eo.id, _body_doc(nuevo), actor=actor)
    assert prev["puede_aplicar"] is True
    assert prev.get("conflicto") in (None, {})
    assert prev["fingerprint"]
    assert prev["contribuyente"]["cambia_documento_identidad"] is True
    assert (prev.get("conflicto") or {}).get("ofrece_vinculacion") is not True


def test_apply_correccion_documento_ajeno_sigue_sin_reasignar(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_correccion_establecimiento(
            eo.id, _body_doc(dest.documento, confirmado=True), actor=actor
        )
    assert ei.value.codigo == "DOCUMENTO_AJENO"
    assert ei.value.extra.get("ofrece_vinculacion") is True
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id


def test_http_preview_ofrece_vinculacion_y_relevador_403(client, auth_headers, app, service_actor) -> None:
    r = client.post(
        "/establecimientos-operativos/1/correcciones/preview",
        json={"contribuyente": {"documento": "20111222333"}},
    )
    assert r.status_code == 401
    with app.app_context():
        try:
            actor = db.session.get(User, service_actor)
            assert actor is not None
            dest = _contrib(apellido="HttpUxDest")
            origen = _contrib(apellido="HttpUxOrig")
            d = _dom(origen)
            eo = _eo(d, actor)
            rel = _user(role="relevador")
            db.session.commit()
            eid = int(eo.id)
            dest_doc = dest.documento
            rel_token = create_access_token(identity=str(rel.id))

            denied = client.post(
                f"/establecimientos-operativos/{eid}/correcciones/preview",
                json={"contribuyente": {"documento": dest_doc}},
                headers={"Authorization": f"Bearer {rel_token}", "Content-Type": "application/json"},
            )
            assert denied.status_code == 403

            prev = client.post(
                f"/establecimientos-operativos/{eid}/correcciones/preview",
                json={"contribuyente": {"documento": dest_doc}},
                headers=auth_headers,
            )
            assert prev.status_code == 200, prev.get_json()
            body = prev.get_json()
            assert body["puede_aplicar"] is False
            assert body["conflicto"]["codigo"] == "DOCUMENTO_AJENO"
            assert body["conflicto"]["ofrece_vinculacion"] is True
            db.session.refresh(d)
            assert d.contribuyente_id == origen.id
        finally:
            db.session.rollback()
