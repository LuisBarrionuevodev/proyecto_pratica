"""
Export CSV enriquecido de actuaciones históricas desde ``digitaliza_sandbox`` (read-only).

V1.1-MIG-ACTAS.0C — sin media, URLs ni escrituras en DB.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, joinedload, selectinload

from app.domains.migracion_historica.epicollect_actas_inventario import (
    assert_output_outside_repo,
    resolve_repo_root,
    sha256_file,
)
from app.domains.migracion_historica.historico_sandbox_export_security import (
    SanitizedDatabaseTarget,
    resolve_export_database_uri,
    validate_sandbox_export_database_uri,
)
from app.models.actuaciones import Actuaciones
from app.models.contribuyente import Contribuyente
from app.models.domicilio import Domicilio

# Campos no presentes en el esquema actual (se documentan en el resumen JSON).
SOURCE_UNAVAILABLE_FIELDS: Tuple[str, ...] = (
    "decomiso_faja",
    "decomiso_desnaturalizacion",
    "notificacion_estado_operativo",
)

EXPORT_CSV_COLUMNS: Tuple[str, ...] = (
    "legacy_actuacion_id",
    "legacy_ref_hash",
    "fecha_actuacion",
    "mes",
    "anio",
    "tipo_actuacion",
    "carga_solo_comprobacion",
    "ec5_uuid",
    "contraproducencia",
    "realizo_nueva_inspeccion",
    "resultado_cumplimiento_oficio",
    "odt_numero",
    "odt_anio",
    "inspeccion_numero",
    "inspeccion_anio",
    "notificacion_numero",
    "notificacion_anio",
    "notificacion_fecha",
    "notificacion_plazo_dias",
    "notificacion_fecha_vencimiento",
    "notificacion_motivos",
    "comprobacion_numero",
    "comprobacion_anio",
    "comprobacion_motivo",
    "clausura_numero",
    "clausura_anio",
    "decomiso_numero",
    "decomiso_anio",
    "decomiso_kilos",
    "expediente_numero",
    "expediente_anio",
    "oficio_numero",
    "oficio_anio",
    "oficio_causa",
    "juzgado_nombre",
    "documento",
    "nombre",
    "apellido",
    "razon_social",
    "titular_nombre_historico",
    "titular_apellido_historico",
    "titular_razon_social_historica",
    "calle",
    "domicilio_numero",
    "domicilio_numero_tipo",
    "ciudad",
    "codigo_postal",
    "nombre_local",
    "inspectores",
)

@dataclass
class ExportEnriquecidoResult:
    csv_path: Path
    resumen_path: Path
    csv_sha256: str
    total_exportadas: int
    target: SanitizedDatabaseTarget
    conteos: Dict[str, int] = field(default_factory=dict)
    campos_no_disponibles: Sequence[str] = field(default_factory=lambda: list(SOURCE_UNAVAILABLE_FIELDS))


def legacy_ref_hash_for_actuacion(actuacion_id: int) -> str:
    """Hash estable para referenciar la fila sin exponer PII en artefactos 0B."""
    payload = f"legacy_actuacion:{int(actuacion_id)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _enum_value(val: Any) -> str:
    if val is None:
        return ""
    return val.value if hasattr(val, "value") else str(val)


def _motivos_notificacion(act: Actuaciones) -> str:
    noti = act.notificacion
    if not noti or not getattr(noti, "motivos", None):
        return ""
    partes = sorted({(m.nombre or str(m.id)) for m in noti.motivos if m})
    return "|".join(p for p in partes if p)


def _pick_expediente_oficio(act: Actuaciones) -> Dict[str, str]:
    out = {
        "expediente_numero": "",
        "expediente_anio": "",
        "oficio_numero": "",
        "oficio_anio": "",
        "oficio_causa": "",
        "juzgado_nombre": "",
    }
    comp = act.comprobacion
    if not comp:
        return out
    raw_exp = getattr(comp, "expediente", None)
    if raw_exp is None:
        exp_list: List[Any] = []
    elif isinstance(raw_exp, list):
        exp_list = raw_exp
    else:
        exp_list = [raw_exp]
    for exp in exp_list:
        if exp and exp.numero_expediente:
            out["expediente_numero"] = str(exp.numero_expediente)
            out["expediente_anio"] = str(exp.anio or "")
            break
    oficios = getattr(comp, "oficio", None)
    if oficios is None:
        return out
    ofi_list = oficios if isinstance(oficios, list) else [oficios]
    for ofi in ofi_list:
        if not ofi:
            continue
        out["oficio_numero"] = str(ofi.numero_oficio or "")
        out["oficio_anio"] = str(ofi.anio or "")
        out["oficio_causa"] = str(ofi.causa or "")
        juz = getattr(ofi, "juzgado", None)
        if juz:
            out["juzgado_nombre"] = str(juz.nombre or juz.codigo or "")
        break
    return out


def _contribuyente_from_act(act: Actuaciones) -> Optional[Contribuyente]:
    dom = act.domicilio
    if dom and dom.contribuyente:
        return dom.contribuyente
    return None


def actuacion_to_export_row(act: Actuaciones) -> Dict[str, str]:
    """
    Convierte una actuación ORM en fila CSV (puede contener PII — solo archivo local).

    Args:
        act: actuación con relaciones ya cargadas cuando sea posible.

    Returns:
        Dict alineado a ``EXPORT_CSV_COLUMNS``.
    """
    contrib = _contribuyente_from_act(act)
    dom: Optional[Domicilio] = act.domicilio
    doc = exped = _pick_expediente_oficio(act)

    inspectores = ""
    if getattr(act, "inspector", None):
        inspectores = "|".join(sorted({i.nombre for i in act.inspector if i and i.nombre}))

    row: Dict[str, str] = {
        "legacy_actuacion_id": str(act.id),
        "legacy_ref_hash": legacy_ref_hash_for_actuacion(int(act.id)),
        "fecha_actuacion": act.fecha.isoformat() if act.fecha else "",
        "mes": str(act.mes or ""),
        "anio": str(act.anio or ""),
        "tipo_actuacion": _enum_value(act.tipo),
        "carga_solo_comprobacion": "1" if getattr(act, "carga_solo_comprobacion", False) else "0",
        "ec5_uuid": str(act.ec5_uuid or ""),
        "contraproducencia": _enum_value(act.contraproducencia),
        "realizo_nueva_inspeccion": (
            "1" if act.realizo_nueva_inspeccion is True else "0" if act.realizo_nueva_inspeccion is False else ""
        ),
        "resultado_cumplimiento_oficio": _enum_value(getattr(act, "resultado_cumplimiento_oficio", None)),
        "odt_numero": str(act.orden_trabajo.numero_acta) if act.orden_trabajo else "",
        "odt_anio": str(act.orden_trabajo.anio) if act.orden_trabajo else "",
        "inspeccion_numero": str(act.inspeccion.numero_acta) if act.inspeccion else "",
        "inspeccion_anio": str(act.inspeccion.anio) if act.inspeccion else "",
        "notificacion_numero": str(act.notificacion.numero_acta) if act.notificacion else "",
        "notificacion_anio": str(act.notificacion.anio) if act.notificacion else "",
        "notificacion_fecha": (
            act.notificacion.fecha_notificacion.isoformat()
            if act.notificacion and act.notificacion.fecha_notificacion
            else ""
        ),
        "notificacion_plazo_dias": (
            str(act.notificacion.plazo_dias) if act.notificacion else ""
        ),
        "notificacion_fecha_vencimiento": (
            act.notificacion.fecha_vencimiento.isoformat()
            if act.notificacion and act.notificacion.fecha_vencimiento
            else ""
        ),
        "notificacion_motivos": _motivos_notificacion(act),
        "comprobacion_numero": str(act.comprobacion.numero_acta) if act.comprobacion else "",
        "comprobacion_anio": str(act.comprobacion.anio) if act.comprobacion else "",
        "comprobacion_motivo": str(act.comprobacion.motivo or "") if act.comprobacion else "",
        "clausura_numero": str(act.clausura.numero_acta) if act.clausura else "",
        "clausura_anio": str(act.clausura.anio) if act.clausura else "",
        "decomiso_numero": str(act.decomiso.numero_acta) if act.decomiso else "",
        "decomiso_anio": str(act.decomiso.anio) if act.decomiso else "",
        "decomiso_kilos": str(act.decomiso.cantidad) if act.decomiso and act.decomiso.cantidad is not None else "",
        "documento": str(contrib.documento) if contrib else "",
        "nombre": str(contrib.nombre or "") if contrib else "",
        "apellido": str(contrib.apellido or "") if contrib else "",
        "razon_social": str(contrib.razon_social or "") if contrib else "",
        "titular_nombre_historico": str(getattr(act, "titular_nombre_historico", "") or ""),
        "titular_apellido_historico": str(getattr(act, "titular_apellido_historico", "") or ""),
        "titular_razon_social_historica": str(getattr(act, "titular_razon_social_historica", "") or ""),
        "calle": str(dom.calle) if dom else "",
        "domicilio_numero": str(dom.numero) if dom else "",
        "domicilio_numero_tipo": str(dom.numero_tipo or "") if dom else "",
        "ciudad": str(dom.ciudad or "") if dom else "",
        "codigo_postal": str(dom.cp or "") if dom else "",
        "nombre_local": str(act.nombre_local or ""),
        "inspectores": inspectores,
    }
    row.update(doc)
    return row


def _assert_row_has_no_media_urls(row: Mapping[str, str]) -> None:
    joined = " ".join(row.values()).lower()
    if "http://" in joined or "https://" in joined:
        raise ValueError("export contiene URL")


def _load_options():
    from app.models.comprobacion import Comprobacion
    from app.models.inspector import Inspector
    from app.models.motivo import Motivo
    from app.models.notificacion import Notificacion
    from app.models.oficio import Oficio

    return (
        joinedload(Actuaciones.orden_trabajo),
        joinedload(Actuaciones.notificacion).selectinload(Notificacion.motivos),
        joinedload(Actuaciones.comprobacion).selectinload(Comprobacion.expediente),
        joinedload(Actuaciones.comprobacion)
        .selectinload(Comprobacion.oficio)
        .joinedload(Oficio.juzgado),
        joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
        joinedload(Actuaciones.clausura),
        joinedload(Actuaciones.decomiso),
        joinedload(Actuaciones.inspeccion),
        selectinload(Actuaciones.inspector).joinedload(Inspector.turno),
    )


def fetch_actuaciones_readonly(session: Session) -> List[Actuaciones]:
    """Carga actuaciones con relaciones necesarias (solo SELECT)."""
    opts = _load_options()
    return session.query(Actuaciones).options(*opts).order_by(Actuaciones.id.asc()).all()


def _install_readonly_guard(engine) -> None:
    """Bloquea statements de escritura en la conexión del export."""

    @event.listens_for(engine, "before_cursor_execute")
    def _block_writes(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        head = (statement or "").lstrip().upper()
        if head.startswith(("INSERT", "UPDATE", "DELETE", "REPLACE", "DROP", "ALTER", "CREATE", "TRUNCATE")):
            raise RuntimeError("Export histórico: operación de escritura en DB bloqueada.")


def compute_export_stats(rows: Sequence[Mapping[str, str]]) -> Dict[str, int]:
    """Métricas agregadas sin PII."""
    def _has(col: str) -> int:
        return sum(1 for r in rows if (r.get(col) or "").strip())

    con_notif = _has("notificacion_numero")
    con_comp = _has("comprobacion_numero")
    ambas = sum(
        1
        for r in rows
        if (r.get("notificacion_numero") or "").strip() and (r.get("comprobacion_numero") or "").strip()
    )
    return {
        "total_actuaciones_exportadas": len(rows),
        "con_notificacion": con_notif,
        "con_comprobacion": con_comp,
        "con_ambas_actas": ambas,
        "con_clausura": _has("clausura_numero"),
        "con_decomiso": _has("decomiso_numero"),
        "con_documento": _has("documento"),
        "con_domicilio": _has("calle"),
        "con_titular": sum(
            1
            for r in rows
            if (r.get("razon_social") or r.get("nombre") or r.get("titular_razon_social_historica") or "").strip()
        ),
    }


def write_enriquecido_outputs(
    rows: Sequence[Dict[str, str]],
    output_dir: Path,
    target: SanitizedDatabaseTarget,
    campos_no_disponibles: Sequence[str],
) -> ExportEnriquecidoResult:
    """Escribe CSV (PII permitido) y resumen JSON sin PII."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "inventario_actas_historicas_enriquecido.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(EXPORT_CSV_COLUMNS))
        writer.writeheader()
        for row in rows:
            _assert_row_has_no_media_urls(row)
            writer.writerow({k: row.get(k, "") for k in EXPORT_CSV_COLUMNS})

    csv_sha = sha256_file(csv_path)
    stats = compute_export_stats(rows)
    resumen = {
        "database": target.database,
        "host": target.host,
        "port": target.port,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "csv_sha256": csv_sha,
        "csv_filename": csv_path.name,
        "conteos": stats,
        "campos_no_disponibles_en_fuente": list(campos_no_disponibles),
        "media_urls_exportadas": False,
        "modo": "READ_ONLY_SELECT",
    }
    resumen_path = output_dir / "resumen_export_actas_historicas_enriquecido.json"
    with resumen_path.open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    return ExportEnriquecidoResult(
        csv_path=csv_path,
        resumen_path=resumen_path,
        csv_sha256=csv_sha,
        total_exportadas=len(rows),
        target=target,
        conteos=stats,
        campos_no_disponibles=campos_no_disponibles,
    )


