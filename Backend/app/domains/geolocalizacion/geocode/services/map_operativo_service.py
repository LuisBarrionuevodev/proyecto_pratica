"""
Mapa operativo DIGITALIZA: pendientes y realizados alineados al circuito de rutas / iniciadores.

Fuente de verdad:
- **Pendientes (cola)**: ``IniciadorRuta`` en ``PENDIENTE`` sin ítem en ruta ``BORRADOR``, con geocode OK.
- **Pendientes (en ruta)**: ``RutaItem`` ``EN_PROCESO`` en ruta ``PUBLICADA`` únicamente (completar trabajo pendiente).
  No incluye ítems en rutas ``BORRADOR`` ni otros estados de ruta.
- **Realizados**: ``RutaItem`` ``FINALIZADO`` + ``estado_ejecucion == REALIZADO`` (visita realizada), fecha de cierre
  ``coalesce(date(ejecutado_at), RutaTrabajo.fecha)`` dentro del rango.
"""

from __future__ import annotations

import types
from datetime import date
from typing import Any, Optional

from sqlalchemy import and_, exists, func
from sqlalchemy.orm import joinedload, selectinload

from app.database import db
from app.domains.rutas_trabajo.services.iniciador_policy_service import (
    VALOR_PRIORIDAD_ALTA,
    VALOR_PRIORIDAD_MEDIA,
)
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Oficio,
    OrdenTrabajo,
    RutaGrupoInspector,
    RutaItem,
    RutaTrabajo,
)


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except Exception:
        return None


def _geo_ok_join():
    return and_(
        Domicilio.id == DomicilioGeocode.domicilio_id,
        DomicilioGeocode.deleted_at.is_(None),
        DomicilioGeocode.geo_status == "OK",
        DomicilioGeocode.lat.isnot(None),
        DomicilioGeocode.lng.isnot(None),
    )


def _prioridad_categoria(p: int) -> str:
    """Categoría de leyenda: misma escala que planificación (1=BAJA, 2=MEDIA, 3+=ALTA)."""
    if p >= VALOR_PRIORIDAD_ALTA:
        return "ALTA"
    if p == VALOR_PRIORIDAD_MEDIA:
        return "MEDIA"
    return "BAJA"


def _contribuyente_linea(c: Contribuyente | None) -> Optional[str]:
    if c is None:
        return None
    rs = (getattr(c, "razon_social", None) or "").strip()
    if rs:
        return rs
    ap = (getattr(c, "apellido", None) or "").strip()
    nom = (getattr(c, "nombre", None) or "").strip()
    parts = [p for p in (ap, nom) if p]
    return " ".join(parts) if parts else None


def _domicilio_linea(dom: Domicilio | None) -> Optional[str]:
    if dom is None:
        return None
    calle = (dom.calle_normalizada or dom.calle or "").strip()
    num = (dom.numero or "").strip()
    if calle and num:
        return f"{calle} {num}"
    return calle or num or None


def _domicilio_linea_desde_campos(
    calle_normalizada: Any,
    calle: Any,
    numero: Any,
) -> Optional[str]:
    """Misma lógica que ``_domicilio_linea`` para filas planas del query de cola."""
    dom = types.SimpleNamespace(
        calle_normalizada=calle_normalizada,
        calle=calle,
        numero=numero,
    )
    return _domicilio_linea(dom)  # type: ignore[arg-type]


def _orden_trabajo_linea(numero: Any, mes: Any, anio: Any) -> Optional[str]:
    n = (str(numero).strip()) if numero is not None else ""
    if not n:
        return None
    try:
        m = int(mes) if mes is not None else None
        a = int(anio) if anio is not None else None
    except (TypeError, ValueError):
        return n
    if m is not None and a is not None:
        return f"{n} · {m:02d}/{a}"
    return n


def _documento_contribuyente(c: Contribuyente | None) -> Optional[str]:
    if c is None:
        return None
    d = (getattr(c, "documento", None) or "").strip()
    return d or None


def _expediente_oficio_linea(exp: Any) -> Optional[str]:
    if exp is None:
        return None
    ne = (getattr(exp, "numero_expediente", None) or "").strip()
    if not ne:
        return None
    ay = getattr(exp, "anio", None)
    return f"{ne}/{ay}" if ay is not None else ne


