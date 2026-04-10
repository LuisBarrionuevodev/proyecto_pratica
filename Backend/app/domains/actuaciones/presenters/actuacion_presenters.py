"""
Presentación de actuaciones hacia grilla / bandejas.

Semántica en `actuacion_to_grid_row`: `expediente_numero` / `expediente_anio` = solo expediente de
**envío de comprobación** (`oficio_id` NULL). `oficio_*` = tabla `oficio` por `comprobacion_id`.
El expediente de respuesta de oficio no se refleja en los campos `expediente_*` del canal actas.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, Optional, List

from app.domains.actuaciones.config.epicollect_evidencias_display import (
    EPICOLLECT_EVIDENCIAS_DISPLAY_ORDER,
    EPICOLLECT_MEDIA_PREFIX,
    label_for_epicollect_suffix,
    suffix_from_epicollect_categoria,
)
from app.domains.actuaciones.config.epicollect_sectors_display import (
    EPICOLLECT_SECTORES_CONDICIONES_FIELDS,
    EPICOLLECT_SECTOR_FIELD_IDS,
)
from app.domains.actuaciones.services.expediente_actas_edit_guard import (
    comprobacion_editable_desde_canal_actas,
    notificacion_editable_desde_canal_actas,
)
from app.models import Actuaciones, Expediente, Oficio


def _enum_to_str(value: Any) -> Optional[str]:
    """
    Convierte un Enum o string a un string limpio para el front.

    Caso normal:
      - Enum -> "INSPECCION" (usa .value si existe)
    Casos defensivos:
      - "Tipo.INSPECCION" -> "INSPECCION"
      - None -> None
    """
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if enum_value:
        return str(enum_value)

    name = getattr(value, "name", None)
    if name:
        return str(name)

    s = str(value).strip()
    if not s:
        return None

    if "." in s:
        s = s.split(".")[-1].strip()

    return s or None


def expediente_envio_por_comprobacion(comprobacion_id: int) -> Optional[Expediente]:
    """
    Expediente de **comprobación** (envío de acta): `oficio_id` NULL.
    No incluye el expediente de respuesta de oficio (ese lleva `oficio_id`).

    Orden estable por `id` para el caso 0..1 operativo con datos legados.
    """
    return (
        Expediente.query.filter_by(comprobacion_id=comprobacion_id, oficio_id=None)
        .order_by(Expediente.id.asc())
        .first()
    )


def _epicollect_value_preview(value: Any, max_len: int = 72) -> str:
    """Texto corto para vista previa de un valor JSON (no se expone el JSON completo)."""
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        s = str(value)
    else:
        s = str(value).strip()
    if not s:
        return "—"
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def _epicollect_sector_value_present(value: Any) -> bool:
    """True si el valor del formulario debe mostrarse en Sectores / condiciones."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _epicollect_detalle_for_grid(act: Actuaciones) -> Dict[str, Any]:
    """
    Campos derivados de `actuacion_epicollect_detalle` para grilla / modal (solo lectura).

    - ``epicollect_sectores_condiciones``: SI/NO y similares con etiquetas humanas (orden fijo).
    - ``epicollect_otros_preview``: resto de claves en ``data``, orden alfabético por field_id.
    - ``epicollect_preview``: compatibilidad — primeras 5 entradas de ``epicollect_otros_preview``.
    """
    det = getattr(act, "epicollect_detalle", None)
    if det is None:
        return {
            "has_epicollect_detalle": False,
            "epicollect_non_media_field_count": 0,
            "epicollect_sectores_condiciones": [],
            "epicollect_otros_preview": [],
            "epicollect_preview": [],
        }
    raw = getattr(det, "payload_non_media", None) or {}
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    keys = sorted(data.keys())

    sectores: List[Dict[str, str]] = []
    for field_id, label in EPICOLLECT_SECTORES_CONDICIONES_FIELDS:
        if field_id not in data:
            continue
        val = data[field_id]
        if not _epicollect_sector_value_present(val):
            continue
        sectores.append(
            {
                "field_id": field_id,
                "label": label,
                "value_preview": _epicollect_value_preview(val),
            }
        )

    otros_keys = [k for k in keys if k not in EPICOLLECT_SECTOR_FIELD_IDS]
    otros_preview: List[Dict[str, str]] = [
        {"field_id": k, "value_preview": _epicollect_value_preview(data[k])} for k in otros_keys
    ]
    preview_cap = otros_preview[:5]

    return {
        "has_epicollect_detalle": True,
        "epicollect_non_media_field_count": len(keys),
        "epicollect_sectores_condiciones": sectores,
        "epicollect_otros_preview": otros_preview,
        "epicollect_preview": preview_cap,
    }


