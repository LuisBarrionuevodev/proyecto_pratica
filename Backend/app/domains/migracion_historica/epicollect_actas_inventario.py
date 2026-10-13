"""
Inventario read-only de actas históricas EpiCollect (dry-run).

No usa Flask, SQLAlchemy ni red. Solo lectura de CSV y escritura de artefactos locales.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# --- Columnas lógicas permitidas (manifiesto / lectura) ---
ALLOWED_LOGICAL_COLUMNS: Tuple[str, ...] = (
    "ec5_uuid",
    "1_Fecha_de_la_inspec",
    "2_Orden_de_Trabajo_N",
    "3_Qu_inspectores_con",
    "4_Domicilio",
    "5_Pudo_realizar_la_i",
    "6_Tipo_de_inspeccin",
    "8_Numero_de_la_Notif",
    "10_Se_dio_cumplimien",
    "14_Nombre_de_Fantasa",
    "15_Razn_Socialnombre",
    "16_DNI_del_Contribuy",
    "17_Rubro",
    "80_Realizo_Acta_de_I",
    "82_Numero_del_Acta_d",
    "84_Realizo_Acta_de_N",
    "86_Numero_del_Acta_d",
    "87_Infracciones",
    "91_Realizo_Acta_de_C",
    "93_Numero_del_Acta_d",
    "94_Infracciones",
    "99_Realizo_Acta_de_C",
    "101_Numero_de_Acta_d",
    "103_Realizo_Acta_de_",
    "105_Numero_de_Acta_d",
    "107_Kilos_Decomisado",
    "108_Realizo_Desnatur",
    "114_Observaciones_so",
    "115_Pego_Faja_de_Cla",
    "117_Numero_de_Expedi",
    "118_Ao",
    "119_Numero_de_Oficio",
    "251_Porque_no_realiz",
    "255_Describe_porque_",
)

# Índices de bloque secundario (reinspección / visitas repetidas en el mismo entry).
_SECONDARY_ACTA_BLOCK_START = 192

_MEDIA_URL_RE = re.compile(
    r"(^https?://)|(_Foto|Foto_|_Video|Video_|uploaded_at|/media/)",
    re.IGNORECASE,
)


class Decision(str, Enum):
    CANDIDATA_ACTUACION_INICIAL = "CANDIDATA_ACTUACION_INICIAL"
    CANDIDATA_CON_NOTIFICACION = "CANDIDATA_CON_NOTIFICACION"
    CANDIDATA_CON_COMPROBACION = "CANDIDATA_CON_COMPROBACION"
    CANDIDATA_CON_AMBAS_ACTAS = "CANDIDATA_CON_AMBAS_ACTAS"
    CANDIDATA_REINSPECCION_NOTIFICACION = "CANDIDATA_REINSPECCION_NOTIFICACION"
    CANDIDATA_REINSPECCION_OFICIO = "CANDIDATA_REINSPECCION_OFICIO"
    REVISAR = "REVISAR"
    EXCLUIR_POST_CORTE = "EXCLUIR_POST_CORTE"
    EXCLUIR_NO_OPERATIVA = "EXCLUIR_NO_OPERATIVA"


OUTPUT_CSV_FIELDS: Tuple[str, ...] = (
    "ec5_uuid",
    "fecha_inspec_iso",
    "decision",
    "tipo_inspeccion_epi",
    "odt_historica_ref",
    "pudo_realizar",
    "acta_inspeccion_num",
    "acta_notificacion_num",
    "acta_comprobacion_num",
    "acta_clausura_num",
    "acta_decomiso_num",
    "ref_notificacion_previa",
    "ref_comprobacion_previa",
    "previa_ec5_uuid",
    "motivo_revision",
    "tiene_kilos_decomiso",
    "tiene_faja_clausura",
    "tiene_desnaturalizacion",
)


@dataclass
class RowSnapshot:
    """Datos mínimos extraídos de una fila (sin PII en export)."""

    ec5_uuid: str
    fecha_inspec: Optional[date]
    fecha_parse_note: str
    tipo_inspeccion: str
    odt_ref: str
    pudo_realizar: str
    domicilio_presente: bool
    acta_inspeccion_num: str
    acta_notificacion_num: str
    acta_comprobacion_num: str
    acta_clausura_num: str
    acta_decomiso_num: str
    ref_notificacion_previa: str
    ref_comprobacion_previa: str
    kilos_decomiso: str
    faja_clausura: str
    desnaturalizacion: str
    motivo_no_realizacion: str
    expediente_claves: List[str] = field(default_factory=list)
    decision: Decision = Decision.REVISAR
    motivo_revision: str = ""
    previa_ec5_uuid: str = ""


@dataclass
class InventarioResult:
    source_sha256: str
    cutoff: date
    total_filas_leidas: int
    total_anterior_corte: int
    por_tipo_epi: Dict[str, int]
    por_decision: Dict[str, int]
    conteos_actas: Dict[str, int]
    reinspeccion_vinculables: int
    reinspeccion_no_vinculables: int
    duplicados_acta: Dict[str, List[str]]
    filas: List[RowSnapshot] = field(default_factory=list)
    date_format_samples: Counter = field(default_factory=Counter)


def sha256_file(path: Path) -> str:
    """Calcula SHA-256 de un archivo en streaming."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_inspection_date(raw: str) -> Tuple[Optional[date], str]:
    """
    Parsea fecha de inspección (YYYY-MM-DD o DD/MM/YYYY).

    Returns:
        (fecha o None, etiqueta de formato detectado / error).
    """
    s = (raw or "").strip()
    if not s:
        return None, "vacio"
    for fmt, label in (("%Y-%m-%d", "YYYY-MM-DD"), ("%d/%m/%Y", "DD/MM/YYYY")):
        try:
            return datetime.strptime(s, fmt).date(), label
        except ValueError:
            continue
    return None, "invalido"


