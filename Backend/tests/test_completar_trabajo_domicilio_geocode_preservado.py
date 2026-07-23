"""
Completar Trabajo: edición de domicilio conserva geocode existente.

Regresión del hotfix: ``on_domicilio_changed`` post-cierre no debe invalidar lat/lng
en corrección textual sobre la misma fila.
"""

from __future__ import annotations

import random
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    compute_addr_hash,
)
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    User,
)

from tests.test_completar_trabajo_cierre_domicilio_f3_3 import _mk_item_base


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
        "domicilio_id": dom_id,
        "calle": dom.calle,
        "calle_raw": dom.calle_raw,
        "numero": dom.numero,
        "numero_tipo": dom.numero_tipo,
        "lat": geo.lat if geo else None,
        "lng": geo.lng if geo else None,
        "geo_status": geo.geo_status if geo else None,
        "addr_hash": geo.addr_hash if geo else None,
    }


def _assert_geo_unchanged(before: dict, after: dict) -> None:
    for key in ("lat", "lng", "geo_status"):
        b = before[key]
        a = after[key]
        if key in ("lat", "lng") and b is not None and a is not None:
            assert float(a) == float(b), f"{key}: {b!r} -> {a!r}"
        else:
            assert a == b, f"{key}: {b!r} -> {a!r}"


def _seed_geocode(dom: Domicilio, *, lat=-26.8241, lng=-65.2226) -> None:
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="OK",
            lat=lat,
            lng=lng,
            addr_hash=compute_addr_hash(dom),
            source="AUTO",
        )
    )
    db.session.flush()


def test_completar_trabajo_cambio_calle_conserva_geocode(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, dom, _ini, u, rub = _mk_item_base(suf)
    dom.calle_raw = f"monteagudo_{suf}"
    dom.calle_normalizada = f"Dr Bernardo Monteagudo {suf}"
    dom.calle_norm_status = "OK"
    db.session.add(dom)
    _seed_geocode(dom)
    db.session.commit()
    antes = _geo_snapshot(dom.id)
    nueva_calle = f"monteagudo editado {suf}"

    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ) as geo_hook:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "calle": nueva_calle,
                    "numero": "200",
                    "numero_tipo": "NUMERO",
                    "rubro_nombre": rub.nombre,
                }
            ),
            ejecutado_por_user_id=u.id,
        )
        geo_hook.assert_not_called()

    db.session.expunge_all()
    act_db = (
        Actuaciones.query.filter_by(id=act.id)
        .options(joinedload(Actuaciones.domicilio))
        .first()
    )
    assert act_db is not None and act_db.domicilio_id == dom.id
    despues = _geo_snapshot(dom.id)
    assert despues["calle"] == nueva_calle
    assert despues["calle_raw"] == nueva_calle
    _assert_geo_unchanged(antes, despues)


def test_completar_trabajo_cambio_numero_conserva_geocode(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, dom, _ini, u, rub = _mk_item_base(suf)
    _seed_geocode(dom)
    db.session.commit()
    antes = _geo_snapshot(dom.id)

    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ) as geo_hook:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "calle": dom.calle,
                    "numero": "999",
                    "rubro_nombre": rub.nombre,
                }
            ),
            ejecutado_por_user_id=u.id,
        )
        geo_hook.assert_not_called()

    assert db.session.get(Actuaciones, act.id).domicilio_id == dom.id
    despues = _geo_snapshot(dom.id)
    assert despues["numero"] == "999"
    _assert_geo_unchanged(antes, despues)


def test_completar_trabajo_cambio_esquina_conserva_geocode(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, dom, _ini, u, rub = _mk_item_base(suf)
    dom.numero_tipo = "NUMERO"
    db.session.add(dom)
    _seed_geocode(dom)
    db.session.commit()
    antes = _geo_snapshot(dom.id)

    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ) as geo_hook:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "calle": dom.calle,
                    "numero": "Belgrano",
                    "numero_tipo": "ESQUINA",
                    "rubro_nombre": rub.nombre,
                }
            ),
            ejecutado_por_user_id=u.id,
        )
        geo_hook.assert_not_called()

    assert db.session.get(Actuaciones, act.id).domicilio_id == dom.id
    despues = _geo_snapshot(dom.id)
    assert despues["numero"] == "Belgrano"
    assert despues["numero_tipo"] == "ESQUINA"
    _assert_geo_unchanged(antes, despues)


