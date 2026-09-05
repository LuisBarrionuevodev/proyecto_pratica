"""
Vinculación de ``establecimiento_operativo`` desde el canal **Actuación** (alta / PUT grilla).

Complementa (sin reemplazar) la resolución en **Completar trabajo**, que sigue siendo el lugar
donde se garantiza EO al cerrar una visita realizada.
"""

from __future__ import annotations

from app.database import db
from app.models import Actuaciones, Domicilio, EstablecimientoOperativo
from app.domains.establecimientos.services.resolve_establecimiento_por_domicilio import (
    resolve_establecimiento_por_domicilio,
)
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    domicilio_puede_resolver_establecimiento_operativo,
    identidad_logica_completa,
)


def _tipo_actuacion_presente(act: Actuaciones) -> bool:
    """True si la actuación tiene tipo operativo persistido (no registro mínimo solo contraproducencia)."""
    t = getattr(act, "tipo", None)
    if t is None:
        return False
    if hasattr(t, "value"):
        t = t.value
    return bool(str(t).strip())


def _domicilio_cumple_ancla_operativa(dom: Domicilio) -> bool:
    """
    Domicilio con datos mínimos para anclar una ficha operativa.

    Requiere titular (contribuyente), rubro y dirección básica no vacía.
    """
    if getattr(dom, "deleted_at", None) is not None:
        return False
    if dom.contribuyente_id is None or dom.rubro_id is None:
        return False
    calle = (dom.calle or "").strip()
    numero = (dom.numero or "").strip()
    return bool(calle and numero)


def _establecimiento_coincide_domicilio(act: Actuaciones) -> bool:
    """True si el EO vinculado (si hay) corresponde al ``domicilio_id`` actual de la actuación."""
    if not act.establecimiento_operativo_id or not act.domicilio_id:
        return False
    eo = db.session.get(EstablecimientoOperativo, act.establecimiento_operativo_id)
    if eo is None:
        return False
    return int(eo.domicilio_id) == int(act.domicilio_id)


def try_vincular_establecimiento_operativo_desde_actuacion(
    act: Actuaciones,
    *,
    created_by_user_id: int,
) -> None:
    """
    Intenta resolver o vincular ``establecimiento_operativo_id`` cuando hay datos suficientes.

    Qué hace:
        - Sin ``domicilio_id``: limpia el vínculo EO en la actuación.
        - Si el EO actual no corresponde al domicilio (**stale**): lo limpia.
        - Si ya hay EO coherente con el domicilio actual: no hace nada (idempotente).
        - Si no cumple política mínima (tipo de actuación, contribuyente y rubro en domicilio,
          calle y número): no crea EO (queda para Completar trabajo u otro flujo).
        - Si cumple: delega en ``resolve_establecimiento_por_domicilio`` (una ficha por domicilio).

    Parámetros:
        act: instancia ORM ya mutada en sesión (domicilio/tipo coherentes con el payload aplicado).
        created_by_user_id: usuario autenticado (auditoría al crear EO).

    Retorno:
        None. Modifica ``act`` en memoria; sin commit.

    Errores:
        Ninguno explícito; integridad DB puede fallar al commit del llamador.
    """
    if act.domicilio_id is None:
        act.establecimiento_operativo_id = None
        return

    dom = db.session.get(Domicilio, act.domicilio_id)
    if dom is None or getattr(dom, "deleted_at", None) is not None:
        act.establecimiento_operativo_id = None
        return

    if not domicilio_puede_resolver_establecimiento_operativo(dom):
        act.establecimiento_operativo_id = None
        return

    if act.establecimiento_operativo_id is not None and not _establecimiento_coincide_domicilio(act):
        act.establecimiento_operativo_id = None

    if act.establecimiento_operativo_id is not None:
        return

    if not _tipo_actuacion_presente(act):
        return

    eid = resolve_establecimiento_por_domicilio(
        act.domicilio_id,
        created_by_user_id=created_by_user_id,
    )
    if eid is not None:
        act.establecimiento_operativo_id = eid
