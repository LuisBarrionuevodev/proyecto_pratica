"""Reserva atómica y GET_LOCK de documento normalizado (Cargar, Completar, PUT, A2)."""

from __future__ import annotations

import logging

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import db
from app.domains.actuaciones.attach.documento_identidad_errors import (
    DOCUMENTO_MAX_LEN,
    MSG_DOCUMENTO_AMBIGUO,
    MSG_DOCUMENTO_INVALIDO,
    MSG_DOCUMENTO_LARGO,
    DocumentoIdentidadError,
)
from app.domains.establecimientos.services.historial_contribuyente_service import (
    contribuyente_ids_por_documento,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
)
from app.domains.establecimientos.utils.documento_normalizer import normalizar_documento
from app.models import Contribuyente, ContribuyenteDocumentoUnico

logger = logging.getLogger(__name__)

MSG_DOC_AJENO = (
    "El documento propuesto ya pertenece a otro contribuyente. "
    "No se fusionan registros ni se reasigna el titular."
)
MSG_DOC_EN_USO = (
    "Otro usuario está corrigiendo el mismo documento. "
    "Volvé a consultar el alcance antes de confirmar."
)

_SESSION_INFO_KEY = "contribuyente_doc_locks"
_SESSION_DBAPI_KEY = "contribuyente_doc_lock_dbapi"
_SESSION_EVENTS_REGISTERED = False


def lock_key_documento(documento_normalizado: str) -> str:
    """Nombre de GET_LOCK acotado a 64 caracteres (compartido por todos los canales)."""
    return f"corr_doc:{documento_normalizado}"[:64]


def _dbapi_from_sqla_connection(conn) -> object:
    """DBAPI (pymysql) de una Connection SQLAlchemy."""
    inner = getattr(conn, "connection", conn)
    return getattr(inner, "dbapi_connection", inner)


def _pin_session_dbapi(session: Session | None = None) -> object:
    """Fija la conexión MySQL de esta sesión para GET_LOCK/RELEASE_LOCK."""
    sess = session if session is not None else db.session
    stored = sess.info.get(_SESSION_DBAPI_KEY)
    if stored is not None:
        return stored
    dbapi = _dbapi_from_sqla_connection(sess.connection())
    sess.info[_SESSION_DBAPI_KEY] = dbapi
    return dbapi


def _cursor_scalar(dbapi, sql: str, params: tuple) -> object:
    """Ejecuta un SELECT de un valor sobre el DBAPI crudo (misma conexión MySQL)."""
    cur = dbapi.cursor()
    try:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        cur.close()


def _track_lock_key(key: str) -> None:
    """Marca el lock en session.info (no en el pool: un reset transaccional no debe soltarlo)."""
    held = db.session.info.setdefault(_SESSION_INFO_KEY, [])
    if key not in held:
        held.append(key)


def adquirir_lock_documento(documento_normalizado: str) -> str:
    """
    Serializa altas y correcciones del mismo documento normalizado (MySQL GET_LOCK).

    El lock queda en la conexión MySQL hasta ``liberar_lock_documento`` o hasta
    after_commit / after_rollback. No es reentrante: si esta sesión ya lo tiene,
    no vuelve a pedir GET_LOCK.

    Parámetros:
        documento_normalizado: CUIT/DNI sin separadores.

    Retorno:
        Clave a pasar a ``liberar_lock_documento``.

    Errores:
        CorreccionEstablecimientoConflictError si el lock no se obtiene a tiempo.
    """
    key = lock_key_documento(documento_normalizado)
    held = db.session.info.get(_SESSION_INFO_KEY) or []
    if key in held:
        return key
    dbapi = _pin_session_dbapi()
    # Misma Connection SQLAlchemy que el INSERT posterior (no un cursor suelto).
    got = db.session.connection().exec_driver_sql(
        "SELECT GET_LOCK(%s, %s)", (key, 10)
    ).scalar()
    if int(got or 0) != 1:
        raise CorreccionEstablecimientoConflictError(MSG_DOC_EN_USO, codigo="DOCUMENTO_EN_USO")
    _track_lock_key(key)
    return key


def liberar_lock_documento(key: str | None) -> None:
    """
    Libera GET_LOCK de la conexión MySQL de esta sesión.

    Qué hace: RELEASE_LOCK + quita el tracking. No relanza errores de liberación.
    Parámetros: clave devuelta por ``adquirir_lock_documento``.
    Retorno: None.
    """
    if not key:
        return
    held = db.session.info.get(_SESSION_INFO_KEY) or []
    if key in held:
        held.remove(key)
    try:
        dbapi = _pin_session_dbapi()
        _cursor_scalar(dbapi, "SELECT RELEASE_LOCK(%s)", (key,))
    except Exception:
        logger.warning("no se pudo liberar GET_LOCK de documento", extra={"key": key})


