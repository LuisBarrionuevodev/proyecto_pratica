"""
Queries compartidas para indicadores basados en cierres operativos de ``RutaItem``.

Criterio canónico «realizada» (dashboard D1d.11fix-a / D1d.11fix-a4):
- ``RutaTrabajo.estado_ruta == PUBLICADA``
- ``RutaTrabajo.fecha`` en rango del período (día operativo de la ruta)
- ``RutaItem.estado_ruta_item == FINALIZADO``
- ``RutaItem.estado_ejecucion == REALIZADO``
- ``RutaItem.actuacion_id IS NOT NULL``

``ejecutado_at`` es auditoría de cierre real; no define el mes del Dashboard.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import aliased

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    _loose_key,
)
from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    _realizados_inspector_coincide,
)
from app.models import Actuaciones, Domicilio, IniciadorRuta, Rubro, RutaItem, RutaTrabajo

# Buckets operativos canónicos (D1d.11fix-a3).
BUCKET_REINSPECCION_OFICIO = "REINSPECCION_OFICIO"
BUCKET_RATIFICACION_CLAUSURA = "RATIFICACION_CLAUSURA"
BUCKET_RATIFICACION_DECOMISO = "RATIFICACION_DECOMISO"
BUCKET_VERIFICAR_INFORMAR = "VERIFICAR_INFORMAR"
BUCKET_REINSPECCION_NOTIFICACION = "REINSPECCION_NOTIFICACION"
BUCKET_DENUNCIA = "DENUNCIA"
BUCKET_RELEVAMIENTO = "RELEVAMIENTO"
BUCKET_OTRO = "OTRO"

# Tipos de iniciador con visita realizada (oficio / reinspección / ratificaciones).
TIPOS_INICIADOR_VISITA_REALIZADA: tuple[str, ...] = (
    "REINSPECCION_NOTIFICACION",
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)

# Universo «oficio realizado»: todos los buckets híbridos del circuito oficio.
TIPOS_INICIADOR_OFICIO_REALIZADA: tuple[str, ...] = (
    "REINSPECCION_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
)

# Clave de bucket → clave enum usada por ejecutivo/resumen (contrato interno sin cambiar Pydantic).
_BUCKET_TO_INICIADOR_KEY: dict[str, str] = {
    BUCKET_RATIFICACION_CLAUSURA: "RATIFICACION_CLAUSURA_OFICIO",
    BUCKET_RATIFICACION_DECOMISO: "RATIFICACION_DECOMISO_OFICIO",
    BUCKET_VERIFICAR_INFORMAR: "VERIFICAR_INFORMAR_OFICIO",
    BUCKET_REINSPECCION_OFICIO: "REINSPECCION_OFICIO",
    BUCKET_REINSPECCION_NOTIFICACION: "REINSPECCION_NOTIFICACION",
}

# Alias normalizados (loose key) → valor canónico del enum en BD.
_TIPO_INICIADOR_CANONICAL_BY_LOOSE: dict[str, str] = {
    _loose_key("RELEVAMIENTO"): "RELEVAMIENTO",
    _loose_key("DENUNCIA"): "DENUNCIA",
    _loose_key("REINSPECCION_OFICIO"): "REINSPECCION_OFICIO",
    _loose_key("REINSPECCION OFICIO"): "REINSPECCION_OFICIO",
    _loose_key("REINSPECCION_NOTIFICACION"): "REINSPECCION_NOTIFICACION",
    _loose_key("REINSPECCION NOTIFICACION"): "REINSPECCION_NOTIFICACION",
    _loose_key("VERIFICAR_INFORMAR_OFICIO"): "VERIFICAR_INFORMAR_OFICIO",
    _loose_key("VERIFICAR E INFORMAR"): "VERIFICAR_INFORMAR_OFICIO",
    _loose_key("VERIFICAR E INFORMAR OFICIO"): "VERIFICAR_INFORMAR_OFICIO",
    _loose_key("RATIFICACION_CLAUSURA_OFICIO"): "RATIFICACION_CLAUSURA_OFICIO",
    _loose_key("RATIFICACION CLAUSURA OFICIO"): "RATIFICACION_CLAUSURA_OFICIO",
    _loose_key("RATIFICACION DE CLAUSURA"): "RATIFICACION_CLAUSURA_OFICIO",
    _loose_key("RATIFICACION CLAUSURA"): "RATIFICACION_CLAUSURA_OFICIO",
    _loose_key("RATIFICACION_DECOMISO_OFICIO"): "RATIFICACION_DECOMISO_OFICIO",
    _loose_key("RATIFICACION DECOMISO OFICIO"): "RATIFICACION_DECOMISO_OFICIO",
    _loose_key("RATIFICACION DE DECOMISO"): "RATIFICACION_DECOMISO_OFICIO",
    _loose_key("RATIFICACION DECOMISO"): "RATIFICACION_DECOMISO_OFICIO",
    _loose_key("RATIFICACION DECOMISO OFICIO"): "RATIFICACION_DECOMISO_OFICIO",
}


def _fecha_periodo_operativo_expr():
    """Período del Dashboard: fecha operativa de la ruta publicada."""
    return RutaTrabajo.fecha


def _fecha_cierre_ruta_expr():
    """
    Alias de período operativo (D1d.11fix-a4).

    Retorna ``RutaTrabajo.fecha``, no ``ejecutado_at``.
    """
    return _fecha_periodo_operativo_expr()


def _fecha_ejecutado_auditoria_expr():
    """Auditoría: cuándo se cerró el ítem (no usar como período del Dashboard)."""
    return func.coalesce(func.date(RutaItem.ejecutado_at), RutaTrabajo.fecha)


def domicilio_id_efectivo_expr():
    """Domicilio operativo: actuación, o iniciador si la actuación no tiene domicilio."""
    return func.coalesce(Actuaciones.domicilio_id, IniciadorRuta.domicilio_id)


def loose_key_tipo_operativo(value: str | None) -> str:
    """
    Normaliza tipo de iniciador/actuación para comparación flexible.

    Quita acentos, pasa a minúsculas, unifica separadores y espacios.
    """
    if value is None:
        return ""
    s = str(value).strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    s = s.replace("_", " ").replace("-", " ").replace("/", " ")
    return " ".join(s.lower().split())


def _subtipo_desde_actuacion_tipo(actuacion_tipo: str | None) -> str | None:
    """
    Detecta subtipo oficio en ``actuaciones.tipo`` (ratificación / verificar / reinspección genérica).

    Retorno:
        ``RATIFICACION_CLAUSURA``, ``RATIFICACION_DECOMISO``, ``VERIFICAR_INFORMAR``,
        ``REINSPECCION_GENERICO`` o ``None``.
    """
    loose = loose_key_tipo_operativo(actuacion_tipo)
    if not loose:
        return None
    if "ratificacion" in loose and "clausura" in loose:
        return BUCKET_RATIFICACION_CLAUSURA
    if "ratificacion" in loose and "decomiso" in loose:
        return BUCKET_RATIFICACION_DECOMISO
    if "verificar" in loose and "informar" in loose:
        return BUCKET_VERIFICAR_INFORMAR
    if loose == "reinspeccion":
        return BUCKET_REINSPECCION_OFICIO
    return None


def bucket_operativo(
    tipo_iniciador: str | None,
    actuacion_tipo: str | None,
) -> str:
    """
    Clasificación híbrida iniciador + tipo de actuación para cierres realizados.

    Reglas (D1d.11fix-a3):
    - Enum directo en iniciador (``RATIFICACION_*_OFICIO``, ``VERIFICAR_*``) cuenta como subtipo.
    - ``REINSPECCION_OFICIO`` + ``actuaciones.tipo`` concreto desglosa ratificación/verificar.
    - ``REINSPECCION_OFICIO`` sin subtipo reconocido queda como oficio genérico.

    Parámetros:
        tipo_iniciador: ``IniciadorRuta.tipo_iniciador``.
        actuacion_tipo: ``Actuaciones.tipo`` (puede ser None).

    Retorno:
        Bucket canónico (``REINSPECCION_OFICIO``, ``RATIFICACION_CLAUSURA``, etc.).
    """
    ini = canonical_tipo_iniciador(tipo_iniciador)

    if ini == "RATIFICACION_CLAUSURA_OFICIO":
        return BUCKET_RATIFICACION_CLAUSURA
    if ini == "RATIFICACION_DECOMISO_OFICIO":
        return BUCKET_RATIFICACION_DECOMISO
    if ini == "VERIFICAR_INFORMAR_OFICIO":
        return BUCKET_VERIFICAR_INFORMAR

    sub_act = _subtipo_desde_actuacion_tipo(actuacion_tipo)

    if ini == "REINSPECCION_OFICIO":
        if sub_act in (
            BUCKET_RATIFICACION_CLAUSURA,
            BUCKET_RATIFICACION_DECOMISO,
            BUCKET_VERIFICAR_INFORMAR,
        ):
            return sub_act
        return BUCKET_REINSPECCION_OFICIO

    if ini == "REINSPECCION_NOTIFICACION":
        return BUCKET_REINSPECCION_NOTIFICACION
    if ini == "DENUNCIA":
        return BUCKET_DENUNCIA
    if ini == "RELEVAMIENTO":
        return BUCKET_RELEVAMIENTO
    return BUCKET_OTRO


def bucket_a_clave_iniciador(bucket: str) -> str:
    """Mapea bucket operativo a clave enum usada por KPIs ejecutivos existentes."""
    return _BUCKET_TO_INICIADOR_KEY.get(bucket, bucket)


def sum_visitas_oficio_realizadas(por_tipo_ini: dict[str, int]) -> int:
    """
    Suma visitas realizadas del circuito oficio (sin reinspección por notificación).

    Usa el dict de ``visitas_realizadas_por_tipo_iniciador``; cada cierre cuenta una vez
    en su bucket híbrido (genérico, ratificación clausura/decomiso o verificar e informar).
    """
    return sum(por_tipo_ini.get(k, 0) for k in TIPOS_INICIADOR_OFICIO_REALIZADA)


def canonical_tipo_iniciador(value: str | None) -> str | None:
    """
    Mapea un valor crudo de ``tipo_iniciador`` al enum canónico de BD.

    Retorna ``None`` si no se reconoce.
    """
    if not value:
        return None
    raw = str(value).strip()
    if raw in _TIPO_INICIADOR_CANONICAL_BY_LOOSE.values():
        return raw
    key = _loose_key(raw)
    if key in _TIPO_INICIADOR_CANONICAL_BY_LOOSE:
        return _TIPO_INICIADOR_CANONICAL_BY_LOOSE[key]
    loose = loose_key_tipo_operativo(raw)
    for alias, canonical in _TIPO_INICIADOR_CANONICAL_BY_LOOSE.items():
        if loose_key_tipo_operativo(alias) == loose:
            return canonical
    return None


def _apply_filtros_cierre(
    q,
    *,
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    tipos_iniciador: Optional[tuple[str, ...]] = None,
):
    """Aplica filtros de período operativo, distrito e inspector sobre RutaItem REALIZADO."""
    fecha_periodo = _fecha_periodo_operativo_expr()
    q = q.filter(
        RutaItem.deleted_at.is_(None),
        IniciadorRuta.deleted_at.is_(None),
        RutaItem.actuacion_id.isnot(None),
        RutaItem.estado_ruta_item == "FINALIZADO",
        RutaItem.estado_ejecucion == "REALIZADO",
        RutaTrabajo.estado_ruta == "PUBLICADA",
        fecha_periodo >= desde,
        fecha_periodo <= hasta,
    )
    if tipos_iniciador:
        q = q.filter(IniciadorRuta.tipo_iniciador.in_(tipos_iniciador))
    if distrito_id is not None:
        dom_filtro = aliased(Domicilio)
        q = q.outerjoin(dom_filtro, dom_filtro.id == domicilio_id_efectivo_expr()).filter(
            dom_filtro.distrito_id == distrito_id,
            dom_filtro.deleted_at.is_(None),
        )
    if inspector_id is not None:
        q = q.filter(_realizados_inspector_coincide(inspector_id))
    return q


def _base_cierres_realizados_query(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    tipos_iniciador: Optional[tuple[str, ...]] = None,
):
    """
    Query base de cierres realizados (RutaItem + Actuación vinculada).

    Retorno:
        Query con columnas accesibles vía ``RutaItem``, ``Actuaciones``, ``IniciadorRuta``.
    """
    q = (
        db.session.query(RutaItem)
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
    )
    return _apply_filtros_cierre(
        q,
        desde=desde,
        hasta=hasta,
        distrito_id=distrito_id,
        inspector_id=inspector_id,
        tipos_iniciador=tipos_iniciador,
    )


def actuacion_ids_realizadas_subquery(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    tipos_iniciador: Optional[tuple[str, ...]] = None,
):
    """
    Subquery de ``actuaciones.id`` con cierre REALIZADO en rutas del período operativo.

    Período: ``RutaTrabajo.fecha`` en rango. Fuente canónica para Ejecutivo, Riesgo y productividad.
    """
    q = (
        db.session.query(Actuaciones.id)
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
    )
    q = _apply_filtros_cierre(
        q,
        desde=desde,
        hasta=hasta,
        distrito_id=distrito_id,
        inspector_id=inspector_id,
        tipos_iniciador=tipos_iniciador,
    )
    return q.distinct().subquery("act_realizadas_cierre")


def count_cierres_realizados(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    tipos_iniciador: Optional[tuple[str, ...]] = None,
) -> int:
    """Cuenta ítems de ruta cerrados como REALIZADO (sin exigir geocode)."""
    q = _base_cierres_realizados_query(
        desde, hasta, distrito_id, inspector_id, tipos_iniciador=tipos_iniciador
    )
    return int(q.with_entities(func.count(func.distinct(RutaItem.id))).scalar() or 0)


def visitas_realizadas_por_tipo_iniciador(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> dict[str, int]:
    """
    Cuenta visitas realizadas por bucket híbrido (iniciador + ``actuaciones.tipo``).

    Retorna claves enum compatibles con ejecutivo (``RATIFICACION_CLAUSURA_OFICIO``, etc.).
    ``REINSPECCION_OFICIO`` solo incluye oficio genérico (excluye ratificación/verificar).
    """
    q = (
        db.session.query(
            IniciadorRuta.tipo_iniciador,
            Actuaciones.tipo,
            func.count(func.distinct(RutaItem.id)),
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
    )
    q = _apply_filtros_cierre(
        q,
        desde=desde,
        hasta=hasta,
        distrito_id=distrito_id,
        inspector_id=inspector_id,
    )
    rows = q.group_by(IniciadorRuta.tipo_iniciador, Actuaciones.tipo).all()

    allowed = frozenset(TIPOS_INICIADOR_VISITA_REALIZADA)
    merged: dict[str, int] = defaultdict(int)
    for ini_tipo, act_tipo, cnt in rows:
        bucket = bucket_operativo(
            str(ini_tipo) if ini_tipo is not None else None,
            str(act_tipo) if act_tipo is not None else None,
        )
        key = bucket_a_clave_iniciador(bucket)
        if key not in allowed:
            continue
        merged[key] += int(cnt)
    return dict(merged)


def query_top_rubros_cierres_realizados(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    limit: int = 10,
) -> list[tuple[int, str, int]]:
    """
    Top rubros por cierres realizados con domicilio efectivo (actuación o iniciador).

    Retorno:
        Lista de (rubro_id, nombre, count) por ``RutaItem`` distinto.
    """
    dom_eff = domicilio_id_efectivo_expr()
    dom_rubro = aliased(Domicilio)
    q = _base_cierres_realizados_query(desde, hasta, distrito_id, inspector_id)
    rows = (
        q.with_entities(
            Rubro.id,
            Rubro.nombre,
            func.count(func.distinct(RutaItem.id)),
        )
        .outerjoin(dom_rubro, dom_rubro.id == dom_eff)
        .join(Rubro, Rubro.id == dom_rubro.rubro_id)
        .group_by(Rubro.id, Rubro.nombre)
        .order_by(func.count(func.distinct(RutaItem.id)).desc())
        .limit(limit)
        .all()
    )
    return [(int(rid), str(nombre), int(cnt)) for rid, nombre, cnt in rows]
