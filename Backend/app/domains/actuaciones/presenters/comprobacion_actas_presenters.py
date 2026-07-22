"""
Presentación para bandejas de Actas de comprobación (reinspección oficio / recorrido).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, Optional

from sqlalchemy import or_

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    expediente_envio_por_comprobacion,
    oficio_por_comprobacion,
)
from app.domains.actuaciones.services.comprobacion_oficio_recorrido_service import (
    oficio_recorrido_campos_operativos,
)
from app.domains.actuaciones.services.oficio_list_service import list_oficios_by_comprobacion
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.domains.rutas_trabajo.services.ruta_publicar_service import tipo_actuacion_para_iniciador
from app.models import Actuaciones, Expediente, IniciadorRuta, JuzgadoCatalogo, Oficio, RutaItem


def iniciador_reinspeccion_oficio_vigente(actuacion_id: int) -> Optional[IniciadorRuta]:
    """
    Último iniciador ``REINSPECCION_OFICIO`` no soft-deleted para la actuación.

    Solo alimenta columnas del presenter (F3.6b): **no** determina si la fila entra o sale de la bandeja;
    eso lo resuelve ``list_pendientes_reinspeccion_oficio`` (ítem en ruta activa).

    Parámetros:
        actuacion_id: PK de ``Actuaciones``.

    Retorno:
        ``IniciadorRuta`` o ``None`` si no hay iniciador activo de ese tipo.

    Errores:
        Ninguno (consulta de solo lectura).
    """
    return (
        IniciadorRuta.query.filter(
            IniciadorRuta.actuacion_id == actuacion_id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _expediente_respuesta_oficio(comprobacion_id: int) -> Optional[Expediente]:
    """
    Expediente de respuesta vinculado a un oficio de la comprobación.

    Alineado a la bandeja de reinspección: admite ``tipo_expediente`` explícito o ``NULL`` (legado).
    """
    return (
        Expediente.query.filter_by(comprobacion_id=comprobacion_id)
        .filter(Expediente.oficio_id.isnot(None))
        .filter(
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            )
        )
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.desc())
        .first()
    )


def estado_recorrido_label(act: Actuaciones) -> str:
    """
    Etiqueta consultiva del estado del circuito documental para la fila de actuación.

    Orden del circuito: expediente de envío de acta → oficio administrativo → (re)programación
    de reinspección. Sin expediente de envío aún no corresponde mostrar «Esperando oficio».
    """
    if not act.comprobacion_id:
        return "—"
    exp_env = expediente_envio_por_comprobacion(act.comprobacion_id)
    if not exp_env:
        return "Esperando expediente"
    ofi = oficio_por_comprobacion(act.comprobacion_id)
    if not ofi:
        return "Esperando oficio"

    ini = iniciador_reinspeccion_oficio_vigente(act.id)
    if not ini:
        return "Oficio cargado — sin reinspección programada"
    if ini.estado_iniciador == "CUMPLIDO":
        return "Reinspección cumplida"
    if ini.estado_iniciador in inactive_estados():
        return f"Cerrado ({ini.estado_iniciador})"
    return "Pendiente reinspección por oficio"


def _expediente_respuesta_por_oficio_id(oficio_id: int) -> Optional[Expediente]:
    return (
        Expediente.query.filter_by(oficio_id=int(oficio_id))
        .filter(
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            )
        )
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .first()
    )


def reinspeccion_oficio_bandeja_row(
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
    iniciador: IniciadorRuta | None = None,
    oficio: Oficio | None = None,
) -> Dict[str, Any]:
    """
    Fila JSON para la bandeja «Pendiente de reinspección» (circuito documental listo).

    Parámetros:
        act: actuación ancla (con comprobación).
        counts_by_eo: mapa opcional para ``actuacion_to_grid_row``.
        iniciador: si se pasa, se incluyen ``iniciador_id`` / estado / tipo (compat. tests y callers legacy).

    Retorno:
        dict alineado a ``IReinspeccionOficioPendienteRow`` (iniciador ausente → ``iniciador_id`` 0 y strings vacíos).

    Nota:
        Cuando ``iniciador`` es ``None``, corresponde al caso «oficio cargado — sin reinspección programada»
        (la bandeja operativa lista antes de crear ``REINSPECCION_OFICIO``).
    """
    base = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
    row: Dict[str, Any] = dict(base)
    if iniciador is not None:
        row["iniciador_id"] = iniciador.id
        row["estado_iniciador"] = iniciador.estado_iniciador
        row["tipo_iniciador"] = iniciador.tipo_iniciador
        row["fecha_origen_iniciador"] = (
            iniciador.fecha_origen.isoformat() if iniciador.fecha_origen else None
        )
    else:
        row["iniciador_id"] = 0
        row["estado_iniciador"] = ""
        row["tipo_iniciador"] = ""
        row["fecha_origen_iniciador"] = None
    row["documento_pendiente"] = "Reinspección por oficio"

    ofi_ref = oficio
    cid = getattr(act, "comprobacion_id", None)
    if cid:
        exp_env = expediente_envio_por_comprobacion(int(cid))
        if exp_env:
            row["expediente_envio_numero"] = getattr(exp_env, "numero_expediente", None)
            row["expediente_envio_anio"] = getattr(exp_env, "anio", None)
            fe = getattr(exp_env, "fecha_expediente", None)
            row["fecha_expediente_envio"] = fe.isoformat() if fe is not None else None
        ofi = oficio if oficio is not None else oficio_por_comprobacion(int(cid))
        ofi_ref = ofi
        if ofi:
            row["oficio_id"] = ofi.id
            row["oficio_numero"] = getattr(ofi, "numero_oficio", None)
            row["oficio_anio"] = getattr(ofi, "anio", None)
            fo = getattr(ofi, "fecha_oficio", None)
            row["fecha_oficio"] = fo.isoformat() if fo is not None else None
            row["juzgado_nombre"] = _juzgado_nombre(ofi)
            row["oficio_causa"] = getattr(ofi, "causa", None)
        exp_resp = _expediente_respuesta_por_oficio_id(ofi.id) if ofi else _expediente_respuesta_oficio(int(cid))
        if exp_resp:
            row["expediente_respuesta_numero"] = getattr(exp_resp, "numero_expediente", None)
            row["expediente_respuesta_anio"] = getattr(exp_resp, "anio", None)
            fr = getattr(exp_resp, "fecha_expediente", None)
            row["fecha_expediente_respuesta"] = fr.isoformat() if fr is not None else None

    ini_oficio = _iniciador_trabajo_oficio_mas_reciente(act.id)
    row["tipo_visita_resultado"] = _tipo_visita_resultado_final(base, ini_oficio)
    row["estado_recorrido"] = estado_recorrido_label(act)
    oid = ofi_ref.id if ofi_ref is not None else 0
    iid = iniciador.id if iniciador is not None else 0
    row["bandeja_row_key"] = f"{act.id}-{oid}-{iid}"

    if ofi_ref is not None:
        from app.domains.actuaciones.services.oficio_editable_service import evaluar_editable_oficio

        policy = evaluar_editable_oficio(ofi_ref.id)
        for key in (
            "editable",
            "bloqueado_motivo",
            "ruta_estado",
            "estado_ejecucion",
            "en_ruta_borrador",
            "estado_operativo",
            "acciones_permitidas",
        ):
            if policy.get(key) is not None:
                row[key] = policy[key]
        if "editable" not in row:
            row["editable"] = policy.get("editable", True)

    return row


def iniciador_reinspeccion_to_row(
    ini: IniciadorRuta,
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
) -> Dict[str, Any]:
    """
    Fila para bandeja Pendientes de reinspección (oficio ya cargado).

    Incluye el mismo snapshot que ``actuacion_to_grid_row`` (contribuyente, domicilio, inspección,
    acta de comprobación, etc.) más los campos del iniciador y el detalle documental de envío /
    oficio / expediente de respuesta para modales alineados al circuito.

    Además (paridad con recorrido / grilla):
    - ``tipo_visita_resultado``: tipo de visita desambigüado (p. ej. verificar e informar) o ``None``.
    - ``estado_recorrido``: etiqueta de circuito documental (misma función que la tabla Recorrido).
    """
    return reinspeccion_oficio_bandeja_row(act, counts_by_eo=counts_by_eo, iniciador=ini)


def _oficio_compact_label(numero: Any, anio: Any) -> str:
    """``numero/año`` legible; cadena vacía si no hay datos."""
    n = (str(numero).strip() if numero is not None else "")
    a = (str(anio).strip() if anio is not None else "")
    if not n and not a:
        return ""
    return "/".join(p for p in (n, a) if p)


def _oficio_recorrido_resumen_item(
    ofi: Oficio,
    *,
    actuacion_ancla: Actuaciones | None = None,
) -> Dict[str, Any]:
    """
    Snapshot de oficio + expediente de respuesta asociado para listado de recorrido.

    Incluye textos compactos listos para UI, OT y conclusión propias del oficio.
    """
    exp = _expediente_respuesta_por_oficio_id(int(ofi.id))
    num_o = getattr(ofi, "numero_oficio", None)
    an_o = getattr(ofi, "anio", None)
    num_e = getattr(exp, "numero_expediente", None) if exp else None
    an_e = getattr(exp, "anio", None) if exp else None
    oficio_texto = _oficio_compact_label(num_o, an_o) or None
    expediente_texto = _oficio_compact_label(num_e, an_e) or None
    operativo = oficio_recorrido_campos_operativos(
        ofi,
        actuacion_ancla_id=int(actuacion_ancla.id) if actuacion_ancla is not None else None,
    )
    return {
        "id": ofi.id,
        "numero_oficio": num_o,
        "anio_oficio": an_o,
        "oficio_texto": oficio_texto,
        "numero_expediente": num_e,
        "anio_expediente": an_e,
        "expediente_texto": expediente_texto,
        "causa": getattr(ofi, "causa", None),
        "juzgado_nombre": _juzgado_nombre(ofi),
        # Compat. con consumidores que usaban ``numero`` / ``anio``.
        "numero": num_o,
        "anio": an_o,
        **operativo,
    }


def _oficio_expediente_linea_compacta(item: Dict[str, Any]) -> str:
    """``3489/2026 (Exp. 012388/2026)`` o solo oficio si no hay expediente."""
    ot = (item.get("oficio_texto") or "").strip()
    et = (item.get("expediente_texto") or "").strip()
    if ot and et:
        return f"{ot} (Exp. {et})"
    return ot


def resultado_cumplimiento_recorrido(act: Actuaciones) -> Optional[str]:
    """
    Resultado de cumplimiento efectivo para filtros de recorrido.

    Si la reinspección por oficio está CUMPLIDA y existe actuación de segunda visita,
    usa el resultado persistido en esa visita; si no, el de la actuación ancla.
    """
    ini = iniciador_reinspeccion_oficio_vigente(act.id)
    if ini is not None and ini.estado_iniciador == "CUMPLIDO":
        act_visita = _actuacion_visita_reinspeccion_desde_ruta_item(
            ini,
            actuacion_ancla_id=int(act.id),
        )
        if act_visita is not None:
            resultado = getattr(act_visita, "resultado_cumplimiento_oficio", None)
            if resultado is not None:
                return resultado.value if hasattr(resultado, "value") else str(resultado)
    resultado = getattr(act, "resultado_cumplimiento_oficio", None)
    if resultado is None:
        return None
    return resultado.value if hasattr(resultado, "value") else str(resultado)


def comprobacion_recorrido_resumen_row(
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
) -> Dict[str, Any]:
    base = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
    base["estado_recorrido"] = estado_recorrido_label(act)
    base["resultado_cumplimiento_oficio"] = resultado_cumplimiento_recorrido(act)
    cid = getattr(act, "comprobacion_id", None)
    if cid:
        oficios = list_oficios_by_comprobacion(int(cid))
        oficios_resumen = [_oficio_recorrido_resumen_item(ofi, actuacion_ancla=act) for ofi in oficios]
        base["oficios_resumen"] = oficios_resumen
        lineas = [_oficio_expediente_linea_compacta(o) for o in oficios_resumen]
        base["oficios_texto"] = ", ".join(l for l in lineas if l) or None
        if oficios:
            first = oficios[0]
            base["oficio_numero"] = getattr(first, "numero_oficio", None)
            base["oficio_anio"] = getattr(first, "anio", None)
            fo = getattr(first, "fecha_oficio", None)
            base["fecha_oficio"] = fo.isoformat() if fo is not None else None
            base["juzgado_nombre"] = _juzgado_nombre(first)
        first_item = oficios_resumen[0] if oficios_resumen else None
        if first_item and first_item.get("expediente_texto"):
            base["expediente_respuesta_numero"] = first_item.get("numero_expediente")
            base["expediente_respuesta_anio"] = first_item.get("anio_expediente")
        elif oficios_resumen:
            exp_resp = _expediente_respuesta_oficio(int(cid))
            if exp_resp:
                base["expediente_respuesta_numero"] = getattr(exp_resp, "numero_expediente", None)
                base["expediente_respuesta_anio"] = getattr(exp_resp, "anio", None)
    return base


def _iniciador_origen_primera_actuacion(act: Actuaciones) -> Optional[IniciadorRuta]:
    """
    Iniciador mostrado en ``origen.iniciador`` del detalle de recorrido (solo lectura / UI).

    Debe reflejar el **origen de la actuación** donde se labró la primera comprobación
    (p. ej. DENUNCIA, RELEVAMIENTO), no el iniciador de **reinspección por oficio**
    (posterior en el circuito).

    Regla: entre los ``IniciadorRuta`` de esta actuación (no borrados), el de menor ``id``
    excluyendo ``REINSPECCION_OFICIO``. Si solo hubiera reinspección por oficio, se usa el
    de menor ``id`` (compatibilidad). No altera cómo se crean ni actualizan iniciadores en BD.
    """
    q_base = IniciadorRuta.query.filter(
        IniciadorRuta.actuacion_id == act.id,
        IniciadorRuta.deleted_at.is_(None),
    )
    primero_sin_reinsp_ofi = (
        q_base.filter(IniciadorRuta.tipo_iniciador != "REINSPECCION_OFICIO")
        .order_by(IniciadorRuta.id.asc())
        .first()
    )
    if primero_sin_reinsp_ofi is not None:
        return primero_sin_reinsp_ofi
    return q_base.order_by(IniciadorRuta.id.asc()).first()


_TIPOS_INI_TRABAJO_OFICIO = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)

_TIPOS_VISITA_CATALOG = frozenset(
    {
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
    }
)


def _norm_tipo_catalogo(s: str | None) -> str:
    if not s:
        return ""
    t = str(s).strip().upper().replace("_", " ")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.split())


def _iniciador_trabajo_oficio_mas_reciente(act_id: int) -> Optional[IniciadorRuta]:
    """Último iniciador de circuito oficio/reinspección (tipos operativos alineados a Completar trabajo)."""
    return (
        IniciadorRuta.query.filter(
            IniciadorRuta.actuacion_id == act_id,
            IniciadorRuta.tipo_iniciador.in_(_TIPOS_INI_TRABAJO_OFICIO),
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _tipo_visita_resultado_final(
    grid: Dict[str, Any],
    ini_oficio: Optional[IniciadorRuta],
) -> Optional[str]:
    """
    Actuación **resultante** del circuito oficio/reinspección (ratificación / verificar e informar).

    No devuelve ``REINSPECCION`` genérico: ese valor describe el paso/circuito, no la actuación hija.
    En ese caso se devuelve ``None`` y la UI muestra «Pendiente» hasta que ``act.tipo`` refleje
    el tipo concreto labrado.
    """
    raw = grid.get("tipo_actuacion")
    if raw and _norm_tipo_catalogo(str(raw)) in {_norm_tipo_catalogo(x) for x in _TIPOS_VISITA_CATALOG}:
        return str(raw).strip()

    if ini_oficio and ini_oficio.tipo_iniciador in (
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    ):
        try:
            return tipo_actuacion_para_iniciador(ini_oficio.tipo_iniciador)
        except KeyError:
            pass

    if raw and _norm_tipo_catalogo(str(raw)) == "REINSPECCION":
        return None

    if raw:
        return str(raw).strip()
    return None


def _actuacion_visita_reinspeccion_desde_ruta_item(
    ini: IniciadorRuta,
    *,
    actuacion_ancla_id: int,
) -> Optional[Actuaciones]:
    """
    Actuación labrada al cerrar el trabajo del iniciador (segunda visita), distinta del ancla.

    Último ``RutaItem`` FINALIZADO y REALIZADO con ``actuacion_id`` para este ``iniciador_ruta_id``.
    No usa la actuación ancla como sustituto.

    Parámetros:
        ini: iniciador ``REINSPECCION_OFICIO``.
        actuacion_ancla_id: PK de la actuación con acta de comprobación (GET recorrido).

    Retorno:
        ``Actuaciones`` de la visita posterior o ``None``.
    """
    item = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    if item is None or item.actuacion_id is None:
        return None
    if int(item.actuacion_id) == int(actuacion_ancla_id):
        return None
    return db.session.get(Actuaciones, int(item.actuacion_id))


def _payload_ejecucion_reinspeccion(
    act_visita: Actuaciones,
    *,
    ini_oficio: Optional[IniciadorRuta],
) -> Dict[str, Any]:
    """Snapshot de grilla de la segunda visita + cumplimiento persistido en esa actuación."""
    grid_v = actuacion_to_grid_row(act_visita)
    resultado = getattr(act_visita, "resultado_cumplimiento_oficio", None)
    res_val_v = resultado.value if resultado is not None and hasattr(resultado, "value") else resultado
    tipo_tv = _tipo_visita_resultado_final(grid_v, ini_oficio)
    tipo_lab = tipo_tv or (
        str(grid_v.get("tipo_actuacion")).strip() if grid_v.get("tipo_actuacion") else None
    )
    return {
        "actuacion_id": act_visita.id,
        "inspectores_texto": grid_v.get("inspectores_texto"),
        "inspector1": grid_v.get("inspector1"),
        "inspector2": grid_v.get("inspector2"),
        "inspector3": grid_v.get("inspector3"),
        "fecha_actuacion": grid_v.get("fecha_actuacion"),
        "orden_trabajo_numero": grid_v.get("orden_trabajo_numero"),
        "tipo_inspeccion_labrada": tipo_lab,
        "resultado_cumplimiento_oficio": res_val_v,
    }


def _juzgado_nombre(ofi: Optional[Oficio]) -> Optional[str]:
    if not ofi or not getattr(ofi, "juzgado_id", None):
        return None
    jz = JuzgadoCatalogo.query.filter_by(id=int(ofi.juzgado_id)).first()
    return getattr(jz, "nombre", None) if jz else None


def referencia_actuacion_from_grid_row(grid: Dict[str, Any]) -> Dict[str, Any]:
    """
    Snapshot de la actuación (misma fuente que ``actuacion_to_grid_row``).

    Reutilizable en detalle de recorrido (solo lectura) y en ficha documental operativa de comprobación.
    """
    return {
        "fecha_actuacion": grid.get("fecha_actuacion"),
        "orden_trabajo_numero": grid.get("orden_trabajo_numero"),
        "calle": grid.get("calle_mostrar") or grid.get("calle"),
        "numero": grid.get("numero_mostrar") or grid.get("numero"),
        "contrib_apellido": grid.get("contrib_apellido"),
        "contrib_nombre": grid.get("contrib_nombre"),
        "razon_social": grid.get("razon_social"),
        "doc_nro": grid.get("doc_nro"),
        "rubro_nombre": grid.get("rubro_nombre"),
        "comprobacion_motivo": grid.get("comprobacion_motivo"),
        "acta_inspeccion_num": grid.get("acta_inspeccion_num"),
        "acta_comprobacion_num": grid.get("acta_comprobacion_num"),
        "inspectores_texto": grid.get("inspectores_texto"),
        "inspector1": grid.get("inspector1"),
        "inspector2": grid.get("inspector2"),
        "inspector3": grid.get("inspector3"),
        "tipo_actuacion": grid.get("tipo_actuacion"),
    }


def comprobacion_recorrido_detalle(act: Actuaciones) -> Dict[str, Any]:
    """
    Detalle estructurado consultivo (sin PDF): origen, comprobación, expedientes, oficio, reinspección, resultado.

    Contrato estable (extensiones UI recorrido):
    - ``referencia_actuacion``: mismos hechos de visita que la grilla (domicilio mostrable, titular,
      documento, rubro, inspectores, tipo de actuación, acta de inspección) para que el modal no
      dependa del listado.
    - ``origen.iniciador``: iniciador de origen de la actuación / primera comprobación
      (excluye ``REINSPECCION_OFICIO`` salvo si es el único).
    - ``oficio``: incluye ``causa``, ``juzgado_id``, ``juzgado_nombre`` cuando hay oficio.
    - ``resultado_final.tipo_actuacion``: mismo string que la grilla (``actuacion_to_grid_row``).
    - ``resultado_final.tipo_visita``: actuación resultante (ratificación / verificar e informar) o
      ``None`` si aún no hay tipo concreto (p. ej. ``REINSPECCION`` genérico en ``act.tipo``).
    - ``reinspeccion_por_oficio``: metadatos del iniciador ``REINSPECCION_OFICIO`` (id, tipo, estado,
      fecha de origen, documento). Si el trámite está ``CUMPLIDO`` y existe una actuación distinta del ancla
      vinculada por ``RutaItem`` FINALIZADO/REALIZADO, ``ejecucion_reinspeccion`` resume esa segunda visita
      (inspectores, fecha, OT, tipo y cumplimiento). Si no hay actuación resultante resoluble, ``None``
      (sin usar el ancla como sustituto).
    """
    if not act.comprobacion_id:
        raise ValueError("La actuación no tiene comprobación")

    grid = actuacion_to_grid_row(act)
    ini_oficio = _iniciador_trabajo_oficio_mas_reciente(act.id)
    exp_env = expediente_envio_por_comprobacion(act.comprobacion_id)
    ofi = oficio_por_comprobacion(act.comprobacion_id)
    exp_resp = _expediente_respuesta_oficio(act.comprobacion_id)

    ini = (
        IniciadorRuta.query.filter(
            IniciadorRuta.actuacion_id == act.id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )

    act_visita_rein: Optional[Actuaciones] = None
    if ini is not None:
        act_visita_rein = _actuacion_visita_reinspeccion_desde_ruta_item(
            ini,
            actuacion_ancla_id=int(act.id),
        )

    ini_origen = _iniciador_origen_primera_actuacion(act)
    iniciador_payload: Optional[Dict[str, Any]] = None
    if ini_origen is not None:
        iniciador_payload = {
            "tipo_iniciador": ini_origen.tipo_iniciador,
            "estado_iniciador": ini_origen.estado_iniciador,
            "fecha_origen": ini_origen.fecha_origen.isoformat() if ini_origen.fecha_origen else None,
        }

    resultado = getattr(act, "resultado_cumplimiento_oficio", None)
    res_val = resultado.value if resultado is not None and hasattr(resultado, "value") else resultado
    tipo_visita_final = _tipo_visita_resultado_final(grid, ini_oficio)

    oficio_payload: Optional[Dict[str, Any]] = None
    if ofi is not None:
        oficio_payload = {
            "id": ofi.id,
            "numero_oficio": ofi.numero_oficio,
            "anio": ofi.anio,
            "fecha_oficio": ofi.fecha_oficio.isoformat() if ofi.fecha_oficio else None,
            "causa": getattr(ofi, "causa", None),
            "juzgado_id": getattr(ofi, "juzgado_id", None),
            "juzgado_nombre": _juzgado_nombre(ofi),
        }

    return {
        "actuacion_id": act.id,
        "oficios_resumen": (
            [_oficio_recorrido_resumen_item(ofi, actuacion_ancla=act) for ofi in list_oficios_by_comprobacion(int(act.comprobacion_id))]
            if act.comprobacion_id
            else []
        ),
        "origen": {
            "descripcion": "Actuación con acta de comprobación",
            "fecha_actuacion": grid.get("fecha_actuacion"),
            "orden_trabajo_numero": grid.get("orden_trabajo_numero"),
            "iniciador": iniciador_payload,
        },
        "acta_comprobacion": {
            "numero": grid.get("acta_comprobacion_num"),
            "motivo": grid.get("comprobacion_motivo"),
        },
        "expediente_comprobacion_envio": (
            {
                "id": exp_env.id,
                "numero": exp_env.numero_expediente,
                "anio": exp_env.anio,
                "fecha": exp_env.fecha_expediente.isoformat() if exp_env.fecha_expediente else None,
                "tipo": exp_env.tipo_expediente,
            }
            if exp_env
            else None
        ),
        "oficio": oficio_payload,
        "expediente_respuesta_oficio": (
            {
                "id": exp_resp.id,
                "numero": exp_resp.numero_expediente,
                "anio": exp_resp.anio,
                "fecha": exp_resp.fecha_expediente.isoformat() if exp_resp.fecha_expediente else None,
                "tipo": exp_resp.tipo_expediente,
            }
            if exp_resp
            else None
        ),
        "reinspeccion_por_oficio": (
            {
                "iniciador_id": ini.id,
                "tipo_iniciador": ini.tipo_iniciador,
                "estado_iniciador": ini.estado_iniciador,
                "fecha_origen": ini.fecha_origen.isoformat() if ini.fecha_origen else None,
                "documento_pendiente": "Reinspección por oficio",
                "ejecucion_reinspeccion": (
                    _payload_ejecucion_reinspeccion(act_visita_rein, ini_oficio=ini_oficio)
                    if ini.estado_iniciador == "CUMPLIDO" and act_visita_rein is not None
                    else None
                ),
            }
            if ini
            else None
        ),
        "referencia_actuacion": referencia_actuacion_from_grid_row(grid),
        "resultado_final": {
            "resultado_cumplimiento_oficio": res_val,
            "estado_recorrido": estado_recorrido_label(act),
            "tipo_actuacion": grid.get("tipo_actuacion"),
            "tipo_visita": tipo_visita_final,
        },
    }
