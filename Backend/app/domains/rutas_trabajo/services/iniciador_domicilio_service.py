from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import and_, exists

from app.database import db
from app.domains.geolocalizacion.geocode.services.distrito_backfill_service import (
    backfill_distrito_for_domicilio_if_needed,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.models import (
    Actuaciones,
    Comprobacion,
    Denuncia,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Notificacion,
    Oficio,
    Relevamiento,
    RutaItem,
    RutaTrabajo,
)

_GEO_OK_STATUSES = ("OK", "MANUAL", "REVIEW")

_TIPOS_DERIVADOS_CON_ORIGEN = (
    "REINSPECCION_NOTIFICACION",
    "REINSPECCION_OFICIO",
    "RELEVAMIENTO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)

# PR2 — estados que permiten alinear domicilio desde el origen (si no hay ruta publicada/en curso).
_ESTADOS_PROPAGABLES_DOMICILIO: tuple[str, ...] = (
    "PENDIENTE",
    "PLANIFICADO",
    "NO_REALIZADO_REPROGRAMAR",
    "EN_EJECUCION",
)

_ESTADOS_TERMINALES_DOMICILIO: tuple[str, ...] = ("CUMPLIDO",) + inactive_estados()

_RUTA_ESTADOS_BLOQUEAN_PROPAGACION: tuple[str, ...] = ("PUBLICADA", "EN_CURSO", "CERRADA")

DomicilioEfectivoSource = str  # iniciador | relevamiento | actuacion | notificacion | comprobacion | oficio | denuncia | none


@dataclass(frozen=True)
class DomicilioEfectivoResult:
    """
    Domicilio operativo resuelto para lectura (pendientes, rutas, indicadores).

    Attributes:
        domicilio_id: id efectivo o None si no hay fuente resoluble.
        source: fuente elegida (iniciador u origen lógico).
        has_geocode: True si el domicilio efectivo tiene geocode OK/MANUAL/REVIEW con lat/lng.
        has_distrito: True si el domicilio efectivo tiene ``distrito_id``.
        needs_geo: True si hay domicilio pero sin geocode operativo.
        desalineado_con_origen: True si el iniciador tenía domicilio activo distinto al origen.
    """

    domicilio_id: int | None
    source: DomicilioEfectivoSource
    has_geocode: bool = False
    has_distrito: bool = False
    needs_geo: bool = False
    desalineado_con_origen: bool = False


@dataclass(frozen=True)
class PropagacionDomicilioOutcome:
    """
    Resultado de propagar domicilio desde una entidad origen hacia iniciadores vinculados.

    Attributes:
        origen_tipo: RELEVAMIENTO o ACTUACION.
        origen_id: id del registro origen.
        domicilio_id: domicilio operativo aplicado (None si no había domicilio).
        total_vinculados: iniciadores no borrados vinculados al origen.
        actualizados: iniciadores cuyo domicilio_id cambió.
        omitidos_estado_terminal: omitidos por CUMPLIDO/CERRADO/ANULADO/etc.
        omitidos_ruta_publicada: omitidos por ítem en ruta PUBLICADA/EN_CURSO/CERRADA.
        omitidos_ya_alineados: ya tenían el domicilio operativo correcto.
        omitidos_sin_permiso: estado no contemplado en la policy PR2.
        iniciadores_actualizados: ids actualizados en esta corrida.
    """

    origen_tipo: str
    origen_id: int
    domicilio_id: int | None
    total_vinculados: int = 0
    actualizados: int = 0
    omitidos_estado_terminal: int = 0
    omitidos_ruta_publicada: int = 0
    omitidos_ya_alineados: int = 0
    omitidos_sin_permiso: int = 0
    iniciadores_actualizados: list[int] = field(default_factory=list)


def estados_propagables_domicilio() -> tuple[str, ...]:
    """Retorna estados de iniciador que permiten propagación de domicilio (PR2)."""
    return _ESTADOS_PROPAGABLES_DOMICILIO


def estados_terminales_domicilio() -> tuple[str, ...]:
    """Retorna estados históricos/inactivos que no deben mutarse (PR2)."""
    return _ESTADOS_TERMINALES_DOMICILIO


def iniciador_en_ruta_publicada_o_en_curso(iniciador_id: int) -> bool:
    """
    Indica si el iniciador tiene un ítem activo en ruta PUBLICADA, EN_CURSO o CERRADA.

    Regla conservadora PR2: no propagar domicilio si afectaría planificación/ejecución publicada.
    """
    subq = exists().where(
        and_(
            RutaItem.iniciador_ruta_id == iniciador_id,
            RutaItem.deleted_at.is_(None),
            RutaItem.ruta_trabajo.has(RutaTrabajo.estado_ruta.in_(_RUTA_ESTADOS_BLOQUEAN_PROPAGACION)),
        )
    )
    return bool(db.session.query(subq).scalar())


def puede_propagar_domicilio_a_iniciador(iniciador: IniciadorRuta) -> tuple[bool, str]:
    """
    Evalúa si un iniciador puede recibir propagación de domicilio desde su origen.

    Returns:
        (True, "ok") si puede actualizarse; (False, motivo) en caso contrario.
    """
    estado = str(iniciador.estado_iniciador or "")
    if estado in _ESTADOS_TERMINALES_DOMICILIO:
        return False, "estado_terminal"
    if iniciador_en_ruta_publicada_o_en_curso(int(iniciador.id)):
        return False, "ruta_publicada_o_en_curso"
    if estado in _ESTADOS_PROPAGABLES_DOMICILIO:
        return True, "ok"
    return False, "estado_no_propagable"


def domicilio_tiene_geocode_operativo_ok(domicilio_id: int | None) -> bool:
    """
    Indica si el domicilio tiene geocode activo con coordenadas utilizables.

    Args:
        domicilio_id: id del domicilio.

    Returns:
        True si existe fila de geocode no eliminada en estado OK/MANUAL/REVIEW con lat/lng.
    """
    if not domicilio_id:
        return False
    geo = (
        DomicilioGeocode.query.filter(
            DomicilioGeocode.domicilio_id == domicilio_id,
            DomicilioGeocode.deleted_at.is_(None),
        )
        .first()
    )
    if not geo:
        return False
    return (
        geo.geo_status in _GEO_OK_STATUSES
        and geo.lat is not None
        and geo.lng is not None
    )


def resolve_domicilio_operativo_para_iniciador(origen_domicilio_id: int | None) -> int:
    """
    Valida el domicilio del origen y aplica backfill de distrito si corresponde.

    Reglas:
    - Referencia el mismo ``domicilio_id`` (no duplica domicilio ni coordenadas sueltas).
    - No dispara geocodificación ni recalcula dirección si el geocode ya es válido.
    - Si hay geocode OK y ``distrito_id`` es nulo, intenta resolver distrito con lógica existente.

    Args:
        origen_domicilio_id: domicilio de la actuación/relevamiento/origen.

    Returns:
        ``domicilio_id`` operativo a asignar al iniciador.

    Raises:
        ValueError: si el domicilio no existe o está eliminado.
    """
    if origen_domicilio_id is None:
        raise ValueError("El origen no tiene domicilio para el iniciador.")

    domicilio = db.session.get(Domicilio, int(origen_domicilio_id))
    if not domicilio or domicilio.deleted_at is not None:
        raise ValueError("Domicilio no encontrado.")

    backfill_distrito_for_domicilio_if_needed(int(domicilio.id))
    return int(domicilio.id)


def assign_iniciador_domicilio_desde_origen(
    iniciador: IniciadorRuta,
    origen_domicilio_id: int | None,
    *,
    allow_update_existing: bool = False,
) -> int | None:
    """
    Asigna al iniciador el domicilio operativo heredado del origen.

    Args:
        iniciador: fila ``IniciadorRuta`` en sesión.
        origen_domicilio_id: domicilio del registro origen (actuación, relevamiento, etc.).
        allow_update_existing: si True y el iniciador permite propagación PR2, alinea domicilio
            cuando difiere del origen resuelto.

    Returns:
        ``domicilio_id`` asignado, o None si el origen no tenía domicilio.

    Raises:
        ValueError: si el domicilio origen no es válido.
    """
    if origen_domicilio_id is None:
        return None

    resolved = resolve_domicilio_operativo_para_iniciador(origen_domicilio_id)
    if iniciador.domicilio_id is None:
        iniciador.domicilio_id = resolved
    elif allow_update_existing and int(iniciador.domicilio_id) != resolved:
        puede, _motivo = puede_propagar_domicilio_a_iniciador(iniciador)
        if puede:
            iniciador.domicilio_id = resolved
    return resolved


def _buscar_iniciadores_vinculados_origen(origen_tipo: str, origen_id: int) -> list[IniciadorRuta]:
    tipo = (origen_tipo or "").strip().upper()
    q = IniciadorRuta.query.filter(IniciadorRuta.deleted_at.is_(None))
    if tipo == "RELEVAMIENTO":
        return q.filter(IniciadorRuta.relevamiento_id == origen_id).all()
    if tipo == "ACTUACION":
        return q.filter(IniciadorRuta.actuacion_id == origen_id).all()
    raise ValueError(f"origen_tipo no soportado para propagación: {origen_tipo}")


def propagar_domicilio_a_iniciadores_activos(
    origen_tipo: str,
    origen_id: int,
    domicilio_id: int | None,
) -> PropagacionDomicilioOutcome:
    """
    Propaga el domicilio operativo del origen hacia iniciadores vinculados activos.

    Reglas PR2:
    - Actualiza iniciadores en estados propagables sin ruta publicada/en curso/cerrada.
    - No muta CUMPLIDO, CERRADO, ANULADO ni equivalentes terminales.
    - Reutiliza ``resolve_domicilio_operativo_para_iniciador`` (sin duplicar domicilio/geocode).

    Args:
        origen_tipo: ``RELEVAMIENTO`` o ``ACTUACION``.
        origen_id: id del registro origen.
        domicilio_id: nuevo domicilio del origen (None → sin cambios).

    Returns:
        Métricas de la corrida.

    Raises:
        ValueError: si ``domicilio_id`` no es válido cuando se intenta resolver.
    """
    outcome = PropagacionDomicilioOutcome(
        origen_tipo=(origen_tipo or "").strip().upper(),
        origen_id=int(origen_id),
        domicilio_id=domicilio_id,
    )
    if domicilio_id is None:
        return outcome

    resolved = resolve_domicilio_operativo_para_iniciador(int(domicilio_id))
    iniciadores = _buscar_iniciadores_vinculados_origen(outcome.origen_tipo, outcome.origen_id)
    outcome = PropagacionDomicilioOutcome(
        origen_tipo=outcome.origen_tipo,
        origen_id=outcome.origen_id,
        domicilio_id=resolved,
        total_vinculados=len(iniciadores),
    )

    actualizados_ids: list[int] = []
    omit_terminal = 0
    omit_ruta = 0
    omit_alineados = 0
    omit_sin_permiso = 0

    for ini in iniciadores:
        puede, motivo = puede_propagar_domicilio_a_iniciador(ini)
        if not puede:
            if motivo == "estado_terminal":
                omit_terminal += 1
            elif motivo == "ruta_publicada_o_en_curso":
                omit_ruta += 1
            else:
                omit_sin_permiso += 1
            continue
        if ini.domicilio_id is not None and int(ini.domicilio_id) == resolved:
            omit_alineados += 1
            continue
        ini.domicilio_id = resolved
        db.session.add(ini)
        actualizados_ids.append(int(ini.id))

    return PropagacionDomicilioOutcome(
        origen_tipo=outcome.origen_tipo,
        origen_id=outcome.origen_id,
        domicilio_id=resolved,
        total_vinculados=outcome.total_vinculados,
        actualizados=len(actualizados_ids),
        omitidos_estado_terminal=omit_terminal,
        omitidos_ruta_publicada=omit_ruta,
        omitidos_ya_alineados=omit_alineados,
        omitidos_sin_permiso=omit_sin_permiso,
        iniciadores_actualizados=actualizados_ids,
    )


def _domicilio_activo_id(domicilio_id: int | None) -> bool:
    if not domicilio_id:
        return False
    dom = db.session.get(Domicilio, int(domicilio_id))
    return dom is not None and dom.deleted_at is None


def _domicilio_origen_actuacion(ini: IniciadorRuta) -> int | None:
    if not ini.actuacion_id:
        return None
    act = db.session.get(Actuaciones, ini.actuacion_id)
    return int(act.domicilio_id) if act and act.domicilio_id else None


def _domicilio_origen_relevamiento(ini: IniciadorRuta) -> int | None:
    if not ini.relevamiento_id:
        return None
    rel = db.session.get(Relevamiento, ini.relevamiento_id)
    return int(rel.domicilio_id) if rel and rel.domicilio_id else None


def _domicilio_origen_denuncia(ini: IniciadorRuta) -> int | None:
    if not ini.denuncia_id:
        return None
    den = db.session.get(Denuncia, ini.denuncia_id)
    return int(den.domicilio_id) if den and den.domicilio_id and den.deleted_at is None else None


def _domicilio_origen_notificacion(ini: IniciadorRuta) -> int | None:
    act_dom = _domicilio_origen_actuacion(ini)
    if act_dom:
        return act_dom
    if not ini.notificacion_id:
        return None
    act = (
        Actuaciones.query.filter(
            Actuaciones.notificacion_id == ini.notificacion_id,
            Actuaciones.tipo == "INSPECCION",
        )
        .order_by(Actuaciones.id.desc())
        .first()
    )
    return int(act.domicilio_id) if act and act.domicilio_id else None


def _domicilio_origen_comprobacion(ini: IniciadorRuta) -> int | None:
    cid = ini.comprobacion_id
    if not cid and ini.oficio_id:
        ofi = db.session.get(Oficio, ini.oficio_id)
        cid = ofi.comprobacion_id if ofi else None
    if not cid:
        return None
    act = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id == cid)
        .order_by(Actuaciones.id.desc())
        .first()
    )
    return int(act.domicilio_id) if act and act.domicilio_id else None


