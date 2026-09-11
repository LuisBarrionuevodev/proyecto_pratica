from __future__ import annotations

from typing import Any, Iterable, Optional

from app.database import db
from app.models import Actuaciones, ActaInspeccionItem, Inspeccion, ItemActaInspeccion
from app.utils.actas import acta_6
from .uniqueness import (
    asegurar_acta_libre_para_actuacion,
    asegurar_acta_no_usada_en_otra,
)

_ESTADOS_VALIDOS = frozenset({"BIEN", "OBSERVADO"})


def _normalizar_items_estado(raw_items: Any) -> list[dict[str, Any]]:
    """Normaliza payload V2: item_id único + estado BIEN/OBSERVADO."""
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise ValueError("items_acta_inspeccion debe ser una lista.")
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("items_acta_inspeccion debe contener objetos con item_id y estado.")
        try:
            item_id = int(raw.get("item_id"))
        except (TypeError, ValueError):
            raise ValueError("item_id debe ser un entero positivo.") from None
        if item_id <= 0:
            raise ValueError("item_id debe ser un entero positivo.")
        if item_id in seen:
            raise ValueError("items_acta_inspeccion no puede repetir item_id.")
        estado = str(raw.get("estado") or "").strip().upper()
        if estado not in _ESTADOS_VALIDOS:
            raise ValueError("estado debe ser BIEN u OBSERVADO.")
        seen.add(item_id)
        out.append({"item_id": item_id, "estado": estado})
    return out


def _validar_items_catalogo(
    inspeccion: Inspeccion,
    requested: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Valida IDs contra catálogo (activo-only para altas nuevas)."""
    if not requested:
        return []

    actuales = {int(j.item_acta_inspeccion_id) for j in (inspeccion.checklist_items or [])}
    item_ids = [int(r["item_id"]) for r in requested]
    rows = ItemActaInspeccion.query.filter(ItemActaInspeccion.id.in_(item_ids)).all()
    by_id = {int(r.id): r for r in rows}
    faltantes = [i for i in item_ids if i not in by_id]
    if faltantes:
        raise ValueError(
            f"Ítem(s) de inspección inválido(s): {', '.join(str(x) for x in faltantes)}."
        )

    for item_id in item_ids:
        row = by_id[item_id]
        if not row.activo and item_id not in actuales:
            raise ValueError(
                f"El ítem de inspección '{row.nombre}' no está activo y no puede agregarse."
            )

    return requested


def _sync_checklist_items(inspeccion: Inspeccion, requested: list[dict[str, Any]]) -> None:
    """Replace exacto de junctions con estado (diff/replace idempotente)."""
    by_item_id = {int(r["item_id"]): str(r["estado"]) for r in requested}
    current = {
        int(j.item_acta_inspeccion_id): j for j in list(inspeccion.checklist_items or [])
    }
    requested_ids = set(by_item_id.keys())

    for item_id, junction in list(current.items()):
        if item_id not in requested_ids:
            db.session.delete(junction)

    for item_id, estado in by_item_id.items():
        if item_id in current:
            junction = current[item_id]
            if junction.estado != estado:
                junction.estado = estado
                db.session.add(junction)
        else:
            db.session.add(
                ActaInspeccionItem(
                    acta_inspeccion_id=int(inspeccion.id),
                    item_acta_inspeccion_id=item_id,
                    estado=estado,
                )
            )


def aplicar_inspeccion_checklist_desde_payload(actuacion: Actuaciones, payload: dict[str, Any]) -> None:
    """
    Aplica checklist V2 si viene explícito en el payload canónico (misma transacción attach).

    Reglas:
    - Ausencia de clave ``items_acta_inspeccion`` → no modifica.
    - ``items_acta_inspeccion=[]`` limpia todas las junctions.
    - Requiere ``Inspeccion`` existente; si no hay, ``ValueError``.
    - ``items_acta_inspeccion_ids`` (V1) rechazado explícitamente.

    Errores:
        ValueError: validación de negocio o inspección ausente.
    """
    if "items_acta_inspeccion_ids" in payload:
        raise ValueError(
            "items_acta_inspeccion_ids ya no es válido. Use items_acta_inspeccion con estado BIEN u OBSERVADO."
        )

    if "items_acta_inspeccion" not in payload:
        return

    inspeccion = Inspeccion.query.filter_by(actuacion_id=actuacion.id).first()
    if inspeccion is None:
        raise ValueError(
            "No hay acta de inspección para guardar condiciones verificadas."
        )

    requested = _normalizar_items_estado(payload.get("items_acta_inspeccion"))
    validated = _validar_items_catalogo(inspeccion, requested)
    _sync_checklist_items(inspeccion, validated)
    db.session.add(inspeccion)


def items_acta_inspeccion_read_dtos(inspeccion: Inspeccion | None) -> list[dict[str, Any]]:
    """Serializa ítems asociados a una inspección con estado para lectura API."""
    if inspeccion is None:
        return []
    junctions = list(inspeccion.checklist_items or [])
    junctions.sort(
        key=lambda j: (
            int(j.item.orden) if j.item else 0,
            int(j.item_acta_inspeccion_id),
        )
    )
    out: list[dict[str, Any]] = []
    for j in junctions:
        item = j.item
        if item is None:
            continue
        out.append(
            {
                "id": int(item.id),
                "codigo": item.codigo,
                "nombre": item.nombre,
                "estado": str(j.estado),
            }
        )
    return out


def attach_inspeccion(actuacion: Actuaciones, acta_num: Optional[Any], crear: bool = True) -> None:
    """
    Adjunta (upsert) el acta de Inspección a una Actuación.

    Comportamiento (sin cambiar queries):
    - Si `acta_num` es falsy o al normalizar con `acta_6` queda vacío -> no hace nada.
    - Determina `anio` y `mes` desde la propia `actuacion`.
    - Valida unicidad del acta:
        - En creación (`crear=True`): el `(numero_acta, anio)` no puede estar asociado a otra actuación.
        - En update (`crear=False`): permite si está libre (`actuacion_id` None) o ya asociada a esta actuación.
    - Si ya existe una `Inspeccion` con `actuacion_id == actuacion.id`, actualiza sus campos.
    - Si no existe por `actuacion_id`, busca por `(numero_acta, anio)`:
        - Si existe, la re-asocia a la actuación.
        - Si no existe, crea una nueva.

    Args:
        actuacion: Actuación destino (debe tener `id`, `anio`, `mes`).
        acta_num: número de acta (cualquier tipo, se normaliza con `acta_6`).
        crear: si es `True`, aplica reglas de unicidad de creación; si es `False`, reglas de update.

    Returns:
        None

    Raises:
        ValueError: si el acta ya está asociada a otra actuación (según las reglas de unicidad).
    """
    if not acta_num:
        return

    numero = acta_6(acta_num)
    if not numero:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Inspeccion, numero, anio, actuacion.id)
    else:
        asegurar_acta_libre_para_actuacion(Inspeccion, numero, anio, actuacion.id)

    actual = Inspeccion.query.filter_by(actuacion_id=actuacion.id).first()
    if actual:
        actual.numero_acta = numero
        actual.anio = anio
        actual.mes = mes
        db.session.add(actual)
        return

    ins = Inspeccion.query.filter_by(numero_acta=numero, anio=anio).first()
    if ins:
        ins.actuacion_id = actuacion.id
        db.session.add(ins)
        return

    ins = Inspeccion(numero_acta=numero, anio=anio, mes=mes, actuacion_id=actuacion.id)
    db.session.add(ins)
