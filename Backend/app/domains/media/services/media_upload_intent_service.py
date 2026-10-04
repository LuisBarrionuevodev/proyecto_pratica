"""Caso de uso: crear intención de carga (PENDING + URL firmada PUT)."""

from __future__ import annotations

from datetime import datetime

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import (
    assert_current_user_can_access_ruta_item,
)
from app.domains.media.constants import (
    CATEGORIA_ACTA_DOCUMENTACION,
    STORAGE_PROVIDER_RAILWAY,
)
from app.domains.media.schemas.media_schemas import UploadIntentIn, UploadIntentOut
from app.domains.media.services.media_storage_service import MediaStorageService
from app.domains.media.utils.file_validation import max_bytes_for_content_type
from app.domains.media.utils.object_key import sanitize_original_filename
from app.integrations.media_storage.config import load_media_storage_config
from app.models import Archivo, RutaItemArchivo


def _count_acta_documentacion_activos(ruta_item_id: int) -> int:
    return (
        db.session.query(RutaItemArchivo)
        .join(Archivo, Archivo.id == RutaItemArchivo.archivo_id)
        .filter(
            RutaItemArchivo.ruta_item_id == int(ruta_item_id),
            RutaItemArchivo.categoria == CATEGORIA_ACTA_DOCUMENTACION,
            Archivo.deleted_at.is_(None),
            Archivo.status.in_(("PENDING", "READY")),
        )
        .count()
    )


def crear_upload_intent(
    *,
    ruta_item_id: int,
    body: UploadIntentIn,
    actor_user_id: int,
) -> UploadIntentOut:
    """
    Valida cupo y MIME, persiste PENDING y devuelve URL firmada de subida.

    Parámetros:
        ruta_item_id: ítem ancla.
        body: metadata declarada por el cliente.
        actor_user_id: usuario autenticado (auditoría).

    Retorno:
        UploadIntentOut con archivo_id y upload_url.

    Errores:
        ValueError: cupo, tamaño o reglas de negocio.
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
        raise ValueError("byte_size excede el límite permitido para el tipo de archivo.")
    if _count_acta_documentacion_activos(ruta_item_id) >= cfg.max_acta_documentacion_per_ruta_item:
        raise ValueError("Se alcanzó el máximo de documentos para este trabajo.")

    storage = MediaStorageService()
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
        sha256=body.sha256,
        status="PENDING",
        uploaded_by_user_id=int(actor_user_id),
    )
    db.session.add(arch)
    db.session.flush()

    link = RutaItemArchivo(
        ruta_item_id=int(ruta_item_id),
        archivo_id=int(arch.id),
        categoria=body.categoria,
        tipo_documento=body.tipo_documento,
    )
    db.session.add(link)
    db.session.commit()

    return UploadIntentOut(
        archivo_id=int(arch.id),
        upload_url=presigned.url,
        expires_at=presigned.expires_at,
    )
