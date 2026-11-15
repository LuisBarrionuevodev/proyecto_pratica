"""Errores de negocio del canal de corrección controlada desde Establecimientos."""

from __future__ import annotations

from typing import Any


class CorreccionEstablecimientoError(Exception):
    """Error de corrección controlada (mapeable a HTTP)."""

    status_code = 400
    codigo = "CORRECCION_INVALIDA"

    def __init__(
        self,
        detail: str,
        *,
        codigo: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        if codigo is not None:
            self.codigo = codigo
        self.extra: dict[str, Any] = extra or {}

    def to_conflicto_dict(self) -> dict[str, Any]:
        """Payload de ``conflicto`` para preview (codigo, detail y extra estructurado)."""
        payload: dict[str, Any] = {"codigo": self.codigo, "detail": self.detail}
        payload.update(self.extra)
        return payload

    def to_http_body(self) -> dict[str, Any]:
        """Cuerpo JSON de error HTTP; no pisa ``detail``/``codigo`` con extra."""
        body: dict[str, Any] = {"detail": self.detail, "codigo": self.codigo}
        for key, value in self.extra.items():
            if key not in body:
                body[key] = value
        return body


class CorreccionEstablecimientoNotFoundError(CorreccionEstablecimientoError):
    """Ficha o entidad ancla inexistente."""

    status_code = 404
    codigo = "NO_ENCONTRADO"


class CorreccionEstablecimientoPermisoError(CorreccionEstablecimientoError):
    """Rol sin permiso para el canal de corrección."""

    status_code = 403
    codigo = "SIN_PERMISO"


class CorreccionEstablecimientoConflictError(CorreccionEstablecimientoError):
    """Conflicto de identidad, documento, alcance o concurrencia."""

    status_code = 409
    codigo = "CONFLICTO"
