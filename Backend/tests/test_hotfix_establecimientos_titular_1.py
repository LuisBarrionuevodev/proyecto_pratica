"""HOTFIX-ESTABLECIMIENTOS-TITULAR.1 — no sobrescribir identidad compartida."""

from __future__ import annotations

from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token
from pydantic import ValidationError

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
from app.domains.establecimientos.services.correccion_establecimiento_scope_service import (
    MSG_CAMBIO_DOCUMENTO,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_apply_service import (
    aplicar_vinculacion_establecimiento,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_preview_service import (
    preview_vinculacion_establecimiento,
)
from app.domains.establecimientos.schemas.vinculacion_establecimiento_in import (
    VinculacionEstablecimientoIn,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
)
from app.models import CorreccionEstablecimientoAudit, User
from tests.test_correccion_establecimiento_edicion_1 import _contrib, _dom, _eo, _user


def _doc() -> str:
    return str(int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000)


def _snapshot(c) -> tuple:
    return (c.id, c.documento, c.apellido, c.nombre, c.razon_social)


def test_1_dos_locales_nombre_y_cuit_ajeno_no_cambia_ninguno(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Otro", nombre="Titular", doc=_doc())
    origen = _contrib(apellido="Original", nombre="Dueño", doc=_doc())
    d1 = _dom(origen, calle=f"LocA{uuid4().hex[:6]}")
    d2 = _dom(origen, calle=f"LocB{uuid4().hex[:6]}")
    eo1 = _eo(d1, actor)
    _eo(d2, actor)
    antes = _snapshot(origen)
    db.session.commit()

    body = CorreccionEstablecimientoIn.model_validate(
        {
            "contribuyente": {
                "apellido": dest.apellido,
                "nombre": dest.nombre,
                "documento": dest.documento,
            },
            "confirmado": True,
        }
    )
    prev = preview_correccion_establecimiento(eo1.id, body, actor=actor)
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "DOCUMENTO_AJENO"
    assert prev["conflicto"]["ofrece_vinculacion"] is True

    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_correccion_establecimiento(eo1.id, body, actor=actor)
    assert ei.value.codigo == "DOCUMENTO_AJENO"
    db.session.refresh(origen)
    db.session.refresh(d1)
    db.session.refresh(d2)
    assert _snapshot(origen) == antes
    assert d1.contribuyente_id == origen.id
    assert d2.contribuyente_id == origen.id
    assert CorreccionEstablecimientoAudit.query.filter_by(establecimiento_operativo_id=eo1.id).count() == 0


def test_2_documento_nuevo_inexistente_bloqueado(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    origen = _contrib(apellido="Solo", nombre="Uno")
    d1 = _dom(origen, calle=f"Uno{uuid4().hex[:6]}")
    d2 = _dom(origen, calle=f"Dos{uuid4().hex[:6]}")
    eo1 = _eo(d1, actor)
    _eo(d2, actor)
    antes = _snapshot(origen)
    nuevo = _doc()
    db.session.commit()

    body = CorreccionEstablecimientoIn.model_validate(
        {
            "contribuyente": {"documento": nuevo, "apellido": "Nuevo", "nombre": "Titular"},
            "confirmado": True,
        }
    )
    prev = preview_correccion_establecimiento(eo1.id, body, actor=actor)
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "CAMBIO_DOCUMENTO"
    assert prev["conflicto"]["ofrece_vinculacion"] is False
    assert "titularidad" in (prev["conflicto"]["detail"] or "").lower()
    assert MSG_CAMBIO_DOCUMENTO in (prev["conflicto"]["detail"] or "")

    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_correccion_establecimiento(eo1.id, body, actor=actor)
    assert ei.value.codigo == "CAMBIO_DOCUMENTO"
    db.session.refresh(origen)
    db.session.refresh(d1)
    db.session.refresh(d2)
    assert _snapshot(origen) == antes
    assert d1.contribuyente_id == origen.id
    assert d2.contribuyente_id == origen.id
    assert CorreccionEstablecimientoAudit.query.filter_by(establecimiento_operativo_id=eo1.id).count() == 0


def test_3_documento_existente_no_sobrescribe_ofrece_asociacion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Destino", nombre="Ok")
    origen = _contrib(apellido="Origen", nombre="Ficha")
    dest_antes = _snapshot(dest)
    origen_antes = _snapshot(origen)
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()

    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": dest.documento}}),
        actor=actor,
    )
    assert prev["conflicto"]["codigo"] == "DOCUMENTO_AJENO"
    assert prev["conflicto"]["ofrece_vinculacion"] is True
    db.session.refresh(dest)
    db.session.refresh(origen)
    assert _snapshot(dest) == dest_antes
    assert _snapshot(origen) == origen_antes


def test_4_solo_nombre_mismo_documento_se_aplica_a_todos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Viejo", nombre="Nom")
    d1 = _dom(c, calle=f"A{uuid4().hex[:6]}")
    d2 = _dom(c, calle=f"B{uuid4().hex[:6]}")
    eo1 = _eo(d1, actor)
    _eo(d2, actor)
    doc = c.documento
    db.session.commit()

    out = aplicar_correccion_establecimiento(
        eo1.id,
        CorreccionEstablecimientoIn.model_validate(
            {"contribuyente": {"apellido": "NuevoAp", "nombre": "NuevoNom"}, "confirmado": True}
        ),
        actor=actor,
    )
    assert out["applied"] is True
    db.session.refresh(c)
    db.session.refresh(d1)
    db.session.refresh(d2)
    assert c.documento == doc
    assert c.apellido == "NuevoAp"
    assert c.nombre == "NuevoNom"
    assert d1.contribuyente_id == c.id
    assert d2.contribuyente_id == c.id


def test_5_separadores_equivalentes_no_son_otro_titular(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(doc="33445566", apellido="Fmt", nombre="Ok")
    d = _dom(c)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": "33.445566"}}),
        actor=actor,
    )
    assert prev.get("conflicto") in (None, {})
    assert prev["puede_aplicar"] is True
    out = aplicar_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate(
            {"contribuyente": {"documento": "33.445566"}, "confirmado": True}
        ),
        actor=actor,
    )
    assert out["applied"] is True
    db.session.refresh(c)
    assert c.documento == "33.445566"
    assert c.apellido == "Fmt"


def test_6_http_directo_apply_rechaza_sin_auditoria_exito(client, auth_headers, app, service_actor) -> None:
    r = client.post(
        "/establecimientos-operativos/1/correcciones",
        json={"contribuyente": {"documento": "20111222"}, "confirmado": True},
    )
    assert r.status_code == 401
    with app.app_context():
        try:
            actor = db.session.get(User, service_actor)
            assert actor is not None
            c = _contrib(apellido="Http")
            d1 = _dom(c, calle=f"H1{uuid4().hex[:6]}")
            d2 = _dom(c, calle=f"H2{uuid4().hex[:6]}")
            eo = _eo(d1, actor)
            _eo(d2, actor)
            rel = _user(role="relevador")
            db.session.commit()
            eid = int(eo.id)
            cid = int(c.id)
            doc0 = c.documento
            rel_token = create_access_token(identity=str(rel.id))
            nuevo = _doc()

            denied = client.post(
                f"/establecimientos-operativos/{eid}/correcciones",
                json={"contribuyente": {"documento": nuevo, "apellido": "X"}, "confirmado": True},
                headers={"Authorization": f"Bearer {rel_token}", "Content-Type": "application/json"},
            )
            assert denied.status_code == 403

            applied = client.post(
                f"/establecimientos-operativos/{eid}/correcciones",
                json={"contribuyente": {"documento": nuevo, "apellido": "X"}, "confirmado": True},
                headers=auth_headers,
            )
            assert applied.status_code == 409, applied.get_json()
            body = applied.get_json()
            assert body["codigo"] == "CAMBIO_DOCUMENTO"
            assert body.get("ofrece_vinculacion") is False
            db.session.refresh(c)
            assert c.documento == doc0
            assert c.apellido == "Http"
            assert CorreccionEstablecimientoAudit.query.filter_by(
                establecimiento_operativo_id=eid, contribuyente_id=cid
            ).count() == 0
        finally:
            db.session.rollback()


def test_7_cancelar_y_sin_cambios_no_tocan_vinculos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Igual", nombre="Mismo")
    d = _dom(c)
    eo = _eo(d, actor)
    antes = _snapshot(c)
    db.session.commit()
    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate(
            {"contribuyente": {"apellido": "Igual", "nombre": "Mismo", "documento": c.documento}}
        ),
        actor=actor,
    )
    assert prev["sin_cambios"] is True
    out = aplicar_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate(
            {
                "contribuyente": {"apellido": "Igual", "nombre": "Mismo", "documento": c.documento},
                "confirmado": True,
            }
        ),
        actor=actor,
    )
    assert out["applied"] is False
    assert out.get("audit_id") is None
    db.session.refresh(c)
    db.session.refresh(d)
    assert _snapshot(c) == antes
    assert d.contribuyente_id == c.id


