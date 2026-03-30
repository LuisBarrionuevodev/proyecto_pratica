from __future__ import annotations

from typing import Any, List, Optional

from pydantic import ConfigDict, field_validator, model_validator

from app.domains.actuaciones.schemas.completar_trabajo_cierre_in import CompletarTrabajoCierreIn


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
        ]
        malos = [k for k, ok in bloque if ok]
        if malos:
            raise ValueError(
                "Si hay contraproducencia (visita no realizada), no se deben cargar actas del día ni "
                f"campos extendidos. Campos a vaciar: {', '.join(malos)}."
            )
        return self
