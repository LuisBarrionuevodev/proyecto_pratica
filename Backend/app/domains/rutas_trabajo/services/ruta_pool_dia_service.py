from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.rutas_trabajo.presenters.ruta_presenters import (
    _build_domicilio_texto_desde_dom,
    iniciador_operativo_campos,
)
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    cargar_domicilio_efectivo_orm,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_eligibility_service import (
    _ESTADOS_POOL_ACTIVOS,
    _MSG_POOL_OTRA_RUTA,
    calcular_puede_agregar_a_ruta,
    infer_origen_tipo_para_iniciador,
    pool_row_bloquea_planificacion,
    validar_iniciador_elegible_para_pool,
)
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id_or_fallback
from app.domains.rutas_trabajo.utils.rubro_operativo import (
    rubro_id_operativo_para_iniciador,
    rubro_nombre_operativo_para_iniciador,
)
from app.models import Comprobacion, Domicilio, IniciadorRuta, Notificacion, Oficio, Relevamiento, RutaItem, RutaPoolDia, RutaTrabajo, User


def _iniciador_operativo_joinedload_options():
    """Eager load de relaciones necesarias para detalle operativo en pool."""
    return (
        joinedload(RutaPoolDia.iniciador_ruta).options(
            joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
            joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
            joinedload(IniciadorRuta.denuncia),
            joinedload(IniciadorRuta.notificacion).joinedload(Notificacion.expedientes),
            joinedload(IniciadorRuta.comprobacion),
            joinedload(IniciadorRuta.oficio).options(
                joinedload(Oficio.comprobacion),
                joinedload(Oficio.juzgado),
                joinedload(Oficio.expediente),
            ),
        ),
    )


def ruta_pool_dia_row_dict(pool: RutaPoolDia) -> dict[str, Any]:
    """
    Serializa fila del pool para API.

    Parámetros:
        pool: instancia con relaciones cargadas si aplica.

    Retorno:
        dict JSON con campos de UI futura.
    """
    iniciador = pool.iniciador_ruta
    dom = pool.domicilio
    if dom is None and iniciador is not None:
        dom_ef, _src = cargar_domicilio_efectivo_orm(iniciador, apply_backfill=False, try_sync=False)
        dom = dom_ef

    distrito_nombre = None
    if pool.distrito and pool.distrito.nombre:
        distrito_nombre = pool.distrito.nombre
    elif dom and dom.distrito and dom.distrito.nombre:
        distrito_nombre = dom.distrito.nombre

    rubro_nombre = None
    if pool.rubro and pool.rubro.nombre:
        rubro_nombre = pool.rubro.nombre
    elif iniciador and dom:
        rubro_nombre = rubro_nombre_operativo_para_iniciador(iniciador, dom)

    ruta_estado = None
    if pool.ruta_trabajo:
        ruta_estado = pool.ruta_trabajo.estado_ruta

    puede, motivo = calcular_puede_agregar_a_ruta(pool)

    usuario_nombre = None
    if pool.usuario:
        usuario_nombre = pool.usuario.username

    domicilio_texto = _build_domicilio_texto_desde_dom(dom)

    operativo = iniciador_operativo_campos(iniciador)

    return {
        "pool_id": pool.id,
        "fecha": pool.fecha.isoformat() if pool.fecha else None,
        "turno_id": pool.turno_id,
        "estado": pool.estado,
        "origen_tipo": pool.origen_tipo,
        "iniciador_id": pool.iniciador_ruta_id,
        "iniciador_ruta_id": pool.iniciador_ruta_id,
        "actuacion_id": pool.actuacion_id,
        "domicilio_id": pool.domicilio_id,
        "domicilio_texto": domicilio_texto,
        "distrito_id": pool.distrito_id,
        "distrito_nombre": distrito_nombre,
        "rubro_id": pool.rubro_id,
        "rubro_nombre": rubro_nombre,
        "ruta_trabajo_id": pool.ruta_trabajo_id,
        "ruta_item_id": pool.ruta_item_id,
        "ruta_estado": ruta_estado,
        "puede_agregar_a_ruta": puede,
        "motivo_bloqueo": motivo,
        "observacion": pool.observacion,
        "created_at": pool.created_at.isoformat() if pool.created_at else None,
        "usuario_id": pool.usuario_id,
        "usuario_nombre": usuario_nombre,
        **operativo,
    }


