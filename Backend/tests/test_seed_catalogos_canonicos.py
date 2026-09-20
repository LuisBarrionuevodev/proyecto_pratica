"""Tests CATALOGOS-PREDEPLOY.3 — seed canónico de catálogos."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest

from app.domains.catalogos.canonical.juzgados import JUZGADOS_CANONICOS
from app.domains.catalogos.canonical.items_inspeccion import ITEMS_INSPECCION_CANONICOS
from app.domains.catalogos.canonical.manifest import CATALOG_VERSION, EXPECTED_COUNTS
from app.domains.catalogos.canonical.relevadores import RELEVADORES_CANONICOS
from app.domains.catalogos.canonical.rubros import RUBROS_CANONICOS
from app.domains.catalogos.seeds.seed_canonical_service import (
    CALLES_CANONICAS_CSV,
    canonical_names_contain_qa,
    run_canonical_catalog_seed,
)
from app.domains.catalogos.seeds.validate_canonical import validate_canonical_catalogs
from app.models import JuzgadoCatalogo, Rubro

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_i_manifest_rubros_29():
    assert len(RUBROS_CANONICOS) == EXPECTED_COUNTS["rubros"]


def test_h_relevadores_10():
    assert len(RELEVADORES_CANONICOS) == EXPECTED_COUNTS["relevadores"]


def test_g_juzgados_15_sin_iix():
    assert len(JUZGADOS_CANONICOS) == 15
    codigos = [c for c, _ in JUZGADOS_CANONICOS]
    assert "IIX" not in "".join(codigos)
    assert all(c.startswith("JF") for c in codigos)


def test_e_calles_csv_734():
    with CALLES_CANONICAS_CSV.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == EXPECTED_COUNTS["calles"]


def test_d_canonical_sources_sin_qa():
    assert canonical_names_contain_qa() == []


def test_catalog_version_defined():
    assert CATALOG_VERSION


def test_items_inspeccion_canonicos_6():
    assert len(ITEMS_INSPECCION_CANONICOS) == EXPECTED_COUNTS["items_inspeccion_seed"]
    assert sum(1 for i in ITEMS_INSPECCION_CANONICOS if i["tipo_respuesta"] == "ESTADO") == 5
    assert sum(1 for i in ITEMS_INSPECCION_CANONICOS if i["tipo_respuesta"] == "SI_NO") == 1
    hab = [i for i in ITEMS_INSPECCION_CANONICOS if i["codigo"] == "TIENE_HABILITACION"]
    assert len(hab) == 1


def test_c_dry_run_sin_writes(app):
    from app.database import db

    with app.app_context():
        before = Rubro.query.count()
        result = run_canonical_catalog_seed(db.session, dry_run=True)
        after = Rubro.query.count()
        assert before == after
        assert result.dry_run is True


def test_a_b_seed_idempotente_y_validacion(app):
    from app.database import db

    with app.app_context():
        first = run_canonical_catalog_seed(db.session, dry_run=False)
        validate_canonical_catalogs(db.session)
        second = run_canonical_catalog_seed(db.session, dry_run=False)
        total_created_second = sum(m["created"] for m in second.catalogs.values())
        assert total_created_second == 0
        assert first.catalog_version == CATALOG_VERSION


def test_juzgados_canonicos_codes(app):
    from app.database import db

    with app.app_context():
        run_canonical_catalog_seed(db.session, dry_run=False)
        rows = JuzgadoCatalogo.query.filter(JuzgadoCatalogo.codigo.like("JF%")).all()
        codes = {r.codigo for r in rows}
        for codigo, _ in JUZGADOS_CANONICOS:
            assert codigo in codes
