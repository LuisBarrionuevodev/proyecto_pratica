"""V1.1-ESTABLECIMIENTOS-CONTRIBUYENTE.3 — alta atómica y vínculo de ficha."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
    CorreccionEstablecimientoIn,
)
from app.domains.establecimientos.schemas.vinculacion_establecimiento_in import (
    VinculacionEstablecimientoIn,
)
from app.domains.establecimientos.services.contribuyente_documento_unico_service import (
    lock_key_documento,
)
from app.domains.establecimientos.services.historial_actuaciones_establecimiento_service import (
    list_actuaciones_por_establecimiento_operativo,
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
    DomicilioGeocode,
    IniciadorRuta,
    Notificacion,
    Oficio,
    RutaItem,
    RutaTrabajo,
    User,
)
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, unique_ot_numero, uniq_ruta_numero
from tests.test_correccion_establecimiento_edicion_1 import _act, _contrib, _dom, _eo, _geo, _suf, _user


_SERVICES = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "domains"
    / "establecimientos"
    / "services"
)


def _doc() -> str:
    return str(int(uuid4().hex[:8], 16) % 80_000_000 + 10_000_000)


def _body(
    documento: str,
    *,
    fingerprint: str | None = None,
    confirmado: bool = False,
    alta: dict | None = None,
) -> VinculacionEstablecimientoIn:
    payload: dict = {"documento": documento}
    if fingerprint is not None:
        payload["fingerprint"] = fingerprint
    if confirmado:
        payload["confirmado"] = True
    if alta is not None:
        payload["alta"] = alta
    return VinculacionEstablecimientoIn.model_validate(payload)


def _alta(apellido: str = "Nuevo", nombre: str = "Titular", razon: str | None = None) -> dict:
    if razon:
        return {"razon_social": razon}
    return {"apellido": apellido, "nombre": nombre}


def test_schema_alta_y_limpiar() -> None:
    with pytest.raises(ValidationError):
        VinculacionEstablecimientoIn.model_validate({"documento": "20111222", "limpiar_contribuyente": True})
    with pytest.raises(ValidationError):
        VinculacionEstablecimientoIn.model_validate(
            {"documento": "20111222", "alta": {"apellido": "Solo"}}
        )
    ok = VinculacionEstablecimientoIn.model_validate(
        {"documento": "20111222", "alta": {"apellido": "Perez", "nombre": "Ana"}}
    )
    assert ok.alta is not None
    assert ok.alta.nombre == "Ana"


def test_no_usa_resolve_contribuyente() -> None:
    src = (_SERVICES / "vinculacion_establecimiento_alta.py").read_text(encoding="utf-8")
    assert "resolve_contribuyente(" not in src


def test_1_cuit_inexistente_crea_y_vincula_uno(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    origen = _contrib(apellido="Erroneo")
    d = _dom(origen)
    eo = _eo(d, actor)
    act = _act(d)
    doc = _doc()
    db.session.commit()
    busqueda = preview_vinculacion_establecimiento(eo.id, _body(doc), actor=actor)
    assert busqueda["puede_aplicar"] is False
    assert busqueda["conflicto"]["codigo"] == "SIN_DESTINO"
    assert busqueda["conflicto"]["puede_crear"] is True
    assert Contribuyente.query.filter_by(documento=doc).first() is None

    prev = preview_vinculacion_establecimiento(
        eo.id, _body(doc, alta=_alta("Ocampo", "Carlos")), actor=actor
    )
    assert prev["puede_aplicar"] is True
    assert prev["crea_contribuyente"] is True
    assert prev["contribuyente_destino"]["apellido"] == "Ocampo"
    out = aplicar_vinculacion_establecimiento(
        eo.id,
        _body(doc, alta=_alta("Ocampo", "Carlos"), fingerprint=prev["fingerprint"], confirmado=True),
        actor=actor,
    )
    assert out["applied"] is True
    creados = Contribuyente.query.filter(Contribuyente.documento == doc, Contribuyente.deleted_at.is_(None)).all()
    assert len(creados) == 1
    dest = creados[0]
    db.session.refresh(d)
    db.session.refresh(origen)
    assert d.contribuyente_id == dest.id
    assert dest.apellido == "Ocampo"
    assert dest.nombre == "Carlos"
    assert origen.apellido == "Erroneo"
    assert act.id in [int(a.id) for a in list_actuaciones_por_establecimiento_operativo(eo.id, page=1, page_size=20)[0]]
    audit = db.session.get(CorreccionEstablecimientoAudit, out["audit_id"])
    assert audit is not None
    assert audit.tipo == "VINCULACION"
    assert audit.alcance["creo_contribuyente"] is True
    assert ContribuyenteDocumentoUnico.query.filter_by(
        documento_normalizado=normalizar_documento(doc)
    ).first() is not None


def test_2_cancelar_preview_no_crea(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    doc = _doc()
    db.session.commit()
    preview_vinculacion_establecimiento(eo.id, _body(doc, alta=_alta()), actor=actor)
    assert Contribuyente.query.filter_by(documento=doc).first() is None
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id
    assert CorreccionEstablecimientoAudit.query.filter_by(establecimiento_operativo_id=eo.id).count() == 0


def test_3_aparece_entre_preview_y_confirm_no_duplica(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    doc = _doc()
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(doc, alta=_alta()), actor=actor)
    otro = _contrib(doc=doc, apellido="YaExiste", nombre="Persona")
    db.session.commit()
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_vinculacion_establecimiento(
            eo.id,
            _body(doc, alta=_alta(), fingerprint=prev["fingerprint"], confirmado=True),
            actor=actor,
        )
    assert ei.value.codigo == "DESTINO_APARECIO"
    activos = Contribuyente.query.filter(
        Contribuyente.documento == doc, Contribuyente.deleted_at.is_(None)
    ).all()
    assert len(activos) == 1
    assert activos[0].id == otro.id
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id


def test_4_lock_concurrente_no_crea_dos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    doc = _doc()
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(doc, alta=_alta()), actor=actor)
    key = lock_key_documento(normalizar_documento(doc))
    conn = db.engine.connect()
    try:
        got = conn.exec_driver_sql("SELECT GET_LOCK(%s, %s)", (key, 1)).scalar()
        assert int(got or 0) == 1
        with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
            aplicar_vinculacion_establecimiento(
                eo.id,
                _body(doc, alta=_alta(), fingerprint=prev["fingerprint"], confirmado=True),
                actor=actor,
            )
        assert ei.value.codigo == "DOCUMENTO_EN_USO"
    finally:
        conn.exec_driver_sql("SELECT RELEASE_LOCK(%s)", (key,))
        conn.close()
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id
    assert Contribuyente.query.filter_by(documento=doc).first() is None


def test_5_falla_despues_de_crear_rollback(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    doc = _doc()
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(doc, alta=_alta()), actor=actor)
    with patch(
        "app.domains.establecimientos.services.vinculacion_establecimiento_apply_service._persistir_reasignacion",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError):
            aplicar_vinculacion_establecimiento(
                eo.id,
                _body(doc, alta=_alta(), fingerprint=prev["fingerprint"], confirmado=True),
                actor=actor,
            )
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id
    assert Contribuyente.query.filter_by(documento=doc).first() is None
    assert CorreccionEstablecimientoAudit.query.filter_by(establecimiento_operativo_id=eo.id).count() == 0


def test_6_otro_local_origen_intacto(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    origen = _contrib(apellido="Keep")
    d_f = _dom(origen, calle=f"Ficha{_suf()}")
    d_otro = _dom(origen, calle=f"Otro{_suf()}")
    eo = _eo(d_f, actor)
    _eo(d_otro, actor)
    act_otro = _act(d_otro)
    calle_otro = d_otro.calle
    doc = _doc()
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(doc, alta=_alta()), actor=actor)
    aplicar_vinculacion_establecimiento(
        eo.id, _body(doc, alta=_alta(), fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    db.session.refresh(d_otro)
    db.session.refresh(origen)
    db.session.refresh(act_otro)
    assert d_otro.contribuyente_id == origen.id
    assert d_otro.calle == calle_otro
    assert origen.apellido == "Keep"
    assert act_otro.domicilio_id == d_otro.id


def test_7_existente_mismo_domicilio_agrupa(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Dest")
    origen = _contrib()
    calle = f"Igual{_suf()}"
    d_dest = _dom(dest, calle=calle, numero="10")
    d_orig = _dom(origen, calle=calle, numero="10")
    eo_dest = _eo(d_dest, actor)
    eo_orig = _eo(d_orig, actor)
    act_d = _act(d_dest)
    act_o = _act(d_orig)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo_orig.id, _body(dest.documento), actor=actor)
    assert prev["crea_contribuyente"] is False
    aplicar_vinculacion_establecimiento(
        eo_orig.id,
        _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True),
        actor=actor,
    )
    ids_d = [int(a.id) for a in list_actuaciones_por_establecimiento_operativo(eo_dest.id, page=1, page_size=20)[0]]
    ids_o = [int(a.id) for a in list_actuaciones_por_establecimiento_operativo(eo_orig.id, page=1, page_size=20)[0]]
    assert sorted(ids_d) == sorted([act_d.id, act_o.id])
    assert sorted(ids_o) == sorted(ids_d)
    assert len(ids_d) == len(set(ids_d))


def test_8_circuito_estados_intactos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    origen = _contrib()
    d = _dom(origen)
    geo = _geo(d)
    lat, lng, distrito_id = geo.lat, geo.lng, d.distrito_id
    eo = _eo(d, actor)
    notif = Notificacion(numero_acta=unique_ot_numero(), anio=2026, mes=3)
    db.session.add(notif)
    db.session.flush()
    comp = Comprobacion(numero_acta=unique_ot_numero(), anio=2026, mes=3)
    db.session.add(comp)
    db.session.flush()
    ofi = Oficio(numero_oficio=f"OF{_suf()[:6]}", anio=2026, comprobacion_id=comp.id)
    db.session.add(ofi)
    db.session.flush()
    act = _act(d, tipo="NOTIFICACION")
    act.notificacion_id = notif.id
    act.comprobacion_id = comp.id
    act.titular_nombre_historico = "Snap"
    act.contraproducencia = "SIN_CONTRAPRODUCENCIA"
    db.session.add(act)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 4, 1),
        anio=2026,
        mes=4,
        domicilio_id=d.id,
        notificacion_id=notif.id,
        created_by_user_id=actor.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fecha_ruta_aislada_mismo_anio(2026),
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        numero=uniq_ruta_numero(),
        created_by_user_id=actor.id,
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        estado_ruta_item="ASIGNADO",
        created_by_user_id=actor.id,
    )
    db.session.add(item)
    db.session.commit()
    doc = _doc()
    prev = preview_vinculacion_establecimiento(eo.id, _body(doc, alta=_alta()), actor=actor)
    assert prev["coordenadas_y_distrito"]["se_recalculan"] is False
    aplicar_vinculacion_establecimiento(
        eo.id, _body(doc, alta=_alta(), fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    db.session.refresh(d)
    db.session.refresh(act)
    db.session.refresh(ini)
    db.session.refresh(item)
    db.session.refresh(ruta)
    db.session.refresh(ofi)
    geo2 = DomicilioGeocode.query.filter_by(domicilio_id=d.id).first()
    assert act.notificacion_id == notif.id
    assert act.comprobacion_id == comp.id
    assert act.titular_nombre_historico == "Snap"
    assert act.contraproducencia == "SIN_CONTRAPRODUCENCIA"
    assert ofi.comprobacion_id == comp.id
    assert ini.estado_iniciador == "PENDIENTE"
    assert item.estado_ruta_item == "ASIGNADO"
    assert ruta.estado_ruta == "PUBLICADA"
    assert d.distrito_id == distrito_id
    assert geo2 is not None
    assert float(geo2.lat) == float(lat)


def test_9_ambiguo_relevador_y_sin_confirmacion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    rel = _user(role="relevador")
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    digits = f"{int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000}"
    _contrib(doc=f"20.{digits}")
    _contrib(doc=f"20{digits}")
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(f"20{digits}"), actor=actor)
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "DOCUMENTO_AMBIGUO"
    with pytest.raises(CorreccionEstablecimientoPermisoError):
        preview_vinculacion_establecimiento(eo.id, _body(_doc(), alta=_alta()), actor=rel)
    with pytest.raises(CorreccionEstablecimientoError) as ei:
        aplicar_vinculacion_establecimiento(eo.id, _body(_doc(), alta=_alta()), actor=actor)
    assert "confirmar" in str(ei.value).lower()
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id


def test_10_existente_y_limpiar_siguen(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Ya")
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    aplicar_vinculacion_establecimiento(
        eo.id, _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    db.session.refresh(d)
    assert d.contribuyente_id == dest.id
    with pytest.raises(ValidationError):
        CorreccionEstablecimientoIn.model_validate({"limpiar_contribuyente": True, "contribuyente": {"nombre": "A"}})
    with pytest.raises(ValidationError):
        VinculacionEstablecimientoIn.model_validate({"documento": dest.documento, "limpiar_contribuyente": True})


def test_http_alta_y_401(client, auth_headers, app, service_actor) -> None:
    r = client.post("/establecimientos-operativos/1/vinculaciones/preview", json={"documento": "20111"})
    assert r.status_code == 401
    with app.app_context():
        try:
            actor = db.session.get(User, service_actor)
            assert actor is not None
            origen = _contrib()
            d = _dom(origen)
            eo = _eo(d, actor)
            db.session.commit()
            eid = int(eo.id)
            doc = _doc()
            prev = client.post(
                f"/establecimientos-operativos/{eid}/vinculaciones/preview",
                json={"documento": doc, "alta": {"apellido": "Http", "nombre": "Alta"}},
                headers=auth_headers,
            )
            assert prev.status_code == 200, prev.get_json()
            body_prev = prev.get_json()
            assert body_prev["crea_contribuyente"] is True
            applied = client.post(
                f"/establecimientos-operativos/{eid}/vinculaciones",
                json={
                    "documento": doc,
                    "alta": {"apellido": "Http", "nombre": "Alta"},
                    "confirmado": True,
                    "fingerprint": body_prev["fingerprint"],
                },
                headers=auth_headers,
            )
            assert applied.status_code == 200, applied.get_json()
            assert applied.get_json()["applied"] is True
        finally:
            db.session.rollback()