def resolve_origen_domicilio_id_y_fuente(ini: IniciadorRuta) -> tuple[int | None, DomicilioEfectivoSource]:
    """
    Resuelve domicilio desde el origen lógico del iniciador (sin usar ``iniciador.domicilio_id``).

    Returns:
        Par (domicilio_id, source) o (None, "none").
    """
    tipo = str(ini.tipo_iniciador or "")
    if tipo == "RELEVAMIENTO":
        dom_id = _domicilio_origen_relevamiento(ini)
        return (dom_id, "relevamiento") if dom_id else (None, "none")
    if tipo == "DENUNCIA":
        dom_id = _domicilio_origen_denuncia(ini)
        return (dom_id, "denuncia") if dom_id else (None, "none")
    if tipo == "REINSPECCION_NOTIFICACION":
        dom_id = _domicilio_origen_notificacion(ini)
        return (dom_id, "notificacion") if dom_id else (None, "none")
    if tipo in (
        "REINSPECCION_OFICIO",
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    ):
        dom_id = _domicilio_origen_actuacion(ini) or _domicilio_origen_comprobacion(ini)
        source: DomicilioEfectivoSource = "actuacion" if _domicilio_origen_actuacion(ini) else "oficio"
        return (dom_id, source) if dom_id else (None, "none")
    dom_id = _domicilio_origen_actuacion(ini)
    return (dom_id, "actuacion") if dom_id else (None, "none")


