"""
Reencolado y sincronización operativa Actuaciones ↔ RutaItem ↔ IniciadorRuta (GESTIÓN-FIX.3).

Centraliza la lógica compartida entre Completar Trabajo y correcciones desde Actuaciones.
"""

from __future__ import annotations

from datetime import datetime

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    ContrapBucket,
    motivo_no_realizado_para_ruta_item,
    normalize_contraproducencia,
)
from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
    es_flujo_cumplimiento_oficio,
    es_iniciador_circuito_reinspeccion_oficio,
    reset_iniciador_reinspeccion_oficio_generico,
)
from app.domains.actuaciones.services.oficio_circuito_service import (
    actuacion_tiene_actas_inspeccion_normal,
    actuacion_tiene_actas_visita_reinspeccion_notificacion,
    actuacion_tiene_evidencia_operativa_real,
)
from app.models import Actuaciones, IniciadorRuta, RutaItem, RutaTrabajo

MSG_CONTRA_CON_ACTAS = (
    "Para registrar una contraproducencia, primero debe quitar las actas labradas."
)

MSG_ACTUACION_BLOQUEADA_INTENTO_POSTERIOR = (
    "Esta actuación no puede editarse porque existe un intento posterior asociado al mismo iniciador."
)

MSG_ACTUACION_BLOQUEADA_INTENTO_EN_CURSO = (
    "Esta actuación no puede corregirse porque existe un intento posterior en curso."
)

_ESTADOS_RUTA_ITEM_ABIERTOS = ("PENDIENTE_ASIGNACION", "ASIGNADO", "EN_PROCESO")
_ESTADOS_RUTA_ITEM_PLANIFICADOS = ("PENDIENTE_ASIGNACION", "ASIGNADO")


