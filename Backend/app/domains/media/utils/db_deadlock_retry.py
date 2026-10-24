"""Reintentos ante deadlock MySQL en transacciones cortas de media."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import OperationalError

from app.database import db

T = TypeVar("T")


def _is_mysql_deadlock(exc: BaseException) -> bool:
    if isinstance(exc, OperationalError):
        orig = getattr(exc, "orig", None)
        args = getattr(orig, "args", ())
        if args and args[0] == 1213:
            return True
    return "deadlock" in str(exc).lower()


def run_with_deadlock_retry(action: Callable[[], T], *, max_attempts: int = 3) -> T:
    """
    Ejecuta ``action`` reintentando ante deadlock (1213).

    Parámetros:
        action: callable que realiza flush/commit dentro de la sesión actual.
        max_attempts: intentos máximos.

    Retorno:
        Valor devuelto por ``action``.

    Errores:
        Propaga la última excepción si se agotan los reintentos.
    """
    last: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return action()
        except OperationalError as exc:
            last = exc
            if not _is_mysql_deadlock(exc) or attempt >= max_attempts - 1:
                raise
            db.session.rollback()
    assert last is not None
    raise last
