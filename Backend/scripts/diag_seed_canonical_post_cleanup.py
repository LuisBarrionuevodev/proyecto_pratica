#!/usr/bin/env python
"""CATALOGOS-PREDEPLOY.4-DIAG — diagnóstico read-only del seed canónico."""
from __future__ import annotations

import csv
import json
import sys
import unicodedata
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.domains.catalogos.canonical.juzgados import JUZGADOS_CANONICOS
from app.domains.catalogos.canonical.normalize import normalize_catalog_display, normalize_catalog_key
from app.domains.catalogos.canonical.relevadores import RELEVADORES_CANONICOS
from app.domains.catalogos.canonical.rubros import RUBROS_CANONICOS
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key

CALLES_CSV = BACKEND_ROOT / "app/domains/catalogos/canonical/data/calles_canonicas.csv"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def nfd(s: str) -> str:
    return unicodedata.normalize("NFD", s)


def classify_rubro(canonical: str, rows: list[dict]) -> dict:
    display = normalize_catalog_display(canonical)
    key = normalize_catalog_key(display)
    exact = [r for r in rows if r["nombre"] == display]
    norm = [r for r in rows if normalize_catalog_key(r["nombre"]) == key]
    test = [
        r
        for r in rows
        if any(
            p in r["nombre"].casefold()
            for p in ("qa", "test", "pr", "rubstab", "rubroe", "uniqrub", "rubro ")
        )
        and normalize_catalog_key(r["nombre"]) != key
    ]
    if exact:
        mt = "EXACT"
        ids = [r["id"] for r in exact]
    elif norm:
        mt = "NORMALIZED_EQUIVALENT"
        ids = [r["id"] for r in norm]
    else:
        mt = "MISSING"
        ids = []
    ambiguous = len(set(ids)) > 1 if ids else False
    if ambiguous:
        mt = "AMBIGUOUS_MULTIPLE"
    return {
        "canonical_name": canonical,
        "canonical_key": key,
        "canonical_repr": repr(display),
        "canonical_hex": display.encode("utf-8").hex(),
        "match_type": mt,
        "exact_match_id": exact[0]["id"] if exact else None,
        "db_equivalent_ids": ids,
        "db_equivalent_samples": [
            {
                "id": r["id"],
                "nombre": r["nombre"],
                "repr": repr(r["nombre"]),
                "hex": r["nombre"].encode("utf-8").hex(),
                "length": r["length"],
                "char_length": r["char_length"],
            }
            for r in (exact or norm)[:3]
        ],
    }


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    import os

    uri = os.environ["SQLALCHEMY_DATABASE_URI"]
    engine = create_engine(uri)
    out: dict = {}

    with engine.connect() as conn:
        out["database"] = conn.execute(text("SELECT DATABASE()")).scalar()
        out["alembic"] = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        out["counts"] = {
            t: conn.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
            for t in (
                "rubro",
                "relevador",
                "juzgado_catalogo",
                "calle_catalogo",
                "inspector",
                "item_acta_inspeccion",
                "turno",
                "motivo",
                "catalog_motivo_comprobacion",
                "catalog_contraproducencia",
                "catalog_tipo_actuacion",
                "distrito",
            )
        }

        col = conn.execute(
            text(
                """
                SHOW FULL COLUMNS FROM rubro WHERE Field = 'nombre'
                """
            )
        ).fetchone()
        idx = conn.execute(
            text(
                """
                SHOW INDEX FROM rubro WHERE Key_name = 'ix_rubro_nombre'
                """
            )
        ).fetchall()
        out["rubro_column"] = dict(col._mapping) if col else None
        out["rubro_index"] = [dict(r._mapping) for r in idx]

        rubro_rows = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    """
                    SELECT id, nombre, LENGTH(nombre) AS length,
                           CHAR_LENGTH(nombre) AS char_length, HEX(nombre) AS hex_nombre
                    FROM rubro
                    """
                )
            )
        ]

        heladeria_canon = "Heladería"
        hel_key = normalize_catalog_key(heladeria_canon)
        hel_candidates = [
            r
            for r in rubro_rows
            if "helader" in normalize_catalog_key(r["nombre"])
            or normalize_catalog_key(r["nombre"]) == hel_key
            or "Helader" in r["nombre"]
        ]
        out["heladeria"] = {
            "canonical": heladeria_canon,
            "canonical_repr": repr(heladeria_canon),
            "canonical_hex": heladeria_canon.encode("utf-8").hex(),
            "canonical_nfc_hex": nfc(heladeria_canon).encode("utf-8").hex(),
            "canonical_nfd_hex": nfd(heladeria_canon).encode("utf-8").hex(),
            "normalize_key": hel_key,
            "candidates": hel_candidates,
        }

        rubro_table = [classify_rubro(name, rubro_rows) for name in RUBROS_CANONICOS]
        out["rubros_29"] = rubro_table
        out["rubros_summary"] = {
            mt: sum(1 for r in rubro_table if r["match_type"] == mt)
            for mt in ("EXACT", "NORMALIZED_EQUIVALENT", "MISSING", "AMBIGUOUS_MULTIPLE")
        }
        missing_rubros = [r["canonical_name"] for r in rubro_table if r["match_type"] == "MISSING"]
        out["missing_rubros_list"] = missing_rubros
        out["dry_run_would_create_rubros"] = missing_rubros

        # 10 vs 11: validate uses same normalize as seed
        out["validate_missing_count"] = len(missing_rubros)

        rel_rows = [
            dict(r._mapping)
            for r in conn.execute(text("SELECT id, nombre, activo FROM relevador"))
        ]
        rel_table = []
        for nombre in RELEVADORES_CANONICOS:
            display = normalize_catalog_display(nombre)
            key = normalize_catalog_key(display)
            exact = [r for r in rel_rows if r["nombre"] == display]
            norm = [r for r in rel_rows if normalize_catalog_key(r["nombre"]) == key]
            if exact:
                mt = "EXACT"
                ids = [r["id"] for r in exact]
            elif norm:
                mt = "NORMALIZED_EQUIVALENT"
                ids = [r["id"] for r in norm]
            else:
                mt = "MISSING"
                ids = []
            if len(ids) > 1:
                mt = "AMBIGUOUS"
            rel_table.append({"canonical": nombre, "match_type": mt, "ids": ids, "rows": (exact or norm)[:2]})
        out["relevadores_10"] = rel_table

        jz_rows = [
            dict(r._mapping)
            for r in conn.execute(text("SELECT id, codigo, nombre FROM juzgado_catalogo ORDER BY id"))
        ]
        jz_table = []
        for codigo, nombre in JUZGADOS_CANONICOS:
            by_code = [r for r in jz_rows if r["codigo"] == codigo]
            by_name = [r for r in jz_rows if normalize_catalog_key(r["nombre"]) == normalize_catalog_key(nombre)]
            if by_code:
                mt = "SAME_ENTITY" if by_code[0]["nombre"] == nombre else "SAME_ENTITY_NAME_DRIFT"
            else:
                mt = "MISSING"
            jz_table.append(
                {
                    "codigo": codigo,
                    "nombre_canon": nombre,
                    "match_type": mt,
                    "by_code": by_code,
                    "by_name_other_code": [r for r in by_name if r not in by_code],
                }
            )
        out["juzgados_15"] = jz_table
        out["juzgado_jf_rows"] = [r for r in jz_rows if r["codigo"] and str(r["codigo"]).upper().startswith("JF")]

        calle_rows = [
            dict(r._mapping)
            for r in conn.execute(text("SELECT id, nombre_canonico, nombre_key FROM calle_catalogo"))
        ]
        calle_keys_db = {r["nombre_key"] for r in calle_rows}
        csv_rows = []
        with CALLES_CSV.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw = row.get("calles") or next(iter(row.values()), "")
                canon = normalize_catalog_display(raw)
                if canon:
                    csv_rows.append(canon)
        exact_calle = missing_calle = norm_equiv = 0
        calle_missing_samples = []
        for canon in csv_rows:
            key = slug_key(canon)
            if key in calle_keys_db:
                exact_calle += 1
            else:
                missing_calle += 1
                if len(calle_missing_samples) < 5:
                    calle_missing_samples.append({"canon": canon, "key": key})
        out["calles"] = {
            "db_total": len(calle_rows),
            "csv_canonical_total": len(csv_rows),
            "exact_key_match": exact_calle,
            "missing_by_key": missing_calle,
            "dry_run_reports_create_all_csv_lines": len(csv_rows),
            "missing_samples": calle_missing_samples,
            "note": "dry-run seed_calles counts CSV lines, not DB diff",
        }

        # simulate seed_rubros order to find which rubro triggers before Heladería
        pending_adds = []
        for nombre in RUBROS_CANONICOS:
            display = normalize_catalog_display(nombre)
            key = normalize_catalog_key(display)
            found = any(normalize_catalog_key(r["nombre"]) == key for r in rubro_rows)
            if not found:
                pending_adds.append(display)
        out["seed_rubros_pending_inserts"] = pending_adds
        out["first_pending_insert"] = pending_adds[0] if pending_adds else None
        out["heladeria_position_in_pending"] = (
            pending_adds.index("Heladería") if "Heladería" in pending_adds else None
        )

    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
