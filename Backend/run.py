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
        Metricas agregadas de inserciones/actualizaciones/sin cambios.
    """
    from app.database import db
    from app.models import (
        CatalogContraproducencia,
        CatalogMotivoComprobacion,
        CatalogTipoActuacion,
        Inspector,
        JuzgadoCatalogo,
        Motivo,
        Rubro,
        Turno,
    )
    from app.models.turno import TipoTurno

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

    turnos = {
        1: TipoTurno.MANIANA,
        2: TipoTurno.TARDE,
    }
    for turno_id, turno_val in turnos.items():
        existing = Turno.query.get(turno_id)
        if existing is None:
            db.session.add(Turno(id=turno_id, turno=turno_val))
            created += 1
        elif existing.turno != turno_val:
            existing.turno = turno_val
            db.session.add(existing)
            updated += 1
        else:
            skipped += 1

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

    inspectores = [
        ("Gomez", "0001", 1),
        ("Luna", "0002", 1),
        ("Pérez", "0003", 1),
        ("Sosa", "0004", 1),
        ("Díaz", "0005", 1),
        ("Romero", "0006", 1),
        ("Torres", "0007", 1),
        ("Rojas", "0008", 1),
        ("Fernández", "0009", 1),
        ("Gutiérrez", "0010", 1),
        ("Martínez", "0011", 2),
        ("Acosta", "0012", 2),
        ("Benítez", "0013", 2),
        ("Herrera", "0014", 2),
        ("Silva", "0015", 2),
        ("Molina", "0016", 2),
        ("Castro", "0017", 2),
        ("Vera", "0018", 2),
        ("Navarro", "0019", 2),
        ("Ibarra", "0020", 2),
    ]
    for nombre, legajo, turno_id in inspectores:
        existing = Inspector.query.filter(Inspector.legajo == legajo).first()
        if existing is None:
            db.session.add(Inspector(nombre=nombre, legajo=legajo, turno_id=turno_id))
            created += 1
            continue
        if existing.nombre != nombre or int(existing.turno_id) != int(turno_id):
            existing.nombre = nombre
            existing.turno_id = turno_id
            db.session.add(existing)
            updated += 1
        else:
            skipped += 1

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
    return {"created": created, "updated": updated, "skipped": skipped}


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
    print(f"Seed: calles OK created={created} updated={updated} skipped={skipped}")
    print(f"Seed: distritos OK created={d_created} updated={d_updated} skipped={d_skipped}")
    print(
        "Seed: catalogos base OK "
        f"created={base_metrics['created']} "
        f"updated={base_metrics['updated']} "
        f"skipped={base_metrics['skipped']}"
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
