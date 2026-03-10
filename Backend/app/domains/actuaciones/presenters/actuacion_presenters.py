from __future__ import annotations

from typing import Any, Dict, Optional, List

from app.models import Actuaciones, Expediente

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


def actuacion_to_grid_row(act: Actuaciones) -> Dict[str, Any]:
    """
    Convierte una Actuación (con relaciones) al formato plano
    que espera Material React Table.

    IMPORTANTE:
    - fecha_actuacion se entrega como YYYY-MM-DD para input type="date"
    - enum se entrega como string limpio
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

    # -------------------------
    # Inspectores (max 3)
    # -------------------------
    inspector1 = None
    inspector2 = None
    inspector3 = None

    insp_list: List[Any] = getattr(act, "inspector", None) or []
    nombres: List[str] = []
    if insp_list:
        for i in insp_list:
            n = getattr(i, "nombre", None)
            if n:
                nombres.append(n)

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
    # Expediente / Oficio
    # -------------------------
    expediente_numero = None
    expediente_anio = None
    oficio_numero = None
    oficio_anio = None
    oficio_causa = None

    exp = None
    if getattr(act, "comprobacion_id", None):
        exp = (
            Expediente.query
            .filter_by(comprobacion_id=act.comprobacion_id)
            .first()
        )

    if exp:
        expediente_numero = getattr(exp, "numero_expediente", None)
        expediente_anio = getattr(exp, "anio", None)

        of = getattr(exp, "oficio", None)
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

    return {
        "id": act.id,
        "orden_trabajo_numero": ot_num,
        "fecha_actuacion": fecha_iso,

        "rubro_nombre": rubro_nombre,

        "inspector1": inspector1,
        "inspector2": inspector2,
        "inspector3": inspector3,

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

        "doc_nro": doc_nro,
        "contrib_apellido": contrib_apellido,
        "contrib_nombre": contrib_nombre,

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


def actuacion_to_pendiente_expediente_row(act: Actuaciones) -> Dict[str, Any]:
    """
    DTO compacto para la bandeja unificada de pendientes de expediente.

    Incluye `source_type` explícito y mantiene campos mínimos para UI administrativa.
    """
    full = actuacion_to_grid_row(act)
    source_type = _infer_expediente_source_type(act)
    full["source_type"] = source_type
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
