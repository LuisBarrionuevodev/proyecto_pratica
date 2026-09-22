"""
Alta y edición de actuaciones históricas (solo acta de comprobación).

Canal: Cargar actuación con ``carga_solo_comprobacion=true``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.attach.domicilio import get_or_create_domicilio
from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.services.actas_canal_payload_guard import (
    rechazar_oficio_expediente_en_payload_canal_actas,
)
from app.domains.rutas_trabajo.services.auth_service import resolve_actor_user_id
from app.models import Actuaciones
from app.utils.fechas import parse_fecha_grid


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


_HISTORICAL_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "orden_trabajo_numero",
        "rubro_nombre",
        "nombre_local",
        "tipo_actuacion",
        "contraproducencia",
        "limpiar_contraproducencia",
        "acta_inspeccion_num",
        "items_acta_inspeccion",
        "notificacion",
        "acta_notificacion_num",
        "notificacion_motivo_1",
        "notificacion_motivo_2",
        "notificacion_motivo_3",
        "cantidad_personas_sin_carnet_sanidad",
        "clausura",
        "acta_clausura_num",
        "decomiso",
        "acta_decomiso_num",
        "decomiso_kilos_total",
        "notificacion_previa_num",
        "comprobacion_previa_num",
        "contribuyente",
        "doc_nro",
        "rubro_nombre",
        "numero_tipo",
    }
)


def _payload_value_present(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, tuple, set, dict)):
        return len(v) > 0
    if isinstance(v, bool):
        return v
    return True


def rechazar_campos_prohibidos_historicos_en_payload(payload: Dict[str, Any]) -> None:
    """
    Rechaza payload híbrido en modo histórico.

    Raises:
        ValueError: si llega algún campo operativo incompatible.
    """
    for key in _HISTORICAL_FORBIDDEN_PAYLOAD_KEYS:
        if key in payload and _payload_value_present(payload.get(key)):
            raise ValueError(f"El campo '{key}' no es compatible con carga histórica solo comprobación.")


def titular_snapshot_desde_payload(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Normaliza titular histórico desde payload canónico o keys de grilla.

    Retorno:
        Dict con ``titular_nombre_historico``, ``titular_apellido_historico``,
        ``titular_razon_social_historica``.
    """
    nombre = _clean_str(payload.get("titular_nombre_historico") or payload.get("contrib_nombre"))
    apellido = _clean_str(payload.get("titular_apellido_historico") or payload.get("contrib_apellido"))
    razon = _clean_str(
        payload.get("titular_razon_social_historica") or payload.get("razon_social")
    )
    return {
        "titular_nombre_historico": nombre,
        "titular_apellido_historico": apellido,
        "titular_razon_social_historica": razon,
    }


