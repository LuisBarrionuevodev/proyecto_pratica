"""Errores de negocio del canal de corrección controlada desde Establecimientos."""

from __future__ import annotations


class CorreccionEstablecimientoError(Exception):
    """Error de corrección controlada (mapeable a HTTP)."""

    status_code = 400
    codigo = "CORRECCION_INVALIDA"

    def __init__(self, detail: str, *, codigo: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if codigo is not None:
            self.codigo = codigo


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