def _resolve_snapshot_from_iniciador(iniciador: IniciadorRuta) -> tuple[int, int | None, int | None]:
    """
    Resuelve domicilio/distrito/rubro snapshot para persistir en pool.

    Parámetros:
        iniciador: instancia ORM.

    Retorno:
        Tupla (domicilio_id, distrito_id, rubro_id).
    """
    dom, _src = cargar_domicilio_efectivo_orm(iniciador, apply_backfill=False, try_sync=False)
    if dom is None:
        raise RuntimeError("El iniciador no tiene domicilio resoluble")
    distrito_id = dom.distrito_id
    rubro_id = rubro_id_operativo_para_iniciador(iniciador, dom)
    return int(dom.id), distrito_id, rubro_id


def list_ruta_pool_dia(
    *,
    fecha,
    turno_id: int | None = None,
    distrito_id: int | None = None,
    rubro_id: int | None = None,
    ruta_trabajo_id: int | None = None,
    estado: str | None = None,
    q: str | None = None,
    page: int = 1,
    per_page: int = 25,
) -> tuple[list[RutaPoolDia], int]:
    """
    Lista paginada del pool del día.

    Parámetros:
        fecha: día operativo obligatorio.
        turno_id, distrito_id, rubro_id, ruta_trabajo_id, estado, q: filtros opcionales.
        page, per_page: paginación.

    Retorno:
        Tupla (filas, total).
    """
    qry = (
        RutaPoolDia.query.filter(
            RutaPoolDia.fecha == fecha,
            RutaPoolDia.deleted_at.is_(None),
        )
        .options(
            *_iniciador_operativo_joinedload_options(),
            joinedload(RutaPoolDia.domicilio).joinedload(Domicilio.distrito),
            joinedload(RutaPoolDia.domicilio).joinedload(Domicilio.rubro),
            joinedload(RutaPoolDia.domicilio).joinedload(Domicilio.calle_catalogo),
            joinedload(RutaPoolDia.distrito),
            joinedload(RutaPoolDia.rubro),
            joinedload(RutaPoolDia.ruta_trabajo),
            joinedload(RutaPoolDia.usuario),
        )
        .order_by(RutaPoolDia.id.desc())
    )

    if turno_id is not None:
        qry = qry.filter(RutaPoolDia.turno_id == turno_id)

    if distrito_id is not None:
        qry = qry.filter(RutaPoolDia.distrito_id == distrito_id)
    if rubro_id is not None:
        qry = qry.filter(RutaPoolDia.rubro_id == rubro_id)
    if ruta_trabajo_id is not None:
        qry = qry.filter(RutaPoolDia.ruta_trabajo_id == ruta_trabajo_id)
    if estado:
        qry = qry.filter(RutaPoolDia.estado == estado)

    if q and q.strip():
        term = f"%{q.strip()}%"
        qry = qry.join(Domicilio, Domicilio.id == RutaPoolDia.domicilio_id).filter(
            or_(
                Domicilio.calle.like(term),
                Domicilio.calle_normalizada.like(term),
                Domicilio.calle_raw.like(term),
                Domicilio.numero.like(term),
            )
        )

    total = qry.order_by(None).count()
    offset = (page - 1) * per_page
    items = qry.offset(offset).limit(per_page).all()
    return items, total


