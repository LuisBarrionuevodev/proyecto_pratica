"""
Evita pisar domicilio.rubro_id cuando una esquina comparte domicilio entre varios relevamientos.
"""
from __future__ import annotations

from app.database import db
from app.models import Domicilio, Relevamiento, Rubro


def rubro_para_edicion_domicilio_relevamiento(
    *,
    rubro: Rubro | None,
    calle: str,
    numero: str,
    domicilio_id_actual: int | None = None,
    numero_tipo_hint: str | None = None,
    exclude_relevamiento_id: int | None = None,
) -> Rubro | None:
    """
    Decide si propagar rubro al domicilio compartido en flujo relevamiento.

    En ESQUINA con otro relevamiento activo en el mismo domicilio, retorna None
    para que el rubro canónico quede solo en relevamiento.rubro_id (PR7.3).

    Parámetros:
        rubro: rubro resuelto del payload.
        calle, numero: claves de domicilio.
        domicilio_id_actual: FK actual en update.
        numero_tipo_hint: tipo explícito del payload antes de normalizar.
        exclude_relevamiento_id: id a ignorar en conteo (updates).

    Retorno:
        Rubro a pasar a aplicar_edicion_domicilio_operativo, o None.
    """
    if rubro is None:
        return None

    dom: Domicilio | None = None
    if domicilio_id_actual is not None:
        dom = db.session.get(Domicilio, int(domicilio_id_actual))
    if dom is None:
        calle_norm = (calle or "").strip()
        numero_norm = (numero or "").strip()
        dom = (
            Domicilio.query.filter_by(calle=calle_norm, numero=numero_norm)
            .filter(Domicilio.deleted_at.is_(None))
            .first()
        )

    tipo = (numero_tipo_hint or getattr(dom, "numero_tipo", None) or "").upper()
    if tipo != "ESQUINA":
        return rubro

    dom_id = int(dom.id) if dom is not None else None
    if dom_id is None:
        return rubro

    q = Relevamiento.query.filter(
        Relevamiento.domicilio_id == dom_id,
        Relevamiento.deleted_at.is_(None),
    )
    if exclude_relevamiento_id is not None:
        q = q.filter(Relevamiento.id != exclude_relevamiento_id)
    if q.count() >= 1:
        return None
    return rubro
