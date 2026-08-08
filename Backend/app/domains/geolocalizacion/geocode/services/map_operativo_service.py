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
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import joinedload, selectinload

from app.database import db
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_efectivo_para_iniciador,
)
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
    actuaciones_inspector,
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


def _borrador_item_exists_clause():
    return exists().where(
        RutaItem.iniciador_ruta_id == IniciadorRuta.id,
        RutaItem.deleted_at.is_(None),
        RutaItem.ruta_trabajo.has(RutaTrabajo.estado_ruta == "BORRADOR"),
    )


def _coords_desde_domicilio_id(
    domicilio_id: int,
    *,
    apply_backfill: bool = False,
) -> tuple[float | None, float | None, int | None, str | None]:
    """
    Obtiene lat/lng/distrito y línea de dirección si el domicilio tiene geocode OK.

    Returns:
        (lat, lng, distrito_id, ubicacion_texto) o Nones si no hay geocode OK.
    """
    if apply_backfill:
        from app.domains.geolocalizacion.geocode.services.distrito_backfill_service import (
            backfill_distrito_for_domicilio_if_needed,
        )

        backfill_distrito_for_domicilio_if_needed(int(domicilio_id))

    dom = db.session.get(Domicilio, domicilio_id)
    if not dom or dom.deleted_at is not None:
        return None, None, None, None

    geo = (
        DomicilioGeocode.query.filter(
            DomicilioGeocode.domicilio_id == domicilio_id,
            DomicilioGeocode.deleted_at.is_(None),
            DomicilioGeocode.geo_status == "OK",
            DomicilioGeocode.lat.isnot(None),
            DomicilioGeocode.lng.isnot(None),
        )
        .first()
    )
    if not geo:
        return None, None, None, None
    ubic = _domicilio_linea(dom)
    dist_id = int(dom.distrito_id) if dom.distrito_id is not None else None
    return float(geo.lat), float(geo.lng), dist_id, ubic


def _map_point_desde_iniciador_backlog(
    ini: IniciadorRuta,
    *,
    distrito_id: Optional[int],
) -> Optional[dict[str, Any]]:
    """Arma punto de mapa backlog usando domicilio efectivo (PR5)."""
    efectivo = resolve_domicilio_efectivo_para_iniciador(
        ini,
        apply_backfill=True,
        try_sync=False,
    )
    if not efectivo.domicilio_id:
        return None
    lat, lng, dist_id, ubic = _coords_desde_domicilio_id(int(efectivo.domicilio_id))
    if lat is None or lng is None:
        return None

    if distrito_id is not None and dist_id != distrito_id:
        return None

    pr = int(ini.prioridad or 1)
    creado = ini.created_at
    creado_iso = creado.date().isoformat() if creado is not None else None
    return {
        "domicilio_id": int(efectivo.domicilio_id),
        "lat": lat,
        "lng": lng,
        "distrito_id": dist_id,
        "map_layer": "iniciador_backlog",
        "iniciador_id": int(ini.id),
        "ruta_item_id": None,
        "tipo_iniciador": str(ini.tipo_iniciador),
        "prioridad": pr,
        "prioridad_categoria": _prioridad_categoria(pr),
        "fecha_ref": ini.fecha_origen.isoformat() if ini.fecha_origen else None,
        "ubicacion_texto": ubic,
        "iniciador_creado_en": creado_iso,
        "has_act": True,
        "has_rel": str(ini.tipo_iniciador) == "RELEVAMIENTO",
        "act_count": 0,
        "rel_count": 0,
    }


