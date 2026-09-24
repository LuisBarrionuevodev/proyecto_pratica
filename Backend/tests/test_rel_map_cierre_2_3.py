"""
REL-MAP-CIERRE.2-3 — paridad modal/batch, relevador único, PUT sin fecha, texto libre.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.relevamientos.mappers.grid.relevamiento_row_mapper import map_relevamiento_row
from app.domains.relevamientos.schemas.grid.relevamiento_row_in import RelevamientoGridRowIn
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from tests.relevamiento_test_helpers import (
    get_or_create_test_relevador,
    get_test_rubro,
    relevamiento_create_payload,
    require_relevadores_migration,
    uniq,
)


@pytest.fixture
def require_rel_migration(app_ctx):
    require_relevadores_migration()


def _crear_segundo_relevador(nombre: str = "Otro Relevador QA") -> object:
    from app.models import Relevador

    row = Relevador.query.filter(Relevador.nombre == nombre).first()
    if row is None:
        row = Relevador(nombre=nombre, activo=True)
        db.session.add(row)
        db.session.commit()
    return row


def test_update_sin_fecha_preserva_fecha_original(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=uniq("FechaPres"),
            numero="300",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
            fecha="2024-11-05",
        )
    )
    row = RelevamientoGridRowIn.model_validate(
        {
            "calle": created.domicilio.calle,
            "numero": created.domicilio.numero,
            "rubro": rub.nombre,
            "relevador_ids": [rel.id],
            "turno": "TARDE",
        },
        context={"allow_missing_relevador": True},
    )
    payload = map_relevamiento_row(row)
    assert "fecha" not in payload
    updated = actualizar_relevamiento(created.id, payload)
    assert updated.fecha.isoformat() == "2024-11-05"
    assert updated.mes == 11
    assert updated.anio == 2024


def test_schema_acepta_relevador_id_canonico(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    row = RelevamientoGridRowIn.model_validate(
        {
            "relevador_id": rel.id,
            "calle": "Calle Libre",
            "numero": "10",
            "rubro": rub.nombre,
        }
    )
    assert row.relevador_ids_resueltos() == [rel.id]


def test_schema_ignora_relevadores_dto_si_hay_ids(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    row = RelevamientoGridRowIn.model_validate(
        {
            "relevador_ids": [rel.id],
            "relevadores": [{"id": rel.id, "nombre": rel.nombre}],
            "calle": "Calle Libre",
            "numero": "11",
            "rubro": rub.nombre,
        },
        context={"allow_missing_relevador": True},
    )
    payload = map_relevamiento_row(row)
    assert payload["relevador_ids"] == [rel.id]
    assert payload["relevadores_nombres"] == []


def test_cero_relevadores_error(require_rel_migration) -> None:
    rub = get_test_rubro()
    with pytest.raises(ValidationError):
        RelevamientoGridRowIn.model_validate(
            {"calle": "X", "numero": "1", "rubro": rub.nombre}
        )


def test_mas_de_un_relevador_id_error(require_rel_migration) -> None:
    r1 = get_or_create_test_relevador()
    r2 = _crear_segundo_relevador()
    rub = get_test_rubro()
    with pytest.raises(ValidationError):
        RelevamientoGridRowIn.model_validate(
            {
                "relevador_ids": [r1.id, r2.id],
                "calle": "X",
                "numero": "1",
                "rubro": rub.nombre,
            }
        )


def test_texto_calle_no_catalogada_guardado_ok(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("CalleSinCatalogoXYZ")
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=calle,
            numero="400",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
        )
    )
    assert created.domicilio.calle == calle


def test_texto_esquina_no_catalogada_guardado_ok(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("EsquinaPrin")
    esquina = uniq("PiedrasLibre")
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=calle,
            numero=esquina,
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
            domicilio={"calle": calle, "numero": esquina, "numero_tipo": "ESQUINA"},
        )
    )
    assert created.domicilio.numero == esquina
    assert created.domicilio.numero_tipo == "ESQUINA"


def test_legacy_multi_preserva_junction_sin_relevador_en_put(require_rel_migration) -> None:
    r1 = get_or_create_test_relevador()
    r2 = _crear_segundo_relevador()
    rub = get_test_rubro()
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=uniq("Legacy"),
            numero="500",
            rubro=rub.nombre,
            relevador_nombre=r1.nombre,
        )
    )
    created.relevadores.append(r2)
    db.session.add(created)
    db.session.commit()
    assert len(created.relevadores) == 2

    row = RelevamientoGridRowIn.model_validate(
        {
            "calle": created.domicilio.calle,
            "numero": created.domicilio.numero,
            "rubro": rub.nombre,
            "nombre_fantasia": "Local histórico",
        },
        context={"allow_missing_relevador": True},
    )
    updated = actualizar_relevamiento(created.id, map_relevamiento_row(row))
    assert len(updated.relevadores) == 2
    assert {r.id for r in updated.relevadores} == {r1.id, r2.id}
    assert updated.nombre_fantasia == "Local histórico"


def test_legacy_multi_rechaza_cambio_relevador(require_rel_migration) -> None:
    r1 = get_or_create_test_relevador()
    r2 = _crear_segundo_relevador()
    rub = get_test_rubro()
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=uniq("LegacyChg"),
            numero="501",
            rubro=rub.nombre,
            relevador_nombre=r1.nombre,
        )
    )
    created.relevadores.append(r2)
    db.session.add(created)
    db.session.commit()

    row = RelevamientoGridRowIn.model_validate(
        {
            "calle": created.domicilio.calle,
            "numero": created.domicilio.numero,
            "rubro": rub.nombre,
            "relevador_ids": [r1.id],
        },
        context={"allow_missing_relevador": True},
    )
    with pytest.raises(ValueError, match="varios relevadores históricos"):
        actualizar_relevamiento(created.id, map_relevamiento_row(row))


def test_inspector_id_no_se_usa_como_relevador(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=uniq("Insp"),
            numero="600",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
        )
    )
    assert created.inspector_id is None
    assert len(created.relevadores) == 1
    assert created.relevadores[0].id == rel.id