def resolver_item_e_iniciador(act: Actuaciones) -> tuple[RutaItem | None, IniciadorRuta | None]:
    """
    Obtiene el ítem de ruta vinculado a la actuación y su iniciador.

    Retorno:
        Tupla (ruta_item, iniciador); ambos None si la actuación no proviene de ruta.
    """
    item = (
        RutaItem.query.filter(
            RutaItem.actuacion_id == act.id,
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    if item is None:
        return None, None
    ini = db.session.get(IniciadorRuta, item.iniciador_ruta_id)
    return item, ini


def iniciador_tiene_intentos_historicos_cerrados(iniciador_ruta_id: int) -> bool:
    """
    True si el iniciador ya cerró al menos un ítem NO_REALIZADO con actuación histórica.

    Usado al publicar rutas para no reutilizar actuaciones de intentos anteriores (FIX.5).

    Parámetros:
        iniciador_ruta_id: PK del iniciador.

    Retorno:
        False si no hay ítems finalizados sin realizar con actuación vinculada.
    """
    return (
        db.session.query(RutaItem.id)
        .filter(
            RutaItem.iniciador_ruta_id == int(iniciador_ruta_id),
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "NO_REALIZADO",
            RutaItem.actuacion_id.isnot(None),
        )
        .limit(1)
        .first()
        is not None
    )


def ruta_item_es_intento_posterior_bloqueante(item: RutaItem) -> bool:
    """
    True si el ítem representa un reintento iniciado o finalizado (FIX.9).

    Un ítem solo planificado (publicado sin ejecución real) no bloquea la actuación anterior.

    Parámetros:
        item: ítem de ruta posterior al intento evaluado.

    Retorno:
        True si debe considerarse intento posterior real.
    """
    return motivo_bloqueo_intento_posterior_item(item) is not None


def motivo_bloqueo_intento_posterior_item(item: RutaItem) -> str | None:
    """
    Mensaje de bloqueo si el ítem posterior impide editar/corregir el intento anterior.

    Parámetros:
        item: ítem de ruta evaluado.

    Retorno:
        Mensaje de bloqueo o None si el ítem no bloquea.
    """
    if item.deleted_at is not None:
        return None

    estado_item = (item.estado_ruta_item or "").strip().upper()
    estado_ejec = (item.estado_ejecucion or "").strip().upper() if item.estado_ejecucion else ""

    if estado_item == "FINALIZADO" or estado_ejec in ("REALIZADO", "NO_REALIZADO"):
        return MSG_ACTUACION_BLOQUEADA_INTENTO_POSTERIOR

    if item.ejecutado_at is not None:
        return MSG_ACTUACION_BLOQUEADA_INTENTO_EN_CURSO

    if item.actuacion_id is not None:
        act = db.session.get(Actuaciones, int(item.actuacion_id))
        if act is not None and actuacion_tiene_evidencia_operativa_real(act):
            if estado_item == "EN_PROCESO":
                return MSG_ACTUACION_BLOQUEADA_INTENTO_EN_CURSO
            return MSG_ACTUACION_BLOQUEADA_INTENTO_POSTERIOR

    return None


def ruta_item_es_reintento_planificado_cancelable(item: RutaItem) -> bool:
    """
    True si el ítem posterior puede anularse al corregir el intento anterior.

    Parámetros:
        item: ítem de ruta del reintento.

    Retorno:
        False si ya bloquea o no es un reintento planificado.
    """
    if item.deleted_at is not None:
        return False
    if ruta_item_es_intento_posterior_bloqueante(item):
        return False
    estado_item = (item.estado_ruta_item or "").strip().upper()
    if estado_item in _ESTADOS_RUTA_ITEM_PLANIFICADOS:
        return True
    if estado_item == "EN_PROCESO" and item.actuacion_id is not None:
        act = db.session.get(Actuaciones, int(item.actuacion_id))
        if act is None or not actuacion_tiene_evidencia_operativa_real(act):
            return True
    return False


def _items_posteriores_mismo_iniciador(item: RutaItem) -> list[RutaItem]:
    """Ítems posteriores activos del mismo iniciador."""
    return (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == int(item.iniciador_ruta_id),
            RutaItem.id > int(item.id),
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.asc())
        .all()
    )


def actuacion_bloqueada_por_intento_posterior(actuacion_id: int) -> tuple[bool, str | None]:
    """
    Indica si una actuación quedó histórica por un intento posterior real del mismo iniciador.

    Política FIX.9: bloquea solo si hay reintento iniciado o finalizado, no por mera planificación.

    Parámetros:
        actuacion_id: PK de la actuación evaluada.

    Retorno:
        Tupla ``(bloqueada, motivo)``; motivo None si es editable.
    """
    item = (
        RutaItem.query.filter(
            RutaItem.actuacion_id == int(actuacion_id),
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.asc())
        .first()
    )
    if item is None:
        return False, None

    posteriores = _items_posteriores_mismo_iniciador(item)
    for posterior in posteriores:
        motivo = motivo_bloqueo_intento_posterior_item(posterior)
        if motivo:
            return True, motivo
    return False, None


def assert_actuacion_editable_sin_intento_posterior(actuacion_id: int) -> None:
    """
    Valida que la actuación no esté supersedida por un intento posterior.

    Errores:
        ValueError: si existe un ``RutaItem`` posterior con actuación del mismo iniciador.
    """
    bloqueada, motivo = actuacion_bloqueada_por_intento_posterior(actuacion_id)
    if bloqueada:
        raise ValueError(motivo or MSG_ACTUACION_BLOQUEADA_INTENTO_POSTERIOR)


def build_actuacion_editable_flags_por_actuacion_id(
    act_ids: list[int],
) -> dict[int, dict[str, object]]:
    """
    Precarga flags de edición por actuación para listados sin N+1.

    Parámetros:
        act_ids: ids de actuaciones del page.

    Retorno:
        Mapa ``actuacion_id`` → ``{actuacion_editable, motivo_bloqueo_edicion}``.
    """
    if not act_ids:
        return {}
    base: dict[int, dict[str, object]] = {
        int(i): {"actuacion_editable": True, "motivo_bloqueo_edicion": None} for i in act_ids
    }
    items = (
        RutaItem.query.filter(
            RutaItem.actuacion_id.in_(act_ids),
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.asc())
        .all()
    )
    act_to_item: dict[int, RutaItem] = {}
    for ri in items:
        if ri.actuacion_id is None:
            continue
        key = int(ri.actuacion_id)
        if key not in act_to_item:
            act_to_item[key] = ri
    if not act_to_item:
        return base
    for aid in act_to_item:
        bloqueada, motivo = actuacion_bloqueada_por_intento_posterior(int(aid))
        if bloqueada:
            base[int(aid)] = {
                "actuacion_editable": False,
                "motivo_bloqueo_edicion": motivo or MSG_ACTUACION_BLOQUEADA_INTENTO_POSTERIOR,
            }
    return base


def iniciador_tiene_item_abierto_en_ruta_operativa(
    iniciador_id: int,
    *,
    excluir_ruta_item_id: int | None = None,
) -> bool:
    """
    True si el iniciador tiene otro ítem no finalizado en ruta PUBLICADA o EN_CURSO.

    Parámetros:
        iniciador_id: iniciador a evaluar.
        excluir_ruta_item_id: ítem de la actuación corregida (no cuenta).

    Retorno:
        False si solo quedan ítems finalizados o la ruta no es operativa.
    """
    q = (
        RutaItem.query.join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.iniciador_ruta_id == int(iniciador_id),
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item.in_(_ESTADOS_RUTA_ITEM_ABIERTOS),
            RutaTrabajo.estado_ruta.in_(("PUBLICADA", "EN_CURSO")),
        )
    )
    if excluir_ruta_item_id is not None:
        q = q.filter(RutaItem.id != int(excluir_ruta_item_id))
    return q.first() is not None


