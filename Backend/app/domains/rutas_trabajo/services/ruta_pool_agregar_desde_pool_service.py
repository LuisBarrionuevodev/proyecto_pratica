from __future__ import annotations

from app.database import db
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_pool_dia_eligibility_service import (
    calcular_puede_agregar_a_ruta,
    iniciador_en_ruta_borrador_activa,
    ruta_item_bloquea_nueva_planificacion,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import revert_pool_si_item_eliminado
from app.models import RutaGrupo, RutaPoolDia, RutaTrabajo

_MSG_POOL_OTRA_RUTA = (
    "El pendiente ya está asociado a otra ruta activa. "
    "Sacalo de esa ruta antes de asignarlo a una nueva."
)


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


def _validar_grupo_pertenece_a_ruta(*, ruta_id: int, grupo_id: int) -> RutaGrupo:
    """
    Verifica que el grupo exista y pertenezca a la ruta del path (OPER-RUTA.6G).

    Errores:
        LookupError: grupo inexistente.
        RuntimeError: grupo de otra ruta.
    """
    grupo = RutaGrupo.query.filter(
        RutaGrupo.id == grupo_id,
        RutaGrupo.deleted_at.is_(None),
    ).first()
    if not grupo:
        raise LookupError("Grupo no encontrado")
    if int(grupo.ruta_trabajo_id) != int(ruta_id):
        raise RuntimeError(_MSG_POOL_OTRA_RUTA)
    return grupo


def _validar_pool_para_ruta_destino(row: RutaPoolDia, ruta_id: int) -> None:
    """
    Impide mover pool EN_POOL a otra ruta distinta a la seleccionada (OPER-RUTA.6G).

    Errores:
        RuntimeError: pool o ítem activo apuntan a otra ruta borrador.
    """
    if row.ruta_trabajo_id is not None and int(row.ruta_trabajo_id) != int(ruta_id):
        raise RuntimeError(_MSG_POOL_OTRA_RUTA)

    if row.iniciador_ruta_id is None:
        return

    item_activo = iniciador_en_ruta_borrador_activa(int(row.iniciador_ruta_id))
    if item_activo is None:
        return
    if not ruta_item_bloquea_nueva_planificacion(item_activo):
        return
    if int(item_activo.ruta_trabajo_id) != int(ruta_id):
        raise RuntimeError(_MSG_POOL_OTRA_RUTA)


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
    _validar_grupo_pertenece_a_ruta(ruta_id=ruta_id, grupo_id=grupo_id)

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
        if row.iniciador_ruta_id is None:
            raise RuntimeError(f"La entrada {row.id} no tiene iniciador (fase 2)")
        _validar_pool_para_ruta_destino(row, ruta_id)
        puede, motivo = calcular_puede_agregar_a_ruta(row)
        if not puede:
            raise RuntimeError(motivo or f"La entrada {row.id} no puede asignarse a ruta")

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
