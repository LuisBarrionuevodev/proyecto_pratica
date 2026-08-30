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
)
from app.domains.actuaciones.services.oficio_circuito_service import (
    actuacion_tiene_actas_inspeccion_normal,
)
from app.models import Actuaciones, IniciadorRuta, RutaItem, RutaTrabajo

MSG_CONTRA_CON_ACTAS = (
    "Para registrar una contraproducencia, primero debe quitar las actas labradas."
)

_ESTADOS_RUTA_ITEM_ABIERTOS = ("PENDIENTE_ASIGNACION", "ASIGNADO", "EN_PROCESO")


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

    if visita_realizada and actuacion_tiene_actas_inspeccion_normal(act):
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