def origen_domicilio_id_para_iniciador(ini: IniciadorRuta) -> int | None:
    """
    Resuelve el domicilio esperado del origen lógico del iniciador (solo lectura).

    Args:
        ini: iniciador operativo.

    Returns:
        ``domicilio_id`` del origen o None si no es resoluble.
    """
    dom_id, _source = resolve_origen_domicilio_id_y_fuente(ini)
    return dom_id


def resolve_domicilio_efectivo_para_iniciador(
    iniciador: IniciadorRuta,
    *,
    apply_backfill: bool = False,
    try_sync: bool = False,
) -> DomicilioEfectivoResult:
    """
    Fuente efectiva unificada (PR5) para lectura operativa de domicilio/geocode/distrito.

    Prioridad:
    1. Si ``iniciador.domicilio_id`` está activo y alineado con origen (o sin origen) → iniciador.
    2. Si iniciador activo pero desalineado y origen activo → origen (recupera snapshot viejo).
    3. Si iniciador inválido/ausente y origen activo → origen.
    4. Sin fuente → ``none``.

    No crea domicilios ni dispara geocodificación. Con ``apply_backfill=True`` puede asignar
    distrito si hay geocode OK. Con ``try_sync=True`` persiste alineación solo si policy PR2 lo permite.

    Args:
        iniciador: fila ``IniciadorRuta``.
        apply_backfill: si True, intenta backfill de distrito en domicilio efectivo.
        try_sync: si True, actualiza ``iniciador.domicilio_id`` cuando puede propagar (PR2).

    Returns:
        ``DomicilioEfectivoResult`` con metadatos operativos.
    """
    ini_dom_id = int(iniciador.domicilio_id) if iniciador.domicilio_id else None
    ini_activo = _domicilio_activo_id(ini_dom_id)
    origen_id, origen_source = resolve_origen_domicilio_id_y_fuente(iniciador)

    effective_id: int | None = None
    source: DomicilioEfectivoSource = "none"
    desalineado = False

    if ini_activo and origen_id and ini_dom_id != int(origen_id):
        desalineado = True
        if _domicilio_activo_id(origen_id):
            effective_id = int(origen_id)
            source = origen_source
        else:
            effective_id = ini_dom_id
            source = "iniciador"
    elif ini_activo:
        effective_id = ini_dom_id
        source = "iniciador"
    elif origen_id and _domicilio_activo_id(origen_id):
        effective_id = int(origen_id)
        source = origen_source

    if effective_id and apply_backfill:
        backfill_distrito_for_domicilio_if_needed(effective_id)

    if try_sync and effective_id:
        puede, _motivo = puede_propagar_domicilio_a_iniciador(iniciador)
        if puede and (iniciador.domicilio_id is None or int(iniciador.domicilio_id) != effective_id):
            iniciador.domicilio_id = effective_id
            db.session.add(iniciador)

    dom = db.session.get(Domicilio, effective_id) if effective_id else None
    has_geo = domicilio_tiene_geocode_operativo_ok(effective_id)
    has_dist = bool(dom and dom.distrito_id is not None)

    return DomicilioEfectivoResult(
        domicilio_id=effective_id,
        source=source,
        has_geocode=has_geo,
        has_distrito=has_dist,
        needs_geo=effective_id is not None and not has_geo,
        desalineado_con_origen=desalineado,
    )


