from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import ValidationError

from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.grid.schemas.batch import ValidateRowResponse
from app.domains.grid.services.row_normalizer import normalize_row_keys, reverse_map_errors
from app.domains.grid.services.registry import get_handler


def _normalize_tipo(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().upper().replace("_", " ")
    return " ".join(s.split())


def _row_has_any_data(row_internal: Dict[str, Any]) -> bool:
    for value in row_internal.values():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return True
    return False


class GridValidateService:
    def __init__(self, store) -> None:
        self.store = store

    def validate_row(self, batch_id: UUID, row_id: str, raw_row: Dict[str, Any], kind: str) -> ValidateRowResponse:
        """
        Valida una fila del grid (sin tocar DB):
        - Pydantic del handler (incluye normalizaciones + reglas base)
        - Reglas UI adicionales por tipo (solo actuaciones)
        - Mapper a payload canon según dominio
        - Duplicados dentro del lote (si aplica)
        """
        handler = get_handler(kind)

        # 0) Normalización de headers Glide -> snake_case interno
        row_internal = normalize_row_keys(raw_row, handler.column_map)

        # Si la fila quedó vacía, limpiar la dup_key y no validar
        if not _row_has_any_data(row_internal):
            self.store.clear_row_key(batch_id=batch_id, row_id=row_id)
            return ValidateRowResponse(
                batch_id=batch_id,
                row_id=row_id,
                ok=True,
                errors={},
                normalized=None,
            )

        # 1) Pydantic (fase 1)
        try:
            row = handler.schema.model_validate(row_internal)
        except ValidationError as e:
            errors_internal = pydantic_errors_to_cell_map(e)
            errors_glide = reverse_map_errors(errors_internal, handler.column_map)
            return ValidateRowResponse(
                batch_id=batch_id,
                row_id=row_id,
                ok=False,
                errors=errors_glide,
                normalized=None,
            )

        # 1.5) Reglas UI específicas de actuaciones
        if kind == "actuaciones":
            tipo_norm = _normalize_tipo(row.tipo_actuacion)

            if tipo_norm == "REINSPECCION" and not row.notificacion_previa_num:
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors={"notificacion_previa_num": "Obligatorio para REINSPECCIÓN."},
                    normalized=None,
                )

            if tipo_norm in (
                "RATIFICACION DE CLAUSURA",
                "RATIFICACION DE DECOMISO",
                "VERIFICAR E INFORMAR",
            ) and not row.comprobacion_previa_num:
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors={"comprobacion_previa_num": "Obligatorio para este tipo (requiere comprobación previa)."},
                    normalized=None,
                )

            if row.decomiso_kilos_total is not None and row.decomiso_kilos_total <= 0:
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors={"decomiso_kilos_total": "Kilos debe ser > 0."},
                    normalized=None,
                )

        # 2) Mapper (sin DB)
        payload = handler.mapper(row)

        # 3) Duplicados dentro del lote (si aplica)
        if handler.dup_key_builder:
            dup_key = handler.dup_key_builder(row)
            if dup_key:
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