def test_relevamiento_update_sin_cambio_direccion_conserva_geocode(app_ctx) -> None:
    from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload

    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere inspector y rubro")
    suf = uuid4().hex[:8]
    calle = f"RelGeoPres_{suf}"
    rel = crear_relevamiento_desde_payload(
        {
            "fecha": "20/06/2026",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": calle, "numero": "10"},
            "rubro_nombre": rub.nombre,
        }
    )
    assert rel.domicilio_id is not None
    dom = db.session.get(Domicilio, rel.domicilio_id)
    assert dom is not None
    dom.calle_normalizada = f"Canon {suf}"
    dom.calle_norm_status = "OK"
    db.session.add(dom)
    _seed_geocode(dom)
    db.session.commit()
    antes = _geo_snapshot(dom.id)

    actualizar_relevamiento(
        rel.id,
        {
            "fecha": "21/06/2026",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": calle, "numero": "10"},
            "rubro_nombre": rub.nombre,
        },
    )

    despues = _geo_snapshot(dom.id)
    _assert_geo_unchanged(antes, despues)


def test_completar_trabajo_misma_fila_no_llama_on_domicilio_changed(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, dom, _ini, u, rub = _mk_item_base(suf)
    _seed_geocode(dom)
    db.session.commit()

    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ) as geo_hook:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "calle": f"CambioGeo_{suf}",
                    "numero": "55",
                    "rubro_nombre": rub.nombre,
                }
            ),
            ejecutado_por_user_id=u.id,
        )
        geo_hook.assert_not_called()

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert geo is not None
    assert geo.lat is not None
    assert geo.lng is not None
    assert geo.geo_status == "OK"


def test_completar_trabajo_esquina_a_numero_conserva_geocode(app_ctx) -> None:
    """ESQUINA → NUMERO (ej. San Martín y Maipú → Maipú 500): conserva lat/lng del origen."""
    suf = uuid4().hex[:8]
    item, act, dom, _ini, u, rub = _mk_item_base(suf)
    dom.calle = f"San Martin {suf}"
    dom.numero = f"Maipu {suf}"
    dom.numero_tipo = "ESQUINA"
    db.session.add(dom)
    _seed_geocode(dom, lat=-26.8300, lng=-65.2300)
    db.session.commit()
    antes = _geo_snapshot(dom.id)

    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ) as geo_hook:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "calle": f"Maipu {suf}",
                    "numero": "500",
                    "numero_tipo": "NUMERO",
                    "rubro_nombre": rub.nombre,
                }
            ),
            ejecutado_por_user_id=u.id,
        )
        geo_hook.assert_not_called()

    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    despues = _geo_snapshot(act_db.domicilio_id)
    assert despues["numero"] == "500"
    assert despues["numero_tipo"] == "NUMERO"
    _assert_geo_unchanged(antes, despues)


def test_completar_trabajo_corrige_interseccion_conserva_geocode(app_ctx) -> None:
    """Corrección textual de intersección sin mover el punto en mapa."""
    suf = uuid4().hex[:8]
    item, act, dom, _ini, u, rub = _mk_item_base(suf)
    dom.calle = f"San Lorenzo {suf}"
    dom.numero = f"Agustin Mazza {suf}"
    dom.numero_tipo = "ESQUINA"
    db.session.add(dom)
    _seed_geocode(dom)
    db.session.commit()
    antes = _geo_snapshot(dom.id)
    nueva_esquina = f"Agustin M. Mazza {suf}"

    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ) as geo_hook:
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "calle": f"San Lorenzo {suf}",
                    "numero": nueva_esquina,
                    "numero_tipo": "ESQUINA",
                    "rubro_nombre": rub.nombre,
                }
            ),
            ejecutado_por_user_id=u.id,
        )
        geo_hook.assert_not_called()

    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    despues = _geo_snapshot(act_db.domicilio_id)
    assert despues["numero"] == nueva_esquina
    _assert_geo_unchanged(antes, despues)