def _contexto_popup_realizado(ini: IniciadorRuta | None) -> dict[str, Any]:
    """
    Textos opcionales para la card de mapa (oficio / expediente / notificación) según tipo de iniciador.

    No agrega claves con valor vacío.
    """
    out: dict[str, Any] = {}
    if ini is None:
        return out
    tipo = str(getattr(ini, "tipo_iniciador", None) or "")

    if tipo == "REINSPECCION_NOTIFICACION":
        notif = getattr(ini, "notificacion", None)
        if notif is not None:
            na = getattr(notif, "numero_acta", None)
            if na:
                ay = getattr(notif, "anio", None)
                out["contexto_notificacion_origen"] = (
                    f"{na}/{ay}" if ay is not None else str(na)
                )

    if tipo in (
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
        "VERIFICAR_INFORMAR_OFICIO",
        "REINSPECCION_OFICIO",
    ):
        ofi = getattr(ini, "oficio", None)
        if ofi is not None and getattr(ofi, "deleted_at", None) is None:
            no = (getattr(ofi, "numero_oficio", None) or "").strip()
            if no:
                oa = getattr(ofi, "anio", None)
                out["contexto_oficio"] = f"{no}/{oa}" if oa is not None else no
            for exp in getattr(ofi, "expediente", None) or []:
                if exp is None or getattr(exp, "deleted_at", None) is not None:
                    continue
                line = _expediente_oficio_linea(exp)
                if line:
                    out["contexto_expediente_oficio"] = line
                    break
    return out


def _inspectores_csv(act: Actuaciones | None) -> Optional[str]:
    if act is None:
        return None
    nombres = []
    for ins in getattr(act, "inspector", None) or []:
        n = (getattr(ins, "nombre", None) or "").strip()
        if n:
            nombres.append(n)
    return ", ".join(nombres) if nombres else None


def _actas_labradas_payload(act: Actuaciones | None) -> dict[str, Optional[str]]:
    """Números de acta operativos para popup de mapa (strings cortos)."""
    if act is None:
        return {}
    ins = getattr(act, "inspeccion", None)
    noti = getattr(act, "notificacion", None)
    comp = getattr(act, "comprobacion", None)
    clau = getattr(act, "clausura", None)
    deco = getattr(act, "decomiso", None)
    return {
        "acta_inspeccion": getattr(ins, "numero_acta", None) if ins else None,
        "acta_notificacion": getattr(noti, "numero_acta", None) if noti else None,
        "acta_comprobacion": getattr(comp, "numero_acta", None) if comp else None,
        "acta_clausura": getattr(clau, "numero_acta", None) if clau else None,
        "acta_decomiso": getattr(deco, "numero_acta", None) if deco else None,
    }


def _map_tipo_filtro_front(tipo: Optional[str]) -> Optional[str]:
    """Traduce valores del filtro UI (``MapaFiltrosUnificados``) a ``IniciadorRuta.tipo_iniciador``."""
    if not tipo or tipo == "TODOS":
        return None
    mapping = {
        "DENUNCIAS": "DENUNCIA",
        "RELEVAMIENTOS": "RELEVAMIENTO",
        "REINSPECCION_OFICIO": "REINSPECCION_OFICIO",
        "NOTIFICACION_VENCIDA": "REINSPECCION_NOTIFICACION",
    }
    return mapping.get(tipo, tipo)