def _is_si(value: str) -> bool:
    v = (value or "").strip().upper()
    return v in ("SI", "SÍ", "S", "YES", "1")


def _normalize_acta_num(value: str) -> str:
    """Normaliza número de acta para conciliación (solo dígitos, sin ceros a la izquierda)."""
    s = (value or "").strip()
    if not s:
        return ""
    digits = re.sub(r"\D+", "", s)
    if not digits:
        return re.sub(r"\s+", "", s)
    return digits.lstrip("0") or "0"


def _header_indices(hdr: Sequence[str]) -> Dict[str, List[int]]:
    by_name: Dict[str, List[int]] = defaultdict(list)
    for i, name in enumerate(hdr):
        if _MEDIA_URL_RE.search(name):
            continue
        by_name[name].append(i)
    return by_name


def _first_index(by_name: Mapping[str, List[int]], col: str) -> Optional[int]:
    lst = by_name.get(col)
    return lst[0] if lst else None


def _indices_starting_with(hdr: Sequence[str], prefix: str, min_index: int = 0) -> List[int]:
    return [i for i, h in enumerate(hdr) if h.startswith(prefix) and i >= min_index]


def _cell(row: Sequence[str], idx: Optional[int]) -> str:
    if idx is None or idx >= len(row):
        return ""
    return (row[idx] or "").strip()


def _coalesce_acta_field(
    row: Sequence[str],
    hdr: Sequence[str],
    by_name: Mapping[str, List[int]],
    primary_col: str,
    prefix_fallback: str,
) -> str:
    """Toma el primer valor no vacío del bloque primario o secundario."""
    val = _cell(row, _first_index(by_name, primary_col))
    if val:
        return val
    for idx in _indices_starting_with(hdr, prefix_fallback, _SECONDARY_ACTA_BLOCK_START):
        v = _cell(row, idx)
        if v:
            return v
    return ""


_EXPEDIENTE_TRIPLET_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("117_Numero_de_Expedi", "118_Ao", "119_Numero_de_Oficio"),
    ("131_Numero_de_Expedi", "132_Ao", "133_Numero_de_Oficio"),
    ("145_Numero_de_Expedi", "146_Ao", "147_Numero_de_Oficio"),
)


