"""
Evidencia sandbox filtrada por ODT + año presentes en EpiCollect histórico.

V1.1-MIG-ACTAS.0C.1 — read-only, sin importar ni modificar sandbox.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.domains.migracion_historica.epicollect_actas_inventario import (
    _header_indices,
    assert_output_outside_repo,
    extract_row_snapshot,
    resolve_repo_root,
    sha256_file,
)
from app.domains.migracion_historica.epicollect_cadenas_historicas import (
    normalize_documento,
    normalize_domicilio,
    normalize_persona_razon,
    resolve_titular_norm,
)
from app.domains.migracion_historica.historico_actas_enriquecido_export import (
    _enum_value,
    _install_readonly_guard,
    _pick_expediente_oficio,
    fetch_actuaciones_readonly,
    legacy_ref_hash_for_actuacion,
)
from app.domains.migracion_historica.historico_sandbox_export_security import (
    SanitizedDatabaseTarget,
    resolve_export_database_uri,
    validate_sandbox_export_database_uri,
)
from app.models.actuaciones import Actuaciones
from app.models.ruta_item import RutaItem

ESTADO_COINCIDENCIA_OT_UNICA = "COINCIDENCIA_OT_UNICA"
ESTADO_COINCIDENCIA_OT_AMBIGUA = "COINCIDENCIA_OT_AMBIGUA"
ESTADO_SIN_COINCIDENCIA_SANDBOX = "SIN_COINCIDENCIA_SANDBOX"
ESTADO_EPI_SIN_OT = "EPI_SIN_OT"
ESTADO_CONFLICTO_IDENTIDAD = "CONFLICTO_IDENTIDAD"
ESTADO_EVIDENCIA_FINALIZADA = "EVIDENCIA_SANDBOX_FINALIZADA"
ESTADO_EVIDENCIA_NO_FINALIZADA = "EVIDENCIA_SANDBOX_NO_FINALIZADA"

EVIDENCIA_CSV_COLUMNS: Tuple[str, ...] = (
    "estado_coincidencia",
    "odt_normalizada",
    "odt_anio",
    "ec5_uuid",
    "fecha_epicollect",
    "tipo_inspeccion_epicollect",
    "legacy_ref_hash",
    "legacy_actuacion_id",
    "fecha_sandbox",
    "tipo_actuacion_sandbox",
    "estado_ruta_item",
    "estado_ejecucion",
    "tiene_notificacion",
    "tiene_comprobacion",
    "tiene_clausura",
    "tiene_decomiso",
    "tiene_expediente",
    "tiene_oficio",
    "identidad_documento_coincide",
    "identidad_domicilio_coincide",
    "identidad_titular_coincide",
    "identidad_motivo",
    "sandbox_finalizada",
)

REVISAR_CSV_COLUMNS: Tuple[str, ...] = (
    "estado_coincidencia",
    "odt_normalizada",
    "odt_anio",
    "ec5_uuid",
    "fecha_epicollect",
    "motivo_revision",
    "cantidad_filas_epicollect",
    "cantidad_actuaciones_sandbox",
    "legacy_ref_hash",
)


def normalize_odt(value: str) -> str:
    """
    Normaliza ODT para conciliación: trim, mayúsculas, sin separadores decorativos.

    Conserva ceros a la izquierda (no usa la regla de actas que los elimina).
    """
    s = (value or "").strip().upper()
    if not s:
        return ""
    s = re.sub(r"[\s.\-/\\_|]+", "", s)
    if not s or not re.search(r"\d", s):
        return ""
    return s


def odt_year_key(odt_norm: str, anio: int) -> Tuple[str, int]:
    """Par canónico ODT + año (nunca usar ODT sin año)."""
    return (odt_norm, int(anio))


@dataclass
class EpiOdtRow:
    """Fila histórica EpiCollect indexada por ODT."""

    snap: Any
    odt_norm: str
    odt_anio: int


@dataclass
class SandboxOdtCandidate:
    """Actuación sandbox candidata a evidencia."""

    act: Actuaciones
    odt_norm: str
    odt_anio: int
    doc_norm: str
    dom_norm: str
    titular_norm: str
    ruta_items: List[RutaItem] = field(default_factory=list)


@dataclass
class ClasificacionOdt:
    estado: str
    epi: Optional[EpiOdtRow] = None
    sandbox: Optional[SandboxOdtCandidate] = None
    motivo_revision: str = ""
    identidad_motivo: str = ""
    identidad_documento_coincide: str = ""
    identidad_domicilio_coincide: str = ""
    identidad_titular_coincide: str = ""
    cantidad_filas_epicollect: int = 0
    cantidad_actuaciones_sandbox: int = 0


@dataclass
class SandboxOdtExportResult:
    evidencia_csv_path: Path
    revisar_csv_path: Path
    resumen_path: Path
    resumen: Dict[str, Any]
    target: SanitizedDatabaseTarget


def _identity_flags(
    epi_doc: str,
    epi_dom: str,
    epi_tit: str,
    sb_doc: str,
    sb_dom: str,
    sb_tit: str,
) -> Tuple[str, str, str, str, bool]:
    """
    Evalúa identidad entre EpiCollect y sandbox.

    Returns:
        (motivo_tecnico, doc_flag, dom_flag, tit_flag, compatible).
    """
    doc_flag = ""
    dom_flag = ""
    tit_flag = ""

    if epi_doc and sb_doc:
        doc_flag = "1" if epi_doc == sb_doc else "0"
        if epi_doc == sb_doc:
            return "", doc_flag, dom_flag, tit_flag, True
        return "conflicto_documento", doc_flag, dom_flag, tit_flag, False

    dom_ok = bool(epi_dom and sb_dom and epi_dom == sb_dom)
    tit_ok = bool(epi_tit and sb_tit and epi_tit == sb_tit)
    dom_flag = "1" if dom_ok else ("0" if epi_dom and sb_dom else "")
    tit_flag = "1" if tit_ok else ("0" if epi_tit and sb_tit else "")

    if dom_ok and tit_ok:
        return "", doc_flag, dom_flag, tit_flag, True
    if dom_ok and not tit_ok:
        return "conflicto_titular", doc_flag, dom_flag, tit_flag, False
    if tit_ok and not dom_ok:
        return "conflicto_domicilio", doc_flag, dom_flag, tit_flag, False
    return "identidad_insuficiente", doc_flag, dom_flag, tit_flag, False


def sandbox_actuacion_finalizada(candidate: SandboxOdtCandidate) -> bool:
    """True si la actuación tiene ruta_item finalizada o ejecución realizada."""
    for ri in candidate.ruta_items:
        estado_item = _enum_value(getattr(ri, "estado_ruta_item", None))
        estado_ej = _enum_value(getattr(ri, "estado_ejecucion", None))
        if estado_item == "FINALIZADO":
            return True
        if estado_ej == "REALIZADO":
            return True
    return False


def _sandbox_identity_from_act(act: Actuaciones) -> Tuple[str, str, str]:
    doc = ""
    dom = ""
    tit = ""
    domicilio = getattr(act, "domicilio", None)
    if domicilio:
        contrib = getattr(domicilio, "contribuyente", None)
        if contrib:
            doc = normalize_documento(str(getattr(contrib, "documento", "") or ""))
        calle = getattr(domicilio, "calle", "") or ""
        numero = getattr(domicilio, "numero", "") or ""
        ciudad = getattr(domicilio, "ciudad", "") or ""
        dom = normalize_domicilio(f"{calle} {numero} {ciudad}".strip())
        if contrib:
            rs = str(getattr(contrib, "razon_social", "") or "")
            nom = str(getattr(contrib, "nombre", "") or "")
            ape = str(getattr(contrib, "apellido", "") or "")
            tit = resolve_titular_norm("", rs) or normalize_persona_razon(f"{ape} {nom}".strip())
    hist_rs = str(getattr(act, "titular_razon_social_historica", "") or "")
    if hist_rs:
        tit = resolve_titular_norm("", hist_rs) or tit
    if not tit:
        hn = str(getattr(act, "titular_nombre_historico", "") or "")
        ha = str(getattr(act, "titular_apellido_historico", "") or "")
        tit = normalize_persona_razon(f"{ha} {hn}".strip())
    return doc, dom, tit


def _sandbox_candidate_from_act(act: Actuaciones, ruta_items: Sequence[RutaItem]) -> Optional[SandboxOdtCandidate]:
    ot = getattr(act, "orden_trabajo", None)
    if not ot:
        return None
    odt_norm = normalize_odt(str(getattr(ot, "numero_acta", "") or ""))
    anio = getattr(ot, "anio", None)
    if not odt_norm or anio is None:
        return None
    doc, dom, tit = _sandbox_identity_from_act(act)
    return SandboxOdtCandidate(
        act=act,
        odt_norm=odt_norm,
        odt_anio=int(anio),
        doc_norm=doc,
        dom_norm=dom,
        titular_norm=tit,
        ruta_items=list(ruta_items),
    )


def load_epicollect_historic_rows(
    epicollect_csv: Path,
    cutoff: date,
) -> Tuple[str, List[EpiOdtRow], int]:
    """
    Lee EpiCollect y devuelve filas históricas con ODT normalizada.

    Returns:
        (sha256, filas con fecha < cutoff, total filas leídas).
    """
    source_sha = sha256_file(epicollect_csv)
    epi_rows: List[EpiOdtRow] = []
    total_leidas = 0
    with epicollect_csv.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        hdr = next(reader)
        by_name = _header_indices(hdr)
        odt_idx_list = by_name.get("2_Orden_de_Trabajo_N")
        odt_idx = odt_idx_list[0] if odt_idx_list else None
        for row in reader:
            total_leidas += 1
            snap = extract_row_snapshot(row, hdr, by_name)
            if not snap.fecha_inspec or snap.fecha_inspec >= cutoff:
                continue
            raw_odt = (row[odt_idx] if odt_idx is not None and odt_idx < len(row) else "") or ""
            odt_norm = normalize_odt(raw_odt)
            if not odt_norm:
                epi_rows.append(EpiOdtRow(snap=snap, odt_norm="", odt_anio=snap.fecha_inspec.year))
                continue
            epi_rows.append(
                EpiOdtRow(snap=snap, odt_norm=odt_norm, odt_anio=snap.fecha_inspec.year)
            )
    return source_sha, epi_rows, total_leidas


def fetch_ruta_items_by_actuacion(session: Session, actuacion_ids: Sequence[int]) -> Dict[int, List[RutaItem]]:
    """Carga ruta_item vinculados a actuaciones (solo SELECT)."""
    if not actuacion_ids:
        return {}
    rows = (
        session.query(RutaItem)
        .filter(RutaItem.actuacion_id.in_(list(actuacion_ids)))
        .all()
    )
    out: Dict[int, List[RutaItem]] = {}
    for ri in rows:
        aid = int(ri.actuacion_id)
        out.setdefault(aid, []).append(ri)
    return out


def clasificar_por_odt(
    epi_rows: Sequence[EpiOdtRow],
    sandbox_candidates: Sequence[SandboxOdtCandidate],
) -> Tuple[List[ClasificacionOdt], int]:
    """
    Clasifica cada fila EpiCollect histórica y cuenta sandbox descartadas.

    Returns:
        (clasificaciones por fila epi, sandbox descartadas por no estar en EpiCollect).
    """
    epi_by_key: Dict[Tuple[str, int], List[EpiOdtRow]] = {}
    for er in epi_rows:
        if not er.odt_norm:
            continue
        epi_by_key.setdefault(odt_year_key(er.odt_norm, er.odt_anio), []).append(er)

    sb_by_key: Dict[Tuple[str, int], List[SandboxOdtCandidate]] = {}
    for sb in sandbox_candidates:
        sb_by_key.setdefault(odt_year_key(sb.odt_norm, sb.odt_anio), []).append(sb)

    eligible_keys = set(epi_by_key.keys())
    sandbox_descartadas = sum(
        1 for sb in sandbox_candidates if odt_year_key(sb.odt_norm, sb.odt_anio) not in eligible_keys
    )

    resultados: List[ClasificacionOdt] = []
    for er in epi_rows:
        if not er.odt_norm:
            resultados.append(
                ClasificacionOdt(estado=ESTADO_EPI_SIN_OT, epi=er, motivo_revision="odt_invalida_o_vacia")
            )
            continue

        key = odt_year_key(er.odt_norm, er.odt_anio)
        epi_list = epi_by_key.get(key, [])
        sb_list = sb_by_key.get(key, [])

        if len(epi_list) > 1 or len(sb_list) > 1:
            resultados.append(
                ClasificacionOdt(
                    estado=ESTADO_COINCIDENCIA_OT_AMBIGUA,
                    epi=er,
                    motivo_revision="multiples_filas_epicollect_o_sandbox",
                    cantidad_filas_epicollect=len(epi_list),
                    cantidad_actuaciones_sandbox=len(sb_list),
                )
            )
            continue

        if len(sb_list) == 0:
            resultados.append(
                ClasificacionOdt(
                    estado=ESTADO_SIN_COINCIDENCIA_SANDBOX,
                    epi=er,
                    cantidad_filas_epicollect=1,
                    cantidad_actuaciones_sandbox=0,
                )
            )
            continue

        sb = sb_list[0]
        snap = er.snap
        motivo_id, doc_f, dom_f, tit_f, compatible = _identity_flags(
            snap.doc_norm,
            snap.dom_norm,
            snap.titular_norm,
            sb.doc_norm,
            sb.dom_norm,
            sb.titular_norm,
        )

        base_kw = dict(
            epi=er,
            sandbox=sb,
            identidad_motivo=motivo_id,
            identidad_documento_coincide=doc_f,
            identidad_domicilio_coincide=dom_f,
            identidad_titular_coincide=tit_f,
            cantidad_filas_epicollect=1,
            cantidad_actuaciones_sandbox=1,
        )

        if motivo_id in ("conflicto_documento", "conflicto_domicilio", "conflicto_titular"):
            resultados.append(
                ClasificacionOdt(
                    estado=ESTADO_CONFLICTO_IDENTIDAD,
                    motivo_revision=motivo_id,
                    **base_kw,
                )
            )
            continue

        if motivo_id == "identidad_insuficiente":
            resultados.append(
                ClasificacionOdt(
                    estado=ESTADO_COINCIDENCIA_OT_UNICA,
                    motivo_revision="identidad_insuficiente",
                    **base_kw,
                )
            )
            continue

        finalizada = sandbox_actuacion_finalizada(sb)
        resultados.append(
            ClasificacionOdt(
                estado=ESTADO_EVIDENCIA_FINALIZADA if finalizada else ESTADO_EVIDENCIA_NO_FINALIZADA,
                **base_kw,
            )
        )

    return resultados, sandbox_descartadas


def _bool_presence(val: Any) -> str:
    return "1" if val else "0"


def clasificacion_to_evidencia_row(cl: ClasificacionOdt) -> Optional[Dict[str, str]]:
    """Fila de evidencia solo para coincidencias con actuación sandbox vinculada."""
    if cl.sandbox is None or cl.estado in (
        ESTADO_SIN_COINCIDENCIA_SANDBOX,
        ESTADO_EPI_SIN_OT,
        ESTADO_COINCIDENCIA_OT_AMBIGUA,
    ):
        return None

    act = cl.sandbox.act
    snap = cl.epi.snap if cl.epi else None
    ri = cl.sandbox.ruta_items[0] if cl.sandbox.ruta_items else None
    exp_ofi = _pick_expediente_oficio(act)

    return {
        "estado_coincidencia": cl.estado,
        "odt_normalizada": cl.sandbox.odt_norm,
        "odt_anio": str(cl.sandbox.odt_anio),
        "ec5_uuid": snap.ec5_uuid if snap else "",
        "fecha_epicollect": snap.fecha_inspec.isoformat() if snap and snap.fecha_inspec else "",
        "tipo_inspeccion_epicollect": snap.tipo_inspeccion if snap else "",
        "legacy_ref_hash": legacy_ref_hash_for_actuacion(int(act.id)),
        "legacy_actuacion_id": str(act.id),
        "fecha_sandbox": act.fecha.isoformat() if act.fecha else "",
        "tipo_actuacion_sandbox": _enum_value(act.tipo),
        "estado_ruta_item": _enum_value(getattr(ri, "estado_ruta_item", None)) if ri else "",
        "estado_ejecucion": _enum_value(getattr(ri, "estado_ejecucion", None)) if ri else "",
        "tiene_notificacion": _bool_presence(getattr(act, "notificacion", None)),
        "tiene_comprobacion": _bool_presence(getattr(act, "comprobacion", None)),
        "tiene_clausura": _bool_presence(getattr(act, "clausura", None)),
        "tiene_decomiso": _bool_presence(getattr(act, "decomiso", None)),
        "tiene_expediente": _bool_presence((exp_ofi.get("expediente_numero") or "").strip()),
        "tiene_oficio": _bool_presence((exp_ofi.get("oficio_numero") or "").strip()),
        "identidad_documento_coincide": cl.identidad_documento_coincide,
        "identidad_domicilio_coincide": cl.identidad_domicilio_coincide,
        "identidad_titular_coincide": cl.identidad_titular_coincide,
        "identidad_motivo": cl.identidad_motivo,
        "sandbox_finalizada": "1" if sandbox_actuacion_finalizada(cl.sandbox) else "0",
    }


def clasificacion_to_revisar_row(cl: ClasificacionOdt) -> Optional[Dict[str, str]]:
    """Filas que requieren revisión manual."""
    revisar_estados = {
        ESTADO_COINCIDENCIA_OT_AMBIGUA,
        ESTADO_CONFLICTO_IDENTIDAD,
        ESTADO_COINCIDENCIA_OT_UNICA,
        ESTADO_SIN_COINCIDENCIA_SANDBOX,
        ESTADO_EPI_SIN_OT,
    }
    if cl.estado not in revisar_estados:
        return None
    snap = cl.epi.snap if cl.epi else None
    sb = cl.sandbox
    return {
        "estado_coincidencia": cl.estado,
        "odt_normalizada": cl.epi.odt_norm if cl.epi else "",
        "odt_anio": str(cl.epi.odt_anio) if cl.epi else "",
        "ec5_uuid": snap.ec5_uuid if snap else "",
        "fecha_epicollect": snap.fecha_inspec.isoformat() if snap and snap.fecha_inspec else "",
        "motivo_revision": cl.motivo_revision or cl.identidad_motivo,
        "cantidad_filas_epicollect": str(cl.cantidad_filas_epicollect or (1 if cl.epi and cl.epi.odt_norm else 0)),
        "cantidad_actuaciones_sandbox": str(cl.cantidad_actuaciones_sandbox),
        "legacy_ref_hash": legacy_ref_hash_for_actuacion(int(sb.act.id)) if sb else "",
    }


def build_resumen_odt(
    epicollect_sha256: str,
    cutoff: date,
    total_filas_leidas: int,
    epi_rows: Sequence[EpiOdtRow],
    clasificaciones: Sequence[ClasificacionOdt],
    sandbox_descartadas: int,
    target: SanitizedDatabaseTarget,
) -> Dict[str, Any]:
    """Resumen JSON sin PII."""
    historic_count = len(epi_rows)
    odt_validas = sum(1 for e in epi_rows if e.odt_norm)
    odt_unicas = len({odt_year_key(e.odt_norm, e.odt_anio) for e in epi_rows if e.odt_norm})

    def _count(estado: str) -> int:
        return sum(1 for c in clasificaciones if c.estado == estado)

    return {
        "modo": "EVIDENCIA_SANDBOX_FILTRADA_ODT",
        "database": target.database,
        "host": target.host,
        "port": target.port,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "cutoff_date": cutoff.isoformat(),
        "epicollect_sha256": epicollect_sha256,
        "filas_epicollect_leidas": total_filas_leidas,
        "filas_epicollect_anterior_corte": historic_count,
        "filas_con_odt_valida": odt_validas,
        "odt_anio_unicos": odt_unicas,
        "coincidencias_sandbox_unicas": _count(ESTADO_COINCIDENCIA_OT_UNICA)
        + _count(ESTADO_EVIDENCIA_FINALIZADA)
        + _count(ESTADO_EVIDENCIA_NO_FINALIZADA)
        + _count(ESTADO_CONFLICTO_IDENTIDAD),
        "coincidencias_ambiguas": _count(ESTADO_COINCIDENCIA_OT_AMBIGUA),
        "conflictos_identidad": _count(ESTADO_CONFLICTO_IDENTIDAD),
        "evidencias_finalizadas": _count(ESTADO_EVIDENCIA_FINALIZADA),
        "evidencias_no_finalizadas": _count(ESTADO_EVIDENCIA_NO_FINALIZADA),
        "sin_coincidencia_sandbox": _count(ESTADO_SIN_COINCIDENCIA_SANDBOX),
        "epi_sin_ot_valida": _count(ESTADO_EPI_SIN_OT),
        "sandbox_descartadas_no_en_epicollect": sandbox_descartadas,
        "media_urls_exportadas": False,
    }


def write_odt_evidencia_outputs(
    clasificaciones: Sequence[ClasificacionOdt],
    resumen: Mapping[str, Any],
    output_dir: Path,
    target: SanitizedDatabaseTarget,
) -> SandboxOdtExportResult:
    """Escribe CSV de evidencia, revisar y resumen JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    evidencia_path = output_dir / "evidencia_sandbox_por_odt.csv"
    revisar_path = output_dir / "revisar_coincidencias_ot.csv"
    resumen_path = output_dir / "resumen_evidencia_sandbox_odt.json"

    with evidencia_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(EVIDENCIA_CSV_COLUMNS))
        writer.writeheader()
        for cl in clasificaciones:
            row = clasificacion_to_evidencia_row(cl)
            if row:
                writer.writerow(row)

    with revisar_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(REVISAR_CSV_COLUMNS))
        writer.writeheader()
        for cl in clasificaciones:
            row = clasificacion_to_revisar_row(cl)
            if row:
                writer.writerow(row)

    with resumen_path.open("w", encoding="utf-8") as f:
        json.dump(dict(resumen), f, ensure_ascii=False, indent=2)

    return SandboxOdtExportResult(
        evidencia_csv_path=evidencia_path,
        revisar_csv_path=revisar_path,
        resumen_path=resumen_path,
        resumen=dict(resumen),
        target=target,
    )


