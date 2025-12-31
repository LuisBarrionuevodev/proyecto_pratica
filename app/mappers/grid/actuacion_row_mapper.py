from __future__ import annotations

from typing import Any, Dict, Optional

from app.schemas.grid.actuacion_row_in import ActuacionGridRowIn


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _zfill6_if_digit(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    return s.zfill(6) if s.isdigit() else s


def _tipo_actuacion_value(v: Any) -> Optional[str]:
    """
    Acepta:
    - str ("INSPECCION", "Tipo.INSPECCION", etc.)
    - Enum con .value
    """
    if v is None:
        return None
    if hasattr(v, "value"):
        v = v.value
    s = _clean_str(v)
    if not s:
        return None
    s = s.upper().strip()
    if s.startswith("TIPO."):
        s = s.split(".", 1)[1].strip()
    return s


def map_actuacion_row(row: ActuacionGridRowIn) -> Dict[str, Any]:
    """
    Mapper UI -> Payload limpio para services (sin DB).
    """
    # fecha_as_date() existe en tu schema :contentReference[oaicite:0]{index=0}
    fecha_iso = row.fecha_as_date().isoformat()

    payload: Dict[str, Any] = {
        "id": row.id,
        "orden_trabajo_numero": _zfill6_if_digit(_clean_str(row.orden_trabajo_numero)),
        "fecha_actuacion": fecha_iso,
        "tipo_actuacion": _tipo_actuacion_value(row.tipo_actuacion),
        "contraproducencia": _clean_str(row.contraproducencia),
        "rubro_nombre": _clean_str(row.rubro_nombre),
        "inspectores": [x for x in [row.inspector1, row.inspector2, row.inspector3] if x],
    }

    # Domicilio (tu regla exige calle+numero juntos) :contentReference[oaicite:1]{index=1}
    if row.calle or row.numero:
        payload["domicilio"] = {"calle": _clean_str(row.calle), "numero": _clean_str(row.numero)}

    # Contribuyente (tu regla exige doc_nro si hay apellido/nombre) :contentReference[oaicite:2]{index=2}
    if row.doc_nro or row.contrib_apellido or row.contrib_nombre:
        payload["contribuyente"] = {
            "doc_nro": _clean_str(row.doc_nro),
            "apellido": _clean_str(row.contrib_apellido),
            "nombre": _clean_str(row.contrib_nombre),
        }

    # Actas
    if row.acta_inspeccion_num:
        payload["acta_inspeccion_num"] = _clean_str(row.acta_inspeccion_num)

    if row.acta_notificacion_num:
        payload["acta_notificacion"] = {
            "num": _clean_str(row.acta_notificacion_num),
            "motivos": [m for m in [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3] if m],
            "previa_num": _clean_str(row.notificacion_previa_num),
        }

    if row.acta_comprobacion_num:
        payload["acta_comprobacion"] = {
            "num": _clean_str(row.acta_comprobacion_num),
            "motivo": _clean_str(row.comprobacion_motivo),
            "previa_num": _clean_str(row.comprobacion_previa_num),
        }

    if row.acta_clausura_num:
        payload["acta_clausura_num"] = _clean_str(row.acta_clausura_num)

    if row.acta_decomiso_num:
        payload["acta_decomiso"] = {"num": _clean_str(row.acta_decomiso_num), "kilos_total": row.decomiso_kilos_total}

    # Expediente / Oficio
    if row.expediente_numero or row.expediente_anio is not None:
        payload["expediente"] = {"numero": _clean_str(row.expediente_numero), "anio": row.expediente_anio}

    if row.oficio_numero or row.oficio_anio is not None or row.oficio_causa:
        payload["oficio"] = {"numero": _clean_str(row.oficio_numero), "anio": row.oficio_anio, "causa": _clean_str(row.oficio_causa)}

    return payload
