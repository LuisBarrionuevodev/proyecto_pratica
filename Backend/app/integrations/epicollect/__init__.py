"""Cliente HTTP para la API de lectura de EpiCollect5 (export entries)."""

from .client import EpicollectApiClient
from .config import EpicollectClientConfig

__all__ = ["EpicollectApiClient", "EpicollectClientConfig"]
