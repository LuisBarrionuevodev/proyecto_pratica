"""Tests CATALOGOS-PREDEPLOY.4 — matchers y seed atómico."""

from __future__ import annotations

import csv
import re
from unittest.mock import patch

import pytest
from sqlalchemy import event

from app.database import db
from app.domains.catalogos.canonical.normalize import normalize_ai_ci_identity
from app.domains.catalogos.seeds.calles_canonical_seed import apply_calles_canonicas, plan_calles_canonicas
from app.domains.catalogos.seeds.catalog_matchers import (
    CalleIndexes,
    MatchAction,
    build_calle_indexes,
    resolve_calle,
    resolve_rubro,
)
from app.domains.catalogos.seeds.seed_canonical_service import (
    CALLES_CANONICAS_CSV,
    run_canonical_catalog_seed,
    seed_rubros,
)
from app.models import CalleCatalogo, Rubro


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _calle_indexes_from_rows(*rows: CalleCatalogo) -> CalleIndexes:
    from collections import defaultdict

    from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key

    by_key = {r.nombre_key: r for r in rows}
    by_key_fold: dict[str, list[CalleCatalogo]] = defaultdict(list)
    by_canon_identity: dict[str, list[CalleCatalogo]] = defaultdict(list)
    by_slug_of_key: dict[str, list[CalleCatalogo]] = defaultdict(list)
    for row in rows:
        by_key_fold[row.nombre_key.casefold()].append(row)
        by_canon_identity[normalize_ai_ci_identity(row.nombre_canonico)].append(row)
        by_slug_of_key[slug_key(row.nombre_key)].append(row)
    return CalleIndexes(
        by_key=by_key,
        by_key_fold=dict(by_key_fold),
        by_canon_identity=dict(by_canon_identity),
        by_slug_of_key=dict(by_slug_of_key),
        all_rows=tuple(rows),
    )


def test_normalize_ai_ci_identity_accent_and_space():
    assert normalize_ai_ci_identity("Heladería") == normalize_ai_ci_identity("Heladeria")
    assert normalize_ai_ci_identity("Distribuidora") == normalize_ai_ci_identity("Distribuidora ")
    assert normalize_ai_ci_identity("Heladería") != normalize_ai_ci_identity("Heladería y Cafetería")


def test_resolve_rubro_reuse_accent_variants(app_ctx):
    row = Rubro(id=900001, nombre="Heladeria")
    index = {normalize_ai_ci_identity("Heladeria"): [row]}
    result = resolve_rubro(db.session, "Heladería", index=index)
    assert result.action == MatchAction.REUSE
    assert result.entity is row


def test_resolve_rubro_reuse_distribuidora_trailing_space(app_ctx):
    row = Rubro(id=900002, nombre="Distribuidora ")
    index = {normalize_ai_ci_identity("Distribuidora "): [row]}
    result = resolve_rubro(db.session, "Distribuidora", index=index)
    assert result.action == MatchAction.REUSE


def test_resolve_rubro_ambiguous_same_identity(app_ctx):
    rows = [Rubro(id=900003, nombre="Heladeria"), Rubro(id=900004, nombre="Heladería")]
    index = {normalize_ai_ci_identity("Heladeria"): rows}
    result = resolve_rubro(db.session, "Heladería", index=index)
    assert result.action == MatchAction.AMBIGUOUS


def test_seed_rubros_dry_run_plans_missing_without_flush(app_ctx, monkeypatch):
    from app.domains.catalogos.seeds import seed_canonical_service as seed_mod

    subset = ("RubroCanonInexistenteZZZ",)
    monkeypatch.setattr(seed_mod, "RUBROS_CANONICOS", subset)
    created, _, skipped = seed_rubros(db.session, dry_run=True)
    assert created == 1
    assert skipped == 0
    assert db.session.query(Rubro).filter(Rubro.nombre == "RubroCanonInexistenteZZZ").count() == 0


def test_calles_csv_734_sin_patrones_test():
    with CALLES_CANONICAS_CSV.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 734
    pattern = re.compile(r"(CalleCat|Main Canon|Esquina Canon)\s+\d+", re.I)
    assert not any(pattern.search((r.get("calles") or "")) for r in rows)


def test_resolve_calle_legacy_batalla_key():
    row = CalleCatalogo(
        id=900010,
        nombre_canonico="Batalla de Chacabuco",
        nombre_key="Batalla de Chacabuco",
        canon_base="batalla de chacabuco",
        activo=True,
    )
    indexes = _calle_indexes_from_rows(row)
    result = resolve_calle("Batalla de Chacabuco", indexes)
    assert result.action == MatchAction.REUSE
    assert result.entity.id == row.id


def test_resolve_calle_legacy_gral_paz():
    row = CalleCatalogo(
        id=900011,
        nombre_canonico="General Jose Maria Paz",
        nombre_key="gral jose maria paz",
        canon_base="general jose maria paz",
        activo=True,
    )
    indexes = _calle_indexes_from_rows(row)
    result = resolve_calle("General Jose Maria Paz", indexes)
    assert result.action == MatchAction.REUSE


def test_pasaje_independencia_no_colapsa_con_avenida():
    av = CalleCatalogo(
        id=900012,
        nombre_canonico="Avenida Independencia",
        nombre_key="avenida independencia",
        canon_base="independencia",
        activo=True,
    )
    pasaje = CalleCatalogo(
        id=900013,
        nombre_canonico="Pasaje Independencia",
        nombre_key="pasaje independencia",
        canon_base="independencia",
        activo=True,
    )
    indexes = _calle_indexes_from_rows(av, pasaje)
    assert resolve_calle("Avenida Independencia", indexes).entity.id == av.id
    assert resolve_calle("Pasaje Independencia", indexes).entity.id == pasaje.id


def test_plan_calles_dry_run_equals_apply_diff(app_ctx):
    before = db.session.query(CalleCatalogo).count()
    dry_created, _, dry_skipped = apply_calles_canonicas(db.session, CALLES_CANONICAS_CSV, dry_run=True)
    after = db.session.query(CalleCatalogo).count()
    assert before == after
    to_create, _, _ = plan_calles_canonicas(db.session, CALLES_CANONICAS_CSV)
    assert len(to_create) == dry_created
    assert dry_created + dry_skipped == 734


def test_atomic_rollback_on_distritos_failure(app_ctx):
    from app.models import Relevador

    rel_before = db.session.query(Relevador).count()
    with patch(
        "app.domains.catalogos.seeds.seed_canonical_service.seed_distritos",
        side_effect=RuntimeError("distritos boom"),
    ):
        with pytest.raises(RuntimeError, match="distritos boom"):
            run_canonical_catalog_seed(db.session, dry_run=False)
    db.session.rollback()
    assert db.session.query(Relevador).count() == rel_before


def test_no_autoflush_during_rubro_planning(app_ctx):
    flushes: list[str] = []

    def _capture_flush(session, flush_context, instances):
        flushes.append("flush")

    event.listen(db.session, "after_flush", _capture_flush)
    try:
        seed_rubros(db.session, dry_run=True)
    finally:
        event.remove(db.session, "after_flush", _capture_flush)
    assert flushes == []