def create_ruta_pool_dia_entry(
    *,
    fecha,
    turno_id: int | None,
    usuario_id: int,
    iniciador_ruta_id: int,
    origen_tipo: str | None = None,
    actuacion_id: int | None = None,
    observacion: str | None = None,
    ruta_trabajo_id: int | None = None,
) -> RutaPoolDia:
    """
    Crea o reutiliza entrada EN_POOL para un iniciador elegible (idempotente por ruta).

    Parámetros:
        fecha, turno_id: clave del día.
        usuario_id: auditoría.
        iniciador_ruta_id: iniciador planificable.
        origen_tipo, actuacion_id, observacion: metadata opcional.
        ruta_trabajo_id: ruta destino (OPER-RUTA.6H).

    Retorno:
        ``RutaPoolDia`` persistido.

    Errores:
        LookupError, RuntimeError.
    """
    if ruta_trabajo_id is None:
        iniciador = (
            IniciadorRuta.query.options(
                joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
                joinedload(IniciadorRuta.relevamiento),
            )
            .filter(IniciadorRuta.id == iniciador_ruta_id)
            .first()
        )
        if not iniciador:
            raise LookupError("Iniciador no encontrado")

        validar_iniciador_elegible_para_pool(
            iniciador,
            fecha=fecha,
            turno_id=turno_id,
            ruta_trabajo_id=ruta_trabajo_id,
        )
        origen = infer_origen_tipo_para_iniciador(iniciador, origen_tipo)
        domicilio_id, distrito_id, rubro_id = _resolve_snapshot_from_iniciador(iniciador)

        row = RutaPoolDia(
            fecha=fecha,
            turno_id=turno_id,
            usuario_id=usuario_id,
            origen_tipo=origen,
            iniciador_ruta_id=int(iniciador.id),
            actuacion_id=actuacion_id or iniciador.actuacion_id,
            domicilio_id=domicilio_id,
            distrito_id=distrito_id,
            rubro_id=rubro_id,
            ruta_trabajo_id=ruta_trabajo_id,
            estado="EN_POOL",
            observacion=(observacion or "").strip() or None,
        )
        db.session.add(row)
        db.session.commit()
        return row

    return ensure_pool_en_pool_para_ruta(
        iniciador_ruta_id=int(iniciador_ruta_id),
        fecha=fecha,
        ruta_trabajo_id=int(ruta_trabajo_id),
        turno_id=turno_id,
        usuario_id=usuario_id,
        origen_tipo=origen_tipo,
        actuacion_id=actuacion_id,
        observacion=observacion,
        commit=True,
    )


def ensure_pool_en_pool_para_ruta(
    *,
    iniciador_ruta_id: int,
    fecha,
    ruta_trabajo_id: int,
    turno_id: int | None = None,
    usuario_id: int | None = None,
    origen_tipo: str | None = None,
    actuacion_id: int | None = None,
    observacion: str | None = None,
    commit: bool = True,
) -> RutaPoolDia:
    """
    Garantiza exactamente una fila EN_POOL para iniciador + fecha + ruta (OPER-RUTA.6I).

    Parámetros:
        iniciador_ruta_id, fecha, ruta_trabajo_id: clave operativa.
        turno_id, usuario_id, origen_tipo, actuacion_id, observacion: metadata pool.
        commit: si True hace commit al final.

    Retorno:
        Fila EN_POOL existente, reactivada o creada.

    Errores:
        LookupError, RuntimeError (pool activo en otra ruta).
    """
    ruta = RutaTrabajo.query.get(int(ruta_trabajo_id))
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")

    iniciador = (
        IniciadorRuta.query.options(
            joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
            joinedload(IniciadorRuta.relevamiento),
        )
        .filter(IniciadorRuta.id == int(iniciador_ruta_id))
        .first()
    )
    if not iniciador:
        raise LookupError("Iniciador no encontrado")

    now = datetime.utcnow()
    pools_activos = (
        RutaPoolDia.query.filter(
            RutaPoolDia.iniciador_ruta_id == int(iniciador_ruta_id),
            RutaPoolDia.deleted_at.is_(None),
            RutaPoolDia.estado.in_(_ESTADOS_POOL_ACTIVOS),
        )
        .all()
    )
    for pool in pools_activos:
        if not pool_row_bloquea_planificacion(pool):
            continue
        dup_ruta_id = pool.ruta_trabajo_id
        if dup_ruta_id is not None and int(dup_ruta_id) == int(ruta_trabajo_id):
            if pool.estado == "EN_POOL":
                pool.fecha = fecha
                pool.updated_at = now
                if commit:
                    db.session.commit()
                return pool
            continue
        if dup_ruta_id is None or int(dup_ruta_id) != int(ruta_trabajo_id):
            raise RuntimeError(_MSG_POOL_OTRA_RUTA)

    orphan = (
        RutaPoolDia.query.filter(
            RutaPoolDia.iniciador_ruta_id == int(iniciador_ruta_id),
            RutaPoolDia.ruta_trabajo_id.is_(None),
            RutaPoolDia.deleted_at.is_(None),
            RutaPoolDia.estado == "EN_POOL",
        )
        .order_by(RutaPoolDia.id.desc())
        .first()
    )
    if orphan is not None:
        orphan.ruta_trabajo_id = int(ruta_trabajo_id)
        orphan.fecha = fecha
        orphan.updated_at = now
        if commit:
            db.session.commit()
        return orphan

    validar_iniciador_elegible_para_pool(
        iniciador,
        fecha=fecha,
        turno_id=turno_id,
        ruta_trabajo_id=int(ruta_trabajo_id),
    )
    origen = infer_origen_tipo_para_iniciador(iniciador, origen_tipo)
    domicilio_id, distrito_id, rubro_id = _resolve_snapshot_from_iniciador(iniciador)
    uid = int(usuario_id) if usuario_id is not None else get_current_user_id_or_fallback()

    row = RutaPoolDia(
        fecha=fecha,
        turno_id=turno_id,
        usuario_id=uid,
        origen_tipo=origen,
        iniciador_ruta_id=int(iniciador.id),
        actuacion_id=actuacion_id or iniciador.actuacion_id,
        domicilio_id=domicilio_id,
        distrito_id=distrito_id,
        rubro_id=rubro_id,
        ruta_trabajo_id=int(ruta_trabajo_id),
        estado="EN_POOL",
        observacion=(observacion or "").strip() or None,
    )
    db.session.add(row)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return row


