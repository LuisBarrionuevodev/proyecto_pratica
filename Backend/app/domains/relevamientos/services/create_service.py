from __future__ import annotations

from datetime import date
from typing import Any, Dict

from app.database import db
from app.models import Domicilio, Relevamiento
from app.utils.fechas import parse_fecha_grid
from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.domicilios.services.domicilio_update_service import aplicar_edicion_domicilio_operativo
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.domains.relevamientos.services.relevamiento_iniciador_service import (
    get_or_create_iniciador_from_relevamiento,
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


def crear_relevamiento_desde_payload(payload: Dict[str, Any]) -> Relevamiento:
    """
    Crea un Relevamiento desde un payload canon.

    Args:
        payload: dict canon (sin DB) con inspector, domicilio y rubro.
            Si no trae ``fecha``, se usa la fecha actual del servidor (PR9.4).

    Returns:
        Relevamiento creado y commiteado.

    Raises:
        ValueError: si faltan campos obligatorios o reglas de negocio.
    """
    fecha_raw = payload.get("fecha")
    inspector_nombre = payload.get("inspector_nombre")
    domicilio = payload.get("domicilio") or {}
    calle = domicilio.get("calle")
    numero = domicilio.get("numero")
    rubro_nombre = payload.get("rubro_nombre")

    if not fecha_raw:
        fecha_raw = date.today().isoformat()
    if not inspector_nombre:
        raise ValueError("Inspector obligatorio.")
    if not calle or not numero:
        raise ValueError("Calle y número son obligatorios.")
    if not rubro_nombre:
        raise ValueError("Rubro obligatorio.")

    mes, anio, fecha = parse_fecha_grid(fecha_raw)
    inspector = get_inspectores_o_falla([inspector_nombre])[0]
    rubro = get_rubro_o_falla(rubro_nombre)
    dom_payload = {
        "calle": calle,
        "numero": numero,
        **{k: v for k, v in domicilio.items() if k not in ("calle", "numero")},
    }
    numero_tipo_override = dom_payload.get("numero_tipo")
    nombre_fantasia, angulo_esquina = campos_establecimiento_desde_payload(
        payload,
        numero_tipo=numero_tipo_override,
    )
    dom_existente = (
        Domicilio.query.filter_by(calle=str(calle).strip(), numero=str(numero).strip())
        .filter(Domicilio.deleted_at.is_(None))
        .first()
    )
    if dom_existente is not None:
        assert_sin_relevamiento_activo_duplicado(
            dom_existente,
            mes=mes,
            anio=anio,
            rubro_id=rubro.id if rubro else None,
            nombre_fantasia=nombre_fantasia,
            angulo_esquina=angulo_esquina,
        )
    rubro_domicilio = rubro_para_edicion_domicilio_relevamiento(
        rubro=rubro,
        calle=str(calle),
        numero=str(numero),
        domicilio_id_actual=None,
        numero_tipo_hint=numero_tipo_override,
    )
    outcome = aplicar_edicion_domicilio_operativo(
        domicilio_id_actual=None,
        cambios=dom_payload,
        contexto="RELEVAMIENTO",
        origen_id=0,
        rubro=rubro_domicilio,
        usar_basico=True,
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
    )

    turno_carga = payload.get("turno_carga")
    if turno_carga is not None and turno_carga not in ("MANIANA", "TARDE"):
        raise ValueError("Turno inválido.")
    esta_abierto = payload.get("esta_abierto")

    rel = Relevamiento(
        fecha=fecha,
        mes=mes,
        anio=anio,
        inspector_id=inspector.id,
        domicilio_id=dom.id,
        rubro_id=rubro.id if rubro else None,
        nombre_fantasia=nombre_fantasia,
        angulo_esquina=angulo_esquina,
        turno_carga=turno_carga,
        esta_abierto=esta_abierto,
    )
    db.session.add(rel)
    db.session.flush()

    iniciador = get_or_create_iniciador_from_relevamiento(rel)
    db.session.add(iniciador)
    db.session.commit()
    return rel