def _release_tracked_locks(session: Session) -> None:
    """RELEASE_LOCK de todas las claves trackeadas, sobre el DBAPI fijado al adquirir."""
    keys = list(session.info.pop(_SESSION_INFO_KEY, []) or [])
    dbapi = session.info.pop(_SESSION_DBAPI_KEY, None)
    if not keys:
        return
    if dbapi is None:
        try:
            dbapi = _dbapi_from_sqla_connection(session.connection())
        except Exception:
            logger.warning(
                "no hay conexión para liberar GET_LOCK de documento", extra={"keys": keys}
            )
            return
    for key in keys:
        try:
            _cursor_scalar(dbapi, "SELECT RELEASE_LOCK(%s)", (key,))
        except Exception:
            logger.warning("no se pudo liberar GET_LOCK de documento", extra={"key": key})


def _on_session_after_commit(session: Session) -> None:
    """Libera GET_LOCK después de que la transacción confirmó."""
    _release_tracked_locks(session)


def _on_session_after_rollback(session: Session) -> None:
    """Libera GET_LOCK después de revertir (incluye teardown de request)."""
    _release_tracked_locks(session)


def register_documento_lock_session_events(app) -> None:
    """
    Enlaza after_commit / after_rollback al ciclo de GET_LOCK.

    No se usa PoolEvents.reset: en SQLAlchemy 2 ese evento también dispara en
    resets transaccionales y soltaría el lock antes del commit del llamador.

    Qué hace: se registra una sola vez por proceso.
    Parámetros: app Flask (no se usa el engine).
    Retorno: None.
    """
    global _SESSION_EVENTS_REGISTERED
    if _SESSION_EVENTS_REGISTERED:
        return
    event.listen(Session, "after_commit", _on_session_after_commit)
    event.listen(Session, "after_rollback", _on_session_after_rollback)
    _SESSION_EVENTS_REGISTERED = True


def assert_documento_almacenable(documento: str) -> str:
    """
    Valida que el valor que se persistiría cabe en ``contribuyente.documento``.

    No trunca. Acepta separadores solo si el string completo (tras strip) tiene
    como máximo 11 caracteres y el normalizado no queda vacío ni más largo.

    Parámetros:
        documento: valor ya con strip.

    Retorno:
        Documento normalizado (sin `.` `-` espacios).

    Errores:
        DocumentoIdentidadError 400 si es inválido o no cabe.
    """
    raw = (documento or "").strip()
    if not raw:
        raise DocumentoIdentidadError(
            MSG_DOCUMENTO_INVALIDO, codigo="DOCUMENTO_INVALIDO", http_status=400
        )
    if len(raw) > DOCUMENTO_MAX_LEN:
        raise DocumentoIdentidadError(
            MSG_DOCUMENTO_LARGO, codigo="DOCUMENTO_INVALIDO", http_status=400
        )
    norm = normalizar_documento(raw)
    if not norm:
        raise DocumentoIdentidadError(
            MSG_DOCUMENTO_INVALIDO, codigo="DOCUMENTO_INVALIDO", http_status=400
        )
    if len(norm) > DOCUMENTO_MAX_LEN:
        raise DocumentoIdentidadError(
            MSG_DOCUMENTO_LARGO, codigo="DOCUMENTO_INVALIDO", http_status=400
        )
    return norm


def adquirir_lock_para_resolve(documento_normalizado: str) -> str:
    """
    GET_LOCK para Cargar/Completar/PUT; traduce timeout a DocumentoIdentidadError.

    Parámetros:
        documento_normalizado: CUIT/DNI sin separadores.

    Retorno:
        Clave de lock.

    Errores:
        DocumentoIdentidadError DOCUMENTO_EN_USO (409) si no se obtiene a tiempo.
    """
    try:
        return adquirir_lock_documento(documento_normalizado)
    except CorreccionEstablecimientoConflictError as exc:
        if getattr(exc, "codigo", "") == "DOCUMENTO_EN_USO":
            from app.domains.actuaciones.attach.documento_identidad_errors import (
                MSG_DOCUMENTO_EN_USO as MSG_EN_USO_CARGA,
            )

            raise DocumentoIdentidadError(
                MSG_EN_USO_CARGA, codigo="DOCUMENTO_EN_USO"
            ) from exc
        raise