def _epicollect_evidencias_for_grid(act: Actuaciones) -> Dict[str, Any]:
    """
    Agrupa filas ``actuacion_media`` con categoría ``epicollect.*`` para el modal (solo lectura).

    Returns:
        ``epicollect_evidencias_grupos``: lista ordenada con label, count e items (url, orden, mime_type).
        ``epicollect_evidencias_total``: cantidad total de filas epicollect.
    """
    items = getattr(act, "actuacion_media_items", None) or []
    rows = [
        m
        for m in items
        if getattr(m, "categoria", None) and str(m.categoria).startswith(EPICOLLECT_MEDIA_PREFIX)
    ]
    if not rows:
        return {
            "epicollect_evidencias_grupos": [],
            "epicollect_evidencias_total": 0,
        }

    by_cat: dict[str, list[Any]] = defaultdict(list)
    for m in rows:
        by_cat[str(m.categoria)].append(m)

    for cat in by_cat:
        by_cat[cat].sort(key=lambda x: (int(x.orden or 0), int(x.id)))

    order_rank = {s: i for i, s in enumerate(EPICOLLECT_EVIDENCIAS_DISPLAY_ORDER)}

    def group_sort_key(categoria: str) -> tuple[int, str]:
        suf = suffix_from_epicollect_categoria(categoria) or ""
        rank = order_rank.get(suf, 10_000)
        label = label_for_epicollect_suffix(suf)
        return (rank, label.lower())

    grupos: List[Dict[str, Any]] = []
    for categoria in sorted(by_cat.keys(), key=group_sort_key):
        lst = by_cat[categoria]
        suf = suffix_from_epicollect_categoria(categoria) or ""
        grupos.append(
            {
                "categoria": categoria,
                "label": label_for_epicollect_suffix(suf),
                "count": len(lst),
                "items": [
                    {
                        "url": (str(r.url)[:2048] if r.url else ""),
                        "orden": int(r.orden or 0),
                        "mime_type": r.mime_type,
                    }
                    for r in lst
                ],
            }
        )

    return {
        "epicollect_evidencias_grupos": grupos,
        "epicollect_evidencias_total": len(rows),
    }


def oficio_por_comprobacion(comprobacion_id: int) -> Optional[Oficio]:
    """
    Oficio asociado a la comprobación (tabla `oficio`), sin inferirlo desde expedientes.
    Orden estable por `id`; ignora filas soft-deleted.
    """
    return (
        Oficio.query.filter_by(comprobacion_id=comprobacion_id)
        .filter(Oficio.deleted_at.is_(None))
        .order_by(Oficio.id.asc())
        .first()
    )


