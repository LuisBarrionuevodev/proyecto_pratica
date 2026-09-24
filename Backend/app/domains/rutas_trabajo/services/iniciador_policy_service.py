from __future__ import annotations

from dataclasses import dataclass

# -----------------------------------------------------------------------------
# Escala persistida en `IniciadorRuta.prioridad` — MISMA que
# `planificacion_prioridad.prioridad_categoria_from_value`:
#   1 = BAJA, 2 = MEDIA, 3+ = ALTA (urgentes / cards usan >= 3).
# -----------------------------------------------------------------------------

VALOR_PRIORIDAD_BAJA = 1
VALOR_PRIORIDAD_MEDIA = 2
VALOR_PRIORIDAD_ALTA = 3

_PRIORIDAD_POR_TIPO: dict[str, int] = {
    # Relevamiento operativo normal: siempre BAJA (no urgentes; nunca “alta” por defecto).
    "RELEVAMIENTO": VALOR_PRIORIDAD_BAJA,
    # Prioridad alta por defecto (denuncia, reinspección, derivados de oficio).
    "DENUNCIA": VALOR_PRIORIDAD_ALTA,
    "REINSPECCION_NOTIFICACION": VALOR_PRIORIDAD_ALTA,
    "REINSPECCION_OFICIO": VALOR_PRIORIDAD_ALTA,
    "VERIFICAR_INFORMAR_OFICIO": VALOR_PRIORIDAD_ALTA,
    "RATIFICACION_CLAUSURA_OFICIO": VALOR_PRIORIDAD_ALTA,
    "RATIFICACION_DECOMISO_OFICIO": VALOR_PRIORIDAD_ALTA,
}

_ESTADOS_INACTIVOS: tuple[str, ...] = (
    "ANULADO",
    "CERRADO",
    "CERRADO_NO_EXISTE_LOCAL",
)


@dataclass(frozen=True)
class ReingresoNoRealizadoDecision:
    """
    Resultado de la regla de reingreso cuando un trabajo queda NO_REALIZADO.

    Attributes:
        reingresa: indica si debe volver al backlog operativo.
        estado_destino: estado sugerido para el iniciador.
        prioridad_destino: prioridad sugerida para el iniciador (escala 1=BAJA, 3+=ALTA).
    """

    reingresa: bool
    estado_destino: str
    prioridad_destino: int | None


def priority_for_tipo(tipo_iniciador: str) -> int:
    """
    Retorna prioridad numérica persistible según tipo de iniciador.

    Escala alineada a Planificación (M1/M3): 1=BAJA, 2=MEDIA, 3+=ALTA.

    Reglas:
    - RELEVAMIENTO → 1 (BAJA; no entra a urgentes por tipo).
    - DENUNCIA, REINSPECCION_NOTIFICACION, derivados de oficio → 3 (ALTA).

    Raises:
        ValueError: si el tipo no tiene prioridad definida en la policy.
    """

    tipo = (tipo_iniciador or "").strip().upper()
    prioridad = _PRIORIDAD_POR_TIPO.get(tipo)
    if prioridad is None:
        raise ValueError(f"tipo_iniciador sin prioridad definida: {tipo_iniciador}")
    return prioridad


def inactive_estados() -> tuple[str, ...]:
    """
    Retorna estados inactivos usados en filtros SQL para deduplicación.
    """

    return _ESTADOS_INACTIVOS


def is_estado_activo(estado_iniciador: str | None) -> bool:
    """
    Indica si un estado de iniciador se considera operativo/activo.
    """

    if estado_iniciador is None:
        return False
    return estado_iniciador not in _ESTADOS_INACTIVOS


def resolve_reingreso_no_realizado(motivo_no_realizado: str | None) -> ReingresoNoRealizadoDecision:
    """
    Resuelve regla de reingreso para NO_REALIZADO.

    - LOCAL_CERRADO | INCLEMENCIA_TIEMPO | OTRO -> reingresa PENDIENTE con prioridad alta (>=3).
    - NO_EXISTE_LOCAL -> no reingresa operativamente.

    Raises:
        ValueError: si el motivo no es reconocido.
    """

    motivo = (motivo_no_realizado or "").strip().upper()
    if motivo in {"LOCAL_CERRADO", "INCLEMENCIA_TIEMPO", "OTRO"}:
        return ReingresoNoRealizadoDecision(
            reingresa=True,
            estado_destino="PENDIENTE",
            prioridad_destino=VALOR_PRIORIDAD_ALTA,
        )
    if motivo == "NO_EXISTE_LOCAL":
        return ReingresoNoRealizadoDecision(
            reingresa=False,
            estado_destino="CERRADO_NO_EXISTE_LOCAL",
            prioridad_destino=None,
        )
    raise ValueError(f"motivo_no_realizado inválido: {motivo_no_realizado}")
