"""
OPER-ANALYTICS.2 — Golden dataset y baseline operativo (solo diagnóstico).

Universo canónico: intentos cerrados (``RutaItem``) en rutas PUBLICADAS con actuación y OT.
Período principal: ``RutaTrabajo.fecha``. No modifica datos ni endpoints productivos.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import joinedload, selectinload

from app.database import db
from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    _realizados_inspector_coincide,
    list_mapa_operativo_realizados_geo,
)
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    fetch_no_realizadas_visita_rows,
    is_contraproducencia_excluida_valor,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    BUCKET_RATIFICACION_CLAUSURA,
    BUCKET_RATIFICACION_DECOMISO,
    BUCKET_REINSPECCION_OFICIO,
    BUCKET_VERIFICAR_INFORMAR,
    bucket_operativo,
    visitas_realizadas_por_tipo_iniciador,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    _comprobacion_labarda_filter,
    _notificacion_labarda_exists,
)
from app.domains.rutas_trabajo.utils.rubro_operativo import rubro_id_operativo_para_iniciador
from app.models import (
    Actuaciones,
    Clausura,
    Decomiso,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Inspeccion,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaGrupoInspector,
    RutaItem,
    RutaTrabajo,
    actuaciones_inspector,
)

TIPOS_OFICIO = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)


def _origen_principal(tipo_iniciador: str | None) -> str:
    """Bucket principal de origen (sin inferir por actas)."""
    t = (tipo_iniciador or "").strip().upper()
    if t == "RELEVAMIENTO":
        return "RELEVAMIENTO"
    if t == "DENUNCIA":
        return "DENUNCIA"
    if t == "REINSPECCION_NOTIFICACION":
        return "REINSPECCION_NOTIFICACION"
    if t in TIPOS_OFICIO:
        return "OFICIO"
    return "OTRO"


def _subtipo_oficio(tipo_iniciador: str | None, actuacion_tipo: str | None) -> str | None:
    """Subtipo oficio conservando enum real."""
    t = (tipo_iniciador or "").strip().upper()
    if t in TIPOS_OFICIO:
        return t
    b = bucket_operativo(tipo_iniciador, actuacion_tipo)
    if b == BUCKET_VERIFICAR_INFORMAR:
        return "VERIFICAR_INFORMAR_OFICIO"
    if b == BUCKET_RATIFICACION_CLAUSURA:
        return "RATIFICACION_CLAUSURA_OFICIO"
    if b == BUCKET_RATIFICACION_DECOMISO:
        return "RATIFICACION_DECOMISO_OFICIO"
    if b == BUCKET_REINSPECCION_OFICIO:
        return "REINSPECCION_OFICIO"
    return None


def _domicilio_efectivo_id(act_dom_id: int | None, ini_dom_id: int | None) -> int | None:
    """Misma regla que indicadores: coalesce(actuación, iniciador)."""
    if act_dom_id is not None:
        return int(act_dom_id)
    if ini_dom_id is not None:
        return int(ini_dom_id)
    return None


def _geo_info(dom: Domicilio | None) -> dict[str, Any]:
    """Estado geográfico del domicilio."""
    if dom is None or dom.deleted_at is not None:
        return {
            "lat": None,
            "lng": None,
            "geo_status": None,
            "tiene_geocode_ok": False,
            "sin_geocode_registro": True,
            "geo_status_distinto_ok": False,
            "lat_lng_null": True,
        }
    geo = DomicilioGeocode.query.filter(
        DomicilioGeocode.domicilio_id == dom.id,
        DomicilioGeocode.deleted_at.is_(None),
    ).first()
    if geo is None:
        return {
            "lat": None,
            "lng": None,
            "geo_status": None,
            "tiene_geocode_ok": False,
            "sin_geocode_registro": True,
            "geo_status_distinto_ok": False,
            "lat_lng_null": True,
        }
    lat = float(geo.lat) if geo.lat is not None else None
    lng = float(geo.lng) if geo.lng is not None else None
    status = str(geo.geo_status or "")
    ok = status == "OK" and lat is not None and lng is not None
    return {
        "lat": lat,
        "lng": lng,
        "geo_status": status or None,
        "tiene_geocode_ok": ok,
        "sin_geocode_registro": False,
        "geo_status_distinto_ok": status != "OK",
        "lat_lng_null": lat is None or lng is None,
    }


def _inspectores_de_intento(item: RutaItem, act: Actuaciones) -> tuple[list[int], list[str]]:
    """Inspectores únicos vía actuaciones_inspector y grupo de ruta."""
    ids: set[int] = set()
    nombres: dict[int, str] = {}
    for ins in act.inspector or []:
        if ins and ins.id is not None:
            ids.add(int(ins.id))
            nombres[int(ins.id)] = str(ins.nombre)
    if item.ruta_grupo_id is not None:
        rows = (
            RutaGrupoInspector.query.filter(
                RutaGrupoInspector.ruta_grupo_id == item.ruta_grupo_id,
            ).all()
        )
        for rg in rows:
            if rg.inspector_id is not None:
                iid = int(rg.inspector_id)
                ids.add(iid)
                if rg.inspector and iid not in nombres:
                    nombres[iid] = str(rg.inspector.nombre)
    return sorted(ids), [nombres[i] for i in sorted(ids)]


def _actas_flags(act: Actuaciones) -> dict[str, Any]:
    """Actas labradas por intento (reglas alineadas a indicadores)."""
    tiene_inspeccion = act.inspeccion is not None
    tiene_clausura = act.clausura is not None
    tiene_decomiso = act.decomiso is not None
    tiene_notificacion = False
    tiene_comprobacion = False
    if act.id is not None:
        tiene_notificacion = bool(
            db.session.query(Actuaciones.id)
            .filter(Actuaciones.id == act.id, _notificacion_labarda_exists())
            .first()
        )
        tiene_comprobacion = bool(
            db.session.query(Actuaciones.id)
            .filter(Actuaciones.id == act.id, _comprobacion_labarda_filter())
            .first()
        )
    partes = [
        tiene_inspeccion,
        tiene_notificacion,
        tiene_comprobacion,
        tiene_clausura,
        tiene_decomiso,
    ]
    return {
        "acta_inspeccion": tiene_inspeccion,
        "acta_notificacion": tiene_notificacion,
        "acta_comprobacion": tiene_comprobacion,
        "acta_clausura": tiene_clausura,
        "acta_decomiso": tiene_decomiso,
        "cantidad_actas_labradas": sum(1 for p in partes if p),
    }


def _kg_decomiso(act: Actuaciones) -> float:
    if act.decomiso is None or act.decomiso.cantidad is None:
        return 0.0
    return float(act.decomiso.cantidad)


def _inspector_participa(item: RutaItem, act: Actuaciones, inspector_id: int) -> bool:
    """True si el inspector participó (grupo o actuaciones_inspector)."""
    via_grupo = (
        item.ruta_grupo_id is not None
        and db.session.query(RutaGrupoInspector.id)
        .filter(
            RutaGrupoInspector.ruta_grupo_id == item.ruta_grupo_id,
            RutaGrupoInspector.inspector_id == inspector_id,
        )
        .first()
        is not None
    )
    if via_grupo:
        return True
    return (
        db.session.query(actuaciones_inspector.c.actuaciones_id)
        .filter(
            actuaciones_inspector.c.actuaciones_id == act.id,
            actuaciones_inspector.c.inspector_id == inspector_id,
            actuaciones_inspector.c.deleted_at.is_(None),
        )
        .first()
        is not None
    )


def _base_intentos_query(desde: date, hasta: date):
    """Query ORM de intentos cerrados canónicos en período por ``RutaTrabajo.fecha``."""
    return (
        RutaItem.query.join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .join(OrdenTrabajo, Actuaciones.orden_trabajo_id == OrdenTrabajo.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion.in_(("REALIZADO", "NO_REALIZADO")),
            RutaTrabajo.estado_ruta == "PUBLICADA",
            Actuaciones.orden_trabajo_id.isnot(None),
            RutaTrabajo.fecha >= desde,
            RutaTrabajo.fecha <= hasta,
        )
        .options(
            joinedload(RutaItem.ruta_trabajo),
            joinedload(RutaItem.iniciador_ruta),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.orden_trabajo),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.domicilio).selectinload(
                Domicilio.distrito
            ),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.domicilio).selectinload(
                Domicilio.rubro
            ),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.inspector),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.inspeccion),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.notificacion),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.comprobacion),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.clausura),
            selectinload(RutaItem.actuacion).selectinload(Actuaciones.decomiso),
            joinedload(RutaItem.iniciador_ruta)
            .joinedload(IniciadorRuta.domicilio)
            .joinedload(Domicilio.distrito),
        )
    )


@dataclass
class OperAnalyticsIntentoRow:
    """Fila plana de un intento operativo cerrado."""

    ruta_item_id: int
    actuacion_id: int
    orden_trabajo_id: int
    numero_orden_trabajo: str | None
    ruta_trabajo_id: int
    fecha_ruta: date
    ejecutado_at: datetime | None
    estado_ejecucion: str
    motivo_no_realizado: str | None
    contraproducencia: str | None
    iniciador_ruta_id: int
    tipo_iniciador: str | None
    origen_operativo_normalizado: str
    subtipo_oficio: str | None
    tipo_actuacion: str | None
    realizo_nueva_inspeccion: bool | None
    resultado_cumplimiento_oficio: str | None
    domicilio_id_actuacion: int | None
    domicilio_id_iniciador: int | None
    domicilio_id_efectivo: int | None
    domicilios_difieren: bool
    distrito_id_actuacion: int | None
    distrito_id_iniciador: int | None
    distrito_id_efectivo: int | None
    distrito_discrepante: bool
    calle: str | None
    numero: str | None
    lat: float | None
    lng: float | None
    geo_status: str | None
    tiene_geocode_ok: bool
    sin_geocode_registro: bool
    geo_status_distinto_ok: bool
    lat_lng_null: bool
    rubro_id_operativo: int | None
    rubro_nombre: str | None
    inspector_ids: list[int] = field(default_factory=list)
    inspector_nombres: list[str] = field(default_factory=list)
    inspector_cantidad: int = 0
    acta_inspeccion: bool = False
    acta_notificacion: bool = False
    acta_comprobacion: bool = False
    acta_clausura: bool = False
    acta_decomiso: bool = False
    cantidad_actas_labradas: int = 0
    kg_decomisados: float = 0.0
    fecha_actuacion: date | None = None
    fecha_ejecutado_date: date | None = None
    difiere_fecha_ruta_ejecucion: bool = False
    difiere_fecha_ruta_actuacion: bool = False
    pertenece_universo_operativo: bool = True
    dibujable_en_mapa: bool = False
    en_ventana_mapa_fecha: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["fecha_ruta"] = self.fecha_ruta.isoformat()
        d["fecha_actuacion"] = self.fecha_actuacion.isoformat() if self.fecha_actuacion else None
        d["fecha_ejecutado_date"] = (
            self.fecha_ejecutado_date.isoformat() if self.fecha_ejecutado_date else None
        )
        if self.ejecutado_at is not None:
            d["ejecutado_at"] = self.ejecutado_at.isoformat()
        return d


def _row_from_item(
    item: RutaItem,
    *,
    desde: date,
    hasta: date,
) -> OperAnalyticsIntentoRow:
    """Construye fila diagnóstica desde un ``RutaItem`` hidratado."""
    act = item.actuacion
    ini = item.iniciador_ruta
    ruta = item.ruta_trabajo
    assert act is not None and ini is not None and ruta is not None

    act_dom_id = int(act.domicilio_id) if act.domicilio_id is not None else None
    ini_dom_id = int(ini.domicilio_id) if ini.domicilio_id is not None else None
    eff_dom_id = _domicilio_efectivo_id(act_dom_id, ini_dom_id)

    dom_act = act.domicilio
    dom_ini = ini.domicilio
    dom_eff = dom_act if eff_dom_id == act_dom_id else dom_ini
    if dom_eff is None and eff_dom_id is not None:
        dom_eff = db.session.get(Domicilio, eff_dom_id)

    geo_eff = _geo_info(dom_eff)
    geo_act = _geo_info(dom_act) if dom_act is not None else _geo_info(None)
    dist_act = dom_act.distrito_id if dom_act else None
    dist_ini = dom_ini.distrito_id if dom_ini else None
    dist_eff = dom_eff.distrito_id if dom_eff else None
    dist_discrepante = dist_act is not None and dist_ini is not None and dist_act != dist_ini

    rub_id = rubro_id_operativo_para_iniciador(ini, dom_eff, act=act)
    rub_nombre = None
    if rub_id is not None:
        rub = db.session.get(Rubro, rub_id)
        rub_nombre = rub.nombre if rub else None
    elif dom_eff and dom_eff.rubro:
        rub_nombre = dom_eff.rubro.nombre

    insp_ids, insp_nombres = _inspectores_de_intento(item, act)
    actas = _actas_flags(act)
    ot = act.orden_trabajo
    fe_exec = item.ejecutado_at.date() if item.ejecutado_at else None
    fecha_mapa = fe_exec if fe_exec is not None else ruta.fecha
    en_ventana_mapa = desde <= fecha_mapa <= hasta

    return OperAnalyticsIntentoRow(
        ruta_item_id=int(item.id),
        actuacion_id=int(act.id),
        orden_trabajo_id=int(act.orden_trabajo_id),
        numero_orden_trabajo=str(ot.numero_acta) if ot else None,
        ruta_trabajo_id=int(ruta.id),
        fecha_ruta=ruta.fecha,
        ejecutado_at=item.ejecutado_at,
        estado_ejecucion=str(item.estado_ejecucion or ""),
        motivo_no_realizado=item.motivo_no_realizado,
        contraproducencia=act.contraproducencia,
        iniciador_ruta_id=int(ini.id),
        tipo_iniciador=ini.tipo_iniciador,
        origen_operativo_normalizado=_origen_principal(ini.tipo_iniciador),
        subtipo_oficio=_subtipo_oficio(ini.tipo_iniciador, act.tipo),
        tipo_actuacion=act.tipo,
        realizo_nueva_inspeccion=act.realizo_nueva_inspeccion,
        resultado_cumplimiento_oficio=act.resultado_cumplimiento_oficio,
        domicilio_id_actuacion=act_dom_id,
        domicilio_id_iniciador=ini_dom_id,
        domicilio_id_efectivo=eff_dom_id,
        domicilios_difieren=act_dom_id is not None
        and ini_dom_id is not None
        and act_dom_id != ini_dom_id,
        distrito_id_actuacion=int(dist_act) if dist_act is not None else None,
        distrito_id_iniciador=int(dist_ini) if dist_ini is not None else None,
        distrito_id_efectivo=int(dist_eff) if dist_eff is not None else None,
        distrito_discrepante=dist_discrepante,
        calle=dom_eff.calle if dom_eff else None,
        numero=dom_eff.numero if dom_eff else None,
        lat=geo_eff["lat"],
        lng=geo_eff["lng"],
        geo_status=geo_eff["geo_status"],
        tiene_geocode_ok=geo_eff["tiene_geocode_ok"],
        sin_geocode_registro=geo_eff["sin_geocode_registro"],
        geo_status_distinto_ok=geo_eff["geo_status_distinto_ok"],
        lat_lng_null=geo_eff["lat_lng_null"],
        rubro_id_operativo=rub_id,
        rubro_nombre=rub_nombre,
        inspector_ids=insp_ids,
        inspector_nombres=insp_nombres,
        inspector_cantidad=len(insp_ids),
        acta_inspeccion=actas["acta_inspeccion"],
        acta_notificacion=actas["acta_notificacion"],
        acta_comprobacion=actas["acta_comprobacion"],
        acta_clausura=actas["acta_clausura"],
        acta_decomiso=actas["acta_decomiso"],
        cantidad_actas_labradas=actas["cantidad_actas_labradas"],
        kg_decomisados=_kg_decomiso(act),
        fecha_actuacion=act.fecha,
        fecha_ejecutado_date=fe_exec,
        difiere_fecha_ruta_ejecucion=fe_exec is not None and fe_exec != ruta.fecha,
        difiere_fecha_ruta_actuacion=act.fecha != ruta.fecha,
        pertenece_universo_operativo=True,
        dibujable_en_mapa=geo_eff["tiene_geocode_ok"],
        en_ventana_mapa_fecha=en_ventana_mapa,
    )


def fetch_golden_dataset(
    desde: date,
    hasta: date,
    *,
    distrito_id: int | None = None,
    inspector_id: int | None = None,
    distrito_modo: str = "efectivo",
) -> list[OperAnalyticsIntentoRow]:
    """
    Lista plana de intentos cerrados en el período (``RutaTrabajo.fecha``).

    Parámetros:
        desde, hasta: rango inclusive sobre fecha de ruta.
        distrito_id: filtro opcional (efectivo, actuación o iniciador según ``distrito_modo``).
        inspector_id: filtro opcional por participación.
        distrito_modo: ``efectivo`` | ``actuacion`` | ``iniciador``.

    Retorno:
        Filas ordenadas por ``ruta_item_id``.
    """
    q = _base_intentos_query(desde, hasta)
    rows: list[OperAnalyticsIntentoRow] = []
    for item in q.order_by(RutaItem.id).all():
        row = _row_from_item(item, desde=desde, hasta=hasta)
        if inspector_id is not None and item.actuacion is not None:
            if not _inspector_participa(item, item.actuacion, inspector_id):
                continue
        if distrito_id is not None:
            dist_val = {
                "efectivo": row.distrito_id_efectivo,
                "actuacion": row.distrito_id_actuacion,
                "iniciador": row.distrito_id_iniciador,
            }.get(distrito_modo, row.distrito_id_efectivo)
            if dist_val != distrito_id:
                continue
        rows.append(row)
    return rows


@dataclass
class OperAnalyticsBaselineMetrics:
    """Métricas agregadas del golden dataset."""

    total_intentos: int = 0
    total_realizados: int = 0
    total_no_realizados: int = 0
    con_geocode_ok: int = 0
    sin_geocode_ok: int = 0
    realizados_con_geo: int = 0
    realizados_sin_geo: int = 0
    no_realizados_con_geo: int = 0
    no_realizados_sin_geo: int = 0
    por_origen: dict[str, dict[str, int]] = field(default_factory=dict)
    por_subtipo_oficio: dict[str, dict[str, int]] = field(default_factory=dict)
    actas_inspeccion: int = 0
    actas_notificacion: int = 0
    actas_comprobacion: int = 0
    actas_clausura: int = 0
    actas_decomiso: int = 0
    total_actas_labradas: int = 0
    kg_realizados: float = 0.0
    kg_no_realizados: float = 0.0
    verificar_informar: dict[str, int] = field(default_factory=dict)
    difiere_fecha_ruta_ejecucion: int = 0
    difiere_fecha_ruta_actuacion: int = 0
    distrito_discrepante: int = 0
    no_realizados_dibujables: list[int] = field(default_factory=list)
    sin_geo: list[dict[str, Any]] = field(default_factory=list)


def compute_baseline_metrics(rows: list[OperAnalyticsIntentoRow]) -> OperAnalyticsBaselineMetrics:
    """
    Agrega métricas del dataset plano.

    Parámetros:
        rows: salida de ``fetch_golden_dataset``.

    Retorno:
        Contadores y listas diagnósticas.
    """
    m = OperAnalyticsBaselineMetrics()
    origenes = ("RELEVAMIENTO", "DENUNCIA", "REINSPECCION_NOTIFICACION", "OFICIO", "OTRO")

    def _bucket_origen(key: str) -> dict[str, int]:
        if key not in m.por_origen:
            m.por_origen[key] = {
                "total": 0,
                "realizados": 0,
                "no_realizados": 0,
                "con_geo": 0,
                "sin_geo": 0,
            }
        return m.por_origen[key]

    for o in origenes:
        _bucket_origen(o)

    for row in rows:
        m.total_intentos += 1
        es_real = row.estado_ejecucion == "REALIZADO"
        es_no = row.estado_ejecucion == "NO_REALIZADO"
        if es_real:
            m.total_realizados += 1
        if es_no:
            m.total_no_realizados += 1
        if row.tiene_geocode_ok:
            m.con_geocode_ok += 1
        else:
            m.sin_geocode_ok += 1
            m.sin_geo.append(
                {
                    "ruta_item_id": row.ruta_item_id,
                    "numero_orden_trabajo": row.numero_orden_trabajo,
                    "fecha_ruta": row.fecha_ruta.isoformat(),
                    "origen": row.origen_operativo_normalizado,
                    "estado_ejecucion": row.estado_ejecucion,
                    "domicilio_efectivo": row.domicilio_id_efectivo,
                    "sin_geocode_registro": row.sin_geocode_registro,
                    "geo_status_distinto_ok": row.geo_status_distinto_ok,
                    "lat_lng_null": row.lat_lng_null,
                }
            )
        if es_real and row.tiene_geocode_ok:
            m.realizados_con_geo += 1
        if es_real and not row.tiene_geocode_ok:
            m.realizados_sin_geo += 1
        if es_no and row.tiene_geocode_ok:
            m.no_realizados_con_geo += 1
            m.no_realizados_dibujables.append(row.ruta_item_id)
        if es_no and not row.tiene_geocode_ok:
            m.no_realizados_sin_geo += 1

        bo = _bucket_origen(row.origen_operativo_normalizado)
        bo["total"] += 1
        if es_real:
            bo["realizados"] += 1
        if es_no:
            bo["no_realizados"] += 1
        if row.tiene_geocode_ok:
            bo["con_geo"] += 1
        else:
            bo["sin_geo"] += 1

        if row.origen_operativo_normalizado == "OFICIO" and row.subtipo_oficio:
            st = row.subtipo_oficio
            if st not in m.por_subtipo_oficio:
                m.por_subtipo_oficio[st] = {
                    "total": 0,
                    "realizados": 0,
                    "no_realizados": 0,
                    "con_geo": 0,
                    "sin_geo": 0,
                }
            sb = m.por_subtipo_oficio[st]
            sb["total"] += 1
            if es_real:
                sb["realizados"] += 1
            if es_no:
                sb["no_realizados"] += 1
            if row.tiene_geocode_ok:
                sb["con_geo"] += 1
            else:
                sb["sin_geo"] += 1

        if es_real:
            if row.acta_inspeccion:
                m.actas_inspeccion += 1
            if row.acta_notificacion:
                m.actas_notificacion += 1
            if row.acta_comprobacion:
                m.actas_comprobacion += 1
            if row.acta_clausura:
                m.actas_clausura += 1
            if row.acta_decomiso:
                m.actas_decomiso += 1
            m.kg_realizados += row.kg_decomisados
        else:
            m.kg_no_realizados += row.kg_decomisados

        if row.subtipo_oficio == "VERIFICAR_INFORMAR_OFICIO":
            if es_no and not is_contraproducencia_excluida_valor(row.contraproducencia):
                key = "A_no_realizado_contra"
            elif es_real and row.realizo_nueva_inspeccion is True:
                key = "C_realizado_con_inspeccion"
            elif es_real and row.realizo_nueva_inspeccion is False:
                key = "B_realizado_sin_inspeccion"
            else:
                key = "D_inconsistente_null"
            m.verificar_informar[key] = m.verificar_informar.get(key, 0) + 1

        if row.difiere_fecha_ruta_ejecucion:
            m.difiere_fecha_ruta_ejecucion += 1
        if row.difiere_fecha_ruta_actuacion:
            m.difiere_fecha_ruta_actuacion += 1
        if row.distrito_discrepante:
            m.distrito_discrepante += 1

    m.total_actas_labradas = (
        m.actas_inspeccion
        + m.actas_notificacion
        + m.actas_comprobacion
        + m.actas_clausura
        + m.actas_decomiso
    )
    return m


@dataclass
class KpiComparisonRow:
    """Comparación baseline vs endpoint productivo."""

    kpi: str
    baseline: int | float
    endpoint: int | float
    diferencia: int | float
    ids_responsables: list[int] = field(default_factory=list)


def compare_dashboard(
    desde: date,
    hasta: date,
    rows: list[OperAnalyticsIntentoRow],
    *,
    distrito_id: int | None = None,
    inspector_id: int | None = None,
) -> list[KpiComparisonRow]:
    """
    Compara KPIs del dashboard activo contra el golden dataset.

    Parámetros:
        desde, hasta, distrito_id, inspector_id: mismos filtros que indicadores.
        rows: dataset ya filtrado (idealmente con mismos filtros).

    Retorno:
        Tabla de diferencias por KPI.
    """
    realizados_rows = [r for r in rows if r.estado_ejecucion == "REALIZADO"]
    no_real_rows = [r for r in rows if r.estado_ejecucion == "NO_REALIZADO"]

    bl_realizados = len(realizados_rows)
    bl_no_real = len(no_real_rows)
    bl_actas = sum(r.cantidad_actas_labradas for r in realizados_rows)
    bl_kg = sum(r.kg_decomisados for r in realizados_rows)
    bl_rn = sum(
        1 for r in realizados_rows if r.origen_operativo_normalizado == "REINSPECCION_NOTIFICACION"
    )
    bl_relev = sum(1 for r in realizados_rows if r.origen_operativo_normalizado == "RELEVAMIENTO")
    bl_oficio = sum(1 for r in realizados_rows if r.origen_operativo_normalizado == "OFICIO")
    bl_rat_clau = sum(
        1 for r in realizados_rows if r.subtipo_oficio == "RATIFICACION_CLAUSURA_OFICIO"
    )
    bl_rat_deco = sum(
        1 for r in realizados_rows if r.subtipo_oficio == "RATIFICACION_DECOMISO_OFICIO"
    )
    bl_verif = sum(1 for r in realizados_rows if r.subtipo_oficio == "VERIFICAR_INFORMAR_OFICIO")

    ej = build_indicadores_ejecutivo(desde, hasta, distrito_id, inspector_id)
    por_tipo = visitas_realizadas_por_tipo_iniciador(desde, hasta, distrito_id, inspector_id)
    no_real_ep = len(fetch_no_realizadas_visita_rows(desde, hasta, distrito_id, inspector_id))

    ep_realizados = ej.kpis.actuaciones_realizadas
    ep_actas = ej.kpis.actas_labradas
    ep_kg = ej.kpis.mercaderia_decomisada_kg
    ep_rn = ej.kpis.reinspecciones_notificacion_realizadas
    ep_relev = ej.kpis.inspecciones_realizadas
    ep_oficio = ej.kpis.reinspecciones_oficio_realizadas
    ep_rat_clau = ej.kpis.ratificaciones_clausura_realizadas
    ep_rat_deco = ej.kpis.ratificaciones_decomiso_realizadas
    ep_verif = ej.kpis.verificar_informar_realizadas

    def _diff(kpi: str, bl: int | float, ep: int | float, ids: list[int] | None = None):
        return KpiComparisonRow(
            kpi=kpi,
            baseline=bl,
            endpoint=ep,
            diferencia=bl - ep,
            ids_responsables=ids or [],
        )

    realizados_ids = [r.ruta_item_id for r in realizados_rows]
    no_real_ids = [r.ruta_item_id for r in no_real_rows]

    return [
        _diff("actuaciones_realizadas", bl_realizados, ep_realizados, realizados_ids),
        _diff("no_realizadas", bl_no_real, no_real_ep, no_real_ids),
        _diff("actas_labradas", bl_actas, ep_actas),
        _diff("kg_decomisados", bl_kg, ep_kg),
        _diff("reinspecciones_notificacion", bl_rn, ep_rn),
        _diff("inspecciones_relevamiento", bl_relev, ep_relev),
        _diff("reinspecciones_oficio_total", bl_oficio, ep_oficio),
        _diff("ratificacion_clausura", bl_rat_clau, ep_rat_clau),
        _diff("ratificacion_decomiso", bl_rat_deco, ep_rat_deco),
        _diff("verificar_informar", bl_verif, ep_verif),
    ]


@dataclass
class MapaComparisonResult:
    """Comparación baseline mapa vs ``list_mapa_operativo_realizados_geo``."""

    baseline_ids: list[int]
    mapa_ids: list[int]
    interseccion: list[int]
    solo_baseline: list[int]
    solo_mapa: list[int]
    explicacion_fecha_ids: list[int]


def compare_mapa(
    desde: date,
    hasta: date,
    rows: list[OperAnalyticsIntentoRow],
    *,
    distrito_id: int | None = None,
    inspector_id: int | None = None,
) -> MapaComparisonResult:
    """
    Compara realizados dibujables (baseline) contra puntos del mapa productivo.

    Baseline mapa esperado: REALIZADO + geo OK (domicilio efectivo) + ``fecha_ruta`` en rango.
    Mapa productivo: misma regla (período ``RutaTrabajo.fecha`` desde OPER-ANALYTICS.3).
    """
    bl_mapa = {
        r.ruta_item_id
        for r in rows
        if r.estado_ejecucion == "REALIZADO"
        and r.dibujable_en_mapa
        and desde <= r.fecha_ruta <= hasta
    }
    puntos = list_mapa_operativo_realizados_geo(
        desde=desde.isoformat(),
        hasta=hasta.isoformat(),
        distrito_id=distrito_id,
        inspector_id=inspector_id,
    )
    mapa_ids = {int(p["ruta_item_id"]) for p in puntos if p.get("ruta_item_id") is not None}

    inter = sorted(bl_mapa & mapa_ids)
    solo_bl = sorted(bl_mapa - mapa_ids)
    solo_map = sorted(mapa_ids - bl_mapa)

    explicacion_fecha: list[int] = []
    for rid in solo_bl + solo_map:
        row = next((r for r in rows if r.ruta_item_id == rid), None)
        if not row or not row.difiere_fecha_ruta_ejecucion:
            continue
        fecha_mapa = row.fecha_ejecutado_date or row.fecha_ruta
        en_rango_ruta = desde <= row.fecha_ruta <= hasta
        en_rango_mapa = desde <= fecha_mapa <= hasta
        if en_rango_ruta != en_rango_mapa:
            explicacion_fecha.append(rid)

    return MapaComparisonResult(
        baseline_ids=sorted(bl_mapa),
        mapa_ids=sorted(mapa_ids),
        interseccion=inter,
        solo_baseline=solo_bl,
        solo_mapa=solo_map,
        explicacion_fecha_ids=sorted(set(explicacion_fecha)),
    )


def format_baseline_report(
    metrics: OperAnalyticsBaselineMetrics,
    *,
    dashboard: list[KpiComparisonRow] | None = None,
    mapa: MapaComparisonResult | None = None,
) -> str:
    """
    Formatea reporte legible para consola o logs.

    Parámetros:
        metrics: métricas agregadas.
        dashboard: comparación opcional con indicadores.
        mapa: comparación opcional con mapa.

    Retorno:
        Texto multilínea.
    """
    lines: list[str] = []
    lines.append("=== OPER-ANALYTICS GOLDEN BASELINE ===")
    lines.append(f"Total intentos cerrados: {metrics.total_intentos}")
    lines.append(f"  REALIZADOS: {metrics.total_realizados}")
    lines.append(f"  NO_REALIZADOS: {metrics.total_no_realizados}")
    lines.append(f"Con geocode OK: {metrics.con_geocode_ok}")
    lines.append(f"Sin geocode OK: {metrics.sin_geocode_ok}")
    lines.append(
        f"  REALIZADOS con/sin geo: {metrics.realizados_con_geo}/{metrics.realizados_sin_geo}"
    )
    lines.append(
        f"  NO_REALIZADOS con/sin geo: {metrics.no_realizados_con_geo}/{metrics.no_realizados_sin_geo}"
    )
    lines.append("")
    lines.append("Por origen:")
    for origen, data in sorted(metrics.por_origen.items()):
        if data["total"] == 0:
            continue
        lines.append(
            f"  {origen}: total={data['total']} real={data['realizados']} "
            f"no_real={data['no_realizados']} geo={data['con_geo']}/{data['sin_geo']}"
        )
    if metrics.por_subtipo_oficio:
        lines.append("")
        lines.append("Oficio (subtipos):")
        for st, data in sorted(metrics.por_subtipo_oficio.items()):
            lines.append(
                f"  {st}: total={data['total']} real={data['realizados']} "
                f"no_real={data['no_realizados']}"
            )
    lines.append("")
    lines.append(
        f"Actas (REALIZADOS): insp={metrics.actas_inspeccion} notif={metrics.actas_notificacion} "
        f"comp={metrics.actas_comprobacion} clau={metrics.actas_clausura} "
        f"deco={metrics.actas_decomiso} total={metrics.total_actas_labradas}"
    )
    lines.append(f"Kg REALIZADOS: {metrics.kg_realizados:.2f} | NO_REALIZADOS: {metrics.kg_no_realizados:.2f}")
    lines.append(
        f"Discrepancias fecha: ruta!=ejecucion={metrics.difiere_fecha_ruta_ejecucion} "
        f"ruta!=actuacion={metrics.difiere_fecha_ruta_actuacion} "
        f"distrito discrepante={metrics.distrito_discrepante}"
    )
    if metrics.verificar_informar:
        lines.append(f"Verificar e informar: {metrics.verificar_informar}")
    lines.append(f"NO_REALIZADOS dibujables (futuro mapa): {len(metrics.no_realizados_dibujables)}")
    if dashboard:
        lines.append("")
        lines.append("=== COMPARACIÓN DASHBOARD ===")
        for row in dashboard:
            flag = " OK" if row.diferencia == 0 else " DIFF"
            lines.append(
                f"  {row.kpi}: baseline={row.baseline} endpoint={row.endpoint} "
                f"diff={row.diferencia}{flag}"
            )
            if row.diferencia != 0 and row.ids_responsables:
                lines.append(f"    ids: {row.ids_responsables[:20]}")
    if mapa:
        lines.append("")
        lines.append("=== COMPARACIÓN MAPA ===")
        lines.append(f"  baseline: {len(mapa.baseline_ids)} | mapa: {len(mapa.mapa_ids)}")
        lines.append(f"  intersección: {len(mapa.interseccion)}")
        lines.append(f"  solo_baseline: {mapa.solo_baseline[:30]}")
        lines.append(f"  solo_mapa: {mapa.solo_mapa[:30]}")
        if mapa.explicacion_fecha_ids:
            lines.append(f"  explicables por fecha: {mapa.explicacion_fecha_ids[:30]}")
    return "\n".join(lines)
