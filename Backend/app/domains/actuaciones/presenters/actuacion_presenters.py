"""
Presentación de actuaciones hacia grilla / bandejas.

F2.2 — contexto documental (solo lectura):
- `documentacion_contexto.circuito` clasifica la fila (común notificación / común comprobación /
  reinspección por oficio o notificación, o desconocido).
- `documentacion_contexto.propia` = trámite de **esta** actuación según el circuito.
- `origen_reinspeccion_*` = datos de origen cuando el trabajo nace de un `IniciadorRuta` vinculado
  por `RutaItem.actuacion_id` (sin inventar origen si no hay ítem de ruta).

Campos planos históricos (compatibilidad exportación / clientes viejos):
- En **común comprobación**: `expediente_*` = envío de la comprobación actual; `oficio_*` = null
  aunque exista oficio en BD (el oficio de seguimiento no se mezcla en la vista de actas).
- En **común notificación**: `expediente_*` = primer expediente asociado a la notificación actual;
  `oficio_*` = null.
- En **reinspección** (oficio / notificación): `expediente_*` / `oficio_*` reflejan solo la parte
  propia de la visita actual; el origen va en `origen_reinspeccion_*`.

`notificacion_previa_num` / `comprobacion_previa_num` quedan reservados en null (no usar el acta
actual como “previa”).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional, List

from sqlalchemy.orm import joinedload

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
from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
    puede_editar_domicilio_actuacion,
)
from app.domains.domicilios.utils.domicilio_calle_ui import (
    calle_cargada_desde_domicilio,
    esquina_cargada_desde_domicilio,
    esquina_key_desde_domicilio,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    count_actuaciones_por_establecimiento_operativo_ids,
)
from app.models import Actuaciones, Comprobacion, Expediente, IniciadorRuta, Notificacion, Oficio, Relevamiento, RutaItem
from app.domains.rutas_trabajo.utils.rubro_operativo import rubro_nombre_operativo_para_iniciador
from app.shared.utils.business_days_ar import contar_dias_habiles_inclusive

logger = logging.getLogger(__name__)

_TIPOS_INICIADOR_ORIGEN_OFICIO_UI = frozenset(
    {
        "REINSPECCION_OFICIO",
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    }
)


@dataclass(frozen=True)
class ActuacionGridBatchMaps:
    """
    Mapas precargados para armar contexto documental sin N+1 en listados.

    Parámetros:
        expediente_envio_by_comp_id: expediente de envío (`oficio_id` NULL) por comprobación.
        expediente_primero_by_notif_id: primer expediente no borrado por notificación (id mínimo).
        expediente_respuesta_by_pair: expediente `RESPUESTA_OFICIO` por (comprobacion_id, oficio_id).
        comprobacion_by_id: filas `Comprobacion` por id.
        oficio_by_id: filas `Oficio` por id.
        notificacion_by_id: filas `Notificacion` por id.
    """

    expediente_envio_by_comp_id: dict[int, Optional[Expediente]]
    expediente_primero_by_notif_id: dict[int, Optional[Expediente]]
    expediente_respuesta_by_pair: dict[tuple[int, int], Optional[Expediente]]
    comprobacion_by_id: dict[int, Comprobacion]
    oficio_by_id: dict[int, Oficio]
    notificacion_by_id: dict[int, Notificacion]


def _domicilio_edit_flags_for_grid(
    act: Actuaciones,
    ini_ruta: Optional[IniciadorRuta],
) -> dict[str, Any]:
    """Flags PR7.15 para habilitar/bloquear edición de domicilio en CRUD Actuaciones."""
    puede, motivo = puede_editar_domicilio_actuacion(act, ini_ruta)
    return {
        "can_edit_domicilio": puede,
        "domicilio_edit_blocked_reason": motivo,
    }


def build_iniciador_ruta_por_actuacion_id(act_ids: list[int]) -> dict[int, Optional[IniciadorRuta]]:
    """
    Resuelve el iniciador operativo vinculado a cada actuación publicada en ruta.

    Regla:
    - Se usa `RutaItem.actuacion_id` → `iniciador_ruta` (no `IniciadorRuta.actuacion_id`, que en
      oficio/notificación vencida apunta a la actuación **base** histórica).

    Parámetros:
        act_ids: ids de actuaciones del page.

    Retorno:
        Mapa actuacion_id → iniciador o None si no hay ítem de ruta o está borrado.
    """
    if not act_ids:
        return {}
    base: dict[int, Optional[IniciadorRuta]] = {int(i): None for i in act_ids}
    rows = (
        RutaItem.query.filter(
            RutaItem.actuacion_id.in_(act_ids),
            RutaItem.deleted_at.is_(None),
        )
        .options(
            joinedload(RutaItem.iniciador_ruta)
            .joinedload(IniciadorRuta.relevamiento)
            .joinedload(Relevamiento.rubro)
        )
        .order_by(RutaItem.id.asc())
        .all()
    )
    for ri in rows:
        aid = ri.actuacion_id
        if aid is None:
            continue
        key = int(aid)
        if base.get(key) is not None:
            continue
        ini = ri.iniciador_ruta
        if ini is None or ini.deleted_at is not None:
            continue
        base[key] = ini
    return base


def _iniciador_desde_ruta_item_single(act_id: int) -> Optional[IniciadorRuta]:
    """Una consulta: iniciador desde ítem de ruta para respuestas unitarias (update, quitar-acta)."""
    m = build_iniciador_ruta_por_actuacion_id([act_id])
    return m.get(act_id)


def expediente_primero_por_notificacion(notificacion_id: int) -> Optional[Expediente]:
    """
    Primer expediente no borrado vinculado a una notificación (orden estable por `id`).

    Usado para contexto documental de notificación (plazos / trámite), sin inferir desde comprobación.
    """
    return (
        Expediente.query.filter(
            Expediente.notificacion_id == notificacion_id,
            Expediente.deleted_at.is_(None),
        )
        .order_by(Expediente.id.asc())
        .first()
    )


def expediente_respuesta_oficio_por_par(comprobacion_id: int, oficio_id: int) -> Optional[Expediente]:
    """
    Expediente administrativo de respuesta de oficio para el par comprobación/oficio explícito.

    Orden: `id` descendente (más reciente).
    """
    return (
        Expediente.query.filter(
            Expediente.comprobacion_id == comprobacion_id,
            Expediente.oficio_id == oficio_id,
            Expediente.tipo_expediente == "RESPUESTA_OFICIO",
            Expediente.deleted_at.is_(None),
        )
        .order_by(Expediente.id.desc())
        .first()
    )


def _batch_expediente_envio(comp_ids: set[int]) -> dict[int, Optional[Expediente]]:
    if not comp_ids:
        return {}
    out: dict[int, Optional[Expediente]] = {int(c): None for c in comp_ids}
    rows = (
        Expediente.query.filter(
            Expediente.comprobacion_id.in_(comp_ids),
            Expediente.oficio_id.is_(None),
            Expediente.deleted_at.is_(None),
        )
        .order_by(Expediente.comprobacion_id.asc(), Expediente.id.asc())
        .all()
    )
    for r in rows:
        cid = r.comprobacion_id
        if cid is None:
            continue
        key = int(cid)
        if out.get(key) is None:
            out[key] = r
    return out


def _batch_expediente_primero_notif(notif_ids: set[int]) -> dict[int, Optional[Expediente]]:
    if not notif_ids:
        return {}
    out: dict[int, Optional[Expediente]] = {int(n): None for n in notif_ids}
    rows = (
        Expediente.query.filter(
            Expediente.notificacion_id.in_(notif_ids),
            Expediente.deleted_at.is_(None),
        )
        .order_by(Expediente.notificacion_id.asc(), Expediente.id.asc())
        .all()
    )
    for r in rows:
        nid = r.notificacion_id
        if nid is None:
            continue
        key = int(nid)
        if out.get(key) is None:
            out[key] = r
    return out


def _batch_expediente_respuesta_pairs(pairs: set[tuple[int, int]]) -> dict[tuple[int, int], Optional[Expediente]]:
    if not pairs:
        return {}
    comp_ids = {p[0] for p in pairs}
    ofi_ids = {p[1] for p in pairs}
    out: dict[tuple[int, int], Optional[Expediente]] = {p: None for p in pairs}
    rows = (
        Expediente.query.filter(
            Expediente.comprobacion_id.in_(comp_ids),
            Expediente.oficio_id.in_(ofi_ids),
            Expediente.tipo_expediente == "RESPUESTA_OFICIO",
            Expediente.deleted_at.is_(None),
        )
        .order_by(Expediente.id.desc())
        .all()
    )
    for r in rows:
        if r.comprobacion_id is None or r.oficio_id is None:
            continue
        key = (int(r.comprobacion_id), int(r.oficio_id))
        if key in out and out[key] is None:
            out[key] = r
    return out


def build_actuacion_grid_batch_maps(
    acts: List[Actuaciones],
    iniciador_por_actuacion_id: dict[int, Optional[IniciadorRuta]],
) -> ActuacionGridBatchMaps:
    """
    Arma mapas para `actuacion_to_grid_row` en listados (evita N+1 en expedientes / ORM).

    Parámetros:
        acts: página de actuaciones.
        iniciador_por_actuacion_id: resultado de `build_iniciador_ruta_por_actuacion_id` para esos ids.

    Retorno:
        `ActuacionGridBatchMaps` listo para pasar como `batch=` al presenter.
    """
    comp_ids: set[int] = set()
    notif_ids: set[int] = set()
    resp_pairs: set[tuple[int, int]] = set()

    for a in acts:
        if a.comprobacion_id is not None:
            comp_ids.add(int(a.comprobacion_id))
        if a.notificacion_id is not None:
            notif_ids.add(int(a.notificacion_id))

    for ini in iniciador_por_actuacion_id.values():
        if ini is None:
            continue
        if ini.comprobacion_id is not None:
            comp_ids.add(int(ini.comprobacion_id))
        if ini.notificacion_id is not None:
            notif_ids.add(int(ini.notificacion_id))
        if ini.comprobacion_id is not None and ini.oficio_id is not None:
            resp_pairs.add((int(ini.comprobacion_id), int(ini.oficio_id)))

    envio = _batch_expediente_envio(comp_ids)
    ex_not = _batch_expediente_primero_notif(notif_ids)
    ex_resp = _batch_expediente_respuesta_pairs(resp_pairs)

    comp_map: dict[int, Comprobacion] = {}
    if comp_ids:
        for c in Comprobacion.query.filter(Comprobacion.id.in_(comp_ids)).all():
            comp_map[int(c.id)] = c

    ofi_ids: set[int] = set()
    for ini in iniciador_por_actuacion_id.values():
        if ini and ini.oficio_id is not None:
            ofi_ids.add(int(ini.oficio_id))
    ofi_map: dict[int, Oficio] = {}
    if ofi_ids:
        for o in Oficio.query.filter(Oficio.id.in_(ofi_ids)).all():
            ofi_map[int(o.id)] = o

    not_map: dict[int, Notificacion] = {}
    if notif_ids:
        for n in Notificacion.query.filter(Notificacion.id.in_(notif_ids)).all():
            not_map[int(n.id)] = n

    return ActuacionGridBatchMaps(
        expediente_envio_by_comp_id=envio,
        expediente_primero_by_notif_id=ex_not,
        expediente_respuesta_by_pair=ex_resp,
        comprobacion_by_id=comp_map,
        oficio_by_id=ofi_map,
        notificacion_by_id=not_map,
    )


def _clasificar_circuito_documental(
    act: Actuaciones,
    ini: Optional[IniciadorRuta],
) -> str:
    """Retorna clave de circuito para UI (ver `documentacion_contexto.circuito`)."""
    if ini is not None and ini.tipo_iniciador == "REINSPECCION_NOTIFICACION":
        return "REINSPECCION_NOTIFICACION"
    if ini is not None and ini.tipo_iniciador in _TIPOS_INICIADOR_ORIGEN_OFICIO_UI:
        if ini.comprobacion_id is not None and ini.oficio_id is not None:
            return "REINSPECCION_OFICIO"
    if act.comprobacion_id is not None:
        return "COMUN_COMPROBACION"
    if act.notificacion_id is not None:
        return "COMUN_NOTIFICACION"
    return "DESCONOCIDO"


def _expediente_envio_resolved(
    comprobacion_id: int | None,
    batch: ActuacionGridBatchMaps | None,
) -> Optional[Expediente]:
    if comprobacion_id is None:
        return None
    cid = int(comprobacion_id)
    if batch is not None:
        return batch.expediente_envio_by_comp_id.get(cid)
    return expediente_envio_por_comprobacion(cid)


def _expediente_notif_resolved(
    notificacion_id: int | None,
    batch: ActuacionGridBatchMaps | None,
) -> Optional[Expediente]:
    if notificacion_id is None:
        return None
    nid = int(notificacion_id)
    if batch is not None:
        return batch.expediente_primero_by_notif_id.get(nid)
    return expediente_primero_por_notificacion(nid)


def _expediente_respuesta_resolved(
    comprobacion_id: int,
    oficio_id: int,
    batch: ActuacionGridBatchMaps | None,
) -> Optional[Expediente]:
    key = (int(comprobacion_id), int(oficio_id))
    if batch is not None:
        return batch.expediente_respuesta_by_pair.get(key)
    return expediente_respuesta_oficio_por_par(int(comprobacion_id), int(oficio_id))


def _comprobacion_resolved(cid: int, batch: ActuacionGridBatchMaps | None) -> Optional[Comprobacion]:
    if batch is not None:
        return batch.comprobacion_by_id.get(int(cid))
    return Comprobacion.query.get(int(cid))


def _oficio_resolved(oid: int, batch: ActuacionGridBatchMaps | None) -> Optional[Oficio]:
    if batch is not None:
        return batch.oficio_by_id.get(int(oid))
    return Oficio.query.get(int(oid))


def _notificacion_resolved(nid: int, batch: ActuacionGridBatchMaps | None) -> Optional[Notificacion]:
    if batch is not None:
        return batch.notificacion_by_id.get(int(nid))
    return Notificacion.query.get(int(nid))


def _date_iso(d: date | None) -> Optional[str]:
    return d.isoformat() if d is not None else None


def _build_origen_reinspeccion_oficio(
    ini: IniciadorRuta,
    batch: ActuacionGridBatchMaps | None,
) -> Optional[Dict[str, Any]]:
    if ini.comprobacion_id is None or ini.oficio_id is None:
        return None
    comp = _comprobacion_resolved(int(ini.comprobacion_id), batch)
    ofi = _oficio_resolved(int(ini.oficio_id), batch)
    if comp is None or ofi is None:
        return None
    exp_r = _expediente_respuesta_resolved(int(ini.comprobacion_id), int(ini.oficio_id), batch)
    return {
        "comprobacion_acta_numero": getattr(comp, "numero_acta", None),
        "comprobacion_acta_anio": getattr(comp, "anio", None),
        "expediente_numero": getattr(exp_r, "numero_expediente", None) if exp_r else None,
        "expediente_anio": getattr(exp_r, "anio", None) if exp_r else None,
        "oficio_numero": getattr(ofi, "numero_oficio", None),
        "oficio_anio": getattr(ofi, "anio", None),
        "oficio_causa": getattr(ofi, "causa", None),
    }


def _build_origen_reinspeccion_notificacion(
    ini: IniciadorRuta,
    batch: ActuacionGridBatchMaps | None,
) -> Optional[Dict[str, Any]]:
    if ini.notificacion_id is None:
        return None
    noti = _notificacion_resolved(int(ini.notificacion_id), batch)
    if noti is None:
        return None
    exp_n = _expediente_notif_resolved(int(ini.notificacion_id), batch)
    return {
        "notificacion_acta_numero": getattr(noti, "numero_acta", None),
        "notificacion_acta_anio": getattr(noti, "anio", None),
        "expediente_numero": getattr(exp_n, "numero_expediente", None) if exp_n else None,
        "expediente_anio": getattr(exp_n, "anio", None) if exp_n else None,
        "plazo_dias": getattr(noti, "plazo_dias", None),
        "prorroga_dias": getattr(noti, "prorroga_dias", None),
        "fecha_vencimiento": _date_iso(getattr(noti, "fecha_vencimiento", None)),
    }


def _propia_payload_for_circuito(
    circuito: str,
    act: Actuaciones,
    batch: ActuacionGridBatchMaps | None,
) -> Dict[str, Any]:
    """Subdocumento `documentacion_contexto.propia` (solo lectura)."""
    out: Dict[str, Any] = {
        "expediente_numero": None,
        "expediente_anio": None,
        "notificacion_plazo_dias": None,
        "notificacion_prorroga_dias": None,
        "notificacion_fecha_vencimiento": None,
    }
    if circuito in ("COMUN_NOTIFICACION", "REINSPECCION_NOTIFICACION") and act.notificacion_id is not None:
        exp_n = _expediente_notif_resolved(int(act.notificacion_id), batch)
        if exp_n:
            out["expediente_numero"] = getattr(exp_n, "numero_expediente", None)
            out["expediente_anio"] = getattr(exp_n, "anio", None)
        noti = getattr(act, "notificacion", None) or _notificacion_resolved(int(act.notificacion_id), batch)
        if noti is not None:
            out["notificacion_plazo_dias"] = getattr(noti, "plazo_dias", None)
            out["notificacion_prorroga_dias"] = getattr(noti, "prorroga_dias", None)
            out["notificacion_fecha_vencimiento"] = _date_iso(getattr(noti, "fecha_vencimiento", None))
    elif circuito == "REINSPECCION_NOTIFICACION" and act.comprobacion_id is not None:
        exp_e = _expediente_envio_resolved(int(act.comprobacion_id), batch)
        if exp_e:
            out["expediente_numero"] = getattr(exp_e, "numero_expediente", None)
            out["expediente_anio"] = getattr(exp_e, "anio", None)
    elif circuito == "COMUN_COMPROBACION" and act.comprobacion_id is not None:
        exp_e = _expediente_envio_resolved(int(act.comprobacion_id), batch)
        if exp_e:
            out["expediente_numero"] = getattr(exp_e, "numero_expediente", None)
            out["expediente_anio"] = getattr(exp_e, "anio", None)
    elif circuito == "REINSPECCION_OFICIO" and act.comprobacion_id is not None:
        exp_e = _expediente_envio_resolved(int(act.comprobacion_id), batch)
        if exp_e:
            out["expediente_numero"] = getattr(exp_e, "numero_expediente", None)
            out["expediente_anio"] = getattr(exp_e, "anio", None)
    return out


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

    Orden estable por `id` ascendente. Si hay más de un expediente activo (datos legados),
    se devuelve el de **menor id** y se registra un warning en logs para auditoría.
    """
    rows = (
        Expediente.query.filter_by(comprobacion_id=comprobacion_id, oficio_id=None)
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .limit(3)
        .all()
    )
    if len(rows) > 1:
        ids = [r.id for r in rows]
        logger.warning(
            "Varios expedientes de envío (comprobacion_id=%s, oficio_id NULL, deleted_at NULL): "
            "ids=%s (mostrando id mínimo). Revisar con expediente_envio_audit.",
            comprobacion_id,
            ids,
        )
    return rows[0] if rows else None


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


