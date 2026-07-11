"""
Unicidad de relevamientos por domicilio y establecimiento (PR7.5 / PR7.6).

- NUMERO / OTRO / NULL: bloquea duplicado exacto por ``domicilio_id`` + ``rubro_id`` +
  ``nombre_fantasia`` normalizado. Permite recambio de rubro o nombre en el mismo domicilio.
- ESQUINA: varios activos; bloquea duplicado exacto por domicilio + rubro + ángulo + nombre.
- Legacy ESQUINA sin ángulo ni fantasía: bloqueo en alta; update coexistencia legacy → warning.
"""

from __future__ import annotations

import logging

from app.database import db
from app.domains.grid.services.relevamiento_dup_key import (
    normalizar_campos_establecimiento_para_clave,
)
from app.models import Domicilio, Relevamiento

logger = logging.getLogger(__name__)

RELEVAMIENTO_UNICIDAD_UBICACION_MSG = (
    "Ya existe un relevamiento activo para esta dirección. "
    "En esquinas se permiten múltiples relevamientos."
)

RELEVAMIENTO_UNICIDAD_NUMERO_MSG = (
    "Ya existe un relevamiento activo para este establecimiento en el mismo domicilio. "
    "Si el local cambió, indique un rubro o nombre fantasía distinto."
)

RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG = (
    "Ya existe un relevamiento activo para este establecimiento en la misma esquina. "
    "Para diferenciarlo, indique otro ángulo de esquina o un nombre fantasía distinto."
)


def domicilio_permite_multiples_relevamientos(domicilio: Domicilio) -> bool:
    """
    Indica si el domicilio admite más de un relevamiento activo (solo esquinas).

    Parámetros:
        domicilio: instancia en sesión, con ``numero_tipo`` ya normalizado.

    Retorno:
        True si ``numero_tipo`` es ESQUINA; False en caso contrario o si es None.
    """
    return (domicilio.numero_tipo or "").upper() == "ESQUINA"


def _es_establecimiento_legacy_vacio(
    nombre_fantasia: str | None,
    angulo_esquina: str | None,
) -> bool:
    nf_key, ang_key = normalizar_campos_establecimiento_para_clave(nombre_fantasia, angulo_esquina)
    return nf_key is None and ang_key is None


def _mismo_establecimiento_esquina(
    rel: Relevamiento,
    *,
    rubro_id: int | None,
    nombre_fantasia: str | None,
    angulo_esquina: str | None,
) -> bool:
    nf_key, ang_key = normalizar_campos_establecimiento_para_clave(nombre_fantasia, angulo_esquina)
    rel_nf, rel_ang = normalizar_campos_establecimiento_para_clave(
        rel.nombre_fantasia,
        rel.angulo_esquina,
    )
    return rel.rubro_id == rubro_id and rel_nf == nf_key and rel_ang == ang_key


def _mismo_establecimiento_numero(
    rel: Relevamiento,
    *,
    rubro_id: int | None,
    nombre_fantasia: str | None,
) -> bool:
    nf_key, _ = normalizar_campos_establecimiento_para_clave(nombre_fantasia, None)
    rel_nf, _ = normalizar_campos_establecimiento_para_clave(rel.nombre_fantasia, None)
    return rel.rubro_id == rubro_id and rel_nf == nf_key


def _buscar_conflicto_establecimiento_esquina(
    domicilio_id: int,
    *,
    rubro_id: int | None,
    nombre_fantasia: str | None,
    angulo_esquina: str | None,
    exclude_relevamiento_id: int | None = None,
) -> Relevamiento | None:
    q = Relevamiento.query.filter(
        Relevamiento.domicilio_id == domicilio_id,
        Relevamiento.deleted_at.is_(None),
    )
    if exclude_relevamiento_id is not None:
        q = q.filter(Relevamiento.id != exclude_relevamiento_id)
    for rel in q.all():
        if _mismo_establecimiento_esquina(
            rel,
            rubro_id=rubro_id,
            nombre_fantasia=nombre_fantasia,
            angulo_esquina=angulo_esquina,
        ):
            return rel
    return None


def _buscar_conflicto_establecimiento_numero(
    domicilio_id: int,
    *,
    rubro_id: int | None,
    nombre_fantasia: str | None,
    exclude_relevamiento_id: int | None = None,
) -> Relevamiento | None:
    q = Relevamiento.query.filter(
        Relevamiento.domicilio_id == domicilio_id,
        Relevamiento.deleted_at.is_(None),
    )
    if exclude_relevamiento_id is not None:
        q = q.filter(Relevamiento.id != exclude_relevamiento_id)
    for rel in q.all():
        if _mismo_establecimiento_numero(
            rel,
            rubro_id=rubro_id,
            nombre_fantasia=nombre_fantasia,
        ):
            return rel
    return None