def _realizados_inspector_coincide(inspector_id: int):
    """
    Filtro de inspector para visitas realizadas.

    Incluye ítems cuyo ``ruta_grupo`` asignó al inspector y también aquellos con ``ruta_grupo_id``
    nulo pero cuya actuación registra al inspector en ``actuaciones_inspector`` (caso habitual al
    cerrar la visita sin depender del grupo persistido).

    Parámetros:
        inspector_id: ID de inspector municipal.

    Retorno:
        Expresión SQLAlchemy booleana para ``.filter(...)``.
    """
    via_grupo = exists().where(
        RutaGrupoInspector.ruta_grupo_id == RutaItem.ruta_grupo_id,
        RutaGrupoInspector.inspector_id == inspector_id,
    )
    via_actuacion = exists().where(
        actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
        actuaciones_inspector.c.inspector_id == inspector_id,
        actuaciones_inspector.c.deleted_at.is_(None),
    )
    return or_(via_grupo, via_actuacion)


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

    points: list[dict[str, Any]] = []

    q_backlog = IniciadorRuta.query.filter(
        IniciadorRuta.deleted_at.is_(None),
        IniciadorRuta.estado_iniciador == "PENDIENTE",
        IniciadorRuta.fecha_origen >= d_desde,
        IniciadorRuta.fecha_origen <= d_hasta,
        ~_borrador_item_exists_clause(),
    )
    if tipo_db is not None:
        q_backlog = q_backlog.filter(IniciadorRuta.tipo_iniciador == tipo_db)

    for ini in q_backlog.all():
        pt = _map_point_desde_iniciador_backlog(ini, distrito_id=distrito_id)
        if pt:
            points.append(pt)

    q_ruta = (
        db.session.query(RutaItem, IniciadorRuta, RutaTrabajo, OrdenTrabajo)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
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
        )
    )
    if tipo_db is not None:
        q_ruta = q_ruta.filter(IniciadorRuta.tipo_iniciador == tipo_db)
    if inspector_id is not None:
        ins_match = exists().where(
            RutaGrupoInspector.ruta_grupo_id == RutaItem.ruta_grupo_id,
            RutaGrupoInspector.inspector_id == inspector_id,
        )
        q_ruta = q_ruta.filter(ins_match)

    for item, ini, ruta, ot in q_ruta.all():
        efectivo = resolve_domicilio_efectivo_para_iniciador(ini, apply_backfill=True, try_sync=False)
        if not efectivo.domicilio_id:
            continue
        lat, lng, dist_id, _ubic = _coords_desde_domicilio_id(int(efectivo.domicilio_id))
        if lat is None or lng is None:
            continue
        if distrito_id is not None and dist_id != distrito_id:
            continue
        pr = int(ini.prioridad or 1)
        ot_linea = _orden_trabajo_linea(
            ot.numero_acta if ot else None,
            ot.mes if ot else None,
            ot.anio if ot else None,
        )
        points.append(
            {
                "domicilio_id": int(efectivo.domicilio_id),
                "lat": lat,
                "lng": lng,
                "distrito_id": dist_id,
                "map_layer": "ruta_en_proceso",
                "iniciador_id": int(ini.id),
                "ruta_item_id": int(item.id),
                "tipo_iniciador": str(ini.tipo_iniciador),
                "prioridad": pr,
                "prioridad_categoria": None,
                "fecha_ref": ruta.fecha.isoformat() if ruta.fecha else None,
                "orden_trabajo_texto": ot_linea,
                "has_act": True,
                "has_rel": str(ini.tipo_iniciador) == "RELEVAMIENTO",
                "act_count": 0,
                "rel_count": 0,
            }
        )

    return points


def _definicion_actuacion_filtro(definicion: Optional[str]) -> Optional[str]:
    """
    Normaliza el filtro UI «definición» (actas de clausura / decomiso) para la query de realizados.

    Parámetros:
        definicion: valor crudo del query string (p. ej. ``CLAUSURA``, ``TODOS``).

    Retorno:
        ``CLAUSURA``, ``DECOMISO``, ``CLAUSURA_DECOMISO`` o ``None`` (sin filtro adicional).

    Errores:
        Ninguno: valores desconocidos se tratan como sin filtro.
    """
    if not definicion:
        return None
    key = str(definicion).strip().upper()
    if key in ("", "TODOS", "ALL"):
        return None
    if key in ("CLAUSURA", "DECOMISO", "CLAUSURA_DECOMISO"):
        return key
    return None


