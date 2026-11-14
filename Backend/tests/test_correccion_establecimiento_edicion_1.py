"""V1.1-ESTABLECIMIENTOS-EDICION.1 — correcciones controladas desde la ficha."""

from __future__ import annotations

from datetime import date
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
from app.domains.establecimientos.services.correccion_establecimiento_apply_service import (
    aplicar_correccion_establecimiento,
)
from app.domains.establecimientos.services.correccion_establecimiento_preview_service import (
    preview_correccion_establecimiento,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
    CorreccionEstablecimientoError,
    CorreccionEstablecimientoPermisoError,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key
from app.models import (
    Actuaciones,
    Comprobacion,
    Contribuyente,
    CorreccionEstablecimientoAudit,
    Domicilio,
    DomicilioGeocode,
    EstablecimientoOperativo,
    IniciadorRuta,
    Notificacion,
    Oficio,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, unique_ot_numero, uniq_ruta_numero


def _suf() -> str:
    return uuid4().hex[:8]


def _user(*, role: str = "usuario") -> User:
    u = User(
        username=f"corr_{role}_{_suf()}",
        email=f"corr_{role}_{_suf()}@t.local",
        password_hash="x",
        role=role,
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _rubro() -> Rubro:
    r = Rubro.query.first()
    if r is None:
        r = Rubro(nombre=f"RubCorr{_suf()}")
        db.session.add(r)
        db.session.flush()
    return r


def _contrib(*, apellido: str = "Corr", nombre: str = "Tit", doc: str | None = None) -> Contribuyente:
    c = Contribuyente(
        apellido=apellido,
        nombre=nombre,
        documento=doc or str(int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000),
    )
    db.session.add(c)
    db.session.flush()
    return c


def _dom(
    contrib: Contribuyente,
    *,
    calle: str | None = None,
    numero: str = "100",
    calle_key: str | None = None,
    distrito_id: int | None = None,
) -> Domicilio:
    rub = _rubro()
    c = calle or f"CalleCorr{_suf()}"
    d = Domicilio(
        calle=c,
        numero=numero,
        calle_key=calle_key or slug_key(c),
        rubro_id=rub.id,
        contribuyente_id=contrib.id,
        distrito_id=distrito_id,
        numero_tipo="NUMERO",
    )
    db.session.add(d)
    db.session.flush()
    return d


def _eo(dom: Domicilio, user: User) -> EstablecimientoOperativo:
    eo = EstablecimientoOperativo(domicilio_id=dom.id, created_by_user_id=user.id)
    db.session.add(eo)
    db.session.flush()
    return eo


def _act(dom: Domicilio, *, tipo: str = "INSPECCION", titular: str | None = None) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 12),
        mes=3,
        anio=2026,
        tipo=tipo,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        titular_nombre_historico=titular,
        titular_apellido_historico="Snap",
    )
    db.session.add(act)
    db.session.flush()
    return act


def _geo(dom: Domicilio, *, lat: str = "-26.8300000", lng: str = "-65.2200000") -> DomicilioGeocode:
    g = DomicilioGeocode(
        domicilio_id=dom.id,
        lat=Decimal(lat),
        lng=Decimal(lng),
        geo_status="OK",
        source="AUTO",
    )
    db.session.add(g)
    db.session.flush()
    return g


def test_schema_rechaza_cambio_titular_y_limpiar() -> None:
    with pytest.raises(ValidationError) as ei:
        CorreccionEstablecimientoIn.model_validate({"contribuyente": {"contribuyente_id": 9}})
    assert "contribuyente_id" in str(ei.value)
    with pytest.raises(ValidationError):
        CorreccionEstablecimientoIn.model_validate({"limpiar_contribuyente": True, "contribuyente": {"nombre": "A"}})


def test_1_contribuyente_varios_establecimientos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Viejo", nombre="Nombre")
    d1 = _dom(c, calle=f"Uno{_suf()}")
    d2 = _dom(c, calle=f"Dos{_suf()}")
    eo1 = _eo(d1, actor)
    _eo(d2, actor)
    _act(d1)
    _act(d2)
    body = CorreccionEstablecimientoIn.model_validate(
        {"contribuyente": {"apellido": "NuevoAp", "nombre": "NuevoNom"}, "confirmado": True}
    )
    out = aplicar_correccion_establecimiento(eo1.id, body, actor=actor)
    assert out["applied"] is True
    db.session.refresh(c)
    assert c.apellido == "NuevoAp"
    assert c.nombre == "NuevoNom"
    assert d1.contribuyente_id == c.id
    assert d2.contribuyente_id == c.id
    audit = db.session.get(CorreccionEstablecimientoAudit, out["audit_id"])
    assert audit is not None
    assert audit.created_by_user_id == actor.id
    assert audit.tipo == "CONTRIBUYENTE"


def test_2_documento_ajeno_409_sin_fusion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    a = _contrib(doc=str(int(uuid4().hex[:8], 16) % 80_000_000 + 10_000_000))
    b = _contrib(doc=str(int(uuid4().hex[:8], 16) % 80_000_000 + 10_000_000))
    d = _dom(a)
    eo = _eo(d, actor)
    prev_doc = a.documento
    db.session.commit()
    body = CorreccionEstablecimientoIn.model_validate(
        {"contribuyente": {"documento": b.documento}, "confirmado": True}
    )
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    assert "otro contribuyente" in str(ei.value).lower()
    db.session.refresh(a)
    db.session.refresh(d)
    assert a.documento == prev_doc
    assert d.contribuyente_id == a.id
    assert b.id != a.id


def test_3_guardar_sin_cambios_no_desvincula(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Igual", nombre="Mismo")
    d = _dom(c)
    eo = _eo(d, actor)
    body = CorreccionEstablecimientoIn.model_validate(
        {
            "contribuyente": {
                "documento": c.documento,
                "apellido": c.apellido,
                "nombre": c.nombre,
                "razon_social": c.razon_social,
            },
            "confirmado": True,
        }
    )
    out = aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    assert out["applied"] is False
    assert out.get("audit_id") is None
    db.session.refresh(d)
    db.session.refresh(c)
    assert d.contribuyente_id == c.id
    assert c.apellido == "Igual"


def test_4_schema_no_trata_cambio_titular(app_ctx) -> None:
    with pytest.raises(ValidationError):
        CorreccionEstablecimientoIn.model_validate(
            {"contribuyente": {"id": 1, "documento": "20111222333"}}
        )


def test_5_domicilio_no_toca_otro_establecimiento(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d1 = _dom(c, calle=f"Orig{_suf()}", numero="10")
    d2 = _dom(c, calle=f"Otro{_suf()}", numero="20")
    calle2 = d2.calle
    eo1 = _eo(d1, actor)
    _eo(d2, actor)
    body = CorreccionEstablecimientoIn.model_validate(
        {"domicilio": {"calle": f"Corr{_suf()}", "numero": "11"}, "confirmado": True}
    )
    out = aplicar_correccion_establecimiento(eo1.id, body, actor=actor)
    assert out["applied"] is True
    db.session.refresh(d1)
    db.session.refresh(d2)
    assert d1.calle.startswith("Corr")
    assert d1.numero == "11"
    assert d2.calle == calle2
    assert d2.numero == "20"


def test_6_7_8_recorrido_vivo_sin_cambiar_estados(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c, calle=f"Rec{_suf()}", numero="50")
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
    act.titular_nombre_historico = "Historico"
    db.session.add(act)
    db.session.flush()

    ini_pend = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 4, 1),
        anio=2026,
        mes=4,
        domicilio_id=d.id,
        notificacion_id=notif.id,
        created_by_user_id=actor.id,
    )
    db.session.add(ini_pend)
    db.session.flush()

    fecha_r = fecha_ruta_aislada_mismo_anio(2026)
    ruta = RutaTrabajo(
        fecha=fecha_r,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        numero=uniq_ruta_numero(),
        created_by_user_id=actor.id,
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini_pend.id,
        estado_ruta_item="ASIGNADO",
        created_by_user_id=actor.id,
    )
    db.session.add(item)
    db.session.flush()

    act_hecha = _act(d, tipo="INSPECCION", titular="Antecedente")
    nueva_calle = f"Nueva{_suf()}"
    body = CorreccionEstablecimientoIn.model_validate(
        {"domicilio": {"calle": nueva_calle, "numero": "51"}, "confirmado": True}
    )
    out = aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    assert out["applied"] is True
    db.session.refresh(d)
    db.session.refresh(ini_pend)
    db.session.refresh(item)
    db.session.refresh(ruta)
    db.session.refresh(act)
    db.session.refresh(act_hecha)
    db.session.refresh(ofi)
    assert d.calle == nueva_calle
    assert act.domicilio_id == d.id
    assert act.notificacion_id == notif.id
    assert act.comprobacion_id == comp.id
    assert ofi.comprobacion_id == comp.id
    assert ini_pend.estado_iniciador == "PENDIENTE"
    assert ini_pend.domicilio_id == d.id
    assert item.estado_ruta_item == "ASIGNADO"
    assert ruta.estado_ruta == "PUBLICADA"
    assert act.titular_nombre_historico == "Historico"
    assert act_hecha.titular_nombre_historico == "Antecedente"
    assert act_hecha.domicilio_id == d.id


def test_9_forks_comprobados_se_actualizan(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    calle = f"Fork{_suf()}"
    key = slug_key(calle)
    d1 = _dom(c, calle=calle, numero="8", calle_key=key)
    d2 = _dom(c, calle=calle, numero="8", calle_key=key)
    eo = _eo(d1, actor)
    _act(d2)
    body = CorreccionEstablecimientoIn.model_validate(
        {"domicilio": {"calle": f"ForkNew{_suf()}", "numero": "9"}, "confirmado": True}
    )
    out = aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    assert out["applied"] is True
    db.session.refresh(d1)
    db.session.refresh(d2)
    assert d1.numero == "9"
    assert d2.numero == "9"
    assert d1.calle == d2.calle


def test_9b_ambiguedad_lookalike_detiene(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    calle = f"Ambig{_suf()}"
    d1 = _dom(c, calle=calle, numero="3", calle_key=slug_key(calle))
    d2 = _dom(c, calle=calle, numero="3", calle_key=f"{slug_key(calle)}_x")
    eo = _eo(d1, actor)
    prev = d1.calle
    db.session.commit()
    body = CorreccionEstablecimientoIn.model_validate(
        {"domicilio": {"calle": f"Stop{_suf()}", "numero": "4"}, "confirmado": True}
    )
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    assert "coinciden" in str(ei.value).lower() or "ambigu" in str(ei.value).lower() or "texto" in str(ei.value).lower()
    db.session.refresh(d1)
    db.session.refresh(d2)
    assert d1.calle == prev
    assert d2.calle_key.endswith("_x")


def test_10_coordenadas_y_distrito_intactos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    from app.models import Distrito

    dist = Distrito.query.first()
    c = _contrib()
    d = _dom(c, distrito_id=dist.id if dist else None)
    geo = _geo(d)
    lat, lng = geo.lat, geo.lng
    distrito_id = d.distrito_id
    eo = _eo(d, actor)
    prev = preview_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate(
            {"domicilio": {"calle": f"Geo{_suf()}", "numero": "77"}}
        ),
        actor=actor,
    )
    assert prev["coordenadas_y_distrito"]["se_recalculan"] is False
    assert any("coordenadas" in a.lower() for a in prev["advertencias"])
    aplicar_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate(
            {"domicilio": {"calle": f"Geo{_suf()}", "numero": "77"}, "confirmado": True}
        ),
        actor=actor,
    )
    db.session.refresh(d)
    geo2 = DomicilioGeocode.query.filter_by(domicilio_id=d.id).first()
    assert d.distrito_id == distrito_id
    assert geo2 is not None
    assert float(geo2.lat) == float(lat)
    assert float(geo2.lng) == float(lng)


def test_11_tramite_ajeno_misma_direccion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c1 = _contrib()
    c2 = _contrib()
    calle = f"Igual{_suf()}"
    d1 = _dom(c1, calle=calle, numero="15")
    d2 = _dom(c2, calle=calle, numero="15")
    eo = _eo(d1, actor)
    act_ajena = _act(d2)
    aplicar_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate(
            {"domicilio": {"calle": f"Solo{_suf()}", "numero": "16"}, "confirmado": True}
        ),
        actor=actor,
    )
    db.session.refresh(d2)
    db.session.refresh(act_ajena)
    assert d2.calle == calle
    assert d2.numero == "15"
    assert act_ajena.domicilio_id == d2.id


