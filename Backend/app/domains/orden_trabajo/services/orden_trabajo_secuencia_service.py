from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import exists

from app.database import db
from app.models import OrdenTrabajo, OrdenTrabajoContador, OrdenTrabajoContadorAudit
from app.utils.actas import format_ot_display


@dataclass(frozen=True)
class OtSecuenciaPreview:
    """Vista read-only de la secuencia OT (sin reserva)."""

    next_value: int
    next_display: str
    count: int
    first_display: str | None
    last_display: str | None
    skipped_count: int
    displays: tuple[str, ...]


@dataclass(frozen=True)
class OtAsignacionAutomatica:
    """OT creada por allocator automático."""

    sequence_value: int
    display: str
    orden_trabajo_id: int


def _numero_acta_ocupado(display: str) -> bool:
    """
    Indica si ``numero_acta`` ya existe (cualquier año, incluye soft-deleted).

    Parámetros:
        display: valor formateado de ``numero_acta``.

    Retorno:
        True si hay al menos un registro con ese ``numero_acta``.
    """
    return bool(
        db.session.query(
            exists().where(OrdenTrabajo.numero_acta == display)
        ).scalar()
    )


def _primer_asignable_desde(candidate: int) -> int:
    """
    Avanza ``candidate`` hasta el primer entero cuyo display no esté ocupado.

    Parámetros:
        candidate: valor inicial de secuencia (>= 1 típicamente).

    Retorno:
        Primer entero libre >= candidate.
    """
    value = int(candidate)
    while _numero_acta_ocupado(format_ot_display(value)):
        value += 1
    return value


def next_available_candidates(candidate: int, count: int) -> tuple[list[int], int, int]:
    """
    Busca ``count`` valores de secuencia disponibles desde ``candidate``.

    Regla única compartida por preview (read-only) y publicación (definitiva bajo lock):
    para cada entero, si ``numero_acta == format_ot_display(candidate)`` existe en cualquier
    año (incluye soft-deleted y legacy sin ``numero_secuencia_global``), se omite.

    Parámetros:
        candidate: primer entero a evaluar (punto de búsqueda; no garantiza asignación).
        count: cantidad de OT a resolver.

    Retorno:
        Tupla (valores_asignados, skipped_count, siguiente_candidate_tras_ultimo_evaluado).
        ``siguiente_candidate`` es el primer entero posterior al último inspeccionado/asignado.
    """
    if count < 0:
        raise ValueError("count debe ser >= 0")
    if count == 0:
        return [], 0, int(candidate)

    asignados: list[int] = []
    skipped = 0
    value = int(candidate)
    while len(asignados) < count:
        if _numero_acta_ocupado(format_ot_display(value)):
            skipped += 1
            value += 1
            continue
        asignados.append(value)
        value += 1
    return asignados, skipped, value


def _lock_contador() -> OrdenTrabajoContador:
    """
    Bloquea la fila singleton del contador con ``FOR UPDATE``.

    Retorno:
        Instancia bloqueada de ``OrdenTrabajoContador``.

    Errores:
        RuntimeError: si no existe fila de contador (migración pendiente).
    """
    row = (
        OrdenTrabajoContador.query.order_by(OrdenTrabajoContador.id.asc())
        .with_for_update()
        .first()
    )
    if row is None:
        raise RuntimeError("Contador de orden de trabajo no inicializado")
    return row


def leer_contador_readonly() -> tuple[int, str]:
    """
    Lee ``next_value`` sin bloqueo persistente.

    Retorno:
        Tupla (next_value, next_display).
    """
    row = OrdenTrabajoContador.query.order_by(OrdenTrabajoContador.id.asc()).first()
    if row is None:
        raise RuntimeError("Contador de orden de trabajo no inicializado")
    nv = int(row.next_value)
    return nv, format_ot_display(nv)


