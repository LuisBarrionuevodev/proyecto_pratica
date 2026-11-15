"""V1.1-ESTABLECIMIENTOS-VINCULACION.1 — vincular ficha a contribuyente existente."""

from __future__ import annotations

from datetime import date
from pathlib import Path
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
from app.domains.establecimientos.services.historial_actuaciones_establecimiento_service import (
    list_actuaciones_por_establecimiento_operativo,
)
from app.domains.establecimientos.services.historial_contribuyente_service import (
    list_historial_por_documento,
)
from app.domains.establecimientos.services.list_establecimientos_operativos_service import (
    list_establecimientos_operativos,
)
from app.domains.establecimientos.services.resolve_establecimiento_por_domicilio import (
    resolve_establecimiento_por_domicilio,
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
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key
from app.models import (
    Comprobacion,
    Contribuyente,
    CorreccionEstablecimientoAudit,
    DomicilioGeocode,
    EstablecimientoOperativo,
    IniciadorRuta,
    Notificacion,
    Oficio,
    RutaItem,
    RutaTrabajo,
    User,
)
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, unique_ot_numero, uniq_ruta_numero
from tests.test_correccion_establecimiento_edicion_1 import (
    _act,
    _contrib,
    _dom,
    _eo,
    _geo,
    _suf,
    _user,
)

_VINC_DIR = Path(__file__).resolve().parents[1] / "app" / "domains" / "establecimientos"


def _body(documento: str, *, fingerprint: str | None = None, confirmado: bool = False) -> VinculacionEstablecimientoIn:
    payload: dict = {"documento": documento}
    if fingerprint is not None:
        payload["fingerprint"] = fingerprint
    if confirmado:
        payload["confirmado"] = True
    return VinculacionEstablecimientoIn.model_validate(payload)


def _act_ids_historial_cuit(documento: str) -> list[int]:
    entries, _, _ = list_historial_por_documento(documento, limit=200)
    return [int(e.act.id) for e in entries if e.act is not None]


def _act_ids_ficha(eo_id: int) -> list[int]:
    acts, _ = list_actuaciones_por_establecimiento_operativo(int(eo_id), page=1, page_size=50)
    return [int(a.id) for a in acts]


def test_schema_rechaza_titular_y_limpiar() -> None:
    with pytest.raises(ValidationError):
        VinculacionEstablecimientoIn.model_validate({"documento": "20111222", "contribuyente_id": 9})
    with pytest.raises(ValidationError):
        VinculacionEstablecimientoIn.model_validate({"documento": "20111222", "limpiar_contribuyente": True})
    with pytest.raises(ValidationError):
        VinculacionEstablecimientoIn.model_validate({"documento": ""})


def test_canal_no_usa_resolve_contribuyente() -> None:
    for name in (
        "vinculacion_establecimiento_apply_service.py",
        "vinculacion_establecimiento_preview_service.py",
        "vinculacion_establecimiento_resolver.py",
    ):
        src = (_VINC_DIR / "services" / name).read_text(encoding="utf-8")
        assert "resolve_contribuyente(" not in src
        assert "from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente" not in src


def test_1_mismo_cuit_mismo_domicilio_agrupa_sin_duplicar(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Ocampo", nombre="Carlos")
    origen = _contrib(apellido="Erroneo", nombre="Cuit")
    calle = f"SanMartin{_suf()}"
    key = slug_key(calle)
    d_dest = _dom(dest, calle=calle, numero="100", calle_key=key)
    d_orig = _dom(origen, calle=calle, numero="100", calle_key=key)
    eo_dest = _eo(d_dest, actor)
    eo_orig = _eo(d_orig, actor)
    act_dest = _act(d_dest, titular="OcampoSnap")
    act_orig = _act(d_orig, titular="ErroneoSnap")
    db.session.commit()

    prev = preview_vinculacion_establecimiento(eo_orig.id, _body(dest.documento), actor=actor)
    assert prev["puede_aplicar"] is True
    assert prev["situacion"] == "B"
    assert prev["ficha_logica_destino"]["establecimiento_operativo_id"] == eo_dest.id
    assert prev["edita_datos_destino"] is False

    out = aplicar_vinculacion_establecimiento(
        eo_orig.id,
        _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True),
        actor=actor,
    )
    assert out["applied"] is True
    db.session.refresh(d_orig)
    db.session.refresh(d_dest)
    db.session.refresh(dest)
    db.session.refresh(origen)
    db.session.refresh(act_orig)
    assert d_orig.contribuyente_id == dest.id
    assert d_dest.contribuyente_id == dest.id
    assert dest.apellido == "Ocampo"
    assert dest.nombre == "Carlos"
    assert origen.apellido == "Erroneo"
    assert act_orig.titular_nombre_historico == "ErroneoSnap"

    ids_dest = _act_ids_ficha(eo_dest.id)
    ids_orig = _act_ids_ficha(eo_orig.id)
    assert sorted(ids_dest) == sorted([act_dest.id, act_orig.id])
    assert sorted(ids_orig) == sorted(ids_dest)
    assert len(ids_dest) == len(set(ids_dest))

    cuit_dest = _act_ids_historial_cuit(dest.documento)
    assert act_dest.id in cuit_dest
    assert act_orig.id in cuit_dest
    cuit_origen = _act_ids_historial_cuit(origen.documento)
    assert act_orig.id not in cuit_origen

    items, _ = list_establecimientos_operativos(page=1, page_size=200, calle=calle)
    ids_listado = [int(e.id) for e in items]
    assert min(int(eo_dest.id), int(eo_orig.id)) in ids_listado
    assert not (int(eo_dest.id) in ids_listado and int(eo_orig.id) in ids_listado)
    assert db.session.get(EstablecimientoOperativo, eo_dest.id) is not None
    assert db.session.get(EstablecimientoOperativo, eo_orig.id) is not None
    assert out["establecimiento_operativo_canonico_id"] == min(int(eo_dest.id), int(eo_orig.id))


def test_2_mismo_cuit_domicilio_distinto_fichas_separadas(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Ocampo", nombre="Carlos")
    origen = _contrib(apellido="MalCuit", nombre="X")
    d_dest = _dom(dest, calle=f"Mitre{_suf()}", numero="10")
    d_orig = _dom(origen, calle=f"Belgrano{_suf()}", numero="20")
    eo_dest = _eo(d_dest, actor)
    eo_orig = _eo(d_orig, actor)
    act_dest = _act(d_dest)
    act_orig = _act(d_orig)
    db.session.commit()

    prev = preview_vinculacion_establecimiento(eo_orig.id, _body(dest.documento), actor=actor)
    assert prev["situacion"] == "A"
    assert prev["ficha_logica_destino"]["existe"] is False

    aplicar_vinculacion_establecimiento(
        eo_orig.id,
        _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True),
        actor=actor,
    )
    db.session.refresh(d_orig)
    db.session.refresh(d_dest)
    assert d_orig.contribuyente_id == dest.id
    assert d_dest.contribuyente_id == dest.id
    assert d_orig.calle != d_dest.calle
    assert sorted(_act_ids_ficha(eo_dest.id)) == [act_dest.id]
    assert sorted(_act_ids_ficha(eo_orig.id)) == [act_orig.id]
    cuit = _act_ids_historial_cuit(dest.documento)
    assert act_dest.id in cuit and act_orig.id in cuit


def test_3_historial_documento_anterior_deja_de_atribuir(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    act = _act(d)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    aplicar_vinculacion_establecimiento(
        eo.id, _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    assert act.id not in _act_ids_historial_cuit(origen.documento)
    assert act.id in _act_ids_historial_cuit(dest.documento)


def test_4_otros_locales_origen_intactos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib(apellido="Keep")
    d_f = _dom(origen, calle=f"Ficha{_suf()}")
    d_otro = _dom(origen, calle=f"OtroLocal{_suf()}")
    eo = _eo(d_f, actor)
    eo_otro = _eo(d_otro, actor)
    act_otro = _act(d_otro)
    calle_otro, nro_otro = d_otro.calle, d_otro.numero
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    assert eo_otro.id in prev["otros_locales_contribuyente_anterior"]["ids"]
    aplicar_vinculacion_establecimiento(
        eo.id, _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    db.session.refresh(d_otro)
    db.session.refresh(origen)
    db.session.refresh(act_otro)
    assert d_otro.contribuyente_id == origen.id
    assert d_otro.calle == calle_otro
    assert d_otro.numero == nro_otro
    assert origen.apellido == "Keep"
    assert act_otro.domicilio_id == d_otro.id
    assert act_otro.id in _act_ids_historial_cuit(origen.documento)


def test_5_y_6_destino_otros_locales_y_datos_personales(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib(apellido="Destino", nombre="Persona")
    dest.razon_social = "Razon Destino SA"
    origen = _contrib()
    d_dest_otro = _dom(dest, calle=f"LocalB{_suf()}")
    d_f = _dom(origen, calle=f"Ficha{_suf()}")
    eo = _eo(d_f, actor)
    _eo(d_dest_otro, actor)
    act_b = _act(d_dest_otro)
    calle_b = d_dest_otro.calle
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    aplicar_vinculacion_establecimiento(
        eo.id, _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    db.session.refresh(dest)
    db.session.refresh(d_dest_otro)
    db.session.refresh(act_b)
    assert dest.apellido == "Destino"
    assert dest.nombre == "Persona"
    assert dest.razon_social == "Razon Destino SA"
    assert d_dest_otro.contribuyente_id == dest.id
    assert d_dest_otro.calle == calle_b
    assert act_b.domicilio_id == d_dest_otro.id


def test_7_8_circuito_notif_comprobacion_ruta(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen, calle=f"Rec{_suf()}", numero="50")
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
    act.contraproducencia = "SIN_CONTRAPRODUCENCIA"
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
        orden_trabajo_id=act.orden_trabajo_id,
        created_by_user_id=actor.id,
    )
    db.session.add(item)
    db.session.flush()
    act_hecha = _act(d, tipo="INSPECCION", titular="Hecha")
    db.session.commit()

    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    assert prev["alcance"]["notificaciones"]["cantidad"] >= 1
    assert prev["alcance"]["ruta_items"]["cantidad"] >= 1
    aplicar_vinculacion_establecimiento(
        eo.id, _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    db.session.refresh(d)
    db.session.refresh(act)
    db.session.refresh(act_hecha)
    db.session.refresh(ini_pend)
    db.session.refresh(item)
    db.session.refresh(ruta)
    db.session.refresh(ofi)
    assert d.contribuyente_id == dest.id
    assert act.domicilio_id == d.id
    assert act.notificacion_id == notif.id
    assert act.comprobacion_id == comp.id
    assert act.orden_trabajo_id is not None
    assert act.contraproducencia == "SIN_CONTRAPRODUCENCIA"
    assert ofi.comprobacion_id == comp.id
    assert ini_pend.estado_iniciador == "PENDIENTE"
    assert ini_pend.domicilio_id == d.id
    assert item.estado_ruta_item == "ASIGNADO"
    assert item.orden_trabajo_id == act.orden_trabajo_id
    assert ruta.estado_ruta == "PUBLICADA"
    assert act.titular_nombre_historico == "Historico"
    assert act_hecha.titular_nombre_historico == "Hecha"


def test_9_coordenadas_y_distrito_intactos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    from app.models import Distrito

    dist = Distrito.query.first()
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen, distrito_id=dist.id if dist else None)
    geo = _geo(d)
    lat, lng, distrito_id = geo.lat, geo.lng, d.distrito_id
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    assert prev["coordenadas_y_distrito"]["se_recalculan"] is False
    aplicar_vinculacion_establecimiento(
        eo.id, _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    db.session.refresh(d)
    geo2 = DomicilioGeocode.query.filter_by(domicilio_id=d.id).first()
    assert d.distrito_id == distrito_id
    assert geo2 is not None
    assert float(geo2.lat) == float(lat)
    assert float(geo2.lng) == float(lng)


def test_10_snapshots_historicos_intactos(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    act = _act(d, titular="SnapViejo")
    act.nombre_local = "LocalSnapshot"
    db.session.add(act)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    assert prev["snapshots_y_pdf"]["se_actualizan"] is False
    aplicar_vinculacion_establecimiento(
        eo.id, _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    db.session.refresh(act)
    assert act.titular_nombre_historico == "SnapViejo"
    assert act.titular_apellido_historico == "Snap"
    assert act.nombre_local == "LocalSnapshot"


def test_11_documento_ambiguo_bloquea(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    digits = f"{int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000}"
    doc_dot = f"20.{digits}"
    doc_plain = f"20{digits}"
    assert len(doc_dot) == 11
    dest_a = _contrib(doc=doc_dot)
    dest_b = _contrib(doc=doc_plain)
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(doc_plain), actor=actor)
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "DOCUMENTO_AMBIGUO"
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_vinculacion_establecimiento(
            eo.id,
            _body(doc_plain, fingerprint="a" * 64, confirmado=True),
            actor=actor,
        )
    assert "más de un contribuyente" in str(ei.value).lower()
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id
    assert dest_a.id != dest_b.id


def test_12_ambiguedad_domicilio_bloquea(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    calle = f"Ambig{_suf()}"
    d1 = _dom(origen, calle=calle, numero="3", calle_key=slug_key(calle))
    d2 = _dom(origen, calle=calle, numero="3", calle_key=f"{slug_key(calle)}_x")
    eo = _eo(d1, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "AMBIGUEDAD_DOMICILIO"
    with pytest.raises(CorreccionEstablecimientoConflictError):
        aplicar_vinculacion_establecimiento(
            eo.id,
            _body(dest.documento, fingerprint="b" * 64, confirmado=True),
            actor=actor,
        )
    db.session.refresh(d1)
    assert d1.contribuyente_id == origen.id
    assert d2.calle_key.endswith("_x")


def test_13_preview_no_escribe_y_cancelar(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(
        eo.id, _body(dest.documento, confirmado=True), actor=actor
    )
    assert prev["puede_aplicar"] is True
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id
    assert CorreccionEstablecimientoAudit.query.filter_by(establecimiento_operativo_id=eo.id).count() == 0


def test_14_fingerprint_stale_rechaza(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_vinculacion_establecimiento(
            eo.id,
            _body(dest.documento, fingerprint="0" * 64, confirmado=True),
            actor=actor,
        )
    assert "vista previa" in str(ei.value).lower()
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id


def test_14b_cambio_real_entre_preview_y_apply(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    tercero = _contrib()
    d.contribuyente_id = tercero.id
    db.session.commit()
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_vinculacion_establecimiento(
            eo.id,
            _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True),
            actor=actor,
        )
    assert ei.value.codigo == "PREVIEW_STALE"
    db.session.refresh(d)
    assert d.contribuyente_id == tercero.id


def test_15_error_durante_apply_rollback(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    with patch(
        "app.domains.establecimientos.services.vinculacion_establecimiento_apply_service.db.session.commit",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError):
            aplicar_vinculacion_establecimiento(
                eo.id,
                _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True),
                actor=actor,
            )
    db.session.refresh(d)
    db.session.refresh(dest)
    assert d.contribuyente_id == origen.id
    assert dest.nombre is not None
    assert (
        CorreccionEstablecimientoAudit.query.filter_by(
            establecimiento_operativo_id=eo.id, tipo="VINCULACION"
        ).count()
        == 0
    )


def test_16_relevador_sin_permiso(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    rel = _user(role="relevador")
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    with pytest.raises(CorreccionEstablecimientoPermisoError):
        preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=rel)
    with pytest.raises(CorreccionEstablecimientoPermisoError):
        aplicar_vinculacion_establecimiento(
            eo.id, _body(dest.documento, fingerprint="c" * 64, confirmado=True), actor=rel
        )
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id


def test_17_auditoria_vinculacion_y_confirmacion(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    dest = _contrib()
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    with pytest.raises(CorreccionEstablecimientoError) as ei:
        aplicar_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    assert "confirmar" in str(ei.value).lower()
    prev = preview_vinculacion_establecimiento(eo.id, _body(dest.documento), actor=actor)
    with pytest.raises(CorreccionEstablecimientoError):
        aplicar_vinculacion_establecimiento(
            eo.id, _body(dest.documento, fingerprint=prev["fingerprint"]), actor=actor
        )
    out = aplicar_vinculacion_establecimiento(
        eo.id, _body(dest.documento, fingerprint=prev["fingerprint"], confirmado=True), actor=actor
    )
    audit = db.session.get(CorreccionEstablecimientoAudit, out["audit_id"])
    assert audit is not None
    assert audit.tipo == "VINCULACION"
    assert audit.created_by_user_id == actor.id
    assert audit.alcance["contribuyente_origen_id"] == origen.id
    assert audit.alcance["contribuyente_destino_id"] == dest.id
    assert d.id in audit.alcance["domicilio_ids"]


def test_18_correccion_sigue_rechazando_documento_ajeno_y_limpiar(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    a = _contrib()
    b = _contrib()
    d = _dom(a)
    eo = _eo(d, actor)
    prev_doc = a.documento
    db.session.commit()
    with pytest.raises(CorreccionEstablecimientoConflictError) as ei:
        aplicar_correccion_establecimiento(
            eo.id,
            CorreccionEstablecimientoIn.model_validate(
                {"contribuyente": {"documento": b.documento}, "confirmado": True}
            ),
            actor=actor,
        )
    assert "otro contribuyente" in str(ei.value).lower()
    db.session.refresh(a)
    db.session.refresh(d)
    assert a.documento == prev_doc
    assert d.contribuyente_id == a.id
    with pytest.raises(ValidationError):
        CorreccionEstablecimientoIn.model_validate(
            {"limpiar_contribuyente": True, "contribuyente": {"nombre": "A"}}
        )
    with pytest.raises(ValidationError):
        VinculacionEstablecimientoIn.model_validate(
            {"documento": b.documento, "limpiar_contribuyente": True}
        )


def test_19_carga_misma_identidad_sin_cambiar_reglas(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d1 = _dom(c, calle=f"Igual{_suf()}", numero="230")
    d2 = _dom(c, calle=d1.calle, numero="230", calle_key=d1.calle_key)
    eo1 = resolve_establecimiento_por_domicilio(d1.id, created_by_user_id=actor.id)
    eo2 = resolve_establecimiento_por_domicilio(d2.id, created_by_user_id=actor.id)
    assert eo1 == eo2
    d3 = _dom(c, calle=f"Otra{_suf()}", numero="500")
    eo3 = resolve_establecimiento_por_domicilio(d3.id, created_by_user_id=actor.id)
    assert eo3 != eo1


def test_lookup_normalizado_unico(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    digits = f"{int(uuid4().hex[:8], 16) % 90_000_000 + 10_000_000}"
    dest = _contrib(apellido="Ocampo", nombre="Carlos", doc=f"20.{digits}")
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(f"20{digits}"), actor=actor)
    assert prev["puede_aplicar"] is True
    assert prev["contribuyente_destino"]["id"] == dest.id
    assert prev["contribuyente_destino"]["apellido"] == "Ocampo"


def test_sin_destino_no_crea(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    origen = _contrib()
    d = _dom(origen)
    eo = _eo(d, actor)
    db.session.commit()
    doc = str(int(uuid4().hex[:8], 16) % 80_000_000 + 10_000_000)
    prev = preview_vinculacion_establecimiento(eo.id, _body(doc), actor=actor)
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "SIN_DESTINO"
    assert Contribuyente.query.filter_by(documento=doc).first() is None
    db.session.refresh(d)
    assert d.contribuyente_id == origen.id


def test_mismo_contribuyente_no_vincula(app_ctx, service_actor) -> None:
    actor = db.session.get(User, service_actor)
    assert actor is not None
    c = _contrib()
    d = _dom(c)
    eo = _eo(d, actor)
    db.session.commit()
    prev = preview_vinculacion_establecimiento(eo.id, _body(c.documento), actor=actor)
    assert prev["puede_aplicar"] is False
    assert prev["conflicto"]["codigo"] == "MISMO_CONTRIBUYENTE"


def test_http_jwt_y_apply(client, auth_headers, app, service_actor) -> None:
    r = client.post("/establecimientos-operativos/1/vinculaciones/preview", json={"documento": "20111"})
    assert r.status_code == 401
    with app.app_context():
        try:
            actor = db.session.get(User, service_actor)
            assert actor is not None
            dest = _contrib(apellido="HttpDest")
            origen = _contrib(apellido="HttpOrig")
            d = _dom(origen)
            eo = _eo(d, actor)
            rel = _user(role="relevador")
            db.session.commit()
            eid = int(eo.id)
            dest_doc = dest.documento
            rel_token = create_access_token(identity=str(rel.id))

            denied = client.post(
                f"/establecimientos-operativos/{eid}/vinculaciones",
                json={"documento": dest_doc, "confirmado": True, "fingerprint": "a" * 64},
                headers={"Authorization": f"Bearer {rel_token}", "Content-Type": "application/json"},
            )
            assert denied.status_code == 403

            prev = client.post(
                f"/establecimientos-operativos/{eid}/vinculaciones/preview",
                json={"documento": dest_doc},
                headers=auth_headers,
            )
            assert prev.status_code == 200, prev.get_json()
            body_prev = prev.get_json()
            assert body_prev["puede_aplicar"] is True
            fp = body_prev["fingerprint"]

            applied = client.post(
                f"/establecimientos-operativos/{eid}/vinculaciones",
                json={"documento": dest_doc, "confirmado": True, "fingerprint": fp},
                headers=auth_headers,
            )
            assert applied.status_code == 200, applied.get_json()
            body = applied.get_json()
            assert body["applied"] is True
            assert body["audit_id"]
        finally:
            db.session.rollback()
