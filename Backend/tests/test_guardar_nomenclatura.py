"""POST /geolocalizacion/calles/guardar-nomenclatura: nomenclatura híbrida."""

from __future__ import annotations

import random

import pytest

from app.database import db
from app.models import CalleCatalogo, Domicilio


def _rand() -> int:
    return random.randint(100_000, 999_999)


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_calle_catalogo(prefix: str) -> CalleCatalogo:
    n = _rand()
    canon = f"{prefix} Canon {n}"
    key = f"{prefix.lower()}-key-{n}"
    c = CalleCatalogo(nombre_canonico=canon, canon_base=canon, nombre_key=key, activo=True)
    db.session.add(c)
    db.session.flush()
    return c


def _mk_domicilio() -> Domicilio:
    n = _rand()
    d = Domicilio(calle=f"Calle Inicial {n}", numero="100")
    db.session.add(d)
    db.session.flush()
    return d


def test_guardar_nomenclatura_sin_jwt_401(client):
    resp = client.post("/geolocalizacion/calles/guardar-nomenclatura/1", json={})
    assert resp.status_code == 401


def test_guardar_calle_catalogo_y_esquina_manual(app_ctx, client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.guardar_nomenclatura_service.on_domicilio_changed",
        lambda _id: None,
    )
    c1 = _mk_calle_catalogo("CalleCat")
    dom = _mk_domicilio()
    db.session.commit()

    body = {
        "calle": {"mode": "CATALOGO", "calle_catalogo_id": c1.id},
        "numero": "Otra Esquina Libre",
        "numero_tipo": "ESQUINA",
        "esquina": {"mode": "MANUAL"},
    }
    r = client.post(
        f"/geolocalizacion/calles/guardar-nomenclatura/{dom.id}",
        json=body,
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    db.session.expire_all()
    dom2 = db.session.get(Domicilio, dom.id)
    assert dom2 is not None
    assert dom2.calle_catalogo_id == c1.id
    assert dom2.calle_norm_status == "OK"
    assert dom2.numero_tipo == "ESQUINA"
    assert dom2.esquina_catalogo_id is None
    assert dom2.esquina_norm_status == "OK"
    assert dom2.esquina_norm_error == "MANUAL"
    assert dom2.esquina_normalizada == "Otra Esquina Libre"


def test_guardar_calle_manual_y_numero(app_ctx, client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.guardar_nomenclatura_service.on_domicilio_changed",
        lambda _id: None,
    )
    dom = _mk_domicilio()
    db.session.commit()

    body = {
        "calle": {"mode": "MANUAL", "calle_texto": "Calle No Catalogada XYZ"},
        "numero": "500",
        "numero_tipo": "NUMERO",
    }
    r = client.post(
        f"/geolocalizacion/calles/guardar-nomenclatura/{dom.id}",
        json=body,
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    db.session.expire_all()
    dom2 = db.session.get(Domicilio, dom.id)
    assert dom2 is not None
    assert dom2.calle == "Calle No Catalogada XYZ"
    assert dom2.calle_catalogo_id is None
    assert dom2.calle_norm_status == "OK"
    assert dom2.calle_norm_error == "MANUAL"
    assert dom2.calle_normalizada == "Calle No Catalogada XYZ"
    assert dom2.esquina_catalogo_id is None
    assert dom2.numero == "500"


def test_guardar_esquina_catalogo(app_ctx, client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.guardar_nomenclatura_service.on_domicilio_changed",
        lambda _id: None,
    )
    c_main = _mk_calle_catalogo("Main")
    c_esq = _mk_calle_catalogo("Esquina")
    dom = _mk_domicilio()
    db.session.commit()

    body = {
        "calle": {"mode": "CATALOGO", "calle_catalogo_id": c_main.id},
        "numero": "Cualquier texto esquina",
        "numero_tipo": "ESQUINA",
        "esquina": {"mode": "CATALOGO", "esquina_catalogo_id": c_esq.id},
    }
    r = client.post(
        f"/geolocalizacion/calles/guardar-nomenclatura/{dom.id}",
        json=body,
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    db.session.expire_all()
    dom2 = db.session.get(Domicilio, dom.id)
    assert dom2 is not None
    assert dom2.esquina_catalogo_id == c_esq.id
    assert dom2.esquina_norm_status == "OK"
    assert dom2.esquina_normalizada == c_esq.nombre_canonico


def test_guardar_validacion_esquina_con_numero_422(client, auth_headers):
    r = client.post(
        "/geolocalizacion/calles/guardar-nomenclatura/1",
        json={
            "calle": {"mode": "MANUAL", "calle_texto": "X"},
            "numero": "1",
            "numero_tipo": "NUMERO",
            "esquina": {"mode": "MANUAL"},
        },
        headers=auth_headers,
    )
    assert r.status_code == 422
