from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from pydantic import ValidationError

from app.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.schemas.grid.errors import pydantic_errors_to_cell_map
from app.schemas.grid.batch import ValidateRowResponse
from app.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.services.grid.batch_store import InMemoryBatchStore, DupKey


def _normalize_ot(numero_ot: Any) -> str:
    s = ("" if numero_ot is None else str(numero_ot)).strip()
    return s.zfill(6) if s.isdigit() else s


def build_dup_key(row_validada: ActuacionGridRowIn) -> DupKey:
    """
    Regla de duplicado dentro del lote:
      orden_trabajo_numero + fecha_actuacion
    """
    ot = _normalize_ot(row_validada.orden_trabajo_numero)
    fecha_iso = row_validada.fecha_as_date().isoformat()  # ✅ FIX (sin duplicar variable)
    return (ot, fecha_iso)


class GridValidateService:
    def __init__(self, store: InMemoryBatchStore) -> None:
        self.store = store

    def validate_row(self, batch_id: UUID, row_id: str, raw_row: Dict[str, Any]) -> ValidateRowResponse:
        # 1) Pydantic (fase 1)
        try:
            row = ActuacionGridRowIn.model_validate(raw_row)
        except ValidationError as e:
            return ValidateRowResponse(
                batch_id=batch_id,
                row_id=row_id,
                ok=False,
                errors=pydantic_errors_to_cell_map(e),
                normalized=None,
            )

        # ✅ 1.5) Reglas UI por tipo_actuacion (errores por CELDA para Glide)
        tipo = (row.tipo_actuacion or "").strip().upper()

        if tipo == "NOTIFICACION":
            cell_errors = {}
            if not row.acta_notificacion_num:
                cell_errors["acta_notificacion_num"] = "Obligatorio para NOTIFICACION."
            if not any([row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3]):
                cell_errors["notificacion_motivo_1"] = "Cargá al menos 1 motivo."
            if cell_errors:
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors=cell_errors,
                    normalized=None,
                )

        if tipo == "COMPROBACION":
            cell_errors = {}
            if not row.acta_comprobacion_num:
                cell_errors["acta_comprobacion_num"] = "Obligatorio para COMPROBACION."
            if not row.comprobacion_motivo:
                cell_errors["comprobacion_motivo"] = "Motivo obligatorio en COMPROBACION."
            if cell_errors:
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors=cell_errors,
                    normalized=None,
                )

        if tipo == "DECOMISO":
            cell_errors = {}
            if not row.acta_decomiso_num:
                cell_errors["acta_decomiso_num"] = "Obligatorio para DECOMISO."
            if row.decomiso_kilos_total is None or row.decomiso_kilos_total <= 0:
                cell_errors["decomiso_kilos_total"] = "Kilos debe ser > 0."
            if cell_errors:
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors=cell_errors,
                    normalized=None,
                )

        # 2) Mapper (sin DB)
        payload = map_actuacion_row(row)

        # 3) Duplicados dentro del lote (OT+fecha)
        dup_key = build_dup_key(row)
        other_row = self.store.upsert_row_key(batch_id=batch_id, row_id=row_id, dup_key=dup_key)
        if other_row:
            return ValidateRowResponse(
                batch_id=batch_id,
                row_id=row_id,
                ok=False,
                errors={"_row": f"Duplicado en el lote: misma OT+fecha que {other_row}"},
                normalized=None,
            )

        return ValidateRowResponse(
            batch_id=batch_id,
            row_id=row_id,
            ok=True,
            errors={},
            normalized=payload,
        )
