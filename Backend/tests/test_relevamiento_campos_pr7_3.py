"""
PR7.3 — nombre_fantasia y angulo_esquina en relevamiento (backend).
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_to_row
from app.domains.relevamientos.schemas.grid.relevamiento_row_in import RelevamientoGridRowIn
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.domains.relevamientos.utils.relevamiento_campos_normalizers import (
    normalizar_angulo_esquina,
    normalizar_nombre_fantasia,
    resolver_angulo_esquina_para_persistencia,
)
from app.domains.grid.services.relevamiento_dup_key import build_relevamiento_establishment_key
from app.models import Domicilio, Inspector, Relevamiento, Rubro


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
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


def _payload(
    *,
    calle: str,
    numero: str,
    rubro: str,
    inspector: str,
    fecha: str = "2026-05-10",
    tipo: str | None = None,
    nombre_fantasia: str | None = None,
    angulo_esquina: str | None = None,
):
    dom = {"calle": calle, "numero": numero}
    if tipo:
        dom["numero_tipo"] = tipo
    out = {
        "fecha": fecha,
        "inspector_nombre": inspector,
        "domicilio": dom,
        "rubro_nombre": rubro,
    }
    if nombre_fantasia is not None:
        out["nombre_fantasia"] = nombre_fantasia
    if angulo_esquina is not None:
        out["angulo_esquina"] = angulo_esquina
    return out


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


# --- Normalizadores unitarios ---


def test_pr73_normalizar_nombre_fantasia_vacio_none() -> None:
    assert normalizar_nombre_fantasia(None) is None
    assert normalizar_nombre_fantasia("") is None
    assert normalizar_nombre_fantasia("   ") is None


def test_pr73_normalizar_nombre_fantasia_colapsa_espacios() -> None:
    assert normalizar_nombre_fantasia("  Carnicería   El Toro  ") == "Carnicería El Toro"


def test_pr73_normalizar_angulo_ne() -> None:
    assert normalizar_angulo_esquina("ne") == "NE"


def test_pr73_normalizar_angulo_invalido() -> None:
    with pytest.raises(ValueError, match="Ángulo de esquina inválido"):
        normalizar_angulo_esquina("NORTE")


def test_pr73_resolver_angulo_no_esquina_guarda_null() -> None:
    assert resolver_angulo_esquina_para_persistencia("NE", numero_tipo="NUMERO") is None


def test_pr73_establishment_key_preparada() -> None:
    key = build_relevamiento_establishment_key(
        "Maipú",
        "y Salta",
        mes=5,
        anio=2026,
        rubro_id=3,
        nombre_fantasia="El Toro",
        angulo_esquina="NE",
        es_esquina=True,
    )
    assert "MAIPÚ|Y SALTA" in key
    assert "|R3|" in key
    assert "NFEL TORO" in key
    assert key.endswith("|ANE|M5|Y2026")


# --- Schema ---


def test_pr73_schema_angulo_invalido_422(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    with pytest.raises(ValidationError):
        RelevamientoGridRowIn.model_validate(
            {
                "fecha": "2026-05-10",
                "inspector": ins.nombre,
                "calle": "Test",
                "numero": "100",
                "rubro": rub.nombre,
                "angulo_esquina": "INVALIDO",
            }
        )


# --- Create / update integración ---


def test_pr73_create_con_nombre_fantasia(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("FantasiaPR73")
    try:
        rel = crear_relevamiento_desde_payload(
            _payload(
                calle=calle,
                numero="100",
                rubro=rub.nombre,
                inspector=ins.nombre,
                nombre_fantasia="Carnicería El Toro",
            )
        )
        assert rel.nombre_fantasia == "Carnicería El Toro"
        assert rel.angulo_esquina is None
    finally:
        db.session.rollback()


def test_pr73_create_nombre_fantasia_vacio_null(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("FantasiaVaciaPR73")
    try:
        rel = crear_relevamiento_desde_payload(
            _payload(
                calle=calle,
                numero="101",
                rubro=rub.nombre,
                inspector=ins.nombre,
                nombre_fantasia="   ",
            )
        )
        assert rel.nombre_fantasia is None
    finally:
        db.session.rollback()


def test_pr73_create_angulo_esquina_normalizado(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("AnguloPR73")
    try:
        rel = crear_relevamiento_desde_payload(
            _payload(
                calle=calle,
                numero="y Norte",
                rubro=rub.nombre,
                inspector=ins.nombre,
                tipo="ESQUINA",
                angulo_esquina="se",
            )
        )
        assert rel.angulo_esquina == "SE"
    finally:
        db.session.rollback()


def test_pr73_create_angulo_en_numero_no_persiste(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("AnguloNumPR73")
    try:
        rel = crear_relevamiento_desde_payload(
            _payload(
                calle=calle,
                numero="200",
                rubro=rub.nombre,
                inspector=ins.nombre,
                angulo_esquina="NE",
            )
        )
        assert rel.angulo_esquina is None
    finally:
        db.session.rollback()


def test_pr73_legacy_sin_campos_nuevos(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("LegacyPR73")
    try:
        rel = crear_relevamiento_desde_payload(
            _payload(calle=calle, numero="50", rubro=rub.nombre, inspector=ins.nombre)
        )
        assert rel.nombre_fantasia is None
        assert rel.angulo_esquina is None
    finally:
        db.session.rollback()


def test_pr73_update_modifica_nombre_y_angulo(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("UpdatePR73")
    try:
        rel = crear_relevamiento_desde_payload(
            _payload(
                calle=calle,
                numero="y Sur",
                rubro=rub.nombre,
                inspector=ins.nombre,
                tipo="ESQUINA",
            )
        )
        updated = actualizar_relevamiento(
            rel.id,
            _payload(
                calle=calle,
                numero="y Sur",
                rubro=rub.nombre,
                inspector=ins.nombre,
                tipo="ESQUINA",
                nombre_fantasia="Panadería Sol",
                angulo_esquina="NO",
            ),
        )
        assert updated.nombre_fantasia == "Panadería Sol"
        assert updated.angulo_esquina == "NO"
    finally:
        db.session.rollback()


def test_pr73_update_esquina_a_numero_limpia_angulo(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("LimpiaAngPR73")
    try:
        rel = crear_relevamiento_desde_payload(
            _payload(
                calle=calle,
                numero="y Este",
                rubro=rub.nombre,
                inspector=ins.nombre,
                tipo="ESQUINA",
                angulo_esquina="NE",
            )
        )
        updated = actualizar_relevamiento(
            rel.id,
            _payload(
                calle=calle,
                numero="300",
                rubro=rub.nombre,
                inspector=ins.nombre,
                tipo="NUMERO",
                angulo_esquina="NE",
            ),
        )
        assert updated.angulo_esquina is None
    finally:
        db.session.rollback()


def test_pr73_esquina_dos_rubros_unicidad_actual_ok(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first() or rub
    calle = _uniq("EsquinaDupPR73")
    try:
        crear_relevamiento_desde_payload(
            _payload(
                calle=calle,
                numero="y Oeste",
                rubro=rub.nombre,
                inspector=ins.nombre,
                tipo="ESQUINA",
                angulo_esquina="NE",
            )
        )
        rel2 = crear_relevamiento_desde_payload(
            _payload(
                calle=calle,
                numero="y Oeste",
                rubro=rub2.nombre,
                inspector=ins.nombre,
                tipo="ESQUINA",
                angulo_esquina="SE",
                fecha="2026-05-12",
            )
        )
        assert rel2.angulo_esquina == "SE"
    finally:
        db.session.rollback()


def test_pr73_presenter_devuelve_campos() -> None:
    rel = SimpleNamespace(
        id=1,
        fecha=datetime(2026, 5, 10).date(),
        turno_carga="MANIANA",
        esta_abierto=True,
        nombre_fantasia="La Esquina",
        angulo_esquina="NE",
        inspector=SimpleNamespace(nombre="Inspector Test"),
        domicilio=SimpleNamespace(
            calle="Maipú",
            numero="y Salta",
            calle_normalizada=None,
            calle_norm_status=None,
            calle_norm_score=None,
            calle_catalogo_id=None,
            numero_tipo="ESQUINA",
            esquina_raw="y Salta",
            esquina_normalizada=None,
            esquina_catalogo_id=None,
            esquina_norm_status=None,
            esquina_norm_score=None,
            id=99,
        ),
        rubro=SimpleNamespace(nombre="Carnicería"),
    )
    row = relevamiento_to_row(rel)  # type: ignore[arg-type]
    assert row["nombre_fantasia"] == "La Esquina"
    assert row["angulo_esquina"] == "NE"
