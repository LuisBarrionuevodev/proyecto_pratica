"""
Preservación de geocode en flujos documentales (Actuaciones, oficios, reencolado).

Regla: cargar actas / editar actuación / agregar oficio / reencolar / corregir contra
no deben borrar ni recalcular lat/lng/geocode_status salvo flujos explícitos de Nomenclatura.
"""

from __future__ import annotations

import random
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.oficio_completion_service import (
    complete_oficio_from_actuacion,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.domicilios.services.domicilio_edit_policy_service import (
    domicilio_payload_cambia_texto_geografico,
    resolver_policy_edicion_domicilio,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    compute_addr_hash,
)
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    DomicilioGeocode,
    Inspector,
    IniciadorRuta,
    OrdenTrabajo,
    Rubro,
)

from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada


def _ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _geo_snapshot(dom_id: int) -> dict:
    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()
    return {
        "calle": dom.calle,
        "numero": dom.numero,
        "lat": geo.lat if geo else None,
        "lng": geo.lng if geo else None,
        "geo_status": geo.geo_status if geo else None,
        "addr_hash": geo.addr_hash if geo else None,
    }


def _assert_geo_unchanged(before: dict, after: dict) -> None:
    for key in ("lat", "lng", "geo_status", "addr_hash"):
        assert after[key] == before[key], f"{key}: {before[key]!r} -> {after[key]!r}"


def _mk_actuacion_geocodificada(suf: str) -> tuple[Actuaciones, Domicilio, Rubro, str]:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere rubro en catálogo")
    doc = str(random.randint(10_000_000, 99_999_999))
    c = Contribuyente(apellido=f"Geo{suf}", nombre="Tit", documento=doc)
    db.session.add(c)
    db.session.flush()
    calle = f"GeoCalle_{suf}"
    dom = Domicilio(
        calle=calle,
        numero="100",
        calle_normalizada=calle,
        calle_norm_status="OK",
        rubro_id=rub.id,
        contribuyente_id=c.id,
    )
    db.session.add(dom)
    db.session.flush()
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="OK",
            lat=-26.8241,
            lng=-65.2226,
            addr_hash=compute_addr_hash(dom),
            source="AUTO",
        )
    )
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 6, 1),
        mes=6,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.commit()
    return act, dom, rub, doc


def _payload_put_actuacion(
    *,
    act: Actuaciones,
    rub: Rubro,
    doc: str,
    calle: str,
    numero: str,
    **extra,
) -> dict:
    return {
        "fecha_actuacion": act.fecha.strftime("%d/%m/%Y") if act.fecha else "01/06/2026",
        "tipo_actuacion": act.tipo or "INSPECCION",
        "rubro_nombre": rub.nombre,
        "contribuyente": {"doc_nro": doc, "apellido": "Geo", "nombre": "Tit"},
        "domicilio": {"calle": calle, "numero": numero},
        "inspectores": [],
        **extra,
    }


def test_policy_mismo_texto_no_requiere_geocode_refresh(app_ctx) -> None:
    try:
        suf = uuid4().hex[:8]
        calle = f"PolicyGeo_{suf}"
        dom = Domicilio(calle=calle, numero="100")
        db.session.add(dom)
        db.session.flush()
        policy = resolver_policy_edicion_domicilio(
            domicilio_id=dom.id,
            contexto="ACTUACION",
            origen_id=1,
            cambios={"calle": calle, "numero": "100"},
        )
        assert policy.modo == "EDITAR_MISMA_FILA"
        assert policy.requiere_geocode_refresh is False
        assert domicilio_payload_cambia_texto_geografico(dom, {"calle": calle, "numero": "100"}) is False
    finally:
        db.session.rollback()


def test_cargar_acta_inspeccion_no_cambia_geocode(app_ctx) -> None:
    suf = uuid4().hex[:8]
    act, dom, rub, doc = _mk_actuacion_geocodificada(suf)
    antes = _geo_snapshot(dom.id)
    payload = _payload_put_actuacion(
        act=act,
        rub=rub,
        doc=doc,
        calle=dom.calle,
        numero=dom.numero,
        acta_inspeccion_num=_ot_num(),
    )
    actualizar_actuacion(act.id, payload)
    despues = _geo_snapshot(dom.id)
    _assert_geo_unchanged(antes, despues)
    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None and act_db.inspeccion is not None


