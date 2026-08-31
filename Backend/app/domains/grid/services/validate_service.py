from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import ValidationError

from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.grid.schemas.batch import ValidateRowResponse
from app.domains.grid.services.row_normalizer import normalize_row_keys, reverse_map_errors
from app.domains.grid.services.registry import get_handler
from app.domains.relevamientos.services.relevamiento_unicidad_service import (
    RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG,
    RELEVAMIENTO_UNICIDAD_NUMERO_MSG,
    count_active_relevamientos_por_calle_numero,
    existe_relevamiento_activo_mismo_establecimiento_esquina,
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

    def _fecha_relevamiento_efectiva_lote(self, batch_id: UUID, row_fecha: Optional[date]) -> date:
        """
        Fecha efectiva para validación/alta de relevamientos en lote (PR9.4).

        - Si la fila trae fecha (payload legacy), se respeta.
        - Si no, todas las filas del mismo batch comparten ``fecha_relevamiento_default``.
        """
        if row_fecha is not None:
            return row_fecha
        st = self.store.get(batch_id)
        if st.fecha_relevamiento_default is None:
            st.fecha_relevamiento_default = date.today()
        return st.fecha_relevamiento_default

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

        validation_ctx: dict[str, object] = {}
        if kind == "actuaciones" and row_internal.get("id") is not None:
            from app.domains.actuaciones.utils.circuito_operativo import (
                build_actuacion_grid_validation_context,
            )

            validation_ctx = build_actuacion_grid_validation_context(int(row_internal["id"]))

        # 1) Pydantic (fase 1)
        try:
            row = handler.schema.model_validate(row_internal, context=validation_ctx or None)
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

        if kind == "relevamientos":
            fecha_efectiva = self._fecha_relevamiento_efectiva_lote(batch_id, row.fecha)
            updates: dict[str, Any] = {"fecha": fecha_efectiva}
            if not row.numero_tipo:
                detected = detect_numero_o_esquina(row.numero)
                if detected in ("NUMERO", "ESQUINA", "OTRO"):
                    updates["numero_tipo"] = detected
            row = row.model_copy(update=updates)

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

            if (
                not validation_ctx.get("es_reinspeccion_oficio")
                and tipo_norm in (
                    "RATIFICACION DE CLAUSURA",
                    "RATIFICACION DE DECOMISO",
                    "VERIFICAR E INFORMAR",
                )
                and not row.comprobacion_previa_num
            ):
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
            from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
            from app.domains.grid.services.relevamiento_dup_key import (
                build_relevamiento_establishment_key,
                build_relevamiento_location_key,
            )

            loc_key = build_relevamiento_location_key(row.calle, row.numero)
            is_esquina = _relevamiento_fila_es_esquina(row)
            rubro_obj = get_rubro_o_falla(row.rubro)
            rubro_id = rubro_obj.id
            mes = row.fecha.month
            anio = row.fecha.year
            establishment_key = build_relevamiento_establishment_key(
                row.calle,
                row.numero,
                mes=mes,
                anio=anio,
                rubro_id=rubro_id,
                nombre_fantasia=row.nombre_fantasia,
                angulo_esquina=row.angulo_esquina if is_esquina else None,
                es_esquina=is_esquina,
            )
            other_row = self.store.upsert_relevamiento_ubicacion(
                batch_id=batch_id,
                row_id=row_id,
                location_key=loc_key,
                is_esquina=is_esquina,
                establishment_key=establishment_key,
            )
            if other_row:
                msg = (
                    RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG
                    if is_esquina
                    else RELEVAMIENTO_UNICIDAD_NUMERO_MSG
                )
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors={"_row": msg},
                    normalized=None,
                )
            if is_esquina and existe_relevamiento_activo_mismo_establecimiento_esquina(
                calle=row.calle,
                numero=row.numero,
                mes=mes,
                anio=anio,
                rubro_id=rubro_id,
                nombre_fantasia=row.nombre_fantasia,
                angulo_esquina=row.angulo_esquina,
                exclude_relevamiento_id=row.id,
            ):
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors={"_row": RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG},
                    normalized=None,
                )
            if not is_esquina and count_active_relevamientos_por_calle_numero(
                row.calle,
                row.numero,
                mes=mes,
                anio=anio,
                rubro_id=rubro_id,
                nombre_fantasia=row.nombre_fantasia,
                exclude_relevamiento_id=row.id,
            ) > 0:
                return ValidateRowResponse(
                    batch_id=batch_id,
                    row_id=row_id,
                    ok=False,
                    errors={"_row": RELEVAMIENTO_UNICIDAD_NUMERO_MSG},
                    normalized=None,
                )

        return ValidateRowResponse(
            batch_id=batch_id,
            row_id=row_id,
            ok=True,
            errors={},
            normalized=payload,
        )
