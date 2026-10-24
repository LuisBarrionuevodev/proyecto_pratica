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


def _archivo_es_terminal_no_reintentable(arch: Archivo) -> bool:
    if arch.deleted_at is not None:
        return True
    return arch.status in ("REJECTED", "DELETED")


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


def _raise_si_archivo_terminal_no_reintentable(arch: Archivo) -> None:
    """
    Impide reintentar upload-intent sobre evidencia dada de baja o rechazada.

    Errores:
        MediaDomainError: MEDIA_STATE_INVALID.
    """
    if not _archivo_es_terminal_no_reintentable(arch):
        return
    raise MediaDomainError(
        MEDIA_STATE_INVALID,
        "No se puede reutilizar la carga: el archivo está en un estado final "
        f"({arch.status}).",
    )


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


def _resolve_upload_intent_after_integrity_conflict(
    *,
    ruta_item_id: int,
    categoria: str,
    sha256: str,
    storage: MediaStorageService,
    original_err: IntegrityError,
) -> UploadIntentOut:
    """
    Tras colisión en el índice único de SHA, relee el vínculo y responde idempotentemente.

    Errores:
        MediaDomainError: archivo terminal no reintentable.
        IntegrityError: si no se pudo reconciliar el conflicto esperado.
    """
    db.session.query(RutaItem).filter(RutaItem.id == int(ruta_item_id)).with_for_update().one()
    active = _find_active_by_sha(ruta_item_id, categoria, sha256)
    if active:
        _link, arch = active
        return _upload_intent_out_for_archivo(arch, storage)
    vinculo = _find_vinculo_by_content_sha(ruta_item_id, categoria, sha256)
    if vinculo:
        _link, arch = vinculo
        _raise_si_archivo_terminal_no_reintentable(arch)
    raise original_err


def crear_upload_intent(
    *,
    ruta_item_id: int,
    body: UploadIntentIn,
    actor_user_id: int,
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
    vinculo_previo = _find_vinculo_by_content_sha(ruta_item_id, body.categoria, sha)
    if vinculo_previo:
        _link_prev, arch_prev = vinculo_previo
        _raise_si_archivo_terminal_no_reintentable(arch_prev)
        if arch_prev.status in ("PENDING", "READY") and arch_prev.deleted_at is None:
            return _upload_intent_out_for_archivo(arch_prev, storage)

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
    try:
        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()
        if not _is_idempotency_sha_unique_violation(err):
            raise
        return _resolve_upload_intent_after_integrity_conflict(
            ruta_item_id=ruta_item_id,
            categoria=body.categoria,
            sha256=sha,
            storage=storage,
            original_err=err,
        )

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
