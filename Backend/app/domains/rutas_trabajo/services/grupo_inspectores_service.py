from __future__ import annotations

from app.database import db
from app.models import Inspector, RutaGrupo, RutaGrupoInspector, RutaTrabajo
from sqlalchemy.exc import IntegrityError

from .auth_service import get_current_user_id_or_fallback


def replace_grupo_inspectores(*, ruta_id: int, grupo_id: int, inspector_ids: list[int]) -> list[RutaGrupoInspector]:
    """
    Reemplaza totalmente los inspectores de un grupo.

    Reglas:
    - ruta en BORRADOR.
    - grupo debe pertenecer a la ruta y no estar soft-deleted.
    - un inspector no puede estar en más de un grupo dentro de la misma ruta.

    Errores:
    - LookupError: ruta/grupo/inspector no encontrados.
    - RuntimeError: estado inválido o conflicto por inspector asignado en otro grupo.
    """
    ruta = RutaTrabajo.query.get(ruta_id)
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")
    if ruta.estado_ruta != "BORRADOR":
        raise RuntimeError("Solo se pueden asignar inspectores en rutas BORRADOR")

    grupo = RutaGrupo.query.filter(
        RutaGrupo.id == grupo_id,
        RutaGrupo.ruta_trabajo_id == ruta_id,
        RutaGrupo.deleted_at.is_(None),
    ).first()
    if not grupo:
        raise LookupError("Grupo no encontrado para la ruta indicada")

    if inspector_ids:
        existing_ids = {
            row[0]
            for row in db.session.query(Inspector.id).filter(Inspector.id.in_(inspector_ids)).all()
        }
        missing = [inspector_id for inspector_id in inspector_ids if inspector_id not in existing_ids]
        if missing:
            raise LookupError(f"Inspectores inexistentes: {missing}")

    conflicts = (
        db.session.query(RutaGrupoInspector.inspector_id)
        .join(RutaGrupo, RutaGrupo.id == RutaGrupoInspector.ruta_grupo_id)
        .filter(
            RutaGrupo.ruta_trabajo_id == ruta_id,
            RutaGrupo.deleted_at.is_(None),
            RutaGrupoInspector.ruta_grupo_id != grupo_id,
            RutaGrupoInspector.inspector_id.in_(inspector_ids or [-1]),
        )
        .all()
    )
    if conflicts:
        conflict_ids = [row[0] for row in conflicts]
        raise RuntimeError(f"Inspectores ya asignados en otro grupo de la ruta: {conflict_ids}")

    db.session.query(RutaGrupoInspector).filter(
        RutaGrupoInspector.ruta_grupo_id == grupo_id
    ).delete(synchronize_session=False)

    user_id = get_current_user_id_or_fallback()
    for inspector_id in inspector_ids:
        db.session.add(
            RutaGrupoInspector(
                ruta_grupo_id=grupo_id,
                inspector_id=inspector_id,
                created_by_user_id=user_id,
            )
        )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise RuntimeError("No se pudo guardar la asignación de inspectores") from exc

    return (
        RutaGrupoInspector.query.filter(
            RutaGrupoInspector.ruta_grupo_id == grupo_id
        )
        .order_by(RutaGrupoInspector.id.asc())
        .all()
    )
