"""Helpers aislados para tests de colisión OT-AUTO (banda 4000)."""

from __future__ import annotations

import random
from datetime import datetime

from app.database import db
from app.domains.orden_trabajo.services.orden_trabajo_secuencia_service import (
    next_available_candidates,
)
from app.domains.orden_trabajo.services.orden_trabajo_secuencia_service import (
    _numero_acta_ocupado,
)
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import Domicilio, IniciadorRuta, OrdenTrabajo, OrdenTrabajoContador, RutaItem, RutaTrabajo
from app.utils.actas import format_ot_display


def fresh_collision_band(width: int = 20) -> int:
    """
    Elige banda numérica libre para un test de colisión aislado.

    Parámetros:
        width: cantidad de enteros consecutivos que deben estar libres.

    Retorno:
        Entero base (>= 1_000_000) sin ``numero_acta`` ocupados en el rango.

    Errores:
        RuntimeError: si no encuentra banda libre tras varios intentos.
    """
    for _ in range(80):
        band = 1_000_000 + random.randint(0, 199_999) * (width + 3)
        if all(not _numero_acta_ocupado(format_ot_display(band + i)) for i in range(width)):
            return band
    raise RuntimeError("No se encontró banda libre para test de colisión")


def set_counter_force(value: int) -> int:
    """
    Fija ``next_value`` sin normalizar (tests de colisión en banda controlada).

    Parámetros:
        value: entero exacto para el contador.

    Retorno:
        Valor persistido.
    """
    row = OrdenTrabajoContador.query.order_by(OrdenTrabajoContador.id.asc()).first()
    assert row is not None
    row.next_value = int(value)
    db.session.add(row)
    db.session.commit()
    return int(value)


def read_counter() -> int:
    """Lee ``next_value`` del singleton."""
    row = OrdenTrabajoContador.query.order_by(OrdenTrabajoContador.id.asc()).first()
    assert row is not None
    return int(row.next_value)


def ensure_legacy_ot(
    display: str,
    *,
    anio: int = 2090,
    soft_deleted: bool = False,
    numero_secuencia_global: int | None = None,
) -> OrdenTrabajo:
    """
    Garantiza una OT legacy/ocupada con ``numero_acta`` dado (sin consumir contador).

    Parámetros:
        display: ``numero_acta`` formateado.
        anio: año documental de la fila legacy.
        soft_deleted: si True, marca ``deleted_at``.
        numero_secuencia_global: secuencia automática opcional.

    Retorno:
        Instancia ``OrdenTrabajo`` persistida.
    """
    ot = OrdenTrabajo.query.filter_by(numero_acta=display, anio=anio).first()
    if ot is None:
        ot = OrdenTrabajo(
            numero_acta=display,
            anio=int(anio),
            mes=1,
            numero_secuencia_global=numero_secuencia_global,
        )
        db.session.add(ot)
    else:
        ot.numero_secuencia_global = numero_secuencia_global
    if soft_deleted:
        ot.deleted_at = ot.deleted_at or datetime.utcnow()
    db.session.commit()
    return ot


def publish_n_items(uid: int, n: int, *, fecha_year: int = 2026) -> tuple[list[str], int]:
    """
    Publica una ruta borrador con ``n`` ítems y devuelve displays OT asignados.

    Parámetros:
        uid: usuario actor.
        n: cantidad de ítems.
        fecha_year: año de la ruta.

    Retorno:
        Tupla (lista de ``numero_acta`` en orden de publicación, ``next_value`` posterior).
    """
    from datetime import date
    import random

    from app.models import Inspector

    inspectores = Inspector.query.limit(2).all()
    assert len(inspectores) >= 2

    inis: list[IniciadorRuta] = []
    for i in range(n):
        dom = Domicilio(calle=f"ColTest_{random.randint(1, 999999)}_{i}", numero="1")
        db.session.add(dom)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(fecha_year, 6, 1),
            anio=fecha_year,
            mes=6,
            domicilio_id=dom.id,
            created_by_user_id=uid,
        )
        db.session.add(ini)
        db.session.flush()
        inis.append(ini)

    ruta = RutaTrabajo(
        fecha=date(fecha_year, 6, 15),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=uid,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(
        ruta_id=ruta.id, nombre="ColTest", estado="ACTIVO", actor_user_id=uid
    )
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[inspectores[0].id, inspectores[1].id],
        actor_user_id=uid,
    )
    assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[i.id for i in inis],
        actor_user_id=uid,
    )
    db.session.commit()

    _, _, meta = publicar_ruta_trabajo(ruta_id=ruta.id)
    displays = [a["numero_acta"] for a in meta["ordenes_asignadas"]]
    return displays, int(meta["next_value"])


def expected_displays(candidate: int, count: int) -> list[str]:
    """Resuelve candidatos esperados con la misma regla del allocator."""
    valores, _, _ = next_available_candidates(candidate, count)
    return [format_ot_display(v) for v in valores]