def _extract_expediente_claves(
    row: Sequence[str],
    by_name: Mapping[str, List[int]],
) -> List[str]:
    claves: List[str] = []
    for exp_c, anio_c, of_c in _EXPEDIENTE_TRIPLET_SPECS:
        exp = _normalize_acta_num(_cell(row, _first_index(by_name, exp_c)))
        anio = _normalize_acta_num(_cell(row, _first_index(by_name, anio_c)))
        ofi = _normalize_acta_num(_cell(row, _first_index(by_name, of_c)))
        if exp and anio and ofi:
            claves.append(f"{exp}|{anio}|{ofi}")
    return list(dict.fromkeys(claves))


def _coalesce_si_field(
    row: Sequence[str],
    hdr: Sequence[str],
    by_name: Mapping[str, List[int]],
    primary_col: str,
    prefix_fallback: str,
) -> bool:
    raw = _coalesce_acta_field(row, hdr, by_name, primary_col, prefix_fallback)
    if raw:
        return _is_si(raw)
    for idx in _indices_starting_with(hdr, prefix_fallback, _SECONDARY_ACTA_BLOCK_START):
        if _is_si(_cell(row, idx)):
            return True
    primary_idx = _first_index(by_name, primary_col)
    return _is_si(_cell(row, primary_idx))


def extract_row_snapshot(
    row: Sequence[str],
    hdr: Sequence[str],
    by_name: Mapping[str, List[int]],
) -> RowSnapshot:
    """Extrae snapshot sin escribir PII en logs."""
    fecha_raw = _cell(row, _first_index(by_name, "1_Fecha_de_la_inspec"))
    fecha, fmt_note = parse_inspection_date(fecha_raw)
    dom = _cell(row, _first_index(by_name, "4_Domicilio"))

    inspeccion_num = _normalize_acta_num(
        _coalesce_acta_field(row, hdr, by_name, "82_Numero_del_Acta_d", "217_Numero_del_Acta_")
    )
    notif_si = _coalesce_si_field(row, hdr, by_name, "84_Realizo_Acta_de_N", "219_Realizo_Acta_de_")
    notif_num = _normalize_acta_num(
        _coalesce_acta_field(row, hdr, by_name, "86_Numero_del_Acta_d", "221_Numero_del_Acta_")
    )
    if not notif_si:
        notif_num = ""

    comp_si = _coalesce_si_field(row, hdr, by_name, "91_Realizo_Acta_de_C", "226_Realizo_Acta_de_")
    comp_num = _normalize_acta_num(
        _coalesce_acta_field(row, hdr, by_name, "93_Numero_del_Acta_d", "228_Numero_del_Acta_")
    )
    if not comp_si:
        comp_num = ""

    claus_si = _coalesce_si_field(row, hdr, by_name, "99_Realizo_Acta_de_C", "234_Realizo_Acta_de_")
    claus_num = _normalize_acta_num(
        _coalesce_acta_field(row, hdr, by_name, "101_Numero_de_Acta_d", "236_Numero_de_Acta_d")
    )
    if not claus_si:
        claus_num = ""

    deco_si = _coalesce_si_field(row, hdr, by_name, "103_Realizo_Acta_de_", "238_Realizo_Acta_de_")
    deco_num = _normalize_acta_num(
        _coalesce_acta_field(row, hdr, by_name, "105_Numero_de_Acta_d", "240_Numero_de_Acta_d")
    )
    if not deco_si:
        deco_num = ""

    inspeccion_si = _coalesce_si_field(row, hdr, by_name, "80_Realizo_Acta_de_I", "215_Realizo_Acta_de_")
    if not inspeccion_si and not inspeccion_num:
        inspeccion_num = ""

    ref_notif = _normalize_acta_num(_cell(row, _first_index(by_name, "8_Numero_de_la_Notif")))

    motivo_no = _cell(row, _first_index(by_name, "251_Porque_no_realiz"))
    if not motivo_no:
        motivo_no = _cell(row, _first_index(by_name, "255_Describe_porque_"))

    return RowSnapshot(
        ec5_uuid=_cell(row, _first_index(by_name, "ec5_uuid")),
        fecha_inspec=fecha,
        fecha_parse_note=fmt_note,
        tipo_inspeccion=_cell(row, _first_index(by_name, "6_Tipo_de_inspeccin")),
        odt_ref=_normalize_acta_num(_cell(row, _first_index(by_name, "2_Orden_de_Trabajo_N"))),
        pudo_realizar=_cell(row, _first_index(by_name, "5_Pudo_realizar_la_i")),
        domicilio_presente=bool(dom),
        acta_inspeccion_num=inspeccion_num if inspeccion_si or inspeccion_num else "",
        acta_notificacion_num=notif_num,
        acta_comprobacion_num=comp_num,
        acta_clausura_num=claus_num,
        acta_decomiso_num=deco_num,
        ref_notificacion_previa=ref_notif,
        ref_comprobacion_previa="",
        expediente_claves=_extract_expediente_claves(row, by_name),
        kilos_decomiso=_cell(row, _first_index(by_name, "107_Kilos_Decomisado")),
        faja_clausura=_cell(row, _first_index(by_name, "115_Pego_Faja_de_Cla")),
        desnaturalizacion=_cell(row, _first_index(by_name, "108_Realizo_Desnatur")),
        motivo_no_realizacion=motivo_no,
    )


