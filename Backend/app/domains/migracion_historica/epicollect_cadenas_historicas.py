"""
Conciliación de cadenas históricas EpiCollect (V1.1-MIG-ACTAS.0A).

Read-only: índices por acta + identidad, validación de vínculos de reinspección.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app.domains.migracion_historica.epicollect_actas_inventario import (
    Decision,
    RowSnapshot,
    _es_reinspeccion_notificacion,
    _es_reinspeccion_oficio,
    _normalize_acta_num,
)

_ACTA_TIPO_NOTIFICACION = "NOTIFICACION"
_ACTA_TIPO_COMPROBACION = "COMPROBACION"


class EstadoVinculo(str, Enum):
    VINCULO_CONFIABLE = "VINCULO_CONFIABLE"
    VINCULO_PARCIAL = "VINCULO_PARCIAL"
    VINCULO_CONFLICTIVO = "VINCULO_CONFLICTIVO"
    SIN_REFERENCIA_PREVIA = "SIN_REFERENCIA_PREVIA"


class ResultadoCadenaEsperado(str, Enum):
    CERRADA_SIN_COMPROBACION = "CERRADA_SIN_COMPROBACION"
    CERRADA_CON_COMPROBACION = "CERRADA_CON_COMPROBACION"
    CIRCUITO_OFICIO_RESUELTO = "CIRCUITO_OFICIO_RESUELTO"
    REVISAR = "REVISAR"


_VINCULO_CSV_FIELDS: Tuple[str, ...] = (
    "ec5_uuid",
    "fuente_previa_uuid",
    "fecha_inspec_iso",
    "tipo_inspeccion_epi",
    "estado_vinculo",
    "tipo_origen_esperado",
    "resultado_cadena_esperado",
    "motivo_revision",
    "acta_referencia_hash",
    "previa_acta_hash",
)


@dataclass
class ActaIndexRecord:
    """Fila histórica indexada como acta de notificación o comprobación."""

    ec5_uuid: str
    fecha: date
    acta_tipo: str
    acta_num: str
    acta_anio: int
    doc_norm: str
    dom_norm: str
    titular_norm: str


@dataclass
class CadenaVinculo:
    """Resultado de conciliación para una fila de reinspección/oficio."""

    ec5_uuid: str
    fuente_previa_uuid: str
    fecha_inspec: Optional[date]
    tipo_inspeccion: str
    estado_vinculo: EstadoVinculo
    tipo_origen_esperado: str
    resultado_cadena_esperado: ResultadoCadenaEsperado
    motivo_revision: str
    acta_referencia_hash: str
    previa_acta_hash: str
    es_reinspeccion: bool = True
    origen_evidencia_vinculo: str = ""
    fuente_previa_legacy_hash: str = ""


@dataclass
class CadenasHistoricasResult:
    vinculos: List[CadenaVinculo] = field(default_factory=list)
    reinspecciones_por_tipo: Dict[str, int] = field(default_factory=dict)
    vinculos_confiables: int = 0
    revisiones_por_motivo: Dict[str, int] = field(default_factory=dict)
    notificaciones_cerradas_historicas: int = 0
    comprobaciones_circuito_oficio_resuelto: int = 0
    conflictos_documento: int = 0
    conflictos_domicilio: int = 0
    conflictos_titular: int = 0
    conflictos_cronologia: int = 0


def normalize_documento(raw: str) -> str:
    """DNI/CUIT: solo dígitos."""
    return re.sub(r"\D+", "", (raw or "").strip())


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_persona_razon(raw: str) -> str:
    """Mayúsculas, sin acentos, espacios simples, sin puntuación no significativa."""
    s = _strip_accents((raw or "").strip().upper())
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


_STREET_ABBR = (
    (r"\bAV\.?\b", "AV"),
    (r"\bAVENIDA\b", "AV"),
    (r"\bCALLE\b", "C"),
    (r"\bC\.?\b", "C"),
    (r"\bESQ\.?\b", "ESQ"),
    (r"\bESQUINA\b", "ESQ"),
)


def normalize_domicilio(raw: str) -> str:
    """Mayúsculas, espacios simples, abreviaturas usuales."""
    s = normalize_persona_razon(raw)
    for pat, repl in _STREET_ABBR:
        s = re.sub(pat, repl, s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def resolve_titular_norm(nombre_fantasia: str, razon_social: str) -> str:
    """Titular: razón social prioritaria; si no, nombre de fantasía."""
    rs = normalize_persona_razon(razon_social)
    if rs:
        return rs
    return normalize_persona_razon(nombre_fantasia)


def mask_acta_correlacion(acta_num: str) -> str:
    """Hash de correlación para salidas (sin exponer número completo)."""
    if not acta_num:
        return ""
    return hashlib.sha256(f"acta:{acta_num}".encode("utf-8")).hexdigest()[:16]


def acta_index_key(acta_tipo: str, num: str, anio: int) -> str:
    """Clave canónica NOTIFICACION|num|año."""
    n = _normalize_acta_num(num)
    return f"{acta_tipo}|{n}|{anio}"


def build_acta_indexes(
    historic_rows: Sequence[RowSnapshot],
) -> Tuple[Dict[str, List[ActaIndexRecord]], Dict[Tuple[str, str], List[ActaIndexRecord]]]:
    """
    Construye índices por clave acta+año y por (tipo, número) para búsqueda amplia.

    Returns:
        (index_por_clave_completa, index_por_tipo_numero).
    """
    by_key: Dict[str, List[ActaIndexRecord]] = defaultdict(list)
    by_tipo_num: Dict[Tuple[str, str], List[ActaIndexRecord]] = defaultdict(list)

    for snap in historic_rows:
        if not snap.fecha_inspec or not snap.ec5_uuid:
            continue
        anio = snap.fecha_inspec.year
        base = ActaIndexRecord(
            ec5_uuid=snap.ec5_uuid,
            fecha=snap.fecha_inspec,
            acta_tipo="",
            acta_num="",
            acta_anio=anio,
            doc_norm=snap.doc_norm,
            dom_norm=snap.dom_norm,
            titular_norm=snap.titular_norm,
        )
        if snap.acta_notificacion_num:
            rec = ActaIndexRecord(
                ec5_uuid=base.ec5_uuid,
                fecha=base.fecha,
                acta_tipo=_ACTA_TIPO_NOTIFICACION,
                acta_num=snap.acta_notificacion_num,
                acta_anio=anio,
                doc_norm=base.doc_norm,
                dom_norm=base.dom_norm,
                titular_norm=base.titular_norm,
            )
            k = acta_index_key(_ACTA_TIPO_NOTIFICACION, rec.acta_num, anio)
            by_key[k].append(rec)
            by_tipo_num[(_ACTA_TIPO_NOTIFICACION, rec.acta_num)].append(rec)
        if snap.acta_comprobacion_num:
            rec = ActaIndexRecord(
                ec5_uuid=base.ec5_uuid,
                fecha=base.fecha,
                acta_tipo=_ACTA_TIPO_COMPROBACION,
                acta_num=snap.acta_comprobacion_num,
                acta_anio=anio,
                doc_norm=base.doc_norm,
                dom_norm=base.dom_norm,
                titular_norm=base.titular_norm,
            )
            k = acta_index_key(_ACTA_TIPO_COMPROBACION, rec.acta_num, anio)
            by_key[k].append(rec)
            by_tipo_num[(_ACTA_TIPO_COMPROBACION, rec.acta_num)].append(rec)

    return by_key, by_tipo_num


def build_expediente_index(
    historic_rows: Sequence[RowSnapshot],
) -> Dict[str, List[ActaIndexRecord]]:
    """Índice expediente|año|oficio → filas con comprobación."""
    idx: Dict[str, List[ActaIndexRecord]] = defaultdict(list)
    for snap in historic_rows:
        if not snap.acta_comprobacion_num or not snap.fecha_inspec:
            continue
        anio = snap.fecha_inspec.year
        rec = ActaIndexRecord(
            ec5_uuid=snap.ec5_uuid,
            fecha=snap.fecha_inspec,
            acta_tipo=_ACTA_TIPO_COMPROBACION,
            acta_num=snap.acta_comprobacion_num,
            acta_anio=anio,
            doc_norm=snap.doc_norm,
            dom_norm=snap.dom_norm,
            titular_norm=snap.titular_norm,
        )
        for clave in snap.expediente_claves:
            idx[clave].append(rec)
    return idx


def _identity_match(rein: RowSnapshot, origen: ActaIndexRecord) -> Tuple[bool, str]:
    """
    Confirma identidad: DNI exacto o domicilio + titular.

    Returns:
        (ok, motivo_tecnico si falla).
    """
    if rein.doc_norm and origen.doc_norm:
        if rein.doc_norm == origen.doc_norm:
            return True, ""
        return False, "conflicto_documento"

    dom_ok = bool(rein.dom_norm and origen.dom_norm and rein.dom_norm == origen.dom_norm)
    tit_ok = bool(
        rein.titular_norm and origen.titular_norm and rein.titular_norm == origen.titular_norm
    )
    if dom_ok and tit_ok:
        return True, ""
    if dom_ok and not tit_ok:
        return False, "conflicto_titular"
    if tit_ok and not dom_ok:
        return False, "conflicto_domicilio"
    return False, "identidad_insuficiente"


def _filter_candidates(
    candidates: List[ActaIndexRecord],
    rein: RowSnapshot,
) -> Tuple[List[ActaIndexRecord], str]:
    """Filtra por cronología e identidad; detecta conflictos."""
    if not candidates:
        return [], "referencia_previa_inexistente"

    by_uuid: Dict[str, ActaIndexRecord] = {}
    for c in candidates:
        by_uuid.setdefault(c.ec5_uuid, c)
    if len(by_uuid) > 1:
        docs = {c.doc_norm for c in by_uuid.values() if c.doc_norm}
        if len(docs) > 1:
            return [], "referencia_previa_ambigua"
        return [], "referencia_previa_ambigua"

    cand = next(iter(by_uuid.values()))
    if rein.fecha_inspec and cand.fecha >= rein.fecha_inspec:
        return [], "cronologia_invalida"

    ok, motivo = _identity_match(rein, cand)
    if not ok:
        return [], motivo
    return [cand], ""


def _lookup_notificacion(
    rein: RowSnapshot,
    by_tipo_num: Mapping[Tuple[str, str], List[ActaIndexRecord]],
) -> Tuple[List[ActaIndexRecord], str, str]:
    ref = rein.ref_notificacion_previa or rein.acta_notificacion_num
    ref = _normalize_acta_num(ref)
    if not ref:
        return [], "referencia_previa_ausente", ""
    cands = [c for c in by_tipo_num.get((_ACTA_TIPO_NOTIFICACION, ref), []) if c.ec5_uuid != rein.ec5_uuid]
    filtered, motivo = _filter_candidates(cands, rein)
    return filtered, motivo, ref


def _lookup_comprobacion(
    rein: RowSnapshot,
    by_tipo_num: Mapping[Tuple[str, str], List[ActaIndexRecord]],
    expediente_index: Mapping[str, List[ActaIndexRecord]],
) -> Tuple[List[ActaIndexRecord], str, str]:
    ref = _normalize_acta_num(rein.ref_comprobacion_previa)
    if ref:
        cands = [
            c for c in by_tipo_num.get((_ACTA_TIPO_COMPROBACION, ref), []) if c.ec5_uuid != rein.ec5_uuid
        ]
        filtered, motivo = _filter_candidates(cands, rein)
        return filtered, motivo, ref

    for clave in rein.expediente_claves:
        raw_cands = [c for c in expediente_index.get(clave, []) if c.ec5_uuid != rein.ec5_uuid]
        uuids = {c.ec5_uuid for c in raw_cands}
        if len(uuids) > 1:
            return [], "referencia_expediente_ambigua", f"exp:{clave}"
        if len(uuids) == 1:
            filtered, motivo = _filter_candidates(raw_cands, rein)
            return filtered, motivo, f"exp:{clave}"

    return [], "referencia_previa_ausente", ""


def _resultado_cadena_notificacion(rein: RowSnapshot) -> ResultadoCadenaEsperado:
    if rein.acta_comprobacion_num:
        return ResultadoCadenaEsperado.CERRADA_CON_COMPROBACION
    return ResultadoCadenaEsperado.CERRADA_SIN_COMPROBACION


def _resultado_cadena_comprobacion(rein: RowSnapshot) -> ResultadoCadenaEsperado:
    if rein.acta_comprobacion_num:
        return ResultadoCadenaEsperado.CERRADA_CON_COMPROBACION
    return ResultadoCadenaEsperado.CIRCUITO_OFICIO_RESUELTO


def analizar_cadena_reinspeccion(
    rein: RowSnapshot,
    by_tipo_num: Mapping[Tuple[str, str], List[ActaIndexRecord]],
    expediente_index: Mapping[str, List[ActaIndexRecord]],
) -> CadenaVinculo:
    """
    Determina estado de vínculo y resultado de cadena para una fila de reinspección.

    No infiere por cercanía de fechas ni rubro.
    """
    tipo = rein.tipo_inspeccion
    tipo_origen = ""
    ref_hash = ""
    prev_hash = ""

    if _es_reinspeccion_notificacion(tipo):
        tipo_origen = _ACTA_TIPO_NOTIFICACION
        cands, motivo, ref = _lookup_notificacion(rein, by_tipo_num)
        ref_hash = mask_acta_correlacion(ref)
    elif _es_reinspeccion_oficio(tipo):
        tipo_origen = _ACTA_TIPO_COMPROBACION
        cands, motivo, ref = _lookup_comprobacion(rein, by_tipo_num, expediente_index)
        ref_hash = mask_acta_correlacion(ref) if ref and not ref.startswith("exp:") else ref
    else:
        return CadenaVinculo(
            ec5_uuid=rein.ec5_uuid,
            fuente_previa_uuid="",
            fecha_inspec=rein.fecha_inspec,
            tipo_inspeccion=tipo,
            estado_vinculo=EstadoVinculo.SIN_REFERENCIA_PREVIA,
            tipo_origen_esperado="",
            resultado_cadena_esperado=ResultadoCadenaEsperado.REVISAR,
            motivo_revision="no_es_reinspeccion",
            acta_referencia_hash="",
            previa_acta_hash="",
            es_reinspeccion=False,
        )

    if not cands:
        estado = EstadoVinculo.SIN_REFERENCIA_PREVIA
        if motivo in ("conflicto_documento",):
            estado = EstadoVinculo.VINCULO_CONFLICTIVO
        elif motivo in ("referencia_previa_ambigua", "referencia_expediente_ambigua"):
            estado = EstadoVinculo.VINCULO_CONFLICTIVO
        elif motivo in ("conflicto_domicilio", "conflicto_titular"):
            estado = EstadoVinculo.VINCULO_CONFLICTIVO
        elif motivo == "cronologia_invalida":
            estado = EstadoVinculo.VINCULO_CONFLICTIVO
        elif motivo == "identidad_insuficiente":
            estado = EstadoVinculo.VINCULO_PARCIAL
        elif motivo.startswith("referencia"):
            estado = EstadoVinculo.SIN_REFERENCIA_PREVIA
        return CadenaVinculo(
            ec5_uuid=rein.ec5_uuid,
            fuente_previa_uuid="",
            fecha_inspec=rein.fecha_inspec,
            tipo_inspeccion=tipo,
            estado_vinculo=estado,
            tipo_origen_esperado=tipo_origen,
            resultado_cadena_esperado=ResultadoCadenaEsperado.REVISAR,
            motivo_revision=motivo or "sin_vinculo",
            acta_referencia_hash=ref_hash,
            previa_acta_hash="",
        )

    origen = cands[0]
    prev_hash = mask_acta_correlacion(origen.acta_num)
    if tipo_origen == _ACTA_TIPO_NOTIFICACION:
        resultado = _resultado_cadena_notificacion(rein)
    else:
        resultado = _resultado_cadena_comprobacion(rein)

    return CadenaVinculo(
        ec5_uuid=rein.ec5_uuid,
        fuente_previa_uuid=origen.ec5_uuid,
        fecha_inspec=rein.fecha_inspec,
        tipo_inspeccion=tipo,
        estado_vinculo=EstadoVinculo.VINCULO_CONFIABLE,
        tipo_origen_esperado=tipo_origen,
        resultado_cadena_esperado=resultado,
        motivo_revision="",
        acta_referencia_hash=ref_hash,
        previa_acta_hash=prev_hash,
        origen_evidencia_vinculo="EPICOLLECT",
    )


def aplicar_cadenas_a_filas(
    filas: Sequence[RowSnapshot],
    cutoff: date,
    by_tipo_num: Mapping[Tuple[str, str], List[ActaIndexRecord]],
    expediente_index: Mapping[str, List[ActaIndexRecord]],
) -> CadenasHistoricasResult:
    """
    Analiza reinspecciones históricas y actualiza campos de cadena en cada fila.

    Ajusta ``decision`` a REVISAR si el vínculo no es confiable.
    """
    vinculos: List[CadenaVinculo] = []
    reins_tipo: Counter = Counter()
    revisiones: Counter = Counter()
    conf_doc = conf_dom = conf_tit = conf_crono = 0
    notif_cerradas = 0
    comp_resueltas = 0
    confiables = 0

    for snap in filas:
        if not snap.fecha_inspec or snap.fecha_inspec >= cutoff:
            continue
        if not (_es_reinspeccion_notificacion(snap.tipo_inspeccion) or _es_reinspeccion_oficio(snap.tipo_inspeccion)):
            continue

        reins_tipo[snap.tipo_inspeccion or "(vacío)"] += 1
        cadena = analizar_cadena_reinspeccion(snap, by_tipo_num, expediente_index)
        vinculos.append(cadena)

        snap.estado_vinculo = cadena.estado_vinculo.value
        snap.tipo_origen_esperado = cadena.tipo_origen_esperado
        snap.resultado_cadena_esperado = cadena.resultado_cadena_esperado.value
        snap.fuente_previa_uuid = cadena.fuente_previa_uuid
        snap.origen_evidencia_vinculo = cadena.origen_evidencia_vinculo
        snap.fuente_previa_legacy_hash = cadena.fuente_previa_legacy_hash
        if cadena.motivo_revision:
            snap.motivo_revision = cadena.motivo_revision

        if cadena.estado_vinculo == EstadoVinculo.VINCULO_CONFIABLE:
            confiables += 1
            snap.previa_ec5_uuid = cadena.fuente_previa_uuid
            if _es_reinspeccion_notificacion(snap.tipo_inspeccion):
                snap.decision = Decision.CANDIDATA_REINSPECCION_NOTIFICACION
                if cadena.resultado_cadena_esperado in (
                    ResultadoCadenaEsperado.CERRADA_SIN_COMPROBACION,
                    ResultadoCadenaEsperado.CERRADA_CON_COMPROBACION,
                ):
                    notif_cerradas += 1
            else:
                snap.decision = Decision.CANDIDATA_REINSPECCION_OFICIO
                if cadena.resultado_cadena_esperado == ResultadoCadenaEsperado.CIRCUITO_OFICIO_RESUELTO:
                    comp_resueltas += 1
                elif cadena.resultado_cadena_esperado == ResultadoCadenaEsperado.CERRADA_CON_COMPROBACION:
                    comp_resueltas += 1
        else:
            snap.decision = Decision.REVISAR
            revisiones[cadena.motivo_revision or cadena.estado_vinculo.value] += 1
            if cadena.motivo_revision == "conflicto_documento":
                conf_doc += 1
            elif cadena.motivo_revision == "conflicto_domicilio":
                conf_dom += 1
            elif cadena.motivo_revision == "conflicto_titular":
                conf_tit += 1
            elif cadena.motivo_revision == "cronologia_invalida":
                conf_crono += 1

    return CadenasHistoricasResult(
        vinculos=vinculos,
        reinspecciones_por_tipo=dict(reins_tipo),
        vinculos_confiables=confiables,
        revisiones_por_motivo=dict(revisiones),
        notificaciones_cerradas_historicas=notif_cerradas,
        comprobaciones_circuito_oficio_resuelto=comp_resueltas,
        conflictos_documento=conf_doc,
        conflictos_domicilio=conf_dom,
        conflictos_titular=conf_tit,
        conflictos_cronologia=conf_crono,
    )


def cadena_to_csv_row(c: CadenaVinculo) -> Dict[str, str]:
    """Fila CSV de vínculo sin PII."""
    return {
        "ec5_uuid": c.ec5_uuid,
        "fuente_previa_uuid": c.fuente_previa_uuid,
        "fecha_inspec_iso": c.fecha_inspec.isoformat() if c.fecha_inspec else "",
        "tipo_inspeccion_epi": c.tipo_inspeccion,
        "estado_vinculo": c.estado_vinculo.value,
        "tipo_origen_esperado": c.tipo_origen_esperado,
        "resultado_cadena_esperado": c.resultado_cadena_esperado.value,
        "motivo_revision": c.motivo_revision,
        "acta_referencia_hash": c.acta_referencia_hash,
        "previa_acta_hash": c.previa_acta_hash,
    }


def _assert_vinculo_row_safe(row: Mapping[str, str]) -> None:
    joined = " ".join(row.values()).lower()
    if "http://" in joined or "https://" in joined:
        raise ValueError("salida contiene URL")


def write_cadenas_outputs(result: CadenasHistoricasResult, output_dir: Path) -> None:
    """Escribe resumen JSON y CSVs de vínculos confiables / a revisar."""
    output_dir.mkdir(parents=True, exist_ok=True)

    confiables = [v for v in result.vinculos if v.estado_vinculo == EstadoVinculo.VINCULO_CONFIABLE]
    revisar = [v for v in result.vinculos if v.estado_vinculo != EstadoVinculo.VINCULO_CONFIABLE]

    for name, rows in (
        ("vinculos_confiables.csv", confiables),
        ("vinculos_a_revisar.csv", revisar),
    ):
        path = output_dir / name
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(_VINCULO_CSV_FIELDS))
            w.writeheader()
            for v in rows:
                out = cadena_to_csv_row(v)
                _assert_vinculo_row_safe(out)
                w.writerow(out)

    resumen = {
        "reinspecciones_por_tipo": result.reinspecciones_por_tipo,
        "vinculos_confiables": result.vinculos_confiables,
        "revisiones_por_motivo": result.revisiones_por_motivo,
        "notificaciones_cerradas_historicamente": result.notificaciones_cerradas_historicas,
        "comprobaciones_circuito_oficio_resuelto": result.comprobaciones_circuito_oficio_resuelto,
        "conflictos": {
            "documento": result.conflictos_documento,
            "domicilio": result.conflictos_domicilio,
            "titular": result.conflictos_titular,
            "cronologia": result.conflictos_cronologia,
        },
    }
    with (output_dir / "resumen_cadenas_historicas.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
