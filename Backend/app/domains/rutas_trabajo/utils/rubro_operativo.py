"""Resolución de rubro operativo según origen (relevamiento, iniciador, domicilio)."""

from __future__ import annotations

from app.models import Actuaciones, Domicilio, IniciadorRuta, RutaItem


def _s(value: str | None) -> str:
    return (value or "").strip()


def _actuacion_visita_realizada(act: Actuaciones) -> bool:
    """
    True si el ítem de ruta vinculado cerró la visita como realizada (no reencolado).

    Parámetros:
        act: actuación publicada desde ruta.

    Retorno:
        True si ``estado_ejecucion == REALIZADO`` en el ``RutaItem`` activo.
    """
    if act.id is None:
        return False
    item = (
        RutaItem.query.filter(
            RutaItem.actuacion_id == int(act.id),
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    if item is None:
        return False
    return (item.estado_ejecucion or "").strip().upper() == "REALIZADO"


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

    Relevamientos y denuncias pendientes no heredan titular de ``domicilio`` compartido.

    Parámetros:
        iniciador: origen del ítem de ruta.
        act: actuación vinculada al ítem.

    Retorno:
        False para relevamiento/denuncia con visita aún no realizada.
    """
    if iniciador and iniciador.tipo_iniciador in ("RELEVAMIENTO", "DENUNCIA"):
        if act is not None and not _actuacion_visita_realizada(act):
            return False
    return True
