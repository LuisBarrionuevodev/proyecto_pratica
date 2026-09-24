"""Resolución de rubro operativo según origen (relevamiento, iniciador, domicilio)."""

from __future__ import annotations

from app.models import Actuaciones, Domicilio, IniciadorRuta, RutaItem


def _s(value: str | None) -> str:
    return (value or "").strip()


def _ruta_item_de_actuacion(act: Actuaciones) -> RutaItem | None:
    """Ítem de ruta activo vinculado a la actuación, si existe."""
    if act.id is None:
        return None
    return (
        RutaItem.query.filter(
            RutaItem.actuacion_id == int(act.id),
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )


def _actuacion_visita_realizada(act: Actuaciones) -> bool:
    """
    True si el ítem de ruta vinculado cerró la visita como realizada (no reencolado).

    Parámetros:
        act: actuación publicada desde ruta.

    Retorno:
        True si ``estado_ejecucion == REALIZADO`` en el ``RutaItem`` activo.
    """
    item = _ruta_item_de_actuacion(act)
    if item is None:
        return False
    return (item.estado_ejecucion or "").strip().upper() == "REALIZADO"


def _actuacion_visita_cerrada(act: Actuaciones) -> bool:
    """
    True si la visita operativa del ítem de ruta ya fue cerrada (con o sin actas).

    Incluye cierres por contraproducencia (``estado_ejecucion == NO_REALIZADO``) cuando
    el ítem quedó ``FINALIZADO`` y tiene ``ejecutado_at``.

    Parámetros:
        act: actuación publicada desde ruta.

    Retorno:
        True si el trabajo ya no está pendiente de ejecución en ruta.
    """
    item = _ruta_item_de_actuacion(act)
    if item is None:
        return False
    if (item.estado_ejecucion or "").strip().upper() == "REALIZADO":
        return True
    estado_item = (item.estado_ruta_item or "").strip().upper()
    return estado_item == "FINALIZADO" and item.ejecutado_at is not None


def rubro_id_operativo_para_iniciador(
    iniciador: IniciadorRuta | None,
    dom: Domicilio | None,
    *,
    act: Actuaciones | None = None,
) -> int | None:
    """
    Resuelve el ``rubro_id`` operativo del trabajo (misma prioridad que el nombre).

    Parámetros:
        iniciador: iniciador de ruta vinculado al ítem/actuación.
        dom: domicilio efectivo de la actuación o iniciador.
        act: actuación vinculada (denuncia constatada en visita realizada).

    Retorno:
        ID de rubro operativo o ``None`` si no aplica / no constatado.
    """
    if iniciador and iniciador.tipo_iniciador == "RELEVAMIENTO":
        rel = iniciador.relevamiento
        if rel and rel.rubro_id is not None:
            return int(rel.rubro_id)

    if iniciador and iniciador.tipo_iniciador == "DENUNCIA":
        if act is not None and _actuacion_visita_realizada(act):
            act_dom = getattr(act, "domicilio", None)
            if act_dom and act_dom.rubro_id is not None:
                return int(act_dom.rubro_id)
        return None

    if dom and dom.rubro_id is not None:
        return int(dom.rubro_id)
    if iniciador and iniciador.relevamiento and iniciador.relevamiento.rubro_id is not None:
        return int(iniciador.relevamiento.rubro_id)
    return None


def rubro_nombre_operativo_para_iniciador(
    iniciador: IniciadorRuta | None,
    dom: Domicilio | None,
    *,
    act: Actuaciones | None = None,
) -> str | None:
    """
    Resuelve el rubro mostrado para un trabajo según su origen operativo.

    Prioridad:
    - RELEVAMIENTO: ``relevamiento.rubro`` (canónico; PR7.8 ESQUINA multi-rubro).
    - DENUNCIA: sin rubro de origen; solo rubro constatado en visita realizada
      (``act.domicilio.rubro``). Nunca hereda ``domicilio.rubro`` compartido.
    - Otros tipos: ``domicilio.rubro`` con fallback legacy a ``relevamiento.rubro``.
    - Sin iniciador: solo ``domicilio.rubro``.

    Parámetros:
        iniciador: iniciador de ruta vinculado al ítem/actuación (puede ser None).
        dom: domicilio efectivo de la actuación o iniciador.
        act: actuación vinculada (necesaria para rubro constatado en denuncia).

    Retorno:
        Nombre del rubro o None si no hay fuente / aún no constatado.
    """
    if iniciador and iniciador.tipo_iniciador == "RELEVAMIENTO":
        rel = iniciador.relevamiento
        if rel and rel.rubro:
            nombre = _s(rel.rubro.nombre)
            if nombre:
                return nombre

    if iniciador and iniciador.tipo_iniciador == "DENUNCIA":
        if act is not None and _actuacion_visita_realizada(act):
            act_dom = getattr(act, "domicilio", None)
            if act_dom and act_dom.rubro:
                nombre = _s(act_dom.rubro.nombre)
                if nombre:
                    return nombre
        return None

    rubro_nombre = dom.rubro.nombre if dom and dom.rubro else None
    if not rubro_nombre and iniciador and iniciador.relevamiento and iniciador.relevamiento.rubro:
        rubro_nombre = iniciador.relevamiento.rubro.nombre
    return rubro_nombre or None


def titular_operativo_visible_para_iniciador(
    iniciador: IniciadorRuta | None,
    *,
    act: Actuaciones | None = None,
) -> bool:
    """
    Indica si titular/contrib debe mostrarse en UI operativa del trabajo.

    Relevamientos y denuncias pendientes no heredan titular de ``domicilio`` compartido,
    salvo que el titular esté ya asociado al domicilio de la actuación (constatado/persistido).

    Parámetros:
        iniciador: origen del ítem de ruta.
        act: actuación vinculada al ítem.

    Retorno:
        False para relevamiento/denuncia pendiente o realizada sin titular capturado en la visita.
    """
    if iniciador and iniciador.tipo_iniciador in ("RELEVAMIENTO", "DENUNCIA"):
        if act is None:
            return False
        if not _actuacion_visita_cerrada(act):
            return False
        dom = getattr(act, "domicilio", None)
        return dom is not None and getattr(dom, "contribuyente_id", None) is not None

    if act is not None:
        dom = getattr(act, "domicilio", None)
        if dom is not None and getattr(dom, "contribuyente_id", None) is not None:
            return True
    return True
