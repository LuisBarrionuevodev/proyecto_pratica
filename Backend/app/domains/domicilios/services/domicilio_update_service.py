"""
Aplicaci?n unificada de edici?n de domicilio operativo (STAB-7).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.database import db
from app.models import Contribuyente, Domicilio, Rubro
from app.domains.actuaciones.attach.domicilio import get_or_create_domicilio
from app.shared.services.domicilio_repo import get_or_create_domicilio_basico
from app.domains.domicilios.schemas.domicilio_edit_policy import EditDomicilioPolicy
from app.domains.domicilios.services.domicilio_edit_policy_service import (
    resolver_policy_edicion_domicilio,
)


@dataclass(frozen=True)
class AplicarDomicilioOutcome:
    """Resultado de aplicar edici?n de domicilio."""

    domicilio: Domicilio | None
    policy: EditDomicilioPolicy
    domicilio_id_anterior: int | None
    domicilio_id_cambio: bool


def _actualizar_rubro_contrib(
    dom: Domicilio,
    *,
    contribuyente: Optional[Contribuyente],
    rubro: Optional[Rubro],
    numero_tipo: str | None,
) -> bool:
    changed = False
    if contribuyente is not None and dom.contribuyente_id != contribuyente.id:
        dom.contribuyente_id = contribuyente.id
        changed = True
    if rubro is not None and dom.rubro_id != rubro.id:
        dom.rubro_id = rubro.id
        changed = True
    if numero_tipo is not None and dom.numero_tipo != numero_tipo:
        dom.numero_tipo = numero_tipo
        changed = True
    if changed:
        db.session.add(dom)
    return changed


def _editar_misma_fila(
    dom: Domicilio,
    cambios: dict[str, Any],
    *,
    contribuyente: Optional[Contribuyente],
    rubro: Optional[Rubro],
) -> Domicilio:
    calle = cambios.get("calle")
    numero = cambios.get("numero")
    if calle is not None:
        calle_txt = str(calle).strip()
        dom.calle = calle_txt
        dom.calle_raw = calle_txt
    if numero is not None:
        dom.numero = str(numero).strip()
    raw_nt = cambios.get("numero_tipo")
    numero_tipo = str(raw_nt).strip().upper() if raw_nt is not None and str(raw_nt).strip() else None
    _actualizar_rubro_contrib(dom, contribuyente=contribuyente, rubro=rubro, numero_tipo=numero_tipo)
    db.session.add(dom)
    return dom


def aplicar_edicion_domicilio_operativo(
    *,
    domicilio_id_actual: int | None,
    cambios: dict[str, Any] | None,
    contribuyente: Optional[Contribuyente] = None,
    rubro: Optional[Rubro] = None,
    contexto: str,
    origen_id: int,
    modo_explicito: str | None = None,
    allow_missing_catalogs: bool = False,
    usar_basico: bool = False,
    relevamiento_id: int | None = None,
) -> AplicarDomicilioOutcome:
    """
    Resuelve policy y aplica edici?n de domicilio sin commit.

    Par?metros:
        domicilio_id_actual: FK actual del origen.
        cambios: calle, numero, numero_tipo, etc.
        contribuyente/rubro: cat?logos (actuaci?n).
        contexto: ACTUACION, RELEVAMIENTO, DENUNCIA, COMPLETAR_TRABAJO.
        origen_id: id del origen para policy.
        modo_explicito: intenci?n del usuario (NUEVO / REASIGNAR).
        allow_missing_catalogs: permite domicilio sin rubro/contrib (actuaci?n).
        usar_basico: relevamiento/denuncia (sin rubro en fila domicilio).
        relevamiento_id: habilita copy-on-write si el origen proviene de relevamiento.

    Retorno:
        ``AplicarDomicilioOutcome`` con domicilio resultante y si cambi? el id.

    Errores:
        ValueError: policy BLOQUEAR o datos insuficientes.
    """
    cambios_dict = dict(cambios or {})
    calle = cambios_dict.get("calle")
    numero = cambios_dict.get("numero")
    if not calle or not numero:
        if domicilio_id_actual is None:
            return AplicarDomicilioOutcome(
                domicilio=None,
                policy=EditDomicilioPolicy(modo="CREAR_NUEVO", motivo="sin_datos"),
                domicilio_id_anterior=None,
                domicilio_id_cambio=False,
            )
        dom = db.session.get(Domicilio, int(domicilio_id_actual))
        if dom and (contribuyente is not None or rubro is not None):
            _actualizar_rubro_contrib(
                dom,
                contribuyente=contribuyente,
                rubro=rubro,
                numero_tipo=None,
            )
            policy = EditDomicilioPolicy(
                modo="EDITAR_MISMA_FILA",
                motivo="solo_rubro_contrib",
                domicilio_id_objetivo=int(dom.id),
            )
            return AplicarDomicilioOutcome(
                domicilio=dom,
                policy=policy,
                domicilio_id_anterior=domicilio_id_actual,
                domicilio_id_cambio=False,
            )
        return AplicarDomicilioOutcome(
            domicilio=dom,
            policy=EditDomicilioPolicy(modo="EDITAR_MISMA_FILA", motivo="sin_cambio_direccion"),
            domicilio_id_anterior=domicilio_id_actual,
            domicilio_id_cambio=False,
        )

    policy = resolver_policy_edicion_domicilio(
        domicilio_id=domicilio_id_actual,
        contexto=contexto,
        origen_id=origen_id,
        cambios=cambios_dict,
        modo_explicito=modo_explicito,
        relevamiento_id=relevamiento_id,
    )
    if policy.modo == "BLOQUEAR":
        raise ValueError(policy.motivo)

    id_anterior = domicilio_id_actual

    if policy.modo == "EDITAR_MISMA_FILA":
        dom = db.session.get(Domicilio, int(policy.domicilio_id_objetivo or domicilio_id_actual))
        if dom is None or dom.deleted_at is not None:
            raise ValueError("Domicilio a editar no encontrado.")
        dom = _editar_misma_fila(dom, cambios_dict, contribuyente=contribuyente, rubro=rubro)
        return AplicarDomicilioOutcome(
            domicilio=dom,
            policy=policy,
            domicilio_id_anterior=id_anterior,
            domicilio_id_cambio=False,
        )

    if policy.modo == "REASIGNAR_EXISTENTE":
        if policy.domicilio_id_objetivo:
            dom = db.session.get(Domicilio, int(policy.domicilio_id_objetivo))
            if dom is None or dom.deleted_at is not None:
                raise ValueError("Domicilio existente para reasignar no encontrado.")
            _actualizar_rubro_contrib(
                dom,
                contribuyente=contribuyente,
                rubro=rubro,
                numero_tipo=(
                    str(cambios_dict["numero_tipo"]).strip().upper()
                    if cambios_dict.get("numero_tipo")
                    else None
                ),
            )
            return AplicarDomicilioOutcome(
                domicilio=dom,
                policy=policy,
                domicilio_id_anterior=id_anterior,
                domicilio_id_cambio=int(dom.id) != int(id_anterior or 0),
            )

    # CREAR_NUEVO: comportamiento historico get-or-create.
    if usar_basico:
        dom = get_or_create_domicilio_basico(str(calle).strip(), str(numero).strip())
        _actualizar_rubro_contrib(
            dom,
            contribuyente=contribuyente,
            rubro=rubro,
            numero_tipo=(
                str(cambios_dict["numero_tipo"]).strip().upper()
                if cambios_dict.get("numero_tipo")
                else None
            ),
        )
    else:
        dom = get_or_create_domicilio(
            cambios_dict,
            contribuyente,
            rubro,
            allow_missing_catalogs=allow_missing_catalogs,
        )

    nuevo_id = int(dom.id) if dom else None
    return AplicarDomicilioOutcome(
        domicilio=dom,
        policy=policy,
        domicilio_id_anterior=id_anterior,
        domicilio_id_cambio=nuevo_id is not None and nuevo_id != id_anterior,
    )
