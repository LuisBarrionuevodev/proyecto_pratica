from __future__ import annotations

from typing import Any, Optional

from app.models import Actuaciones, IniciadorRuta

from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _zfill6_if_digit(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    return s.zfill(6) if s.isdigit() else s


def map_completar_trabajo_cierre_to_aplicar_payload(
    row: CompletarTrabajoCierreCompletoIn,
    *,
    act: Actuaciones,
    ini: IniciadorRuta,
) -> dict[str, Any]:
    """
    Construye el dict canónico para `aplicar_payload_actuacion` en visita **realizada** (Completar trabajo).

    No incluye: orden_trabajo_numero, fecha_actuacion, previas, oficio ni expediente (rechazados en schema).

    Parámetros:
        row: body validado del POST cerrar (fase 3).
        act: actuación actual (fallbacks de domicilio/contrib).
        ini: iniciador (fallback calle/número).

    Retorno:
        Payload parcial para `aplicar_payload_actuacion(..., ejecutar_resolver_previas=False)`.
    """
    payload: dict[str, Any] = {
        "contraproducencia": None,
    }

    if row.tipo_actuacion is not None:
        payload["tipo_actuacion"] = row.tipo_actuacion

    if row.rubro_nombre is not None:
        payload["rubro_nombre"] = _clean_str(row.rubro_nombre)

    calle = row.calle
    numero = row.numero
    if calle is None and act.domicilio:
        calle = act.domicilio.calle
    elif calle is None and ini.domicilio:
        calle = ini.domicilio.calle
    if numero is None and act.domicilio:
        numero = act.domicilio.numero
    elif numero is None and ini.domicilio:
        numero = ini.domicilio.numero

    need_domicilio = (
        row.calle is not None
        or row.numero is not None
        or row.numero_tipo is not None
        or row.rubro_nombre is not None
        or row.doc_nro is not None
        or row.contrib_apellido is not None
        or row.contrib_nombre is not None
    )
    if need_domicilio and (calle or numero or row.numero_tipo):
        payload["domicilio"] = {
            "calle": _clean_str(calle),
            "numero": _clean_str(numero),
            "numero_tipo": row.numero_tipo,
        }

    if row.doc_nro or row.contrib_apellido or row.contrib_nombre:
        payload["contribuyente"] = {
            "doc_nro": _clean_str(row.doc_nro),
            "apellido": _clean_str(row.contrib_apellido),
            "nombre": _clean_str(row.contrib_nombre),
        }

    if row.inspectores is not None:
        payload["inspectores"] = [n for n in row.inspectores if n]

    if row.acta_inspeccion_num:
        payload["acta_inspeccion_num"] = _zfill6_if_digit(_clean_str(row.acta_inspeccion_num))

    motivos_nf = [
        m
        for m in [
            row.notificacion_motivo_1,
            row.notificacion_motivo_2,
            row.notificacion_motivo_3,
        ]
        if m
    ]
    acta_src = _clean_str(row.acta_notificacion_num) if row.acta_notificacion_num else None
    if not acta_src and motivos_nf and getattr(act, "notificacion", None) is not None:
        acta_src = _clean_str(getattr(act.notificacion, "numero_acta", None))
    if acta_src or motivos_nf:
        acta_for_attach = _zfill6_if_digit(acta_src) if acta_src else None
        if motivos_nf and not acta_for_attach:
            raise ValueError(
                "Si cargás motivos de notificación, el número de acta de notificación es obligatorio "
                "(o debe existir ya en la actuación)."
            )
        if acta_for_attach:
            payload["notificacion"] = {
                "acta_num": acta_for_attach,
                "motivos": motivos_nf,
            }

    if row.acta_comprobacion_num:
        payload["comprobacion"] = {
            "acta_num": _zfill6_if_digit(_clean_str(row.acta_comprobacion_num)),
            "motivo": _clean_str(row.comprobacion_motivo),
        }

    if row.acta_clausura_num:
        payload["clausura"] = {"acta_num": _zfill6_if_digit(_clean_str(row.acta_clausura_num))}

    if row.acta_decomiso_num:
        payload["decomiso"] = {
            "acta_num": _zfill6_if_digit(_clean_str(row.acta_decomiso_num)),
            "kilos_total": row.decomiso_kilos_total,
        }

    return payload
