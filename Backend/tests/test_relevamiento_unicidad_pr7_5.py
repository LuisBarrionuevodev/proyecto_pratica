"""
PR7.5 — Auditoría de duplicados y unicidad segura en relevamientos ESQUINA.
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
    auditar_relevamientos_esquina_duplicados,
)
from app.domains.relevamientos.services.relevamiento_unicidad_service import (
    RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG,
    RELEVAMIENTO_UNICIDAD_NUMERO_MSG,
)
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
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


# --- Unicidad NUMERO ---


def test_pr75_numero_mismo_rubro_sin_nombre_bloquea(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("NumDup")
    try:
        p1 = _payload(calle=calle, numero="501", rubro=rub.nombre, inspector=ins.nombre)
        crear_relevamiento_desde_payload(p1)
        with pytest.raises(ValueError, match="establecimiento en el mismo domicilio"):
            crear_relevamiento_desde_payload({**p1, "fecha": "2026-05-11"})
    finally:
        db.session.rollback()


def test_pr75_numero_mismo_rubro_nombre_distinto_permite(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("NumNom")
    try:
        p1 = _payload(
            calle=calle,
            numero="502",
            rubro=rub.nombre,
            inspector=ins.nombre,
            nombre_fantasia="Local A",
        )
        crear_relevamiento_desde_payload(p1)
        crear_relevamiento_desde_payload(
            {**p1, "fecha": "2026-05-12", "nombre_fantasia": "Local B"}
        )
    finally:
        db.session.rollback()


# --- Unicidad ESQUINA ---


def test_pr75_esquina_dos_rubros_distintos_ok(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first() or rub
    calle = _uniq("Esq2Rub")
    try:
        p1 = _payload(
            calle=calle,
            numero="y Norte",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
            angulo_esquina="NE",
        )
        p2 = {**p1, "rubro_nombre": rub2.nombre, "fecha": "2026-05-12", "angulo_esquina": "NE"}
        crear_relevamiento_desde_payload(p1)
        crear_relevamiento_desde_payload(p2)
    finally:
        db.session.rollback()


def test_pr75_esquina_mismo_rubro_distinto_angulo_ok(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqAng")
    try:
        p1 = _payload(
            calle=calle,
            numero="y Sur",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
            angulo_esquina="NE",
        )
        p2 = {**p1, "fecha": "2026-05-13", "angulo_esquina": "NO"}
        crear_relevamiento_desde_payload(p1)
        crear_relevamiento_desde_payload(p2)
    finally:
        db.session.rollback()


def test_pr75_esquina_mismo_rubro_mismo_angulo_bloqueado(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqDupAng")
    try:
        p1 = _payload(
            calle=calle,
            numero="y Oeste",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
            angulo_esquina="SE",
        )
        crear_relevamiento_desde_payload(p1)
        p2 = {**p1, "fecha": "2026-05-14"}
        with pytest.raises(ValueError, match=RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG[:40]):
            crear_relevamiento_desde_payload(p2)
    finally:
        db.session.rollback()


def test_pr75_esquina_mismo_rubro_distinto_nombre_ok(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqNom")
    try:
        p1 = _payload(
            calle=calle,
            numero="y Este",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
            nombre_fantasia="El Toro",
        )
        p2 = {**p1, "fecha": "2026-05-15", "nombre_fantasia": "La Vaquita"}
        crear_relevamiento_desde_payload(p1)
        crear_relevamiento_desde_payload(p2)
    finally:
        db.session.rollback()


def test_pr75_esquina_mismo_nombre_normalizado_bloqueado(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqNomDup")
    try:
        p1 = _payload(
            calle=calle,
            numero="y Centro",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
            nombre_fantasia="Pan Express",
        )
        crear_relevamiento_desde_payload(p1)
        p2 = {**p1, "fecha": "2026-05-16", "nombre_fantasia": "  pan   express "}
        with pytest.raises(ValueError, match="establecimiento en la misma esquina"):
            crear_relevamiento_desde_payload(p2)
    finally:
        db.session.rollback()


def test_pr75_esquina_legacy_vacio_mismo_rubro_bloquea_alta(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqLegCreate")
    try:
        p1 = _payload(
            calle=calle,
            numero="y Legacy",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
        )
        crear_relevamiento_desde_payload(p1)
        p2 = {**p1, "fecha": "2026-05-17"}
        with pytest.raises(ValueError, match="establecimiento en la misma esquina"):
            crear_relevamiento_desde_payload(p2)
    finally:
        db.session.rollback()


def test_pr75_update_mismo_registro_no_se_bloquea(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqUpSelf")
    try:
        p = _payload(
            calle=calle,
            numero="y Self",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
            angulo_esquina="NE",
            nombre_fantasia="Uno",
        )
        rel = crear_relevamiento_desde_payload(p)
        actualizar_relevamiento(rel.id, {**p, "esta_abierto": True})
    finally:
        db.session.rollback()


def test_pr75_update_angulo_a_existente_bloquea(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqUpAng")
    try:
        base = _payload(
            calle=calle,
            numero="y UpAng",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
        )
        r1 = crear_relevamiento_desde_payload({**base, "angulo_esquina": "NE"})
        r2 = crear_relevamiento_desde_payload({**base, "fecha": "2026-05-18", "angulo_esquina": "NO"})
        with pytest.raises(ValueError, match="establecimiento en la misma esquina"):
            actualizar_relevamiento(r2.id, {**base, "fecha": "2026-05-18", "angulo_esquina": "NE"})
        assert r1.id != r2.id
    finally:
        db.session.rollback()


def test_pr75_soft_delete_no_bloquea_nuevo(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqSD")
    try:
        p = _payload(
            calle=calle,
            numero="y Soft",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
            angulo_esquina="SO",
        )
        rel = crear_relevamiento_desde_payload(p)
        rel.deleted_at = datetime.utcnow()
        db.session.commit()
        crear_relevamiento_desde_payload({**p, "fecha": "2026-05-20"})
    finally:
        db.session.rollback()


def test_pr75_legacy_update_coexistencia_no_bloquea(app_ctx, require_pr72_migration) -> None:
    """Dos legacy preexistentes: assert con exclude_id no bloquea (solo warning)."""
    from app.domains.relevamientos.services.relevamiento_unicidad_service import (
        assert_sin_relevamiento_activo_duplicado,
    )

    ins, rub = _inspector_y_rubro()
    calle = _uniq("EsqLegUp")
    try:
        dom = Domicilio(calle=calle, numero="y LegacyUp", numero_tipo="ESQUINA")
        db.session.add(dom)
        db.session.flush()
        r1 = Relevamiento(
            fecha=date(2026, 5, 1),
            mes=5,
            anio=2026,
            domicilio_id=dom.id,
            rubro_id=rub.id,
            inspector_id=ins.id,
        )
        r2 = Relevamiento(
            fecha=date(2026, 5, 2),
            mes=5,
            anio=2026,
            domicilio_id=dom.id,
            rubro_id=rub.id,
            inspector_id=ins.id,
        )
        db.session.add_all([r1, r2])
        db.session.flush()
        assert_sin_relevamiento_activo_duplicado(
            dom,
            rubro_id=rub.id,
            nombre_fantasia=None,
            angulo_esquina=None,
            exclude_relevamiento_id=r1.id,
        )
    finally:
        db.session.rollback()


# --- Auditoría ---


def test_pr75_auditoria_detecta_colision_exacta(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("AudExact")
    try:
        dom = Domicilio(calle=calle, numero="y Audit", numero_tipo="ESQUINA")
        db.session.add(dom)
        db.session.flush()
        for i in range(2):
            db.session.add(
                Relevamiento(
                    fecha=date(2026, 5, 10 + i),
                    mes=5,
                    anio=2026,
                    domicilio_id=dom.id,
                    rubro_id=rub.id,
                    inspector_id=ins.id,
                    nombre_fantasia="Dup Audit",
                    angulo_esquina="NE",
                )
            )
        db.session.flush()
        result = auditar_relevamientos_esquina_duplicados()
        tipos = [g.tipo for g in result.grupos if g.domicilio_id == dom.id]
        assert "colision_exacta" in tipos
        assert result.grupos_con_colision >= 1
    finally:
        db.session.rollback()


def test_pr75_auditoria_reporta_legacy_vacio(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("AudLeg")
    try:
        dom = Domicilio(calle=calle, numero="y LegAudit", numero_tipo="ESQUINA")
        db.session.add(dom)
        db.session.flush()
        for i in range(2):
            db.session.add(
                Relevamiento(
                    fecha=date(2026, 6, 1 + i),
                    mes=6,
                    anio=2026,
                    domicilio_id=dom.id,
                    rubro_id=rub.id,
                    inspector_id=ins.id,
                )
            )
        db.session.flush()
        result = auditar_relevamientos_esquina_duplicados()
        assert any(g.tipo == "legacy_vacio" and g.domicilio_id == dom.id for g in result.grupos)
    finally:
        db.session.rollback()


# --- Grid batch ---


def test_pr75_batch_esquina_mismo_rubro_angulo_duplicado(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    calle = _uniq("BatchEsqDup")
    base = {
        "fecha": "2026-05-22",
        "inspector": ins.nombre,
        "calle": calle,
        "numero": "y Batch",
        "rubro": rub.nombre,
        "numero_tipo": "ESQUINA",
        "angulo_esquina": "NE",
    }
    assert svc.validate_row(batch_id, "e1", base, "relevamientos").ok is True
    r2 = svc.validate_row(batch_id, "e2", {**base, "fecha": "2026-05-23"}, "relevamientos")
    assert r2.ok is False
    assert RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG in (r2.errors.get("_row") or "")


def test_pr75_batch_esquina_mismo_rubro_distinto_angulo_ok(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    calle = _uniq("BatchEsqOk")
    base = {
        "fecha": "2026-05-24",
        "inspector": ins.nombre,
        "calle": calle,
        "numero": "y BatchOk",
        "rubro": rub.nombre,
        "numero_tipo": "ESQUINA",
        "angulo_esquina": "NE",
    }
    assert svc.validate_row(batch_id, "a", base, "relevamientos").ok is True
    r2 = svc.validate_row(
        batch_id,
        "b",
        {**base, "fecha": "2026-05-25", "angulo_esquina": "NO"},
        "relevamientos",
    )
    assert r2.ok is True, r2.errors


def test_pr75_batch_numero_distinto_rubro_permite(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("BatchNumOk")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    try:
        p = _payload(calle=calle, numero="880", rubro=rub.nombre, inspector=ins.nombre)
        crear_relevamiento_desde_payload(p)
        raw = {
            "fecha": "2026-05-26",
            "inspector": ins.nombre,
            "calle": calle,
            "numero": "880",
            "rubro": rub.nombre,
        }
        rub_otro = Rubro.query.filter(Rubro.id != rub.id).first()
        if rub_otro:
            raw["rubro"] = rub_otro.nombre
            resp = svc.validate_row(batch_id, "n1", raw, "relevamientos")
            assert resp.ok is True, resp.errors
        else:
            pytest.skip("Se requiere segundo rubro")
    finally:
        db.session.rollback()


def test_pr75_batch_numero_duplicado_exacto_bloquea(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("BatchNumDup")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    try:
        p = _payload(calle=calle, numero="881", rubro=rub.nombre, inspector=ins.nombre)
        crear_relevamiento_desde_payload(p)
        raw = {
            "fecha": "2026-05-27",
            "inspector": ins.nombre,
            "calle": calle,
            "numero": "881",
            "rubro": rub.nombre,
        }
        resp = svc.validate_row(batch_id, "n1", raw, "relevamientos")
        assert resp.ok is False
        assert RELEVAMIENTO_UNICIDAD_NUMERO_MSG in (resp.errors.get("_row") or "")
    finally:
        db.session.rollback()


def test_pr75_batch_store_esquina_establecimiento_index() -> None:
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "CALLE|Y ESQ"
    est = build_relevamiento_establishment_key("Calle", "y Esq", rubro_id=1, angulo_esquina="NE", es_esquina=True)
    assert store.upsert_relevamiento_ubicacion(batch_id, "r1", loc, True, est) is None
    other = store.upsert_relevamiento_ubicacion(batch_id, "r2", loc, True, est)
    assert other == "r1"