def test_8_asociacion_explicita_sigue_por_ficha(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Dest", nombre="Ok")
    origen = _contrib(apellido="Orig", nombre="Ficha")
    dest_antes = _snapshot(dest)
    d_dest = _dom(dest, calle=f"Dest{uuid4().hex[:6]}")
    d_orig = _dom(origen, calle=f"Orig{uuid4().hex[:6]}")
    _eo(d_dest, actor)
    eo_orig = _eo(d_orig, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(
        eo_orig.id,
        VinculacionEstablecimientoIn.model_validate({"documento": dest.documento}),
        actor=actor,
    )
    assert prev["puede_aplicar"] is True
    out = aplicar_vinculacion_establecimiento(
        eo_orig.id,
        VinculacionEstablecimientoIn.model_validate(
            {"documento": dest.documento, "fingerprint": prev["fingerprint"], "confirmado": True}
        ),
        actor=actor,
    )
    assert out["applied"] is True
    db.session.refresh(d_orig)
    db.session.refresh(dest)
    assert d_orig.contribuyente_id == dest.id
    assert _snapshot(dest) == dest_antes
    audit = db.session.get(CorreccionEstablecimientoAudit, out["audit_id"])
    assert audit is not None
    assert audit.tipo == "VINCULACION"


def test_9_limpiar_contribuyente_sigue_rechazado() -> None:
    with pytest.raises(ValidationError):
        CorreccionEstablecimientoIn.model_validate(
            {"limpiar_contribuyente": True, "contribuyente": {"nombre": "A"}}
        )


def test_10_preview_mensaje_titularidad_y_relevador_sin_acceso(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    rel = _user(role="relevador")
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": _doc()}}),
        actor=actor,
    )
    detail = (prev["conflicto"] or {}).get("detail") or ""
    assert "Para cambiar el CUIT/DNI necesitamos verificar la titularidad." in detail
    assert "otros establecimientos asociados" in detail
    from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
        CorreccionEstablecimientoPermisoError,
    )

    with pytest.raises(CorreccionEstablecimientoPermisoError):
        aplicar_correccion_establecimiento(
            eo.id,
            CorreccionEstablecimientoIn.model_validate(
                {"contribuyente": {"documento": _doc()}, "confirmado": True}
            ),
            actor=rel,
        )
