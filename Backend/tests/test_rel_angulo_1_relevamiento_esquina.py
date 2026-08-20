"""REL-ANGULO.1 — Persistencia y DTO de angulo_esquina en relevamientos ESQUINA."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.database import db
from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_to_row
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.models import Domicilio, Inspector, Rubro


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _migration_pr72_aplicada() -> bool:
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("relevamiento")}
    return "nombre_fantasia" in cols and "angulo_esquina" in cols


@pytest.fixture
def require_pr72_migration(app_ctx):
    if not _migration_pr72_aplicada():
        pytest.skip("Requiere migración PR7.2 (revision b7e8f9a0c1d2) aplicada en BD")


def _inspector_y_rubro():
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere al menos un inspector y un rubro en la BD de test")
    return ins, rub


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _payload_esquina(
    *,
    calle: str,
    numero: str,
    rubro: str,
    inspector: str,
    angulo_esquina: str | None = None,
    numero_tipo: str | None = None,
):
    dom = {"calle": calle, "numero": numero}
    if numero_tipo:
        dom["numero_tipo"] = numero_tipo
    out = {
        "fecha": "2026-05-10",
        "inspector_nombre": inspector,
        "domicilio": dom,
        "rubro_nombre": rubro,
    }
    if angulo_esquina is not None:
        out["angulo_esquina"] = angulo_esquina
    return out


def test_rel_angulo_1_create_esquina_sin_numero_tipo_persiste_angulo(
    app_ctx, require_pr72_migration
) -> None:
    """Regresión grilla: sin numero_tipo explícito pero número tipo esquina."""
    ins, rub = _inspector_y_rubro()
    calle = _uniq("RelAnguloCreate")
    rel = crear_relevamiento_desde_payload(
        _payload_esquina(
            calle=calle,
            numero="y Mitre",
            rubro=rub.nombre,
            inspector=ins.nombre,
            angulo_esquina="NE",
        )
    )
    assert rel.angulo_esquina == "NE"
    row = relevamiento_to_row(rel)
    assert row["angulo_esquina"] == "NE"


def test_rel_angulo_1_update_esquina_cambia_angulo(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("RelAnguloUpd")
    rel = crear_relevamiento_desde_payload(
        _payload_esquina(
            calle=calle,
            numero="y San Martín",
            rubro=rub.nombre,
            inspector=ins.nombre,
            angulo_esquina="NE",
            numero_tipo="ESQUINA",
        )
    )
    updated = actualizar_relevamiento(
        rel.id,
        _payload_esquina(
            calle=calle,
            numero="y San Martín",
            rubro=rub.nombre,
            inspector=ins.nombre,
            angulo_esquina="SO",
            numero_tipo="ESQUINA",
        ),
    )
    assert updated.angulo_esquina == "SO"
    assert relevamiento_to_row(updated)["angulo_esquina"] == "SO"


def test_rel_angulo_1_cambio_a_numero_limpia_angulo(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("RelAnguloNum")
    rel = crear_relevamiento_desde_payload(
        _payload_esquina(
            calle=calle,
            numero="y Colón",
            rubro=rub.nombre,
            inspector=ins.nombre,
            angulo_esquina="SE",
            numero_tipo="ESQUINA",
        )
    )
    updated = actualizar_relevamiento(
        rel.id,
        _payload_esquina(
            calle=calle,
            numero="1200",
            rubro=rub.nombre,
            inspector=ins.nombre,
            angulo_esquina="SE",
            numero_tipo="NUMERO",
        ),
    )
    assert updated.angulo_esquina is None


def test_rel_angulo_1_unicidad_mismo_angulo_bloquea(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("RelAnguloDup")
    numero = "y Rivadavia"
    base = _payload_esquina(
        calle=calle,
        numero=numero,
        rubro=rub.nombre,
        inspector=ins.nombre,
        angulo_esquina="NE",
        numero_tipo="ESQUINA",
    )
    crear_relevamiento_desde_payload(base)
    with pytest.raises(ValueError):
        crear_relevamiento_desde_payload({**base, "fecha": "2026-05-11"})


def test_rel_angulo_1_unicidad_distinto_angulo_permite(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("RelAnguloDist")
    numero = "y Belgrano"
    base = _payload_esquina(
        calle=calle,
        numero=numero,
        rubro=rub.nombre,
        inspector=ins.nombre,
        angulo_esquina="NE",
        numero_tipo="ESQUINA",
    )
    r1 = crear_relevamiento_desde_payload(base)
    r2 = crear_relevamiento_desde_payload(
        {**base, "fecha": "2026-05-12", "angulo_esquina": "NO"}
    )
    assert r1.angulo_esquina == "NE"
    assert r2.angulo_esquina == "NO"
    dom = db.session.get(Domicilio, r1.domicilio_id)
    assert dom is not None
    assert dom.numero_tipo == "ESQUINA"
