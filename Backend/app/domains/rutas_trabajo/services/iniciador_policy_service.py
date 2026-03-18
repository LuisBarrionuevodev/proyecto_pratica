from __future__ import annotations

from dataclasses import dataclass

PRIORIDAD_ALTA = 1
PRIORIDAD_MEDIA = 2
PRIORIDAD_BAJA = 3

_PRIORIDAD_POR_TIPO: dict[str, int] = {
    "REINSPECCION_NOTIFICACION": PRIORIDAD_ALTA,
    "REINSPECCION_OFICIO": PRIORIDAD_ALTA,
    "DENUNCIA": PRIORIDAD_MEDIA,
    "RELEVAMIENTO": PRIORIDAD_BAJA,
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
        prioridad_destino: prioridad sugerida para el iniciador.
    """

    reingresa: bool
    estado_destino: str
    prioridad_destino: int | None


def priority_for_tipo(tipo_iniciador: str) -> int:
    """
    Retorna prioridad operativa por tipo de iniciador.

    Reglas cerradas:
    - RELEVAMIENTO = 3
    - DENUNCIA = 2
    - REINSPECCION_NOTIFICACION = 1
    - REINSPECCION_OFICIO = 1

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

    - LOCAL_CERRADO | INCLEMENCIA_TIEMPO | OTRO -> reingresa PENDIENTE con prioridad alta.
    - NO_EXISTE_LOCAL -> no reingresa operativamente.

    Raises:
        ValueError: si el motivo no es reconocido.
    """

    motivo = (motivo_no_realizado or "").strip().upper()
    if motivo in {"LOCAL_CERRADO", "INCLEMENCIA_TIEMPO", "OTRO"}:
        return ReingresoNoRealizadoDecision(
            reingresa=True,
            estado_destino="PENDIENTE",
            prioridad_destino=PRIORIDAD_ALTA,
        )
    if motivo == "NO_EXISTE_LOCAL":
        return ReingresoNoRealizadoDecision(
            reingresa=False,
            estado_destino="CERRADO_NO_EXISTE_LOCAL",
            prioridad_destino=None,
        )
    raise ValueError(f"motivo_no_realizado inválido: {motivo_no_realizado}")
