from __future__ import annotations

from typing import Optional

from pydantic import field_validator, model_validator

from app.domains.actuaciones.schemas.completar_trabajo_cierre_in import CompletarTrabajoCierreIn


def _clean_str(v: object) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


class CompletarTrabajoCierreCompletoIn(CompletarTrabajoCierreIn):
    """
    Cierre Completar trabajo (fase 3): PR2 + actas del día cuando la visita está **realizada**
    (sin contraproducencia).

    - OT/fecha no se envían; inspectores no se modifican desde este payload.
    - Con contraproducencia (no realizada): no se permiten actas ni oficio/expediente ampliados.
    - Sin previas en payload.
    """

    doc_nro: Optional[str] = None
    contrib_apellido: Optional[str] = None
    contrib_nombre: Optional[str] = None
    numero_tipo: Optional[str] = None

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

    expediente_numero: Optional[str] = None
    expediente_anio: Optional[int] = None
    oficio_numero: Optional[str] = None
    oficio_anio: Optional[int] = None
    oficio_causa: Optional[str] = None

    @field_validator(
        "doc_nro",
        "contrib_apellido",
        "contrib_nombre",
        "acta_inspeccion_num",
        "acta_notificacion_num",
        "notificacion_motivo_1",
        "notificacion_motivo_2",
        "notificacion_motivo_3",
        "acta_comprobacion_num",
        "comprobacion_motivo",
        "acta_clausura_num",
        "acta_decomiso_num",
        "expediente_numero",
        "oficio_numero",
        "oficio_causa",
        mode="before",
    )
    @classmethod
    def strip_str_opt(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return v

    @field_validator("numero_tipo", mode="before")
    @classmethod
    def normalize_numero_tipo(cls, v: object) -> object:
        s = _clean_str(v)
        if not s:
            return None
        u = s.strip().upper()
        if u in ("NUMERO", "ESQUINA", "OTRO"):
            return u
        raise ValueError("numero_tipo inválido.")

    @model_validator(mode="after")
    def comprobacion_exige_motivo_si_hay_acta(self) -> "CompletarTrabajoCierreCompletoIn":
        if self.acta_comprobacion_num and not (self.comprobacion_motivo and str(self.comprobacion_motivo).strip()):
            raise ValueError(
                "Si cargás acta de comprobación, el motivo de comprobación es obligatorio "
                "(catálogo motivos comprobación)."
            )
        return self

    @model_validator(mode="after")
    def no_actas_si_visita_no_realizada(self) -> "CompletarTrabajoCierreCompletoIn":
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
            ("expediente", self.expediente_numero is not None or self.expediente_anio is not None),
            (
                "oficio",
                self.oficio_numero is not None or self.oficio_anio is not None or bool(self.oficio_causa),
            ),
        ]
        malos = [k for k, ok in bloque if ok]
        if malos:
            raise ValueError(
                "Si hay contraproducencia (visita no realizada), no se deben cargar actas del día ni "
                f"oficio/expediente. Campos a vaciar: {', '.join(malos)}."
            )
        return self