def cancelar_reintentos_posteriores_planificados(
    ini: IniciadorRuta,
    *,
    item_origen_id: int,
    now: datetime,
) -> None:
    """
    Anula ítems de reintento planificados (sin ejecución real) al corregir un intento anterior.

    Parámetros:
        ini: iniciador del intento corregido.
        item_origen_id: ítem de la actuación que se corrige (no se toca).
        now: timestamp para ``deleted_at``.

    Side effects:
        Soft-delete de ``RutaItem`` planificados y desvincula actuaciones borrador sin evidencia.
    """
    posteriores = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == int(ini.id),
            RutaItem.id > int(item_origen_id),
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.asc())
        .all()
    )
    for bi in posteriores:
        if not ruta_item_es_reintento_planificado_cancelable(bi):
            motivo = motivo_bloqueo_intento_posterior_item(bi)
            if motivo:
                raise ValueError(motivo)
            continue
        bi.deleted_at = now
        bi.orden_trabajo_id = None
        db.session.add(bi)


def aplicar_reencolado_iniciador(
    ini: IniciadorRuta,
    now: datetime,
    *,
    act: Actuaciones | None = None,
    cerrado_motivo: str | None = None,
) -> None:
    """
    Devuelve un iniciador al backlog planificable con prioridad alta y fecha de reingreso actualizada.

    Parámetros:
        ini: iniciador a reactivar.
        now: timestamp de cierre (UTC naive).
        act: actuación del cierre; define ``fecha_origen`` operativa (mínimo hoy UTC).
        cerrado_motivo: traza opcional (p. ej. OFICIO_NO_CUMPLE); None limpia cierre previo.

    Side effects:
        Modifica ``ini`` en la sesión actual; no hace commit.
    """
    hoy = now.date()
    act_fecha = getattr(act, "fecha", None) if act is not None else None
    fecha_reencolado = act_fecha if act_fecha is not None and act_fecha >= hoy else hoy

    ini.estado_iniciador = "PENDIENTE"
    ini.prioridad = max(int(ini.prioridad or 0), 5)
    ini.cerrado_at = None
    ini.cerrado_motivo = cerrado_motivo
    ini.fecha_origen = fecha_reencolado
    ini.anio = fecha_reencolado.year
    ini.mes = fecha_reencolado.month
    ini.updated_at = now
    db.session.add(ini)


def reencolar_iniciador_si_oficio_no_cumple(
    *,
    ini: IniciadorRuta,
    act: Actuaciones,
    item: RutaItem,
    now: datetime,
) -> None:
    """
    Reinspección por oficio con NO_CUMPLE vuelve a pendientes si no hay otra ruta activa.

    Parámetros:
        ini: iniciador del ítem.
        act: actuación corregida.
        item: ítem de ruta vinculado.
        now: timestamp UTC naive.

    Side effects:
        Puede mutar ``ini`` vía ``aplicar_reencolado_iniciador``.
    """
    if not es_flujo_cumplimiento_oficio(ini.tipo_iniciador):
        return
    if getattr(act, "resultado_cumplimiento_oficio", None) != "NO_CUMPLE":
        return
    if iniciador_tiene_item_abierto_en_ruta_operativa(ini.id, excluir_ruta_item_id=item.id):
        return
    aplicar_reencolado_iniciador(ini, now, act=act, cerrado_motivo="OFICIO_NO_CUMPLE")


def _visita_estaba_realizada(
    act: Actuaciones,
    *,
    contra_anterior: str,
    item: RutaItem | None,
) -> bool:
    """True si la corrección parte de una visita realizada (sin contra previa)."""
    if contra_anterior:
        return False
    if item is not None and (item.estado_ejecucion or "").strip().upper() == "REALIZADO":
        return True
    if actuacion_tiene_actas_inspeccion_normal(act):
        return True
    return False


