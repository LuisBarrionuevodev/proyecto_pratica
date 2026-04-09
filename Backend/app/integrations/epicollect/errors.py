"""Errores del cliente EpiCollect (red, auth, respuesta inesperada)."""


class EpicollectClientError(Exception):
    """Error base del cliente EpiCollect."""


class EpicollectConfigError(EpicollectClientError):
    """Configuración incompleta o inválida (p. ej. falta project slug)."""


class EpicollectAuthError(EpicollectClientError):
    """Fallo de autenticación OAuth (credenciales o token)."""


class EpicollectHttpError(EpicollectClientError):
    """Respuesta HTTP no exitosa de la API EpiCollect."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class EpicollectNetworkError(EpicollectClientError):
    """Timeout o error de red al contactar EpiCollect."""


class EpicollectEntryNotFoundError(EpicollectClientError):
    """No hay entry para el uuid solicitado en el proyecto/form configurado."""