def devolver_iniciador_al_pool_ruta(
    *,
    iniciador_ruta_id: int,
    ruta_trabajo_id: int,
    ruta_item_id: int | None = None,
    fecha=None,
    turno_id: int | None = None,
    usuario_id: int | None = None,
) -> RutaPoolDia:
    """
    Devuelve un iniciador al pool EN_POOL de la misma ruta tras quitar ítem o eliminar grupo.

    Idempotente: reutiliza fila ASIGNADO_A_RUTA vinculada al ítem o ``ensure_pool_en_pool_para_ruta``.
    """
    ruta = RutaTrabajo.query.get(int(ruta_trabajo_id))
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")
    pool_fecha = fecha or ruta.fecha
    now = datetime.utcnow()

    if ruta_item_id is not None:
        row = RutaPoolDia.query.filter(
            RutaPoolDia.ruta_item_id == int(ruta_item_id),
            RutaPoolDia.estado == "ASIGNADO_A_RUTA",
            RutaPoolDia.deleted_at.is_(None),
        ).first()
        if row is not None:
            row.estado = "EN_POOL"
            row.ruta_item_id = None
            row.ruta_trabajo_id = int(ruta_trabajo_id)
            if pool_fecha is not None:
                row.fecha = pool_fecha
            row.updated_at = now
            db.session.add(row)
            return row

    return ensure_pool_en_pool_para_ruta(
        iniciador_ruta_id=int(iniciador_ruta_id),
        fecha=pool_fecha,
        ruta_trabajo_id=int(ruta_trabajo_id),
        turno_id=turno_id,
        usuario_id=usuario_id,
        commit=False,
    )


def descartar_ruta_pool_dia_entry(*, pool_id: int) -> RutaPoolDia:
    """
    Baja lógica de entrada del pool (DESCARTADO).

    Parámetros:
        pool_id: id de fila.

    Retorno:
        Fila actualizada.

    Errores:
        LookupError, RuntimeError si ya ASIGNADO_A_RUTA.
    """
    row = RutaPoolDia.query.filter(
        RutaPoolDia.id == pool_id,
        RutaPoolDia.deleted_at.is_(None),
    ).first()
    if not row:
        raise LookupError("Entrada de pool no encontrada")
    if row.estado == "ASIGNADO_A_RUTA":
        raise RuntimeError("No se puede descartar una entrada ya asignada a ruta")
    if row.estado == "DESCARTADO":
        return row

    now = datetime.utcnow()
    row.estado = "DESCARTADO"
    row.deleted_at = now
    row.updated_at = now
    db.session.commit()
    return row


_ESTADOS_RUTA_NO_LIBERABLE = ("PUBLICADA", "EN_CURSO", "CERRADA")


