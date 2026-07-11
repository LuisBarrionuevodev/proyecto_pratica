"""
PR7.6 — Recambio de rubro/nombre en domicilio NUMERO/OTRO.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest

from app.database import db
from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.relevamiento_dup_key import build_relevamiento_establishment_key
from app.domains.grid.services.validate_service import GridValidateService
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.relevamiento_duplicados_audit_service import (
    auditar_relevamientos_duplicados,
)
from app.domains.relevamientos.services.relevamiento_unicidad_service import (
    RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG,
    RELEVAMIENTO_UNICIDAD_NUMERO_MSG,
)
from app.models import IniciadorRuta, Inspector, Relevamiento, Rubro


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
        pytest.skip("Requiere migración PR7.2 aplicada en BD")


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
    fecha: str = "2026-07-01",
    nombre_fantasia: str | None = None,
):
    out = {
        "fecha": fecha,
        "inspector_nombre": inspector,
        "domicilio": {"calle": calle, "numero": numero},
        "rubro_nombre": rubro,
    }
    if nombre_fantasia is not None:
        out["nombre_fantasia"] = nombre_fantasia
    return out


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def test_pr76_numero_recambio_rubro_crea_iniciador_nuevo(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first()
    if not rub2:
        pytest.skip("Se requiere segundo rubro")
    calle = _uniq("RecambioRubro")
    try:
        p1 = _payload(calle=calle, numero="234", rubro=rub.nombre, inspector=ins.nombre)
        r1 = crear_relevamiento_desde_payload(p1)
        p2 = {**p1, "fecha": "2026-07-02", "rubro_nombre": rub2.nombre}
        r2 = crear_relevamiento_desde_payload(p2)
        assert r1.domicilio_id == r2.domicilio_id
        ini1 = IniciadorRuta.query.filter_by(relevamiento_id=r1.id, deleted_at=None).count()
        ini2 = IniciadorRuta.query.filter_by(relevamiento_id=r2.id, deleted_at=None).count()
        assert ini1 >= 1
        assert ini2 >= 1
    finally:
        db.session.rollback()


def test_pr76_numero_mismo_nombre_normalizado_bloquea(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("NomNorm")
    try:
        p1 = _payload(
            calle=calle,
            numero="10",
            rubro=rub.nombre,
            inspector=ins.nombre,
            nombre_fantasia="Mi Local",
        )
        crear_relevamiento_desde_payload(p1)
        with pytest.raises(ValueError, match="establecimiento en el mismo domicilio"):
            crear_relevamiento_desde_payload(
                {**p1, "fecha": "2026-07-03", "nombre_fantasia": "  mi   local "}
            )
    finally:
        db.session.rollback()


def test_pr76_numero_soft_delete_permite_nuevo(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("NumSD")
    try:
        p = _payload(calle=calle, numero="20", rubro=rub.nombre, inspector=ins.nombre)
        rel = crear_relevamiento_desde_payload(p)
        rel.deleted_at = datetime.utcnow()
        db.session.commit()
        crear_relevamiento_desde_payload({**p, "fecha": "2026-07-04"})
    finally:
        db.session.rollback()


def test_pr76_esquina_regla_pr75_intacta(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqIntacta")
    try:
        p = {
            **_payload(calle=calle, numero="y Test", rubro=rub.nombre, inspector=ins.nombre),
            "domicilio": {"calle": calle, "numero": "y Test", "numero_tipo": "ESQUINA"},
            "angulo_esquina": "NE",
        }
        crear_relevamiento_desde_payload(p)
        with pytest.raises(ValueError, match=RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG[:30]):
            crear_relevamiento_desde_payload({**p, "fecha": "2026-07-05"})
    finally:
        db.session.rollback()


def test_pr76_auditoria_multi_establecimiento_numero(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first()
    if not rub2:
        pytest.skip("Se requiere segundo rubro")
    calle = _uniq("AudMultiNum")
    try:
        from app.models import Domicilio

        dom = Domicilio(calle=calle, numero="55", numero_tipo="NUMERO")
        db.session.add(dom)
        db.session.flush()
        db.session.add_all(
            [
                Relevamiento(
                    fecha=date(2026, 7, 1),
                    mes=7,
                    anio=2026,
                    domicilio_id=dom.id,
                    rubro_id=rub.id,
                    inspector_id=ins.id,
                ),
                Relevamiento(
                    fecha=date(2026, 7, 2),
                    mes=7,
                    anio=2026,
                    domicilio_id=dom.id,
                    rubro_id=rub2.id,
                    inspector_id=ins.id,
                    nombre_fantasia="Nuevo Local",
                ),
            ]
        )
        db.session.flush()
        result = auditar_relevamientos_duplicados()
        assert any(
            g.tipo == "multi_establecimiento_numero" and g.domicilio_id == dom.id
            for g in result.grupos
        )
    finally:
        db.session.rollback()


def test_pr76_batch_numero_duplicado_exacto_en_lote(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    calle = _uniq("BatchDup")
    raw = {
        "fecha": "2026-07-06",
        "inspector": ins.nombre,
        "calle": calle,
        "numero": "99",
        "rubro": rub.nombre,
    }
    assert svc.validate_row(batch_id, "a", raw, "relevamientos").ok is True
    r2 = svc.validate_row(batch_id, "b", {**raw, "fecha": "2026-07-07"}, "relevamientos")
    assert r2.ok is False
    assert RELEVAMIENTO_UNICIDAD_NUMERO_MSG in (r2.errors.get("_row") or "")


def test_pr76_batch_numero_distinto_rubro_en_lote(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first()
    if not rub2:
        pytest.skip("Se requiere segundo rubro")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    calle = _uniq("BatchRub")
    base = {
        "fecha": "2026-07-08",
        "inspector": ins.nombre,
        "calle": calle,
        "numero": "77",
        "rubro": rub.nombre,
    }
    assert svc.validate_row(batch_id, "a", base, "relevamientos").ok is True
    r2 = svc.validate_row(
        batch_id,
        "b",
        {**base, "rubro": rub2.nombre, "fecha": "2026-07-09"},
        "relevamientos",
    )
    assert r2.ok is True, r2.errors


def test_pr76_establishment_key_numero_sin_angulo() -> None:
    k = build_relevamiento_establishment_key(
        "San Martín",
        "234",
        rubro_id=5,
        nombre_fantasia="Pollería",
        angulo_esquina="NE",
        es_esquina=False,
    )
    assert k.endswith("|NUM")
    assert "|ANE" not in k