def actuacion_to_grid_row(act: Actuaciones) -> Dict[str, Any]:
    """
    Convierte una Actuación (con relaciones) al formato plano
    que espera Material React Table.

    IMPORTANTE:
    - fecha_actuacion se entrega como YYYY-MM-DD para input type="date"
    - enum se entrega como string limpio
    - `expediente_*` refleja solo el expediente de comprobación (envío), nunca el de respuesta de oficio.
    - `oficio_*` sale del registro `Oficio` de la comprobación, no desde el expediente colateral.
    """

    # -------------------------
    # OT
    # -------------------------
    ot_num: Optional[str] = None
    if getattr(act, "orden_trabajo", None):
        ot_num = (
            getattr(act.orden_trabajo, "numero_acta", None)
            or getattr(act.orden_trabajo, "numero", None)
        )

    # -------------------------
    # Fecha para el grid (input date)
    # -------------------------
    fecha_iso: Optional[str] = act.fecha.isoformat() if act.fecha else None

    # -------------------------
    # Rubro / domicilio / contribuyente
    # -------------------------
    rubro_nombre: Optional[str] = None
    calle: Optional[str] = None
    numero: Optional[str] = None
    calle_normalizada: Optional[str] = None
    calle_estado: Optional[str] = None
    calle_score: Optional[float] = None
    calle_catalogo_id: Optional[int] = None
    numero_tipo: Optional[str] = None
    esquina_raw: Optional[str] = None
    esquina_normalizada: Optional[str] = None
    esquina_catalogo_id: Optional[int] = None
    esquina_status: Optional[str] = None
    esquina_score: Optional[float] = None
    domicilio_id: Optional[int] = None

    doc_nro: Optional[str] = None
    contrib_apellido: Optional[str] = None
    contrib_nombre: Optional[str] = None
    razon_social: Optional[str] = None

    dom = getattr(act, "domicilio", None)
    if dom:
        domicilio_id = getattr(dom, "id", None)
        calle = getattr(dom, "calle", None)
        numero = getattr(dom, "numero", None)
        calle_normalizada = getattr(dom, "calle_normalizada", None)
        calle_estado = getattr(dom, "calle_norm_status", None)
        calle_score = getattr(dom, "calle_norm_score", None)
        calle_catalogo_id = getattr(dom, "calle_catalogo_id", None)
        numero_tipo = getattr(dom, "numero_tipo", None)
        esquina_raw = getattr(dom, "esquina_raw", None)
        esquina_normalizada = getattr(dom, "esquina_normalizada", None)
        esquina_catalogo_id = getattr(dom, "esquina_catalogo_id", None)
        esquina_status = getattr(dom, "esquina_norm_status", None)
        esquina_score = getattr(dom, "esquina_norm_score", None)

        rub = getattr(dom, "rubro", None)
        if rub:
            rubro_nombre = getattr(rub, "nombre", None)

        contrib = getattr(dom, "contribuyente", None)
        if contrib:
            doc_nro = getattr(contrib, "documento", None) or getattr(contrib, "doc_nro", None)
            contrib_apellido = getattr(contrib, "apellido", None)
            contrib_nombre = getattr(contrib, "nombre", None)
            razon_social = getattr(contrib, "razon_social", None)

    # -------------------------
    # Inspectores (max 3)
    # -------------------------
    inspector1 = None
    inspector2 = None
    inspector3 = None

    insp_list: List[Any] = getattr(act, "inspector", None) or []
    if insp_list:
        insp_list = sorted(insp_list, key=lambda x: getattr(x, "id", 0))
    nombres: List[str] = []
    if insp_list:
        for i in insp_list:
            n = getattr(i, "nombre", None)
            if n:
                nombres.append(str(n).strip())
    inspectores_texto = ", ".join(nombres) if nombres else None

    if len(nombres) > 0:
        inspector1 = nombres[0]
    if len(nombres) > 1:
        inspector2 = nombres[1]
    if len(nombres) > 2:
        inspector3 = nombres[2]

    # -------------------------
    # Actas principales
    # -------------------------
    inspeccion = getattr(act, "inspeccion", None)
    clausura = getattr(act, "clausura", None)
    decomiso = getattr(act, "decomiso", None)

    acta_inspeccion_num = getattr(inspeccion, "numero_acta", None) if inspeccion else None
    acta_clausura_num = getattr(clausura, "numero_acta", None) if clausura else None
    acta_decomiso_num = getattr(decomiso, "numero_acta", None) if decomiso else None
    decomiso_kilos_total = getattr(decomiso, "cantidad", None) if decomiso else None

    # -------------------------
    # Notificación / comprobación
    # -------------------------
    noti = getattr(act, "notificacion", None)
    comp = getattr(act, "comprobacion", None)

    acta_notificacion_num = getattr(noti, "numero_acta", None) if noti else None
    acta_comprobacion_num = getattr(comp, "numero_acta", None) if comp else None
    comprobacion_motivo = getattr(comp, "motivo", None) if comp else None

    # Motivos de notificación (M2M)
    # Tu modelo real usa "motivo", pero dejamos compatibilidad con "motivos"
    motivos: List[str] = []
    if noti:
        rel = getattr(noti, "motivo", None) or getattr(noti, "motivos", None) or []
        for m in rel:
            mn = getattr(m, "nombre", None)
            if mn:
                motivos.append(mn)

    notificacion_motivo_1 = motivos[0] if len(motivos) > 0 else None
    notificacion_motivo_2 = motivos[1] if len(motivos) > 1 else None
    notificacion_motivo_3 = motivos[2] if len(motivos) > 2 else None

    # -------------------------
    # Previas (según tipo)
    # -------------------------
    tipo_val = _enum_to_str(getattr(act, "tipo", None))
    notificacion_previa_num = None
    comprobacion_previa_num = None
    if tipo_val == "REINSPECCION" and acta_notificacion_num:
        notificacion_previa_num = acta_notificacion_num
    if tipo_val in (
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
    ) and acta_comprobacion_num:
        comprobacion_previa_num = acta_comprobacion_num

    # -------------------------
    # Expediente de comprobación / Oficio (contextos separados)
    # -------------------------
    expediente_numero = None
    expediente_anio = None
    oficio_numero = None
    oficio_anio = None
    oficio_causa = None

    cid = getattr(act, "comprobacion_id", None)
    if cid:
        exp_envio = expediente_envio_por_comprobacion(cid)
        if exp_envio:
            expediente_numero = getattr(exp_envio, "numero_expediente", None)
            expediente_anio = getattr(exp_envio, "anio", None)

        of = oficio_por_comprobacion(cid)
        if of:
            oficio_numero = getattr(of, "numero_oficio", None)
            oficio_anio = getattr(of, "anio", None)
            oficio_causa = getattr(of, "causa", None)

    
    calle_mostrar = calle_normalizada if calle_estado == "OK" and calle_normalizada else calle
    numero_mostrar = (
        f"ESQ: {esquina_normalizada}"
        if numero_tipo == "ESQUINA" and esquina_status == "OK" and esquina_normalizada
        else numero
    )
    calle_sugerida = calle_normalizada if calle_normalizada else None

    _raw_nombre_local = getattr(act, "nombre_local", None)
    nombre_local_val = (str(_raw_nombre_local).strip() or None) if _raw_nombre_local is not None else None

    return {
        "id": act.id,
        "orden_trabajo_numero": ot_num,
        "fecha_actuacion": fecha_iso,

        "rubro_nombre": rubro_nombre,

        "inspector1": inspector1,
        "inspector2": inspector2,
        "inspector3": inspector3,
        "inspectores_texto": inspectores_texto,

        "calle": calle,
        "numero": numero,
        "numero_tipo": numero_tipo,
        "numero_mostrar": numero_mostrar,
        "esquina_raw": esquina_raw,
        "esquina_normalizada": esquina_normalizada,
        "esquina_catalogo_id": esquina_catalogo_id,
        "esquina_status": esquina_status,
        "esquina_score": esquina_score,
        "domicilio_id": domicilio_id,
        "calle_normalizada": calle_normalizada,
        "calle_estado": calle_estado,
        "calle_score": calle_score,
        "calle_catalogo_id": calle_catalogo_id,
        "calle_sugerida": calle_sugerida,
        "calle_mostrar": calle_mostrar,

        "tipo_actuacion": _enum_to_str(getattr(act, "tipo", None)),
        "contraproducencia": _enum_to_str(getattr(act, "contraproducencia", None)),
        "resultado_cumplimiento_oficio": _enum_to_str(getattr(act, "resultado_cumplimiento_oficio", None)),

        "doc_nro": doc_nro,
        "contrib_apellido": contrib_apellido,
        "contrib_nombre": contrib_nombre,
        "razon_social": razon_social,
        "ec5_uuid": getattr(act, "ec5_uuid", None),

        "nombre_local": nombre_local_val,

        "acta_inspeccion_num": acta_inspeccion_num,

        "acta_notificacion_num": acta_notificacion_num,
        "notificacion_motivo_1": notificacion_motivo_1,
        "notificacion_motivo_2": notificacion_motivo_2,
        "notificacion_motivo_3": notificacion_motivo_3,

        "acta_comprobacion_num": acta_comprobacion_num,
        "comprobacion_motivo": comprobacion_motivo,

        "acta_clausura_num": acta_clausura_num,

        "acta_decomiso_num": acta_decomiso_num,
        "decomiso_kilos_total": decomiso_kilos_total,

        "expediente_numero": expediente_numero,
        "expediente_anio": expediente_anio,

        "oficio_numero": oficio_numero,
        "oficio_anio": oficio_anio,
        "oficio_causa": oficio_causa,

        "notificacion_previa_num": notificacion_previa_num,
        "comprobacion_previa_num": comprobacion_previa_num,

        "notificacion_editable": notificacion_editable_desde_canal_actas(getattr(act, "notificacion_id", None)),
        "comprobacion_editable": comprobacion_editable_desde_canal_actas(getattr(act, "comprobacion_id", None)),
        **_epicollect_detalle_for_grid(act),
        **_epicollect_evidencias_for_grid(act),
    }


