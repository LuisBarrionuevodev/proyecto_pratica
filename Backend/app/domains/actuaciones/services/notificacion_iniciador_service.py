from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
import logging
import os

from flask_jwt_extended import get_jwt_identity
from sqlalchemy import and_, exists, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from app.database import db
from app.models import Actuaciones, Domicilio, IniciadorRuta, Notificacion, RutaItem, User
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_operativo_para_iniciador,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import (
    inactive_estados,
    priority_for_tipo,
)

logger = logging.getLogger(__name__)

# --- PR3 política de negocio (actuación mixta notificación + comprobación) ---
# Gestión y expediente operan por canal en paralelo (PR1/PR2). La materialización de
# REINSPECCION_NOTIFICACION por notificación vencida **no** se suprime por tener
# `comprobacion_id` en la misma INSPECCION: el plazo de la notificación sigue siendo un
# compromiso operativo independiente. Idempotencia: una fila bloqueante por `notificacion_id`
# (índice único + prefiltro en sync). Iniciadores de otros tipos/canales (p. ej. oficio) no
# compiten con esa clave.


@dataclass(frozen=True)
class SyncReinspeccionNotificacionOutcome:
    """
    Métricas operativas de una corrida de sync (Fase C: trazabilidad).
    No modifica reglas de negocio ni idempotencia (Fases A/B).

    revoked:
        Iniciadores `REINSPECCION_NOTIFICACION` en `PENDIENTE` anulados en esta corrida
        porque la notificación dejó de estar vencida operativa (reconciliación).
    """

    created: int
    eligible_notificaciones: int
    skipped_already_blocking: int
    collisions_idempotent: int
    revoked: int = 0


