from __future__ import annotations

from typing import Any, Dict

from flask import current_app

from app.database import db
from app.models import Relevamiento
from app.utils.fechas import parse_fecha_grid
from app.domains.domicilios.services.domicilio_update_service import aplicar_edicion_domicilio_operativo
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.relevamientos.catalogs.relevador import (
    get_relevadores_o_falla,
    resolve_relevador_nombres_o_falla,
)
from app.domains.relevamientos.services.relevamiento_relevadores_service import (
    sync_relevamiento_relevadores,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.domains.grid.services.post_commit_geocode import schedule_geocode_after_grid_commit
from app.domains.actuaciones.cleanup.garbage_collector import (
    soft_delete_domicilio_if_orphan,
)
from app.domains.relevamientos.services.operational_guard_service import (
    get_iniciador_pendiente_relevamiento,
)
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    propagar_domicilio_a_iniciadores_activos,
)
from app.domains.relevamientos.services.relevamiento_domicilio_rubro_guard import (
    rubro_para_edicion_domicilio_relevamiento,
)
from app.domains.relevamientos.services.relevamiento_unicidad_service import (
    assert_sin_relevamiento_activo_duplicado,
)
from app.domains.relevamientos.utils.relevamiento_campos_normalizers import (
    campos_establecimiento_desde_payload,
)


def _get_relevamiento_or_404(relevamiento_id: int) -> Relevamiento:
    rel = (
        Relevamiento.query.filter(
            Relevamiento.id == relevamiento_id,
            Relevamiento.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    if not rel:
        raise ValueError("Relevamiento no encontrado.")
    return rel


def actualizar_relevamiento(relevamiento_id: int, payload: Dict[str, Any]) -> Relevamiento:
    """
    Actualiza un Relevamiento existente en base a un payload canon.

    Args:
        relevamiento_id: id del relevamiento.
        payload: dict canon (sin DB).

    Returns:
        Relevamiento actualizado y commiteado.

    Raises:
        ValueError: si no existe o reglas de negocio.
    """
    rel = _get_relevamiento_or_404(relevamiento_id)
    get_iniciador_pendiente_relevamiento(relevamiento_id)
    old_domicilio_id = rel.domicilio_id

    fecha_raw = payload.get("fecha")
    relevador_ids = payload.get("relevador_ids")
    relevadores_nombres = payload.get("relevadores_nombres") or []
    domicilio = payload.get("domicilio") or {}
    calle = domicilio.get("calle")
    numero = domicilio.get("numero")
    rubro_nombre = payload.get("rubro_nombre")

    if not calle or not numero:
        raise ValueError("Calle y número son obligatorios.")

    if fecha_raw:
        mes, anio, fecha = parse_fecha_grid(fecha_raw)
    else:
        mes, anio, fecha = rel.mes, rel.anio, rel.fecha

    existing_relevador_ids = sorted(r.id for r in rel.relevadores)
    legacy_multi_relevador = len(existing_relevador_ids) > 1
    sync_relevadores = True

    if relevador_ids:
        if len(relevador_ids) != 1:
            raise ValueError("Debe indicar exactamente un relevador.")
        if legacy_multi_relevador:
            if sorted(relevador_ids) != existing_relevador_ids:
                raise ValueError(
                    "Este relevamiento tiene varios relevadores históricos. "
                    "No puede cambiar el relevador hasta una limpieza de datos."
                )
            sync_relevadores = False
            relevadores = list(rel.relevadores)
        else:
            relevadores = get_relevadores_o_falla(relevador_ids)
    elif relevadores_nombres:
        if len(relevadores_nombres) != 1:
            raise ValueError("Debe indicar exactamente un relevador.")
        if legacy_multi_relevador:
            raise ValueError(
                "Este relevamiento tiene varios relevadores históricos. "
                "No puede cambiar el relevador hasta una limpieza de datos."
            )
        relevadores = resolve_relevador_nombres_o_falla(relevadores_nombres)
    elif legacy_multi_relevador:
        sync_relevadores = False
        relevadores = list(rel.relevadores)
    else:
        raise ValueError("Relevador obligatorio.")
    rubro = get_rubro_o_falla(rubro_nombre)
    dom_payload = {"calle": calle, "numero": numero, **{k: v for k, v in domicilio.items() if k not in ("calle", "numero")}}
    numero_tipo_override = dom_payload.get("numero_tipo")
    rubro_domicilio = rubro_para_edicion_domicilio_relevamiento(
        rubro=rubro,
        calle=str(calle),
        numero=str(numero),
        domicilio_id_actual=rel.domicilio_id,
        numero_tipo_hint=numero_tipo_override,
        exclude_relevamiento_id=relevamiento_id,
    )
    outcome = aplicar_edicion_domicilio_operativo(
        domicilio_id_actual=rel.domicilio_id,
        cambios=dom_payload,
        contexto="RELEVAMIENTO",
        origen_id=relevamiento_id,
        modo_explicito=payload.get("modo_domicilio"),
        rubro=rubro_domicilio,
        usar_basico=True,
        relevamiento_id=relevamiento_id,
    )
    dom = outcome.domicilio
    if dom is None:
        raise ValueError("No se pudo resolver domicilio.")
    normalizar_domicilio_en_sesion(dom, override_numero_tipo=numero_tipo_override)

    nombre_fantasia, angulo_esquina = campos_establecimiento_desde_payload(
        payload,
        numero_tipo=getattr(dom, "numero_tipo", None),
    )
    assert_sin_relevamiento_activo_duplicado(
        dom,
        mes=mes,
        anio=anio,
        rubro_id=rubro.id if rubro else None,
        nombre_fantasia=nombre_fantasia,
        angulo_esquina=angulo_esquina,
        exclude_relevamiento_id=relevamiento_id,
    )

    rel.fecha = fecha
    rel.mes = mes
    rel.anio = anio
    rel.domicilio_id = dom.id
    rel.rubro_id = rubro.id if rubro else None
    rel.nombre_fantasia = nombre_fantasia
    rel.angulo_esquina = angulo_esquina

    turno_carga = payload.get("turno_carga")
    if turno_carga is not None and turno_carga not in ("MANIANA", "TARDE"):
        raise ValueError("Turno inválido.")
    rel.turno_carga = turno_carga
    rel.esta_abierto = payload.get("esta_abierto")

    db.session.add(rel)
    if sync_relevadores:
        sync_relevamiento_relevadores(rel, [r.id for r in relevadores])
    if old_domicilio_id != rel.domicilio_id and rel.domicilio_id:
        propagar_domicilio_a_iniciadores_activos(
            "RELEVAMIENTO",
            relevamiento_id,
            int(rel.domicilio_id),
        )
    db.session.commit()

    if old_domicilio_id is not None and old_domicilio_id != rel.domicilio_id:
        soft_delete_domicilio_if_orphan(old_domicilio_id)
        db.session.commit()

    if rel.domicilio_id and (
        outcome.domicilio_id_cambio or outcome.policy.requiere_geocode_refresh
    ):
        try:
            schedule_geocode_after_grid_commit([int(rel.domicilio_id)])
        except Exception:
            current_app.logger.exception(
                "No se pudo encolar geocode post-commit relevamiento_id=%s domicilio_id=%s",
                relevamiento_id,
                rel.domicilio_id,
            )
    return rel