def list_mapa_operativo_pendientes_geo(
    *,
    desde: Optional[str],
    hasta: Optional[str],
    distrito_id: Optional[int] = None,
    tipo: Optional[str] = None,
    inspector_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Lista puntos para mapa «pendientes»: backlog planificable + ítems EN_PROCESO en rutas publicadas.

    Parámetros:
        desde/hasta: rango inclusive (ISO ``date``) sobre ``IniciadorRuta.fecha_origen`` (cola) o
            ``RutaTrabajo.fecha`` (ítem en ruta).
        distrito_id: filtra por ``Domicilio.distrito_id``.
        tipo: filtro UI (TODOS, DENUNCIAS, …) → ``IniciadorRuta.tipo_iniciador``.
        inspector_id: si viene, restringe la rama **en ruta** a ítems cuyo grupo incluye ese inspector.
            No aplica a la cola ``PENDIENTE`` (aún sin grupo asignado).

    Retorno:
        Lista de dicts con lat/lng y metadatos para armar GeoJSON.

    Errores:
        ValueError: si falta ``desde`` o ``hasta`` válidos.
    """
    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)
    if d_desde is None or d_hasta is None:
        raise ValueError("Parámetros desde y hasta (fechas ISO) son obligatorios.")
    tipo_db = _map_tipo_filtro_front(tipo)

    borrador_item_exists = exists().where(
        RutaItem.iniciador_ruta_id == IniciadorRuta.id,
        RutaItem.deleted_at.is_(None),
        RutaItem.ruta_trabajo.has(RutaTrabajo.estado_ruta == "BORRADOR"),
    )

    points: list[dict[str, Any]] = []

    q_backlog = (
        db.session.query(
            IniciadorRuta.id,
            IniciadorRuta.tipo_iniciador,
            IniciadorRuta.prioridad,
            IniciadorRuta.fecha_origen,
            IniciadorRuta.created_at,
            Domicilio.calle_normalizada,
            Domicilio.calle,
            Domicilio.numero,
            Domicilio.id.label("domicilio_id"),
            Domicilio.distrito_id,
            DomicilioGeocode.lat,
            DomicilioGeocode.lng,
        )
        .join(Domicilio, IniciadorRuta.domicilio_id == Domicilio.id)
        .join(DomicilioGeocode, _geo_ok_join())
        .filter(
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador == "PENDIENTE",
            IniciadorRuta.fecha_origen >= d_desde,
            IniciadorRuta.fecha_origen <= d_hasta,
            ~borrador_item_exists,
            Domicilio.deleted_at.is_(None),
        )
    )
    if distrito_id is not None:
        q_backlog = q_backlog.filter(Domicilio.distrito_id == distrito_id)
    if tipo_db is not None:
        q_backlog = q_backlog.filter(IniciadorRuta.tipo_iniciador == tipo_db)

    for row in q_backlog.all():
        pr = int(row.prioridad or 1)
        ubic = _domicilio_linea_desde_campos(
            row.calle_normalizada, row.calle, row.numero
        )
        creado = row.created_at
        creado_iso = creado.date().isoformat() if creado is not None else None
        points.append(
            {
                "domicilio_id": int(row.domicilio_id),
                "lat": float(row.lat),
                "lng": float(row.lng),
                "distrito_id": int(row.distrito_id) if row.distrito_id is not None else None,
                "map_layer": "iniciador_backlog",
                "iniciador_id": int(row.id),
                "ruta_item_id": None,
                "tipo_iniciador": str(row.tipo_iniciador),
                "prioridad": pr,
                "prioridad_categoria": _prioridad_categoria(pr),
                "fecha_ref": row.fecha_origen.isoformat() if row.fecha_origen else None,
                "ubicacion_texto": ubic,
                "iniciador_creado_en": creado_iso,
                "has_act": True,
                "has_rel": str(row.tipo_iniciador) == "RELEVAMIENTO",
                "act_count": 0,
                "rel_count": 0,
            }
        )

    q_ruta = (
        db.session.query(
            RutaItem.id.label("ruta_item_id"),
            IniciadorRuta.id.label("iniciador_id"),
            IniciadorRuta.tipo_iniciador,
            IniciadorRuta.prioridad,
            RutaTrabajo.fecha.label("fecha_ruta"),
            Domicilio.id.label("domicilio_id"),
            Domicilio.distrito_id,
            DomicilioGeocode.lat,
            DomicilioGeocode.lng,
            OrdenTrabajo.numero_acta.label("ot_numero"),
            OrdenTrabajo.mes.label("ot_mes"),
            OrdenTrabajo.anio.label("ot_anio"),
        )
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Domicilio, IniciadorRuta.domicilio_id == Domicilio.id)
        .join(DomicilioGeocode, _geo_ok_join())
        .outerjoin(
            OrdenTrabajo,
            and_(
                OrdenTrabajo.id == RutaItem.orden_trabajo_id,
                OrdenTrabajo.deleted_at.is_(None),
            ),
        )
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "EN_PROCESO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            RutaTrabajo.fecha >= d_desde,
            RutaTrabajo.fecha <= d_hasta,
            IniciadorRuta.deleted_at.is_(None),
            Domicilio.deleted_at.is_(None),
        )
    )
    if distrito_id is not None:
        q_ruta = q_ruta.filter(Domicilio.distrito_id == distrito_id)
    if tipo_db is not None:
        q_ruta = q_ruta.filter(IniciadorRuta.tipo_iniciador == tipo_db)
    if inspector_id is not None:
        ins_match = exists().where(
            RutaGrupoInspector.ruta_grupo_id == RutaItem.ruta_grupo_id,
            RutaGrupoInspector.inspector_id == inspector_id,
        )
        q_ruta = q_ruta.filter(ins_match)

    for row in q_ruta.all():
        pr = int(row.prioridad or 1)
        ot_linea = _orden_trabajo_linea(row.ot_numero, row.ot_mes, row.ot_anio)
        points.append(
            {
                "domicilio_id": int(row.domicilio_id),
                "lat": float(row.lat),
                "lng": float(row.lng),
                "distrito_id": int(row.distrito_id) if row.distrito_id is not None else None,
                "map_layer": "ruta_en_proceso",
                "iniciador_id": int(row.iniciador_id),
                "ruta_item_id": int(row.ruta_item_id),
                "tipo_iniciador": str(row.tipo_iniciador),
                "prioridad": pr,
                "prioridad_categoria": None,
                "fecha_ref": row.fecha_ruta.isoformat() if row.fecha_ruta else None,
                "orden_trabajo_texto": ot_linea,
                "has_act": True,
                "has_rel": str(row.tipo_iniciador) == "RELEVAMIENTO",
                "act_count": 0,
                "rel_count": 0,
            }
        )

    return points


def list_mapa_operativo_realizados_geo(
    *,
    desde: Optional[str],
    hasta: Optional[str],
    distrito_id: Optional[int] = None,
    tipo: Optional[str] = None,
    inspector_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Puntos «realizados»: cierres con visita realizada (``RutaItem`` finalizado + ``REALIZADO``).

    Fecha operativa: ``coalesce(date(ejecutado_at), RutaTrabajo.fecha)`` dentro del rango inclusive.
    Coordenadas: ``Actuaciones.domicilio_id`` (post-corrección en Completar trabajo) con geocode OK.
    """
    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)
    if d_desde is None or d_hasta is None:
        raise ValueError("Parámetros desde y hasta (fechas ISO) son obligatorios.")
    tipo_db = _map_tipo_filtro_front(tipo)

    fecha_cierre = func.coalesce(func.date(RutaItem.ejecutado_at), RutaTrabajo.fecha)

    q = (
        RutaItem.query.join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .join(DomicilioGeocode, _geo_ok_join())
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            fecha_cierre >= d_desde,
            fecha_cierre <= d_hasta,
            Actuaciones.domicilio_id.isnot(None),
            Domicilio.deleted_at.is_(None),
        )
        .options(
            selectinload(RutaItem.actuacion)
            .selectinload(Actuaciones.domicilio)
            .selectinload(Domicilio.geocode),
            selectinload(RutaItem.actuacion)
            .selectinload(Actuaciones.domicilio)
            .selectinload(Domicilio.distrito),
            selectinload(RutaItem.actuacion)
            .selectinload(Actuaciones.domicilio)
            .selectinload(Domicilio.contribuyente),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.inspector),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.inspeccion),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.notificacion),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.comprobacion),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.clausura),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.decomiso),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.orden_trabajo),
            selectinload(RutaItem.iniciador_ruta).selectinload(IniciadorRuta.oficio).selectinload(
                Oficio.expediente
            ),
            selectinload(RutaItem.iniciador_ruta).selectinload(IniciadorRuta.notificacion),
            joinedload(RutaItem.ruta_trabajo),
        )
    )
    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    if tipo_db is not None:
        q = q.filter(IniciadorRuta.tipo_iniciador == tipo_db)
    if inspector_id is not None:
        ins_match = exists().where(
            RutaGrupoInspector.ruta_grupo_id == RutaItem.ruta_grupo_id,
            RutaGrupoInspector.inspector_id == inspector_id,
        )
        q = q.filter(ins_match)

    points: list[dict[str, Any]] = []
    for item in q.order_by(RutaItem.id).all():
        act = item.actuacion
        ini = item.iniciador_ruta
        dom = act.domicilio if act else None
        geo = dom.geocode if dom else None
        if (
            geo is None
            or geo.lat is None
            or geo.lng is None
            or str(getattr(geo, "geo_status", "") or "") != "OK"
        ):
            continue
        ej = item.ejecutado_at
        fecha_ref = ej.date() if ej else (item.ruta_trabajo.fecha if item.ruta_trabajo else None)
        dist_nom = None
        if dom and dom.distrito:
            dist_nom = getattr(dom.distrito, "nombre", None) or getattr(dom.distrito, "codigo", None)
        actas = _actas_labradas_payload(act)
        ot_num = None
        if act and getattr(act, "orden_trabajo", None):
            ot_num = getattr(act.orden_trabajo, "numero_acta", None)
        nl = getattr(act, "nombre_local", None) if act else None
        nombre_local_val = (str(nl).strip() or None) if nl is not None else None
        tipo_act = getattr(act, "tipo", None) if act else None
        tipo_act_str = str(tipo_act) if tipo_act is not None else None
        doc_c = _documento_contribuyente(dom.contribuyente if dom else None)

        base: dict[str, Any] = {
            "domicilio_id": int(dom.id) if dom else None,
            "lat": float(geo.lat),
            "lng": float(geo.lng),
            "distrito_id": int(dom.distrito_id) if dom and dom.distrito_id is not None else None,
            "distrito_nombre": dist_nom,
            "map_layer": "ruta_realizado",
            "iniciador_id": int(ini.id) if ini else None,
            "ruta_item_id": int(item.id),
            "actuacion_id": int(act.id) if act else None,
            "tipo_iniciador": str(ini.tipo_iniciador) if ini else None,
            "fecha_ref": fecha_ref.isoformat() if fecha_ref else None,
            "has_act": True,
            "has_rel": str(ini.tipo_iniciador) == "RELEVAMIENTO" if ini else False,
            "act_count": 1,
            "rel_count": 0,
            "inspectores": _inspectores_csv(act),
            "contribuyente_o_razon_social": _contribuyente_linea(dom.contribuyente if dom else None),
            "domicilio_texto": _domicilio_linea(dom),
            "acta_inspeccion": actas.get("acta_inspeccion"),
            "acta_notificacion": actas.get("acta_notificacion"),
            "acta_comprobacion": actas.get("acta_comprobacion"),
            "acta_clausura": actas.get("acta_clausura"),
            "acta_decomiso": actas.get("acta_decomiso"),
            "prioridad_categoria": None,
            "orden_trabajo_numero": str(ot_num).strip() if ot_num else None,
            "nombre_local": nombre_local_val,
            "tipo_actuacion": tipo_act_str,
            "doc_contribuyente": doc_c,
        }
        base.update(_contexto_popup_realizado(ini))
        points.append(base)
    return points


