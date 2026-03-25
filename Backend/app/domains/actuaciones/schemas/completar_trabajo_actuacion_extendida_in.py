from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class CompletarTrabajoActuacionExtendidaIn(BaseModel):
    """
    Contrato futuro: cuerpo ampliado para completar la actuación desde Completar trabajo.

    Reglas (fase 1 — documentación; el POST aún usa `CompletarTrabajoCierreIn`):
    - Si hay **contraproducencia** (visita no realizada), **no** deben enviarse actas del día.
    - Sin previas en este módulo.
    """

    contraproducencia: Optional[str] = None
    acta_inspeccion_num: Optional[str] = None
    acta_notificacion_num: Optional[str] = None
    notificacion_motivo_1: Optional[str] = None
    notificacion_motivo_2: Optional[str] = None
    notificacion_motivo_3: Optional[str] = None
    acta_comprobacion_num: Optional[str] = None
    comprobacion_motivo: Optional[str] = None
    acta_clausura_num: Optional[str] = None
    acta_decomiso_num: Optional[str] = None
    decomiso_kilos_total: Optional[float] = None

    @field_validator("contraproducencia", mode="before")
    @classmethod
    def empty_contra(cls, v: object) -> object:
        if v == "":
            return None
        return v

    @model_validator(mode="after")
    def no_actas_si_contraproducencia(self) -> "CompletarTrabajoActuacionExtendidaIn":
        if not self.contraproducencia:
            return self
        bloque: list[tuple[str, bool]] = [
            ("acta_inspeccion_num", bool(self.acta_inspeccion_num)),
            ("acta_notificacion_num", bool(self.acta_notificacion_num)),
            ("acta_comprobacion_num", bool(self.acta_comprobacion_num)),
            ("acta_clausura_num", bool(self.acta_clausura_num)),
            ("acta_decomiso_num", bool(self.acta_decomiso_num)),
            (
                "notificacion_motivos",
                any([self.notificacion_motivo_1, self.notificacion_motivo_2, self.notificacion_motivo_3]),
            ),
            ("comprobacion_motivo", bool(self.comprobacion_motivo)),
            ("decomiso_kilos_total", self.decomiso_kilos_total is not None),
        ]
        malos = [k for k, ok in bloque if ok]
        if malos:
            raise ValueError(
                "Si hay contraproducencia (visita no realizada), no se deben cargar actas del día. "
                f"Campos a vaciar: {', '.join(malos)}."
            )
        return self