def actuacion_to_grid_row(
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
    iniciador_desde_ruta: IniciadorRuta | None = None,
    batch: ActuacionGridBatchMaps | None = None,
) -> Dict[str, Any]:
    """
    Convierte una Actuación (con relaciones) al formato plano
    que espera Material React Table.

    IMPORTANTE:
    - fecha_actuacion se entrega como YYYY-MM-DD para input type="date"
    - enum se entrega como string limpio
    - Contexto documental F2.2: `documentacion_contexto`, `origen_reinspeccion_*`; los campos planos
      `expediente_*` / `oficio_*` reflejan solo la documentación **propia** de la visita según el
      circuito (sin mezclar oficio de seguimiento ni origen de reinspección).
    - `notificacion_previa_num` / `comprobacion_previa_num` se dejan en null (no usar acta actual como previa).

    Parámetros:
        counts_by_eo: mapa ``establecimiento_operativo_id`` -> cantidad de actuaciones en esa ficha.
            En listados, pasar el resultado de ``build_counts_by_eo_from_actuaciones`` para evitar N+1.
            Si es None y hay ficha, se hace una consulta por actuación (aceptable para alta/baja única).
        iniciador_desde_ruta: iniciador ya resuelto por ``build_iniciador_ruta_por_actuacion_id`` (listados).
            Si es None, se intenta una consulta por ``RutaItem.actuacion_id`` (respuestas unitarias).
        batch: mapas precargados (``build_actuacion_grid_batch_maps``) para listados sin N+1.
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
    calle_raw: Optional[str] = None
    calle_cargada: Optional[str] = None
    calle_estado: Optional[str] = None
    calle_score: Optional[float] = None
    calle_catalogo_id: Optional[int] = None
    numero_tipo: Optional[str] = None
    esquina_raw: Optional[str] = None
    esquina_normalizada: Optional[str] = None
    esquina_cargada: Optional[str] = None
    esquina_key: Optional[str] = None
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
        calle_raw = getattr(dom, "calle_raw", None)
        calle_cargada = calle_cargada_desde_domicilio(dom)
        calle_normalizada = getattr(dom, "calle_normalizada", None)
        calle_estado = getattr(dom, "calle_norm_status", None)
        calle_score = getattr(dom, "calle_norm_score", None)
        calle_catalogo_id = getattr(dom, "calle_catalogo_id", None)
        numero_tipo = getattr(dom, "numero_tipo", None)
        esquina_raw = getattr(dom, "esquina_raw", None)
        esquina_normalizada = getattr(dom, "esquina_normalizada", None)
        esquina_cargada = esquina_cargada_desde_domicilio(dom)
        esquina_key = esquina_key_desde_domicilio(dom)
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
    # Lista completa para el canal grilla / PUT (evita truncado a 3 al guardar).
    inspectores_lista = list(nombres) if nombres else []

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
    # Contexto documental (F2.2) — solo lectura
    # -------------------------
    ini_ruta = iniciador_desde_ruta
    if ini_ruta is None:
        ini_ruta = _iniciador_desde_ruta_item_single(int(act.id))

    rubro_operativo = rubro_nombre_operativo_para_iniciador(ini_ruta, dom, act=act)
    if ini_ruta and ini_ruta.tipo_iniciador == "DENUNCIA":
        rubro_nombre = rubro_operativo
    elif rubro_operativo:
        rubro_nombre = rubro_operativo

    circuito = _clasificar_circuito_documental(act, ini_ruta)
    propia_doc = _propia_payload_for_circuito(circuito, act, batch)

    origen_ofi: Optional[Dict[str, Any]] = None
    origen_notif: Optional[Dict[str, Any]] = None
    if circuito == "REINSPECCION_OFICIO" and ini_ruta is not None:
        origen_ofi = _build_origen_reinspeccion_oficio(ini_ruta, batch)
    if circuito == "REINSPECCION_NOTIFICACION" and ini_ruta is not None:
        origen_notif = _build_origen_reinspeccion_notificacion(ini_ruta, batch)

    documentacion_contexto: Dict[str, Any] = {
        "circuito": circuito,
        "propia": propia_doc,
    }

    expediente_numero = propia_doc.get("expediente_numero")
    expediente_anio = propia_doc.get("expediente_anio")
    oficio_numero = None
    oficio_anio = None
    oficio_causa = None

    notificacion_previa_num = None
    comprobacion_previa_num = None

    
    calle_mostrar = calle_normalizada if calle_estado == "OK" and calle_normalizada else calle
    if numero_tipo == "ESQUINA" and esquina_status == "OK" and esquina_normalizada:
        numero_mostrar = esquina_normalizada
    elif numero_tipo == "ESQUINA":
        numero_mostrar = numero
    else:
        numero_mostrar = numero
    calle_sugerida = calle_normalizada if calle_normalizada else None

    _raw_nombre_local = getattr(act, "nombre_local", None)
    nombre_local_val = (str(_raw_nombre_local).strip() or None) if _raw_nombre_local is not None else None

    eo_id = getattr(act, "establecimiento_operativo_id", None)
    en_ficha: int | None = None
    if eo_id is not None:
        eid = int(eo_id)
        if counts_by_eo is not None:
            en_ficha = int(counts_by_eo.get(eid, 0))
        else:
            en_ficha = int(count_actuaciones_por_establecimiento_operativo_ids([eid]).get(eid, 0))

    return {
        "id": act.id,
        "orden_trabajo_numero": ot_num,
        "fecha_actuacion": fecha_iso,

        "rubro_nombre": rubro_nombre,

        "inspector1": inspector1,
        "inspector2": inspector2,
        "inspector3": inspector3,
        "inspectores": inspectores_lista,
        "inspectores_texto": inspectores_texto,

        "calle": calle_cargada or calle,
        "calle_raw": calle_raw,
        "calle_cargada": calle_cargada,
        "numero": numero,
        "numero_tipo": numero_tipo,
        "numero_mostrar": numero_mostrar,
        "numero_esquina": esquina_cargada if numero_tipo == "ESQUINA" else None,
        "esquina_raw": esquina_raw,
        "esquina_normalizada": esquina_normalizada,
        "esquina_cargada": esquina_cargada,
        "esquina_key": esquina_key,
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

        "establecimiento_operativo_id": eo_id,
        "establecimiento_actuaciones_en_ficha": en_ficha,

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

        "documentacion_contexto": documentacion_contexto,
        "origen_reinspeccion_oficio": origen_ofi,
        "origen_reinspeccion_notificacion": origen_notif,

        "notificacion_editable": notificacion_editable_desde_canal_actas(getattr(act, "notificacion_id", None)),
        "comprobacion_editable": comprobacion_editable_desde_canal_actas(getattr(act, "comprobacion_id", None)),
        **_domicilio_edit_flags_for_grid(act, ini_ruta),
        **_epicollect_detalle_for_grid(act),
        **_epicollect_evidencias_for_grid(act),
    }


def _infer_expediente_source_type(act: Actuaciones) -> str:
    """
    Infiere la rama administrativa para expediente desde estado DB (vista neutra / listado ``all``).

    Regla determinística:
    - Si existe comprobación, domina COMPROBACION.
    - Si no, y existe notificación, NOTIFICACION.
    - Si no hay ninguna, UNKNOWN.

    Para listados filtrados por canal (``pendientes/expediente?source_type=notificacion|comprobacion``),
    usar ``_pendiente_expediente_source_type_for_list`` para que la notificación siga visible aunque
    coexistan ambas actas en la misma actuación.
    """
    if getattr(act, "comprobacion_id", None):
        return "COMPROBACION"
    if getattr(act, "notificacion_id", None):
        return "NOTIFICACION"
    return "UNKNOWN"


def _pendiente_expediente_source_type_for_list(
    act: Actuaciones,
    expediente_list_channel: str | None,
) -> str:
    """
    ``source_type`` de la fila según el filtro del listado de pendientes de expediente.

    Parámetros:
        act: actuación ORM.
        expediente_list_channel: ``notificacion`` | ``comprobacion`` | ``all`` (o None como ``all``).

    Retorno:
        ``NOTIFICACION``, ``COMPROBACION`` o ``UNKNOWN`` coherente con el canal pedido; si el canal
        es ``notificacion`` y hay ``notificacion_id``, devuelve ``NOTIFICACION`` aunque también
        exista comprobación en la misma actuación.
    """
    ch = (expediente_list_channel or "all").strip().lower()
    if ch == "notificacion" and getattr(act, "notificacion_id", None):
        return "NOTIFICACION"
    if ch == "comprobacion" and getattr(act, "comprobacion_id", None):
        return "COMPROBACION"
    return _infer_expediente_source_type(act)


def _dias_restantes_desde_vencimiento(fecha_vencimiento: date | None) -> int | None:
    """
    Días **hábiles** restantes hasta el vencimiento operativo (`Notificacion.fecha_vencimiento`),
    alineado con el plazo en hábiles (misma regla que `calcular_fecha_vencimiento_notificacion_habiles`).

    Cuenta hábiles desde hoy hasta ``fecha_vencimiento`` inclusive. Si ya venció: 0.
    Sin fecha: None.

    Nota: el job/CLI ``sync-notificaciones-vencidas`` no recalcula esto; solo reconcilia
    iniciadores de reinspección. Este valor se deriva en cada lectura desde la fecha persistida.
    """
    if fecha_vencimiento is None:
        return None
    hoy = date.today()
    if fecha_vencimiento < hoy:
        return 0
    return contar_dias_habiles_inclusive(hoy, fecha_vencimiento)


def _inspectores_joined_text_from_orm(act: Actuaciones) -> Optional[str]:
    """Nombres de inspectores de la actuación ORM (relación `inspector` cargada)."""
    insp_list: List[Any] = getattr(act, "inspector", None) or []
    if insp_list:
        insp_list = sorted(insp_list, key=lambda x: getattr(x, "id", 0))
    nombres: List[str] = []
    for i in insp_list:
        n = getattr(i, "nombre", None)
        if n:
            t = str(n).strip()
            if t:
                nombres.append(t)
    return ", ".join(nombres) if nombres else None


def actuacion_to_pendiente_expediente_row(
    act: Actuaciones,
    *,
    plazos_por_notificacion: dict[int, int] | None = None,
    fecha_vencimiento_por_notificacion: dict[int, date | None] | None = None,
    prorroga_dias_por_notificacion: dict[int, int] | None = None,
    counts_by_eo: dict[int, int] | None = None,
    posterior_por_actuacion_id: dict[int, Actuaciones | None] | None = None,
    reinspeccion_comprobacion_por_actuacion_id: dict[int, Actuaciones | None] | None = None,
    expediente_list_channel: str | None = None,
) -> Dict[str, Any]:
    """
    DTO compacto para la bandeja unificada de pendientes de expediente.

    Incluye ``source_type`` explícito y ``notificacion_id`` / ``comprobacion_id`` para que el cliente
    pueda validar actuaciones mixtas (notificación + comprobación en la misma fila).
    Rama NOTIFICACION: `dias_restantes` (hábiles hasta `fecha_vencimiento`) y `plazos_otorgados`
    cuando se pasan mapas batch
    (`build_notificacion_expediente_bandeja_metrics`). Rama COMPROBACION: ambos None.

    ``expediente_list_channel``: alineado con el query ``source_type`` del endpoint
    (``notificacion`` / ``comprobacion`` / ``all``). En ``notificacion``, una actuación con notificación
    y comprobación conserva métricas de plazo y ``source_type`` ``NOTIFICACION`` para la gestión de
    notificación; en ``all`` sigue predominando la inferencia por estado (ambas actas → COMPROBACION).

    Campos `comprobacion_posterior_*`: comprobación de la reinspección por notificación vencida
    (actuación ``REINSPECCION`` con la misma ``notificacion_id``), vía
    ``build_reinspeccion_comprobacion_por_actuacion_id``. No se usa la comprobación cargada en la
    actuación origen mixta ni una posterior genérica por domicilio en canal ``notificacion``.
    ``posterior_por_actuacion_id`` (domicilio) solo aplica fuera del canal notificación.
    """
    full = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
    source_type = _pendiente_expediente_source_type_for_list(act, expediente_list_channel)
    full["source_type"] = source_type
    full["notificacion_id"] = getattr(act, "notificacion_id", None)
    full["comprobacion_id"] = getattr(act, "comprobacion_id", None)

    plazos_map = plazos_por_notificacion or {}
    venc_map = fecha_vencimiento_por_notificacion or {}
    prorroga_map = prorroga_dias_por_notificacion or {}

    if source_type == "NOTIFICACION" and act.notificacion_id is not None:
        nid = int(act.notificacion_id)
        full["plazos_otorgados"] = int(plazos_map.get(nid, 0))
        full["dias_restantes"] = _dias_restantes_desde_vencimiento(venc_map.get(nid))
        full["notificacion_prorroga_dias"] = int(prorroga_map.get(nid, 0))
    else:
        full["plazos_otorgados"] = None
        full["dias_restantes"] = None
        full["notificacion_prorroga_dias"] = None

    ch = (expediente_list_channel or "all").strip().lower()

    post_act: Actuaciones | None = None
    if source_type == "NOTIFICACION" or ch == "notificacion":
        if reinspeccion_comprobacion_por_actuacion_id is not None:
            post_act = reinspeccion_comprobacion_por_actuacion_id.get(int(act.id))
    elif posterior_por_actuacion_id is not None:
        post_act = posterior_por_actuacion_id.get(int(act.id))

    if post_act is not None:
        comp_p = getattr(post_act, "comprobacion", None)
        full["comprobacion_posterior_fecha"] = post_act.fecha.isoformat() if post_act.fecha else None
        full["comprobacion_posterior_inspectores_texto"] = _inspectores_joined_text_from_orm(post_act)
        full["comprobacion_posterior_acta_num"] = getattr(comp_p, "numero_acta", None) if comp_p else None
    elif source_type == "COMPROBACION" and getattr(act, "comprobacion_id", None):
        full["comprobacion_posterior_fecha"] = full.get("fecha_actuacion")
        full["comprobacion_posterior_inspectores_texto"] = full.get("inspectores_texto")
        full["comprobacion_posterior_acta_num"] = full.get("acta_comprobacion_num")
    else:
        full["comprobacion_posterior_fecha"] = None
        full["comprobacion_posterior_inspectores_texto"] = None
        full["comprobacion_posterior_acta_num"] = None

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
    calle_cargada: Optional[str] = None
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
        calle_cargada = calle_cargada_desde_domicilio(dom)
        calle_normalizada = getattr(dom, "calle_normalizada", None)
        calle_catalogo_id = getattr(dom, "calle_catalogo_id", None)
        esquina_normalizada = getattr(dom, "esquina_normalizada", None)
        esquina_catalogo_id = getattr(dom, "esquina_catalogo_id", None)
        esquina_status = getattr(dom, "esquina_norm_status", None)
        rub = getattr(dom, "rubro", None)
        if rub:
            rubro_nombre = getattr(rub, "nombre", None)

    ini_ruta = _iniciador_desde_ruta_item_single(int(act.id))
    rubro_operativo = rubro_nombre_operativo_para_iniciador(ini_ruta, dom, act=act)
    if ini_ruta and ini_ruta.tipo_iniciador == "DENUNCIA":
        rubro_nombre = rubro_operativo
    elif rubro_operativo:
        rubro_nombre = rubro_operativo

    return {
        "id": act.id,
        "fecha_actuacion": fecha_iso,
        "orden_trabajo_numero": ot_num,
        "tipo_actuacion": _enum_to_str(getattr(act, "tipo", None)),
        "contraproducencia": _enum_to_str(getattr(act, "contraproducencia", None)),
        "rubro_nombre": rubro_nombre,
        "calle_ingresada": calle_cargada or calle,
        "calle": calle_cargada or calle,
        "calle_raw": getattr(dom, "calle_raw", None) if dom else None,
        "calle_cargada": calle_cargada,
        "calle_normalizada": calle_normalizada,
        "calle_catalogo_id": calle_catalogo_id,
        "numero": numero,
        "numero_tipo": numero_tipo,
        "esquina_normalizada": esquina_normalizada,
        "esquina_catalogo_id": esquina_catalogo_id,
        "esquina_status": esquina_status,
        "domicilio_id": domicilio_id,
    }


def actuacion_to_pendiente_oficio_row(
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
) -> Dict[str, Any]:
    """
    Convierte una actuación a una fila compacta para la bandeja "Esperando oficio".

    Incluye contexto operativo mínimo y el expediente original de comprobación.
    """
    full = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
    exp_original = None
    if getattr(act, "comprobacion_id", None):
        exp_original = expediente_envio_por_comprobacion(act.comprobacion_id)

    return {
        "id": full.get("id"),
        "fecha_actuacion": full.get("fecha_actuacion"),
        "orden_trabajo_numero": full.get("orden_trabajo_numero"),
        "tipo_actuacion": full.get("tipo_actuacion"),
        "acta_comprobacion_num": full.get("acta_comprobacion_num"),
        "comprobacion_motivo": full.get("comprobacion_motivo"),
        "contrib_apellido": full.get("contrib_apellido"),
        "contrib_nombre": full.get("contrib_nombre"),
        "razon_social": full.get("razon_social"),
        "doc_nro": full.get("doc_nro"),
        "calle": full.get("calle"),
        "numero": full.get("numero"),
        "rubro_nombre": full.get("rubro_nombre"),
        "acta_inspeccion_num": full.get("acta_inspeccion_num"),
        "inspectores_texto": full.get("inspectores_texto"),
        "inspector1": full.get("inspector1"),
        "inspector2": full.get("inspector2"),
        "inspector3": full.get("inspector3"),
        "expediente_original_id": getattr(exp_original, "id", None),
        "expediente_original_numero": getattr(exp_original, "numero_expediente", None),
        "expediente_original_anio": getattr(exp_original, "anio", None),
        "expediente_original_fecha": (
            exp_original.fecha_expediente.isoformat() if exp_original and exp_original.fecha_expediente else None
        ),
    }
