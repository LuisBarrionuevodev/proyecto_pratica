"""
Quitar actas operativas desde el canal **Cargar actuación** (modal / PUT actuaciones).

- Notificación y comprobación: desvinculan FK en ``Actuaciones`` y aplican soft delete huérfano
  (misma semántica que el garbage collector post-update).
- Inspección, clausura y decomiso: no tienen ``deleted_at`` en modelo; se elimina la fila hija
  asociada a la actuación (la actuación permanece). Es el único mecanismo ORM disponible hoy.
"""

from __future__ import annotations

from typing import Final

from app.database import db
from app.models import Actuaciones, Clausura, Decomiso, Inspeccion
from app.domains.actuaciones.cleanup.garbage_collector import (
    soft_delete_comprobacion_if_orphan,
    soft_delete_notificacion_if_orphan,
)
from app.domains.actuaciones.services.expediente_actas_edit_guard import (
    comprobacion_editable_desde_canal_actas,
    notificacion_editable_desde_canal_actas,
)

_TIPOS: Final[frozenset[str]] = frozenset(
    {"INSPECCION", "NOTIFICACION", "COMPROBACION", "CLAUSURA", "DECOMISO"}
)
_MSG_DOC_ASOCIADA = (
    "Esta acta tiene documentación asociada y debe modificarse desde su sección correspondiente."
)


def quitar_acta_canal_actas(actuacion_id: int, tipo: str) -> Actuaciones:
    """
    Quita el vínculo del acta indicada con la actuación y aplica borrado lógico o eliminación de fila hija.

    Parámetros:
        actuacion_id: PK de ``Actuaciones``.
        tipo: ``INSPECCION`` | ``NOTIFICACION`` | ``COMPROBACION`` | ``CLAUSURA`` | ``DECOMISO``.

    Retorno:
        Instancia ``Actuaciones`` recargada desde BD tras ``commit``.

    Errores:
        ValueError: tipo inválido, actuación inexistente, o reglas documentales bloquean notif/comp.
    """
    t = (tipo or "").strip().upper()
    if t not in _TIPOS:
        raise ValueError(f"Tipo de acta inválido: {tipo!r}.")

    act = Actuaciones.query.get(actuacion_id)
    if not act:
        raise ValueError("Actuación no encontrada.")

    try:
        if t == "NOTIFICACION":
            nid = act.notificacion_id
            if nid is None:
                raise ValueError("No hay acta de notificación vinculada.")
            if not notificacion_editable_desde_canal_actas(nid):
                raise ValueError(_MSG_DOC_ASOCIADA)
            act.notificacion_id = None
            db.session.add(act)
            db.session.flush()
            soft_delete_notificacion_if_orphan(int(nid))

        elif t == "COMPROBACION":
            cid = act.comprobacion_id
            if cid is None:
                raise ValueError("No hay acta de comprobación vinculada.")
            if not comprobacion_editable_desde_canal_actas(cid):
                raise ValueError(_MSG_DOC_ASOCIADA)
            act.comprobacion_id = None
            db.session.add(act)
            db.session.flush()
            soft_delete_comprobacion_if_orphan(int(cid))

        elif t == "INSPECCION":
            ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
            if ins is None:
                raise ValueError("No hay acta de inspección vinculada.")
            db.session.delete(ins)

        elif t == "CLAUSURA":
            cl = Clausura.query.filter_by(actuacion_id=act.id).first()
            if cl is None:
                raise ValueError("No hay acta de clausura vinculada.")
            db.session.delete(cl)

        elif t == "DECOMISO":
            dec = Decomiso.query.filter_by(actuacion_id=act.id).first()
            if dec is None:
                raise ValueError("No hay acta de decomiso vinculada.")
            db.session.delete(dec)

        else:
            raise ValueError(f"Tipo no implementado: {t!r}.")

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    out = Actuaciones.query.get(actuacion_id)
    if not out:
        raise RuntimeError("Actuación no encontrada tras persistir el cambio.")
    return out
