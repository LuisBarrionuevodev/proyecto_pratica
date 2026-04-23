from __future__ import annotations

from datetime import date

from app.database import db
from app.models import RutaTrabajo

# Valores del enum `estado_ruta_enum` en `ruta_trabajo` (SQLAlchemy / migraciones).
_ESTADOS_RUTA_PERMITIDOS: frozenset[str] = frozenset(
    {"BORRADOR", "PUBLICADA", "EN_CURSO", "CERRADA", "CANCELADA"}
)


def _validar_estados(estados: tuple[str, ...]) -> tuple[str, ...]:
    if not estados:
        raise ValueError("Debe indicarse al menos un estado_ruta para listar")
    out: list[str] = []
    for raw in estados:
        e = str(raw).strip().upper()
        if e not in _ESTADOS_RUTA_PERMITIDOS:
            raise ValueError(
                f"estado_ruta no válido: {raw!r}. Valores permitidos: "
                f"{', '.join(sorted(_ESTADOS_RUTA_PERMITIDOS))}"
            )
        if e not in out:
            out.append(e)
    return tuple(out)


def list_rutas_trabajo(
    *,
    estados: tuple[str, ...] = ("BORRADOR",),
    fecha: date | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[RutaTrabajo], int, int, tuple[str, ...]]:
    """
    Lista rutas de trabajo paginadas filtrando por uno o más ``estado_ruta`` y por fecha.

    Parámetros:
        estados: tupla de estados a incluir (OR). Por defecto solo ``BORRADOR`` (compatibilidad
            con el listado histórico de borradores).
        fecha: si se informa, filtra ``RutaTrabajo.fecha == fecha`` (día exacto). Tiene prioridad
            sobre ``fecha_desde`` / ``fecha_hasta`` (se ignoran si ``fecha`` está presente).
        fecha_desde / fecha_hasta: rango inclusivo en ``RutaTrabajo.fecha`` (solo si ``fecha`` es None).
        page / per_page: paginación 1-based; ``per_page`` acotado a 100.

    Retorno:
        Tupla ``(filas, total, per_page_efectivo, estados_normalizados)`` ordenadas por fecha desc, id desc.

    Errores:
        ValueError: ``page`` / ``per_page`` o ``estados`` inválidos.
    """
    estados_norm = _validar_estados(estados)
    if page < 1:
        raise ValueError("page debe ser >= 1")
    per = max(1, min(int(per_page), 100))
    q = db.session.query(RutaTrabajo).filter(RutaTrabajo.estado_ruta.in_(estados_norm))

    if fecha is not None:
        q = q.filter(RutaTrabajo.fecha == fecha)
    else:
        if fecha_desde is not None:
            q = q.filter(RutaTrabajo.fecha >= fecha_desde)
        if fecha_hasta is not None:
            q = q.filter(RutaTrabajo.fecha <= fecha_hasta)

    total = q.count()
    rows = (
        q.order_by(RutaTrabajo.fecha.desc(), RutaTrabajo.id.desc())
        .offset((page - 1) * per)
        .limit(per)
        .all()
    )
    return rows, int(total), per, estados_norm


def list_rutas_borrador(
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    fecha: date | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[RutaTrabajo], int, int]:
    """
    Lista rutas de trabajo en estado BORRADOR (para reabrir en la UI).

    Parámetros:
        fecha: día exacto (``RutaTrabajo.fecha``); si viene, ignora ``fecha_desde`` / ``fecha_hasta``.
        fecha_desde: si se informa (y no hay ``fecha``), incluye solo rutas con fecha >= este día.
        fecha_hasta: si se informa (y no hay ``fecha``), incluye solo rutas con fecha <= este día.
        page: página 1-based.
        per_page: tamaño de página (acotado internamente).

    Retorno:
        Tupla (filas ordenadas por fecha desc, id desc, total que matchea filtros, per_page efectivo).

    Errores:
        ValueError: page o per_page inválidos.
    """
    rows, total, per, _ = list_rutas_trabajo(
        estados=("BORRADOR",),
        fecha=fecha,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        page=page,
        per_page=per_page,
    )
    return rows, total, per
