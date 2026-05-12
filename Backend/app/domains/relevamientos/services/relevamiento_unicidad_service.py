"""
Unicidad de relevamientos por domicilio (altura vs esquina).

Para domicilios que no son esquina (`numero_tipo != ESQUINA`) solo puede existir
un relevamiento activo por `domicilio_id` (misma calle + número en el modelo actual),
sin importar rubro ni fecha. Los relevamientos con `deleted_at` no cuentan.

Para `ESQUINA` se permiten varios relevamientos en el mismo domicilio.
"""

from __future__ import annotations

from app.database import db
from app.models import Domicilio, Relevamiento

RELEVAMIENTO_UNICIDAD_UBICACION_MSG = (
    "Ya existe un relevamiento activo para esta dirección. "
    "En esquinas se permiten múltiples relevamientos."
)


def domicilio_permite_multiples_relevamientos(domicilio: Domicilio) -> bool:
    """
    Indica si el domicilio admite más de un relevamiento activo (solo esquinas).

    Parámetros:
        domicilio: instancia en sesión, con `numero_tipo` ya normalizado.

    Retorno:
        True si `numero_tipo` es ESQUINA; False en caso contrario o si es None.
    """
    return (domicilio.numero_tipo or "").upper() == "ESQUINA"


def assert_sin_relevamiento_activo_duplicado(
    domicilio: Domicilio,
    *,
    exclude_relevamiento_id: int | None = None,
) -> None:
    """
    Bloquea alta o cambio de domicilio si ya hay otro relevamiento activo en la
    misma ubicación no-esquina.

    Parámetros:
        domicilio: domicilio ya normalizado (`numero_tipo` definido).
        exclude_relevamiento_id: id de relevamiento a ignorar (updates).

    Errores:
        ValueError: si la regla de unicidad no se cumple.
    """
    if domicilio_permite_multiples_relevamientos(domicilio):
        return
    q = Relevamiento.query.filter(
        Relevamiento.domicilio_id == domicilio.id,
        Relevamiento.deleted_at.is_(None),
    )
    if exclude_relevamiento_id is not None:
        q = q.filter(Relevamiento.id != exclude_relevamiento_id)
    if q.first() is not None:
        raise ValueError(RELEVAMIENTO_UNICIDAD_UBICACION_MSG)


def count_active_relevamientos_por_calle_numero(
    calle: str,
    numero: str,
    *,
    exclude_relevamiento_id: int | None = None,
) -> int:
    """
    Cuenta relevamientos activos asociados al domicilio `(calle, numero)` vigente.

    Usado en validación de grilla/lote antes de persistir: misma normalización que
    `get_or_create_domicilio_basico` (strip, sin crear filas).

    Parámetros:
        calle, numero: texto de domicilio como en la grilla.
        exclude_relevamiento_id: ignora ese id (ediciones en el mismo domicilio).

    Retorno:
        Cantidad de relevamientos con `deleted_at` nulo para ese domicilio; 0 si no hay domicilio.
    """
    calle_norm = (calle or "").strip()
    numero_norm = (numero or "").strip()
    dom = (
        Domicilio.query.filter_by(calle=calle_norm, numero=numero_norm)
        .filter(Domicilio.deleted_at.is_(None))
        .first()
    )
    if not dom:
        return 0
    q = Relevamiento.query.filter(
        Relevamiento.domicilio_id == dom.id,
        Relevamiento.deleted_at.is_(None),
    )
    if exclude_relevamiento_id is not None:
        q = q.filter(Relevamiento.id != exclude_relevamiento_id)
    return q.count()
