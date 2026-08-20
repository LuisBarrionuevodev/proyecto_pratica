from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import joinedload

from app.models import IniciadorRuta, RutaItem, RutaPoolDia, RutaTrabajo

_ESTADOS_POOL_ACTIVOS = ("EN_POOL", "ASIGNADO_A_RUTA")
_ESTADOS_RUTA_BLOQUEAN = ("PUBLICADA", "EN_CURSO", "CERRADA", "CANCELADA")
_ESTADOS_RUTA_ITEM_ABIERTOS = ("PENDIENTE_ASIGNACION", "ASIGNADO", "EN_PROCESO")
_TIPOS_PLANIFICABLES = {
    "RELEVAMIENTO",
    "DENUNCIA",
    "REINSPECCION_OFICIO",
    "REINSPECCION_NOTIFICACION",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
}
_MSG_POOL_OTRA_RUTA = (
    "El pendiente ya está asociado a otra ruta activa. "
    "Sacalo de esa ruta antes de asignarlo a una nueva."
)


def _turno_clause(query, turno_id: int | None):
    if turno_id is None:
        return query.filter(RutaPoolDia.turno_id.is_(None))
    return query.filter(RutaPoolDia.turno_id == turno_id)


_MSG_ITEM_NO_LIBERABLE = (
    "No se puede quitar porque ya tiene Orden de Trabajo, ejecución o actuación vinculada."
)


def es_iniciador_agregable_a_ruta(iniciador_id: int, ruta_trabajo_id: int) -> bool:
    """
    True si el iniciador puede mostrarse como candidato agregable en el mapa de la ruta.

    Usa reglas OPER-RUTA.6F/6G/6H: pool/ruta activa de otra ruta, ítem borrador/publicado
    o estados no pendientes bloquean.
    """
    iniciador = IniciadorRuta.query.filter(
        IniciadorRuta.id == int(iniciador_id),
        IniciadorRuta.deleted_at.is_(None),
        IniciadorRuta.estado_iniciador == "PENDIENTE",
    ).first()
    if not iniciador:
        return False

    if iniciador_en_ruta_no_borrador_activa(int(iniciador_id)) is not None:
        return False

    if iniciador_en_ruta_borrador_activa(int(iniciador_id)) is not None:
        return False

    pools = (
        RutaPoolDia.query.filter(
            RutaPoolDia.iniciador_ruta_id == int(iniciador_id),
            RutaPoolDia.deleted_at.is_(None),
            RutaPoolDia.estado.in_(_ESTADOS_POOL_ACTIVOS),
        )
        .all()
    )
    for pool in pools:
        if not pool_row_bloquea_planificacion(pool):
            continue
        dup_ruta_id = pool.ruta_trabajo_id
        if dup_ruta_id is None or int(dup_ruta_id) != int(ruta_trabajo_id):
            return False
        # EN_POOL / ASIGNADO activo en esta misma ruta → no candidato (va al panel pool/grupo).
        return False

    return True


def filtrar_iniciadores_agregables_a_ruta(
    iniciadores: list[IniciadorRuta],
    ruta_trabajo_id: int,
) -> list[IniciadorRuta]:
    """Filtra iniciadores no agregables al mapa de la ruta indicada."""
    return [
        ini
        for ini in iniciadores
        if es_iniciador_agregable_a_ruta(int(ini.id), int(ruta_trabajo_id))
    ]


def assert_ruta_item_liberable_desde_grupo(item: RutaItem) -> None:
    """
    Valida que un ítem de ruta BORRADOR pueda volver al pool (Quitar / Eliminar grupo).

    Errores:
        RuntimeError: OT, actuación o ejecución REALIZADO.
    """
    if item.orden_trabajo_id is not None:
        raise RuntimeError(_MSG_ITEM_NO_LIBERABLE)
    if item.actuacion_id is not None:
        raise RuntimeError(_MSG_ITEM_NO_LIBERABLE)
    if (item.estado_ejecucion or "").strip().upper() == "REALIZADO":
        raise RuntimeError(_MSG_ITEM_NO_LIBERABLE)