def count_mapa_operativo_pendientes_cola(
    *,
    desde: str,
    hasta: str,
    distrito_id: Optional[int] = None,
    tipo: Optional[str] = None,
) -> int:
    """
    Cuenta iniciadores en cola con geocode OK (misma semántica que puntos ``iniciador_backlog`` del mapa).

    Parámetros:
        desde/hasta: ISO date inclusive sobre ``IniciadorRuta.fecha_origen``.
        distrito_id / tipo: mismos filtros que el GeoJSON de pendientes.

    Retorno:
        Cantidad de filas (entero ≥ 0).

    Errores:
        ValueError: fechas inválidas o ausentes.
    """
    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)
    if d_desde is None or d_hasta is None:
        raise ValueError("Parámetros desde y hasta (fechas ISO) son obligatorios.")
    tipo_db = _map_tipo_filtro_front(tipo)
    borrador_item_exists = exists().where(
        RutaItem.iniciador_ruta_id == IniciadorRuta.id,
        RutaItem.deleted_at.is_(None),
        RutaItem.ruta_trabajo.has(RutaTrabajo.estado_ruta == "BORRADOR"),
    )
    q = (
        db.session.query(func.count(IniciadorRuta.id))
        .select_from(IniciadorRuta)
        .join(Domicilio, IniciadorRuta.domicilio_id == Domicilio.id)
        .join(DomicilioGeocode, _geo_ok_join())
        .filter(
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador == "PENDIENTE",
            IniciadorRuta.fecha_origen >= d_desde,
            IniciadorRuta.fecha_origen <= d_hasta,
            ~borrador_item_exists,
            Domicilio.deleted_at.is_(None),
        )
    )
    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    if tipo_db is not None:
        q = q.filter(IniciadorRuta.tipo_iniciador == tipo_db)
    return int(q.scalar() or 0)


