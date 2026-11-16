"""Alta de contribuyente para vincular una ficha (sin ``resolve_contribuyente``)."""

from __future__ import annotations

from typing import Any

from app.database import db
from app.domains.establecimientos.schemas.vinculacion_establecimiento_in import (
    VinculacionAltaIn,
    VinculacionEstablecimientoIn,
)
from app.domains.establecimientos.services.contribuyente_documento_unico_service import (
    asegurar_reserva_documento,
)
from app.domains.establecimientos.utils.documento_normalizer import normalizar_documento
from app.models import Contribuyente


def alta_desde_body(body: VinculacionEstablecimientoIn) -> VinculacionAltaIn | None:
    """Devuelve el bloque alta validado o None si no se pidió crear."""
    return body.alta


def alta_key(alta: VinculacionAltaIn | None) -> str:
    """Clave estable de identidad propuesta para el fingerprint."""
    if alta is None:
        return ""
    return "|".join(
        [
            (alta.apellido or "").strip(),
            (alta.nombre or "").strip(),
            (alta.razon_social or "").strip(),
        ]
    )


def destino_propuesto_dict(documento: str, alta: VinculacionAltaIn) -> dict[str, Any]:
    """Titular propuesto (aún sin id) para preview de alta."""
    return {
        "id": None,
        "documento": documento,
        "apellido": alta.apellido,
        "nombre": alta.nombre,
        "razon_social": alta.razon_social,
    }


def crear_contribuyente_alta(documento: str, alta: VinculacionAltaIn) -> Contribuyente:
    """
    Inserta el contribuyente y reserva el documento normalizado.

    Qué hace: alta + ``asegurar_reserva_documento``. No hace commit.
    No llama ``resolve_contribuyente`` (no pisa nombres de nadie).

    Parámetros:
        documento: valor persistido (strip, máx. 11).
        alta: nombre/apellido o razón social.

    Retorno:
        Contribuyente persistido (flush).

    Errores:
        DocumentoIdentidadError si el documento ya está reservado o es ambiguo.
    """
    row = Contribuyente(
        documento=documento.strip(),
        apellido=alta.apellido,
        nombre=alta.nombre,
        razon_social=alta.razon_social,
    )
    db.session.add(row)
    db.session.flush()
    asegurar_reserva_documento(int(row.id), documento)
    return row


def documento_norm_body(documento: str) -> str:
    """Normaliza el CUIT/DNI del payload para fingerprint y lock."""
    return normalizar_documento(documento)