def materializacion_notificacion_vencida_on_read_enabled() -> bool:
    """
    Compatibilidad transitoria (Fase C): si es True, algunos GET pueden disparar sync.

    Desaconsejado en producción; usar CLI / scheduler. Variable: `SYNC_NOTIFICACIONES_VENCIDAS_ON_READ`.
    """
    return os.environ.get("SYNC_NOTIFICACIONES_VENCIDAS_ON_READ", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def estado_bloquea_nueva_materializacion_reinspeccion_notificacion(estado_iniciador: str | None) -> bool:
    """
    Indica si un iniciador `REINSPECCION_NOTIFICACION` en ese estado impide crear otro
    para la misma notificación (idempotencia en aplicación).

    Política (Fase A, alineada a `inactive_estados()`):
    - **No bloquean** (se puede materializar de nuevo si el flujo lo permite): `ANULADO`,
      `CERRADO`, `CERRADO_NO_EXISTE_LOCAL`.
    - **Bloquean** (no se crea duplicado mientras exista uno así): `PENDIENTE`, `PLANIFICADO`,
      `EN_EJECUCION`, `CUMPLIDO`, `NO_REALIZADO_REPROGRAMAR`.

    Si `estado_iniciador` es None, se considera que no bloquea (no hay fila).
    """
    if estado_iniciador is None:
        return False
    return estado_iniciador not in inactive_estados()


def elegir_actuacion_base_inspeccion_para_notificacion(
    candidates: list[Actuaciones],
) -> Actuaciones | None:
    """
    Elige la actuación base INSPECCION para materializar el iniciador por notificación vencida.

    Regla explícita (Fase A): si hay varias actuaciones INSPECCION elegibles para la misma
    notificación, se usa **la de mayor `id`** (la más reciente en inserción).
    """
    if not candidates:
        return None
    return max(candidates, key=lambda a: a.id)


def _agrupar_eligible_por_notificacion_id(
    actuaciones: list[Actuaciones],
) -> dict[int, Actuaciones]:
    """
    Agrupa actuaciones elegibles por `notificacion_id` y aplica `elegir_actuacion_base_inspeccion_para_notificacion`
    en cada grupo (un solo acto base por notificación).
    """
    by_nid: dict[int, list[Actuaciones]] = defaultdict(list)
    for act in actuaciones:
        if act.notificacion_id is None:
            continue
        by_nid[int(act.notificacion_id)].append(act)
    return {
        nid: elegir_actuacion_base_inspeccion_para_notificacion(acts)
        for nid, acts in by_nid.items()
    }


def _get_current_user_id() -> int:
    """
    Resuelve user_id autenticado para auditoría.

    Compatibilidad:
    - Si no hay contexto JWT (ruta legacy), usa un usuario activo como fallback.
    """
    try:
        identity = get_jwt_identity()
    except Exception:
        identity = None

    user_id = identity.get("user_id") if isinstance(identity, dict) else identity
    if user_id is not None:
        try:
            parsed_id = int(user_id)
        except (TypeError, ValueError):
            parsed_id = None
        if parsed_id is not None:
            user = User.query.get(parsed_id)
            if user and getattr(user, "is_active", True):
                return parsed_id

    fallback_user = User.query.filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
    if fallback_user:
        return int(fallback_user.id)
    raise ValueError("No hay usuario activo para registrar created_by_user_id")


def _subq_reinsp_misma_notificacion():
    """Existe actuación REINSPECCION con el mismo ``notificacion_id`` que la fila base."""
    A2 = aliased(Actuaciones)
    return exists().where(
        and_(
            A2.notificacion_id == Actuaciones.notificacion_id,
            A2.tipo == "REINSPECCION",
        )
    )


def _subq_reinsp_via_ruta_item_iniciador():
    """
    Existe RutaItem activo del iniciador con actuación de trabajo tipo REINSPECCION,
    aunque esa actuación tenga ``notificacion_id`` NULL (reinspección huérfana en datos).
    """
    A_rein = aliased(Actuaciones)
    return exists().where(
        and_(
            RutaItem.iniciador_ruta_id == IniciadorRuta.id,
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.actuacion_id == A_rein.id,
            A_rein.tipo == "REINSPECCION",
        )
    )


def _subq_reinsp_via_ruta_item_misma_notificacion():
    """
    Para elegibilidad de sync: existe iniciador REINSPECCION_NOTIFICACION de la misma
    notificación con ítem de ruta apuntando a actuación REINSPECCION.
    """
    A_rein = aliased(Actuaciones)
    Ini = aliased(IniciadorRuta)
    return exists().where(
        and_(
            Ini.notificacion_id == Actuaciones.notificacion_id,
            Ini.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            Ini.deleted_at.is_(None),
            RutaItem.iniciador_ruta_id == Ini.id,
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.actuacion_id == A_rein.id,
            A_rein.tipo == "REINSPECCION",
        )
    )


def _eligible_inspecciones_vencidas() -> list[Actuaciones]:
    """
    Retorna actuaciones base INSPECCION elegibles para crear iniciador por
    vencimiento de notificación.

    Puede haber **varias filas** por el mismo `notificacion_id`; la elección de una sola
    actuación base por notificación se hace en `_agrupar_eligible_por_notificacion_id`
    (mayor `id`).

    Elegibilidad:
    - notificación no borrada.
    - fecha_vencimiento no nula y <= hoy.
    - actuación base de tipo INSPECCION.
    - domicilio operativo (domicilio_id no nulo y domicilio no soft-deleteado).
    - sin reinspección ya registrada para la misma notificación.

    **Actuación mixta** (misma fila con ``notificacion_id`` y ``comprobacion_id``): sigue siendo
    elegible si cumple lo anterior (canal notificación en paralelo al de comprobación; PR3).
    """
    today = date.today()
    subq_reinsp = _subq_reinsp_misma_notificacion()
    subq_reinsp_via_ruta = _subq_reinsp_via_ruta_item_misma_notificacion()
    return (
        Actuaciones.query.join(Notificacion, Notificacion.id == Actuaciones.notificacion_id)
        .join(Domicilio, Domicilio.id == Actuaciones.domicilio_id)
        .filter(Actuaciones.tipo == "INSPECCION")
        .filter(Actuaciones.notificacion_id.isnot(None))
        .filter(Actuaciones.domicilio_id.isnot(None))
        .filter(Domicilio.deleted_at.is_(None))
        .filter(Notificacion.deleted_at.is_(None))
        .filter(Notificacion.fecha_vencimiento.isnot(None))
        .filter(Notificacion.fecha_vencimiento <= today)
        .filter(~subq_reinsp)
        .filter(~subq_reinsp_via_ruta)
        .all()
    )


def _exists_iniciador_reinspeccion_notificacion_que_bloquea_nueva_materializacion(
    notificacion_id: int,
) -> bool:
    """
    True si ya hay un iniciador `REINSPECCION_NOTIFICACION` no borrado cuyo estado
    **bloquea** una nueva materialización (ver `estado_bloquea_nueva_materializacion_reinspeccion_notificacion`).

    Implementación: equivalente a filtrar `estado_iniciador NOT IN` estados inactivos.
    """
    iniciador = (
        IniciadorRuta.query.filter(
            IniciadorRuta.notificacion_id == notificacion_id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )
    return iniciador is not None


_REVOKE_OBSERVACIONES_SUFFIX = (
    "[sync notif vencidas] Anulado por reconciliación: la notificación asociada ya no "
    "está vencida operativa (p. ej. prórroga), fue borrada, no tiene fecha de vencimiento "
    "o no existe."
)
_REVOKE_CERRADO_MOTIVO = "SYNC_REINSPECCION_NOTIF_REVOCADA"


def _revoke_obsolete_reinspeccion_notificacion_iniciadores(today: date) -> int:
    """
    Anula iniciadores `REINSPECCION_NOTIFICACION` en `PENDIENTE` que ya no deben estar en
    cola operativa por notificación vencida.

    Solo filas con `notificacion_id` no nulo, sin `RutaItem` activo (`deleted_at` nulo),
    `deleted_at` nulo en el iniciador, y cuya notificación: no existe (join), está borrada,
    tiene `fecha_vencimiento` nula o tiene `fecha_vencimiento` posterior a `today`.

    No borra físicamente: pasa a `ANULADO` y deja trazabilidad en `observaciones` /
    `cerrado_motivo` / `cerrado_at`.

    Args:
        today: Fecha de corte para considerar vencida operativa (`fecha_vencimiento <= today`).

    Returns:
        Cantidad de iniciadores actualizados en esta corrida.
    """
    tiene_item_activo = exists().where(
        and_(
            RutaItem.iniciador_ruta_id == IniciadorRuta.id,
            RutaItem.deleted_at.is_(None),
        )
    )
    candidatos = (
        IniciadorRuta.query.outerjoin(Notificacion, Notificacion.id == IniciadorRuta.notificacion_id)
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
        .filter(IniciadorRuta.estado_iniciador == "PENDIENTE")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .filter(IniciadorRuta.notificacion_id.isnot(None))
        .filter(~tiene_item_activo)
        .filter(
            or_(
                Notificacion.id.is_(None),
                Notificacion.deleted_at.isnot(None),
                Notificacion.fecha_vencimiento.is_(None),
                Notificacion.fecha_vencimiento > today,
            )
        )
        .all()
    )
    if not candidatos:
        return 0

    now = datetime.utcnow()
    n = 0
    for ini in candidatos:
        ini.estado_iniciador = "ANULADO"
        ini.cerrado_at = ini.cerrado_at or now
        ini.cerrado_motivo = ini.cerrado_motivo or _REVOKE_CERRADO_MOTIVO
        prev = (ini.observaciones or "").strip()
        suffix = _REVOKE_OBSERVACIONES_SUFFIX
        ini.observaciones = f"{prev} | {suffix}" if prev else suffix
        db.session.add(ini)
        n += 1
    return n


def sync_iniciadores_reinspeccion_notificacion() -> SyncReinspeccionNotificacionOutcome:
    """
    Materializa iniciadores derivados para notificaciones vencidas y reconcilia obsoletos.

    Al inicio de cada corrida se anulan iniciadores `REINSPECCION_NOTIFICACION` en `PENDIENTE`
    sin ítem de ruta activo cuya notificación ya no está vencida operativa (ver
    `_revoke_obsolete_reinspeccion_notificacion_iniciadores`), para que un nuevo iniciador
    pueda crearse si corresponde.

    **Ejecución (Fase C):** camino canónico = CLI / `flask sync-notificaciones-vencidas` / pipeline
    `sync_notificaciones_vencidas` (scheduler externo). No depender de GETs de lectura.

    Idempotencia (aplicación + BD Fase B):
    - Una sola actuación base por `notificacion_id`: la INSPECCION elegible con **mayor `id`**.
    - Si ya existe iniciador `REINSPECCION_NOTIFICACION` en estado bloqueante para esa notificación,
      no se duplica (prefiltro).
    - Índice único funcional `uq_iniciador_ruta_reinsp_notif_vencida_key` (migración): a lo sumo un iniciador
      bloqueante por notificación; carreras concurrentes → `IntegrityError` manejada como skip idempotente.

    **Caso mixto** (notificación + comprobación en la misma actuación): no se suprime la creación;
    convive con otros ``tipo_iniciador`` que usen otras claves (p. ej. comprobación/oficio).

    Returns:
        Métricas de la corrida (`SyncReinspeccionNotificacionOutcome`).
    """
    eligible = _eligible_inspecciones_vencidas()
    actuacion_por_noti = _agrupar_eligible_por_notificacion_id(eligible)

    eligible_n = len(actuacion_por_noti)
    today = date.today()
    revoked = _revoke_obsolete_reinspeccion_notificacion_iniciadores(today)
    logger.info(
        "sync_reinspeccion_notificacion_inicio eligible_notificaciones=%s revoked=%s",
        eligible_n,
        revoked,
    )

    created = 0
    skipped_already_blocking = 0
    collisions_idempotent = 0
    processed_notificacion_ids: set[int] = set()
    user_id = _get_current_user_id()

    for notificacion_id in sorted(actuacion_por_noti.keys()):
        act = actuacion_por_noti[notificacion_id]
        noti = act.notificacion
        if not noti or not noti.fecha_vencimiento:
            continue
        if noti.deleted_at is not None:
            continue
        if noti.fecha_vencimiento > today:
            continue
        if not act.domicilio_id:
            continue
        if notificacion_id in processed_notificacion_ids:
            continue
        if _exists_iniciador_reinspeccion_notificacion_que_bloquea_nueva_materializacion(
            notificacion_id
        ):
            skipped_already_blocking += 1
            processed_notificacion_ids.add(notificacion_id)
            continue

        obs_base = (
            f"Derivado automático por vencimiento de notificación "
            f"{noti.numero_acta}/{noti.anio}"
        )
        if getattr(act, "comprobacion_id", None) is not None:
            obs_base += (
                " | Misma actuación con acta de comprobación; canal notificación en paralelo (PR3)."
            )

        domicilio_operativo_id = resolve_domicilio_operativo_para_iniciador(int(act.domicilio_id))

        iniciador = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            fecha_origen=noti.fecha_vencimiento,
            anio=int(noti.fecha_vencimiento.year),
            mes=int(noti.fecha_vencimiento.month),
            domicilio_id=domicilio_operativo_id,
            prioridad=priority_for_tipo("REINSPECCION_NOTIFICACION"),
            notificacion_id=notificacion_id,
            actuacion_id=act.id,
            created_by_user_id=user_id,
            observaciones=obs_base,
        )
        try:
            with db.session.begin_nested():
                db.session.add(iniciador)
                db.session.flush()
        except IntegrityError as exc:
            # Único en BD (índice uq_iniciador_ruta_reinsp_notif_vencida_key): carrera / doble sync / retry.
            collisions_idempotent += 1
            logger.debug(
                "sync_reinspeccion_notificacion_colision_idempotente notificacion_id=%s: %s",
                notificacion_id,
                exc,
            )
            processed_notificacion_ids.add(notificacion_id)
            continue
        processed_notificacion_ids.add(notificacion_id)
        created += 1

    if created > 0 or revoked > 0:
        db.session.commit()

    outcome = SyncReinspeccionNotificacionOutcome(
        created=created,
        eligible_notificaciones=eligible_n,
        skipped_already_blocking=skipped_already_blocking,
        collisions_idempotent=collisions_idempotent,
        revoked=revoked,
    )
    logger.info(
        "sync_reinspeccion_notificacion_fin created=%s eligible=%s skipped_blocking=%s "
        "collisions=%s revoked=%s",
        outcome.created,
        outcome.eligible_notificaciones,
        outcome.skipped_already_blocking,
        outcome.collisions_idempotent,
        outcome.revoked,
    )
    return outcome


def list_reinspeccion_notificacion_operativas() -> list[Actuaciones]:
    """
    Lista actuaciones base INSPECCION con iniciador `REINSPECCION_NOTIFICACION` en `PENDIENTE`.

    Defensa en profundidad (lectura): misma noción de **vencida operativa** que el sync /
    `_eligible_inspecciones_vencidas` para la notificación: no borrada, `fecha_vencimiento`
    no nula y ``<=`` fecha de consulta. Así una prórroga que mueve el vencimiento al futuro
    deja de listarse aunque el sync aún no haya corrido.

    Incluye actuaciones **mixtas** (con ``comprobacion_id``) si el iniciador materializado apunta a
    esa actuación (alineado con PR1/PR3).
    """
    today = date.today()
    subq_reinsp = _subq_reinsp_misma_notificacion()
    subq_item_realizado = exists().where(
        and_(
            RutaItem.iniciador_ruta_id == IniciadorRuta.id,
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
        )
    )
    subq_reinsp_via_item = _subq_reinsp_via_ruta_item_iniciador()
    return (
        Actuaciones.query.join(IniciadorRuta, IniciadorRuta.actuacion_id == Actuaciones.id)
        .join(Notificacion, Notificacion.id == Actuaciones.notificacion_id)
        .filter(Actuaciones.tipo == "INSPECCION")
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
        .filter(IniciadorRuta.estado_iniciador == "PENDIENTE")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .filter(Notificacion.deleted_at.is_(None))
        .filter(Notificacion.fecha_vencimiento.isnot(None))
        .filter(Notificacion.fecha_vencimiento <= today)
        .filter(~subq_reinsp)
        .filter(~subq_item_realizado)
        .filter(~subq_reinsp_via_item)
        .order_by(Actuaciones.id.desc())
        .all()
    )
