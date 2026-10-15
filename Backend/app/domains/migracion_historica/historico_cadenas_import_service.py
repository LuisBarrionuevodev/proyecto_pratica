"""
Planificación e importación por fases de cadenas históricas (V1.1-MIG-ACTAS.1C).

Sin rutas ni iniciadores operativos; vínculos vía previas y FKs existentes.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.attach.clausura import attach_clausura
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.attach.domicilio import get_or_create_domicilio
from app.domains.actuaciones.attach.expediente import attach_expediente
from app.domains.actuaciones.attach.inspeccion import attach_inspeccion
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.actuaciones.attach.oficio import attach_oficio
from app.domains.actuaciones.attach.orden_trabajo import get_or_create_orden_trabajo
from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.catalogs.motivo import get_motivo_o_falla
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.actuaciones.services.previas_service import resolver_previas
from app.domains.migracion_historica.epicollect_actas_inventario import (
    RowSnapshot,
    _cell,
    _es_ratificacion,
    _es_reinspeccion_notificacion,
    _es_reinspeccion_oficio,
    _extract_expediente_claves,
    _first_index,
    _header_indices,
    _normalize_acta_num,
)
from app.domains.migracion_historica.epicollect_cadenas_historicas import (
    EstadoVinculo,
    analizar_cadena_reinspeccion,
    build_acta_indexes,
    build_expediente_index,
    mask_acta_correlacion,
)
if TYPE_CHECKING:
    from app.domains.migracion_historica.historico_piloto_import_service import PilotChainPlan
from app.models import Actuaciones, Comprobacion, Expediente, MigracionHistoricaRegistro, Notificacion, Oficio
from app.utils.actas import acta_6

FASE_1_RAIZ = "1_RAIZ"
FASE_2_REINSPECCION = "2_REINSPECCION_NOTIFICACION"
FASE_3_OFICIO = "3_OFICIO"

ESTADO_VINCULO_CONFIABLE = "VINCULO_CONFIABLE"
ESTADO_VINCULO_REVISAR = "REVISAR"

MOTIVO_REINSPECCION_SIN_ORIGEN = "reinspeccion_notificacion_sin_origen_confiable"
MOTIVO_OFICIO_SIN_ORIGEN = "oficio_sin_comprobacion_expediente_origen_confiable"

CADENA_PLAN_COLUMNS: Tuple[str, ...] = (
    "ec5_uuid",
    "fase_importacion",
    "tipo_cadena",
    "estado_vinculo",
    "decision",
    "motivo_revision",
    "parent_source_uuid",
    "parent_source_hash",
    "acta_origen_numero",
    "parent_target_id",
    "legacy_ref_hash",
)

SOURCE_NAME = "epicollect_odt_pilot_v1"


@dataclass
class AdministrativoEpi:
    """Triplete expediente/oficio extraído de fila EpiCollect."""

    expediente_num: str
    expediente_anio: str
    oficio_num: str


def clasificar_fase_importacion(snap: RowSnapshot) -> str:
    """Asigna fase 1/2/3 según tipo EpiCollect."""
    if _es_reinspeccion_notificacion(snap.tipo_inspeccion):
        return FASE_2_REINSPECCION
    if _es_reinspeccion_oficio(snap.tipo_inspeccion) or _es_ratificacion(snap.tipo_inspeccion):
        return FASE_3_OFICIO
    return FASE_1_RAIZ


def resolver_tipo_cadena(snap: RowSnapshot, fase: str) -> str:
    """Etiqueta legible del rol en la cadena."""
    if fase == FASE_1_RAIZ:
        if snap.acta_comprobacion_num and snap.acta_notificacion_num:
            return "inspeccion_notificacion_comprobacion"
        if snap.acta_notificacion_num:
            return "notificacion"
        if snap.acta_comprobacion_num:
            return "comprobacion"
        return "inspeccion"
    if fase == FASE_2_REINSPECCION:
        return "reinspeccion_notificacion"
    t = (snap.tipo_inspeccion or "").casefold()
    if "ratificaci" in t and "clausura" in t:
        return "ratificacion_clausura"
    if "ratificaci" in t and "decomiso" in t:
        return "ratificacion_decomiso"
    if "verificar" in t:
        return "verificar_informar"
    return "oficio"


def parse_administrativo_from_row(
    raw: Sequence[str],
    hdr: Sequence[str],
) -> Optional[AdministrativoEpi]:
    """Primer triplete expediente/año/oficio de la fila."""
    by_name = _header_indices(hdr)
    claves = _extract_expediente_claves(raw, by_name)
    if not claves:
        return None
    parts = claves[0].split("|")
    if len(parts) != 3:
        return None
    return AdministrativoEpi(expediente_num=parts[0], expediente_anio=parts[1], oficio_num=parts[2])


def enriquecer_planes_con_cadenas(
    plans: List["PilotChainPlan"],
    historic_snaps: Sequence[RowSnapshot],
) -> None:
    """
    Clasifica fases y aplica conciliación de vínculos EpiCollect a cada plan.

    Puede degradar decisiones a REVISAR si el vínculo no es confiable.
    """
    by_key, by_tipo_num = build_acta_indexes(historic_snaps)
    expediente_index = build_expediente_index(historic_snaps)

    for plan in plans:
        snap = plan.snap
        if not snap:
            plan.fase_importacion = FASE_1_RAIZ
            plan.estado_vinculo = ESTADO_VINCULO_REVISAR
            continue

        plan.fase_importacion = clasificar_fase_importacion(snap)
        plan.tipo_cadena = resolver_tipo_cadena(snap, plan.fase_importacion)

        if plan.fase_importacion == FASE_1_RAIZ:
            plan.estado_vinculo = ESTADO_VINCULO_CONFIABLE
            plan.parent_source_uuid = ""
            plan.parent_source_hash = ""
            plan.acta_origen_numero = ""
            continue

        cadena = analizar_cadena_reinspeccion(snap, by_tipo_num, expediente_index)
        plan.parent_source_uuid = cadena.fuente_previa_uuid or ""
        plan.parent_source_hash = cadena.previa_acta_hash or cadena.acta_referencia_hash or ""
        ref_num = _normalize_acta_num(snap.ref_notificacion_previa)
        if plan.fase_importacion == FASE_2_REINSPECCION and ref_num:
            plan.acta_origen_numero = ref_num
        elif cadena.acta_referencia_hash and not cadena.acta_referencia_hash.startswith("exp:"):
            plan.acta_origen_numero = ref_num or ""

        if cadena.estado_vinculo == EstadoVinculo.VINCULO_CONFIABLE:
            plan.estado_vinculo = ESTADO_VINCULO_CONFIABLE
        else:
            plan.estado_vinculo = ESTADO_VINCULO_REVISAR
            if plan.decision not in ("REVISAR", "ERROR", "INSERTED", "SKIPPED_IDEMPOTENT"):
                plan.decision = "REVISAR"
            if plan.fase_importacion == FASE_2_REINSPECCION:
                plan.motivo_revision = MOTIVO_REINSPECCION_SIN_ORIGEN
            else:
                plan.motivo_revision = MOTIVO_OFICIO_SIN_ORIGEN
            if cadena.motivo_revision and plan.motivo_revision == MOTIVO_OFICIO_SIN_ORIGEN:
                plan.motivo_revision = (
                    f"{MOTIVO_OFICIO_SIN_ORIGEN}:{cadena.motivo_revision}"
                )[:200]


def _actuacion_por_ec5(ec5_uuid: str) -> Optional[Actuaciones]:
    if not ec5_uuid:
        return None
    return Actuaciones.query.filter_by(ec5_uuid=ec5_uuid).first()


def _actuacion_con_notificacion(acta_num: str, anio: int) -> Optional[Actuaciones]:
    num = acta_6(acta_num)
    if not num:
        return None
    noti = Notificacion.query.filter_by(numero_acta=num, anio=anio).first()
    if not noti:
        return None
    q = Actuaciones.query.filter_by(notificacion_id=noti.id, anio=anio)
    rows = q.all()
    if len(rows) != 1:
        return None
    return rows[0]


def _comprobacion_por_acta(acta_num: str, anio: int) -> Optional[Comprobacion]:
    num = acta_6(acta_num)
    if not num:
        return None
    return Comprobacion.query.filter_by(numero_acta=num, anio=anio).first()


def validar_vinculo_en_destino(plan: "PilotChainPlan") -> Optional[str]:
    """
    Comprueba que el padre existe en la base destino antes de importar derivados.

    Returns:
        Motivo de revisión si falla; None si OK.
    """
    snap = plan.snap
    if not snap or not snap.fecha_inspec:
        return "snapshot_invalido"
    if plan.estado_vinculo != ESTADO_VINCULO_CONFIABLE:
        return plan.motivo_revision or MOTIVO_REINSPECCION_SIN_ORIGEN

    anio = snap.fecha_inspec.year

    if plan.fase_importacion == FASE_2_REINSPECCION:
        parent = _actuacion_por_ec5(plan.parent_source_uuid)
        ref = _normalize_acta_num(snap.ref_notificacion_previa)
        if not parent and ref:
            parent = _actuacion_con_notificacion(ref, anio)
        if not parent or not parent.notificacion_id:
            return MOTIVO_REINSPECCION_SIN_ORIGEN
        noti = Notificacion.query.get(parent.notificacion_id)
        if not noti:
            return MOTIVO_REINSPECCION_SIN_ORIGEN
        if ref and acta_6(ref) != acta_6(noti.numero_acta):
            return MOTIVO_REINSPECCION_SIN_ORIGEN
        if parent.fecha and snap.fecha_inspec <= parent.fecha:
            return MOTIVO_REINSPECCION_SIN_ORIGEN
        plan.parent_target_id = int(parent.id)
        plan.acta_origen_numero = acta_6(noti.numero_acta) or plan.acta_origen_numero
        return None

    if plan.fase_importacion == FASE_3_OFICIO:
        parent_act = _actuacion_por_ec5(plan.parent_source_uuid)
        comp: Optional[Comprobacion] = None
        if parent_act and parent_act.comprobacion_id:
            comp = Comprobacion.query.get(parent_act.comprobacion_id)
        if comp is None:
            ref = _normalize_acta_num(snap.ref_comprobacion_previa)
            if ref:
                comp = _comprobacion_por_acta(ref, anio)
                if comp:
                    parent_act = (
                        Actuaciones.query.filter_by(comprobacion_id=comp.id, anio=anio)
                        .order_by(Actuaciones.id.asc())
                        .first()
                    )
        if comp is None or parent_act is None:
            return MOTIVO_OFICIO_SIN_ORIGEN

        exp_envio = (
            Expediente.query.filter_by(comprobacion_id=comp.id, oficio_id=None).first()
        )
        ofi = Oficio.query.filter_by(comprobacion_id=comp.id).first()
        if plan.administrativo and (not exp_envio or not ofi):
            _materializar_administrativo_en_comprobacion(comp, plan.administrativo, anio)
            exp_envio = (
                Expediente.query.filter_by(comprobacion_id=comp.id, oficio_id=None).first()
            )
            ofi = Oficio.query.filter_by(comprobacion_id=comp.id).first()
        if not exp_envio or not ofi:
            return MOTIVO_OFICIO_SIN_ORIGEN

        tipo_c = (plan.tipo_cadena or "").casefold()
        if "ratificacion_clausura" in tipo_c and not parent_act.clausura:
            return MOTIVO_OFICIO_SIN_ORIGEN
        if "ratificacion_decomiso" in tipo_c and not parent_act.decomiso:
            return MOTIVO_OFICIO_SIN_ORIGEN
        if parent_act.fecha and snap.fecha_inspec <= parent_act.fecha:
            return MOTIVO_OFICIO_SIN_ORIGEN

        plan.parent_target_id = int(parent_act.id)
        plan.acta_origen_numero = acta_6(comp.numero_acta) or ""
        return None

    return None


def _materializar_administrativo_en_comprobacion(
    comp: Comprobacion,
    admin: AdministrativoEpi,
    anio_actuacion: int,
) -> None:
    """Crea expediente de envío y oficio mínimos en la comprobación padre si faltan."""
    attach_expediente(
        {"numero": admin.expediente_num, "anio": str(admin.expediente_anio)},
        comp.id,
        None,
    )
    attach_oficio(
        {
            "numero": admin.oficio_num,
            "anio": anio_actuacion,
        },
        comp.id,
    )
    db.session.flush()


def _crear_actuacion_base(plan: "PilotChainPlan") -> Actuaciones:
    """Crea actuación vacía con domicilio/inspectores (sin actas)."""
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
    return act


def _adjuntar_actas_visita(act: Actuaciones, plan: "PilotChainPlan") -> None:
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


def importar_cadena_historica(plan: "PilotChainPlan") -> int:
    """
    Importa una cadena según su fase (transacción a nivel de llamador).

    Returns:
        id de actuación creada.

    Raises:
        ValueError: vínculo o reglas de negocio.
    """
    motivo = validar_vinculo_en_destino(plan)
    if motivo and plan.fase_importacion != FASE_1_RAIZ:
        raise ValueError(motivo)
    if plan.fase_importacion == FASE_1_RAIZ:
        motivo = None

    if plan.fase_importacion == FASE_1_RAIZ:
        if not plan.tipo_actuacion or plan.tipo_actuacion == "REINSPECCION":
            plan.tipo_actuacion = "INSPECCION"
        act = _crear_actuacion_base(plan)
        _adjuntar_actas_visita(act, plan)
        return int(act.id)

    if plan.fase_importacion == FASE_2_REINSPECCION:
        plan.tipo_actuacion = "REINSPECCION"
        act = _crear_actuacion_base(plan)
        prev_payload: Dict[str, Any] = {}
        if plan.acta_origen_numero:
            prev_payload["acta_notificacion_previa_num"] = plan.acta_origen_numero
        resolver_previas(act, prev_payload)
        if plan.acta_inspeccion:
            attach_inspeccion(act, plan.acta_inspeccion, crear=True)
        if plan.comprobacion:
            attach_comprobacion(act, plan.comprobacion)
        if plan.clausura:
            attach_clausura(act, plan.clausura, crear=True)
        if plan.decomiso:
            attach_decomiso(act, plan.decomiso, crear=True)
        db.session.add(act)
        db.session.flush()
        return int(act.id)

    # Fase 3
    act = _crear_actuacion_base(plan)
    comp_num = plan.acta_origen_numero
    prev_payload = {}
    if comp_num:
        prev_payload["comprobacion_previa_num"] = comp_num
        if plan.comprobacion and plan.comprobacion.get("motivo"):
            prev_payload["comprobacion_previa_motivo"] = plan.comprobacion["motivo"]
    resolver_previas(act, prev_payload)
    if plan.acta_inspeccion:
        attach_inspeccion(act, plan.acta_inspeccion, crear=True)
    if plan.comprobacion and plan.comprobacion.get("acta_num"):
        attach_comprobacion(act, plan.comprobacion)
    if plan.clausura:
        attach_clausura(act, plan.clausura, crear=True)
    if plan.decomiso:
        attach_decomiso(act, plan.decomiso, crear=True)
    db.session.add(act)
    db.session.flush()
    return int(act.id)


def _plan_to_cadena_row(plan: "PilotChainPlan") -> Dict[str, str]:
    return {
        "ec5_uuid": plan.ec5_uuid,
        "fase_importacion": plan.fase_importacion or "",
        "tipo_cadena": plan.tipo_cadena or "",
        "estado_vinculo": plan.estado_vinculo or "",
        "decision": plan.decision,
        "motivo_revision": plan.motivo_revision,
        "parent_source_uuid": plan.parent_source_uuid or "",
        "parent_source_hash": plan.parent_source_hash or "",
        "acta_origen_numero": plan.acta_origen_numero or "",
        "parent_target_id": str(plan.parent_target_id or ""),
        "legacy_ref_hash": plan.legacy_ref_hash,
    }


def build_resumen_cadenas(plans: Sequence["PilotChainPlan"]) -> Dict[str, Any]:
    """Conteos por fase sin PII."""
    por_fase: Counter = Counter()
    por_vinculo: Counter = Counter()
    por_tipo: Counter = Counter()
    revisar_motivos: Counter = Counter()
    for p in plans:
        por_fase[p.fase_importacion or "sin_fase"] += 1
        por_vinculo[p.estado_vinculo or ""] += 1
        por_tipo[p.tipo_cadena or ""] += 1
        if p.decision == "REVISAR" and p.motivo_revision:
            revisar_motivos[p.motivo_revision.split(":")[0]] += 1
    return {
        "conteos_por_fase": dict(por_fase),
        "conteos_estado_vinculo": dict(por_vinculo),
        "conteos_tipo_cadena": dict(por_tipo),
        "revisar_por_motivo": dict(revisar_motivos),
    }


def write_cadenas_outputs(output_dir: Path, plans: Sequence["PilotChainPlan"]) -> Path:
    """Escribe CSVs y resumen de cadenas fuera del repo."""
    resumen = build_resumen_cadenas(plans)
    resumen_path = output_dir / "resumen_cadenas_importacion.json"
    with resumen_path.open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    fase_files = {
        FASE_1_RAIZ: output_dir / "plan_fase_1_raiz.csv",
        FASE_2_REINSPECCION: output_dir / "plan_fase_2_reinspecciones.csv",
        FASE_3_OFICIO: output_dir / "plan_fase_3_oficios.csv",
    }
    for fase, path in fase_files.items():
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(CADENA_PLAN_COLUMNS))
            w.writeheader()
            for p in plans:
                if p.fase_importacion == fase:
                    w.writerow(_plan_to_cadena_row(p))

    revisar_path = output_dir / "plan_revisar_cadenas.csv"
    with revisar_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(CADENA_PLAN_COLUMNS))
        w.writeheader()
        for p in plans:
            if p.decision == "REVISAR" or p.estado_vinculo == ESTADO_VINCULO_REVISAR:
                w.writerow(_plan_to_cadena_row(p))

    return resumen_path


def reporte_registros_piloto_existentes(output_dir: Path) -> Path:
    """
    Clasifica registros ya importados en destino (sin modificar datos).

    Returns:
        Ruta del JSON generado.
    """
    registros = (
        db.session.query(MigracionHistoricaRegistro)
        .filter_by(source_name=SOURCE_NAME, decision="INSERTED")
        .all()
    )
    filas: List[Dict[str, Any]] = []
    for reg in registros:
        act = None
        if reg.target_actuacion_id:
            act = (
                Actuaciones.query.options(
                    joinedload(Actuaciones.notificacion),
                    joinedload(Actuaciones.comprobacion),
                )
                .filter_by(id=reg.target_actuacion_id)
                .first()
            )
        clasificacion = "desconocido"
        if act:
            if act.tipo == "REINSPECCION":
                clasificacion = "derivado_reinspeccion_notificacion"
            elif act.tipo in ("VERIFICAR E INFORMAR", "RATIFICACION DE CLAUSURA", "RATIFICACION DE DECOMISO"):
                clasificacion = "derivado_oficio"
            elif act.notificacion_id and act.comprobacion_id:
                clasificacion = "raiz_notificacion_y_comprobacion"
            elif act.notificacion_id:
                clasificacion = "raiz_con_notificacion"
            elif act.comprobacion_id:
                clasificacion = "raiz_con_comprobacion"
            else:
                clasificacion = "raiz_inspeccion"
            vinculo = "con_fk"
            if act.tipo == "REINSPECCION" and not act.notificacion_id:
                vinculo = "reinspeccion_sin_notificacion_id"
            if act.tipo in ("VERIFICAR E INFORMAR", "RATIFICACION DE CLAUSURA", "RATIFICACION DE DECOMISO"):
                if not act.comprobacion_id:
                    vinculo = "oficio_sin_comprobacion_id"
        else:
            vinculo = "sin_actuacion"
        filas.append(
            {
                "source_record_uuid": reg.source_record_uuid,
                "target_actuacion_id": reg.target_actuacion_id,
                "clasificacion": clasificacion,
                "estado_vinculo_observado": vinculo,
            }
        )
    out = output_dir / "reporte_registros_piloto_existentes.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump({"registros": filas, "total": len(filas)}, f, ensure_ascii=False, indent=2)
    return out