def export_evidencia_sandbox_por_odt(
    output_dir: Path,
    epicollect_csv: Path,
    cutoff: date,
    database_uri: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> SandboxOdtExportResult:
    """
    Exporta evidencia sandbox filtrada por ODT presente en EpiCollect histórico.

    Args:
        output_dir: directorio fuera del repositorio.
        epicollect_csv: CSV congelado EpiCollect.
        cutoff: filas con fecha de inspección >= cutoff se excluyen del universo.
        database_uri: URI sandbox local opcional.
        repo_root: raíz git para validar salida.

    Returns:
        SandboxOdtExportResult con rutas y resumen sin PII.

    Raises:
        HistoricoExportSecurityError: URI no permitida.
        ValueError: salida dentro del repo.
        RuntimeError: escritura en DB bloqueada.
    """
    root = repo_root or resolve_repo_root()
    assert_output_outside_repo(output_dir, root)

    epicollect_sha, epi_rows, total_leidas = load_epicollect_historic_rows(epicollect_csv, cutoff)

    uri = resolve_export_database_uri(database_uri)
    target = validate_sandbox_export_database_uri(uri)
    engine = create_engine(uri, pool_pre_ping=True)
    _install_readonly_guard(engine)

    sandbox_candidates: List[SandboxOdtCandidate] = []
    with Session(engine) as session:
        actuaciones = fetch_actuaciones_readonly(session)
        act_ids = [int(a.id) for a in actuaciones]
        ruta_map = fetch_ruta_items_by_actuacion(session, act_ids)
        for act in actuaciones:
            cand = _sandbox_candidate_from_act(act, ruta_map.get(int(act.id), []))
            if cand:
                sandbox_candidates.append(cand)

    clasificaciones, descartadas = clasificar_por_odt(epi_rows, sandbox_candidates)
    resumen = build_resumen_odt(
        epicollect_sha,
        cutoff,
        total_leidas,
        epi_rows,
        clasificaciones,
        descartadas,
        target,
    )
    return write_odt_evidencia_outputs(clasificaciones, resumen, output_dir, target)
