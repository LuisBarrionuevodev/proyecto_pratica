from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import ConfigDict, ValidationError, field_validator, model_validator

from app.domains.actuaciones.schemas.completar_trabajo_cierre_in import CompletarTrabajoCierreIn
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    es_no_permite_inspeccion_contraproducencia,
)


def _clean_str(v: object) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _tiene_oficio_en_body(data: dict[str, Any]) -> bool:
    raw = data.get("oficio")
    if isinstance(raw, dict) and any(v not in (None, "") for v in raw.values()):
        return True
    if raw not in (None, "", {}):
        return True
    if data.get("oficio_numero") not in (None, ""):
        return True
    if data.get("oficio_anio") is not None:
        return True
    if data.get("oficio_causa") not in (None, ""):
        return True
    return False


def _tiene_expediente_en_body(data: dict[str, Any]) -> bool:
    raw = data.get("expediente")
    if isinstance(raw, dict) and any(v not in (None, "") for v in raw.values()):
        return True
    if raw not in (None, "", {}):
        return True
    if data.get("expediente_numero") not in (None, ""):
        return True
    if data.get("expediente_anio") is not None:
        return True
    return False


class CompletarTrabajoCierreCompletoIn(CompletarTrabajoCierreIn):
    """
    Body del POST **Completar trabajo** / cerrar ítem (canal operativo de actas).

    - PR2 (tipo, contraproducencia, domicilio/contrib opcional) + actas del día si la visita está
      **realizada** (sin contraproducencia).
    - OT/fecha no se envían (ancla operativa: `ruta_item_id`).
    - Sin previas en payload (origen en iniciador).
    - **Prohibido:** oficio, expediente de comprobación o expediente de oficio; esos documentos solo
      por **Esperando oficio** / **Esperando expediente**.
    """

    model_config = ConfigDict(extra="forbid")

    doc_nro: Optional[str] = None
    contrib_apellido: Optional[str] = None
    contrib_nombre: Optional[str] = None
    razon_social: Optional[str] = None
    nombre_local: Optional[str] = None
    numero_tipo: Optional[str] = None
    inspectores: Optional[List[str]] = None

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

    resultado_cumplimiento_oficio: Optional[Literal["CUMPLE", "NO_CUMPLE"]] = None

    @model_validator(mode="before")
    @classmethod
    def rechazar_oficio_y_expediente_canal_completar_trabajo(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if _tiene_oficio_en_body(data):
            raise ValueError(
                "El canal Completar trabajo no admite oficio. "
                "Use el flujo específico de oficio (Esperando oficio)."
            )
        if _tiene_expediente_en_body(data):
            raise ValueError(
                "El canal Completar trabajo no admite expediente. "
                "Use el flujo específico de expediente (Esperando expediente)."
            )
        return data

    @field_validator(
        "doc_nro",
        "contrib_apellido",
        "contrib_nombre",
        "razon_social",
        "nombre_local",
        "acta_inspeccion_num",
        "acta_notificacion_num",
        "notificacion_motivo_1",
        "notificacion_motivo_2",
        "notificacion_motivo_3",
        "acta_comprobacion_num",
        "comprobacion_motivo",
        "acta_clausura_num",
        "acta_decomiso_num",
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

    @field_validator("resultado_cumplimiento_oficio", mode="before")
    @classmethod
    def normalize_resultado_cumplimiento_oficio(cls, v: object) -> object:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            return v
        u = v.strip().upper()
        if u in ("CUMPLE", "NO_CUMPLE"):
            return u
        raise ValueError("resultado_cumplimiento_oficio debe ser CUMPLE o NO_CUMPLE.")

    @field_validator("inspectores", mode="before")
    @classmethod
    def normalize_inspectores(cls, v: object) -> object:
        if v is None:
            return None
        if not isinstance(v, list):
            return v
        # Lista vacía válida: limpia inspectores en actuación (front envía [] explícito).
        return [str(x).strip() for x in v if str(x).strip()]

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
            msg = (
                "Si cargás acta de comprobación, el motivo de comprobación es obligatorio "
                "(catálogo motivos comprobación)."
            )
            raise ValidationError.from_exception_data(
                self.__class__.__name__,
                [
                    {
                        "type": "value_error",
                        "loc": ("comprobacion_motivo",),
                        "msg": "Value error",
                        "input": None,
                        "ctx": {"error": msg},
                    }
                ],
            )
        return self

    @model_validator(mode="after")
    def notificacion_exige_motivo_si_hay_acta(self) -> "CompletarTrabajoCierreCompletoIn":
        if self.acta_notificacion_num and str(self.acta_notificacion_num).strip():
            if not any(
                [
                    self.notificacion_motivo_1 and str(self.notificacion_motivo_1).strip(),
                    self.notificacion_motivo_2 and str(self.notificacion_motivo_2).strip(),
                    self.notificacion_motivo_3 and str(self.notificacion_motivo_3).strip(),
                ]
            ):
                raise ValidationError.from_exception_data(
                    self.__class__.__name__,
                    [
                        {
                            "type": "value_error",
                            "loc": ("notificacion_motivo_1",),
                            "msg": "Value error",
                            "input": None,
                            "ctx": {"error": "La notificación requiere al menos un motivo."},
                        }
                    ],
                )
        return self

    @model_validator(mode="after")
    def no_actas_si_visita_no_realizada(self) -> "CompletarTrabajoCierreCompletoIn":
        if not self.contraproducencia:
            return self
        if es_no_permite_inspeccion_contraproducencia(self.contraproducencia):
            bloque: list[tuple[str, bool]] = [
                ("acta_inspeccion_num", bool(self.acta_inspeccion_num)),
                ("acta_notificacion_num", bool(self.acta_notificacion_num)),
                ("acta_decomiso_num", bool(self.acta_decomiso_num)),
                (
                    "notificacion_motivos",
                    any(
                        [
                            self.notificacion_motivo_1,
                            self.notificacion_motivo_2,
                            self.notificacion_motivo_3,
                        ]
                    ),
                ),
                ("decomiso_kilos_total", self.decomiso_kilos_total is not None),
                ("resultado_cumplimiento_oficio", self.resultado_cumplimiento_oficio is not None),
            ]
        else:
            bloque = [
                ("acta_inspeccion_num", bool(self.acta_inspeccion_num)),
                ("acta_notificacion_num", bool(self.acta_notificacion_num)),
                ("acta_comprobacion_num", bool(self.acta_comprobacion_num)),
                ("acta_clausura_num", bool(self.acta_clausura_num)),
                ("acta_decomiso_num", bool(self.acta_decomiso_num)),
                (
                    "notificacion_motivos",
                    any(
                        [
                            self.notificacion_motivo_1,
                            self.notificacion_motivo_2,
                            self.notificacion_motivo_3,
                        ]
                    ),
                ),
                ("comprobacion_motivo", bool(self.comprobacion_motivo)),
                ("decomiso_kilos_total", self.decomiso_kilos_total is not None),
                ("resultado_cumplimiento_oficio", self.resultado_cumplimiento_oficio is not None),
            ]
        malos = [k for k, ok in bloque if ok]
        if malos:
            raise ValueError(
                "Si hay contraproducencia (visita no realizada), no se deben cargar actas del día ni "
                f"campos extendidos. Campos a vaciar: {', '.join(malos)}."
            )
        return self

    @model_validator(mode="after")
    def no_permite_inspeccion_exige_acta_comprobacion_y_motivo(self) -> "CompletarTrabajoCierreCompletoIn":
        if not self.contraproducencia or not es_no_permite_inspeccion_contraproducencia(
            self.contraproducencia
        ):
            return self
        acta = (self.acta_comprobacion_num or "").strip()
        motivo = (self.comprobacion_motivo or "").strip()
        if not acta or not motivo:
            msg = (
                "Con contraproducencia NO PERMITE INSPECCION es obligatorio cargar acta de comprobación "
                "y motivo de comprobación."
            )
            raise ValidationError.from_exception_data(
                self.__class__.__name__,
                [
                    {
                        "type": "value_error",
                        "loc": ("acta_comprobacion_num",),
                        "msg": "Value error",
                        "input": None,
                        "ctx": {"error": msg},
                    }
                ],
            )
        return self
