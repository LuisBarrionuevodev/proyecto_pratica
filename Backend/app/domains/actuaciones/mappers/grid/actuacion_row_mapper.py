from __future__ import annotations

from typing import Any, Dict, Optional

from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _zfill6_if_digit(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    return s.zfill(6) if s.isdigit() else s


def _enum_value(v: Any) -> Optional[str]:
    """
    Si viene Enum -> devuelve .value
    Si viene str -> devuelve str limpia
    """
    if v is None:
        return None
    if hasattr(v, "value"):
        return _clean_str(v.value)
    return _clean_str(v)


def map_actuacion_row(row: ActuacionGridRowIn) -> Dict[str, Any]:
    """
    Mapper **CargarActuacion** → payload canónico para create/update (sin DB).

    No emite `oficio` ni `expediente` en el dict (circuitos Esperando oficio / expediente).
    """
    fecha_iso = row.fecha_as_date().isoformat()

    payload: Dict[str, Any] = {
        "id": row.id,
        "orden_trabajo_numero": _zfill6_if_digit(_clean_str(row.orden_trabajo_numero)),
        "fecha_actuacion": fecha_iso,
        "tipo_actuacion": _enum_value(row.tipo_actuacion),
        "contraproducencia": _enum_value(row.contraproducencia),
        "rubro_nombre": _clean_str(row.rubro_nombre),
        "inspectores": [x for x in [row.inspector1, row.inspector2, row.inspector3] if x],
    }

    # Domicilio
    if row.calle or row.numero:
        payload["domicilio"] = {
            "calle": _clean_str(row.calle),
            "numero": _clean_str(row.numero),
            "numero_tipo": _clean_str(row.numero_tipo),
        }

    # Contribuyente
    if row.doc_nro or row.contrib_apellido or row.contrib_nombre:
        payload["contribuyente"] = {
            "doc_nro": _clean_str(row.doc_nro),
            "apellido": _clean_str(row.contrib_apellido),
            "nombre": _clean_str(row.contrib_nombre),
        }

    # Actas (CANÓNICO según tus helpers attach_*)

    # Inspección: service espera acta_inspeccion_num (string)
    if row.acta_inspeccion_num:
        payload["acta_inspeccion_num"] = _clean_str(row.acta_inspeccion_num)

    # Notificación: service llama attach_notificacion(act, payload.get("notificacion"))
    # helpers esperan data["acta_num"] + motivos + previa_num
    if row.acta_notificacion_num:
        payload["notificacion"] = {
            "acta_num": _clean_str(row.acta_notificacion_num),
            "motivos": [m for m in [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3] if m],
            "previa_num": _clean_str(row.notificacion_previa_num),
        }

    # Comprobación: service llama attach_comprobacion(act, payload.get("comprobacion"))
    # helpers esperan data["acta_num"] y data["motivo"]
    if row.acta_comprobacion_num:
        payload["comprobacion"] = {
            "acta_num": _clean_str(row.acta_comprobacion_num),
            "motivo": _clean_str(row.comprobacion_motivo),
            # previa no va acá porque las previas se resuelven en resolver_previas()
        }

    # Clausura: service llama attach_clausura(act, payload.get("clausura"), crear=True)
    # helpers esperan data["acta_num"]
    if row.acta_clausura_num:
        payload["clausura"] = {"acta_num": _clean_str(row.acta_clausura_num)}

    # Decomiso: service llama attach_decomiso(act, payload.get("decomiso"), crear=True)
    # helpers esperan data["acta_num"] y "kilos_total" (en tu helper veo que lee acta_num)
    if row.acta_decomiso_num:
        payload["decomiso"] = {
            "acta_num": _clean_str(row.acta_decomiso_num),
            "kilos_total": row.decomiso_kilos_total,
        }

    if row.notificacion_previa_num:
        payload["notificacion_previa_num"] = _clean_str(row.notificacion_previa_num)

    if row.comprobacion_previa_num:
        payload["comprobacion_previa_num"] = _clean_str(row.comprobacion_previa_num)
    

    return payload