def _tipo_norm(tipo: str) -> str:
    return (tipo or "").strip().casefold()


def _es_reinspeccion_notificacion(tipo: str) -> bool:
    t = _tipo_norm(tipo)
    return "reinspecci" in t and "notific" in t


def _es_reinspeccion_oficio(tipo: str) -> bool:
    t = _tipo_norm(tipo)
    if "reinspecci" in t and "oficio" in t:
        return True
    if "verificar" in t and "informar" in t:
        return True
    return False


def _es_ratificacion(tipo: str) -> bool:
    t = _tipo_norm(tipo)
    return "ratificaci" in t


def _datos_minimos_inicial(snap: RowSnapshot) -> bool:
    if not snap.ec5_uuid:
        return False
    if snap.fecha_inspec is None:
        return False
    if not snap.domicilio_presente:
        return False
    if _is_si(snap.pudo_realizar):
        return bool(snap.acta_inspeccion_num) or snap.acta_notificacion_num or snap.acta_comprobacion_num
    if snap.motivo_no_realizacion:
        return True
    return False


def _resolver_previa_comprobacion(
    snap: RowSnapshot,
    comp_index: Mapping[str, List[str]],
    expediente_index: Mapping[str, List[str]],
) -> Tuple[str, str, str]:
    """
    Intenta vincular reinspección/oficio a comprobación previa por número o clave expediente.

    Returns:
        (ec5_uuid previo, motivo error, referencia usada para trazabilidad).
    """
    ref_num = snap.ref_comprobacion_previa
    if ref_num:
        uuid_prev, motivo = _resolver_previa(ref_num, comp_index, snap.ec5_uuid)
        return uuid_prev, motivo, ref_num

    for clave in snap.expediente_claves:
        hits = [u for u in expediente_index.get(clave, []) if u != snap.ec5_uuid]
        if len(set(hits)) == 1:
            return hits[0], "", f"exp:{clave}"
        if len(set(hits)) > 1:
            return "", "referencia_expediente_ambigua", f"exp:{clave}"
    return "", "referencia_previa_ausente", ""


def _resolver_previa(
    ref: str,
    index: Mapping[str, List[str]],
    self_uuid: str,
) -> Tuple[str, str]:
    """
    Resuelve ec5_uuid previo por número de acta.

    Returns:
        (uuid único o vacío, motivo si no único).
    """
    if not ref:
        return "", "referencia_previa_ausente"
    hits = [u for u in index.get(ref, []) if u != self_uuid]
    if not hits:
        return "", "referencia_previa_inexistente"
    if len(set(hits)) > 1:
        return "", "referencia_previa_ambigua"
    return hits[0], ""


