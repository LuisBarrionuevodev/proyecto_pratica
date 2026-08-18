"""
Bandejas operativas unificadas para actas de comprobación (oficio / reinspección / recorrido).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import String, and_, exists, func, or_
from sqlalchemy.orm import joinedload, selectinload

from app.domains.actuaciones.services.comprobacion_oficio_recorrido_service import (
    iniciador_reinspeccion_por_oficio,
)
from app.domains.actuaciones.services.oficio_editable_service import iniciador_en_ruta_operativa
from app.domains.actuaciones.services.oficio_list_service import list_oficios_by_comprobacion
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    estado_recorrido_label,
    resultado_cumplimiento_recorrido,
)
from app.domains.actuaciones.services.pendientes_service import (
    _apply_distrito_optional,
    _apply_fecha_comprobacion_acta,
)
from app.models import Actuaciones, Comprobacion, Contribuyente, Domicilio, Expediente, IniciadorRuta, Oficio
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters

RECORRIDO_CAP_SIN_BUSQUEDA = 500


def _recorrido_busqueda_especifica_activa(
    *,
    contrib_q: Optional[str] = None,
    calle_q: Optional[str] = None,
    numero_q: Optional[str] = None,
    acta_comprobacion: Optional[str] = None,
    expediente_numero: Optional[str] = None,
    oficio_numero: Optional[str] = None,
    estado_recorrido: Optional[str] = None,
    tipo_final: Optional[str] = None,
) -> bool:
    """True si hay filtro documental/operativo que no debe verse afectado por el cap defensivo."""
    return bool(
        (contrib_q and contrib_q.strip())
        or (calle_q and calle_q.strip())
        or (numero_q and numero_q.strip())
        or (acta_comprobacion and acta_comprobacion.strip())
        or (expediente_numero and expediente_numero.strip())
        or (oficio_numero and oficio_numero.strip())
        or (estado_recorrido and estado_recorrido.strip())
        or (tipo_final and tipo_final.strip())
    )


def _contains_ci(column, term: str):
    """Subcadena case-insensitive (``ILIKE`` / ``lower LIKE``)."""
    t = term.strip().lower()
    return func.lower(column).contains(t)


def _apply_recorrido_busqueda_sql(
    query,
    *,
    contrib_q: Optional[str] = None,
    calle_q: Optional[str] = None,
    numero_q: Optional[str] = None,
    acta_comprobacion: Optional[str] = None,
    expediente_numero: Optional[str] = None,
    oficio_numero: Optional[str] = None,
):
    """
    Filtros documentales de Recorrido en SQL (``EXISTS`` para no duplicar actuaciones).

    Parámetros:
        query: consulta base de ``Actuaciones`` con comprobación.
        contrib_q, calle_q, numero_q, acta_comprobacion, expediente_numero, oficio_numero:
            subcadenas opcionales.

    Retorno:
        Query con restricciones adicionales.

    Errores:
        Ninguno.
    """
    if acta_comprobacion and acta_comprobacion.strip():
        term = acta_comprobacion.strip()
        query = query.filter(
            exists().where(
                and_(
                    Comprobacion.id == Actuaciones.comprobacion_id,
                    Comprobacion.deleted_at.is_(None),
                    _contains_ci(Comprobacion.numero_acta, term),
                )
            )
        )

    if calle_q and calle_q.strip():
        term = calle_q.strip()
        query = query.filter(
            exists().where(
                and_(
                    Domicilio.id == Actuaciones.domicilio_id,
                    Domicilio.deleted_at.is_(None),
                    _contains_ci(Domicilio.calle, term),
                )
            )
        )

    if numero_q and numero_q.strip():
        term = numero_q.strip()
        query = query.filter(
            exists().where(
                and_(
                    Domicilio.id == Actuaciones.domicilio_id,
                    Domicilio.deleted_at.is_(None),
                    _contains_ci(Domicilio.numero, term),
                )
            )
        )

    if contrib_q and contrib_q.strip():
        term = contrib_q.strip()
        query = query.filter(
            exists().where(
                and_(
                    Domicilio.id == Actuaciones.domicilio_id,
                    Domicilio.deleted_at.is_(None),
                    Contribuyente.id == Domicilio.contribuyente_id,
                    or_(
                        _contains_ci(Contribuyente.apellido, term),
                        _contains_ci(Contribuyente.nombre, term),
                        _contains_ci(Contribuyente.razon_social, term),
                    ),
                )
            )
        )

    if oficio_numero and oficio_numero.strip():
        term = oficio_numero.strip()
        term_lower = term.lower()
        term_flat = term_lower.replace("/", "")
        oficio_blob = func.lower(
            func.concat(
                func.coalesce(Oficio.numero_oficio, ""),
                "/",
                func.cast(Oficio.anio, String),
            )
        )
        query = query.filter(
            exists().where(
                and_(
                    Oficio.comprobacion_id == Actuaciones.comprobacion_id,
                    Oficio.deleted_at.is_(None),
                    or_(
                        _contains_ci(Oficio.numero_oficio, term),
                        oficio_blob.contains(term_lower),
                        func.replace(oficio_blob, "/", "").contains(term_flat),
                    ),
                )
            )
        )

    if expediente_numero and expediente_numero.strip():
        term = expediente_numero.strip()
        term_lower = term.lower()
        term_flat = term_lower.replace("/", "")
        exp_blob = func.lower(
            func.concat(
                func.coalesce(Expediente.numero_expediente, ""),
                "/",
                func.coalesce(Expediente.anio, ""),
            )
        )
        exp_digits = func.replace(
            func.replace(func.lower(func.coalesce(Expediente.numero_expediente, "")), "/", ""),
            " ",
            "",
        )
        query = query.filter(
            exists().where(
                and_(
                    Expediente.comprobacion_id == Actuaciones.comprobacion_id,
                    Expediente.deleted_at.is_(None),
                    or_(
                        _contains_ci(Expediente.numero_expediente, term),
                        exp_blob.contains(term_lower),
                        func.replace(exp_blob, "/", "").contains(term_flat),
                        exp_digits.contains("".join(c for c in term_flat if c.isdigit()) or term_flat),
                    ),
                )
            )
        )

    return query

def _query_actuaciones_circuito_reinspeccion(filters: ActuacionesPendientesFilters):
    """Actuaciones con envío + oficio + respuesta (sin filtrar por ruta a nivel actuación)."""
    has_envio = exists().where(
        and_(
            Expediente.comprobacion_id == Actuaciones.comprobacion_id,
            Expediente.oficio_id.is_(None),
            Expediente.deleted_at.is_(None),
        )
    )
    has_oficio = exists().where(
        and_(
            Oficio.comprobacion_id == Actuaciones.comprobacion_id,
            Oficio.deleted_at.is_(None),
        )
    )
    has_respuesta = exists().where(
        and_(
            Expediente.comprobacion_id == Actuaciones.comprobacion_id,
            Expediente.oficio_id.isnot(None),
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            ),
            Expediente.deleted_at.is_(None),
            exists().where(
                and_(
                    Oficio.id == Expediente.oficio_id,
                    Oficio.comprobacion_id == Actuaciones.comprobacion_id,
                    Oficio.deleted_at.is_(None),
                )
            ),
        )
    )
    q = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(has_envio, has_oficio, has_respuesta)
        .options(
            joinedload(Actuaciones.orden_trabajo),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
            selectinload(Actuaciones.inspector),
            joinedload(Actuaciones.inspeccion),
            joinedload(Actuaciones.comprobacion),
        )
    )
    q = _apply_fecha_comprobacion_acta(q, filters)
    distrito_id = getattr(filters, "distrito_id", None)
    q = _apply_distrito_optional(q, distrito_id)
    return q.order_by(Actuaciones.id.desc())


def _iniciador_reinspeccion_por_oficio(oficio_id: int) -> IniciadorRuta | None:
    return iniciador_reinspeccion_por_oficio(oficio_id)


def _iniciador_reinspeccion_legacy_actuacion(actuacion_id: int) -> IniciadorRuta | None:
    """Iniciador REINSPECCION_OFICIO sin ``oficio_id`` (datos legados / tests)."""
    return (
        IniciadorRuta.query.filter_by(actuacion_id=int(actuacion_id))
        .filter(IniciadorRuta.oficio_id.is_(None))
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _iniciador_para_oficio_en_actuacion(oficio: Oficio, act: Actuaciones) -> IniciadorRuta | None:
    ini = _iniciador_reinspeccion_por_oficio(oficio.id)
    if ini is not None:
        return ini
    oficios = list_oficios_by_comprobacion(int(act.comprobacion_id))
    if len(oficios) == 1 and oficios[0].id == oficio.id:
        return _iniciador_reinspeccion_legacy_actuacion(act.id)
    return None


def _expediente_respuesta_por_oficio(oficio_id: int) -> Expediente | None:
    return (
        Expediente.query.filter_by(oficio_id=int(oficio_id))
        .filter(
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            )
        )
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .first()
    )


def _tramite_reinspeccion_oficio_cumplido(ini: IniciadorRuta | None) -> bool:
    """
    True si el trámite de reinspección por oficio ya cerró operativamente.

    Reencolados por contraproducencia quedan en ``PENDIENTE`` y siguen listables.
    """
    if ini is None:
        return False
    if ini.estado_iniciador == "CUMPLIDO":
        return True
    return ini.estado_iniciador in inactive_estados()


def list_pendientes_reinspeccion_oficio_filas(
    filters: ActuacionesPendientesFilters,
) -> List[Tuple[Actuaciones, Oficio, Optional[IniciadorRuta]]]:
    """
    Filas pendientes de reinspección **por oficio/iniciador** (PR4b).

    Una actuación con dos oficios puede generar dos filas si ninguno (o solo uno) está en ruta activa.
    """
    acts = _query_actuaciones_circuito_reinspeccion(filters).all()
    filas: List[Tuple[Actuaciones, Oficio, Optional[IniciadorRuta]]] = []
    for act in acts:
        if act.comprobacion_id is None:
            continue
        for ofi in list_oficios_by_comprobacion(int(act.comprobacion_id)):
            if _expediente_respuesta_por_oficio(ofi.id) is None:
                continue
            ini = _iniciador_para_oficio_en_actuacion(ofi, act)
            if iniciador_en_ruta_operativa(ini):
                continue
            if _tramite_reinspeccion_oficio_cumplido(ini):
                continue
            filas.append((act, ofi, ini))
    return filas


def list_pendientes_reinspeccion_oficio(
    filters: ActuacionesPendientesFilters,
) -> List[Actuaciones]:
    """
    Reinspecciones por oficio **pendientes de planificación en ruta** (F3.6b).

    Documental:

    - Expediente de envío de acta activo (``oficio_id`` NULL, no borrado).
    - Oficio administrativo activo (no borrado).
    - Expediente de respuesta al oficio activo (``oficio_id`` al oficio de la misma comprobación;
      ``tipo_expediente`` ``RESPUESTA_OFICIO`` o ``NULL`` legado).

    Puede existir o no ``IniciadorRuta`` tipo ``REINSPECCION_OFICIO``; eso **no** oculta la fila.

    Fuera de bandeja solo si existe un ``RutaItem`` **incorporado** a planificación operativa:

    - ``IniciadorRuta`` mismo ``actuacion_id``, tipo ``REINSPECCION_OFICIO``, no soft-deleted.
    - ``RutaItem`` no soft-deleted.
    - ``RutaTrabajo.estado_ruta`` en ``PUBLICADA`` | ``EN_CURSO`` (STAB-3: ``BORRADOR`` no oculta).

    Si la ruta está ``BORRADOR`` / ``CERRADA`` / ``CANCELADA``, el ítem está borrado en soft delete, o el iniciador no
    tiene ítem en esa ruta, la actuación **sigue** en bandeja (puede tener o no iniciador materializado).

    Fechas / distrito: ``Actuaciones.fecha`` vía ``_apply_fecha`` / ``_apply_distrito_optional``.

    Compat: devuelve actuaciones únicas presentes en ``list_pendientes_reinspeccion_oficio_filas``.
    """
    seen: set[int] = set()
    out: List[Actuaciones] = []
    for act, _ofi, _ini in list_pendientes_reinspeccion_oficio_filas(filters):
        if act.id not in seen:
            seen.add(act.id)
            out.append(act)
    return out


def list_comprobacion_recorrido(
    filters: ActuacionesPendientesFilters,
    *,
    contrib_q: Optional[str] = None,
    calle_q: Optional[str] = None,
    numero_q: Optional[str] = None,
    acta_comprobacion: Optional[str] = None,
    expediente_numero: Optional[str] = None,
    oficio_numero: Optional[str] = None,
    estado_recorrido: Optional[str] = None,
    tipo_final: Optional[str] = None,
    limit: int = RECORRIDO_CAP_SIN_BUSQUEDA,
) -> List[Actuaciones]:
    """
    Actuaciones con comprobación para vista consultiva de recorrido.

    Filtros documentales (acta, calle, contribuyente, oficio, expediente, etc.) se aplican en SQL
    cuando hay búsqueda específica, **antes** de cualquier cap defensivo.

    ``estado_recorrido`` y ``tipo_final`` requieren lógica de presentación y se aplican en Python
    sobre el universo ya acotado por SQL / período.

    Sin búsqueda específica se mantiene ``limit`` (500 por defecto) sobre ``id DESC``.

    Mes/año explícitos filtran ``Comprobacion.mes/anio``; rango filtra ``Actuaciones.fecha``.
    """
    busqueda_especifica = _recorrido_busqueda_especifica_activa(
        contrib_q=contrib_q,
        calle_q=calle_q,
        numero_q=numero_q,
        acta_comprobacion=acta_comprobacion,
        expediente_numero=expediente_numero,
        oficio_numero=oficio_numero,
        estado_recorrido=estado_recorrido,
        tipo_final=tipo_final,
    )

    q = Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
    q = _apply_fecha_comprobacion_acta(q, filters)
    distrito_id = getattr(filters, "distrito_id", None)
    q = _apply_distrito_optional(q, distrito_id)
    q = _apply_recorrido_busqueda_sql(
        q,
        contrib_q=contrib_q,
        calle_q=calle_q,
        numero_q=numero_q,
        acta_comprobacion=acta_comprobacion,
        expediente_numero=expediente_numero,
        oficio_numero=oficio_numero,
    )

    q = q.order_by(Actuaciones.id.desc())
    if busqueda_especifica:
        rows: List[Actuaciones] = q.all()
    else:
        rows = q.limit(limit).all()

    if not (estado_recorrido and estado_recorrido.strip()) and not (tipo_final and tipo_final.strip()):
        return rows

    def _keep_estado_y_tipo(act: Actuaciones) -> bool:
        if estado_recorrido and estado_recorrido.strip():
            if estado_recorrido_label(act).lower() != estado_recorrido.strip().lower():
                return False
        if tipo_final and tipo_final.strip():
            rc = (resultado_cumplimiento_recorrido(act) or "").strip().upper()
            if rc != tipo_final.strip().upper():
                return False
        return True

    return [a for a in rows if _keep_estado_y_tipo(a)]