def export_actas_historicas_enriquecidas(
    output_dir: Path,
    database_uri: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> ExportEnriquecidoResult:
    """
    Exporta actuaciones desde sandbox local a CSV enriquecido + resumen JSON.

    Args:
        output_dir: directorio fuera del repositorio.
        database_uri: URI opcional (mismas validaciones que config local).
        repo_root: raíz git para validar salida.

    Returns:
        ExportEnriquecidoResult con rutas y métricas.

    Raises:
        HistoricoExportSecurityError: URI no permitida.
        ValueError: salida dentro del repo.
        RuntimeError: intento de escritura en DB.
    """
    root = repo_root or resolve_repo_root()
    assert_output_outside_repo(output_dir, root)

    uri = resolve_export_database_uri(database_uri)
    target = validate_sandbox_export_database_uri(uri)

    engine = create_engine(uri, pool_pre_ping=True)
    _install_readonly_guard(engine)

    rows: List[Dict[str, str]] = []
    with Session(engine) as session:
        actuaciones = fetch_actuaciones_readonly(session)
        for act in actuaciones:
            rows.append(actuacion_to_export_row(act))

    return write_enriquecido_outputs(
        rows,
        output_dir,
        target,
        SOURCE_UNAVAILABLE_FIELDS,
    )


def actuacion_like_from_row_dict(data: Mapping[str, Any]) -> Actuaciones:
    """Helper de tests: construye un ``Actuaciones`` mínimo desde dict plano."""
    act = Actuaciones()
    for key in ("id", "mes", "anio", "nombre_local", "ec5_uuid"):
        if key in data:
            setattr(act, key, data[key])
    if "fecha" in data:
        act.fecha = data["fecha"]
    if "tipo" in data:
        act.tipo = data["tipo"]
    if "carga_solo_comprobacion" in data:
        act.carga_solo_comprobacion = data["carga_solo_comprobacion"]
    for rel_name in (
        "orden_trabajo",
        "notificacion",
        "comprobacion",
        "clausura",
        "decomiso",
        "inspeccion",
        "domicilio",
        "inspector",
    ):
        if rel_name in data:
            setattr(act, rel_name, data[rel_name])
    return act
