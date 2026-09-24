"""resolve_contribuyente: limpieza coherente PF/PJ cuando el payload incluye claves con None."""

from __future__ import annotations

import random

import pytest

from app import create_app
from app.database import db
from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente
from app.models import Contribuyente


def _uniq_doc() -> str:
    return str(random.randint(10000000000, 99999999999))[:11]


@pytest.fixture
def app_ctx():
    app = create_app(
        {
            "TESTING": True,
            "PROPAGATE_EXCEPTIONS": True,
            "JWT_SECRET_KEY": "pytest-jwt-secret-key-32bytes-min",
            "RATELIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        yield app
        db.session.rollback()


def test_pf_luego_rs_limpia_apellido_nombre(app_ctx) -> None:
    doc = _uniq_doc()
    c1 = resolve_contribuyente(
        {
            "doc_nro": doc,
            "apellido": "García",
            "nombre": "Ana",
            "razon_social": None,
        }
    )
    assert c1 is not None
    db.session.flush()
    assert c1.apellido == "García"
    assert c1.nombre == "Ana"
    assert c1.razon_social is None

    c2 = resolve_contribuyente(
        {
            "doc_nro": doc,
            "apellido": None,
            "nombre": None,
            "razon_social": "ACME SA",
        }
    )
    assert c2 is c1
    db.session.refresh(c1)
    assert c1.documento == doc
    assert c1.apellido is None
    assert c1.nombre is None
    assert c1.razon_social == "ACME SA"


def test_rs_luego_pf_limpia_razon_social(app_ctx) -> None:
    doc = _uniq_doc()
    c1 = resolve_contribuyente(
        {
            "doc_nro": doc,
            "apellido": None,
            "nombre": None,
            "razon_social": "Beta SRL",
        }
    )
    assert c1 is not None
    db.session.flush()
    assert c1.razon_social == "Beta SRL"
    assert c1.apellido is None

    c2 = resolve_contribuyente(
        {
            "doc_nro": doc,
            "apellido": "López",
            "nombre": "Luis",
            "razon_social": None,
        }
    )
    assert c2 is c1
    db.session.refresh(c1)
    assert c1.apellido == "López"
    assert c1.nombre == "Luis"
    assert c1.razon_social is None


def test_sin_claves_titular_no_borra_campos_existentes(app_ctx) -> None:
    doc = _uniq_doc()
    resolve_contribuyente(
        {
            "doc_nro": doc,
            "apellido": "Pérez",
            "nombre": "María",
            "razon_social": None,
        }
    )
    db.session.flush()
    cid = Contribuyente.query.filter_by(documento=doc).first().id

    c2 = resolve_contribuyente({"doc_nro": doc})
    assert c2 is not None
    assert c2.id == cid
    db.session.refresh(c2)
    assert c2.apellido == "Pérez"
    assert c2.nombre == "María"


def test_actualizar_solo_razon_social_no_toca_apellido_si_no_viene_clave(app_ctx) -> None:
    doc = _uniq_doc()
    resolve_contribuyente(
        {
            "doc_nro": doc,
            "apellido": "Solo",
            "nombre": "Apellido",
            "razon_social": None,
        }
    )
    db.session.flush()

    c2 = resolve_contribuyente({"doc_nro": doc, "razon_social": "Nueva RS"})
    db.session.refresh(c2)
    assert c2.apellido == "Solo"
    assert c2.nombre == "Apellido"
    assert c2.razon_social == "Nueva RS"