def preview_secuencia_ot(count: int = 1) -> OtSecuenciaPreview:
    """
    Preview read-only de próximos números OT (sin lock ni reserva).

    Parámetros:
        count: cantidad de OT a estimar (default 1).

    Retorno:
        ``OtSecuenciaPreview`` con rango estimado y saltos.

    Errores:
        ValueError: count inválido.
        RuntimeError: contador no inicializado.
    """
    if count < 0:
        raise ValueError("count debe ser >= 0")
    next_value, next_display = leer_contador_readonly()
    if count == 0:
        return OtSecuenciaPreview(
            next_value=next_value,
            next_display=next_display,
            count=0,
            first_display=None,
            last_display=None,
            skipped_count=0,
            displays=(),
        )

    valores, skipped, _ = next_available_candidates(next_value, count)
    displays = tuple(format_ot_display(v) for v in valores)
    return OtSecuenciaPreview(
        next_value=next_value,
        next_display=next_display,
        count=count,
        first_display=displays[0] if displays else None,
        last_display=displays[-1] if displays else None,
        skipped_count=skipped,
        displays=displays,
    )


def allocar_rango_orden_trabajo(
    *,
    count: int,
    mes: int,
    anio: int,
) -> list[OtAsignacionAutomatica]:
    """
    Asigna ``count`` OT automáticas bajo lock del contador (transacción externa).

    Parámetros:
        count: cantidad de OT a crear.
        mes: mes documental de la OT.
        anio: año documental de la OT.

    Retorno:
        Lista de asignaciones en orden de consumo.

    Errores:
        ValueError: count inválido.
        RuntimeError: contador no inicializado.
    """
    if count < 0:
        raise ValueError("count debe ser >= 0")
    if count == 0:
        return []

    contador = _lock_contador()
    start = int(contador.next_value)
    valores, _skipped, siguiente = next_available_candidates(start, count)

    resultados: list[OtAsignacionAutomatica] = []
    for seq in valores:
        display = format_ot_display(seq)
        ot = OrdenTrabajo(
            numero_acta=display,
            numero_secuencia_global=seq,
            anio=int(anio),
            mes=int(mes),
        )
        db.session.add(ot)
        db.session.flush()
        resultados.append(
            OtAsignacionAutomatica(
                sequence_value=seq,
                display=display,
                orden_trabajo_id=int(ot.id),
            )
        )

    contador.next_value = int(siguiente)
    db.session.add(contador)
    return resultados


def patch_contador_admin(
    *,
    new_value: int,
    reason: str,
    actor_user_id: int,
) -> tuple[int, int, str, int]:
    """
    Reposiciona el inicio de búsqueda OT normalizando al primer libre >= new_value.

    ``next_value`` indica desde qué entero comienza el allocator; puede moverse
    hacia adelante o hacia atrás. La no reutilización se garantiza por
    ``numero_acta`` existente, no por monotonicidad del contador.

    Parámetros:
        new_value: valor solicitado por admin (>= 1).
        reason: motivo obligatorio (trim, no vacío).
        actor_user_id: usuario admin que ejecuta el cambio.

    Retorno:
        Tupla (old_value, effective_new_value, effective_display, requested_new_value).

    Errores:
        ValueError: reason vacío o new_value inválido.
        RuntimeError: contador ausente.
    """
    reason_clean = (reason or "").strip()
    if not reason_clean:
        raise ValueError("reason es obligatorio")
    if len(reason_clean) > 500:
        raise ValueError("reason demasiado largo (máx 500)")
    if new_value < 1:
        raise ValueError("new_value debe ser >= 1")

    contador = _lock_contador()
    old_value = int(contador.next_value)
    requested = int(new_value)

    effective = _primer_asignable_desde(requested)
    if effective == old_value:
        return old_value, old_value, format_ot_display(old_value), requested

    audit = OrdenTrabajoContadorAudit(
        old_value=old_value,
        new_value=effective,
        requested_new_value=requested,
        reason=reason_clean,
        user_id=int(actor_user_id),
    )
    contador.next_value = effective
    contador.updated_by_user_id = int(actor_user_id)
    db.session.add(contador)
    db.session.add(audit)
    return old_value, effective, format_ot_display(effective), requested


def items_orden_publicacion(items: Sequence) -> list:
    """
    Orden determinista para asignación OT al publicar.

    Orden: ``ruta_grupo_id`` ASC (nulls last), luego ``id`` ASC.
    """
    return sorted(
        items,
        key=lambda it: (
            it.ruta_grupo_id is None,
            it.ruta_grupo_id or 0,
            it.id,
        ),
    )