def _infer_expediente_source_type(act: Actuaciones) -> str:
    """
    Infiere la rama administrativa para expediente desde estado DB.

    Regla determinística:
    - Si existe comprobación, domina COMPROBACION.
    - Si no, y existe notificación, NOTIFICACION.
    - Si no hay ninguna, UNKNOWN.
    """
    if getattr(act, "comprobacion_id", None):
        return "COMPROBACION"
    if getattr(act, "notificacion_id", None):
        return "NOTIFICACION"
    return "UNKNOWN"


def _dias_restantes_desde_vencimiento(fecha_vencimiento: date | None) -> int | None:
    """
    Días hasta el vencimiento operativo de la notificación (`Notificacion.fecha_vencimiento`).
    Si ya venció: 0 (criterio conservador). Sin fecha: None.
    """
    if fecha_vencimiento is None:
        return None
    delta = (fecha_vencimiento - date.today()).days
    return max(0, delta)


def actuacion_to_pendiente_expediente_row(
    act: Actuaciones,
    *,
    plazos_por_notificacion: dict[int, int] | None = None,
    fecha_vencimiento_por_notificacion: dict[int, date | None] | None = None,
) -> Dict[str, Any]:
    """
    DTO compacto para la bandeja unificada de pendientes de expediente.

    Incluye `source_type` explícito y mantiene campos mínimos para UI administrativa.
    Rama NOTIFICACION: `dias_restantes` y `plazos_otorgados` cuando se pasan mapas batch
    (`build_notificacion_expediente_bandeja_metrics`). Rama COMPROBACION: ambos None.
    """
    full = actuacion_to_grid_row(act)
    source_type = _infer_expediente_source_type(act)
    full["source_type"] = source_type

    plazos_map = plazos_por_notificacion or {}
    venc_map = fecha_vencimiento_por_notificacion or {}

    if source_type == "NOTIFICACION" and act.notificacion_id is not None:
        nid = int(act.notificacion_id)
        full["plazos_otorgados"] = int(plazos_map.get(nid, 0))
        full["dias_restantes"] = _dias_restantes_desde_vencimiento(venc_map.get(nid))
    else:
        full["plazos_otorgados"] = None
        full["dias_restantes"] = None

    return full