def classify_row(
    snap: RowSnapshot,
    cutoff: date,
    notif_index: Mapping[str, List[str]],
    comp_index: Mapping[str, List[str]],
    expediente_index: Mapping[str, List[str]],
) -> RowSnapshot:
    """Asigna decisión y motivo de revisión."""
    if snap.fecha_inspec is None:
        snap.decision = Decision.REVISAR
        snap.motivo_revision = "fecha_invalida"
        return snap
    if snap.fecha_inspec >= cutoff:
        snap.decision = Decision.EXCLUIR_POST_CORTE
        return snap

    tipo = snap.tipo_inspeccion
    if not tipo.strip():
        if not _is_si(snap.pudo_realizar):
            snap.decision = Decision.EXCLUIR_NO_OPERATIVA
            snap.motivo_revision = "tipo_vacio_sin_visita"
            return snap
        snap.decision = Decision.REVISAR
        snap.motivo_revision = "tipo_vacio"
        return snap

    if _es_reinspeccion_notificacion(tipo):
        ref = snap.ref_notificacion_previa or snap.acta_notificacion_num
        uuid_prev, motivo = _resolver_previa(ref, notif_index, snap.ec5_uuid)
        if uuid_prev:
            snap.previa_ec5_uuid = uuid_prev
            snap.decision = Decision.CANDIDATA_REINSPECCION_NOTIFICACION
        else:
            snap.decision = Decision.REVISAR
            snap.motivo_revision = motivo or "reinspeccion_notif_sin_vinculo"
        return snap

    if _es_reinspeccion_oficio(tipo) or _es_ratificacion(tipo):
        if _es_reinspeccion_oficio(tipo):
            uuid_prev, motivo, ref_usada = _resolver_previa_comprobacion(
                snap, comp_index, expediente_index
            )
            if uuid_prev:
                snap.previa_ec5_uuid = uuid_prev
                snap.ref_comprobacion_previa = ref_usada
                snap.decision = Decision.CANDIDATA_REINSPECCION_OFICIO
            else:
                snap.decision = Decision.REVISAR
                snap.motivo_revision = motivo or "reinspeccion_oficio_sin_vinculo"
            return snap
        # Ratificación: actuación con comprobación/clausura/decomiso, sin auto-reinspección
        if not _datos_minimos_inicial(snap):
            snap.decision = Decision.REVISAR
            snap.motivo_revision = "datos_minimos_insuficientes"
            return snap
        snap.decision = _decision_actas_en_visita(snap)
        return snap

    if not _datos_minimos_inicial(snap):
        snap.decision = Decision.REVISAR
        snap.motivo_revision = "datos_minimos_insuficientes"
        return snap

    snap.decision = _decision_actas_en_visita(snap)
    return snap


def _decision_actas_en_visita(snap: RowSnapshot) -> Decision:
    tiene_n = bool(snap.acta_notificacion_num)
    tiene_c = bool(snap.acta_comprobacion_num)
    if tiene_n and tiene_c:
        return Decision.CANDIDATA_CON_AMBAS_ACTAS
    if tiene_n:
        return Decision.CANDIDATA_CON_NOTIFICACION
    if tiene_c:
        return Decision.CANDIDATA_CON_COMPROBACION
    return Decision.CANDIDATA_ACTUACION_INICIAL


def _register_acta(index: Dict[str, List[str]], num: str, ec5_uuid: str) -> None:
    if not num or not ec5_uuid:
        return
    index.setdefault(num, []).append(ec5_uuid)


