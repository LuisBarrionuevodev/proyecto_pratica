"""
Seed idempotente de catálogos canónicos aprobados (CATALOGOS-PREDEPLOY.4).

Qué hace: plan/reconcile atómico por claves naturales.
Parámetros: sesión SQLAlchemy, dry_run.
Retorno: métricas por catálogo.
Errores: ValueError en conflictos no resolubles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.domains.catalogos.canonical.contraproducencias import CONTRAPRODUCENCIAS_CANONICAS
from app.domains.catalogos.canonical.items_inspeccion import ITEMS_INSPECCION_CANONICOS
from app.domains.catalogos.canonical.juzgados import JUZGADOS_CANONICOS
from app.domains.catalogos.canonical.manifest import CATALOG_VERSION
from app.domains.catalogos.canonical.motivos import (
    MOTIVOS_COMPROBACION_CANONICOS,
    MOTIVOS_NOTIFICACION_CANONICOS,
)
from app.domains.catalogos.canonical.normalize import normalize_catalog_display, normalize_catalog_key
from app.domains.catalogos.canonical.relevadores import RELEVADORES_CANONICOS
from app.domains.catalogos.canonical.rubros import RUBROS_CANONICOS
from app.domains.catalogos.canonical.tipos_actuacion import TIPOS_ACTUACION_CANONICOS
from app.domains.catalogos.seeds.calles_canonical_seed import apply_calles_canonicas
from app.domains.catalogos.seeds.catalog_matchers import (
    MatchAction,
    build_rubro_identity_index,
    resolve_rubro,
)
from app.domains.grid.seeds.inspectores_canonicos import _normalize_legajo
from app.models import Inspector
from app.domains.geolocalizacion.geocode.pipelines.seed_distritos import seed_distritos_from_geojson
from app.domains.grid.seeds.inspectores_canonicos import (
    INSPECTORES_CANONICO,
    seed_turnos_base,
    upsert_inspectores_canonicos,
)
from app.models import (
    CatalogContraproducencia,
    CatalogMotivoComprobacion,
    CatalogTipoActuacion,
    Distrito,
    ItemActaInspeccion,
    JuzgadoCatalogo,
    Motivo,
    Relevador,
    Rubro,
    Turno,
)

CALLES_CANONICAS_CSV = (
    Path(__file__).resolve().parent.parent / "canonical" / "data" / "calles_canonicas.csv"
)

QA_NAME_PATTERNS = (
    "qa",
    "test",
    "pr715rub",
    "rubstab",
    "rub10b1",
    "rubroe",
    "uniqrub",
    "jzrb",
    "jzso",
    "jzed",
    "@t.local",
)


@dataclass
class CatalogSeedResult:
    """Resultado agregado del seed."""

    catalog_version: str = CATALOG_VERSION
    dry_run: bool = False
    catalogs: dict[str, dict[str, int]] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)

    def add(self, catalog: str, created: int = 0, updated: int = 0, skipped: int = 0) -> None:
        self.catalogs[catalog] = {
            "created": created,
            "updated": updated,
            "skipped": skipped,
        }


def seed_rubros(session, *, dry_run: bool) -> tuple[int, int, int]:
    """
    Reconcilia los 29 rubros canónicos con matcher ai_ci y precarga.

    Returns:
        Tupla (created, updated, skipped/reused).
    """
    created = updated = skipped = 0
    rubro_index = build_rubro_identity_index(session)
    ambiguous: list[str] = []

    for nombre in RUBROS_CANONICOS:
        display = normalize_catalog_display(nombre)
        result = resolve_rubro(session, display, index=rubro_index)
        if result.action == MatchAction.AMBIGUOUS:
            ambiguous.append(f"{display}: {result.reason}")
            continue
        if result.action == MatchAction.CREATE:
            if not dry_run:
                session.add(Rubro(nombre=display))
            created += 1
        else:
            skipped += 1

    if ambiguous:
        raise ValueError("Rubros ambiguos: " + "; ".join(ambiguous))

    return created, updated, skipped


def seed_relevadores(session, *, dry_run: bool) -> tuple[int, int, int]:
    """Reconcilia relevadores canónicos por nombre normalizado."""
    created = updated = skipped = 0
    rows = session.query(Relevador).all()
    for nombre in RELEVADORES_CANONICOS:
        display = normalize_catalog_display(nombre)
        key = normalize_catalog_key(display)
        existing = next((r for r in rows if normalize_catalog_key(r.nombre) == key), None)
        if existing is None:
            if not dry_run:
                session.add(Relevador(nombre=display, activo=True))
            created += 1
        elif not existing.activo:
            if not dry_run:
                existing.activo = True
                session.add(existing)
            updated += 1
        else:
            skipped += 1
    return created, updated, skipped


def seed_juzgados(session, *, dry_run: bool) -> tuple[int, int, int]:
    """Reconcilia juzgados por código JF1..JF15."""
    created = updated = skipped = 0
    for codigo, nombre in JUZGADOS_CANONICOS:
        existing = session.query(JuzgadoCatalogo).filter(JuzgadoCatalogo.codigo == codigo).first()
        if existing is None:
            if not dry_run:
                session.add(JuzgadoCatalogo(codigo=codigo, nombre=nombre))
            created += 1
        elif existing.nombre != nombre:
            if not dry_run:
                existing.nombre = nombre
                session.add(existing)
            updated += 1
        else:
            skipped += 1
    return created, updated, skipped


def _upsert_by_nombre(model, session, nombres: tuple[str, ...], *, dry_run: bool) -> tuple[int, int, int]:
    created = updated = skipped = 0
    rows = session.query(model).all()
    for nombre in nombres:
        display = normalize_catalog_display(nombre)
        key = normalize_catalog_key(display)
        existing = next((r for r in rows if r.nombre == display), None)
        if existing is None:
            existing = next((r for r in rows if normalize_catalog_key(r.nombre) == key), None)
        if existing is None:
            if not dry_run:
                session.add(model(nombre=display))
            created += 1
        else:
            skipped += 1
    return created, updated, skipped


def seed_motivos_notificacion(session, *, dry_run: bool) -> tuple[int, int, int]:
    return _upsert_by_nombre(Motivo, session, MOTIVOS_NOTIFICACION_CANONICOS, dry_run=dry_run)


def seed_motivos_comprobacion(session, *, dry_run: bool) -> tuple[int, int, int]:
    return _upsert_by_nombre(
        CatalogMotivoComprobacion,
        session,
        MOTIVOS_COMPROBACION_CANONICOS,
        dry_run=dry_run,
    )


def seed_contraproducencias(session, *, dry_run: bool) -> tuple[int, int, int]:
    return _upsert_by_nombre(
        CatalogContraproducencia,
        session,
        CONTRAPRODUCENCIAS_CANONICAS,
        dry_run=dry_run,
    )


def seed_tipos_actuacion(session, *, dry_run: bool) -> tuple[int, int, int]:
    return _upsert_by_nombre(
        CatalogTipoActuacion,
        session,
        TIPOS_ACTUACION_CANONICOS,
        dry_run=dry_run,
    )


def seed_items_inspeccion(session, *, dry_run: bool) -> tuple[int, int, int]:
    created = updated = skipped = 0
    for item in ITEMS_INSPECCION_CANONICOS:
        existing = (
            session.query(ItemActaInspeccion)
            .filter(ItemActaInspeccion.codigo == item["codigo"])
            .first()
        )
        if existing is None:
            if not dry_run:
                session.add(
                    ItemActaInspeccion(
                        codigo=item["codigo"],
                        nombre=item["nombre"],
                        orden=item["orden"],
                        activo=True,
                        tipo_respuesta=item["tipo_respuesta"],
                    )
                )
            created += 1
            continue
        changed = False
        if existing.nombre != item["nombre"]:
            if not dry_run:
                existing.nombre = item["nombre"]
            changed = True
        if int(existing.orden) != int(item["orden"]):
            if not dry_run:
                existing.orden = int(item["orden"])
            changed = True
        if str(existing.tipo_respuesta or "ESTADO") != str(item["tipo_respuesta"]):
            if not dry_run:
                existing.tipo_respuesta = item["tipo_respuesta"]
            changed = True
        if not existing.activo:
            if not dry_run:
                existing.activo = True
            changed = True
        if changed:
            if not dry_run:
                session.add(existing)
            updated += 1
        else:
            skipped += 1
    return created, updated, skipped


def seed_turnos(session, *, dry_run: bool) -> tuple[int, int, int]:
    """Planifica/asegura turnos base id 1 y 2."""
    if dry_run:
        created = skipped = 0
        for turno_id in (1, 2):
            if session.query(Turno).filter(Turno.id == turno_id).first() is None:
                created += 1
            else:
                skipped += 1
        return created, 0, skipped
    return seed_turnos_base(session)


def seed_inspectores(session, *, dry_run: bool) -> tuple[int, int, int]:
    """Planifica inspectores canónicos por legajo."""
    if dry_run:
        created = updated = skipped = 0
        legajos_db = {str(i.legajo) for i in session.query(Inspector).all()}
        for _nombre, legajo, _turno in INSPECTORES_CANONICO:
            if _normalize_legajo(legajo) in legajos_db:
                skipped += 1
            else:
                created += 1
        return created, updated, skipped
    return upsert_inspectores_canonicos(session)


def seed_calles(session, *, dry_run: bool) -> tuple[int, int, int]:
    """Reconcilia calles canónicas con el mismo planner en dry-run y apply."""
    if not CALLES_CANONICAS_CSV.is_file():
        raise FileNotFoundError(f"CSV canónico no encontrado: {CALLES_CANONICAS_CSV}")
    return apply_calles_canonicas(session, CALLES_CANONICAS_CSV, dry_run=dry_run)


def seed_distritos(session, *, dry_run: bool) -> tuple[int, int, int]:
    """Seed distritos desde GeoJSON sin commit interno."""
    if dry_run:
        geo_count = 20
        try:
            from app.domains.geolocalizacion.geocode.pipelines.seed_distritos import _geojson_path, _load_distritos_from_geojson

            geo_count = len(_load_distritos_from_geojson(_geojson_path()))
        except (ValueError, OSError):
            geo_count = 20
        db_count = session.query(Distrito).count()
        return 0, 0, min(db_count, geo_count)
    return seed_distritos_from_geojson(session=session, commit=False)


def run_canonical_catalog_seed(session, *, dry_run: bool = False) -> CatalogSeedResult:
    """
    Ejecuta todos los seeds canónicos en una transacción atómica.

    Parameters:
        session: sesión SQLAlchemy.
        dry_run: si True, no persiste cambios.

    Returns:
        CatalogSeedResult con métricas por catálogo.

    Raises:
        ValueError: validación o ambigüedad en reconciliación.
    """
    from app.domains.catalogos.seeds.validate_canonical import validate_canonical_catalogs

    result = CatalogSeedResult(dry_run=dry_run)
    steps: list[tuple[str, Any]] = [
        ("turnos", lambda: seed_turnos(session, dry_run=dry_run)),
        ("rubros", lambda: seed_rubros(session, dry_run=dry_run)),
        ("relevadores", lambda: seed_relevadores(session, dry_run=dry_run)),
        ("inspectores", lambda: seed_inspectores(session, dry_run=dry_run)),
        ("motivos_notificacion", lambda: seed_motivos_notificacion(session, dry_run=dry_run)),
        ("motivos_comprobacion", lambda: seed_motivos_comprobacion(session, dry_run=dry_run)),
        ("juzgados", lambda: seed_juzgados(session, dry_run=dry_run)),
        ("contraproducencias", lambda: seed_contraproducencias(session, dry_run=dry_run)),
        ("items_inspeccion", lambda: seed_items_inspeccion(session, dry_run=dry_run)),
        ("tipos_actuacion", lambda: seed_tipos_actuacion(session, dry_run=dry_run)),
        ("calles", lambda: seed_calles(session, dry_run=dry_run)),
        ("distritos", lambda: seed_distritos(session, dry_run=dry_run)),
    ]

    try:
        with session.no_autoflush:
            for name, fn in steps:
                created, updated, skipped = fn()
                result.add(name, created=created, updated=updated, skipped=skipped)
            if not dry_run:
                session.flush()
                validate_canonical_catalogs(session)
                session.commit()
    except Exception:
        session.rollback()
        raise

    return result


def canonical_names_contain_qa() -> list[str]:
    """Detecta patrones QA en las fuentes canónicas versionadas."""
    offenders: list[str] = []
    all_names: list[str] = list(RUBROS_CANONICOS) + list(RELEVADORES_CANONICOS)
    all_names += [n for _, n in JUZGADOS_CANONICOS]
    for name in all_names:
        low = name.casefold()
        if any(p in low for p in QA_NAME_PATTERNS):
            offenders.append(name)
    return offenders
