"""
Conciliación EpiCollect ↔ inventario MySQL histórico (V1.1-MIG-ACTAS.0B).

Solo lectura de CSV; sin conexión a base de datos.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app.domains.migracion_historica.epicollect_actas_inventario import (
    Decision,
    RowSnapshot,
    _normalize_acta_num,
    parse_inspection_date,
    sha256_file,
)
from app.domains.migracion_historica.epicollect_cadenas_historicas import (
    ActaIndexRecord,
    CadenaVinculo,
    CadenasHistoricasResult,
    EstadoVinculo,
    ResultadoCadenaEsperado,
    _ACTA_TIPO_COMPROBACION,
    _ACTA_TIPO_NOTIFICACION,
    _es_reinspeccion_notificacion,
    _es_reinspeccion_oficio,
    _filter_candidates,
    _lookup_comprobacion,
    _lookup_notificacion,
    _resultado_cadena_comprobacion,
    _resultado_cadena_notificacion,
    analizar_cadena_reinspeccion,
    mask_acta_correlacion,
    normalize_documento,
    normalize_domicilio,
    resolve_titular_norm,
)

# Alias de columnas (cabeceras normalizadas: minúsculas, espacios → _)
_LEGACY_COLUMN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "fecha": ("fecha_actuacion", "fecha_inspeccion", "fecha"),
    "anio": ("ot_anio", "anio", "year"),
    "tipo_actuacion": ("tipo_actuacion", "tipo"),
    "numero_acta_notificacion": (
        "numero_acta_notificacion",
        "notificacion_numero",
        "notificacion_numero",
        "acta_notificacion_num",
        "numero_notificacion",
        "num_acta_notificacion",
    ),
    "numero_acta_comprobacion": (
        "numero_acta_comprobacion",
        "comprobacion_numero",
        "comprobacion_numero",
        "acta_comprobacion_num",
        "numero_comprobacion",
        "num_acta_comprobacion",
    ),
    "expediente": ("expediente_numero", "numero_expediente", "numero_de_expediente"),
    "anio_expediente": ("expediente_anio", "anio_expediente"),
    "oficio": ("numero_oficio", "oficio_numero"),
    "documento": ("documento", "dni_cuit", "contribuyente_documento", "cuit", "dni"),
    "titular": (
        "titular",
        "razon_social",
        "contribuyente_nombre",
        "nombre_titular",
        "razon_social_nombre",
        "titular_razon_social_historica",
    ),
    "domicilio": ("domicilio_texto", "domicilio", "domicilio_completo", "calle"),
    "legacy_ref_hash": ("legacy_ref_hash",),
    "estado": ("estado_ruta_item", "estado_actuacion", "estado"),
    "legacy_id": ("source_actuacion_id", "legacy_actuacion_id", "actuacion_id", "id"),
    "tiene_notificacion": ("tiene_notificacion",),
    "tiene_comprobacion": ("tiene_comprobacion",),
}

_LEGACY_VINCULO_CSV_FIELDS: Tuple[str, ...] = (
    "ec5_uuid",
    "fuente_previa_uuid",
    "fuente_previa_legacy_hash",
    "fecha_inspec_iso",
    "tipo_inspeccion_epi",
    "tipo_origen_esperado",
    "origen_evidencia_vinculo",
    "estado_vinculo",
    "resultado_cadena_esperado",
    "motivo_revision",
    "acta_referencia_hash",
    "previa_acta_hash",
)


@dataclass
class LegacyColumnMap:
    """Mapeo lógico → nombre de columna real en el CSV."""

    fecha: Optional[str] = None
    anio: Optional[str] = None
    tipo_actuacion: Optional[str] = None
    numero_acta_notificacion: Optional[str] = None
    numero_acta_comprobacion: Optional[str] = None
    expediente: Optional[str] = None
    anio_expediente: Optional[str] = None
    oficio: Optional[str] = None
    documento: Optional[str] = None
    titular: Optional[str] = None
    domicilio: Optional[str] = None
    estado: Optional[str] = None
    legacy_id: Optional[str] = None
    tiene_notificacion: Optional[str] = None
    tiene_comprobacion: Optional[str] = None
    legacy_ref_hash: Optional[str] = None


@dataclass
class LegacyActaRecord:
    """Acta previa indexada desde inventario MySQL."""

    legacy_hash: str
    legacy_id: str
    fecha: date
    acta_tipo: str
    acta_num: str
    acta_anio: int
    doc_norm: str
    dom_norm: str
    titular_norm: str


@dataclass
class ConciliacionLegacyResult:
    legacy_sha256: str
    referencias_pendientes_0a: int = 0
    resueltas_epicollect: int = 0
    resueltas_adicional_mysql: int = 0
    parciales_sin_identidad: int = 0
    conflictos_entre_fuentes: int = 0
    sin_origen: int = 0
    notificaciones_cierre_historico_posible: int = 0
    comprobaciones_circuito_respaldado: int = 0
    vinculos: List[CadenaVinculo] = field(default_factory=list)


def _norm_header(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def map_legacy_columns(headers: Sequence[str]) -> LegacyColumnMap:
    """Detecta columnas disponibles en el inventario MySQL."""
    normalized = {_norm_header(h): h for h in headers}
    mapped = LegacyColumnMap()
    for logical, aliases in _LEGACY_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                setattr(mapped, logical, normalized[alias])
                break
    return mapped


def build_compatibilidad_diagnostico(
    headers: Sequence[str],
    column_map: LegacyColumnMap,
    total_filas: int,
) -> Dict[str, Any]:
    """Genera diagnóstico de evidencia disponible en el inventario."""
    evidencia = {
        "fecha_tipo_anio": bool(column_map.fecha and column_map.tipo_actuacion),
        "numero_acta_notificacion": bool(column_map.numero_acta_notificacion),
        "numero_acta_comprobacion": bool(column_map.numero_acta_comprobacion),
        "expediente_oficio": bool(column_map.expediente and column_map.oficio),
        "documento": bool(column_map.documento),
        "titular": bool(column_map.titular),
        "domicilio": bool(column_map.domicilio),
        "estado_actuacion": bool(column_map.estado),
    }
    identidad_completa = evidencia["documento"] or (
        evidencia["domicilio"] and evidencia["titular"]
    )
    return {
        "total_filas_inventario": total_filas,
        "columnas_detectadas": {k: getattr(column_map, k) for k in _LEGACY_COLUMN_ALIASES if getattr(column_map, k)},
        "evidencia_disponible": evidencia,
        "puede_elevar_vinculo_confiable": identidad_completa
        and (
            evidencia["numero_acta_notificacion"] or evidencia["numero_acta_comprobacion"]
        ),
        "campos_ausentes": [k for k, ok in evidencia.items() if not ok],
        "nota": (
            "Sin identidad (documento o domicilio+titular) el inventario solo puede aportar "
            "referencia parcial de acta, nunca VINCULO_CONFIABLE."
        ),
    }


def legacy_reference_hash(legacy_id: str, acta_tipo: str, acta_num: str, acta_anio: int) -> str:
    """Hash técnico de referencia MySQL (sin PII)."""
    payload = f"{legacy_id}|{acta_tipo}|{acta_num}|{acta_anio}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _cell_mapped(row: Mapping[str, str], col: Optional[str]) -> str:
    if not col:
        return ""
    return (row.get(col) or "").strip()


def _truthy_flag(raw: str) -> bool:
    return raw.strip().lower() in ("1", "si", "sí", "true", "yes")


def _parse_legacy_row(
    row: Dict[str, str],
    column_map: LegacyColumnMap,
    cutoff: date,
) -> List[LegacyActaRecord]:
    """Extrae registros de acta indexables desde una fila de inventario."""
    fecha_raw = _cell_mapped(row, column_map.fecha)
    fecha_parsed, _ = parse_inspection_date(fecha_raw)
    if fecha_parsed is None or fecha_parsed >= cutoff:
        return []

    anio_raw = _cell_mapped(row, column_map.anio)
    anio = int(_normalize_acta_num(anio_raw)) if anio_raw else fecha_parsed.year
    legacy_id = _cell_mapped(row, column_map.legacy_id) or legacy_reference_hash(
        "", "ROW", fecha_raw, anio
    )
    doc = normalize_documento(_cell_mapped(row, column_map.documento))
    dom = normalize_domicilio(_cell_mapped(row, column_map.domicilio))
    tit = resolve_titular_norm("", _cell_mapped(row, column_map.titular))

    records: List[LegacyActaRecord] = []
    notif_num = _normalize_acta_num(_cell_mapped(row, column_map.numero_acta_notificacion))
    if notif_num:
        records.append(
            LegacyActaRecord(
                legacy_hash=legacy_reference_hash(legacy_id, _ACTA_TIPO_NOTIFICACION, notif_num, anio),
                legacy_id=legacy_id,
                fecha=fecha_parsed,
                acta_tipo=_ACTA_TIPO_NOTIFICACION,
                acta_num=notif_num,
                acta_anio=anio,
                doc_norm=doc,
                dom_norm=dom,
                titular_norm=tit,
            )
        )
    elif column_map.tiene_notificacion and _truthy_flag(_cell_mapped(row, column_map.tiene_notificacion)):
        pass  # sin número de acta no indexable

    comp_num = _normalize_acta_num(_cell_mapped(row, column_map.numero_acta_comprobacion))
    if comp_num:
        records.append(
            LegacyActaRecord(
                legacy_hash=legacy_reference_hash(legacy_id, _ACTA_TIPO_COMPROBACION, comp_num, anio),
                legacy_id=legacy_id,
                fecha=fecha_parsed,
                acta_tipo=_ACTA_TIPO_COMPROBACION,
                acta_num=comp_num,
                acta_anio=anio,
                doc_norm=doc,
                dom_norm=dom,
                titular_norm=tit,
            )
        )

    exp = _normalize_acta_num(_cell_mapped(row, column_map.expediente))
    ofi = _normalize_acta_num(_cell_mapped(row, column_map.oficio))
    anio_exp = _normalize_acta_num(_cell_mapped(row, column_map.anio_expediente)) or str(anio)
    if comp_num and exp and ofi:
        # expediente indexado como comprobación con clave auxiliar (misma fila)
        pass
    return records


def build_legacy_acta_indexes(
    legacy_path: Path,
    cutoff: date,
) -> Tuple[LegacyColumnMap, Dict[str, Any], Dict[Tuple[str, str], List[LegacyActaRecord]], Dict[str, List[LegacyActaRecord]]]:
    """
    Lee inventario MySQL y construye índices por (tipo, número) y expediente.

    Returns:
        (column_map, compatibilidad_dict, by_tipo_num, expediente_index).
    """
    by_tipo_num: Dict[Tuple[str, str], List[LegacyActaRecord]] = defaultdict(list)
    expediente_index: Dict[str, List[LegacyActaRecord]] = defaultdict(list)
    rows_count = 0

    with legacy_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        column_map = map_legacy_columns(headers)
        for row in reader:
            rows_count += 1
            for rec in _parse_legacy_row(row, column_map, cutoff):
                by_tipo_num[(rec.acta_tipo, rec.acta_num)].append(rec)
                exp = _normalize_acta_num(_cell_mapped(row, column_map.expediente))
                ofi = _normalize_acta_num(_cell_mapped(row, column_map.oficio))
                anio_exp = _normalize_acta_num(_cell_mapped(row, column_map.anio_expediente))
                if rec.acta_tipo == _ACTA_TIPO_COMPROBACION and exp and ofi and anio_exp:
                    clave = f"{exp}|{anio_exp}|{ofi}"
                    expediente_index[clave].append(rec)

    compat = build_compatibilidad_diagnostico(headers, column_map, rows_count)
    compat["legacy_inventory_sha256"] = sha256_file(legacy_path)
    return column_map, compat, by_tipo_num, expediente_index


def _legacy_to_acta_index_record(rec: LegacyActaRecord) -> ActaIndexRecord:
    return ActaIndexRecord(
        ec5_uuid=rec.legacy_hash,
        fecha=rec.fecha,
        acta_tipo=rec.acta_tipo,
        acta_num=rec.acta_num,
        acta_anio=rec.acta_anio,
        doc_norm=rec.doc_norm,
        dom_norm=rec.dom_norm,
        titular_norm=rec.titular_norm,
    )


def _lookup_legacy_notificacion(
    rein: RowSnapshot,
    by_tipo_num: Mapping[Tuple[str, str], List[LegacyActaRecord]],
) -> Tuple[List[LegacyActaRecord], str, str]:
    ref = _normalize_acta_num(rein.ref_notificacion_previa or rein.acta_notificacion_num)
    if not ref:
        return [], "referencia_previa_ausente", ""
    cands = [c for c in by_tipo_num.get((_ACTA_TIPO_NOTIFICACION, ref), [])]
    acta_cands = [_legacy_to_acta_index_record(c) for c in cands]
    filtered, motivo = _filter_candidates(acta_cands, rein)
    if not filtered:
        return [], motivo, ref
    legacy_by_hash = {c.legacy_hash: c for c in cands}
    return [legacy_by_hash[f.ec5_uuid] for f in filtered], "", ref


def _lookup_legacy_comprobacion(
    rein: RowSnapshot,
    by_tipo_num: Mapping[Tuple[str, str], List[LegacyActaRecord]],
    expediente_index: Mapping[str, List[LegacyActaRecord]],
) -> Tuple[List[LegacyActaRecord], str, str]:
    ref = _normalize_acta_num(rein.ref_comprobacion_previa)
    if ref:
        cands = [c for c in by_tipo_num.get((_ACTA_TIPO_COMPROBACION, ref), [])]
        acta_cands = [_legacy_to_acta_index_record(c) for c in cands]
        filtered, motivo = _filter_candidates(acta_cands, rein)
        if not filtered:
            return [], motivo, ref
        legacy_by_hash = {c.legacy_hash: c for c in cands}
        return [legacy_by_hash[f.ec5_uuid] for f in filtered], "", ref

    for clave in rein.expediente_claves:
        raw = list(expediente_index.get(clave, []))
        uuids = {c.legacy_hash for c in raw}
        if len(uuids) > 1:
            return [], "referencia_expediente_ambigua", f"exp:{clave}"
        if len(uuids) == 1:
            acta_cands = [_legacy_to_acta_index_record(c) for c in raw]
            filtered, motivo = _filter_candidates(acta_cands, rein)
            if not filtered:
                return [], motivo, f"exp:{clave}"
            return raw, "", f"exp:{clave}"
    return [], "referencia_previa_ausente", ""


def _epicollect_blocks_legacy(cadena_epi: CadenaVinculo) -> bool:
    """No consultar MySQL si EpiCollect ya marcó conflicto."""
    return cadena_epi.estado_vinculo == EstadoVinculo.VINCULO_CONFLICTIVO


def _identity_capable(compat: Mapping[str, Any]) -> bool:
    ev = compat.get("evidencia_disponible") or {}
    return bool(ev.get("documento")) or (bool(ev.get("domicilio")) and bool(ev.get("titular")))


def _apply_cadena_to_snap(snap: RowSnapshot, cadena: CadenaVinculo) -> None:
    snap.estado_vinculo = cadena.estado_vinculo.value
    snap.tipo_origen_esperado = cadena.tipo_origen_esperado
    snap.resultado_cadena_esperado = cadena.resultado_cadena_esperado.value
    snap.fuente_previa_uuid = cadena.fuente_previa_uuid
    snap.origen_evidencia_vinculo = getattr(cadena, "origen_evidencia_vinculo", "") or ""
    snap.fuente_previa_legacy_hash = getattr(cadena, "fuente_previa_legacy_hash", "") or ""
    snap.motivo_revision = cadena.motivo_revision
    if cadena.estado_vinculo == EstadoVinculo.VINCULO_CONFIABLE:
        snap.previa_ec5_uuid = cadena.fuente_previa_uuid
        if _es_reinspeccion_notificacion(snap.tipo_inspeccion):
            snap.decision = Decision.CANDIDATA_REINSPECCION_NOTIFICACION
        elif _es_reinspeccion_oficio(snap.tipo_inspeccion):
            snap.decision = Decision.CANDIDATA_REINSPECCION_OFICIO
    else:
        snap.decision = Decision.REVISAR


def conciliar_vinculo_legacy(
    rein: RowSnapshot,
    cadena_epi: CadenaVinculo,
    compat: Mapping[str, Any],
    legacy_by_tipo_num: Mapping[Tuple[str, str], List[LegacyActaRecord]],
    legacy_expediente: Mapping[str, List[LegacyActaRecord]],
    epi_by_tipo_num: Mapping[Tuple[str, str], List[ActaIndexRecord]],
    epi_expediente: Mapping[str, List[ActaIndexRecord]],
) -> CadenaVinculo:
    """
    Aplica orden de conciliación: EpiCollect primero; MySQL solo si aplica.

    Enriquece ``CadenaVinculo`` con ``origen_evidencia_vinculo`` y ``fuente_previa_legacy_hash``.
    """
    cadena = CadenaVinculo(
        ec5_uuid=cadena_epi.ec5_uuid,
        fuente_previa_uuid=cadena_epi.fuente_previa_uuid,
        fecha_inspec=cadena_epi.fecha_inspec,
        tipo_inspeccion=cadena_epi.tipo_inspeccion,
        estado_vinculo=cadena_epi.estado_vinculo,
        tipo_origen_esperado=cadena_epi.tipo_origen_esperado,
        resultado_cadena_esperado=cadena_epi.resultado_cadena_esperado,
        motivo_revision=cadena_epi.motivo_revision,
        acta_referencia_hash=cadena_epi.acta_referencia_hash,
        previa_acta_hash=cadena_epi.previa_acta_hash,
        es_reinspeccion=cadena_epi.es_reinspeccion,
    )
    cadena.origen_evidencia_vinculo = ""
    cadena.fuente_previa_legacy_hash = ""

    if cadena_epi.estado_vinculo == EstadoVinculo.VINCULO_CONFIABLE:
        cadena.origen_evidencia_vinculo = "EPICOLLECT"
        ref_key = _normalize_acta_num(
            rein.ref_notificacion_previa
            if cadena.tipo_origen_esperado == _ACTA_TIPO_NOTIFICACION
            else rein.ref_comprobacion_previa
        )
        epi_rec: Optional[ActaIndexRecord] = None
        if cadena.fuente_previa_uuid and ref_key:
            for rec in epi_by_tipo_num.get((cadena.tipo_origen_esperado, ref_key), []):
                if rec.ec5_uuid == cadena.fuente_previa_uuid:
                    epi_rec = rec
                    break
        leg_raw = list(legacy_by_tipo_num.get((cadena.tipo_origen_esperado, ref_key), [])) if ref_key else []
        if leg_raw:
            docs = {leg.doc_norm for leg in leg_raw if leg.doc_norm}
            cadena.fuente_previa_legacy_hash = leg_raw[0].legacy_hash
            conflicto = len(docs) > 1
            if epi_rec and epi_rec.doc_norm and docs and epi_rec.doc_norm not in docs:
                conflicto = True
            if epi_rec and leg_raw:
                leg = leg_raw[0]
                if epi_rec.doc_norm and leg.doc_norm and epi_rec.doc_norm != leg.doc_norm:
                    conflicto = True
            if conflicto:
                cadena.estado_vinculo = EstadoVinculo.VINCULO_CONFLICTIVO
                cadena.motivo_revision = "conflicto_fuentes_epi_mysql"
                cadena.origen_evidencia_vinculo = "AMBOS"
                cadena.resultado_cadena_esperado = ResultadoCadenaEsperado.REVISAR
            else:
                leg_ok, _, _ = (
                    _lookup_legacy_notificacion(rein, legacy_by_tipo_num)
                    if cadena.tipo_origen_esperado == _ACTA_TIPO_NOTIFICACION
                    else _lookup_legacy_comprobacion(rein, legacy_by_tipo_num, legacy_expediente)
                )
                if leg_ok:
                    cadena.origen_evidencia_vinculo = "AMBOS"
        return cadena

    if _epicollect_blocks_legacy(cadena_epi):
        cadena.origen_evidencia_vinculo = "EPICOLLECT"
        return cadena

    if not _identity_capable(compat):
        if cadena_epi.estado_vinculo == EstadoVinculo.VINCULO_PARCIAL:
            cadena.motivo_revision = cadena_epi.motivo_revision or "legacy_sin_columnas_identidad"
        return cadena

    if cadena.tipo_origen_esperado == _ACTA_TIPO_NOTIFICACION:
        leg_cands, leg_motivo, leg_ref = _lookup_legacy_notificacion(rein, legacy_by_tipo_num)
    elif cadena.tipo_origen_esperado == _ACTA_TIPO_COMPROBACION:
        leg_cands, leg_motivo, leg_ref = _lookup_legacy_comprobacion(
            rein, legacy_by_tipo_num, legacy_expediente
        )
    else:
        return cadena

    if not leg_cands:
        if leg_motivo in ("conflicto_documento", "conflicto_domicilio", "conflicto_titular", "cronologia_invalida"):
            cadena.estado_vinculo = EstadoVinculo.VINCULO_CONFLICTIVO
            cadena.motivo_revision = leg_motivo
        elif leg_motivo in ("referencia_previa_ambigua", "referencia_expediente_ambigua"):
            cadena.estado_vinculo = EstadoVinculo.VINCULO_CONFLICTIVO
            cadena.motivo_revision = leg_motivo
        elif leg_motivo == "identidad_insuficiente":
            cadena.estado_vinculo = EstadoVinculo.VINCULO_PARCIAL
            cadena.motivo_revision = "legacy_identidad_insuficiente"
        return cadena

    leg = leg_cands[0]
    ref_norm = _normalize_acta_num(leg_ref if leg_ref else leg.acta_num)
    epi_raw = [
        c
        for c in epi_by_tipo_num.get((cadena.tipo_origen_esperado, ref_norm), [])
        if c.ec5_uuid != rein.ec5_uuid
    ]
    epi_uuids = {c.ec5_uuid for c in epi_raw}
    if len(epi_uuids) > 1:
        cadena.estado_vinculo = EstadoVinculo.VINCULO_CONFLICTIVO
        cadena.motivo_revision = "conflicto_fuentes_epi_mysql"
        cadena.origen_evidencia_vinculo = "MYSQL_HISTORICO"
        cadena.resultado_cadena_esperado = ResultadoCadenaEsperado.REVISAR
        return cadena
    if len(epi_raw) == 1:
        er = epi_raw[0]
        if er.doc_norm and leg.doc_norm and er.doc_norm != leg.doc_norm:
            cadena.estado_vinculo = EstadoVinculo.VINCULO_CONFLICTIVO
            cadena.motivo_revision = "conflicto_fuentes_epi_mysql"
            cadena.origen_evidencia_vinculo = "MYSQL_HISTORICO"
            cadena.resultado_cadena_esperado = ResultadoCadenaEsperado.REVISAR
            return cadena

    cadena.estado_vinculo = EstadoVinculo.VINCULO_CONFIABLE
    cadena.fuente_previa_legacy_hash = leg.legacy_hash
    cadena.fuente_previa_uuid = ""
    cadena.previa_acta_hash = mask_acta_correlacion(leg.acta_num)
    cadena.motivo_revision = ""
    cadena.origen_evidencia_vinculo = "MYSQL_HISTORICO"
    if cadena.tipo_origen_esperado == _ACTA_TIPO_NOTIFICACION:
        cadena.resultado_cadena_esperado = _resultado_cadena_notificacion(rein)
    else:
        cadena.resultado_cadena_esperado = _resultado_cadena_comprobacion(rein)
    return cadena


def aplicar_conciliacion_legacy(
    filas: Sequence[RowSnapshot],
    cutoff: date,
    cadenas: CadenasHistoricasResult,
    legacy_path: Path,
    epi_by_tipo_num: Mapping[Tuple[str, str], List[ActaIndexRecord]],
    epi_expediente: Mapping[str, List[ActaIndexRecord]],
) -> Tuple[CadenasHistoricasResult, ConciliacionLegacyResult, Dict[str, Any]]:
    """
    Segunda pasada de conciliación con inventario MySQL.

    Actualiza vínculos, filas y métricas agregadas.
    """
    column_map, compat, legacy_by_tipo_num, legacy_expediente = build_legacy_acta_indexes(
        legacy_path, cutoff
    )
    filas_by_uuid = {s.ec5_uuid: s for s in filas}

    pendientes = [v for v in cadenas.vinculos if v.es_reinspeccion]
    resueltas_epi = sum(1 for v in pendientes if v.estado_vinculo == EstadoVinculo.VINCULO_CONFIABLE)

    nuevos_vinculos: List[CadenaVinculo] = []
    res_mysql = 0
    parciales = 0
    conflictos = 0
    sin_origen = 0
    notif_cierre = 0
    comp_resp = 0

    for cadena_epi in pendientes:
        rein = filas_by_uuid.get(cadena_epi.ec5_uuid)
        if rein is None:
            nuevos_vinculos.append(cadena_epi)
            continue
        cadena = conciliar_vinculo_legacy(
            rein,
            cadena_epi,
            compat,
            legacy_by_tipo_num,
            legacy_expediente,
            epi_by_tipo_num,
            epi_expediente,
        )
        nuevos_vinculos.append(cadena)
        _apply_cadena_to_snap(rein, cadena)

        if cadena.estado_vinculo == EstadoVinculo.VINCULO_CONFIABLE:
            if cadena.origen_evidencia_vinculo == "MYSQL_HISTORICO":
                res_mysql += 1
            if cadena.tipo_origen_esperado == _ACTA_TIPO_NOTIFICACION:
                notif_cierre += 1
            if cadena.tipo_origen_esperado == _ACTA_TIPO_COMPROBACION:
                comp_resp += 1
        elif cadena.estado_vinculo == EstadoVinculo.VINCULO_PARCIAL:
            parciales += 1
        elif cadena.estado_vinculo == EstadoVinculo.VINCULO_CONFLICTIVO:
            if cadena.motivo_revision == "conflicto_fuentes_epi_mysql":
                conflictos += 1
        elif cadena.estado_vinculo == EstadoVinculo.SIN_REFERENCIA_PREVIA:
            sin_origen += 1

    confiables = sum(1 for v in nuevos_vinculos if v.estado_vinculo == EstadoVinculo.VINCULO_CONFIABLE)
    cadenas.vinculos = nuevos_vinculos
    cadenas.vinculos_confiables = confiables
    cadenas.notificaciones_cerradas_historicas = notif_cierre
    cadenas.comprobaciones_circuito_oficio_resuelto = comp_resp

    legacy_result = ConciliacionLegacyResult(
        legacy_sha256=compat["legacy_inventory_sha256"],
        referencias_pendientes_0a=len(pendientes),
        resueltas_epicollect=resueltas_epi,
        resueltas_adicional_mysql=res_mysql,
        parciales_sin_identidad=parciales,
        conflictos_entre_fuentes=conflictos,
        sin_origen=sin_origen,
        notificaciones_cierre_historico_posible=notif_cierre,
        comprobaciones_circuito_respaldado=comp_resp,
        vinculos=nuevos_vinculos,
    )
    return cadenas, legacy_result, compat


def legacy_vinculo_to_csv_row(c: CadenaVinculo) -> Dict[str, str]:
    """CSV de conciliación legacy sin PII."""
    return {
        "ec5_uuid": c.ec5_uuid,
        "fuente_previa_uuid": c.fuente_previa_uuid,
        "fuente_previa_legacy_hash": getattr(c, "fuente_previa_legacy_hash", "") or "",
        "fecha_inspec_iso": c.fecha_inspec.isoformat() if c.fecha_inspec else "",
        "tipo_inspeccion_epi": c.tipo_inspeccion,
        "tipo_origen_esperado": c.tipo_origen_esperado,
        "origen_evidencia_vinculo": getattr(c, "origen_evidencia_vinculo", "") or "",
        "estado_vinculo": c.estado_vinculo.value,
        "resultado_cadena_esperado": c.resultado_cadena_esperado.value,
        "motivo_revision": c.motivo_revision,
        "acta_referencia_hash": c.acta_referencia_hash,
        "previa_acta_hash": c.previa_acta_hash,
    }


def _assert_legacy_row_safe(row: Mapping[str, str]) -> None:
    joined = " ".join(row.values()).lower()
    if "http://" in joined or "https://" in joined:
        raise ValueError("salida contiene URL")


def write_legacy_conciliacion_outputs(
    compat: Dict[str, Any],
    legacy_result: ConciliacionLegacyResult,
    output_dir: Path,
) -> None:
    """Escribe artefactos 0B en el directorio de salida."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "compatibilidad_inventario_mysql.json").open("w", encoding="utf-8") as f:
        json.dump(compat, f, ensure_ascii=False, indent=2)

    resueltos = [
        v
        for v in legacy_result.vinculos
        if v.estado_vinculo == EstadoVinculo.VINCULO_CONFIABLE
        and getattr(v, "origen_evidencia_vinculo", "") in ("MYSQL_HISTORICO", "AMBOS")
    ]
    conflictivos = [
        v
        for v in legacy_result.vinculos
        if v.estado_vinculo == EstadoVinculo.VINCULO_CONFLICTIVO
        or (
            v.estado_vinculo != EstadoVinculo.VINCULO_CONFIABLE
            and getattr(v, "origen_evidencia_vinculo", "") == "MYSQL_HISTORICO"
        )
    ]

    for name, rows in (
        ("vinculos_resueltos_legacy.csv", resueltos),
        ("vinculos_conflictivos_legacy.csv", conflictivos),
    ):
        path = output_dir / name
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(_LEGACY_VINCULO_CSV_FIELDS))
            w.writeheader()
            for v in rows:
                out = legacy_vinculo_to_csv_row(v)
                _assert_legacy_row_safe(out)
                w.writerow(out)

    resumen = {
        "legacy_inventory_sha256": legacy_result.legacy_sha256,
        "referencias_pendientes_desde_0a": legacy_result.referencias_pendientes_0a,
        "resueltas_por_epicollect": legacy_result.resueltas_epicollect,
        "resueltas_adicional_por_inventario_mysql": legacy_result.resueltas_adicional_mysql,
        "parciales_falta_identidad": legacy_result.parciales_sin_identidad,
        "conflictos_entre_fuentes": legacy_result.conflictos_entre_fuentes,
        "referencias_sin_origen": legacy_result.sin_origen,
        "notificaciones_cierre_historico_posible": legacy_result.notificaciones_cierre_historico_posible,
        "comprobaciones_circuito_respaldado": legacy_result.comprobaciones_circuito_respaldado,
    }
    with (output_dir / "resumen_conciliacion_legacy.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