def actuacion_to_pendiente_domicilio_row(act: Actuaciones) -> Dict[str, Any]:
    """
    Convierte una Actuación a un formato mínimo para pendientes de domicilio.

    Retorna solo las columnas necesarias para la UI de pendientes.
    """
    ot_num: Optional[str] = None
    if getattr(act, "orden_trabajo", None):
        ot_num = (
            getattr(act.orden_trabajo, "numero_acta", None)
            or getattr(act.orden_trabajo, "numero", None)
        )

    fecha_iso: Optional[str] = act.fecha.isoformat() if act.fecha else None

    dom = getattr(act, "domicilio", None)
    rubro_nombre: Optional[str] = None
    calle: Optional[str] = None
    numero: Optional[str] = None
    numero_tipo: Optional[str] = None
    calle_normalizada: Optional[str] = None
    calle_catalogo_id: Optional[int] = None
    esquina_normalizada: Optional[str] = None
    esquina_catalogo_id: Optional[int] = None
    esquina_status: Optional[str] = None
    domicilio_id: Optional[int] = None

    if dom:
        domicilio_id = getattr(dom, "id", None)
        calle = getattr(dom, "calle", None)
        numero = getattr(dom, "numero", None)
        numero_tipo = getattr(dom, "numero_tipo", None)
        calle_normalizada = getattr(dom, "calle_normalizada", None)
        calle_catalogo_id = getattr(dom, "calle_catalogo_id", None)
        esquina_normalizada = getattr(dom, "esquina_normalizada", None)
        esquina_catalogo_id = getattr(dom, "esquina_catalogo_id", None)
        esquina_status = getattr(dom, "esquina_norm_status", None)
        rub = getattr(dom, "rubro", None)
        if rub:
            rubro_nombre = getattr(rub, "nombre", None)

    return {
        "id": act.id,
        "fecha_actuacion": fecha_iso,
        "orden_trabajo_numero": ot_num,
        "tipo_actuacion": _enum_to_str(getattr(act, "tipo", None)),
        "contraproducencia": _enum_to_str(getattr(act, "contraproducencia", None)),
        "rubro_nombre": rubro_nombre,
        "calle_ingresada": calle,
        "calle": calle,
        "calle_normalizada": calle_normalizada,
        "calle_catalogo_id": calle_catalogo_id,
        "numero": numero,
        "numero_tipo": numero_tipo,
        "esquina_normalizada": esquina_normalizada,
        "esquina_catalogo_id": esquina_catalogo_id,
        "esquina_status": esquina_status,
        "domicilio_id": domicilio_id,
    }


def actuacion_to_pendiente_oficio_row(act: Actuaciones) -> Dict[str, Any]:
    """
    Convierte una actuación a una fila compacta para la bandeja "Esperando oficio".

    Incluye contexto operativo mínimo y el expediente original de comprobación.
    """
    full = actuacion_to_grid_row(act)
    exp_original = None
    if getattr(act, "comprobacion_id", None):
        exp_original = expediente_envio_por_comprobacion(act.comprobacion_id)

    return {
        "id": full.get("id"),
        "fecha_actuacion": full.get("fecha_actuacion"),
        "orden_trabajo_numero": full.get("orden_trabajo_numero"),
        "acta_comprobacion_num": full.get("acta_comprobacion_num"),
        "comprobacion_motivo": full.get("comprobacion_motivo"),
        "contrib_apellido": full.get("contrib_apellido"),
        "contrib_nombre": full.get("contrib_nombre"),
        "calle": full.get("calle"),
        "numero": full.get("numero"),
        "rubro_nombre": full.get("rubro_nombre"),
        "expediente_original_id": getattr(exp_original, "id", None),
        "expediente_original_numero": getattr(exp_original, "numero_expediente", None),
        "expediente_original_anio": getattr(exp_original, "anio", None),
    }
