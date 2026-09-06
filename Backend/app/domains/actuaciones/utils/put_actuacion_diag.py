"""
Logging diagnóstico temporal — GESTIÓN-FIX.10B.1.6.

Solo trazas; no altera comportamiento. Activar con env ``PUT_ACTUACION_DIAG=1``.
"""

from __future__ import annotations

import json
import logging
import os
import traceback
from typing import Any

from app.models import Actuaciones, Clausura, Decomiso, Expediente, Inspeccion, IniciadorRuta, Oficio

logger = logging.getLogger("put_actuacion_diag")


def diag_enabled() -> bool:
    """True si el logging diagnóstico está activo."""
    return os.environ.get("PUT_ACTUACION_DIAG", "").strip() in ("1", "true", "TRUE", "yes")


def _enabled() -> bool:
    return diag_enabled()


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return repr(obj)


def configure_diag_logging() -> None:
    """Configura handler de consola para trazas FIX.10B.1.6 (idempotente)."""
    if not diag_enabled():
        return
    if not logging.root.handlers:
        logging.basicConfig(level=logging.WARNING)
    logger.setLevel(logging.WARNING)


def log_put_request(actuacion_id: int, raw_body: dict[str, Any], mapped_payload: dict[str, Any]) -> None:
    """Registra JSON crudo y payload mapeado del PUT."""
    if not _enabled():
        return
    keys_interes = (
        "contraproducencia",
        "limpiar_contraproducencia",
        "limpiar_contribuyente",
        "actas_a_quitar",
        "acta_inspeccion_num",
        "acta_notificacion_num",
        "acta_comprobacion_num",
        "acta_clausura_num",
        "acta_decomiso_num",
        "notificacion_motivo_1",
        "notificacion_motivo_2",
        "notificacion_motivo_3",
        "comprobacion_motivo",
        "doc_nro",
        "contrib_nombre",
        "contrib_apellido",
        "razon_social",
        "notificacion",
        "comprobacion",
        "contribuyente",
        "domicilio",
    )
    raw_subset = {k: raw_body.get(k) for k in keys_interes if k in raw_body}
    mapped_subset = {k: mapped_payload.get(k) for k in keys_interes if k in mapped_payload}
    logger.warning(
        "[FIX.10B.1.6] PUT actuacion_id=%s RAW=%s MAPPED=%s",
        actuacion_id,
        _safe_json(raw_subset),
        _safe_json(mapped_subset),
    )


def log_actas_before(act: Actuaciones, actas_a_quitar: list[str] | None) -> None:
    """Estado de actas al entrar a ``actualizar_actuacion``."""
    if not _enabled():
        return
    ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
    cl = Clausura.query.filter_by(actuacion_id=act.id).first()
    dec = Decomiso.query.filter_by(actuacion_id=act.id).first()
    logger.warning(
        "[FIX.10B.1.6] BEFORE act_id=%s "
        "INSPECCION=%s notif_id=%s comp_id=%s CLAUSURA=%s DECOMISO=%s "
        "actas_a_quitar=%s",
        act.id,
        getattr(ins, "numero_acta", None) if ins else None,
        act.notificacion_id,
        act.comprobacion_id,
        getattr(cl, "numero_acta", None) if cl else None,
        getattr(dec, "numero_acta", None) if dec else None,
        actas_a_quitar,
    )


def log_stage(actuacion_id: int, stage: str) -> None:
    """Marca etapa alcanzada en el PUT transaccional."""
    if not _enabled():
        return
    logger.warning("[FIX.10B.1.6] STAGE act_id=%s → %s", actuacion_id, stage)


def log_acta_dependencies(act: Actuaciones, tipo: str) -> None:
    """
    Audita dependencias documentales antes de quitar NOTIFICACION / COMPROBACION.
    Solo trazas; no altera comportamiento.
    """
    if not _enabled():
        return
    t = (tipo or "").strip().upper()
    act_id = int(act.id)
    if t == "NOTIFICACION":
        nid = act.notificacion_id
        if not nid:
            logger.warning("[FIX.10B.1.6] DEPS act_id=%s NOTIFICACION sin vínculo", act_id)
            return
        exp_count = (
            Expediente.query.filter(
                Expediente.notificacion_id == int(nid),
                Expediente.deleted_at.is_(None),
            ).count()
        )
        ini_rn = (
            IniciadorRuta.query.filter(
                IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
                IniciadorRuta.notificacion_id == int(nid),
            ).count()
        )
        prorroga = None
        if act.notificacion is not None:
            prorroga = getattr(act.notificacion, "prorroga_dias", None)
        logger.warning(
            "[FIX.10B.1.6] DEPS act_id=%s NOTIFICACION id=%s expedientes=%s "
            "iniciadores_rn=%s prorroga_dias=%s",
            act_id,
            nid,
            exp_count,
            ini_rn,
            prorroga,
        )
    elif t == "COMPROBACION":
        cid = act.comprobacion_id
        if not cid:
            logger.warning("[FIX.10B.1.6] DEPS act_id=%s COMPROBACION sin vínculo", act_id)
            return
        exp_count = (
            Expediente.query.filter(
                Expediente.comprobacion_id == int(cid),
                Expediente.oficio_id.is_(None),
                Expediente.deleted_at.is_(None),
            ).count()
        )
        of_count = (
            Oficio.query.filter(
                Oficio.comprobacion_id == int(cid),
                Oficio.deleted_at.is_(None),
            ).count()
        )
        ini_ro = (
            IniciadorRuta.query.filter(
                IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
                IniciadorRuta.comprobacion_id == int(cid),
            ).count()
        )
        cl = Clausura.query.filter_by(actuacion_id=act_id).first()
        dec = Decomiso.query.filter_by(actuacion_id=act_id).first()
        logger.warning(
            "[FIX.10B.1.6] DEPS act_id=%s COMPROBACION id=%s expedientes_envio=%s "
            "oficios=%s iniciadores_ro=%s clausura=%s decomiso=%s",
            act_id,
            cid,
            exp_count,
            of_count,
            ini_ro,
            getattr(cl, "numero_acta", None) if cl else None,
            getattr(dec, "numero_acta", None) if dec else None,
        )


def log_quitar_acta(actuacion_id: int, tipo: str, resultado: str, detalle: str = "") -> None:
    """Trazas por acta en ``quitar_actas_de_actuacion_en_sesion``."""
    if not _enabled():
        return
    logger.warning(
        "[FIX.10B.1.6] QUITAR act_id=%s tipo=%s → %s %s",
        actuacion_id,
        tipo,
        resultado,
        detalle,
    )


def log_exception(actuacion_id: int, exc: BaseException) -> None:
    """Excepción completa con traceback."""
    if not _enabled():
        return
    tb = traceback.format_exc()
    logger.error(
        "[FIX.10B.1.6] EXCEPTION act_id=%s type=%s msg=%s\n%s",
        actuacion_id,
        type(exc).__name__,
        exc,
        tb,
    )
