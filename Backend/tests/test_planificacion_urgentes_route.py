"""STAB-10b-HOTFIX — regresión endpoint M3 urgentes (presenter import)."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.schemas.planificacion_in import PlanificacionUrgentesQuery
from app.models import Domicilio, IniciadorRuta, RutaTrabajo, User


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"uhf_{_unique_num()}",
        email=f"uhf_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_ruta_borrador(u: User) -> RutaTrabajo:
    ruta = RutaTrabajo(
        fecha=date.today(),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    return ruta


def test_planificacion_urgentes_query_todos_se_normaliza_a_none():
    q = PlanificacionUrgentesQuery.model_validate({"tipo_urgente": "TODOS"})
    assert q.tipo_urgente is None


def test_planificacion_urgentes_route_sin_filtros_200(client, auth_headers, app_ctx):
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    dom = Domicilio(calle=f"UHF{_unique_num()}", numero="1")
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="DENUNCIA",
        estado_iniciador="PENDIENTE",
        fecha_origen=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom.id,
        prioridad=3,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.commit()

    rv = client.get(
        f"/rutas-trabajo/{ruta.id}/planificacion/urgentes",
        headers=auth_headers,
        query_string={"page": 1, "per_page": 25},
    )
    assert rv.status_code == 200, rv.get_data(as_text=True)
    body = rv.get_json()
    assert isinstance(body.get("items"), list)
    assert body.get("meta", {}).get("total") is not None


@pytest.mark.parametrize(
    "query_string",
    [
        {"tipo_urgente": "DENUNCIA"},
        {"tipo_urgente": "NOTIFICACION"},
        {"tipo_urgente": "OFICIO"},
        {"q": "san"},
        {"numero_oficio": "123"},
        {"numero_comprobacion": "456"},
        {"tipo_urgente": "TODOS"},
    ],
)
def test_planificacion_urgentes_route_filtros_200(
    client, auth_headers, app_ctx, query_string
):
    u = _mk_user()
    ruta = _mk_ruta_borrador(u)
    db.session.commit()

    rv = client.get(
        f"/rutas-trabajo/{ruta.id}/planificacion/urgentes",
        headers=auth_headers,
        query_string={"page": 1, "per_page": 25, **query_string},
    )
    assert rv.status_code == 200, rv.get_data(as_text=True)
