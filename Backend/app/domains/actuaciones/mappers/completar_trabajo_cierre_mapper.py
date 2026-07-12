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


def _contrib_payload_from_act(act: Actuaciones) -> Optional[dict[str, Any]]:
    """
    Snapshot mínimo del contribuyente ya vinculado a la actuación (para `resolve_contribuyente`).

    Se usa cuando el cierre ajusta domicilio/rubro pero el body no repite titular: sin esto,
    `aplicar_payload_actuacion` exige contrib al mutar domicilio.
    """
    dom = getattr(act, "domicilio", None)
    if dom is None:
        return None
    c = getattr(dom, "contribuyente", None)
    if c is None:
        return None
    doc = getattr(c, "documento", None)
    if not doc or not str(doc).strip():
        return None
    return {
        "doc_nro": _clean_str(str(doc).strip()),
        "apellido": _clean_str(getattr(c, "apellido", None)),
        "nombre": _clean_str(getattr(c, "nombre", None)),
        "razon_social": _clean_str(getattr(c, "razon_social", None)),
    }


def _rubro_nombre_from_act(act: Actuaciones) -> Optional[str]:
    dom = getattr(act, "domicilio", None)
    if dom is None:
        return None
    rub = getattr(dom, "rubro", None)
    if rub is None:
        return None
    return _clean_str(getattr(rub, "nombre", None))


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

    contrib_from_row: Optional[dict[str, Any]] = None
    if row.doc_nro or row.contrib_apellido or row.contrib_nombre or row.razon_social:
        contrib_from_row = {
            "doc_nro": _clean_str(row.doc_nro),
            "apellido": _clean_str(row.contrib_apellido),
            "nombre": _clean_str(row.contrib_nombre),
            "razon_social": _clean_str(row.razon_social),
        }

    calle = row.calle
    numero = row.numero
    # No mezclar calle del domicilio original si el body trae solo número (PR7.12c).
    if row.numero is not None and row.calle is None:
        calle = None
    ref_dom = act.domicilio or (ini.domicilio if ini else None)
    corrige_esquina_sin_numero = (
        row.calle is not None
        and row.numero is None
        and (row.numero_tipo or "").strip().upper() == "NUMERO"
        and ref_dom is not None
        and (getattr(ref_dom, "numero_tipo", None) or "").strip().upper() == "ESQUINA"
    )
    if calle is None and numero is None:
        if act.domicilio:
            calle = act.domicilio.calle
        elif ini.domicilio:
            calle = ini.domicilio.calle
    if numero is None and not corrige_esquina_sin_numero:
        if act.domicilio:
            numero = act.domicilio.numero
        elif ini.domicilio:
            numero = ini.domicilio.numero

    need_domicilio = (
        row.calle is not None
        or row.numero is not None
        or row.numero_tipo is not None
        or row.rubro_nombre is not None
        or row.doc_nro is not None
        or row.contrib_apellido is not None
        or row.contrib_nombre is not None
        or row.razon_social is not None
    )
    if need_domicilio:
        if contrib_from_row:
            payload["contribuyente"] = contrib_from_row
        else:
            fb_contrib = _contrib_payload_from_act(act)
            if fb_contrib and fb_contrib.get("doc_nro"):
                payload["contribuyente"] = fb_contrib

        eff_rubro = _clean_str(row.rubro_nombre) if row.rubro_nombre is not None else None
        if not eff_rubro:
            eff_rubro = _rubro_nombre_from_act(act)
        if eff_rubro:
            payload["rubro_nombre"] = eff_rubro

        if _clean_str(calle) and _clean_str(numero):
            domicilio_payload: dict[str, Any] = {
                "calle": _clean_str(calle),
                "numero": _clean_str(numero),
            }
            if row.numero_tipo is not None:
                domicilio_payload["numero_tipo"] = row.numero_tipo
            payload["domicilio"] = domicilio_payload
    elif contrib_from_row:
        payload["contribuyente"] = contrib_from_row

    if row.inspectores is not None:
        payload["inspectores"] = [n for n in row.inspectores if n]

    if row.acta_inspeccion_num:
        payload["acta_inspeccion_num"] = _zfill6_if_digit(_clean_str(row.acta_inspeccion_num))

    motivos_nf: list[str] = []
    _seen_m: set[str] = set()
    for raw in (
        row.notificacion_motivo_1,
        row.notificacion_motivo_2,
        row.notificacion_motivo_3,
    ):
        if not raw:
            continue
        t = str(raw).strip()
        if not t or t in _seen_m:
            continue
        _seen_m.add(t)
        motivos_nf.append(t)
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


def map_no_permite_inspeccion_actas_to_aplicar_payload(
    row: CompletarTrabajoCierreCompletoIn,
) -> dict[str, Any]:
    """
    Solo actas permitidas con contraproducencia «NO PERMITE INSPECCION»: comprobación y clausura opcional.

    Debe llamarse tras validar el schema (acta + motivo de comprobación obligatorios).
    """
    payload: dict[str, Any] = {}
    if row.acta_comprobacion_num:
        payload["comprobacion"] = {
            "acta_num": _zfill6_if_digit(_clean_str(row.acta_comprobacion_num)),
            "motivo": _clean_str(row.comprobacion_motivo),
        }
    if row.acta_clausura_num:
        payload["clausura"] = {"acta_num": _zfill6_if_digit(_clean_str(row.acta_clausura_num))}
    return payload