def test_cargar_acta_comprobacion_no_cambia_geocode(app_ctx) -> None:
    suf = uuid4().hex[:8]
    act, dom, rub, doc = _mk_actuacion_geocodificada(suf)
    antes = _geo_snapshot(dom.id)
    payload = _payload_put_actuacion(
        act=act,
        rub=rub,
        doc=doc,
        calle=dom.calle,
        numero=dom.numero,
        comprobacion={"acta_num": _ot_num(), "motivo": "Control geocode"},
    )
    actualizar_actuacion(act.id, payload)
    despues = _geo_snapshot(dom.id)
    _assert_geo_unchanged(antes, despues)
    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None and act_db.comprobacion_id is not None


def test_agregar_oficio_no_cambia_geocode(app_ctx) -> None:
    from tests.test_comprobacion_pendientes_reinspeccion_bandeja import (
        _mk_actuacion_solo_expediente_envio,
        _unique_num,
    )

    act_id, jz_id = _mk_actuacion_solo_expediente_envio()
    act = db.session.get(Actuaciones, act_id)
    assert act is not None and act.domicilio_id is not None
    dom_id = int(act.domicilio_id)
    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()
    if geo is None:
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom_id,
                geo_status="OK",
                lat=-26.8241,
                lng=-65.2226,
                addr_hash=compute_addr_hash(dom),
                source="AUTO",
            )
        )
        db.session.commit()
    antes = _geo_snapshot(dom_id)

    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ) as geo_mock:
        complete_oficio_from_actuacion(
            act_id,
            {
                "numero_oficio": f"OF{_unique_num()[:4]}",
                "fecha_oficio": date(2026, 6, 15),
                "juzgado_id": jz_id,
                "numero_expediente_oficio": _unique_num()[:6],
                "fecha_expediente_oficio": date(2026, 6, 15),
            },
        )
        geo_mock.assert_not_called()

    _assert_geo_unchanged(antes, _geo_snapshot(dom_id))


def test_reencolar_local_cerrado_conserva_geocode(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _rb, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    if DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first() is None:
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom_id,
                geo_status="OK",
                lat=-31.42,
                lng=-64.18,
                addr_hash=compute_addr_hash(dom),
            )
        )
        db.session.commit()
    antes = _geo_snapshot(dom_id)

    with patch(
        "app.domains.actuaciones.services.completar_trabajo_cierre_service.on_domicilio_changed"
    ):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
            ),
            ejecutado_por_user_id=user_id,
        )

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None and ini_db.domicilio_id == dom_id
    despues = _geo_snapshot(dom_id)
    _assert_geo_unchanged(antes, despues)


