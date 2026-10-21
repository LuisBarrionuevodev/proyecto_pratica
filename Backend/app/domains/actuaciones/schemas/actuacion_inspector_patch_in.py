"""PUT parcial de actuación para rol Inspector (Mis trabajos → Editar datos)."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import ActaCanalQuitarTipo
from app.domains.actuaciones.schemas.grid.actuacion_row_in import (
    _clean_str,
    _coerce_catalog_value,
    _zfill6_if_digit,
)
from app.domains.actuaciones.services.actas_quitar_canal_actas_service import (
    normalizar_tipo_acta_canal,
)
from app.domains.actuaciones.schemas.item_acta_inspeccion_estado_in import (
    ItemActaInspeccionEstadoIn,
)
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    contraproducencia_es_familia_no_existe_local,
    map_contraproducencia_alias_to_catalog_nombre,
)
from app.database import db
from app.models import CatalogContraproducencia, CatalogMotivoComprobacion, CatalogTipoActuacion


class ActuacionInspectorPatchIn(BaseModel):
    """
    Campos editables por Inspector en PUT /actuaciones/:id.

    No incluye fecha, OT, inspectores ni metadatos de pertenencia. ``extra=forbid`` rechaza
    cualquier otra clave de primer nivel.
    """

    model_config = ConfigDict(extra="forbid")

    rubro_nombre: Optional[str] = None
    nombre_local: Optional[str] = None
    tipo_actuacion: Optional[str] = None
    contraproducencia: Optional[str] = None
    limpiar_contraproducencia: bool = False
    limpiar_contribuyente: bool = False
    actas_a_quitar: Optional[list[ActaCanalQuitarTipo]] = None

    calle: Optional[str] = None
    numero: Optional[str] = None
    numero_tipo: Optional[str] = None

    doc_nro: Optional[str] = None
    contrib_apellido: Optional[str] = None
    contrib_nombre: Optional[str] = None
    razon_social: Optional[str] = None

    acta_inspeccion_num: Optional[str] = None
    items_acta_inspeccion: Optional[List[ItemActaInspeccionEstadoIn]] = None
    cantidad_personas_sin_carnet_sanidad: Optional[int] = Field(default=None, ge=0)

    acta_notificacion_num: Optional[str] = None
    notificacion_motivo_1: Optional[str] = None
    notificacion_motivo_2: Optional[str] = None
    notificacion_motivo_3: Optional[str] = None

    acta_comprobacion_num: Optional[str] = None
    comprobacion_motivo: Optional[str] = None

    acta_clausura_num: Optional[str] = None

    acta_decomiso_num: Optional[str] = None
    decomiso_kilos_total: Optional[float] = None

    notificacion_previa_num: Optional[str] = None
    comprobacion_previa_num: Optional[str] = None

    solicita_carnet_manipulador: Optional[bool] = None
    telefono_contacto_solicitud_carnet: Optional[str] = None
    faltas_notificacion_subsanadas: Optional[bool] = None

    observaciones_ejecucion: Optional[str] = Field(default=None, max_length=4000)

    @model_validator(mode="before")
    @classmethod
    def rechazar_contrato_checklist_v1(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "items_acta_inspeccion_ids" in data:
            raise ValueError(
                "items_acta_inspeccion_ids ya no es válido. Use items_acta_inspeccion con estado BIEN u OBSERVADO."
            )
        return data

    @field_validator(
        "acta_inspeccion_num",
        "acta_notificacion_num",
        "acta_comprobacion_num",
        "acta_clausura_num",
        "acta_decomiso_num",
        "notificacion_previa_num",
        "comprobacion_previa_num",
        mode="before",
    )
    @classmethod
    def normalize_num6(cls, v: Any) -> Any:
        return _zfill6_if_digit(v)

    @field_validator(
        "rubro_nombre",
        "nombre_local",
        "calle",
        "numero",
        "doc_nro",
        "contrib_apellido",
        "contrib_nombre",
        "razon_social",
        "comprobacion_motivo",
        "notificacion_motivo_1",
        "notificacion_motivo_2",
        "notificacion_motivo_3",
        mode="before",
    )
    @classmethod
    def strip_empty_to_none(cls, v: Any) -> Any:
        return _clean_str(v)

    @field_validator("tipo_actuacion", mode="before")
    @classmethod
    def parse_tipo(cls, v: Any) -> Any:
        return _coerce_catalog_value(
            v,
            CatalogTipoActuacion,
            "tipo",
            strip_prefix="TIPO.",
        )

    @field_validator("contraproducencia", mode="before")
    @classmethod
    def parse_contra(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            return v
        s = v.strip()
        if not s:
            return None
        if db.session is None:  # pragma: no cover
            return s
        s = map_contraproducencia_alias_to_catalog_nombre(s)
        try:
            return _coerce_catalog_value(s, CatalogContraproducencia, "contraproducencia")
        except ValueError:
            from app.domains.actuaciones.schemas.grid.actuacion_row_in import _upper_norm

            want = _upper_norm(s).replace("/", " ")

            def _ck_loose(x: str) -> str:
                z = x.upper().replace("_", " ").replace("/", " ")
                return " ".join(z.split())

            for (nombre,) in db.session.query(CatalogContraproducencia.nombre).all():
                if nombre and _ck_loose(str(nombre)) == _ck_loose(s):
                    return str(nombre).strip()
            if contraproducencia_es_familia_no_existe_local(s):
                for (nombre,) in db.session.query(CatalogContraproducencia.nombre).all():
                    if nombre and contraproducencia_es_familia_no_existe_local(str(nombre)):
                        return str(nombre).strip()
            raise ValueError("contraproducencia inválido.")

    @field_validator("items_acta_inspeccion", mode="before")
    @classmethod
    def normalize_items_acta_inspeccion(cls, v: Any) -> Any:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("items_acta_inspeccion debe ser una lista.")
        return v

    @field_validator("actas_a_quitar", mode="before")
    @classmethod
    def normalize_actas_a_quitar(cls, v: object) -> object:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("actas_a_quitar debe ser una lista de tipos de acta.")
        out: list[str] = []
        seen: set[str] = set()
        for raw in v:
            t = normalizar_tipo_acta_canal(str(raw))
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out or None

    @field_validator("comprobacion_motivo", mode="before")
    @classmethod
    def parse_motivo_comprobacion(cls, v: Any) -> Any:
        return _coerce_catalog_value(v, CatalogMotivoComprobacion, "motivo de comprobación")