def cargar_domicilio_efectivo_orm(
    iniciador: IniciadorRuta,
    *,
    apply_backfill: bool = False,
    try_sync: bool = False,
):
    """
    Carga el ``Domicilio`` ORM efectivo para presenters (con relaciones ya eager-loaded si existen).

    Returns:
        Tupla (Domicilio | None, DomicilioEfectivoResult).
    """
    efectivo = resolve_domicilio_efectivo_para_iniciador(
        iniciador,
        apply_backfill=apply_backfill,
        try_sync=try_sync,
    )
    if not efectivo.domicilio_id:
        return None, efectivo
    dom = db.session.get(Domicilio, efectivo.domicilio_id)
    return dom, efectivo


def diagnose_propagacion_domicilio_pr2(
    *,
    limit_ejemplos: int = 10,
) -> dict[str, Any]:
    """
    Diagnóstico read-only PR2: desalineaciones corregibles vs bloqueadas por estado/ruta.

    Returns:
        Contadores por origen (relevamiento/actuación) y ejemplos.
    """
    from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados

    activos = (
        IniciadorRuta.query.filter(
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
            IniciadorRuta.tipo_iniciador.in_(_TIPOS_DERIVADOS_CON_ORIGEN),
        )
        .all()
    )

    stats = {
        "relevamiento_desalineados": 0,
        "actuacion_desalineados": 0,
        "corregibles_pr2": 0,
        "no_corregibles_terminal": 0,
        "no_corregibles_ruta_publicada": 0,
        "no_corregibles_otro": 0,
    }
    ejemplos_corregibles: list[dict[str, Any]] = []
    ejemplos_terminal: list[dict[str, Any]] = []
    ejemplos_ruta: list[dict[str, Any]] = []

    for ini in activos:
        origen_id = origen_domicilio_id_para_iniciador(ini)
        if not origen_id or (ini.domicilio_id and int(ini.domicilio_id) == origen_id):
            continue

        origen_key = "relevamiento" if ini.tipo_iniciador == "RELEVAMIENTO" else "actuacion"
        if origen_key == "relevamiento":
            stats["relevamiento_desalineados"] += 1
        else:
            stats["actuacion_desalineados"] += 1

        puede, motivo = puede_propagar_domicilio_a_iniciador(ini)
        payload = {
            "iniciador_id": ini.id,
            "tipo": ini.tipo_iniciador,
            "estado": ini.estado_iniciador,
            "origen": origen_key,
            "domicilio_actual": ini.domicilio_id,
            "domicilio_origen": origen_id,
            "motivo": motivo,
        }
        if puede:
            stats["corregibles_pr2"] += 1
            if len(ejemplos_corregibles) < limit_ejemplos:
                ejemplos_corregibles.append(payload)
        elif motivo == "estado_terminal":
            stats["no_corregibles_terminal"] += 1
            if len(ejemplos_terminal) < limit_ejemplos:
                ejemplos_terminal.append(payload)
        elif motivo == "ruta_publicada_o_en_curso":
            stats["no_corregibles_ruta_publicada"] += 1
            if len(ejemplos_ruta) < limit_ejemplos:
                ejemplos_ruta.append(payload)
        else:
            stats["no_corregibles_otro"] += 1

    stats["ejemplos_corregibles"] = ejemplos_corregibles
    stats["ejemplos_no_corregibles_terminal"] = ejemplos_terminal
    stats["ejemplos_no_corregibles_ruta_publicada"] = ejemplos_ruta
    return stats