def test_corregir_contraproducencia_conserva_geocode(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _rb, dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    dom = db.session.get(Domicilio, dom_id)
    assert dom is not None
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()
    if geo is not None and geo.addr_hash is None:
        geo.addr_hash = compute_addr_hash(dom)
        db.session.add(geo)
        db.session.commit()
    antes = _geo_snapshot(dom_id)

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    rub = Rubro.query.first()
    assert rub is not None
    doc = (
        str(act.domicilio.contribuyente.documento)
        if act.domicilio and act.domicilio.contribuyente
        else "30123456"
    )
    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren 2 inspectores")
    row = ActuacionGridRowIn.model_validate(
        {
            "id": act_id,
            "orden_trabajo_numero": act.orden_trabajo.numero_acta if act.orden_trabajo else "000001",
            "fecha_actuacion": act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026",
            "tipo_actuacion": "INSPECCION",
            "calle": dom.calle,
            "numero": dom.numero,
            "rubro_nombre": rub.nombre,
            "doc_nro": doc,
            "contrib_apellido": "Reenc",
            "contrib_nombre": "Tit",
            "inspector1": inspectores[0].nombre,
            "inspector2": inspectores[1].nombre,
            "acta_inspeccion_num": _ot_num(),
            "limpiar_contraproducencia": True,
            "contraproducencia": None,
        }
    )
    actualizar_actuacion(act_id, map_actuacion_row(row))
    despues = _geo_snapshot(dom_id)
    _assert_geo_unchanged(antes, despues)


def test_editar_solo_acta_conserva_geocode(app_ctx) -> None:
    """PUT con misma calle/número reenviada (mapper típico) no toca geocode."""
    suf = uuid4().hex[:8]
    act, dom, rub, doc = _mk_actuacion_geocodificada(suf)
    antes = _geo_snapshot(dom.id)
    payload = _payload_put_actuacion(
        act=act,
        rub=rub,
        doc=doc,
        calle=dom.calle,
        numero=dom.numero,
        acta_inspeccion_num=_ot_num(),
    )
    actualizar_actuacion(act.id, payload)
    _assert_geo_unchanged(antes, _geo_snapshot(dom.id))


def test_editar_calle_desde_actuaciones_directa_crud_permite_y_geocode(app_ctx, monkeypatch) -> None:
    """PR7.15b: actuación cargada directa desde CRUD puede corregir calle y dispara geocode."""
    suf = uuid4().hex[:8]
    act, dom, rub, doc = _mk_actuacion_geocodificada(suf)
    nueva_calle = f"{dom.calle} Corregida"
    payload = _payload_put_actuacion(
        act=act,
        rub=rub,
        doc=doc,
        calle=nueva_calle,
        numero=dom.numero,
    )
    called: list[int] = []

    def _fake_on_changed(dom_id: int, force: bool = False) -> dict:
        called.append(dom_id)
        return {"ok": True}

    monkeypatch.setattr(
        "app.domains.actuaciones.services.update_service.on_domicilio_changed",
        _fake_on_changed,
    )
    actualizar_actuacion(act.id, payload)
    db.session.expunge_all()
    act_db = Actuaciones.query.get(act.id)
    dom_db = Domicilio.query.get(act_db.domicilio_id) if act_db else None
    assert dom_db is not None
    assert dom_db.calle == nueva_calle
    assert called


def test_nomenclatura_sigue_pudiendo_disparar_geocode(app_ctx, monkeypatch) -> None:
    from app.domains.geolocalizacion.normalizacion_calles.schemas.guardar_nomenclatura_in import (
        CalleNomenclaturaIn,
        GuardarNomenclaturaIn,
    )
    from app.domains.geolocalizacion.normalizacion_calles.services import (
        guardar_nomenclatura_service,
    )
    from app.domains.geolocalizacion.normalizacion_calles.services.guardar_nomenclatura_service import (
        guardar_nomenclatura_hibrida,
    )

    called: list[int] = []

    def _fake_on_changed(dom_id: int, force: bool = False) -> dict:
        called.append(dom_id)
        return {"ok": True}

    monkeypatch.setattr(guardar_nomenclatura_service, "on_domicilio_changed", _fake_on_changed)
    dom = Domicilio(calle="NomenTest", numero="50")
    db.session.add(dom)
    db.session.flush()
    body = GuardarNomenclaturaIn(
        calle=CalleNomenclaturaIn(mode="MANUAL", calle_texto="NomenTest Canon"),
        numero="50",
        numero_tipo="NUMERO",
    )
    guardar_nomenclatura_hibrida(dom.id, body)
    assert dom.id in called


def test_relevamiento_nuevo_crea_domicilio(app_ctx) -> None:
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere inspector y rubro")
    calle = f"RelGeo_{uuid4().hex[:8]}"
    rel = crear_relevamiento_desde_payload(
        {
            "fecha": "2026-06-20",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": calle, "numero": "42"},
            "rubro_nombre": rub.nombre,
        }
    )
    assert rel.domicilio_id is not None
    dom = db.session.get(Domicilio, rel.domicilio_id)
    assert dom is not None
    assert dom.calle == calle
    assert dom.numero == "42"
