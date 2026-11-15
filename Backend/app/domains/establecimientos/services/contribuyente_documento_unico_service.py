"""Reserva atómica de documento normalizado para corrección de CUIT/DNI."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.domains.establecimientos.services.historial_contribuyente_service import (
    contribuyente_ids_por_documento,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
)
from app.domains.establecimientos.utils.documento_normalizer import normalizar_documento
from app.models import ContribuyenteDocumentoUnico

logger = logging.getLogger(__name__)

MSG_DOC_AJENO = (
    "El documento propuesto ya pertenece a otro contribuyente. "
    "No se fusionan registros ni se reasigna el titular."
)
MSG_DOC_EN_USO = (
    "Otro usuario está corrigiendo el mismo documento. "
    "Volvé a consultar el alcance antes de confirmar."
)


def lock_key_documento(documento_normalizado: str) -> str:
    """Nombre de GET_LOCK acotado a 64 caracteres."""
    return f"corr_doc:{documento_normalizado}"[:64]


def adquirir_lock_documento(documento_normalizado: str) -> str:
    """
    Serializa correcciones A2 del mismo documento normalizado (MySQL GET_LOCK).

    Parámetros:
        documento_normalizado: CUIT/DNI sin separadores.

    Retorno:
        Clave a pasar a ``liberar_lock_documento``.

    Errores:
        CorreccionEstablecimientoConflictError si el lock no se obtiene a tiempo.
    """
    key = lock_key_documento(documento_normalizado)
    got = db.session.execute(text("SELECT GET_LOCK(:k, 10)"), {"k": key}).scalar()
    if int(got or 0) != 1:
        raise CorreccionEstablecimientoConflictError(MSG_DOC_EN_USO, codigo="DOCUMENTO_EN_USO")
    return key


def liberar_lock_documento(key: str | None) -> None:
    """Libera GET_LOCK de la conexión actual. No relanza errores de liberación."""
    if not key:
        return
    try:
        db.session.execute(text("SELECT RELEASE_LOCK(:k)"), {"k": key})
    except Exception:
        logger.warning("no se pudo liberar GET_LOCK de documento", extra={"key": key})


def reclamar_documento_normalizado(contribuyente_id: int, documento: str, documento_anterior: str) -> None:
    """
    Reserva el documento normalizado para este contribuyente.

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
