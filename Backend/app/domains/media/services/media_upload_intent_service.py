"""Caso de uso: crear intención de carga (PENDING + URL firmada PUT)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import (
    assert_current_user_can_access_ruta_item,
)
from app.domains.media.constants import STORAGE_PROVIDER_RAILWAY
from app.domains.media.errors import (
    MEDIA_QUOTA_EXCEEDED,
    MEDIA_STATE_INVALID,
    MediaDomainError,
)
from app.domains.media.schemas.media_schemas import UploadIntentIn, UploadIntentOut
from app.domains.media.services.media_storage_service import MediaStorageService
from app.domains.media.utils.file_validation import max_bytes_for_content_type
from app.domains.media.utils.object_key import sanitize_original_filename
from app.domains.media.utils.db_deadlock_retry import run_with_deadlock_retry
from app.domains.media.utils.ruta_item_archivo_idempotency import (
    release_content_sha256_idempotency_key,
)
from app.integrations.media_storage.config import (
    load_media_storage_config,
    max_archivos_por_categoria,
)
from app.domains.media.utils.media_observability import log_upload_intent_created
from app.domains.actuaciones.services.completar_trabajo_pendiente_filters import (
    normalize_upload_origin_for_create,
)
from app.models import Archivo, RutaItem, RutaItemArchivo


def _count_activos_por_categoria(ruta_item_id: int, categoria: str) -> int:
    return (
        db.session.query(RutaItemArchivo)
        .join(Archivo, Archivo.id == RutaItemArchivo.archivo_id)
        .filter(
            RutaItemArchivo.ruta_item_id == int(ruta_item_id),
            RutaItemArchivo.categoria == categoria,
            Archivo.deleted_at.is_(None),
            Archivo.status.in_(("PENDING", "READY")),
        )
        .count()
    )


_IDEMPOTENCY_UNIQUE_INDEX = "uq_ruta_item_archivo_item_cat_sha"


def _is_idempotency_sha_unique_violation(err: IntegrityError) -> bool:
    """True si el conflicto proviene del índice (ruta_item, categoría, content_sha256)."""
    raw = str(getattr(err, "orig", err)).lower()
    return _IDEMPOTENCY_UNIQUE_INDEX in raw or (
        "duplicate" in raw and "content_sha256" in raw
    )


def _archivo_es_rechazado_no_reintentable(arch: Archivo) -> bool:
    return arch.status == "REJECTED"


def _archivo_eliminado_o_borrado(arch: Archivo) -> bool:
    return arch.deleted_at is not None or arch.status == "DELETED"


def _find_vinculo_by_content_sha(
    ruta_item_id: int,
    categoria: str,
    sha256: str,
) -> tuple[RutaItemArchivo, Archivo] | None:
    """
    Busca vínculo por clave de idempotencia (incluye archivos terminales).

    Parámetros:
        ruta_item_id, categoria, sha256: clave de negocio.

    Retorno:
        Par (RutaItemArchivo, Archivo) o None si no hay fila con ese SHA en el vínculo.
    """
    sha = sha256.lower()
    row = (
        db.session.query(RutaItemArchivo, Archivo)
        .join(Archivo, Archivo.id == RutaItemArchivo.archivo_id)
        .filter(
            RutaItemArchivo.ruta_item_id == int(ruta_item_id),
            RutaItemArchivo.categoria == categoria,
            RutaItemArchivo.content_sha256 == sha,
        )
        .with_for_update()
        .first()
    )
    if not row:
        return None
    return row[0], row[1]


def _find_active_by_sha(
    ruta_item_id: int,
    categoria: str,
    sha256: str,
) -> tuple[RutaItemArchivo, Archivo] | None:
    """Vínculo activo PENDING/READY reutilizable para idempotencia."""
    found = _find_vinculo_by_content_sha(ruta_item_id, categoria, sha256)
    if not found:
        return None
    _link, arch = found
    if arch.deleted_at is not None or arch.status not in ("PENDING", "READY"):
        return None
    return found


def _raise_si_archivo_rechazado(arch: Archivo) -> None:
    """
    Impide reintentar upload-intent sobre contenido rechazado en validación.

    Errores:
        MediaDomainError: MEDIA_STATE_INVALID.
    """
    if not _archivo_es_rechazado_no_reintentable(arch):
        return
    raise MediaDomainError(
        MEDIA_STATE_INVALID,
        "No se puede reutilizar la carga: el archivo está en un estado final "
        f"({arch.status}).",
    )


def _release_vinculo_eliminado_si_bloquea(
    link: RutaItemArchivo,
    arch: Archivo,
) -> None:
    """Libera SHA en vínculo histórico DELETED para permitir una carga nueva."""
    if not _archivo_eliminado_o_borrado(arch):
        return
    release_content_sha256_idempotency_key(link)


def _upload_intent_out_for_archivo(arch: Archivo, storage: MediaStorageService) -> UploadIntentOut:
    """Construye respuesta idempotente para un Archivo PENDING o READY existente."""
    if arch.status == "READY":
        return UploadIntentOut(
            archivo_id=int(arch.id),
            upload_url="",
            expires_at=datetime.utcnow(),
            status="READY",
        )
    presigned = storage.create_presigned_put(arch.object_key, arch.content_type)
    return UploadIntentOut(
        archivo_id=int(arch.id),
        upload_url=presigned.url,
        expires_at=presigned.expires_at,
        status="PENDING",
    )


def _try_resolve_existing_upload_intent(
    *,
    ruta_item_id: int,
    categoria: str,
    sha256: str,
    storage: MediaStorageService,
) -> UploadIntentOut | None:
    """
    Reutiliza PENDING/READY, libera vínculo DELETED o rechaza REJECTED.

    Retorno:
        UploadIntentOut si hay reutilización idempotente; None si debe crearse uno nuevo.

    Errores:
        MediaDomainError: REJECTED.
    """
    vinculo = _find_vinculo_by_content_sha(ruta_item_id, categoria, sha256)
    if not vinculo:
        return None
    link, arch = vinculo
    _raise_si_archivo_rechazado(arch)
    if _archivo_eliminado_o_borrado(arch):
        _release_vinculo_eliminado_si_bloquea(link, arch)
        db.session.flush()
        return None
    if arch.status in ("PENDING", "READY"):
        return _upload_intent_out_for_archivo(arch, storage)
    return None


def _persist_new_upload_intent(
    *,
    ruta_item_id: int,
    body: UploadIntentIn,
    actor_user_id: int,
    sha: str,
    storage: MediaStorageService,
    cfg,
) -> UploadIntentOut:
    """Crea Archivo PENDING + vínculo y confirma transacción."""
    cupo = max_archivos_por_categoria(cfg, body.categoria)
    if _count_activos_por_categoria(ruta_item_id, body.categoria) >= cupo:
        raise MediaDomainError(
            MEDIA_QUOTA_EXCEEDED,
            "Se alcanzó el máximo de archivos para esta categoría.",
        )

    object_key = storage.generate_object_key(
        ruta_item_id=ruta_item_id,
        categoria=body.categoria,
        content_type=body.content_type,
    )
    original = sanitize_original_filename(body.filename)
    presigned = storage.create_presigned_put(object_key, body.content_type)

    arch = Archivo(
        storage_provider=STORAGE_PROVIDER_RAILWAY,
        bucket=storage.bucket,
        object_key=object_key,
        original_filename=original,
        content_type=body.content_type,
        byte_size=int(body.byte_size),
        sha256=sha,
        status="PENDING",
        uploaded_by_user_id=int(actor_user_id),
    )
    db.session.add(arch)
    db.session.flush()

    origin = normalize_upload_origin_for_create(getattr(body, "upload_origin", None))
    link = RutaItemArchivo(
        ruta_item_id=int(ruta_item_id),
        archivo_id=int(arch.id),
        categoria=body.categoria,
        tipo_documento=body.tipo_documento,
        content_sha256=sha,
        upload_origin=origin,
    )
    db.session.add(link)

    def _commit_new() -> None:
        db.session.commit()

    run_with_deadlock_retry(_commit_new)

    log_upload_intent_created(
        archivo_id=int(arch.id),
        ruta_item_id=int(ruta_item_id),
        categoria=body.categoria,
    )

    return UploadIntentOut(
        archivo_id=int(arch.id),
        upload_url=presigned.url,
        expires_at=presigned.expires_at,
        status="PENDING",
    )


def crear_upload_intent(
    *,
    ruta_item_id: int,
    body: UploadIntentIn,
    actor_user_id: int,
    _retry_after_sha_conflict: bool = False,
) -> UploadIntentOut:
    """
    Valida cupo y MIME, persiste PENDING y devuelve URL firmada de subida.

    Idempotente por ``RutaItem + categoría + SHA-256`` (archivo activo PENDING/READY).

    Parámetros:
        ruta_item_id: ítem ancla.
        body: metadata declarada por el cliente.
        actor_user_id: usuario autenticado (auditoría).

    Retorno:
        UploadIntentOut con archivo_id y upload_url (vacío si ya READY).

    Errores:
        MediaDomainError: cupo, tamaño o reglas de negocio.
        RutaItemAccessError: sin acceso al ítem.
    """
    assert_current_user_can_access_ruta_item(int(ruta_item_id))
    cfg = load_media_storage_config()
    max_bytes = max_bytes_for_content_type(
        body.content_type,
        max_image=cfg.max_image_bytes,
        max_document=cfg.max_document_bytes,
    )
    if body.byte_size > max_bytes:
        raise MediaDomainError(
            "MEDIA_SIZE_EXCEEDED",
            "byte_size excede el límite permitido para el tipo de archivo.",
        )

    sha = body.sha256.lower()
    db.session.query(RutaItem).filter(RutaItem.id == int(ruta_item_id)).with_for_update().one()

    storage = MediaStorageService()
    resolved = _try_resolve_existing_upload_intent(
        ruta_item_id=ruta_item_id,
        categoria=body.categoria,
        sha256=sha,
        storage=storage,
    )
    if resolved is not None:
        return resolved

    try:
        return _persist_new_upload_intent(
            ruta_item_id=ruta_item_id,
            body=body,
            actor_user_id=actor_user_id,
            sha=sha,
            storage=storage,
            cfg=cfg,
        )
    except IntegrityError as err:
        db.session.rollback()
        if not _is_idempotency_sha_unique_violation(err):
            raise
        if _retry_after_sha_conflict:
            raise
        db.session.query(RutaItem).filter(RutaItem.id == int(ruta_item_id)).with_for_update().one()
        resolved = _try_resolve_existing_upload_intent(
            ruta_item_id=ruta_item_id,
            categoria=body.categoria,
            sha256=sha,
            storage=storage,
        )
        if resolved is not None:
            return resolved
        return crear_upload_intent(
            ruta_item_id=ruta_item_id,
            body=body,
            actor_user_id=actor_user_id,
            _retry_after_sha_conflict=True,
        )
