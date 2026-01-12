from __future__ import annotations

from app.database import db

from app.services.actuaciones.update_service import _get_actuacion_or_404


def eliminar_actuacion(actuacion_id: int) -> None:
    """
    Elimina una `Actuaciones` por id.

    Mantiene el comportamiento histórico:
    - Si la actuación no existe -> `ValueError("Actuación no encontrada.")`.
    - Si existe, hace `db.session.delete(...)` + `db.session.commit()`.

    Args:
        actuacion_id: id de la actuación a eliminar.

    Returns:
        None

    Raises:
        ValueError: si la actuación no existe.
    """
    act = _get_actuacion_or_404(actuacion_id)
    db.session.delete(act)
    db.session.commit()