def test_12_fallo_durante_guardado_rollback(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib(apellido="Antes")
    d = _dom(c, calle=f"Rb{_suf()}", numero="1")
    eo = _eo(d, actor)
    calle0, doc0 = d.calle, c.documento
    db.session.commit()
    body = CorreccionEstablecimientoIn.model_validate(
        {
            "contribuyente": {"apellido": "Despues"},
            "domicilio": {"calle": f"RbNew{_suf()}", "numero": "2"},
            "confirmado": True,
        }
    )
    with patch(
        "app.domains.establecimientos.services.correccion_establecimiento_apply_service._corregir_domicilios_ficha",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError):
            aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    db.session.refresh(c)
    db.session.refresh(d)
    assert c.apellido == "Antes"
    assert d.calle == calle0
    assert c.documento == doc0
    assert CorreccionEstablecimientoAudit.query.filter_by(establecimiento_operativo_id=eo.id).count() == 0


def test_13_permiso_relevador_y_preview(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    rel = _user(role="relevador")
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    db.session.commit()
    body = CorreccionEstablecimientoIn.model_validate(
        {"contribuyente": {"apellido": "X"}, "confirmado": True}
    )
    with pytest.raises(CorreccionEstablecimientoPermisoError):
        aplicar_correccion_establecimiento(eo.id, body, actor=rel)
    prev = preview_correccion_establecimiento(eo.id, body, actor=actor)
    assert "contribuyente" in prev
    assert prev["contribuyente"]["establecimientos_afectados"]["cantidad"] >= 1
    assert any("establecimientos asociados" in a.lower() for a in prev["advertencias"])


def test_14_actas_estados_flujo_intactos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    act = _act(d, tipo="COMPROBACION")
    act.contraproducencia = "SIN_CONTRAPRODUCENCIA"
    db.session.add(act)
    db.session.flush()
    aplicar_correccion_establecimiento(
        eo.id,
        CorreccionEstablecimientoIn.model_validate(
            {"contribuyente": {"nombre": "Corr14"}, "confirmado": True}
        ),
        actor=actor,
    )
    db.session.refresh(act)
    assert act.tipo == "COMPROBACION"
    assert act.contraproducencia == "SIN_CONTRAPRODUCENCIA"
    assert act.domicilio_id == d.id


def test_apply_requiere_confirmacion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    body = CorreccionEstablecimientoIn.model_validate({"contribuyente": {"nombre": "Z"}})
    with pytest.raises(CorreccionEstablecimientoError) as ei:
        aplicar_correccion_establecimiento(eo.id, body, actor=actor)
    assert "confirmar" in str(ei.value).lower()


def test_http_jwt_y_apply(client, auth_headers, app, service_actor) -> None:
    r = client.post("/establecimientos-operativos/1/correcciones/preview", json={"contribuyente": {"nombre": "A"}})
    assert r.status_code == 401
    with app.app_context():
        try:
            actor = db.session.get(User, service_actor)
            assert actor is not None
            c = _contrib(apellido="Http")
            d = _dom(c)
            eo = _eo(d, actor)
            rel = _user(role="relevador")
            db.session.commit()
            eid = int(eo.id)
            rel_token = create_access_token(identity=str(rel.id))

            denied = client.post(
                f"/establecimientos-operativos/{eid}/correcciones",
                json={"contribuyente": {"apellido": "Nope"}, "confirmado": True},
                headers={"Authorization": f"Bearer {rel_token}", "Content-Type": "application/json"},
            )
            assert denied.status_code == 403

            prev = client.post(
                f"/establecimientos-operativos/{eid}/correcciones/preview",
                json={"contribuyente": {"apellido": "HttpNew"}},
                headers=auth_headers,
            )
            assert prev.status_code == 200, prev.get_json()
            assert prev.get_json()["puede_aplicar"] is True

            applied = client.post(
                f"/establecimientos-operativos/{eid}/correcciones",
                json={"contribuyente": {"apellido": "HttpNew"}, "confirmado": True},
                headers=auth_headers,
            )
            assert applied.status_code == 200, applied.get_json()
            body = applied.get_json()
            assert body["applied"] is True
            assert body["audit_id"]
        finally:
            db.session.rollback()
