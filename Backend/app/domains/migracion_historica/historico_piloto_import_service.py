"""
Piloto local de importación histórica (EpiCollect + evidencia sandbox finalizada).

V1.1-MIG-ACTAS.1A — transaccional, idempotente, sin rutas ni iniciadores.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy import func, text

from app.database import db
from app.domains.actuaciones.attach.clausura import attach_clausura
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.attach.domicilio import get_or_create_domicilio
from app.domains.actuaciones.attach.inspeccion import attach_inspeccion
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.actuaciones.attach.orden_trabajo import get_or_create_orden_trabajo
from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.catalogs.motivo import get_motivo_o_falla
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.catalogos.canonical.motivos import (
    MOTIVOS_COMPROBACION_CANONICOS,
    MOTIVOS_NOTIFICACION_CANONICOS,
)
from app.domains.catalogos.canonical.tipos_actuacion import TIPOS_ACTUACION_CANONICOS
from app.domains.migracion_historica.epicollect_actas_inventario import (
    RowSnapshot,
    _cell,
    _first_index,
    _header_indices,
    assert_output_outside_repo,
    extract_row_snapshot,
    resolve_repo_root,
    sha256_file,
)
from app.domains.migracion_historica.historico_migracion_import_security import (
    MigracionImportTarget,
)
from app.domains.migracion_historica.migracion_target_connection import (
    connection_summary_fields,
    verify_pilot_target_connection,
)
from app.domains.migracion_historica.historico_sandbox_odt_evidencia import (
    ESTADO_EVIDENCIA_FINALIZADA,
    normalize_odt,
)
from app.models import (
    Actuaciones,
    Clausura,
    Comprobacion,
    Decomiso,
    IniciadorRuta,
    Inspeccion,
    MigracionHistoricaRegistro,
    Notificacion,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
)
from app.utils.actas import acta_6

SOURCE_NAME = "epicollect_odt_pilot_v1"
DECISION_APPLICABLE = "APPLICABLE"
DECISION_REVISAR = "REVISAR"
DECISION_INSERTED = "INSERTED"
DECISION_SKIPPED_IDEMPOTENT = "SKIPPED_IDEMPOTENT"
DECISION_ERROR = "ERROR"

MAPEO_APPLICABLE_COLUMNS: Tuple[str, ...] = (
    "ec5_uuid",
    "decision",
    "legacy_ref_hash",
    "odt_normalizada",
    "odt_anio",
    "fecha_inspec_iso",
    "motivo_revision",
)

MAPEO_REVISAR_COLUMNS: Tuple[str, ...] = (
    "ec5_uuid",
    "decision",
    "motivo_revision",
    "legacy_ref_hash",
)

ZERO_COUNT_TABLES: Tuple[str, ...] = (
    "actuaciones",
    "orden_trabajo",
    "notificacion",
    "comprobacion",
    "inspeccion",
    "clausura",
    "decomiso",
    "ruta_trabajo",
    "ruta_item",
    "iniciador_ruta",
)


@dataclass
class PilotChainPlan:
    """Plan de importación para una cadena histórica."""

    ec5_uuid: str
    legacy_ref_hash: str
    decision: str
    motivo_revision: str = ""
    snap: Optional[RowSnapshot] = None
    odt_numero: str = ""
    odt_anio: int = 0
    inspectores: List[str] = field(default_factory=list)
    rubro_nombre: str = ""
    domicilio: Dict[str, str] = field(default_factory=dict)
    contribuyente: Dict[str, str] = field(default_factory=dict)
    tipo_actuacion: Optional[str] = None
    acta_inspeccion: str = ""
    notificacion: Dict[str, Any] = field(default_factory=dict)
    comprobacion: Dict[str, Any] = field(default_factory=dict)
    clausura: Dict[str, Any] = field(default_factory=dict)
    decomiso: Dict[str, Any] = field(default_factory=dict)
    nombre_local: str = ""


@dataclass
class PilotImportResult:
    resumen_path: Path
    resumen: Dict[str, Any]
    plans: List[PilotChainPlan]


def combined_source_sha256(epicollect_sha: str, evidence_sha: str) -> str:
    """Hash estable de las dos fuentes del piloto."""
    payload = f"{epicollect_sha.strip()}|{evidence_sha.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_evidence_finalizadas(path: Path) -> Tuple[str, List[Dict[str, str]]]:
    """Carga filas de evidencia con estado finalizado."""
    sha = sha256_file(path)
    rows: List[Dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            estado = (row.get("estado_coincidencia") or "").strip()
            if estado == ESTADO_EVIDENCIA_FINALIZADA:
                rows.append(dict(row))
    return sha, rows


def load_epicollect_by_uuid(path: Path) -> Tuple[str, Dict[str, RowSnapshot], Dict[str, Sequence[str]]]:
    """
    Indexa snapshots EpiCollect por ec5_uuid.

    Returns:
        (sha256, map uuid→snap, map uuid→fila cruda para columnas extra).
    """
    sha = sha256_file(path)
    by_uuid: Dict[str, RowSnapshot] = {}
    raw_rows: Dict[str, List[str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        hdr = next(reader)
        by_name = _header_indices(hdr)
        for row in reader:
            snap = extract_row_snapshot(row, hdr, by_name)
            if not snap.ec5_uuid:
                continue
            by_uuid[snap.ec5_uuid] = snap
            raw_rows[snap.ec5_uuid] = row
    return sha, by_uuid, raw_rows


def _parse_domicilio_epi(raw: str) -> Optional[Dict[str, str]]:
    s = (raw or "").strip()
    if not s:
        return None
    m = re.search(r"(\d+)\s*$", s)
    if not m:
        return None
    numero = m.group(1)
    calle = s[: m.start()].strip().rstrip(",-")
    if not calle:
        return None
    return {"calle": calle, "numero": numero}


def _split_inspectores(raw: str) -> List[str]:
    if not (raw or "").strip():
        return []
    parts = re.split(r"[|,;/]+", raw)
    return [p.strip() for p in parts if p.strip()]


def _match_catalog_motivo(text: str, catalog: Sequence[str]) -> Optional[str]:
    t = (text or "").strip().lower()
    if not t:
        return None
    for name in catalog:
        n = name.lower()
        if n in t or t in n:
            return name
    return None


def _resolve_motivos_notificacion(infracciones: str) -> List[str]:
    matched: List[str] = []
    for chunk in re.split(r"[|;]+", infracciones or ""):
        m = _match_catalog_motivo(chunk, MOTIVOS_NOTIFICACION_CANONICOS)
        if m and m not in matched:
            matched.append(m)
    return matched


def _resolve_tipo_actuacion(tipo_epi: str) -> Optional[str]:
    t = (tipo_epi or "").strip().upper()
    if not t:
        return "INSPECCION"
    for canon in TIPOS_ACTUACION_CANONICOS:
        if canon.upper() in t or t in canon.upper():
            return canon
    if "REINSPECC" in t:
        return "REINSPECCION"
    return "INSPECCION"


def _try_catalog_resolution(plan: PilotChainPlan) -> Optional[str]:
    """Devuelve motivo de revisión si catálogos no resuelven."""
    if not plan.inspectores:
        return "inspectores_ausentes"
    try:
        get_inspectores_o_falla(plan.inspectores)
    except ValueError:
        return "inspector_no_resoluble"
    if plan.rubro_nombre:
        try:
            get_rubro_o_falla(plan.rubro_nombre)
        except ValueError:
            return "rubro_no_resoluble"
    else:
        return "rubro_ausente"
    if plan.domicilio:
        if not plan.contribuyente.get("doc_nro"):
            return "documento_ausente_para_domicilio"
    if plan.notificacion:
        motivos = plan.notificacion.get("motivos") or []
        if not motivos:
            return "motivos_notificacion_no_resueltos"
        try:
            for m in motivos:
                get_motivo_o_falla(m)
        except ValueError:
            return "motivo_notificacion_no_catalogo"
    if plan.comprobacion:
        if not (plan.comprobacion.get("motivo") or "").strip():
            return "motivo_comprobacion_ausente"
    if plan.decomiso and not plan.decomiso.get("kilos_total"):
        return "decomiso_sin_kilos"
    if not (
        plan.acta_inspeccion
        or plan.notificacion
        or plan.comprobacion
        or plan.clausura
        or plan.decomiso
    ):
        return "sin_actas_minimas"
    return None


def build_plan_from_sources(
    evidence_rows: Sequence[Mapping[str, str]],
    epi_by_uuid: Mapping[str, RowSnapshot],
    raw_by_uuid: Mapping[str, Sequence[str]],
    hdr_by_uuid: Mapping[str, Sequence[str]],
    cutoff: date,
) -> List[PilotChainPlan]:
    """Construye planes por fila de evidencia finalizada."""
    plans: List[PilotChainPlan] = []
    for ev in evidence_rows:
        ec5 = (ev.get("ec5_uuid") or "").strip()
        legacy_hash = (ev.get("legacy_ref_hash") or "").strip()
        plan = PilotChainPlan(
            ec5_uuid=ec5,
            legacy_ref_hash=legacy_hash,
            decision=DECISION_REVISAR,
            motivo_revision="",
        )
        if not ec5:
            plan.motivo_revision = "ec5_uuid_ausente"
            plans.append(plan)
            continue

        snap = epi_by_uuid.get(ec5)
        if not snap:
            plan.motivo_revision = "fila_epicollect_inexistente"
            plans.append(plan)
            continue
        plan.snap = snap

        if not snap.fecha_inspec or snap.fecha_inspec >= cutoff:
            plan.motivo_revision = "fecha_fuera_de_corte"
            plans.append(plan)
            continue

        raw = raw_by_uuid.get(ec5)
        hdr = hdr_by_uuid.get(ec5)
        if raw is None or hdr is None:
            plan.motivo_revision = "fila_cruda_epicollect_perdida"
            plans.append(plan)
            continue

        by_name = _header_indices(hdr)
        odt_raw = _cell(raw, _first_index(by_name, "2_Orden_de_Trabajo_N"))
        odt_norm = normalize_odt(odt_raw)
        if odt_norm:
            plan.odt_numero = acta_6(odt_norm) or odt_norm
            plan.odt_anio = snap.fecha_inspec.year

        insp_raw = _cell(raw, _first_index(by_name, "3_Qu_inspectores_con"))
        plan.inspectores = _split_inspectores(insp_raw)
        plan.rubro_nombre = _cell(raw, _first_index(by_name, "17_Rubro"))
        dom = _parse_domicilio_epi(_cell(raw, _first_index(by_name, "4_Domicilio")))
        if dom:
            plan.domicilio = dom
        doc = re.sub(r"\D+", "", _cell(raw, _first_index(by_name, "16_DNI_del_Contribuy")))
        rs = _cell(raw, _first_index(by_name, "15_Razn_Socialnombre"))
        nf = _cell(raw, _first_index(by_name, "14_Nombre_de_Fantasa"))
        if doc:
            plan.contribuyente = {"doc_nro": doc}
            if rs:
                plan.contribuyente["razon_social"] = rs
            elif nf:
                plan.contribuyente["nombre"] = nf
        plan.nombre_local = nf or rs
        plan.tipo_actuacion = _resolve_tipo_actuacion(snap.tipo_inspeccion)

        if snap.acta_inspeccion_num:
            plan.acta_inspeccion = snap.acta_inspeccion_num
        if snap.acta_notificacion_num:
            motivos = _resolve_motivos_notificacion(
                _cell(raw, _first_index(by_name, "87_Infracciones"))
            )
            plan.notificacion = {
                "acta_num": snap.acta_notificacion_num,
                "motivos": motivos,
            }
        if snap.acta_comprobacion_num:
            motivo_comp = _match_catalog_motivo(
                _cell(raw, _first_index(by_name, "94_Infracciones")),
                MOTIVOS_COMPROBACION_CANONICOS,
            )
            plan.comprobacion = {
                "acta_num": snap.acta_comprobacion_num,
                "motivo": motivo_comp or "",
            }
        if snap.acta_clausura_num:
            plan.clausura = {"acta_num": snap.acta_clausura_num}
        if snap.acta_decomiso_num:
            kilos_raw = (snap.kilos_decomiso or "").strip().replace(",", ".")
            kilos: Optional[float] = None
            if kilos_raw:
                try:
                    kilos = float(kilos_raw)
                except ValueError:
                    kilos = None
            plan.decomiso = {
                "acta_num": snap.acta_decomiso_num,
                "kilos_total": kilos,
            }

        revision = _try_catalog_resolution(plan)
        if revision:
            plan.motivo_revision = revision
            plan.decision = DECISION_REVISAR
        else:
            plan.decision = DECISION_APPLICABLE
            plan.motivo_revision = ""
        plans.append(plan)
    return plans


def count_operational_tables() -> Dict[str, int]:
    """Conteos actuales en tablas operativas del piloto."""
    return {
        "actuaciones": db.session.query(func.count(Actuaciones.id)).scalar() or 0,
        "orden_trabajo": db.session.query(func.count(OrdenTrabajo.id)).scalar() or 0,
        "notificacion": db.session.query(func.count(Notificacion.id)).scalar() or 0,
        "comprobacion": db.session.query(func.count(Comprobacion.id)).scalar() or 0,
        "inspeccion": db.session.query(func.count(Inspeccion.id)).scalar() or 0,
        "clausura": db.session.query(func.count(Clausura.id)).scalar() or 0,
        "decomiso": db.session.query(func.count(Decomiso.id)).scalar() or 0,
        "ruta_trabajo": db.session.query(func.count(RutaTrabajo.id)).scalar() or 0,
        "ruta_item": db.session.query(func.count(RutaItem.id)).scalar() or 0,
        "iniciador_ruta": db.session.query(func.count(IniciadorRuta.id)).scalar() or 0,
    }


def read_alembic_revision() -> str:
    """Lee revisión Alembic actual."""
    row = db.session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
    return str(row[0]) if row else ""


def assert_pilot_destination_empty() -> None:
    """Falla si hay datos operativos previos al piloto."""
    counts = count_operational_tables()
    bad = {k: v for k, v in counts.items() if k in ZERO_COUNT_TABLES and v != 0}
    if bad:
        raise ValueError(
            "La base destino debe comenzar sin actuaciones ni rutas; conteos: "
            + ", ".join(f"{k}={v}" for k, v in bad.items())
        )


def _existing_registro(
    source_sha: str,
    ec5_uuid: str,
) -> Optional[MigracionHistoricaRegistro]:
    return (
        db.session.query(MigracionHistoricaRegistro)
        .filter_by(
            source_name=SOURCE_NAME,
            source_sha256=source_sha,
            source_record_uuid=ec5_uuid,
        )
        .first()
    )


def _import_single_chain(plan: PilotChainPlan) -> int:
    """
    Importa una cadena en la sesión actual (sin commit).

    Raises:
        ValueError: reglas de negocio o catálogos.
    """
    snap = plan.snap
    if not snap or not snap.fecha_inspec:
        raise ValueError("snapshot_invalido")

    fecha_str = snap.fecha_inspec.isoformat()
    orden_trabajo_id = None
    if plan.odt_numero and plan.odt_anio:
        ot = get_or_create_orden_trabajo(plan.odt_numero, fecha_str)
        existente = Actuaciones.query.filter_by(orden_trabajo_id=ot.id).first()
        if existente:
            raise ValueError("ot_ya_tiene_actuacion")
        orden_trabajo_id = ot.id

    existente_uuid = Actuaciones.query.filter_by(ec5_uuid=plan.ec5_uuid).first()
    if existente_uuid:
        raise ValueError("ec5_uuid_ya_importado")

    act = Actuaciones(
        fecha=snap.fecha_inspec,
        mes=snap.fecha_inspec.month,
        anio=snap.fecha_inspec.year,
        tipo=plan.tipo_actuacion,
        orden_trabajo_id=orden_trabajo_id,
        ec5_uuid=plan.ec5_uuid,
        nombre_local=plan.nombre_local or None,
    )
    db.session.add(act)
    db.session.flush()

    rubro = get_rubro_o_falla(plan.rubro_nombre) if plan.rubro_nombre else None
    contrib = resolve_contribuyente(plan.contribuyente or None)
    dom = get_or_create_domicilio(plan.domicilio or None, contrib, rubro)
    if dom:
        act.domicilio_id = dom.id

    act.inspector = get_inspectores_o_falla(plan.inspectores)

    if plan.acta_inspeccion:
        attach_inspeccion(act, plan.acta_inspeccion, crear=True)
    if plan.notificacion:
        attach_notificacion(act, plan.notificacion)
    if plan.comprobacion:
        attach_comprobacion(act, plan.comprobacion)
    if plan.clausura:
        attach_clausura(act, plan.clausura, crear=True)
    if plan.decomiso:
        attach_decomiso(act, plan.decomiso, crear=True)

    db.session.add(act)
    db.session.flush()
    return int(act.id)


def _sanitize_error(exc: BaseException) -> Tuple[str, str]:
    code = exc.__class__.__name__
    msg = str(exc).strip()
    msg = re.sub(r"\d{7,}", "[doc]", msg)
    if "http://" in msg.lower() or "https://" in msg.lower():
        msg = "error_con_url_rechazado"
    return code[:64], msg[:512]


def run_pilot_import(
    *,
    output_dir: Path,
    epicollect_csv: Path,
    sandbox_evidence_csv: Path,
    batch_id: str,
    cutoff: date,
    dry_run: bool,
    apply: bool,
    confirm_batch: Optional[str],
    target: MigracionImportTarget,
    repo_root: Optional[Path] = None,
) -> PilotImportResult:
    """
    Ejecuta dry-run o apply del piloto histórico.

    Args:
        output_dir: carpeta local fuera del repo.
        epicollect_csv: CSV EpiCollect congelado.
        sandbox_evidence_csv: evidencia 0C.1.
        batch_id: identificador del lote.
        cutoff: fecha de corte EpiCollect.
        dry_run: si True, no persiste actuaciones ni registro.
        apply: si True, intenta insertar cadenas aplicables.
        confirm_batch: debe coincidir con batch_id para apply.
        repo_root: raíz git para validar salida.

    Returns:
        PilotImportResult con resumen y planes.

    Raises:
        ValueError: confirmación inválida o destino no vacío.
        MigracionTargetConnectionError: ``SELECT DATABASE()`` no coincide con el destino.
        HistoricoMigracionImportSecurityError: URI no permitida (validada antes en CLI).
    """
    if apply and dry_run:
        raise ValueError("No combine --apply con --dry-run")
    if apply:
        if not (confirm_batch or "").strip():
            raise ValueError("--apply requiere --confirm-batch igual a --batch-id.")
        if confirm_batch.strip() != batch_id.strip():
            raise ValueError("--apply requiere --confirm-batch igual a --batch-id.")

    verified = verify_pilot_target_connection(db.session, target)
    conn_meta = connection_summary_fields(verified)

    root = repo_root or resolve_repo_root()
    assert_output_outside_repo(output_dir, root)
    output_dir.mkdir(parents=True, exist_ok=True)

    ev_sha, evidence_rows = load_evidence_finalizadas(sandbox_evidence_csv)
    epi_sha, epi_by_uuid, raw_by_uuid = load_epicollect_by_uuid(epicollect_csv)
    hdr_by_uuid: Dict[str, Sequence[str]] = {}
    with epicollect_csv.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        hdr = next(reader)
        for row in reader:
            idx = _first_index(_header_indices(hdr), "ec5_uuid")
            if idx is None or idx >= len(row):
                continue
            u = (row[idx] or "").strip()
            if u:
                hdr_by_uuid[u] = hdr

    source_sha = combined_source_sha256(epi_sha, ev_sha)
    plans = build_plan_from_sources(
        evidence_rows,
        epi_by_uuid,
        raw_by_uuid,
        hdr_by_uuid,
        cutoff,
    )

    counts_before = count_operational_tables()
    alembic_rev = read_alembic_revision()

    inserted = 0
    skipped = 0
    errores = 0
    created = {
        "orden_trabajo": 0,
        "actuaciones": 0,
        "notificaciones": 0,
        "comprobaciones": 0,
        "clausuras": 0,
        "decomisos": 0,
    }

    if apply and not dry_run and counts_before["actuaciones"] == 0:
        assert_pilot_destination_empty()

    ot_before = counts_before["orden_trabajo"]
    act_before = counts_before["actuaciones"]

    for plan in plans:
        if plan.decision != DECISION_APPLICABLE:
            continue
        if apply and not dry_run:
            prev = _existing_registro(source_sha, plan.ec5_uuid)
            if prev and prev.decision == DECISION_INSERTED:
                plan.decision = DECISION_SKIPPED_IDEMPOTENT
                skipped += 1
                continue
        if dry_run or not apply:
            continue

        try:
            act_id = _import_single_chain(plan)
            reg = MigracionHistoricaRegistro(
                batch_id=batch_id,
                source_name=SOURCE_NAME,
                source_sha256=source_sha,
                source_record_uuid=plan.ec5_uuid,
                decision=DECISION_INSERTED,
                target_actuacion_id=act_id,
            )
            db.session.add(reg)
            db.session.commit()
            plan.decision = DECISION_INSERTED
            inserted += 1
        except Exception as exc:
            db.session.rollback()
            code, detail = _sanitize_error(exc)
            reg = MigracionHistoricaRegistro(
                batch_id=batch_id,
                source_name=SOURCE_NAME,
                source_sha256=source_sha,
                source_record_uuid=plan.ec5_uuid,
                decision=DECISION_ERROR,
                error_code=code,
                error_detail_sanitized=detail,
            )
            db.session.add(reg)
            db.session.commit()
            plan.decision = DECISION_ERROR
            plan.motivo_revision = detail
            errores += 1

    counts_after = count_operational_tables()
    if apply and not dry_run:
        created["orden_trabajo"] = counts_after["orden_trabajo"] - ot_before
        created["actuaciones"] = counts_after["actuaciones"] - act_before
        created["notificaciones"] = counts_after["notificacion"] - counts_before["notificacion"]
        created["comprobaciones"] = counts_after["comprobacion"] - counts_before["comprobacion"]
        created["clausuras"] = counts_after["clausura"] - counts_before["clausura"]
        created["decomisos"] = counts_after["decomiso"] - counts_before["decomiso"]

    candidatas = len(evidence_rows)
    aplicables = sum(
        1
        for p in plans
        if p.decision in (DECISION_APPLICABLE, DECISION_INSERTED, DECISION_SKIPPED_IDEMPOTENT)
    )
    revisadas = sum(1 for p in plans if p.decision in (DECISION_REVISAR, DECISION_ERROR))

    resumen: Dict[str, Any] = {
        "modo": "DRY_RUN" if dry_run else ("APPLY" if apply else "PLAN"),
        "batch_id": batch_id,
        "cutoff_date": cutoff.isoformat(),
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "database": target.database,
        "host": target.host,
        "port": target.port,
        **conn_meta,
        "alembic_revision": alembic_rev,
        "epicollect_sha256": epi_sha,
        "evidencia_sha256": ev_sha,
        "source_sha256": source_sha,
        "source_name": SOURCE_NAME,
        "candidatas_evidencia_finalizada": candidatas,
        "aplicables": aplicables,
        "revisar": revisadas,
        "insertadas": inserted,
        "omitidas_idempotencia": skipped,
        "errores": errores,
        "conteos_creados": created,
        "conteos_rutas_iniciadores": {
            "ruta_trabajo": counts_after["ruta_trabajo"],
            "ruta_item": counts_after["ruta_item"],
            "iniciador_ruta": counts_after["iniciador_ruta"],
        },
        "conteos_antes": counts_before,
        "conteos_despues": counts_after,
        "media_urls_exportadas": False,
    }

    _write_pilot_outputs(output_dir, plans, resumen)
    resumen_path = output_dir / "resumen_piloto_importacion.json"
    return PilotImportResult(resumen_path=resumen_path, resumen=resumen, plans=plans)


def _plan_to_applicable_row(plan: PilotChainPlan) -> Dict[str, str]:
    fecha = plan.snap.fecha_inspec.isoformat() if plan.snap and plan.snap.fecha_inspec else ""
    return {
        "ec5_uuid": plan.ec5_uuid,
        "decision": plan.decision,
        "legacy_ref_hash": plan.legacy_ref_hash,
        "odt_normalizada": plan.odt_numero,
        "odt_anio": str(plan.odt_anio or ""),
        "fecha_inspec_iso": fecha,
        "motivo_revision": plan.motivo_revision,
    }


def _plan_to_revisar_row(plan: PilotChainPlan) -> Dict[str, str]:
    return {
        "ec5_uuid": plan.ec5_uuid,
        "decision": plan.decision,
        "motivo_revision": plan.motivo_revision,
        "legacy_ref_hash": plan.legacy_ref_hash,
    }


def _write_pilot_outputs(
    output_dir: Path,
    plans: Sequence[PilotChainPlan],
    resumen: Mapping[str, Any],
) -> None:
    applicable_path = output_dir / "mapeo_piloto_aplicable.csv"
    revisar_path = output_dir / "mapeo_piloto_revisar.csv"
    resumen_path = output_dir / "resumen_piloto_importacion.json"

    with applicable_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(MAPEO_APPLICABLE_COLUMNS))
        w.writeheader()
        for p in plans:
            if p.decision in (DECISION_APPLICABLE, DECISION_INSERTED, DECISION_SKIPPED_IDEMPOTENT):
                w.writerow(_plan_to_applicable_row(p))

    with revisar_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(MAPEO_REVISAR_COLUMNS))
        w.writeheader()
        for p in plans:
            if p.decision in (DECISION_REVISAR, DECISION_ERROR):
                w.writerow(_plan_to_revisar_row(p))

    with resumen_path.open("w", encoding="utf-8") as f:
        json.dump(dict(resumen), f, ensure_ascii=False, indent=2)
