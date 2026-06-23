"""
HOTFIX — Relevamientos deben crear/vincular filas en ``domicilio``.

Cubre alta individual, reutilización, edición y errores controlados.
"""

from __future__ import annotations

import random
from uuid import uuid4

import pytest

from app.database import db
from app.domains.denuncias.services.denuncias_service import crear_denuncia_con_iniciador
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.models import Domicilio, Inspector, Relevamiento, Rubro


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _uniq(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _inspector_y_rubro() -> tuple[Inspector, Rubro]:
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere inspector y rubro en BD")
    return ins, rub


def _payload_relevamiento(
    *,
    calle: str,
    numero: str,
    ins: Inspector,
    rub: Rubro,
    fecha: str = "2026-06-02",
) -> dict:
    return {
        "fecha": fecha,
        "inspector_nombre": ins.nombre,
        "domicilio": {"calle": calle, "numero": numero},
        "rubro_nombre": rub.nombre,
    }


def test_crear_relevamiento_crea_domicilio_y_vincula(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("TestRelevamientoDomicilio")
    rel = crear_relevamiento_desde_payload(
        _payload_relevamiento(calle=calle, numero="123", ins=ins, rub=rub)
    )
    assert rel.domicilio_id is not None
    dom = db.session.get(Domicilio, rel.domicilio_id)
    assert dom is not None
    assert dom.deleted_at is None
    assert dom.calle == calle
    assert dom.numero == "123"


def test_crear_relevamiento_reutiliza_domicilio_existente(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("RelDomReuse")
    p = _payload_relevamiento(calle=calle, numero="456", ins=ins, rub=rub)
    r1 = crear_relevamiento_desde_payload(p)
    with pytest.raises(ValueError, match="Ya existe un relevamiento activo"):
        crear_relevamiento_desde_payload({**p, "fecha": "2026-06-03", "rubro_nombre": rub.nombre})
    count = Domicilio.query.filter(
        Domicilio.calle == calle,
        Domicilio.numero == "456",
        Domicilio.deleted_at.is_(None),
    ).count()
    assert count == 1
    assert r1.domicilio_id is not None


def test_editar_relevamiento_cambia_calle_misma_fila(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("RelDomEdit")
    rel = crear_relevamiento_desde_payload(
        _payload_relevamiento(calle=calle, numero="10", ins=ins, rub=rub)
    )
    dom_id_antes = rel.domicilio_id
    nueva_calle = calle + " Sur"
    actualizar_relevamiento(
        rel.id,
        _payload_relevamiento(calle=nueva_calle, numero="10", ins=ins, rub=rub, fecha="2026-06-03"),
    )
    db.session.refresh(rel)
    dom = db.session.get(Domicilio, dom_id_antes)
    assert rel.domicilio_id == dom_id_antes
    assert dom is not None and dom.calle == nueva_calle


def test_crear_relevamiento_sin_calle_falla(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    with pytest.raises(ValueError, match="Calle y número"):
        crear_relevamiento_desde_payload(
            {
                "fecha": "2026-06-02",
                "inspector_nombre": ins.nombre,
                "domicilio": {"calle": "", "numero": "1"},
                "rubro_nombre": rub.nombre,
            }
        )


def test_denuncia_sigue_creando_domicilio(app_ctx) -> None:
    from datetime import date
    from unittest.mock import patch

    calle = _uniq("DenDomHotfix")
    with patch(
        "app.domains.denuncias.services.denuncias_service._get_current_user_id",
        return_value=1,
    ):
        den, _ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 6, 2),
            domicilio_id=None,
            calle=calle,
            numero="99",
            interseccion=None,
            motivo="Prueba hotfix domicilio",
        )
    assert den.domicilio_id is not None
    dom = db.session.get(Domicilio, den.domicilio_id)
    assert dom is not None and dom.calle == calle


def test_relevamiento_count_con_domicilio_id(app_ctx) -> None:
    """Sanidad: no debe haber relevamientos activos huérfanos de domicilio."""
    nulls = (
        Relevamiento.query.filter(
            Relevamiento.deleted_at.is_(None),
            Relevamiento.domicilio_id.is_(None),
        ).count()
    )
    assert nulls == 0
