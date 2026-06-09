from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_efectivo_para_iniciador,
)
from app.models import Actuaciones, RutaGrupo, RutaItem, RutaTrabajo


def tipo_actuacion_para_iniciador(tipo_iniciador: str) -> str:
    """
    Mapea `IniciadorRuta.tipo_iniciador` al string de `Actuaciones.tipo` alineado al catálogo
    (`CatalogTipoActuacion` / valores usados en grilla).

    Parámetros:
        tipo_iniciador: valor del enum en `iniciador_ruta.tipo_iniciador`.

    Retorno:
        Nombre de tipo de actuación persistible en `actuaciones.tipo`.

    Errores:
        KeyError: si el tipo no está contemplado (no debería ocurrir con datos válidos de DB).
    """
    mapping: dict[str, str] = {
        "RELEVAMIENTO": "INSPECCION",
        "DENUNCIA": "INSPECCION",
        "REINSPECCION_OFICIO": "REINSPECCION",
        "REINSPECCION_NOTIFICACION": "REINSPECCION",
        "VERIFICAR_INFORMAR_OFICIO": "VERIFICAR E INFORMAR",
        "RATIFICACION_CLAUSURA_OFICIO": "RATIFICACION DE CLAUSURA",
        "RATIFICACION_DECOMISO_OFICIO": "RATIFICACION DE DECOMISO",
    }
    if tipo_iniciador not in mapping:
        raise KeyError(f"tipo_iniciador no mapeado a actuación: {tipo_iniciador!r}")
    return mapping[tipo_iniciador]


def publicar_ruta_trabajo(*, ruta_id: int) -> tuple[RutaTrabajo, list[RutaItem]]:
    """
    Publica una ruta en BORRADOR: valida grupos/ítems/OT, crea una actuación mínima por ítem
    activo, actualiza estados y persiste en una única transacción.

    Parámetros:
        ruta_id: identificador de `ruta_trabajo`.

    Retorno:
        Tupla `(ruta, items_activos_actualizados)` tras el commit.

    Errores:
        LookupError: ruta inexistente.
        RuntimeError: reglas de negocio no cumplidas (estado, inspectores, ítems, OT, duplicados,
        tipo de iniciador sin mapeo).
    """
    ruta = RutaTrabajo.query.filter(RutaTrabajo.id == ruta_id).with_for_update().first()
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")

    if ruta.estado_ruta != "BORRADOR":
        raise RuntimeError("La ruta debe estar en estado BORRADOR para publicar")

    grupos = (
        RutaGrupo.query.filter(
            RutaGrupo.ruta_trabajo_id == ruta.id,
            RutaGrupo.deleted_at.is_(None),
        )
        .options(
            joinedload(RutaGrupo.grupo_inspectores),
            joinedload(RutaGrupo.items).joinedload(RutaItem.iniciador_ruta),
            joinedload(RutaGrupo.items).joinedload(RutaItem.orden_trabajo),
        )
        .order_by(RutaGrupo.id.asc())
        .all()
    )

    if not grupos:
        raise RuntimeError("La ruta debe tener al menos un grupo activo para publicar")

    for grupo in grupos:
        n_insp = len(grupo.grupo_inspectores or [])
        if n_insp < 2:
            raise RuntimeError(
                f"El grupo «{grupo.nombre}» debe tener al menos 2 inspectores asignados"
            )
        n_items_activos = sum(1 for it in (grupo.items or []) if it.deleted_at is None)
        if n_items_activos < 1:
            raise RuntimeError(
                f"El grupo «{grupo.nombre}» debe tener al menos un trabajo (ítem) activo"
            )

    items_activos = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.deleted_at.is_(None),
        )
        .options(
            joinedload(RutaItem.iniciador_ruta),
            joinedload(RutaItem.orden_trabajo),
        )
        .order_by(RutaItem.id.asc())
        .all()
    )

    if not items_activos:
        raise RuntimeError("No hay trabajos activos en la ruta para publicar")

    for item in items_activos:
        if item.ruta_grupo_id is None:
            raise RuntimeError(f"El ítem {item.id} no está asignado a un grupo")
        if item.orden_trabajo_id is None:
            raise RuntimeError(f"El ítem {item.id} no tiene Orden de Trabajo cargada")
        if item.estado_ruta_item != "ASIGNADO":
            raise RuntimeError(
                f"El ítem {item.id} no está en estado ASIGNADO (estado actual: {item.estado_ruta_item})"
            )
        if item.actuacion_id is not None:
            raise RuntimeError(f"El ítem {item.id} ya tiene actuación asociada")
        ini = item.iniciador_ruta
        if not ini:
            raise RuntimeError(f"El ítem {item.id} no tiene iniciador asociado")
        if ini.deleted_at is not None:
            raise RuntimeError(f"El iniciador {ini.id} del ítem {item.id} está eliminado")
        if ini.estado_iniciador != "PLANIFICADO":
            raise RuntimeError(
                f"El iniciador {ini.id} debe estar PLANIFICADO para publicar (actual: {ini.estado_iniciador})"
            )

        existente = Actuaciones.query.filter_by(orden_trabajo_id=item.orden_trabajo_id).first()
        if existente:
            raise RuntimeError(
                f"Ya existe una actuación para la OT del ítem {item.id}; no se puede publicar"
            )

    fecha = ruta.fecha
    mes = int(fecha.month)
    anio = int(fecha.year)

    try:
        for item in items_activos:
            ini = item.iniciador_ruta
            assert ini is not None
            try:
                tipo_act = tipo_actuacion_para_iniciador(ini.tipo_iniciador)
            except KeyError as exc:
                raise RuntimeError(str(exc)) from exc

            efectivo = resolve_domicilio_efectivo_para_iniciador(
                ini,
                apply_backfill=True,
                try_sync=True,
            )
            domicilio_publicar = efectivo.domicilio_id or ini.domicilio_id
            if not domicilio_publicar:
                raise RuntimeError(
                    f"El iniciador {ini.id} no tiene domicilio efectivo para publicar la ruta"
                )

            act = Actuaciones(
                fecha=fecha,
                mes=mes,
                anio=anio,
                tipo=tipo_act,
                contraproducencia=None,
                orden_trabajo_id=item.orden_trabajo_id,
                domicilio_id=int(domicilio_publicar),
            )
            db.session.add(act)
            db.session.flush()

            item.actuacion_id = act.id
            item.estado_ruta_item = "EN_PROCESO"
            ini.estado_iniciador = "EN_EJECUCION"

        ruta.estado_ruta = "PUBLICADA"
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return ruta, items_activos