def _domicilio_data_desde_payload(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Extrae calle/número del payload canónico (``domicilio`` o keys planas)."""
    dom = payload.get("domicilio") or {}
    return {
        "calle": _clean_str(dom.get("calle") or payload.get("calle")),
        "numero": _clean_str(dom.get("numero") or payload.get("numero")),
        "numero_tipo": _clean_str(dom.get("numero_tipo") or payload.get("numero_tipo")),
    }


def validar_domicilio_historico(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Valida domicilio mínimo para carga histórica.

    Retorna dict calle/numero normalizados.

    Raises:
        ValueError: si falta calle o número.
    """
    data = _domicilio_data_desde_payload(payload)
    if not data["calle"]:
        raise ValueError("Ingrese la calle.")
    if not data["numero"]:
        raise ValueError("Ingrese el número.")
    return data


def resolver_domicilio_historico(payload: Dict[str, Any]):
    """
    Crea o reutiliza domicilio histórico (sin contribuyente ni rubro).

    Raises:
        ValueError: si faltan calle o número.
    """
    data = validar_domicilio_historico(payload)
    dom = get_or_create_domicilio(
        data,
        contribuyente=None,
        rubro=None,
        allow_missing_catalogs=True,
    )
    if dom is None:
        raise ValueError("No se pudo resolver el domicilio histórico.")
    return dom


def validar_titular_snapshot(snapshot: Dict[str, Optional[str]]) -> None:
    """
    Valida regla de titular histórico.

    Raises:
        ValueError: si titular inválido o ambiguo.
    """
    nombre = snapshot.get("titular_nombre_historico")
    apellido = snapshot.get("titular_apellido_historico")
    razon = snapshot.get("titular_razon_social_historica")
    has_persona = bool(nombre and apellido)
    has_razon = bool(razon)
    if has_persona and has_razon:
        raise ValueError("Ingrese nombre y apellido o razón social, no ambos.")
    if not has_persona and not has_razon:
        raise ValueError("Ingrese nombre y apellido o razón social.")


def crear_actuacion_historica_solo_comprobacion(
    payload: Dict[str, Any],
    *,
    actor_user_id: int | None = None,
) -> Actuaciones:
    """
    Crea actuación histórica mínima con solo comprobación.

    Raises:
        ValueError: reglas de negocio del modo histórico.
    """
    rechazar_oficio_expediente_en_payload_canal_actas(payload)
    rechazar_campos_prohibidos_historicos_en_payload(payload)
    if not payload.get("carga_solo_comprobacion"):
        raise ValueError("Payload histórico requiere carga_solo_comprobacion=true.")

    fecha_str = payload.get("fecha_actuacion")
    mes, anio, fecha = parse_fecha_grid(fecha_str)

    snapshot = titular_snapshot_desde_payload(payload)
    validar_titular_snapshot(snapshot)

    nombres = payload.get("inspectores") or []
    if not nombres:
        raise ValueError("Seleccione al menos un inspector.")

    comprobacion = payload.get("comprobacion") or {}
    if not comprobacion.get("acta_num"):
        raise ValueError("Ingrese el número de acta de comprobación.")
    if not (comprobacion.get("motivo") or "").strip():
        raise ValueError("Seleccione el motivo del acta de comprobación.")

    dom = resolver_domicilio_historico(payload)

    act = Actuaciones(
        fecha=fecha,
        mes=mes,
        anio=anio,
        tipo=None,
        contraproducencia=None,
        carga_solo_comprobacion=True,
        orden_trabajo_id=None,
        domicilio_id=dom.id,
        titular_nombre_historico=snapshot["titular_nombre_historico"],
        titular_apellido_historico=snapshot["titular_apellido_historico"],
        titular_razon_social_historica=snapshot["titular_razon_social_historica"],
    )
    db.session.add(act)
    db.session.flush()

    act.inspector = get_inspectores_o_falla(nombres)
    attach_comprobacion(act, comprobacion)

    db.session.add(act)
    db.session.commit()
    resolve_actor_user_id(actor_user_id)
    return act


def aplicar_payload_historica_solo_comprobacion(
    act: Actuaciones,
    payload: Dict[str, Any],
) -> None:
    """
    Aplica edición permitida sobre actuación histórica existente.

    Raises:
        ValueError: si se intenta cambiar modo o campos prohibidos.
    """
    if not getattr(act, "carga_solo_comprobacion", False):
        raise ValueError("La actuación no es histórica solo comprobación.")

    if "carga_solo_comprobacion" in payload and not payload.get("carga_solo_comprobacion"):
        raise ValueError("No se puede convertir una actuación histórica en normal.")

    rechazar_oficio_expediente_en_payload_canal_actas(payload)
    rechazar_campos_prohibidos_historicos_en_payload(payload)

    if payload.get("fecha_actuacion"):
        mes, anio, fecha = parse_fecha_grid(payload["fecha_actuacion"])
        act.fecha = fecha
        act.mes = mes
        act.anio = anio

    titular_keys = {
        "titular_nombre_historico",
        "titular_apellido_historico",
        "titular_razon_social_historica",
        "contrib_nombre",
        "contrib_apellido",
        "razon_social",
    }
    if titular_keys.intersection(payload.keys()):
        snapshot = titular_snapshot_desde_payload(
            {
                "titular_nombre_historico": payload.get("titular_nombre_historico", act.titular_nombre_historico),
                "titular_apellido_historico": payload.get("titular_apellido_historico", act.titular_apellido_historico),
                "titular_razon_social_historica": payload.get(
                    "titular_razon_social_historica", act.titular_razon_social_historica
                ),
                "contrib_nombre": payload.get("contrib_nombre"),
                "contrib_apellido": payload.get("contrib_apellido"),
                "razon_social": payload.get("razon_social"),
            }
        )
        validar_titular_snapshot(snapshot)
        act.titular_nombre_historico = snapshot["titular_nombre_historico"]
        act.titular_apellido_historico = snapshot["titular_apellido_historico"]
        act.titular_razon_social_historica = snapshot["titular_razon_social_historica"]

    if "inspectores" in payload:
        nombres = payload.get("inspectores") or []
        if not nombres:
            raise ValueError("Seleccione al menos un inspector.")
        act.inspector = get_inspectores_o_falla(nombres)

    if "comprobacion" in payload:
        attach_comprobacion(act, payload.get("comprobacion"))

    if "domicilio" in payload or "calle" in payload or "numero" in payload:
        dom = resolver_domicilio_historico(payload)
        act.domicilio_id = dom.id

    db.session.add(act)