def asegurar_reserva_documento(contribuyente_id: int, documento: str) -> None:
    """
    Deja ``contribuyente_documento_unico`` coherente para un id activo único.

    - Si no hay fila: INSERT (alta o backfill de un histórico único).
    - Si la fila es de este id: no-op.
    - Si la fila es de un contribuyente borrado lógicamente: reasigna (no fusiona personas).
    - Si la fila es de otro activo: DOCUMENTO_AMBIGUO (no elige ni crea otro).

    Debe llamarse con GET_LOCK tomado. No hace commit.

    Parámetros:
        contribuyente_id: titular que retiene el documento.
        documento: valor persistido o propuesto (se normaliza).

    Errores:
        DocumentoIdentidadError DOCUMENTO_AMBIGUO.
        IntegrityError de unique se traduce al mismo conflicto.
    """
    norm = normalizar_documento(documento)
    if not norm:
        return

    ajenos = sorted(
        {
            int(i)
            for i in contribuyente_ids_por_documento(documento, for_update=True)
            if int(i) != int(contribuyente_id)
        }
    )
    if ajenos:
        raise DocumentoIdentidadError(MSG_DOCUMENTO_AMBIGUO, codigo="DOCUMENTO_AMBIGUO")

    existente = (
        ContribuyenteDocumentoUnico.query.filter_by(documento_normalizado=norm)
        .with_for_update()
        .first()
    )
    if existente is not None:
        if int(existente.contribuyente_id) == int(contribuyente_id):
            return
        owner = db.session.get(Contribuyente, int(existente.contribuyente_id))
        if owner is not None and getattr(owner, "deleted_at", None) is None:
            raise DocumentoIdentidadError(MSG_DOCUMENTO_AMBIGUO, codigo="DOCUMENTO_AMBIGUO")
        existente.contribuyente_id = int(contribuyente_id)
        db.session.add(existente)
        db.session.flush()
        return

    db.session.add(
        ContribuyenteDocumentoUnico(
            documento_normalizado=norm,
            contribuyente_id=int(contribuyente_id),
        )
    )
    try:
        db.session.flush()
    except IntegrityError as exc:
        raise DocumentoIdentidadError(MSG_DOCUMENTO_AMBIGUO, codigo="DOCUMENTO_AMBIGUO") from exc


def reclamar_documento_normalizado(contribuyente_id: int, documento: str, documento_anterior: str) -> None:
    """
    Reserva el documento normalizado para este contribuyente (canal A2).

    Debe llamarse con el contribuyente bloqueado y, si aplica, con GET_LOCK tomado.
    Revalida que ningún otro contribuyente activo tenga el documento.

    Parámetros:
        contribuyente_id: fila que se corrige (mismo id).
        documento: valor propuesto (se normaliza).
        documento_anterior: valor actual (para liberar la reserva vieja).

    Errores:
        DOCUMENTO_AJENO si otro id activo o la reserva ya es de otro.
        IntegrityError de unique se traduce a DOCUMENTO_AJENO.
    """
    nuevo_norm = normalizar_documento(documento)
    anterior_norm = normalizar_documento(documento_anterior)
    if not nuevo_norm or nuevo_norm == anterior_norm:
        return

    ajenos = sorted(
        {
            int(i)
            for i in contribuyente_ids_por_documento(documento)
            if int(i) != int(contribuyente_id)
        }
    )
    if ajenos:
        raise CorreccionEstablecimientoConflictError(
            MSG_DOC_AJENO,
            codigo="DOCUMENTO_AJENO",
            extra={"ofrece_vinculacion": len(ajenos) == 1},
        )

    existente = (
        ContribuyenteDocumentoUnico.query.filter_by(documento_normalizado=nuevo_norm)
        .with_for_update()
        .first()
    )
    if existente is not None:
        if int(existente.contribuyente_id) != int(contribuyente_id):
            raise CorreccionEstablecimientoConflictError(
                MSG_DOC_AJENO,
                codigo="DOCUMENTO_AJENO",
                extra={"ofrece_vinculacion": True},
            )
        _liberar_reserva_anterior(int(contribuyente_id), anterior_norm, nuevo_norm)
        return

    db.session.add(
        ContribuyenteDocumentoUnico(
            documento_normalizado=nuevo_norm,
            contribuyente_id=int(contribuyente_id),
        )
    )
    try:
        db.session.flush()
    except IntegrityError as exc:
        raise CorreccionEstablecimientoConflictError(
            MSG_DOC_AJENO,
            codigo="DOCUMENTO_AJENO",
            extra={"ofrece_vinculacion": True},
        ) from exc

    _liberar_reserva_anterior(int(contribuyente_id), anterior_norm, nuevo_norm)


def _liberar_reserva_anterior(contribuyente_id: int, anterior_norm: str, nuevo_norm: str) -> None:
    """Quita la reserva del documento anterior si era de esta misma persona."""
    if not anterior_norm or anterior_norm == nuevo_norm:
        return
    (
        ContribuyenteDocumentoUnico.query.filter_by(
            documento_normalizado=anterior_norm,
            contribuyente_id=int(contribuyente_id),
        ).delete(synchronize_session=False)
    )
