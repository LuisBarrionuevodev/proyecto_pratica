from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import ValidationError

from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.grid.schemas.batch import ValidateRowResponse
from app.domains.grid.services.row_normalizer import normalize_row_keys, reverse_map_errors
from app.domains.grid.services.registry import get_handler
from app.domains.relevamientos.services.relevamiento_unicidad_service import (
    RELEVAMIENTO_UNICIDAD_UBICACION_MSG,
    count_active_relevamientos_por_calle_numero,
)
from app.domains.geolocalizacion.normalizacion_calles.services.numero_esquina_detector import (
    detect_numero_o_esquina,
)


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


def _relevamiento_fila_es_esquina(row: Any) -> bool:
    """
    True si el domicilio debe tratarse como esquina para unicidad (misma lógica que el alta:
    override explícito o detección por texto de número).
    """
    if row.numero_tipo == "ESQUINA":
        return True
    if row.numero_tipo in ("NUMERO", "OTRO"):
        return False
    return detect_numero_o_esquina(row.numero) == "ESQUINA"


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
        elif kind == "relevamientos":
            from app.domains.grid.services.relevamiento_dup_key import build_relevamiento_location_key

            loc_key = build_relevamiento_location_key(row.calle, row.numero)
            is_esquina = _relevamiento_fila_es_esquina(row)
            other_row = self.store.upsert_relevamiento_ubicacion(
                batch_id=batch_id,
                row_id=row_id,
                location_key=loc_key,
                is_esquina=is_esquina,
            )
            if other_row:
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors={
                        "_row": (
                            "Duplicado en el lote: la misma calle y altura ya está cargada "
                            f"(fila {other_row}). En esquinas se permiten varias filas con el mismo cruce."
                        )
                    },
                    normalized=None,
                )
            if not is_esquina and count_active_relevamientos_por_calle_numero(
                row.calle,
                row.numero,
                exclude_relevamiento_id=row.id,
            ) > 0:
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors={"_row": RELEVAMIENTO_UNICIDAD_UBICACION_MSG},
                    normalized=None,
                )

        return ValidateRowResponse(
            batch_id=batch_id,
            row_id=row_id,
            ok=True,
            errors={},
            normalized=payload,
        )
