from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from app import create_app


app = create_app()


def _run_flask_db(args: list[str], cwd: Path) -> None:
    env = os.environ.copy()
    env.setdefault("FLASK_APP", "run.py")
    subprocess.run(
        [sys.executable, "-m", "flask", "db", *args],
        cwd=str(cwd),
        env=env,
        check=True,
    )


def _seed_catalogos_base() -> dict[str, int]:
    """
    Seedea catalogos base, turnos, rubros e inspectores de forma idempotente.

    Returns:
        Métricas agregadas de inserciones/actualizaciones/sin cambio, más
        ``legacy_inspectores_removed`` (placeholders 0001–0020 borrados tras liberar FKs).
    """
    from app.database import db
    from app.domains.grid.seeds.inspectores_canonicos import (
        remove_legacy_placeholder_inspectors,
        seed_turnos_base,
        upsert_inspectores_canonicos,
    )
    from app.models import (
        CatalogContraproducencia,
        CatalogMotivoComprobacion,
        CatalogTipoActuacion,
        JuzgadoCatalogo,
        Motivo,
        Rubro,
    )

    created = 0
    updated = 0
    skipped = 0

    def upsert_nombre(model, nombre: str) -> None:
        nonlocal created, skipped
        existing = model.query.filter(model.nombre == nombre).first()
        if existing:
            skipped += 1
            return
        db.session.add(model(nombre=nombre))
        created += 1

    t_created, t_updated, t_skipped = seed_turnos_base(db.session)
    created += t_created
    updated += t_updated
    skipped += t_skipped

    rubros = [
        "Comestibles",
        "Carnicería",
        "Drugstore",
        "Kiosco",
        "Supermercado",
        "Pollería",
        "Pescadería",
        "Bar",
        "Cervecería",
        "Rotisería",
        "Cafetería",
        "Verdulería",
    ]
    for rubro in rubros:
        existing = Rubro.query.filter(Rubro.nombre == rubro).first()
        if existing is None:
            db.session.add(Rubro(nombre=rubro))
            created += 1
        else:
            skipped += 1

    i_created, i_updated, i_skipped = upsert_inspectores_canonicos(db.session)
    created += i_created
    updated += i_updated
    skipped += i_skipped
    legacy_removed = remove_legacy_placeholder_inspectors(db.session)

    for nombre in [
        "INSPECCION",
        "REINSPECCION",
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
        "TRANSPORTE",
    ]:
        upsert_nombre(CatalogTipoActuacion, nombre)

    # Contraproducencias: ver también migración f1e2d3c4b5a6 (insert idempotente en deploy).
    for nombre in [
        "LOCAL CERRADO",
        "NO EXISTE/NO ES EL RUBRO",
        "CLIMA",
        "ZONA ROJA",
        "NO_HUBO",
        "OTROS",
        "NO PERMITE INSPECCION",
    ]:
        upsert_nombre(CatalogContraproducencia, nombre)

    for nombre in [
        "Falta de Higiene",
        "Condiciones Edilicias Inadecuadas",
        "No Permite la Inspección",
        "Incumplimiento",
        "Incumplimiento de Notificación",
        "Sin Certificado de Desinfección",
        "Sin Carnet de Sanidad",
        "Sin Certificado de Sanidad",
        "Mercadería Vencida",
        "Productos Sin Rotulación",
    ]:
        upsert_nombre(CatalogMotivoComprobacion, nombre)

    juzgados = [
        ("JF1", "Juzgado de Faltas N° 1"),
        ("JF2", "Juzgado de Faltas N° 2"),
        ("JF3", "Juzgado de Faltas N° 3"),
    ]
    for codigo, nombre in juzgados:
        existing = JuzgadoCatalogo.query.filter(JuzgadoCatalogo.codigo == codigo).first()
        if existing is None:
            db.session.add(JuzgadoCatalogo(codigo=codigo, nombre=nombre))
            created += 1
            continue
        if existing.nombre != nombre:
            existing.nombre = nombre
            db.session.add(existing)
            updated += 1
        else:
            skipped += 1

    for nombre in [
        "Carnet de Sanidad",
        "Desinfeccion",
        "Refacciones",
    ]:
        existing = Motivo.query.filter(Motivo.nombre == nombre).first()
        if existing is None:
            db.session.add(Motivo(nombre=nombre))
            created += 1
        else:
            skipped += 1

    db.session.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "legacy_inspectores_removed": legacy_removed,
    }


