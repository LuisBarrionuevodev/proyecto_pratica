"""STAB-10b — M4 fields=minimal para mapa de planificación."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.presenters.ruta_presenters import (
    iniciador_pendiente_present,
    iniciador_pendiente_to_map_pin,
    iniciador_pendiente_to_row,
)
from app.domains.rutas_trabajo.schemas.planificacion_in import PlanificacionPendientesContextoQuery
from app.models import Domicilio, IniciadorRuta, User


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


_HEAVY_ROW_KEYS = frozenset(
    {
        "turno_sugerido",
        "observaciones",
        "elegible_urgente",
    }
)

_MAP_PIN_KEYS = frozenset(
    {
        "id",
        "tipo_iniciador",
        "estado_iniciador",
        "fecha_origen",
        "prioridad",
        "prioridad_categoria",
        "domicilio_texto",
        "distrito_id",
        "distrito_nombre",
        "rubro_nombre",
        "nombre_fantasia",
        "angulo_esquina",
        "domicilio",
        "origen",
        "lat",
        "lng",
        "geo_status",
        "badges",
        "identificadores",
    }
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _ensure_user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u:
        return u
    u = User(
        username=f"m4f_{_unique_num()}",
        email=f"m4f_{_unique_num()}@test.local",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def test_planificacion_m4_query_fields_default_full():
    q = PlanificacionPendientesContextoQuery.model_validate({"distrito_id": 1})
    assert q.fields == "full"


def test_planificacion_m4_query_fields_minimal_normalizado():
    q = PlanificacionPendientesContextoQuery.model_validate(
        {"distrito_id": 2, "fields": " MINIMAL "}
    )
    assert q.fields == "minimal"


def test_planificacion_m4_query_fields_invalido_cae_a_full():
    q = PlanificacionPendientesContextoQuery.model_validate(
        {"distrito_id": 3, "fields": "mapa"}
    )
    assert q.fields == "full"


def test_presenter_minimal_recorta_campos_pesados(app_ctx) -> None:
    try:
        dom = Domicilio(calle=f"M4F{_unique_num()}", numero="10")
        db.session.add(dom)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            prioridad=5,
            turno_sugerido="MANIANA",
            observaciones="nota larga de prueba",
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        full = iniciador_pendiente_to_row(ini)
        minimal = iniciador_pendiente_to_map_pin(ini)
        via_present = iniciador_pendiente_present(ini, fields="minimal")

        assert set(minimal.keys()) == _MAP_PIN_KEYS
        assert minimal == via_present
        assert minimal["id"] == full["id"]
        assert minimal["lat"] == full["lat"]
        assert minimal["lng"] == full["lng"]
        assert minimal["distrito_id"] == full["distrito_id"]

        for heavy in _HEAVY_ROW_KEYS:
            assert heavy in full
            assert heavy not in minimal

        assert minimal["origen"]["tipo"] == full["origen"]["tipo"]
    finally:
        db.session.rollback()
