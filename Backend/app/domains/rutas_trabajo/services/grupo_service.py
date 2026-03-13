from __future__ import annotations

from app.database import db
from app.models import RutaGrupo, RutaTrabajo
from sqlalchemy.exc import IntegrityError

from .auth_service import get_current_user_id_or_fallback


def create_ruta_grupo(*, ruta_id: int, nombre: str, estado: str | None) -> RutaGrupo:
    """
    Crea un grupo dentro de una ruta en estado BORRADOR.

    Errores:
    - LookupError: ruta inexistente.
    - RuntimeError: ruta no editable por estado.
    - ValueError: datos inválidos.
    """
    ruta = RutaTrabajo.query.get(ruta_id)
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")
    if ruta.estado_ruta != "BORRADOR":
        raise RuntimeError("Solo se pueden crear grupos en rutas BORRADOR")

    nombre_value = (nombre or "").strip()
    if not nombre_value:
        raise ValueError("nombre es obligatorio")

    existente = (
        RutaGrupo.query.filter(
            RutaGrupo.ruta_trabajo_id == ruta_id,
            RutaGrupo.nombre == nombre_value,
            RutaGrupo.deleted_at.is_(None),
        )
        .first()
    )
    if existente:
        raise RuntimeError("Ya existe un grupo con ese nombre en la ruta")

    grupo = RutaGrupo(
        ruta_trabajo_id=ruta_id,
        nombre=nombre_value,
        estado=estado,
        created_by_user_id=get_current_user_id_or_fallback(),
    )
    db.session.add(grupo)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise RuntimeError("No se pudo crear el grupo por conflicto de datos") from exc
    return grupo
