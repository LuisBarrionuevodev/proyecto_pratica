"""V1.1-ESTABLECIMIENTOS-CUIT.1 — corrección segura de documento de la misma persona."""

from __future__ import annotations

import threading
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token
from pydantic import ValidationError

from app.database import db
from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
    CorreccionEstablecimientoIn,
)
from app.domains.establecimientos.schemas.vinculacion_establecimiento_in import (
    VinculacionEstablecimientoIn,
)
from app.domains.establecimientos.services.correccion_establecimiento_apply_service import (
    aplicar_correccion_establecimiento,
)
from app.domains.establecimientos.services.correccion_establecimiento_preview_service import (
    preview_correccion_establecimiento,
)
from app.domains.establecimientos.services.correccion_establecimiento_scope_service import (
    MSG_CONFIRMACION_DOCUMENTO,
    MSG_SIN_FINGERPRINT,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_apply_service import (
    aplicar_vinculacion_establecimiento,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_preview_service import (
    preview_vinculacion_establecimiento,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
    CorreccionEstablecimientoError,
    CorreccionEstablecimientoPermisoError,
)
from app.domains.establecimientos.utils.documento_normalizer import normalizar_documento
from app.models import (
    Comprobacion,
    Contribuyente,
    ContribuyenteDocumentoUnico,
    CorreccionEstablecimientoAudit,
    Notificacion,
    User,
)
from tests.helpers.fixture_isolation import unique_ot_numero
from tests.test_correccion_establecimiento_edicion_1 import (
    _act,
    _contrib,
    _dom,
    _eo,
    _geo,
    _user,
)


def _doc() -> str:
    return str(int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000)


def _snapshot(c: Contribuyente) -> tuple:
    return (c.id, c.documento, c.apellido, c.nombre, c.razon_social)


def _preview_apply(eo_id: int, contrib: dict, actor: User):
    prev = preview_correccion_establecimiento(
        eo_id,
        CorreccionEstablecimientoIn.model_validate({"contribuyente": contrib}),
        actor=actor,
    )
    body = CorreccionEstablecimientoIn.model_validate(
        {
            "contribuyente": contrib,
            "confirmado": True,
            "fingerprint": prev.get("fingerprint"),
        }
    )
    out = aplicar_correccion_establecimiento(eo_id, body, actor=actor)
    return prev, out


def test_1_cuit_inexistente_preview_lista_locales_y_aplica_a_todos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Mal", nombre="Cuit")
    d1 = _dom(c, calle=f"Uno{uuid4().hex[:6]}")
    d2 = _dom(c, calle=f"Dos{uuid4().hex[:6]}")
    eo1 = _eo(d1, actor)
    eo2 = _eo(d2, actor)
    nuevo = _doc()
    db.session.commit()

    prev, out = _preview_apply(
        eo1.id,
        {"documento": nuevo, "apellido": "Mal", "nombre": "Cuit"},
        actor,
    )
    assert prev["puede_aplicar"] is True
    assert prev["conflicto"] in (None, {})
    assert prev["fingerprint"]
    assert prev["contribuyente"]["cambia_documento_identidad"] is True
    asociados = prev["contribuyente"]["establecimientos_asociados"]
    assert len(asociados) == 2
    textos = {row["domicilio_texto"] for row in asociados}
    assert any(d1.calle in (t or "") for t in textos)
    assert any(d2.calle in (t or "") for t in textos)
    assert MSG_CONFIRMACION_DOCUMENTO in (prev["contribuyente"]["advertencia"] or "")
    assert out["applied"] is True
    db.session.refresh(c)
    db.session.refresh(d1)
    db.session.refresh(d2)
    assert c.documento == nuevo
    assert d1.contribuyente_id == c.id
    assert d2.contribuyente_id == c.id
    assert Contribuyente.query.filter_by(id=eo2.domicilio.contribuyente_id).first().id == c.id
    assert ContribuyenteDocumentoUnico.query.filter_by(
        documento_normalizado=normalizar_documento(nuevo)
    ).one().contribuyente_id == c.id


def test_2_conserva_vinculos_y_estados(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c, calle=f"Est{uuid4().hex[:6]}")
    eo = _eo(d, actor)
    notif = Notificacion(numero_acta=unique_ot_numero(), anio=2026, mes=3)
    db.session.add(notif)
    db.session.flush()
    comp = Comprobacion(numero_acta=unique_ot_numero(), anio=2026, mes=3)
    db.session.add(comp)
    db.session.flush()
    act = _act(d, tipo="NOTIFICACION")
    act.notificacion_id = notif.id
    act.comprobacion_id = comp.id
    db.session.add(act)
    db.session.flush()
    nuevo = _doc()
    db.session.commit()
    notif_id, comp_id, act_id = int(notif.id), int(comp.id), int(act.id)
    _, out = _preview_apply(eo.id, {"documento": nuevo}, actor)
    assert out["applied"] is True
    db.session.refresh(act)
    db.session.refresh(notif)
    db.session.refresh(comp)
    db.session.refresh(d)
    assert act.id == act_id
    assert act.notificacion_id == notif_id
    assert act.comprobacion_id == comp_id
    assert d.contribuyente_id == c.id


def test_3_nombre_y_cuit_en_preview_y_auditoria(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Viejo", nombre="Nom", doc=_doc())
    d = _dom(c)
    eo = _eo(d, actor)
    doc_viejo = c.documento
    nuevo = _doc()
    db.session.commit()
    prev, out = _preview_apply(
        eo.id,
        {"documento": nuevo, "apellido": "NuevoAp", "nombre": "NuevoNom"},
        actor,
    )
    assert prev["contribuyente"]["actual"]["apellido"] == "Viejo"
    assert prev["contribuyente"]["propuesto"]["apellido"] == "NuevoAp"
    assert prev["contribuyente"]["actual"]["documento"] == doc_viejo
    assert prev["contribuyente"]["propuesto"]["documento"] == nuevo
    assert out["applied"] is True
    audit = db.session.get(CorreccionEstablecimientoAudit, out["audit_id"])
    assert audit is not None
    assert audit.created_by_user_id == actor.id
    assert audit.valores_anteriores["contribuyente"]["apellido"] == "Viejo"
    assert audit.valores_nuevos["contribuyente"]["apellido"] == "NuevoAp"
    assert audit.valores_nuevos["contribuyente"]["documento"] == nuevo
    assert c.id in (
        audit.alcance.get("contribuyente_id"),
        audit.contribuyente_id,
    )


def test_4_formato_equivalente_sigue_valido(app_ctx, service_actor) -> None:
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
    assert prev["puede_aplicar"] is True
    assert prev["contribuyente"]["cambia_documento_identidad"] is False
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


def test_5_cancelar_y_sin_cambios(app_ctx, service_actor) -> None:
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


def test_6_documento_ajeno_unico_ofrece_asociacion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Destino", nombre="Ok")
    origen = _contrib(apellido="Origen", nombre="Ficha")
    dest_antes = _snapshot(dest)
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": dest.documento}}),
        actor=actor,
    )
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "DOCUMENTO_AJENO"
    assert prev["conflicto"]["ofrece_vinculacion"] is True
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_correccion_establecimiento(
            eo.id,
            CorreccionEstablecimientoIn.model_validate(
                {"contribuyente": {"documento": dest.documento}, "confirmado": True}
            ),
            actor=actor,
        )
    assert ei.value.codigo == "DOCUMENTO_AJENO"
    db.session.refresh(dest)
    db.session.refresh(origen)
    assert _snapshot(dest) == dest_antes
    assert origen.documento != dest.documento


def test_7_asociacion_no_toca_otros_locales_ni_destino(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Dest", nombre="Ok")
    origen = _contrib(apellido="Orig", nombre="Ficha")
    dest_antes = _snapshot(dest)
    d_dest = _dom(dest, calle=f"Dest{uuid4().hex[:6]}")
    d_otro_origen = _dom(origen, calle=f"Otro{uuid4().hex[:6]}")
    d_orig = _dom(origen, calle=f"Orig{uuid4().hex[:6]}")
    _eo(d_dest, actor)
    _eo(d_otro_origen, actor)
    eo_orig = _eo(d_orig, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(
        eo_orig.id,
        VinculacionEstablecimientoIn.model_validate({"documento": dest.documento}),
        actor=actor,
    )
    out = aplicar_vinculacion_establecimiento(
        eo_orig.id,
        VinculacionEstablecimientoIn.model_validate(
            {"documento": dest.documento, "fingerprint": prev["fingerprint"], "confirmado": True}
        ),
        actor=actor,
    )
    assert out["applied"] is True
    db.session.refresh(d_orig)
    db.session.refresh(d_otro_origen)
    db.session.refresh(dest)
    assert d_orig.contribuyente_id == dest.id
    assert d_otro_origen.contribuyente_id == origen.id
    assert _snapshot(dest) == dest_antes


def test_8_documento_ambiguo_bloquea(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    digits = f"{int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000}"
    doc_dot = f"20.{digits}"
    plain = f"20{digits}"
    assert len(doc_dot) == 11
    _contrib(doc=doc_dot)
    _contrib(doc=plain)
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": plain}}),
        actor=actor,
    )
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "DOCUMENTO_AMBIGUO"
    assert prev["conflicto"]["ofrece_vinculacion"] is False


def test_9_asociacion_ignora_nombre_escrito_en_correccion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Conservar", nombre="Destino")
    origen = _contrib(apellido="Orig", nombre="Ficha")
    dest_antes = _snapshot(dest)
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(
        eo.id,
        VinculacionEstablecimientoIn.model_validate({"documento": dest.documento}),
        actor=actor,
    )
    aplicar_vinculacion_establecimiento(
        eo.id,
        VinculacionEstablecimientoIn.model_validate(
            {"documento": dest.documento, "fingerprint": prev["fingerprint"], "confirmado": True}
        ),
        actor=actor,
    )
    db.session.refresh(dest)
    assert dest.apellido == "Conservar"
    assert dest.nombre == "Destino"
    assert _snapshot(dest) == dest_antes


def test_10_preview_obsoleta_rechaza(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d1 = _dom(c, calle=f"A{uuid4().hex[:6]}")
    eo = _eo(d1, actor)
    nuevo = _doc()
    db.session.commit()
    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": nuevo}}),
        actor=actor,
    )
    d2 = _dom(c, calle=f"B{uuid4().hex[:6]}")
    _eo(d2, actor)
    db.session.commit()
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_correccion_establecimiento(
            eo.id,
            CorreccionEstablecimientoIn.model_validate(
                {
                    "contribuyente": {"documento": nuevo},
                    "confirmado": True,
                    "fingerprint": prev["fingerprint"],
                }
            ),
            actor=actor,
        )
    assert ei.value.codigo == "PREVIEW_STALE"
    db.session.refresh(c)
    assert c.documento != nuevo


def test_11_concurrencia_mismo_documento_no_duplica(app, service_actor) -> None:
    with app.app_context():
        actor = db.session.get(User, service_actor)
        assert actor is not None
        c1 = _contrib(apellido="Uno")
        c2 = _contrib(apellido="Dos")
        d1 = _dom(c1, calle=f"C1{uuid4().hex[:6]}")
        d2 = _dom(c2, calle=f"C2{uuid4().hex[:6]}")
        eo1 = _eo(d1, actor)
        eo2 = _eo(d2, actor)
        nuevo = _doc()
        db.session.commit()
        actor_id = int(actor.id)
        eo1_id, eo2_id = int(eo1.id), int(eo2.id)
        c1_id, c2_id = int(c1.id), int(c2.id)
        prev1 = preview_correccion_establecimiento(
            eo1_id,
            CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": nuevo}}),
            actor=actor,
        )
        prev2 = preview_correccion_establecimiento(
            eo2_id,
            CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": nuevo}}),
            actor=actor,
        )
        fp1, fp2 = prev1["fingerprint"], prev2["fingerprint"]

    results: list[tuple] = []

    def _run(eo_id: int, fingerprint: str) -> None:
        with app.app_context():
            person = db.session.get(User, actor_id)
            assert person is not None
            try:
                out = aplicar_correccion_establecimiento(
                    eo_id,
                    CorreccionEstablecimientoIn.model_validate(
                        {
                            "contribuyente": {"documento": nuevo},
                            "confirmado": True,
                            "fingerprint": fingerprint,
                        }
                    ),
                    actor=person,
                )
                results.append(("ok", eo_id, out.get("applied")))
            except Exception as exc:
                results.append(("err", eo_id, getattr(exc, "codigo", type(exc).__name__)))

    t1 = threading.Thread(target=_run, args=(eo1_id, fp1))
    t2 = threading.Thread(target=_run, args=(eo2_id, fp2))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    oks = [r for r in results if r[0] == "ok"]
    errs = [r for r in results if r[0] == "err"]
    assert len(results) == 2
    assert len(oks) == 1
    assert len(errs) == 1
    with app.app_context():
        dueños = Contribuyente.query.filter(
            Contribuyente.id.in_([c1_id, c2_id]),
            Contribuyente.deleted_at.is_(None),
        ).all()
        con_nuevo = [x for x in dueños if normalizar_documento(x.documento) == normalizar_documento(nuevo)]
        assert len(con_nuevo) == 1
        assert ContribuyenteDocumentoUnico.query.filter_by(
            documento_normalizado=normalizar_documento(nuevo)
        ).count() == 1


def test_12_request_directo_sin_preview_confirmacion_o_permiso(
    client, auth_headers, app, service_actor
) -> None:
    r = client.post(
        "/establecimientos-operativos/1/correcciones",
        json={"contribuyente": {"documento": "20111222"}, "confirmado": True},
    )
    assert r.status_code == 401
    with app.app_context():
        actor = db.session.get(User, service_actor)
        assert actor is not None
        c = _contrib(apellido="Http")
        d = _dom(c)
        eo = _eo(d, actor)
        rel = _user(role="relevador")
        db.session.commit()
        eid = int(eo.id)
        doc0 = c.documento
        nuevo = _doc()
        rel_token = create_access_token(identity=str(rel.id))

        denied = client.post(
            f"/establecimientos-operativos/{eid}/correcciones",
            json={"contribuyente": {"documento": nuevo}, "confirmado": True},
            headers={"Authorization": f"Bearer {rel_token}", "Content-Type": "application/json"},
        )
        assert denied.status_code == 403

        sin_fp = client.post(
            f"/establecimientos-operativos/{eid}/correcciones",
            json={"contribuyente": {"documento": nuevo}, "confirmado": True},
            headers=auth_headers,
        )
        assert sin_fp.status_code == 400
        assert sin_fp.get_json()["codigo"] == "FALTA_FINGERPRINT"

        sin_conf = client.post(
            f"/establecimientos-operativos/{eid}/correcciones",
            json={"contribuyente": {"documento": nuevo}, "fingerprint": "x" * 64},
            headers=auth_headers,
        )
        assert sin_conf.status_code == 400
        db.session.refresh(c)
        assert c.documento == doc0


def test_13_falla_escritura_rollback(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    nuevo = _doc()
    db.session.commit()
    doc0 = c.documento
    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate({"contribuyente": {"documento": nuevo}}),
        actor=actor,
    )
    with patch.object(db.session, "commit", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            aplicar_correccion_establecimiento(
                eo.id,
                CorreccionEstablecimientoIn.model_validate(
                    {
                        "contribuyente": {"documento": nuevo},
                        "confirmado": True,
                        "fingerprint": prev["fingerprint"],
                    }
                ),
                actor=actor,
            )
    db.session.rollback()
    db.session.refresh(c)
    assert c.documento == doc0
    assert CorreccionEstablecimientoAudit.query.filter_by(establecimiento_operativo_id=eo.id).count() == 0
    assert ContribuyenteDocumentoUnico.query.filter_by(
        documento_normalizado=normalizar_documento(nuevo)
    ).count() == 0


def test_14_limpiar_contribuyente_sigue_rechazado() -> None:
    with pytest.raises(ValidationError):
        CorreccionEstablecimientoIn.model_validate(
            {"limpiar_contribuyente": True, "contribuyente": {"nombre": "A"}}
        )


def test_15_coordenadas_distrito_intactos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c, distrito_id=None)
    geo = _geo(d, lat="-26.1111111", lng="-65.2222222")
    eo = _eo(d, actor)
    nuevo = _doc()
    db.session.commit()
    lat0, lng0 = geo.lat, geo.lng
    distrito0 = d.distrito_id
    _, out = _preview_apply(eo.id, {"documento": nuevo}, actor)
    assert out["applied"] is True
    db.session.refresh(d)
    db.session.refresh(geo)
    assert d.distrito_id == distrito0
    assert Decimal(str(geo.lat)) == Decimal(str(lat0))
    assert Decimal(str(geo.lng)) == Decimal(str(lng0))
    assert out["coordenadas_y_distrito"]["se_recalculan"] is False


def test_relevador_no_aplica_documento_nuevo(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    rel = _user(role="relevador")
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    db.session.commit()
    with pytest.raises(CorreccionEstablecimientoPermisoError):
        aplicar_correccion_establecimiento(
            eo.id,
            CorreccionEstablecimientoIn.model_validate(
                {"contribuyente": {"documento": _doc()}, "confirmado": True, "fingerprint": "a" * 64}
            ),
            actor=rel,
        )


def test_apply_sin_fingerprint_mensaje(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    db.session.commit()
    with pytest.raises(CorreccionEstablecimientoError) as ei:
        aplicar_correccion_establecimiento(
            eo.id,
            CorreccionEstablecimientoIn.model_validate(
                {"contribuyente": {"documento": _doc()}, "confirmado": True}
            ),
            actor=actor,
        )
    assert ei.value.codigo == "FALTA_FINGERPRINT"
    assert MSG_SIN_FINGERPRINT in ei.value.detail
