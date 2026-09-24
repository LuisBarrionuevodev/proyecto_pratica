"""Helpers de circuito y actas para reinspección por oficio (GESTIÓN-FIX.2C)."""

from __future__ import annotations

from app.models import Actuaciones, IniciadorRuta, RutaItem

_TIPOS_INICIADOR_OFICIO: frozenset[str] = frozenset(
    {
        "REINSPECCION_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
        "VERIFICAR_INFORMAR_OFICIO",
    }
)


def actuacion_es_circuito_reinspeccion_oficio(actuacion_id: int) -> bool:
    """
    True si la actuación pertenece al circuito operativo de reinspección por oficio.

    Usa el iniciador operativo resuelto desde la actuación (RutaItem / contexto).

    Parámetros:
        actuacion_id: PK de la actuación.

    Retorno:
        True cuando el iniciador es genérico o subtipo promovido de oficio.
    """
    from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
        resolve_iniciador_operativo_actuacion,
    )

    ini = resolve_iniciador_operativo_actuacion(int(actuacion_id))
    if ini is None:
        return False
    return es_iniciador_reinspeccion_oficio(ini.tipo_iniciador)


def es_iniciador_reinspeccion_oficio(tipo_iniciador: str | None) -> bool:
    """
    True si el iniciador pertenece al circuito operativo de reinspección por oficio.

    Parámetros:
        tipo_iniciador: valor de ``IniciadorRuta.tipo_iniciador``.

    Retorno:
        True para genérico o subtipos promovidos de oficio.
    """
    if not tipo_iniciador:
        return False
    return str(tipo_iniciador).strip().upper() in _TIPOS_INICIADOR_OFICIO


def resolver_item_iniciador_por_actuacion(
    actuacion_id: int,
) -> tuple[Actuaciones, RutaItem, IniciadorRuta]:
    """
    Resuelve actuación, ítem de ruta e iniciador asociados.

    Parámetros:
        actuacion_id: PK de la actuación.

    Retorno:
        Tupla (act, item, ini) del cierre más reciente vinculado.

    Errores:
        LookupError: actuación o relaciones de ruta no encontradas.
        ValueError: la actuación no pertenece al circuito oficio.
    """
    act = Actuaciones.query.get(actuacion_id)
    if act is None:
        raise LookupError("Actuación no encontrada.")

    item = (
        RutaItem.query.filter(
            RutaItem.actuacion_id == actuacion_id,
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    if item is None:
        raise LookupError("La actuación no está vinculada a un ítem de ruta.")

    ini = IniciadorRuta.query.get(item.iniciador_ruta_id)
    if ini is None:
        raise LookupError("Iniciador de ruta no encontrado.")

    if not es_iniciador_reinspeccion_oficio(ini.tipo_iniciador):
        raise ValueError("La actuación no pertenece al circuito de reinspección por oficio.")

    return act, item, ini


def actuacion_tiene_actas_inspeccion_normal(act: Actuaciones) -> bool:
    """
    True si la actuación tiene actas o datos persistidos del flujo de inspección normal.

    Parámetros:
        act: actuación con relaciones cargadas o lazy.

    Retorno:
        True si hay inspección, notificación con motivos, comprobación, clausura o decomiso.
    """
    if getattr(act, "inspeccion", None) is not None:
        return True
    if act.notificacion_id:
        notif = act.notificacion
        if notif and getattr(notif, "motivos", None):
            if len(notif.motivos or []) > 0:
                return True
    if act.comprobacion_id:
        return True
    if getattr(act, "clausura", None) is not None:
        return True
    if getattr(act, "decomiso", None) is not None:
        return True
    return False


def actuacion_tiene_evidencia_operativa_real(act: Actuaciones) -> bool:
    """
    True si la actuación representa un intento con resultado o actas reales (no shell de publicación).

    Parámetros:
        act: actuación persistida.

    Retorno:
        True si hay contraproducencia, cumplimiento oficio o actas de visita.
    """
    if (act.contraproducencia or "").strip():
        return True
    if getattr(act, "resultado_cumplimiento_oficio", None) is not None:
        if str(act.resultado_cumplimiento_oficio).strip():
            return True
    return actuacion_tiene_actas_inspeccion_normal(act)


def actuacion_tiene_actas_visita_reinspeccion_notificacion(act: Actuaciones) -> bool:
    """
    True si la actuación de reinspección por notificación tiene actas labradas en la visita.

    No cuenta ``notificacion_id`` cuando es la notificación de origen del iniciador (referencial).

    Parámetros:
        act: actuación con relaciones cargadas o lazy.

    Retorno:
        True si hay inspección, comprobación, clausura o decomiso de la visita.
    """
    if getattr(act, "inspeccion", None) is not None:
        return True
    if act.comprobacion_id:
        return True
    if getattr(act, "clausura", None) is not None:
        return True
    if getattr(act, "decomiso", None) is not None:
        return True
    return False


def notificacion_es_origen_reinspeccion_notificacion_en_actuacion(
    act: Actuaciones,
    *,
    notificacion_id: int | None = None,
    ini: IniciadorRuta | None = None,
) -> bool:
    """
    True si la notificación indicada es la de origen del circuito REINSPECCION_NOTIFICACION.

    Parámetros:
        act: actuación persistida.
        notificacion_id: PK de notificación a evaluar; por defecto ``act.notificacion_id``.
        ini: iniciador operativo; si es None se resuelve desde la actuación.

    Retorno:
        True cuando la FK apunta a la notificación que originó la reinspección.
    """
    nid = notificacion_id if notificacion_id is not None else act.notificacion_id
    if nid is None:
        return False
    if ini is None and act.id is not None:
        from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
            resolve_iniciador_operativo_actuacion,
        )

        ini = resolve_iniciador_operativo_actuacion(int(act.id))
    if ini is None or ini.tipo_iniciador != "REINSPECCION_NOTIFICACION":
        return False
    return ini.notificacion_id is not None and int(ini.notificacion_id) == int(nid)


MSG_SI_A_NO_CON_ACTAS = (
    "Para indicar que no realizó una nueva inspección, primero debe quitar las actas labradas."
)
