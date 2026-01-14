from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from pydantic import ValidationError

from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.grid.schemas.batch  import ValidateRowResponse
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn, Tipo


def _normalize_ot(numero_ot: Any) -> str:
    s = ("" if numero_ot is None else str(numero_ot)).strip()
    return s.zfill(6) if s.isdigit() else s


def build_dup_key(row_validada: ActuacionGridRowIn) -> tuple[str, str]:
    """
    Regla de duplicado dentro del lote:
      orden_trabajo_numero + fecha_actuacion (ISO)
    """
    ot = _normalize_ot(row_validada.orden_trabajo_numero)
    fecha_iso = row_validada.fecha_as_date().isoformat()
    return (ot, fecha_iso)


class GridValidateService:
    def __init__(self, store) -> None:
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

        

# ...

        # 1.5) Reglas UI por Tipo (errores por celda)
        if row.tipo_actuacion == Tipo.REINSPECCION and not row.notificacion_previa_num:
            return ValidateRowResponse(
                batch_id=batch_id,
                row_id=row_id,
                ok=False,
                errors={"notificacion_previa_num": "Obligatorio para REINSPECCIÓN."},
                normalized=None,
            )

        if row.tipo_actuacion in (
            Tipo.RATIFICACION_CLAUSURA,
            Tipo.RATIFICACION_DECOMISO,
            Tipo.VERIFICAR_E_INFORMAR,
        ) and not row.comprobacion_previa_num:
            return ValidateRowResponse(
                batch_id=batch_id,
                row_id=row_id,
                ok=False,
                errors={"comprobacion_previa_num": "Obligatorio para este tipo (requiere comprobación previa)."},
                normalized=None,
            )

        # (se mantiene) Si se cargan kilos, que sea > 0
        if row.decomiso_kilos_total is not None and row.decomiso_kilos_total <= 0:
            return ValidateRowResponse(
                batch_id=batch_id,
                row_id=row_id,
                ok=False,
                errors={"decomiso_kilos_total": "Kilos debe ser > 0."},
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
