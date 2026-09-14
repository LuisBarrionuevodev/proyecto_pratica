"""
RELEVADORES.1 — entidad Relevador, junction N:N y contratos de relevamiento.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.relevamientos.catalogs.relevador import listar_relevadores_catalogo
from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_to_row
from app.domains.relevamientos.schemas.grid.relevamiento_row_in import RelevamientoGridRowIn
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.relevamiento_iniciador_service import (
    get_or_create_iniciador_from_relevamiento,
)
from app.models import IniciadorRuta, Relevador, Relevamiento
from tests.relevamiento_test_helpers import (
    get_or_create_test_relevador,
    get_test_rubro,
    relevamiento_create_payload,
    require_relevadores_migration,
    uniq,
)


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


@pytest.fixture
def require_rel_migration(app_ctx):
    require_relevadores_migration()


def _crear_segundo_relevador(nombre: str = "Otro Relevador QA") -> Relevador:
    row = Relevador.query.filter(Relevador.nombre == nombre).first()
    if row is None:
        row = Relevador(nombre=nombre, activo=True)
        db.session.add(row)
        db.session.commit()
    return row


def test_catalogo_relevadores_activos(require_rel_migration) -> None:
    fabian = get_or_create_test_relevador()
    items = listar_relevadores_catalogo(solo_activos=True)
    ids = {i["id"] for i in items}
    assert fabian.id in ids


def test_crear_relevamiento_un_relevador(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("Rel1")
    payload = relevamiento_create_payload(
        calle=calle,
        numero="200",
        rubro=rub.nombre,
        relevador_nombre=rel.nombre,
    )
    created = crear_relevamiento_desde_payload(payload)
    assert len(created.relevadores) == 1
    assert created.relevadores[0].id == rel.id
    assert created.inspector_id is None


def test_crear_relevamiento_varios_relevadores(require_rel_migration) -> None:
    r1 = get_or_create_test_relevador()
    r2 = _crear_segundo_relevador()
    rub = get_test_rubro()
    payload = relevamiento_create_payload(
        calle=uniq("RelN"),
        numero="201",
        rubro=rub.nombre,
        relevadores_nombres=[r1.nombre, r2.nombre],
    )
    created = crear_relevamiento_desde_payload(payload)
    assert {r.id for r in created.relevadores} == {r1.id, r2.id}


def test_sin_relevador_422(require_rel_migration) -> None:
    rub = get_test_rubro()
    with pytest.raises(ValidationError):
        RelevamientoGridRowIn.model_validate(
            {
                "calle": "X",
                "numero": "1",
                "rubro": rub.nombre,
            }
        )


def test_relevador_inexistente(require_rel_migration) -> None:
    rub = get_test_rubro()
    with pytest.raises(ValidationError):
        RelevamientoGridRowIn.model_validate(
            {
                "relevador": "No Existe Relevador XYZ",
                "calle": "X",
                "numero": "1",
                "rubro": rub.nombre,
            }
        )


def test_relevador_inactivo_rechazado(require_rel_migration) -> None:
    rub = get_test_rubro()
    inactivo = Relevador(nombre=uniq("Inactivo"), activo=False)
    db.session.add(inactivo)
    db.session.commit()
    with pytest.raises(ValidationError):
        RelevamientoGridRowIn.model_validate(
            {
                "relevador": inactivo.nombre,
                "calle": "X",
                "numero": "1",
                "rubro": rub.nombre,
            }
        )


def test_historico_conserva_inactivo(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    payload = relevamiento_create_payload(
        calle=uniq("Hist"),
        numero="202",
        rubro=rub.nombre,
        relevador_nombre=rel.nombre,
    )
    created = crear_relevamiento_desde_payload(payload)
    rel.activo = False
    db.session.add(rel)
    db.session.commit()
    row = relevamiento_to_row(created)
    assert row["relevadores_label"] == rel.nombre
    assert row["relevadores"][0]["nombre"] == rel.nombre


def test_presenter_relevadores_label(require_rel_migration) -> None:
    r1 = get_or_create_test_relevador()
    r2 = _crear_segundo_relevador()
    rub = get_test_rubro()
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=uniq("Lbl"),
            numero="203",
            rubro=rub.nombre,
            relevadores_nombres=[r1.nombre, r2.nombre],
        )
    )
    row = relevamiento_to_row(created)
    assert " · " in (row["relevadores_label"] or "")
    assert len(row["relevadores"]) == 2


def test_iniciador_no_hereda_relevadores_como_inspectores(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=uniq("Ini"),
            numero="204",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
        )
    )
    iniciador = (
        IniciadorRuta.query.filter_by(relevamiento_id=created.id, deleted_at=None)
        .order_by(IniciadorRuta.id.desc())
        .first()
    )
    assert iniciador is not None
    assert created.inspector_id is None
    # IDs de catálogos distintos pueden coincidir numéricamente; verificar aislamiento semántico.
    assert not hasattr(iniciador, "inspector_id") or getattr(iniciador, "inspector_id", None) is None
    from app.models import Inspector

    inspector_mismo_id = Inspector.query.filter_by(id=rel.id).first()
    if inspector_mismo_id is not None:
        assert inspector_mismo_id.nombre != rel.nombre


def test_duplicado_nombres_rechazado(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    with pytest.raises(ValidationError):
        RelevamientoGridRowIn.model_validate(
            {
                "relevador": f"{rel.nombre}, {rel.nombre}",
                "calle": "X",
                "numero": "1",
                "rubro": rub.nombre,
            }
        )