def aplicar_sincronizacion_tras_establecer_contraproducencia(
    act: Actuaciones,
    *,
    stored_contra: str,
    bucket: ContrapBucket,
    item: RutaItem | None,
    ini: IniciadorRuta | None,
    now: datetime | None = None,
    reencolar: bool = True,
) -> None:
    """
    Alinea RutaItem e IniciadorRuta tras registrar contraproducencia en una visita no realizada.

    Parámetros:
        act: actuación ya mutada (``contraproducencia`` persistida).
        stored_contra: valor normalizado guardado en actuación.
        bucket: clasificación operativa de la contraproducencia.
        item: ítem de ruta de la visita corregida.
        ini: iniciador asociado.
        now: timestamp UTC naive; default ``datetime.utcnow()``.
        reencolar: si False, solo actualiza ítem/motivo (cambio entre contras ya reencoladas).

    Side effects:
        Modifica ``item`` e ``ini`` en la sesión actual; no hace commit.
    """
    ts = now or datetime.utcnow()
    motivo = motivo_no_realizado_para_ruta_item(stored_contra, bucket)

    if item is not None:
        item.estado_ejecucion = "NO_REALIZADO"
        item.estado_ruta_item = "FINALIZADO"
        item.motivo_no_realizado = motivo
        db.session.add(item)

    if ini is None:
        return

    if bucket == ContrapBucket.NO_EXISTE_LOCAL:
        ini.estado_iniciador = "CERRADO_NO_EXISTE_LOCAL"
        ini.cerrado_at = ts
        ini.cerrado_motivo = "NO_EXISTE_LOCAL"
        ini.updated_at = ts
        db.session.add(ini)
        return

    if reencolar and ini.estado_iniciador != "PENDIENTE":
        aplicar_reencolado_iniciador(ini, ts, act=act, cerrado_motivo=None)
    elif reencolar:
        ini.updated_at = ts
        db.session.add(ini)

    if reencolar and es_iniciador_circuito_reinspeccion_oficio(ini.tipo_iniciador):
        reset_iniciador_reinspeccion_oficio_generico(ini)
        db.session.add(ini)


def _actuacion_tiene_actas_bloqueando_contraproducencia(
    act: Actuaciones,
    ini: IniciadorRuta | None,
) -> bool:
    """
    Detecta actas incompatibles con registrar contraproducencia desde PUT.

    En REINSPECCION_NOTIFICACION ignora la notificación de origen (solo actas de visita).
    """
    if ini is not None and ini.tipo_iniciador == "REINSPECCION_NOTIFICACION":
        return actuacion_tiene_actas_visita_reinspeccion_notificacion(act)
    return actuacion_tiene_actas_inspeccion_normal(act)


def procesar_establecimiento_contraproducencia_desde_put(
    act: Actuaciones,
    *,
    contra_anterior: str,
    contra_nueva: str,
    now: datetime | None = None,
) -> None:
    """
    Sincroniza capas operativas al establecer o cambiar contraproducencia desde PUT CRUD.

    Parámetros:
        act: actuación en sesión (payload ya aplicado).
        contra_anterior: valor previo normalizado (trim).
        contra_nueva: valor nuevo normalizado (trim) tras el PUT.
        now: timestamp UTC naive.

    Errores:
        ValueError: actas incompatibles, contraproducencia inválida o transición no permitida.
    """
    if not contra_nueva or contra_nueva == contra_anterior:
        return

    stored_contra, bucket = normalize_contraproducencia(contra_nueva)
    if bucket == ContrapBucket.NONE or not stored_contra:
        return

    item, ini = resolver_item_e_iniciador(act)
    if item is None and ini is None:
        return

    ts = now or datetime.utcnow()
    visita_realizada = _visita_estaba_realizada(act, contra_anterior=contra_anterior, item=item)

    if visita_realizada and _actuacion_tiene_actas_bloqueando_contraproducencia(act, ini):
        raise ValueError(MSG_CONTRA_CON_ACTAS)

    ya_reencolado = bool(contra_anterior) and ini is not None and ini.estado_iniciador == "PENDIENTE"

    aplicar_sincronizacion_tras_establecer_contraproducencia(
        act,
        stored_contra=stored_contra,
        bucket=bucket,
        item=item,
        ini=ini,
        now=ts,
        reencolar=not ya_reencolado,
    )