def list_mapa_operativo_realizados_geo(
    *,
    desde: Optional[str],
    hasta: Optional[str],
    distrito_id: Optional[int] = None,
    tipo: Optional[str] = None,
    inspector_id: Optional[int] = None,
    definicion: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Puntos «realizados»: cierres con visita realizada (``RutaItem`` finalizado + ``REALIZADO``).

    Fecha operativa: ``coalesce(date(ejecutado_at), RutaTrabajo.fecha)`` dentro del rango inclusive.
    Coordenadas: ``Actuaciones.domicilio_id`` (post-corrección en Completar trabajo) con geocode OK.

    Filtro opcional ``definicion``: restringe a actuaciones con acta de clausura y/o decomiso según UI
    (``CLAUSURA``, ``DECOMISO``, ``CLAUSURA_DECOMISO``).
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
        q = q.filter(_realizados_inspector_coincide(inspector_id))

    definicion_key = _definicion_actuacion_filtro(definicion)
    if definicion_key == "CLAUSURA":
        q = q.filter(Actuaciones.clausura.has())
    elif definicion_key == "DECOMISO":
        q = q.filter(Actuaciones.decomiso.has())
    elif definicion_key == "CLAUSURA_DECOMISO":
        q = q.filter(Actuaciones.clausura.has(), Actuaciones.decomiso.has())

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


_TIPOS_PENDIENTES_COLA_KPI: tuple[str, ...] = (
    "RELEVAMIENTO",
    "REINSPECCION_OFICIO",
    "REINSPECCION_NOTIFICACION",
    "DENUNCIA",
)


def _query_iniciadores_cola_backlog(
    d_desde: date,
    d_hasta: date,
    tipo_db: Optional[str] = None,
    *,
    tipos_db: Optional[tuple[str, ...]] = None,
) -> list[IniciadorRuta]:
    """
    Iniciadores PENDIENTE en cola (sin ítem en ruta BORRADOR) dentro del rango de ``fecha_origen``.

    Parámetros:
        d_desde, d_hasta: rango inclusive.
        tipo_db: filtro opcional sobre ``IniciadorRuta.tipo_iniciador`` (valor canónico BD).
        tipos_db: filtro opcional IN sobre varios tipos (agregación indicadores).

    Retorno:
        Lista de ``IniciadorRuta`` (sin filtrar geocode; eso ocurre en el mapper).
    """
    q = IniciadorRuta.query.options(
        joinedload(IniciadorRuta.domicilio),
        joinedload(IniciadorRuta.relevamiento),
        joinedload(IniciadorRuta.denuncia),
        joinedload(IniciadorRuta.actuacion),
    ).filter(
        IniciadorRuta.deleted_at.is_(None),
        IniciadorRuta.estado_iniciador == "PENDIENTE",
        IniciadorRuta.fecha_origen >= d_desde,
        IniciadorRuta.fecha_origen <= d_hasta,
        ~_borrador_item_exists_clause(),
    )
    if tipos_db is not None:
        q = q.filter(IniciadorRuta.tipo_iniciador.in_(tipos_db))
    elif tipo_db is not None:
        q = q.filter(IniciadorRuta.tipo_iniciador == tipo_db)
    return q.all()


def _iniciador_backlog_countable(
    ini: IniciadorRuta,
    *,
    distrito_id: Optional[int],
    cache: dict[str, Any],
) -> bool:
    """
    True si el iniciador cuenta en cola planificable (equivale a ``_map_point... is not None``).

    Memoiza domicilio efectivo, backfill de distrito y coords por request para evitar trabajo
    repetido cuando varios iniciadores comparten domicilio o el backfill ya se intentó.
    """
    from app.domains.geolocalizacion.geocode.services.distrito_backfill_service import (
        backfill_distrito_for_domicilio_if_needed,
    )

    dist_key = distrito_id if distrito_id is not None else "__all__"
    results: dict[tuple[int, object], bool] = cache.setdefault("results", {})
    result_key = (int(ini.id), dist_key)
    if result_key in results:
        return results[result_key]

    efectivos: dict[int, object] = cache.setdefault("efectivos", {})
    ini_id = int(ini.id)
    if ini_id not in efectivos:
        efectivos[ini_id] = resolve_domicilio_efectivo_para_iniciador(
            ini,
            apply_backfill=False,
            try_sync=False,
        )
    efectivo = efectivos[ini_id]
    if not efectivo.domicilio_id:
        results[result_key] = False
        return False

    dom_id = int(efectivo.domicilio_id)
    if distrito_id is not None:
        backfill_done: set[int] = cache.setdefault("backfill_done", set())
        if dom_id not in backfill_done:
            backfill_distrito_for_domicilio_if_needed(dom_id)
            backfill_done.add(dom_id)

    coords_cache: dict[int, tuple[float | None, float | None, int | None, str | None]] = (
        cache.setdefault("coords", {})
    )
    if dom_id not in coords_cache:
        coords_cache[dom_id] = _coords_desde_domicilio_id(dom_id)
    lat, lng, dist_id, _ubic = coords_cache[dom_id]
    if lat is None or lng is None:
        results[result_key] = False
        return False
    if distrito_id is not None and dist_id != distrito_id:
        results[result_key] = False
        return False

    results[result_key] = True
    return True


def _probable_efectivo_domicilio_ids(iniciadores: list[IniciadorRuta]) -> set[int]:
    """Domicilios candidatos (iniciador + orígenes frecuentes) para precargar geocode."""
    dom_ids: set[int] = set()
    for ini in iniciadores:
        if ini.domicilio_id:
            dom_ids.add(int(ini.domicilio_id))
        rel = ini.relevamiento
        if rel is not None and rel.domicilio_id:
            dom_ids.add(int(rel.domicilio_id))
        den = ini.denuncia
        if den is not None and getattr(den, "domicilio_id", None):
            dom_ids.add(int(den.domicilio_id))
        act = ini.actuacion
        if act is not None and act.domicilio_id:
            dom_ids.add(int(act.domicilio_id))
    return dom_ids


def _warm_geocode_coords_cache(dom_ids: set[int], cache: dict[str, Any]) -> None:
    """Precarga coords/distrito de geocodes OK para reducir N+1 en el loop de conteo."""
    if not dom_ids:
        return
    coords_cache: dict[int, tuple[float | None, float | None, int | None, str | None]] = (
        cache.setdefault("coords", {})
    )
    missing = [dom_id for dom_id in dom_ids if dom_id not in coords_cache]
    if not missing:
        return
    rows = (
        db.session.query(
            DomicilioGeocode.domicilio_id,
            DomicilioGeocode.lat,
            DomicilioGeocode.lng,
            Domicilio.distrito_id,
        )
        .join(Domicilio, Domicilio.id == DomicilioGeocode.domicilio_id)
        .filter(
            DomicilioGeocode.domicilio_id.in_(missing),
            DomicilioGeocode.deleted_at.is_(None),
            DomicilioGeocode.geo_status == "OK",
            DomicilioGeocode.lat.isnot(None),
            DomicilioGeocode.lng.isnot(None),
            Domicilio.deleted_at.is_(None),
        )
        .all()
    )
    for dom_id, lat, lng, dist_id in rows:
        coords_cache[int(dom_id)] = (
            float(lat),
            float(lng),
            int(dist_id) if dist_id is not None else None,
            None,
        )
    for dom_id in missing:
        coords_cache.setdefault(dom_id, (None, None, None, None))


@dataclass(frozen=True)
class PendientesColaKpis:
    """Conteos por tipo de iniciador en cola planificable (geo OK)."""

    relevamientos_pendientes: int
    reinspecciones_oficio_pendientes: int
    reinspecciones_notificacion_pendientes: int
    denuncias_pendientes: int


@dataclass(frozen=True)
class PendientesColaKpisAggregation:
    """Resultado de agregación en una sola pasada + métricas para PERF_LOG."""

    kpis: PendientesColaKpis
    scanned_count: int
    mapped_count: int
    base_query_ms: float
    mapping_ms: float


def aggregate_mapa_operativo_pendientes_cola_kpis(
    *,
    desde: str,
    hasta: str,
    distrito_id: Optional[int] = None,
) -> PendientesColaKpisAggregation:
    """
    Cuenta todos los buckets de cola pendiente en una sola pasada (misma semántica que 4× ``count_*``).

    Parámetros:
        desde/hasta: ISO date inclusive sobre ``IniciadorRuta.fecha_origen``.
        distrito_id: filtro opcional por domicilio efectivo con geocode OK.

    Retorno:
        KPIs por tipo + métricas de escaneo/mapping.

    Errores:
        ValueError: fechas inválidas o ausentes.
    """
    import time

    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)
    if d_desde is None or d_hasta is None:
        raise ValueError("Parámetros desde y hasta (fechas ISO) son obligatorios.")

    t0 = time.perf_counter()
    iniciadores = _query_iniciadores_cola_backlog(
        d_desde,
        d_hasta,
        tipos_db=_TIPOS_PENDIENTES_COLA_KPI,
    )
    base_query_ms = (time.perf_counter() - t0) * 1000.0

    counts = {
        "RELEVAMIENTO": 0,
        "REINSPECCION_OFICIO": 0,
        "REINSPECCION_NOTIFICACION": 0,
        "DENUNCIA": 0,
    }
    mapped = 0
    request_cache: dict[str, Any] = {}
    _warm_geocode_coords_cache(_probable_efectivo_domicilio_ids(iniciadores), request_cache)
    t1 = time.perf_counter()
    for ini in iniciadores:
        if _iniciador_backlog_countable(ini, distrito_id=distrito_id, cache=request_cache):
            mapped += 1
            tipo = str(ini.tipo_iniciador)
            if tipo in counts:
                counts[tipo] += 1
    mapping_ms = (time.perf_counter() - t1) * 1000.0

    kpis = PendientesColaKpis(
        relevamientos_pendientes=counts["RELEVAMIENTO"],
        reinspecciones_oficio_pendientes=counts["REINSPECCION_OFICIO"],
        reinspecciones_notificacion_pendientes=counts["REINSPECCION_NOTIFICACION"],
        denuncias_pendientes=counts["DENUNCIA"],
    )
    return PendientesColaKpisAggregation(
        kpis=kpis,
        scanned_count=len(iniciadores),
        mapped_count=mapped,
        base_query_ms=base_query_ms,
        mapping_ms=mapping_ms,
    )


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
    total = 0
    for ini in _query_iniciadores_cola_backlog(d_desde, d_hasta, tipo_db):
        if _map_point_desde_iniciador_backlog(ini, distrito_id=distrito_id):
            total += 1
    return total


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
        db.session.query(RutaItem, IniciadorRuta, RutaTrabajo)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "EN_PROCESO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            RutaTrabajo.fecha >= d_desde,
            RutaTrabajo.fecha <= d_hasta,
            IniciadorRuta.deleted_at.is_(None),
        )
    )
    if tipo_db is not None:
        q = q.filter(IniciadorRuta.tipo_iniciador == tipo_db)
    if inspector_id is not None:
        ins_match = exists().where(
            RutaGrupoInspector.ruta_grupo_id == RutaItem.ruta_grupo_id,
            RutaGrupoInspector.inspector_id == inspector_id,
        )
        q = q.filter(ins_match)

    total = 0
    for _item, ini, _ruta in q.all():
        efectivo = resolve_domicilio_efectivo_para_iniciador(ini, apply_backfill=True, try_sync=False)
        if not efectivo.domicilio_id:
            continue
        lat, lng, dist_id, _ = _coords_desde_domicilio_id(int(efectivo.domicilio_id))
        if lat is None:
            continue
        if distrito_id is not None and dist_id != distrito_id:
            continue
        total += 1
    return total


def count_mapa_operativo_realizados_visita(
    *,
    desde: str,
    hasta: str,
    distrito_id: Optional[int] = None,
    tipo: Optional[str] = None,
    inspector_id: Optional[int] = None,
    definicion: Optional[str] = None,
) -> int:
    """
    Cuenta cierres con visita realizada visibles en mapa (``FINALIZADO`` + ``REALIZADO``, ruta ``PUBLICADA``,
    fecha de cierre en rango, geocode OK). Misma base que ``list_mapa_operativo_realizados_geo`` sin expandir ORM.

    Parámetros:
        definicion: mismo filtro opcional que el GeoJSON (clausura / decomiso / ambos).
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
        q = q.filter(_realizados_inspector_coincide(inspector_id))

    definicion_key = _definicion_actuacion_filtro(definicion)
    if definicion_key == "CLAUSURA":
        q = q.filter(Actuaciones.clausura.has())
    elif definicion_key == "DECOMISO":
        q = q.filter(Actuaciones.decomiso.has())
    elif definicion_key == "CLAUSURA_DECOMISO":
        q = q.filter(Actuaciones.clausura.has(), Actuaciones.decomiso.has())

    return int(q.scalar() or 0)