def existe_relevamiento_activo_mismo_establecimiento_esquina(
    *,
    calle: str,
    numero: str,
    rubro_id: int | None,
    nombre_fantasia: str | None,
    angulo_esquina: str | None,
    exclude_relevamiento_id: int | None = None,
) -> bool:
    """
    True si ya hay un relevamiento activo con la misma identidad de establecimiento en ESQUINA.
    """
    calle_norm = (calle or "").strip()
    numero_norm = (numero or "").strip()
    dom = (
        Domicilio.query.filter_by(calle=calle_norm, numero=numero_norm)
        .filter(Domicilio.deleted_at.is_(None))
        .first()
    )
    if not dom or not domicilio_permite_multiples_relevamientos(dom):
        return False
    return (
        _buscar_conflicto_establecimiento_esquina(
            dom.id,
            rubro_id=rubro_id,
            nombre_fantasia=nombre_fantasia,
            angulo_esquina=angulo_esquina,
            exclude_relevamiento_id=exclude_relevamiento_id,
        )
        is not None
    )


def existe_relevamiento_activo_mismo_establecimiento_numero(
    *,
    calle: str,
    numero: str,
    rubro_id: int | None,
    nombre_fantasia: str | None,
    exclude_relevamiento_id: int | None = None,
) -> bool:
    """
    True si ya hay un relevamiento activo con la misma identidad en domicilio NUMERO/OTRO.
    """
    calle_norm = (calle or "").strip()
    numero_norm = (numero or "").strip()
    dom = (
        Domicilio.query.filter_by(calle=calle_norm, numero=numero_norm)
        .filter(Domicilio.deleted_at.is_(None))
        .first()
    )
    if not dom or domicilio_permite_multiples_relevamientos(dom):
        return False
    return (
        _buscar_conflicto_establecimiento_numero(
            dom.id,
            rubro_id=rubro_id,
            nombre_fantasia=nombre_fantasia,
            exclude_relevamiento_id=exclude_relevamiento_id,
        )
        is not None
    )


def assert_sin_relevamiento_activo_duplicado(
    domicilio: Domicilio,
    *,
    rubro_id: int | None = None,
    nombre_fantasia: str | None = None,
    angulo_esquina: str | None = None,
    exclude_relevamiento_id: int | None = None,
) -> None:
    """
    Bloquea alta o cambio si viola unicidad por establecimiento (NUMERO o ESQUINA).

    Parámetros:
        domicilio: domicilio ya normalizado (``numero_tipo`` definido).
        rubro_id, nombre_fantasia, angulo_esquina: identidad del establecimiento.
        exclude_relevamiento_id: id a ignorar (updates).

    Errores:
        ValueError: si la regla de unicidad no se cumple.
    """
    if domicilio_permite_multiples_relevamientos(domicilio):
        conflicto = _buscar_conflicto_establecimiento_esquina(
            domicilio.id,
            rubro_id=rubro_id,
            nombre_fantasia=nombre_fantasia,
            angulo_esquina=angulo_esquina,
            exclude_relevamiento_id=exclude_relevamiento_id,
        )
        if conflicto is None:
            return
        candidato_legacy = _es_establecimiento_legacy_vacio(nombre_fantasia, angulo_esquina)
        conflicto_legacy = _es_establecimiento_legacy_vacio(
            conflicto.nombre_fantasia,
            conflicto.angulo_esquina,
        )
        if (
            exclude_relevamiento_id is not None
            and candidato_legacy
            and conflicto_legacy
        ):
            logger.warning(
                "PR7.5 legacy ESQUINA: coexisten relevamientos id=%s e id=%s "
                "mismo domicilio_id=%s rubro_id=%s sin ángulo ni nombre fantasía. "
                "Revisar manualmente o completar discriminadores.",
                exclude_relevamiento_id,
                conflicto.id,
                domicilio.id,
                rubro_id,
            )
            return
        raise ValueError(RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG)

    conflicto = _buscar_conflicto_establecimiento_numero(
        domicilio.id,
        rubro_id=rubro_id,
        nombre_fantasia=nombre_fantasia,
        exclude_relevamiento_id=exclude_relevamiento_id,
    )
    if conflicto is not None:
        raise ValueError(RELEVAMIENTO_UNICIDAD_NUMERO_MSG)


def count_active_relevamientos_por_calle_numero(
    calle: str,
    numero: str,
    *,
    rubro_id: int | None = None,
    nombre_fantasia: str | None = None,
    exclude_relevamiento_id: int | None = None,
) -> int:
    """
    Compatibilidad grilla: 1 si existe conflicto de establecimiento NUMERO/OTRO; 0 si no.

    Parámetros:
        calle, numero: texto de domicilio como en la grilla.
        rubro_id, nombre_fantasia: discriminadores PR7.6.
        exclude_relevamiento_id: ignora ese id.

    Retorno:
        1 si hay duplicado exacto; 0 en caso contrario o si es ESQUINA / no hay domicilio.
    """
    if existe_relevamiento_activo_mismo_establecimiento_numero(
        calle=calle,
        numero=numero,
        rubro_id=rubro_id,
        nombre_fantasia=nombre_fantasia,
        exclude_relevamiento_id=exclude_relevamiento_id,
    ):
        return 1
    return 0