def count_mapa_operativo_pendientes_en_ruta(
    *,
    desde: str,
    hasta: str,
    distrito_id: Optional[int] = None,
    tipo: Optional[str] = None,
    inspector_id: Optional[int] = None,
) -> int:
    """
    Cuenta ítems ``EN_PROCESO`` en rutas ``PUBLICADAS`` con geocode OK (``ruta_en_proceso`` del mapa).

    El inspector_id filtra por grupo (misma regla que el listado GeoJSON).
    """
    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)
    if d_desde is None or d_hasta is None:
        raise ValueError("Parámetros desde y hasta (fechas ISO) son obligatorios.")
    tipo_db = _map_tipo_filtro_front(tipo)
    q = (
        db.session.query(func.count(RutaItem.id))
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Domicilio, IniciadorRuta.domicilio_id == Domicilio.id)
        .join(DomicilioGeocode, _geo_ok_join())
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "EN_PROCESO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            RutaTrabajo.fecha >= d_desde,
            RutaTrabajo.fecha <= d_hasta,
            IniciadorRuta.deleted_at.is_(None),
            Domicilio.deleted_at.is_(None),
        )
    )
    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    if tipo_db is not None:
        q = q.filter(IniciadorRuta.tipo_iniciador == tipo_db)
    if inspector_id is not None:
        ins_match = exists().where(
            RutaGrupoInspector.ruta_grupo_id == RutaItem.ruta_grupo_id,
            RutaGrupoInspector.inspector_id == inspector_id,
        )
        q = q.filter(ins_match)
    return int(q.scalar() or 0)


