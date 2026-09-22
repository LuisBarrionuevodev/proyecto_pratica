"""Helper canónico: crear ruta borrador válida y publicarla (OT-AUTO)."""

from __future__ import annotations

from datetime import date
import random

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import IniciadorRuta, Inspector, RutaItem, RutaTrabajo


def dos_inspectores() -> tuple[Inspector, Inspector]:
    """Dos inspectores de catálogo o skip."""
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores")
    return rows[0], rows[1]


def crear_y_publicar_ruta(
    *,
    iniciadores: list[IniciadorRuta],
    actor_user_id: int,
    fecha: date | None = None,
) -> tuple[RutaTrabajo, list[RutaItem], dict]:
    """
    Crea ruta BORRADOR con un grupo, inspectores e ítems; publica con OT-AUTO.

    Parámetros:
        iniciadores: iniciadores a asignar al grupo.
        actor_user_id: usuario actor.
        fecha: fecha de ruta (default hoy).

    Retorno:
        Tupla (ruta publicada, ítems activos, meta_publicacion).
    """
    ins1, ins2 = dos_inspectores()
    f = fecha or date.today()
    ruta = RutaTrabajo(
        fecha=f,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=int(actor_user_id),
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(
        ruta_id=ruta.id, nombre="TestPub", estado="ACTIVO", actor_user_id=int(actor_user_id)
    )
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
        actor_user_id=int(actor_user_id),
    )
    assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[i.id for i in iniciadores],
        actor_user_id=int(actor_user_id),
    )
    db.session.commit()
    ruta_pub, items, meta = publicar_ruta_trabajo(ruta_id=ruta.id)
    return ruta_pub, items, meta