def diagnose_iniciador_domicilio_desalineaciones(
    *,
    limit_ejemplos: int = 10,
) -> dict[str, Any]:
    """
    Diagnóstico read-only de iniciadores derivados con domicilio desalineado o recuperable.

    Args:
        limit_ejemplos: máximo de ejemplos por categoría en el resultado.

    Returns:
        Resumen con contadores y ejemplos (sin modificar datos).
    """
    from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados

    activos = (
        IniciadorRuta.query.filter(
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
            IniciadorRuta.tipo_iniciador.in_(_TIPOS_DERIVADOS_CON_ORIGEN),
        )
        .all()
    )

    ejemplos_desalineados: list[dict[str, Any]] = []
    ejemplos_sin_domicilio: list[dict[str, Any]] = []
    ejemplos_distrito: list[dict[str, Any]] = []
    ejemplos_geocode_origen: list[dict[str, Any]] = []
    count_desalineados = 0
    count_sin_domicilio = 0
    count_distrito = 0
    count_geocode_origen = 0

    for ini in activos:
        origen_id = origen_domicilio_id_para_iniciador(ini)
        if origen_id and (not ini.domicilio_id or int(ini.domicilio_id) != origen_id):
            payload = {
                "iniciador_id": ini.id,
                "tipo": ini.tipo_iniciador,
                "estado": ini.estado_iniciador,
                "domicilio_actual": ini.domicilio_id,
                "domicilio_origen": origen_id,
            }
            if not ini.domicilio_id:
                count_sin_domicilio += 1
                if len(ejemplos_sin_domicilio) < limit_ejemplos:
                    ejemplos_sin_domicilio.append(payload)
            else:
                count_desalineados += 1
                if len(ejemplos_desalineados) < limit_ejemplos:
                    ejemplos_desalineados.append(payload)
            continue

        dom = db.session.get(Domicilio, ini.domicilio_id) if ini.domicilio_id else None
        if dom and dom.distrito_id is None and domicilio_tiene_geocode_operativo_ok(ini.domicilio_id):
            count_distrito += 1
            if len(ejemplos_distrito) < limit_ejemplos:
                ejemplos_distrito.append(
                    {
                        "iniciador_id": ini.id,
                        "tipo": ini.tipo_iniciador,
                        "domicilio_id": ini.domicilio_id,
                    }
                )
        if (
            origen_id
            and not domicilio_tiene_geocode_operativo_ok(ini.domicilio_id)
            and domicilio_tiene_geocode_operativo_ok(origen_id)
        ):
            count_geocode_origen += 1
            if len(ejemplos_geocode_origen) < limit_ejemplos:
                ejemplos_geocode_origen.append(
                    {
                        "iniciador_id": ini.id,
                        "tipo": ini.tipo_iniciador,
                        "domicilio_actual": ini.domicilio_id,
                        "domicilio_origen": origen_id,
                    }
                )

    return {
        "total_activos_derivados": len(activos),
        "desalineados_con_origen": count_desalineados,
        "sin_domicilio_recuperable_desde_origen": count_sin_domicilio,
        "distrito_recuperable_desde_geocode": count_distrito,
        "geocode_recuperable_desde_origen": count_geocode_origen,
        "ejemplos_desalineados": ejemplos_desalineados,
        "ejemplos_sin_domicilio_recuperable": ejemplos_sin_domicilio,
        "ejemplos_distrito_recuperable": ejemplos_distrito,
        "ejemplos_geocode_recuperable_origen": ejemplos_geocode_origen,
    }