def infer_origen_tipo_para_iniciador(
    iniciador: IniciadorRuta,
    origen_tipo_solicitado: str | None,
) -> str:
    """
    Resuelve ``origen_tipo`` coherente con el iniciador.

    Parámetros:
        iniciador: instancia ORM.
        origen_tipo_solicitado: valor del payload o None.

    Retorno:
        origen_tipo persistible.

    Errores:
        ValueError: origen incompatible con tipo de iniciador.
    """
    if origen_tipo_solicitado:
        return origen_tipo_solicitado
    tipo = (iniciador.tipo_iniciador or "").strip().upper()
    if tipo == "RELEVAMIENTO":
        return "RELEVAMIENTO"
    if tipo == "DENUNCIA":
        return "DENUNCIA"
    if tipo == "REINSPECCION_NOTIFICACION":
        return "INICIADOR"
    if tipo == "REINSPECCION_OFICIO":
        return "INICIADOR"
    return "INICIADOR"


def ruta_item_bloquea_nueva_planificacion(item: RutaItem | None) -> bool:
    """
    True si el ``RutaItem`` representa una asignación operativa vigente (OPER-RUTA.6F).

    Ítems ``FINALIZADO`` (REALIZADO o NO_REALIZADO reencolable) no bloquean replanificación
    aunque la ruta siga PUBLICADA/CERRADA en el historial.
    """
    if item is None or item.deleted_at is not None:
        return False
    if (item.estado_ruta_item or "").upper() == "FINALIZADO":
        return False
    estado_item = (item.estado_ruta_item or "").upper()
    if estado_item not in _ESTADOS_RUTA_ITEM_ABIERTOS:
        return False
    ruta = item.ruta_trabajo
    if ruta is None:
        return True
    estado_ruta = (ruta.estado_ruta or "").upper()
    if estado_ruta in ("BORRADOR", "PUBLICADA", "EN_CURSO", "CERRADA", "CANCELADA"):
        return True
    return False


def pool_row_bloquea_planificacion(
    pool: RutaPoolDia,
    *,
    ruta_items: list[RutaItem] | None = None,
) -> bool:
    """
    True si la fila de pool implica una planificación activa (no histórica).

    ``ASIGNADO_A_RUTA`` ligado a un ítem ya ``FINALIZADO`` no bloquea replanificación.
    """
    if pool.deleted_at is not None:
        return False
    if pool.estado == "EN_POOL":
        return True
    if pool.estado == "ASIGNADO_A_RUTA":
        if pool.ruta_item_id is None:
            return True
        items = ruta_items or []
        item = next((it for it in items if int(it.id) == int(pool.ruta_item_id)), None)
        if item is None:
            item = RutaItem.query.filter(RutaItem.id == int(pool.ruta_item_id)).first()
        return ruta_item_bloquea_nueva_planificacion(item)
    return False


