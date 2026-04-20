"""
Seed de relevamientos “corrientes” (Panadería) para pruebas: tanda inicial + ampliación.

Idempotencia:
    Clave lógica (domicilio_id, fecha_seed, rubro_id=Panadería, deleted_at IS NULL).
    Si ya existe un relevamiento activo con esa combinación, no se inserta otro;
    se asegura iniciador RELEVAMIENTO PENDIENTE si faltara.
    ``get_or_create_domicilio_basico`` reutiliza domicilio por (calle, numero) exactos.

Direcciones:
    Se persisten como ``Domicilio.calle`` + ``Domicilio.numero`` (modelo actual).
    El texto de calle respeta lo indicado (incl. ``Av.`` / ``Avenida``); el número va en ``numero``.

Duplicados / variantes de nombre:
    ``get_or_create_domicilio_basico`` no fusiona "Avenida Belgrano" con "Belgrano": son calles
    distintas en DB. Para no cargar dos relevamientos del mismo predio 1629, la lista incluye solo
    ``("Avenida Belgrano", "1629")`` y se omite el par ``("Belgrano", "1629")`` (comentario en tupla).

Pendiente (fuera de esta seed):
    Direcciones tipo esquina sin altura clara, p. ej. ``Monte esquina Colombia`` — ver
    :data:`DIRECCION_PENDIENTE_ESQUINA_MONTE_COLOMBIA`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import (
    inactive_estados,
    priority_for_tipo,
)
from app.models import Domicilio, IniciadorRuta, Inspector, Relevamiento, Rubro, User
from app.shared.services.domicilio_repo import get_or_create_domicilio_basico

# Fecha fija de la semilla: todas las filas de prueba comparten esta fecha para unicidad.
SEED_RELEVAMIENTOS_CORRIENTES_FECHA: date = date(2026, 4, 17)

RUBRO_NOMBRE = "Panadería"

# Documentación: caso esquina explícamente excluido hasta definir modelo/seed de esquinas.
DIRECCION_PENDIENTE_ESQUINA_MONTE_COLOMBIA = "Monte esquina Colombia"

# Tuplas (calle, numero). Orden: tanda inicial, luego ampliación panaderías (sin duplicar filas lógicas).
DIRECCIONES_SEED: tuple[tuple[str, str], ...] = (
    # --- Tanda inicial (4)
    ("Corrientes", "1802"),
    ("Santa Fe", "1261"),
    ("Av. Ejército del Norte", "840"),
    ("Ejército del Norte", "596"),
    # --- Ampliación Panadería (19 netas: 21 listadas − Santa Fe 1261 ya arriba − Belgrano 1629 duplicado de Avenida Belgrano)
    ("Jujuy", "3601"),
    ("Avenida Colón", "601"),
    ("Pasaje Chazarreta", "1666"),
    ("Corrientes", "751"),
    ("Federico Leguera", "2079"),
    ("Ramírez de Velasco", "3199"),
    ("Avenida Belgrano", "1629"),
    # ("Belgrano", "1629") omitido: mismo predio que Avenida Belgrano 1629 bajo lógica actual (calle distinta en DB).
    ("Santa Fe", "1661"),
    ("San Juan", "202"),
    ("Santiago", "1046"),
    ("Florida", "3198"),
    ("Puerredón", "1201"),
    ("San Juan", "3435"),
    ("Constitución", "444"),
    ("San Lorenzo", "2372"),
    ("Silvano Bores", "101"),
    ("La Madrid", "3153"),
    ("Don Bosco", "1725"),
    ("La Pría", "351"),
    # ("Santa Fe", "1261") repetido en listado de ampliación: ya está en tanda inicial.
)

OBSERVACIONES_INICIADOR_PREFIX = "Seed relevamientos corrientes (domicilio calle="


def _ensure_rubro_panaderia() -> tuple[Rubro, bool]:
    """Devuelve (rubro, True) si se insertó en esta llamada."""
    rubro = Rubro.query.filter_by(nombre=RUBRO_NOMBRE).first()
    if rubro is not None:
        return rubro, False
    rubro = Rubro(nombre=RUBRO_NOMBRE)
    db.session.add(rubro)
    db.session.flush()
    return rubro, True


def _first_inspector() -> Inspector:
    insp = Inspector.query.order_by(Inspector.id.asc()).first()
    if insp is None:
        raise ValueError(
            "No hay inspectores en catálogo. Ejecutá antes la seed de inspectores / migraciones."
        )
    return insp


def _first_active_user_id() -> int:
    u = User.query.filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
    if u is None:
        raise ValueError(
            "No hay usuario activo para created_by_user_id / iniciador_ruta. Creá al menos un usuario."
        )
    return int(u.id)


def _ensure_iniciador_relevamiento_pendiente(rel: Relevamiento, user_id: int, dom: Domicilio) -> str:
    """
    Returns:
        ``"created"`` | ``"skipped"`` según si creó iniciador o ya existía operativo.
    """
    existente = (
        IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == rel.id,
            IniciadorRuta.tipo_iniciador == "RELEVAMIENTO",
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )
    if existente:
        return "skipped"

    fecha_origen = rel.fecha
    if not fecha_origen or not rel.domicilio_id:
        raise ValueError("Relevamiento sin fecha o domicilio; no se puede crear iniciador.")

    ir = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="PENDIENTE",
        fecha_origen=fecha_origen,
        anio=int(fecha_origen.year),
        mes=int(fecha_origen.month),
        domicilio_id=int(rel.domicilio_id),
        prioridad=priority_for_tipo("RELEVAMIENTO"),
        relevamiento_id=rel.id,
        created_by_user_id=user_id,
        observaciones=f"{OBSERVACIONES_INICIADOR_PREFIX}{dom.calle!r}, n={dom.numero!r})",
    )
    db.session.add(ir)
    return "created"


def seed_relevamientos_corrientes_chico() -> dict[str, Any]:
    """
    Inserta relevamientos de prueba (rubro Panadería) por cada par en :data:`DIRECCIONES_SEED`
    e iniciadores pendientes asociados.

    Returns:
        Dict con contadores de filas creadas/omitidas, ``fecha_seed``, ``rubro``,
        y ``rubro_panaderia_inserted`` (True si se insertó el rubro en esa corrida).

    Raises:
        ValueError: si faltan inspectores o usuarios activos.
    """
    rubro, rubro_inserted = _ensure_rubro_panaderia()

    inspector = _first_inspector()
    user_id = _first_active_user_id()

    relev_created = relev_skipped = 0
    ini_created = ini_skipped = 0

    for calle, numero in DIRECCIONES_SEED:
        dom = get_or_create_domicilio_basico(calle, numero)
        if dom.rubro_id != rubro.id:
            dom.rubro_id = rubro.id
        normalizar_domicilio_en_sesion(dom)

        existing = (
            Relevamiento.query.filter(
                Relevamiento.domicilio_id == dom.id,
                Relevamiento.fecha == SEED_RELEVAMIENTOS_CORRIENTES_FECHA,
                Relevamiento.rubro_id == rubro.id,
                Relevamiento.deleted_at.is_(None),
            )
            .order_by(Relevamiento.id.desc())
            .first()
        )

        if existing:
            rel = existing
            relev_skipped += 1
        else:
            rel = Relevamiento(
                fecha=SEED_RELEVAMIENTOS_CORRIENTES_FECHA,
                mes=int(SEED_RELEVAMIENTOS_CORRIENTES_FECHA.month),
                anio=int(SEED_RELEVAMIENTOS_CORRIENTES_FECHA.year),
                inspector_id=inspector.id,
                domicilio_id=dom.id,
                rubro_id=rubro.id,
                turno_carga="MANIANA",
                esta_abierto=True,
                created_by_user_id=user_id,
            )
            db.session.add(rel)
            db.session.flush()
            relev_created += 1

        ini = _ensure_iniciador_relevamiento_pendiente(rel, user_id, dom)
        if ini == "created":
            ini_created += 1
        else:
            ini_skipped += 1

    db.session.commit()

    return {
        "relevamientos_created": relev_created,
        "relevamientos_skipped": relev_skipped,
        "iniciadores_created": ini_created,
        "iniciadores_skipped": ini_skipped,
        "fecha_seed": SEED_RELEVAMIENTOS_CORRIENTES_FECHA.isoformat(),
        "rubro": RUBRO_NOMBRE,
        "rubro_panaderia_inserted": rubro_inserted,
        "direcciones_en_seed": len(DIRECCIONES_SEED),
    }