def inventariar_csv(
    input_path: Path,
    cutoff: date,
) -> InventarioResult:
    """
    Lee el CSV EpiCollect y clasifica filas históricas (< cutoff).

    Args:
        input_path: ruta al export CSV (no se modifica).
        cutoff: fecha de corte; filas con fecha >= cutoff quedan EXCLUIR_POST_CORTE.

    Returns:
        InventarioResult con métricas y snapshots por fila.
    """
    source_sha = sha256_file(input_path)
    snapshots: List[RowSnapshot] = []
    date_formats: Counter = Counter()

    with input_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        hdr = next(reader)
        by_name = _header_indices(hdr)
        for row in reader:
            snap = extract_row_snapshot(row, hdr, by_name)
            if snap.fecha_parse_note not in ("vacio", "invalido"):
                date_formats[snap.fecha_parse_note] += 1
            snapshots.append(snap)

    historic = [s for s in snapshots if s.fecha_inspec and s.fecha_inspec < cutoff]

    notif_index: Dict[str, List[str]] = defaultdict(list)
    comp_index: Dict[str, List[str]] = defaultdict(list)
    expediente_index: Dict[str, List[str]] = defaultdict(list)
    for s in historic:
        _register_acta(notif_index, s.acta_notificacion_num, s.ec5_uuid)
        if s.acta_comprobacion_num:
            _register_acta(comp_index, s.acta_comprobacion_num, s.ec5_uuid)
            for clave in s.expediente_claves:
                expediente_index[clave].append(s.ec5_uuid)

    reins_vinc = 0
    reins_no = 0
    for s in snapshots:
        classify_row(s, cutoff, notif_index, comp_index, expediente_index)
        if s.decision in (
            Decision.CANDIDATA_REINSPECCION_NOTIFICACION,
            Decision.CANDIDATA_REINSPECCION_OFICIO,
        ):
            if s.previa_ec5_uuid:
                reins_vinc += 1
            else:
                reins_no += 1
        elif s.decision == Decision.REVISAR and "reinspeccion" in s.motivo_revision:
            reins_no += 1

    por_tipo: Counter = Counter()
    por_decision: Counter = Counter()
    for s in snapshots:
        por_tipo[s.tipo_inspeccion or "(vacío)"] += 1
        por_decision[s.decision.value] += 1

    conteos_actas = {
        "notificaciones": sum(1 for s in snapshots if s.acta_notificacion_num),
        "comprobaciones": sum(1 for s in snapshots if s.acta_comprobacion_num),
        "clausuras": sum(1 for s in snapshots if s.acta_clausura_num),
        "decomisos": sum(1 for s in snapshots if s.acta_decomiso_num),
    }

    duplicados: Dict[str, List[str]] = {}
    for label, idx in (("notificacion", notif_index), ("comprobacion", comp_index)):
        for num, uuids in idx.items():
            if len(uuids) > 1:
                duplicados[f"{label}:{num}"] = list(dict.fromkeys(uuids))

    return InventarioResult(
        source_sha256=source_sha,
        cutoff=cutoff,
        total_filas_leidas=len(snapshots),
        total_anterior_corte=len(historic),
        por_tipo_epi=dict(por_tipo),
        por_decision=dict(por_decision),
        conteos_actas=conteos_actas,
        reinspeccion_vinculables=reins_vinc,
        reinspeccion_no_vinculables=reins_no,
        duplicados_acta=duplicados,
        filas=snapshots,
        date_format_samples=date_formats,
    )


def snapshot_to_output_row(snap: RowSnapshot) -> Dict[str, str]:
    """Fila de salida CSV sin PII ni URLs."""
    return {
        "ec5_uuid": snap.ec5_uuid,
        "fecha_inspec_iso": snap.fecha_inspec.isoformat() if snap.fecha_inspec else "",
        "decision": snap.decision.value,
        "tipo_inspeccion_epi": snap.tipo_inspeccion,
        "odt_historica_ref": snap.odt_ref,
        "pudo_realizar": snap.pudo_realizar,
        "acta_inspeccion_num": snap.acta_inspeccion_num,
        "acta_notificacion_num": snap.acta_notificacion_num,
        "acta_comprobacion_num": snap.acta_comprobacion_num,
        "acta_clausura_num": snap.acta_clausura_num,
        "acta_decomiso_num": snap.acta_decomiso_num,
        "ref_notificacion_previa": snap.ref_notificacion_previa,
        "ref_comprobacion_previa": snap.ref_comprobacion_previa,
        "previa_ec5_uuid": snap.previa_ec5_uuid,
        "motivo_revision": snap.motivo_revision,
        "tiene_kilos_decomiso": "1" if snap.kilos_decomiso else "0",
        "tiene_faja_clausura": "1" if _is_si(snap.faja_clausura) else "0",
        "tiene_desnaturalizacion": "1" if _is_si(snap.desnaturalizacion) else "0",
    }