def diagnose_domicilio_efectivo_pr5(
    *,
    limit_ejemplos: int = 10,
) -> dict[str, Any]:
    """
    Diagnóstico read-only PR5: fuente efectiva vs snapshot iniciador.

    Returns:
        Tabla agregada por tipo y ejemplos con source_efectiva / distrito / geocode.
    """
    from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados

    activos = (
        IniciadorRuta.query.filter(
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
            IniciadorRuta.tipo_iniciador.in_(_TIPOS_DERIVADOS_CON_ORIGEN + ("DENUNCIA",)),
        )
        .all()
    )

    stats_by_tipo: dict[str, dict[str, int]] = {}
    ejemplos: list[dict[str, Any]] = []

    for ini in activos:
        tipo = str(ini.tipo_iniciador)
        if tipo not in stats_by_tipo:
            stats_by_tipo[tipo] = {
                "total": 0,
                "source_iniciador": 0,
                "source_origen": 0,
                "sin_resolver": 0,
                "recuperables": 0,
                "bloqueados_sync": 0,
            }
        st = stats_by_tipo[tipo]
        st["total"] += 1

        efectivo = resolve_domicilio_efectivo_para_iniciador(ini, apply_backfill=False, try_sync=False)
        origen_id = origen_domicilio_id_para_iniciador(ini)

        if efectivo.domicilio_id is None:
            st["sin_resolver"] += 1
        elif efectivo.source == "iniciador":
            st["source_iniciador"] += 1
        else:
            st["source_origen"] += 1
            if efectivo.desalineado_con_origen or (
                ini.domicilio_id and int(ini.domicilio_id) != efectivo.domicilio_id
            ):
                st["recuperables"] += 1

        puede_sync, motivo = puede_propagar_domicilio_a_iniciador(ini)
        if efectivo.desalineado_con_origen and not puede_sync:
            st["bloqueados_sync"] += 1

        if len(ejemplos) < limit_ejemplos and (
            efectivo.domicilio_id is None
            or efectivo.source != "iniciador"
            or efectivo.desalineado_con_origen
        ):
            ejemplos.append(
                {
                    "iniciador_id": ini.id,
                    "tipo": tipo,
                    "estado": ini.estado_iniciador,
                    "domicilio_ini": ini.domicilio_id,
                    "domicilio_origen": origen_id,
                    "domicilio_efectivo": efectivo.domicilio_id,
                    "source_efectiva": efectivo.source,
                    "distrito_efectivo": efectivo.has_distrito,
                    "geocode_efectivo": efectivo.has_geocode,
                    "sync_bloqueado": not puede_sync,
                    "sync_motivo": motivo if not puede_sync else None,
                }
            )

    return {
        "stats_by_tipo": stats_by_tipo,
        "ejemplos": ejemplos,
        "total_activos": len(activos),
    }