def count_mapa_operativo_realizados_visita(
    *,
    desde: str,
    hasta: str,
    distrito_id: Optional[int] = None,
    tipo: Optional[str] = None,
    inspector_id: Optional[int] = None,
) -> int:
    """
    Cuenta cierres con visita realizada visibles en mapa (``FINALIZADO`` + ``REALIZADO``, ruta ``PUBLICADA``,
    fecha de cierre en rango, geocode OK). Misma base que ``list_mapa_operativo_realizados_geo`` sin expandir ORM.
    """
    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)
    if d_desde is None or d_hasta is None:
        raise ValueError("Parámetros desde y hasta (fechas ISO) son obligatorios.")
    tipo_db = _map_tipo_filtro_front(tipo)
    fecha_cierre = func.coalesce(func.date(RutaItem.ejecutado_at), RutaTrabajo.fecha)
    q = (
        db.session.query(func.count(RutaItem.id))
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .join(DomicilioGeocode, _geo_ok_join())
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            fecha_cierre >= d_desde,
            fecha_cierre <= d_hasta,
            Actuaciones.domicilio_id.isnot(None),
            Domicilio.deleted_at.is_(None),
        )
    )
    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    if tipo_db is not None:
        q = q.filter(IniciadorRuta.tipo_iniciador == tipo_db)
    if inspector_id is not None:
        ins_match = exists().where(
            RutaGrupoInspector.ruta_grupo_id == RutaItem.ruta_grupo_id,
            RutaGrupoInspector.inspector_id == inspector_id,
        )
        q = q.filter(ins_match)
    return int(q.scalar() or 0)
