from __future__ import annotations

from app.database import db
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_pool_dia_eligibility_service import (
    calcular_puede_agregar_a_ruta,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import revert_pool_si_item_eliminado
from app.models import RutaPoolDia, RutaTrabajo


def _assert_ruta_borrador(ruta_id: int) -> RutaTrabajo:
    """
    Valida ruta destino en BORRADOR.

    Errores:
        LookupError, RuntimeError.
    """
    ruta = RutaTrabajo.query.get(ruta_id)
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")
    if ruta.estado_ruta != "BORRADOR":
        raise RuntimeError("Solo se puede agregar al pool en rutas BORRADOR")
    return ruta


def agregar_desde_pool_a_ruta(
    *,
    ruta_id: int,
    grupo_id: int,
    pool_ids: list[int],
) -> dict:
    """
    Asigna filas EN_POOL a un grupo de ruta BORRADOR reutilizando ``assign_iniciadores_to_grupo``.

    Parámetros:
        ruta_id: ruta destino BORRADOR.
        grupo_id: grupo obligatorio.
        pool_ids: ids de pool EN_POOL.

    Retorno:
        dict con items creados y filas de pool actualizadas.

    Errores:
        LookupError, RuntimeError, ValueError.
    """
    _assert_ruta_borrador(ruta_id)

    rows = RutaPoolDia.query.filter(RutaPoolDia.id.in_(pool_ids)).all()
    found = {r.id for r in rows}
    missing = [pid for pid in pool_ids if pid not in found]
    if missing:
        raise LookupError(f"Entradas de pool inexistentes: {missing}")

    for row in rows:
        if row.estado == "DESCARTADO":
            raise RuntimeError(f"La entrada {row.id} está descartada")
        if row.estado != "EN_POOL":
            raise RuntimeError(f"La entrada {row.id} no está EN_POOL")
        puede, motivo = calcular_puede_agregar_a_ruta(row)
        if not puede:
            raise RuntimeError(motivo or f"La entrada {row.id} no puede asignarse a ruta")
        if row.iniciador_ruta_id is None:
            raise RuntimeError(f"La entrada {row.id} no tiene iniciador (fase 2)")

    iniciador_ids = [int(r.iniciador_ruta_id) for r in rows if r.iniciador_ruta_id is not None]

    try:
        items = assign_iniciadores_to_grupo(
            ruta_id=ruta_id,
            grupo_id=grupo_id,
            iniciador_ids=iniciador_ids,
            commit=False,
        )
        items_by_iniciador = {int(i.iniciador_ruta_id): i for i in items}

        updated_rows: list[RutaPoolDia] = []
        for row in rows:
            item = items_by_iniciador.get(int(row.iniciador_ruta_id))
            if not item:
                raise RuntimeError(
                    f"No se generó ítem de ruta para iniciador {row.iniciador_ruta_id}"
                )
            row.estado = "ASIGNADO_A_RUTA"
            row.ruta_trabajo_id = ruta_id
            row.ruta_item_id = int(item.id)
            updated_rows.append(row)

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {
        "items": items,
        "pool_rows": updated_rows,
    }
