"""Helpers PR12 — evitar contaminación operativa en domicilios compartidos."""

from __future__ import annotations

from typing import Any

from app.database import db
from app.models import Actuaciones, Contribuyente, Denuncia, Domicilio, Relevamiento, Rubro


def domicilio_compartido_operativamente(
    domicilio_id: int,
    *,
    exclude_actuacion_id: int | None = None,
    exclude_relevamiento_id: int | None = None,
    exclude_denuncia_id: int | None = None,
) -> bool:
    """
    True si otro registro operativo primario referencia el mismo domicilio.

    No cuenta ``iniciador_ruta`` (espejo del origen). Solo relevamiento, denuncia y actuación.

    Parámetros:
        domicilio_id: fila de domicilio a evaluar.
        exclude_*: ids a ignorar en el conteo (registro en edición).

    Retorno:
        True si hay al menos otro uso activo del domicilio.
    """
    did = int(domicilio_id)

    q_rel = Relevamiento.query.filter(
        Relevamiento.domicilio_id == did,
        Relevamiento.deleted_at.is_(None),
    )
    if exclude_relevamiento_id is not None:
        q_rel = q_rel.filter(Relevamiento.id != int(exclude_relevamiento_id))
    if q_rel.limit(1).first() is not None:
        return True

    q_den = Denuncia.query.filter(
        Denuncia.domicilio_id == did,
        Denuncia.deleted_at.is_(None),
    )
    if exclude_denuncia_id is not None:
        q_den = q_den.filter(Denuncia.id != int(exclude_denuncia_id))
    if q_den.limit(1).first() is not None:
        return True

    q_act = db.session.query(Actuaciones.id).filter(Actuaciones.domicilio_id == did)
    if exclude_actuacion_id is not None:
        q_act = q_act.filter(Actuaciones.id != int(exclude_actuacion_id))
    if q_act.limit(1).first() is not None:
        return True

    return False


def debe_fork_domicilio_operativo(
    dom: Domicilio,
    *,
    contribuyente: Contribuyente | None,
    rubro: Rubro | None,
    exclude_actuacion_id: int | None = None,
    exclude_relevamiento_id: int | None = None,
    exclude_denuncia_id: int | None = None,
) -> bool:
    """
    True si aplicar rubro/contrib al domicilio existente contaminaría otros orígenes.

    Parámetros:
        dom: domicilio existente (misma calle/número).
        contribuyente/rubro: valores operativos solicitados.

    Retorno:
        True si conviene clonar fila en lugar de mutar ``dom``.
    """
    contrib_id = contribuyente.id if contribuyente is not None else None
    rubro_id = rubro.id if rubro is not None else None

    conflicto_contrib = (
        contrib_id is not None
        and dom.contribuyente_id is not None
        and int(dom.contribuyente_id) != int(contrib_id)
    )
    conflicto_rubro = (
        rubro_id is not None
        and dom.rubro_id is not None
        and int(dom.rubro_id) != int(rubro_id)
    )
    if conflicto_contrib or conflicto_rubro:
        return True

    if contrib_id is not None or rubro_id is not None:
        return domicilio_compartido_operativamente(
            int(dom.id),
            exclude_actuacion_id=exclude_actuacion_id,
            exclude_relevamiento_id=exclude_relevamiento_id,
            exclude_denuncia_id=exclude_denuncia_id,
        )

    return False


_GEO_COPY_FIELDS: tuple[str, ...] = (
    "calle",
    "numero",
    "numero_tipo",
    "cp",
    "ciudad",
    "provincia",
    "pais",
    "barrio_id",
    "distrito_id",
    "calle_raw",
    "calle_normalizada",
    "calle_key",
    "calle_catalogo_id",
    "calle_norm_status",
    "calle_norm_score",
    "calle_norm_error",
    "calle_norm_updated_at",
    "esquina_raw",
    "esquina_normalizada",
    "esquina_catalogo_id",
    "esquina_norm_status",
    "esquina_norm_score",
    "esquina_norm_error",
    "esquina_norm_updated_at",
)


def clonar_domicilio_operativo(
    base: Domicilio,
    *,
    contribuyente: Contribuyente | None,
    rubro: Rubro | None,
    numero_tipo: str | None = None,
) -> Domicilio:
    """
    Crea una fila nueva de domicilio copiando geografía y aplicando rubro/contrib propios.

    Parámetros:
        base: domicilio origen (geo).
        contribuyente/rubro: catálogos operativos de la actuación/cierre.
        numero_tipo: override opcional de tipo de número.

    Retorno:
        Instancia ``Domicilio`` nueva (sin flush).
    """
    data: dict[str, Any] = {}
    for field in _GEO_COPY_FIELDS:
        if hasattr(base, field):
            data[field] = getattr(base, field)
    if numero_tipo is not None:
        data["numero_tipo"] = numero_tipo
    data["contribuyente_id"] = contribuyente.id if contribuyente is not None else None
    data["rubro_id"] = rubro.id if rubro is not None else None
    return Domicilio(**data)