def liberar_ruta_pool_dia_entry(*, pool_id: int) -> RutaPoolDia:
    """
    Libera un pendiente del pool/ruta borrador de forma transaccional.

    Parámetros:
        pool_id: fila activa del pool.

    Retorno:
        Fila con estado ``DESCARTADO``.

    Errores:
        LookupError: pool inexistente.
        RuntimeError: ruta publicada, con OT, o ítem en grupo sin eliminar primero.
    """
    row = (
        RutaPoolDia.query.filter(
            RutaPoolDia.id == pool_id,
            RutaPoolDia.deleted_at.is_(None),
        )
        .options(joinedload(RutaPoolDia.ruta_trabajo))
        .first()
    )
    if not row:
        raise LookupError("Entrada de pool no encontrada")
    if row.estado == "DESCARTADO":
        return row

    if row.estado == "EN_POOL":
        if row.ruta_item_id is not None:
            raise RuntimeError(
                "Primero eliminá el ítem del grupo. Luego podrás sacarlo del pool."
            )
        return descartar_ruta_pool_dia_entry(pool_id=pool_id)

    if row.estado != "ASIGNADO_A_RUTA":
        raise RuntimeError("Estado de pool no liberable")

    if not row.ruta_trabajo_id or not row.ruta_item_id:
        raise RuntimeError("Entrada de pool inconsistente con la ruta")

    ruta = row.ruta_trabajo or RutaTrabajo.query.get(row.ruta_trabajo_id)
    estado_ruta = (ruta.estado_ruta or "").upper() if ruta else ""
    if estado_ruta in _ESTADOS_RUTA_NO_LIBERABLE:
        raise RuntimeError("No se puede sacar porque la ruta ya fue publicada o iniciada.")
    if estado_ruta != "BORRADOR":
        raise RuntimeError("No se puede liberar en el estado actual de la ruta.")

    item = RutaItem.query.filter(
        RutaItem.id == row.ruta_item_id,
        RutaItem.deleted_at.is_(None),
    ).first()
    if item is None:
        now = datetime.utcnow()
        row.estado = "DESCARTADO"
        row.deleted_at = now
        row.updated_at = now
        db.session.commit()
        return row

    if item.orden_trabajo_id is not None:
        raise RuntimeError(
            "No se puede sacar porque ya tiene Orden de Trabajo asignada. Primero gestioná la ruta."
        )
    if (item.estado_ejecucion or "").upper() == "REALIZADO":
        raise RuntimeError("No se puede sacar porque el ítem ya tiene ejecución registrada.")

    from app.domains.rutas_trabajo.services.ruta_items_service import soft_delete_ruta_item

    soft_delete_ruta_item(ruta_id=int(row.ruta_trabajo_id), item_id=int(item.id))
    refreshed = RutaPoolDia.query.filter(
        RutaPoolDia.id == pool_id,
        RutaPoolDia.deleted_at.is_(None),
    ).first()
    if refreshed is None:
        raise LookupError("Entrada de pool no encontrada tras liberar ítem")
    if refreshed.estado == "DESCARTADO":
        return refreshed
    return descartar_ruta_pool_dia_entry(pool_id=pool_id)


def revert_pool_si_item_eliminado(*, ruta_item_id: int) -> RutaPoolDia | None:
    """
    Si un ítem de ruta BORRADOR se elimina, la fila de pool vuelve a EN_POOL.

    Parámetros:
        ruta_item_id: id del ítem soft-deleted.

    Retorno:
        Fila revertida o None si no había pool vinculado.
    """
    row = RutaPoolDia.query.filter(
        RutaPoolDia.ruta_item_id == ruta_item_id,
        RutaPoolDia.estado == "ASIGNADO_A_RUTA",
        RutaPoolDia.deleted_at.is_(None),
    ).first()
    if not row:
        return None
    ruta = row.ruta_trabajo
    now = datetime.utcnow()
    row.estado = "EN_POOL"
    row.ruta_item_id = None
    if row.ruta_trabajo_id is None and ruta is not None:
        row.ruta_trabajo_id = int(ruta.id)
    if ruta is not None and ruta.fecha is not None:
        row.fecha = ruta.fecha
    row.updated_at = now
    return row