def _setup_command(message: str, no_migrate: bool) -> None:
    project_root = Path(__file__).resolve().parent
    migrations_dir = project_root / "migrations"

    print("Setup: verificando migraciones...")
    if not migrations_dir.exists():
        print("Setup: ejecutando flask db init")
        _run_flask_db(["init"], project_root)
    else:
        print("Setup: migrations/ ya existe, se omite init")

    if not no_migrate:
        print(f"Setup: ejecutando flask db migrate -m {message!r}")
        _run_flask_db(["migrate", "-m", message], project_root)
    else:
        print("Setup: --no-migrate activo, se omite migrate")

    print("Setup: ejecutando flask db upgrade")
    _run_flask_db(["upgrade"], project_root)

    print("Setup: esquema de base de datos listo.")


def _seed_command(csv_path: str, distritos_path: str | None) -> None:
    project_root = Path(__file__).resolve().parent
    csv_file = Path(csv_path)
    if not csv_file.is_absolute():
        csv_file = (project_root / csv_file).resolve()
    if not csv_file.exists():
        raise SystemExit(f"CSV no existe: {csv_file}")

    print("Seed: ejecutando seeds idempotentes...")
    from app.domains.geolocalizacion.geocode.pipelines.seed_distritos import (
        seed_distritos_from_geojson,
    )
    from app.domains.geolocalizacion.normalizacion_calles.pipelines.import_calle_catalogo import (
        importar_csv,
    )

    with app.app_context():
        created, updated, skipped = importar_csv(str(csv_file))
        distritos_file = Path(distritos_path).resolve() if distritos_path else None
        d_created, d_updated, d_skipped = seed_distritos_from_geojson(path=distritos_file)
        base_metrics = _seed_catalogos_base()
        from app.domains.relevamientos.seeds.relevamientos_corrientes_chico import (
            seed_relevamientos_corrientes_chico,
        )

        rel_demo_metrics = seed_relevamientos_corrientes_chico()
    print(f"Seed: calles OK created={created} updated={updated} skipped={skipped}")
    print(f"Seed: distritos OK created={d_created} updated={d_updated} skipped={d_skipped}")
    print(
        "Seed: catalogos base OK "
        f"created={base_metrics['created']} "
        f"updated={base_metrics['updated']} "
        f"skipped={base_metrics['skipped']} "
        f"legacy_inspectores_removed={base_metrics.get('legacy_inspectores_removed', 0)}"
    )
    print(
        "Seed: relevamientos corrientes (demo) OK "
        f"direcciones_lista={rel_demo_metrics['direcciones_en_seed']} "
        f"relev_creados={rel_demo_metrics['relevamientos_created']} "
        f"relev_omitidos={rel_demo_metrics['relevamientos_skipped']} "
        f"iniciadores_creados={rel_demo_metrics['iniciadores_created']} "
        f"iniciadores_omitidos={rel_demo_metrics['iniciadores_skipped']} "
        f"rubro_panaderia_nuevo={rel_demo_metrics['rubro_panaderia_inserted']} "
        f"fecha_seed={rel_demo_metrics['fecha_seed']}"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    setup_parser = subparsers.add_parser(
        "setup",
        help="Inicializa migraciones, genera migrate y aplica upgrade.",
    )
    setup_parser.add_argument(
        "--message",
        default="auto migration",
        help="Mensaje para flask db migrate",
    )
    setup_parser.add_argument(
        "--no-migrate",
        action="store_true",
        help="Omitir flask db migrate",
    )

    seed_parser = subparsers.add_parser(
        "seed",
        help="Corre seeds idempotentes de calles, distritos y catalogos base.",
    )
    seed_parser.add_argument("--csv", required=True, help="Ruta al CSV de calles")
    seed_parser.add_argument(
        "--distritos-path",
        required=False,
        help=(
            "Ruta opcional del GeoJSON de distritos. "
            "Si no se envia, usa el canonico del backend."
        ),
    )
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "setup":
        _setup_command(args.message, args.no_migrate)
    elif args.command == "seed":
        _seed_command(args.csv, args.distritos_path)
    else:
        app.run(debug=True)
