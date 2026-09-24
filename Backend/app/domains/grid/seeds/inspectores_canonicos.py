"""
Nómina canónica de inspectores (Bromatología) para seed idempotente.

Fuente: nómina operativa inicial; ``legajo`` = número de afiliado (5 dígitos).
La unicidad lógica del seed es por ``legajo``; al re-ejecutar se actualiza
``nombre`` y ``turno_id`` si cambiaron.
"""

from __future__ import annotations

from app.models import Inspector, Relevamiento, RutaGrupoInspector, Turno
from app.models.turno import TipoTurno

# Tuplas (nombre_completo, legajo_afiliado, turno_id). Sin datos de turno por persona:
# todo el plantel queda en turno_id=1 (Mañana) como default operativo del seed.
_DEFAULT_TURNO_ID = 1

# Lista exacta provista por negocio (apellido y nombre, afiliado).
INSPECTORES_CANONICO: tuple[tuple[str, str, int], ...] = (
    ("Accardi José", "19960", _DEFAULT_TURNO_ID),
    ("Alamo Alfredo", "23458", _DEFAULT_TURNO_ID),
    ("Avila Karina", "35577", _DEFAULT_TURNO_ID),
    ("Cabezas Cecilia", "49385", _DEFAULT_TURNO_ID),
    ("Cancino Carlos Rubén", "19908", _DEFAULT_TURNO_ID),
    ("Correa Cristian", "43023", _DEFAULT_TURNO_ID),
    ("Diaz Walter Omar", "23383", _DEFAULT_TURNO_ID),
    ("Figueroa Rita Judith", "48098", _DEFAULT_TURNO_ID),
    ("Flores Gustavo", "22480", _DEFAULT_TURNO_ID),
    ("Ibáñez Fabián", "24621", _DEFAULT_TURNO_ID),
    ("Jerez Clara Carolina", "39082", _DEFAULT_TURNO_ID),
    ("Martinez Aldo", "19483", _DEFAULT_TURNO_ID),
    ("Nieva Facundo R", "45217", _DEFAULT_TURNO_ID),
    ("Paliza Claudia", "26832", _DEFAULT_TURNO_ID),
    ("Pentucci Cecilia", "25796", _DEFAULT_TURNO_ID),
    ("Rivas Francisco", "23281", _DEFAULT_TURNO_ID),
    ("Rueda Carolina", "49223", _DEFAULT_TURNO_ID),
    ("Saco Vertiz Mariela", "23318", _DEFAULT_TURNO_ID),
    ("Segovia Pablo", "22460", _DEFAULT_TURNO_ID),
    ("Soria Dante", "24898", _DEFAULT_TURNO_ID),
    ("Veliz María Elvira", "23462", _DEFAULT_TURNO_ID),
    ("Vier Alberto", "20742", _DEFAULT_TURNO_ID),
    ("Villafañe Ángel Antonio", "19910", _DEFAULT_TURNO_ID),
    ("Zacame Ariel", "49476", _DEFAULT_TURNO_ID),
)

# Inspectores de demostración previos en run.py (legajo 0001–0020). El seed los elimina
# tras liberar FKs (misma política que la migración Alembic).
LEGACY_PLACEHOLDER_LEGAJOS: frozenset[str] = frozenset(f"{i:04d}" for i in range(1, 21))


def _normalize_legajo(legajo: str) -> str:
    """Quita espacios; rellena a 5 caracteres si es numérico corto."""
    s = (legajo or "").strip()
    if s.isdigit() and len(s) < 5:
        return s.zfill(5)
    return s


def seed_turnos_base(session) -> tuple[int, int, int]:
    """
    Asegura filas ``turno`` id 1 (Mañana) y 2 (Tarde).

    Returns:
        Tupla (creados, actualizados, sin_cambio).
    """
    created = updated = skipped = 0
    turnos = {
        1: TipoTurno.MANIANA,
        2: TipoTurno.TARDE,
    }
    for turno_id, turno_val in turnos.items():
        existing = session.query(Turno).filter(Turno.id == turno_id).first()
        if existing is None:
            session.add(Turno(id=turno_id, turno=turno_val))
            created += 1
        elif existing.turno != turno_val:
            existing.turno = turno_val
            session.add(existing)
            updated += 1
        else:
            skipped += 1
    return created, updated, skipped


def upsert_inspectores_canonicos(session) -> tuple[int, int, int]:
    """
    Inserta o actualiza inspectores de :data:`INSPECTORES_CANONICO` por ``legajo``.

    Returns:
        Tupla (creados, actualizados, sin_cambio).
    """
    created = updated = skipped = 0
    for nombre, legajo, turno_id in INSPECTORES_CANONICO:
        nombre_clean = nombre.strip()
        legajo_norm = _normalize_legajo(legajo)
        existing = session.query(Inspector).filter(Inspector.legajo == legajo_norm).first()
        if existing is None:
            session.add(
                Inspector(
                    nombre=nombre_clean,
                    legajo=legajo_norm,
                    turno_id=int(turno_id),
                )
            )
            created += 1
            continue
        if existing.nombre != nombre_clean or int(existing.turno_id) != int(turno_id):
            existing.nombre = nombre_clean
            existing.turno_id = int(turno_id)
            session.add(existing)
            updated += 1
        else:
            skipped += 1
    return created, updated, skipped


def remove_legacy_placeholder_inspectors(
    session,
    legacy_legajos: frozenset[str] | None = None,
) -> int:
    """
    Elimina inspectores placeholder (legajo 0001–0020) como en la migración.

    - Quita filas ``ruta_grupo_inspector`` que apunten a esos inspectores.
    - Pone ``relevamiento.inspector_id`` en NULL.
    - Borra los ``inspector``; las filas ``actuaciones_inspector`` asociadas
      se eliminan por ON DELETE CASCADE en la FK hacia ``inspector``.

    Parameters:
        session: sesión SQLAlchemy activa.
        legacy_legajos: por defecto :data:`LEGACY_PLACEHOLDER_LEGAJOS`.

    Returns:
        Cantidad de filas ``inspector`` eliminadas.
    """
    legacy = legacy_legajos if legacy_legajos is not None else LEGACY_PLACEHOLDER_LEGAJOS
    ids = [
        row[0]
        for row in session.query(Inspector.id).filter(Inspector.legajo.in_(legacy)).all()
    ]
    if not ids:
        return 0
    session.query(RutaGrupoInspector).filter(RutaGrupoInspector.inspector_id.in_(ids)).delete(
        synchronize_session=False
    )
    session.query(Relevamiento).filter(Relevamiento.inspector_id.in_(ids)).update(
        {Relevamiento.inspector_id: None},
        synchronize_session=False,
    )
    return session.query(Inspector).filter(Inspector.id.in_(ids)).delete(synchronize_session=False)