def _assert_no_pii_in_row(row: Mapping[str, str]) -> None:
    joined = " ".join(row.values()).lower()
    if "http://" in joined or "https://" in joined:
        raise ValueError("salida contiene URL")
    for forbidden in ("@", "dni", "cuit", "domicilio"):
        if forbidden in joined:
            raise ValueError("salida contiene patrón prohibido")


def write_inventario_outputs(result: InventarioResult, output_dir: Path) -> None:
    """Escribe JSON de resumen y CSVs de conciliación en output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    candidata_decisions = {
        Decision.CANDIDATA_ACTUACION_INICIAL,
        Decision.CANDIDATA_CON_NOTIFICACION,
        Decision.CANDIDATA_CON_COMPROBACION,
        Decision.CANDIDATA_CON_AMBAS_ACTAS,
        Decision.CANDIDATA_REINSPECCION_NOTIFICACION,
        Decision.CANDIDATA_REINSPECCION_OFICIO,
    }

    def write_csv(name: str, rows: Iterable[RowSnapshot]) -> None:
        path = output_dir / name
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(OUTPUT_CSV_FIELDS))
            w.writeheader()
            for snap in rows:
                out = snapshot_to_output_row(snap)
                _assert_no_pii_in_row(out)
                w.writerow(out)

    write_csv(
        "candidatas_actuaciones_historicas.csv",
        [s for s in result.filas if s.decision in candidata_decisions],
    )
    write_csv(
        "revisar_actas_historicas.csv",
        [s for s in result.filas if s.decision == Decision.REVISAR],
    )
    write_csv(
        "excluidas_post_corte.csv",
        [s for s in result.filas if s.decision == Decision.EXCLUIR_POST_CORTE],
    )

    resumen = {
        "source_sha256": result.source_sha256,
        "cutoff_date": result.cutoff.isoformat(),
        "total_filas_leidas": result.total_filas_leidas,
        "total_anterior_corte": result.total_anterior_corte,
        "conteo_por_tipo_epicollect": result.por_tipo_epi,
        "conteo_por_decision": result.por_decision,
        "conteos_actas_detectadas": result.conteos_actas,
        "reinspeccion_vinculables": result.reinspeccion_vinculables,
        "reinspeccion_no_vinculables": result.reinspeccion_no_vinculables,
        "numeros_acta_duplicados": {
            k: {"cantidad": len(v), "ec5_uuids": v} for k, v in result.duplicados_acta.items()
        },
        "formatos_fecha_detectados": dict(result.date_format_samples),
        "columnas_logicas_permitidas": list(ALLOWED_LOGICAL_COLUMNS),
    }
    with (output_dir / "resumen_actas_historicas.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)


def resolve_repo_root(start: Optional[Path] = None) -> Path:
    """Sube desde `start` hasta encontrar `.git` o `Backend/pyproject` markers."""
    cur = (start or Path.cwd()).resolve()
    for _ in range(12):
        if (cur / ".git").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return (start or Path.cwd()).resolve()


def assert_output_outside_repo(output_dir: Path, repo_root: Path) -> None:
    """Rechaza salidas dentro del árbol del repositorio."""
    out = output_dir.resolve()
    root = repo_root.resolve()
    try:
        out.relative_to(root)
        raise ValueError("La ruta --output no puede estar dentro del repositorio.")
    except ValueError as exc:
        if "no puede" in str(exc):
            raise
        return
