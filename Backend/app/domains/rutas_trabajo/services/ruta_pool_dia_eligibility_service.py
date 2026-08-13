from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import joinedload

from app.models import IniciadorRuta, RutaItem, RutaPoolDia, RutaTrabajo

_ESTADOS_POOL_ACTIVOS = ("EN_POOL", "ASIGNADO_A_RUTA")
_ESTADOS_RUTA_BLOQUEAN = ("PUBLICADA", "EN_CURSO", "CERRADA", "CANCELADA")
_TIPOS_PLANIFICABLES = {
    "RELEVAMIENTO",
    "DENUNCIA",
    "REINSPECCION_OFICIO",
    "REINSPECCION_NOTIFICACION",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
}


def _turno_clause(query, turno_id: int | None):
    if turno_id is None:
        return query.filter(RutaPoolDia.turno_id.is_(None))
    return query.filter(RutaPoolDia.turno_id == turno_id)


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


def iniciador_en_ruta_borrador_activa(iniciador_id: int) -> RutaItem | None:
    """
    Retorna el ítem activo en ruta BORRADOR si existe.

    Parámetros:
        iniciador_id: id de iniciador.

    Retorno:
        ``RutaItem`` activo o None.
    """
    return (
        RutaItem.query.join(RutaTrabajo, RutaTrabajo.id == RutaItem.ruta_trabajo_id)
        .filter(
            RutaItem.iniciador_ruta_id == iniciador_id,
            RutaItem.deleted_at.is_(None),
            RutaTrabajo.estado_ruta == "BORRADOR",
        )
        .first()
    )


def iniciador_en_ruta_no_borrador_activa(iniciador_id: int) -> RutaItem | None:
    """
    Retorna ítem activo en ruta PUBLICADA/EN_CURSO/CERRADA si existe.

    Parámetros:
        iniciador_id: id de iniciador.

    Retorno:
        ``RutaItem`` activo o None.
    """
    return (
        RutaItem.query.join(RutaTrabajo, RutaTrabajo.id == RutaItem.ruta_trabajo_id)
        .filter(
            RutaItem.iniciador_ruta_id == iniciador_id,
            RutaItem.deleted_at.is_(None),
            RutaTrabajo.estado_ruta.in_(_ESTADOS_RUTA_BLOQUEAN),
        )
        .first()
    )


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
    return q.first()


def validar_iniciador_elegible_para_pool(
    iniciador: IniciadorRuta,
    *,
    fecha: date,
    turno_id: int | None,
) -> None:
    """
    Valida reglas de elegibilidad para alta en pool.

    Parámetros:
        iniciador: instancia ORM.
        fecha, turno_id: clave operativa del pool.

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