def iniciador_en_ruta_borrador_activa(iniciador_id: int) -> RutaItem | None:
    """
    Retorna el ítem activo en ruta BORRADOR si existe.

    Parámetros:
        iniciador_id: id de iniciador.

    Retorno:
        ``RutaItem`` activo o None.
    """
    item = (
        RutaItem.query.join(RutaTrabajo, RutaTrabajo.id == RutaItem.ruta_trabajo_id)
        .filter(
            RutaItem.iniciador_ruta_id == iniciador_id,
            RutaItem.deleted_at.is_(None),
            RutaTrabajo.estado_ruta == "BORRADOR",
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    if item is not None and ruta_item_bloquea_nueva_planificacion(item):
        return item
    return None


def iniciador_en_ruta_no_borrador_activa(iniciador_id: int) -> RutaItem | None:
    """
    Retorna ítem activo en ruta PUBLICADA/EN_CURSO/CERRADA si existe.

    Parámetros:
        iniciador_id: id de iniciador.

    Retorno:
        ``RutaItem`` activo o None.
    """
    items = (
        RutaItem.query.join(RutaTrabajo, RutaTrabajo.id == RutaItem.ruta_trabajo_id)
        .filter(
            RutaItem.iniciador_ruta_id == iniciador_id,
            RutaItem.deleted_at.is_(None),
            RutaTrabajo.estado_ruta.in_(_ESTADOS_RUTA_BLOQUEAN),
        )
        .order_by(RutaItem.id.desc())
        .all()
    )
    for item in items:
        if ruta_item_bloquea_nueva_planificacion(item):
            return item
    return None


def buscar_entrada_pool_activa(
    *,
    fecha: date,
    turno_id: int | None,
    iniciador_ruta_id: int | None = None,
    actuacion_id: int | None = None,
    origen_tipo: str | None = None,
) -> RutaPoolDia | None:
    """
    Busca fila activa del pool para evitar duplicados.

    Parámetros:
        fecha, turno_id: clave del día operativo.
        iniciador_ruta_id / actuacion_id+origen_tipo: claves de origen.

    Retorno:
        Fila activa EN_POOL/ASIGNADO_A_RUTA o None.
    """
    q = RutaPoolDia.query.filter(
        RutaPoolDia.fecha == fecha,
        RutaPoolDia.deleted_at.is_(None),
        RutaPoolDia.estado.in_(_ESTADOS_POOL_ACTIVOS),
    )
    q = _turno_clause(q, turno_id)
    if iniciador_ruta_id is not None:
        q = q.filter(RutaPoolDia.iniciador_ruta_id == iniciador_ruta_id)
    elif actuacion_id is not None:
        q = q.filter(
            RutaPoolDia.actuacion_id == actuacion_id,
            RutaPoolDia.origen_tipo == (origen_tipo or "INICIADOR"),
        )
    else:
        return None
    rows = q.order_by(RutaPoolDia.id.desc()).all()
    for row in rows:
        if pool_row_bloquea_planificacion(row):
            return row
    return None


def validar_iniciador_elegible_para_pool(
    iniciador: IniciadorRuta,
    *,
    fecha: date,
    turno_id: int | None,
    ruta_trabajo_id: int | None = None,
) -> None:
    """
    Valida reglas de elegibilidad para alta en pool.

    Parámetros:
        iniciador: instancia ORM.
        fecha, turno_id: clave operativa del pool.
        ruta_trabajo_id: ruta destino opcional; bloquea duplicados en otra ruta activa.

    Errores:
        RuntimeError: regla de negocio incumplida.
        LookupError: iniciador inválido.
    """
    if iniciador.deleted_at is not None:
        raise RuntimeError("El iniciador está eliminado")
    if iniciador.estado_iniciador != "PENDIENTE":
        raise RuntimeError("El iniciador debe estar en estado PENDIENTE")
    tipo = (iniciador.tipo_iniciador or "").strip().upper()
    if tipo not in _TIPOS_PLANIFICABLES:
        raise RuntimeError(f"Tipo de iniciador no planificable: {tipo}")

    if iniciador_en_ruta_no_borrador_activa(int(iniciador.id)):
        raise RuntimeError("El iniciador ya está en una ruta publicada, en curso o cerrada")

    if iniciador_en_ruta_borrador_activa(int(iniciador.id)):
        raise RuntimeError("El iniciador ya está asignado a una ruta borrador")

    dup = buscar_entrada_pool_activa(
        fecha=fecha,
        turno_id=turno_id,
        iniciador_ruta_id=int(iniciador.id),
    )
    if dup is not None:
        dup_ruta_id = dup.ruta_trabajo_id
        if ruta_trabajo_id is not None:
            if dup_ruta_id is None or int(dup_ruta_id) != int(ruta_trabajo_id):
                raise RuntimeError(_MSG_POOL_OTRA_RUTA)
        elif dup_ruta_id is not None:
            raise RuntimeError(_MSG_POOL_OTRA_RUTA)
        raise RuntimeError("El iniciador ya está en el pool del día")


def calcular_puede_agregar_a_ruta(pool: RutaPoolDia) -> tuple[bool, str | None]:
    """
    Indica si una fila EN_POOL puede asignarse a ruta BORRADOR.

    Parámetros:
        pool: fila del pool.

    Retorno:
        Tupla (puede, motivo_bloqueo).
    """
    if pool.estado != "EN_POOL":
        return False, f"Estado del pool: {pool.estado}"
    if pool.deleted_at is not None:
        return False, "Entrada eliminada del pool"
    if pool.iniciador_ruta_id is None:
        return False, "Sin iniciador asociado (fase 2)"

    iniciador = (
        IniciadorRuta.query.options(joinedload(IniciadorRuta.domicilio))
        .filter(IniciadorRuta.id == pool.iniciador_ruta_id)
        .first()
    )
    if not iniciador:
        return False, "Iniciador no encontrado"
    if iniciador.estado_iniciador != "PENDIENTE":
        return False, f"Iniciador en estado {iniciador.estado_iniciador}"
    if iniciador_en_ruta_no_borrador_activa(int(iniciador.id)):
        return False, "Iniciador en ruta publicada/en curso/cerrada"
    if iniciador_en_ruta_borrador_activa(int(iniciador.id)):
        return False, "Iniciador ya asignado a ruta borrador"
    return True, None
