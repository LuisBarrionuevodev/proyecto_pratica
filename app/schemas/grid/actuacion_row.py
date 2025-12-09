from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ActuacionGridRowIn(BaseModel):
    """
    Esta es la fila de carga de actuaciones
    """

    # campos base
    orden_trabajo_numero: str = Field(..., min_length=1)
    fecha_actuacion: str = Field(..., min_length=1)  # DD/MM/YYYY

    rubro_nombre: Optional[str] = None

    inspector1: Optional[str] = None
    inspector2: Optional[str] = None
    inspector3: Optional[str] = None

    calle: Optional[str] = None
    numero: Optional[str] = None

    tipo_actuacion: Optional[str] = None
    contraproducencia: Optional[str] = None

    # contribuyente
    doc_nro: Optional[str] = None
    contrib_apellido: Optional[str] = None
    contrib_nombre: Optional[str] = None

    # actas y motivos opcionales
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

    # expediente / oficio
    expediente_numero: Optional[str] = None
    expediente_anio: Optional[int] = None

    oficio_numero: Optional[str] = None
    oficio_anio: Optional[int] = None
    oficio_causa: Optional[str] = None  # <-- la dejamos opcional (vos la harás nullable en DB)

    # previas
    notificacion_previa_num: Optional[str] = None
    comprobacion_previa_num: Optional[str] = None

    # -------------------------
    # validaciones simples
    # -------------------------

    @field_validator("fecha_actuacion")
    @classmethod
    def validar_fecha(cls, v: str):
        s = (v or "").strip()
        if not s:
            raise ValueError("La fecha es obligatoria")

        try:
            datetime.strptime(s, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Formato inválido. Usá DD/MM/AAAA")

        return s

    @field_validator(
        "orden_trabajo_numero",
        "rubro_nombre",
        "inspector1",
        "inspector2",
        "inspector3",
        "calle",
        "numero",
        "tipo_actuacion",
        "contraproducencia",
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
        "notificacion_previa_num",
        "comprobacion_previa_num",
        mode="before",
    )
    @classmethod
    def limpiar_strings(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    # normalizar "Avenida"  "Av"
    @field_validator("calle", mode="after")
    @classmethod
    def normalizar_calle_basico(cls, v: Optional[str]):
        if not v:
            return v
        s = v.strip()

        lower = s.lower()
        if lower.startswith("avenida "):
            return "Av " + s[8:].strip()
        if lower.startswith("av. "):
            return "Av " + s[4:].strip()
        if lower == "avenida":
            return "Av"
        return s

    @model_validator(mode="after")
    def validaciones_mvp(self):
        # -------------------------
        # 1) regla de fila vacía
        # -------------------------
        hay_algo_mas = any(
            [
                self.rubro_nombre,
                self.inspector1,
                self.inspector2,
                self.inspector3,
                self.calle,
                self.numero,
                self.tipo_actuacion,
                self.doc_nro,
                self.contrib_apellido,
                self.contrib_nombre,
                self.acta_inspeccion_num,
                self.acta_notificacion_num,
                self.notificacion_motivo_1,
                self.notificacion_motivo_2,
                self.notificacion_motivo_3,
                self.acta_comprobacion_num,
                self.comprobacion_motivo,
                self.acta_clausura_num,
                self.acta_decomiso_num,
                self.decomiso_kilos_total is not None,
                self.expediente_numero,
                self.expediente_anio is not None,
                self.oficio_numero,
                self.oficio_anio is not None,
                self.oficio_causa,
                self.notificacion_previa_num,
                self.comprobacion_previa_num,
            ]
        )

        if not hay_algo_mas and not self.contraproducencia:
            raise ValueError("Si la fila está vacía, debés cargar una contraproducencia.")

        # -------------------------
        # 2) contribuyente mínimo
        # -------------------------
        hay_contrib = any([self.doc_nro, self.contrib_apellido, self.contrib_nombre])
        if hay_contrib and not self.doc_nro:
            raise ValueError("Si cargás contribuyente, el documento es obligatorio.")

        # -------------------------
        # 3) domicilio coherente
        # -------------------------
        if (self.calle and not self.numero) or (self.numero and not self.calle):
            raise ValueError("Si cargás domicilio, debés completar calle y número.")

        # NUEVO: si hay domicilio, en tu DB necesitás rubro y contribuyente
        if self.calle and self.numero:
            if not self.rubro_nombre:
                raise ValueError("Si cargás domicilio, el rubro es obligatorio.")
            if not self.doc_nro:
                raise ValueError("Si cargás domicilio, el documento del contribuyente es obligatorio.")

        # -------------------------
        # 4) notificación coherente
        # -------------------------
        tiene_motivo_notif = any(
            [self.notificacion_motivo_1, self.notificacion_motivo_2, self.notificacion_motivo_3]
        )

        if self.acta_notificacion_num and not tiene_motivo_notif:
            raise ValueError("Si cargás acta de notificación, debés indicar al menos 1 motivo.")

        # NUEVO: motivo sin número no tiene sentido para DB/mapper
        if tiene_motivo_notif and not self.acta_notificacion_num:
            raise ValueError("Si cargás motivos de notificación, debés indicar el número de acta.")

        # -------------------------
        # 5) comprobación coherente
        # -------------------------
        if self.acta_comprobacion_num and not self.comprobacion_motivo:
            raise ValueError("Si cargás acta de comprobación, el motivo es obligatorio.")

        # NUEVO: motivo sin número no tiene sentido
        if self.comprobacion_motivo and not self.acta_comprobacion_num:
            raise ValueError("Si cargás motivo de comprobación, debés indicar el número de acta.")

        # -------------------------
        # 6) decomiso coherente
        # -------------------------
        if self.acta_decomiso_num and self.decomiso_kilos_total is None:
            raise ValueError("Si cargás acta de decomiso, debés indicar kilos totales.")

        # -------------------------
        # 7) expediente coherente
        # -------------------------
        hay_expediente = self.expediente_numero or (self.expediente_anio is not None)
        if hay_expediente:
            if not self.expediente_numero or self.expediente_anio is None:
                raise ValueError("Si cargás expediente, número y año son obligatorios.")

        # -------------------------
        # 8) oficio coherente
        # -------------------------
        # (causa queda opcional porque la vas a hacer nullable en DB)
        hay_oficio = any([self.oficio_numero, self.oficio_anio, self.oficio_causa])
        if hay_oficio:
            if not self.oficio_numero or self.oficio_anio is None:
                raise ValueError("Si cargás oficio, número y año son obligatorios.")
            if not self.comprobacion_previa_num:
                raise ValueError("Si cargás oficio, debés indicar el acta de comprobación previa.")

        return self

    def fecha_as_date(self):
        return datetime.strptime(self.fecha_actuacion, "%d/%m/%Y").date()
