"""
F3.2 — Unicidad de relevamientos por ubicación (altura vs esquina).

Requiere BD con al menos un inspector y un rubro.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest

from app.database import db
from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.validate_service import GridValidateService
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.relevamiento_unicidad_service import (
    RELEVAMIENTO_UNICIDAD_NUMERO_MSG,
    assert_sin_relevamiento_activo_duplicado,
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


def _inspector_y_rubro():
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere al menos un inspector y un rubro en la BD de test")
    return ins, rub


def _payload(*, calle: str, numero: str, rubro: str, inspector: str, fecha: str = "2026-05-10", tipo: str | None = None):
    dom = {"calle": calle, "numero": numero}
    if tipo:
        dom["numero_tipo"] = tipo
    return {
        "fecha": fecha,
        "inspector_nombre": inspector,
        "domicilio": dom,
        "rubro_nombre": rubro,
    }


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def test_f32_altura_segundo_rubro_permitido_pr76(app_ctx) -> None:
    """PR7.6: mismo domicilio NUMERO con rubro distinto permite segundo relevamiento."""
    ins, rub = _inspector_y_rubro()
    calle = _uniq("SanMartínF32")
    try:
        p1 = _payload(calle=calle, numero="1009", rubro=rub.nombre, inspector=ins.nombre)
        crear_relevamiento_desde_payload(p1)
        p2 = {
            **p1,
            "fecha": "2026-05-11",
        }
        rub_otro = Rubro.query.filter(Rubro.id != rub.id).first()
        if rub_otro:
            p2["rubro_nombre"] = rub_otro.nombre
            crear_relevamiento_desde_payload(p2)
        else:
            pytest.skip("Se requiere segundo rubro para probar recambio")
    finally:
        db.session.rollback()


def test_f32_altura_mismo_rubro_sin_nombre_bloqueado(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("SanMartínDup")
    try:
        p1 = _payload(calle=calle, numero="1010", rubro=rub.nombre, inspector=ins.nombre)
        crear_relevamiento_desde_payload(p1)
        with pytest.raises(ValueError, match="establecimiento en el mismo domicilio"):
            crear_relevamiento_desde_payload({**p1, "fecha": "2026-05-12"})
    finally:
        db.session.rollback()


def test_f32_esquina_dos_rubros_ok(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first() or rub
    calle = _uniq("MaipúF32")
    try:
        p1 = _payload(
            calle=calle,
            numero="y Salta",
            rubro=rub.nombre,
            inspector=ins.nombre,
            tipo="ESQUINA",
        )
        p2 = {
            **p1,
            "rubro_nombre": rub2.nombre,
            "fecha": "2026-05-12",
        }
        crear_relevamiento_desde_payload(p1)
        crear_relevamiento_desde_payload(p2)
    finally:
        db.session.rollback()


def test_f32_soft_delete_permite_nuevo(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("SarmientoF32SD")
    try:
        p = _payload(calle=calle, numero="200", rubro=rub.nombre, inspector=ins.nombre)
        rel = crear_relevamiento_desde_payload(p)
        rel.deleted_at = datetime.utcnow()
        db.session.commit()
        crear_relevamiento_desde_payload({**p, "fecha": "2026-05-20"})
    finally:
        db.session.rollback()


def test_f32_update_mismo_domicilio_ok(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("LapridaF32U")
    try:
        p = _payload(calle=calle, numero="50", rubro=rub.nombre, inspector=ins.nombre)
        rel = crear_relevamiento_desde_payload(p)
        p2 = {**p, "fecha": "2026-05-25", "esta_abierto": True}
        actualizar_relevamiento(rel.id, p2)
    finally:
        db.session.rollback()


def test_f32_update_a_domicilio_ocupado_bloquea(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    base = _uniq("MitreF32B")
    try:
        p1 = _payload(calle=base, numero="1", rubro=rub.nombre, inspector=ins.nombre)
        p2 = _payload(calle=base, numero="2", rubro=rub.nombre, inspector=ins.nombre, fecha="2026-05-06")
        r1 = crear_relevamiento_desde_payload(p1)
        r2 = crear_relevamiento_desde_payload(
            {
                **p2,
                "domicilio": {"calle": f"{base} Otro", "numero": "99"},
            }
        )
        with pytest.raises(ValueError, match="establecimiento en el mismo domicilio"):
            actualizar_relevamiento(
                r2.id,
                {**p2, "domicilio": {"calle": base, "numero": "1"}},
            )
    finally:
        db.session.rollback()


def test_assert_esquina_no_bloquea_dos(app_ctx) -> None:
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Inspector y rubro requeridos")
    try:
        d = Domicilio(calle=_uniq("EsquinaTest"), numero="y X", numero_tipo="ESQUINA")
        db.session.add(d)
        db.session.flush()
        r1 = Relevamiento(
            fecha=date(2026, 5, 1),
            mes=5,
            anio=2026,
            domicilio_id=d.id,
            rubro_id=rub.id,
            inspector_id=ins.id,
        )
        db.session.add(r1)
        db.session.flush()
        assert_sin_relevamiento_activo_duplicado(d)
    finally:
        db.session.rollback()


def test_f32_validate_batch_segunda_altura_distinto_rubro_ok_pr76(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    calle = _uniq("JunínF32V")
    try:
        p = _payload(calle=calle, numero="300", rubro=rub.nombre, inspector=ins.nombre)
        crear_relevamiento_desde_payload(p)
        raw = {
            "fecha": "2026-05-15",
            "inspector": ins.nombre,
            "calle": calle,
            "numero": "300",
            "rubro": rub.nombre,
        }
        rub_otro = Rubro.query.filter(Rubro.id != rub.id).first()
        if rub_otro:
            raw["rubro"] = rub_otro.nombre
            resp = svc.validate_row(batch_id, "g1", raw, "relevamientos")
            assert resp.ok is True, resp.errors
        else:
            pytest.skip("Se requiere segundo rubro")
    finally:
        db.session.rollback()


def test_f32_validate_batch_mismo_establecimiento_numero_falla(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    calle = _uniq("JunínF32Dup")
    try:
        p = _payload(calle=calle, numero="301", rubro=rub.nombre, inspector=ins.nombre)
        crear_relevamiento_desde_payload(p)
        raw = {
            "fecha": "2026-05-16",
            "inspector": ins.nombre,
            "calle": calle,
            "numero": "301",
            "rubro": rub.nombre,
        }
        resp = svc.validate_row(batch_id, "g1", raw, "relevamientos")
        assert resp.ok is False
        assert RELEVAMIENTO_UNICIDAD_NUMERO_MSG in (resp.errors.get("_row") or "")
    finally:
        db.session.rollback()


def test_f32_validate_mismo_lote_dos_alturas_mismo_establecimiento_bloquea(app_ctx) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("LoteDupAlt")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    raw = {
        "fecha": "2026-05-21",
        "inspector": ins.nombre,
        "calle": calle,
        "numero": "100",
        "rubro": rub.nombre,
    }
    assert svc.validate_row(batch_id, "a", raw, "relevamientos").ok is True
    r2 = svc.validate_row(
        batch_id,
        "b",
        {**raw, "fecha": "2026-06-01", "numero": "100"},
        "relevamientos",
    )
    assert r2.ok is False
    assert RELEVAMIENTO_UNICIDAD_NUMERO_MSG in (r2.errors.get("_row") or "")


def test_f32_validate_batch_dos_esquinas_ok(app_ctx) -> None:
    """Texto de esquina sin `numero_tipo` explícito: detección igual que en alta."""
    ins, rub = _inspector_y_rubro()
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first() or rub
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    calle = _uniq("CatamarcaF32E")
    base = {
        "fecha": "2026-05-18",
        "inspector": ins.nombre,
        "calle": calle,
        "numero": "y Mendoza",
        "rubro": rub.nombre,
    }
    r1 = svc.validate_row(batch_id, "e1", base, "relevamientos")
    assert r1.ok is True, r1.errors
    r2 = svc.validate_row(
        batch_id,
        "e2",
        {**base, "rubro": rub2.nombre, "fecha": "2026-05-19"},
        "relevamientos",
    )
    assert r2.ok is True, r2.errors
