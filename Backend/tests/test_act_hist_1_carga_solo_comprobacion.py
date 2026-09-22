"""ACT-HIST.1 — carga histórica solo acta de comprobación."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.delete_service import eliminar_actuacion
from app.domains.actuaciones.services.expediente_completion_service import (
    complete_expediente_from_actuacion,
)
from app.domains.actuaciones.services.pendientes_service import get_pendientes_expediente
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.search_service import buscar_actuaciones_liviano
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.dup_key import build_dup_key
from app.domains.grid.services.validate_service import GridValidateService
from app.domains.indicadores.services.indicadores_resumen_service import _count_actas_labradas
from app.models import (
    Actuaciones,
    CatalogMotivoComprobacion,
    Contribuyente,
    Domicilio,
    IniciadorRuta,
    OrdenTrabajo,
    RutaItem,
)
from app.models.inspector import Inspector


def _unique_acta() -> str:
    return f"{random.randint(0, 999999):06d}"


def _unique_ot() -> str:
    return f"{random.randint(0, 999999):06d}"


def _inspector_nombre() -> str:
    row = Inspector.query.first()
    if row is None:
        pytest.skip("Se requiere al menos un inspector en catálogo")
    return str(row.nombre)


def _motivo_comprobacion() -> str:
    row = CatalogMotivoComprobacion.query.first()
    if row is None:
        pytest.skip("Se requiere catálogo de motivos de comprobación")
    return str(row.nombre)


def _historical_row(**overrides) -> dict:
    base = {
        "carga_solo_comprobacion": True,
        "fecha_actuacion": "2026-09-21",
        "inspectores": [_inspector_nombre()],
        "contrib_apellido": "Histórico",
        "contrib_nombre": "Apellido",
        "calle": f"Hist {_unique_acta()}",
        "numero": "100",
        "acta_comprobacion_num": _unique_acta(),
        "comprobacion_motivo": _motivo_comprobacion(),
    }
    base.update(overrides)
    return base


def _historical_payload(**overrides) -> dict:
    row = ActuacionGridRowIn.model_validate(_historical_row(**overrides))
    payload = map_actuacion_row(row)
    payload.update(overrides)
    return payload


# --- Validación ---


def test_historical_minimum_valid(app) -> None:
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(_historical_row())
        assert row.carga_solo_comprobacion is True


def test_historical_sin_motivo_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(_historical_row(comprobacion_motivo=None))


def test_historical_sin_titular_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(
                _historical_row(contrib_apellido=None, contrib_nombre=None)
            )


def test_historical_sin_inspectores_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(_historical_row(inspectores=[]))


def test_historical_con_ot_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(_historical_row(orden_trabajo_numero="123456"))


def test_historical_con_dni_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(_historical_row(doc_nro="30123456"))


def test_historical_sin_calle_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(_historical_row(calle=None))


def test_historical_sin_numero_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(_historical_row(numero=None))


def test_historical_con_calle_numero_ok(app) -> None:
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(
            _historical_row(calle="San Martín", numero="100")
        )
        assert row.calle == "San Martín"
        assert row.numero == "100"


def test_historical_con_rubro_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(_historical_row(rubro_nombre="Panadería"))


def test_historical_con_otra_acta_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(_historical_row(acta_inspeccion_num="000111"))


def test_normal_sin_ot_sigue_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(
                {
                    "fecha_actuacion": "2026-09-21",
                    "contraproducencia": "NO HUBO",
                    "calle": "San Martín",
                    "numero": "100",
                }
            )


def test_historical_razon_social_valid(app) -> None:
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(
            _historical_row(
                contrib_apellido=None,
                contrib_nombre=None,
                razon_social="Comercio Histórico SA",
            )
        )
        assert row.razon_social == "Comercio Histórico SA"


def test_historical_solo_nombre_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(
                _historical_row(contrib_apellido=None, contrib_nombre="Solo")
            )


def test_historical_persona_y_razon_reject(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            ActuacionGridRowIn.model_validate(
                _historical_row(razon_social="Ambiguo SA")
            )


# --- Create ---


def test_create_historical_sin_ot(app_ctx) -> None:
    try:
        ot_count_before = OrdenTrabajo.query.count()
        payload = _historical_payload()
        act = crear_actuacion_desde_payload(payload)
        db.session.flush()
        assert act.carga_solo_comprobacion is True
        assert act.orden_trabajo_id is None
        assert act.tipo is None
        assert act.domicilio_id is not None
        dom = Domicilio.query.get(act.domicilio_id)
        assert dom is not None
        assert dom.contribuyente_id is None
        assert dom.rubro_id is None
        assert dom.calle is not None
        assert dom.numero == "100"
        assert act.comprobacion_id is not None
        assert act.titular_apellido_historico == "Histórico"
        assert act.titular_nombre_historico == "Apellido"
        assert OrdenTrabajo.query.count() == ot_count_before
        contrib_count_before = Contribuyente.query.count()
        assert Contribuyente.query.count() == contrib_count_before
        assert len(act.inspector) >= 1
        assert IniciadorRuta.query.filter_by(actuacion_id=act.id).count() == 0
        assert RutaItem.query.filter_by(actuacion_id=act.id).count() == 0
    finally:
        db.session.rollback()


def test_create_no_inferir_inspeccion(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        assert act.tipo is None
        assert act.inspeccion is None
    finally:
        db.session.rollback()


# --- Presenter ---


def test_presenter_historical_titular(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        row = actuacion_to_grid_row(act)
        assert row["contrib_apellido"] == "Histórico"
        assert row["contrib_nombre"] == "Apellido"
        assert row.get("doc_nro") in (None, "")
        assert row.get("orden_trabajo_numero") in (None, "")
        assert row.get("calle") is not None
        assert row.get("numero") == "100"
        assert row.get("rubro_nombre") in (None, "")
    finally:
        db.session.rollback()


# --- Gestión comprobación / expediente ---


def test_gestion_comprobacion_bandeja_historical(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        fl = ActuacionesPendientesFilters.model_validate(
            {
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
                "source_type": "comprobacion",
            }
        )
        acts = get_pendientes_expediente(fl)
        assert act.id in [a.id for a in acts]
    finally:
        db.session.rollback()


def test_expediente_historical_sin_ot_dni(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        result = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_acta(),
                "fecha_expediente": date(2026, 9, 22),
                "source_type": "COMPROBACION",
            },
        )
        assert result["source_type"] == "COMPROBACION"
    finally:
        db.session.rollback()


# --- Search / dup key ---


def test_search_historical_by_titular(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(
            _historical_payload(contrib_apellido="BuscableHist", contrib_nombre="Titular")
        )
        db.session.flush()
        rows = buscar_actuaciones_liviano("BuscableHist", limit=10)
        assert any(r["id"] == act.id for r in rows)
    finally:
        db.session.rollback()


def test_dup_key_historical(app) -> None:
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(_historical_row(acta_comprobacion_num="123"))
        key = build_dup_key(row)
        assert key == ("000123", "2026")


# --- Update / delete ---


def test_update_historical_reject_flag_change(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        with pytest.raises(ValueError, match="histórica en normal"):
            actualizar_actuacion(
                act.id,
                {"carga_solo_comprobacion": False, "fecha_actuacion": "2026-09-22"},
            )
    finally:
        db.session.rollback()


def test_update_historical_reject_ot(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        with pytest.raises(ValueError):
            actualizar_actuacion(
                act.id,
                {"orden_trabajo_numero": _unique_ot(), "fecha_actuacion": "2026-09-21"},
            )
    finally:
        db.session.rollback()


def test_delete_historical_sin_ot_cleanup(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        act_id = act.id
        ot_count = OrdenTrabajo.query.count()
        eliminar_actuacion(act_id)
        assert OrdenTrabajo.query.count() == ot_count
    finally:
        db.session.rollback()


# --- Dashboard ---


def test_dashboard_comprobacion_sin_inspeccion(app_ctx) -> None:
    try:
        act = crear_actuacion_desde_payload(_historical_payload())
        db.session.flush()
        sq = db.session.query(Actuaciones.id).filter(Actuaciones.id == act.id).subquery()
        counts = _count_actas_labradas(sq)
        assert counts.comprobacion >= 1
        assert counts.inspeccion == 0
    finally:
        db.session.rollback()


# --- Grid validate ---


def test_grid_validate_historical_ok(app) -> None:
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="actuaciones")
    with app.app_context():
        resp = svc.validate_row(
            batch_id=batch_id,
            row_id="row-hist",
            raw_row={
                "Cargar solo comprobación": True,
                "Fecha actuación": "2026-09-21",
                "Inspectores": [_inspector_nombre()],
                "Apellido": "Pérez",
                "Nombre": "Juan",
                "Acta comprobación": _unique_acta(),
                "Motivo comprobación": _motivo_comprobacion(),
                "Calle": f"Grid {_unique_acta()}",
                "Número": "50",
            },
            kind="actuaciones",
        )
    assert resp.ok is True
    assert resp.normalized is not None
    assert resp.normalized.get("carga_solo_comprobacion") is True
