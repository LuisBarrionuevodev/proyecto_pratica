"""Errores de identidad de documento compartidos por Cargar, Completar y PUT."""

from __future__ import annotations

from typing import Any


MSG_DOCUMENTO_AMBIGUO = (
    "No pudimos identificar este documento con seguridad. "
    "Contactá a administración para revisarlo."
)
MSG_DOCUMENTO_EN_USO = (
    "Otro usuario está guardando el mismo documento. Reintentá en unos segundos."
)
MSG_DOCUMENTO_LARGO = "El documento no puede superar 11 caracteres."
MSG_DOCUMENTO_INVALIDO = "Documento inválido."

DOCUMENTO_MAX_LEN = 11


class DocumentoIdentidadError(ValueError):
    """
    Conflicto o validación de documento al resolver un contribuyente.

    Qué hace: transporta un código identificable y un mapa de campo para HTTP/grilla.
    Parámetros: detail, codigo, http_status (default 409).
    Retorno: excepción; ``to_http_body`` arma el JSON.
    Errores: no lanza por sí misma.
    """

    codigo = "DOCUMENTO_IDENTIDAD"
    http_status = 409

    def __init__(
        self,
        detail: str,
        *,
        codigo: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        if codigo is not None:
            self.codigo = codigo
        if http_status is not None:
            self.http_status = http_status

    def to_http_body(self) -> dict[str, Any]:
        """Cuerpo JSON con detail, codigo y error de campo ``doc_nro``."""
        return {
            "detail": self.detail,
            "codigo": self.codigo,
            "errors": {"doc_nro": self.detail},
        }

    def to_grid_errors(self) -> dict[str, str]:
        """Mapa de celda para commit de grilla (detail + doc_nro)."""
        return {"detail": self.detail, "doc_nro": self.detail}
