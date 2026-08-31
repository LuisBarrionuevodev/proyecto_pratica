"""
PR7.15 — Reglas de edición de domicilio desde CRUD Actuaciones (canal CargarActuacion).
"""

from __future__ import annotations

from app.database import db
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.models import Actuaciones, Expediente, IniciadorRuta, Oficio, RutaItem

MSG_REINSPECCION = (
    "La actuación proviene de una reinspección y el domicilio no puede modificarse."
)
MSG_ACTAS_DOCUMENTALES = (
    "El domicilio no puede modificarse porque el acta ya fue utilizada "
    "en un circuito posterior."
)
MSG_SOLO_RELEVAMIENTO = (
    "El domicilio solo puede corregirse en actuaciones generadas desde relevamiento."
)
MSG_RUBRO_BLOQUEADO = "No se puede editar el rubro de esta actuación."

_TIPOS_INICIADOR_BLOQUEAN_DOMICILIO = frozenset(
    {
        "REINSPECCION_NOTIFICACION",
        "REINSPECCION_OFICIO",
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
        "DENUNCIA",
    }
)

_ESTADOS_INICIADOR_USO_OPERATIVO = frozenset({"EN_EJECUCION", "CUMPLIDO"})


def resolve_iniciador_operativo_actuacion(actuacion_id: int) -> IniciadorRuta | None:
    """
    Resuelve el iniciador operativo de una actuación (ruta publicada o vínculo directo).

    Parámetros:
        actuacion_id: id de la actuación.

    Retorno:
        ``IniciadorRuta`` vigente o ``None``.
    """
    from app.domains.actuaciones.presenters.actuacion_presenters import (
        build_iniciador_ruta_por_actuacion_id,
    )

    m = build_iniciador_ruta_por_actuacion_id([int(actuacion_id)])
    ini = m.get(int(actuacion_id))
    if ini is not None and ini.deleted_at is None:
        return ini
    return (
        IniciadorRuta.query.filter(
            IniciadorRuta.actuacion_id == int(actuacion_id),
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _tipo_actuacion_posterior_bloqueado(act: Actuaciones) -> bool:
    tipo = (act.tipo or "").strip().upper()
    if tipo == "REINSPECCION":
        return True
    if "RATIFICACION" in tipo:
        return True
    if "VERIFICAR" in tipo and "INFORMAR" in tipo:
        return True
    return False


def _iniciador_bloquea_domicilio(ini: IniciadorRuta | None) -> str | None:
    if ini is None:
        return None
    tipo = (ini.tipo_iniciador or "").strip().upper()
    if tipo in _TIPOS_INICIADOR_BLOQUEAN_DOMICILIO:
        return MSG_REINSPECCION
    return None


def _iniciador_tiene_ruta_item_activo(iniciador_id: int) -> bool:
    """True si el iniciador está asignado a al menos un ítem de ruta activo."""
    return (
        db.session.query(RutaItem.id)
        .filter(
            RutaItem.iniciador_ruta_id == int(iniciador_id),
            RutaItem.deleted_at.is_(None),
        )
        .limit(1)
        .first()
        is not None
    )


def _iniciador_derivado_en_uso(ini: IniciadorRuta) -> bool:
    """
    Iniciador derivado ya consumido operativamente (en ruta, ejecución o cumplido).

    ``PENDIENTE`` sin ítem de ruta no cuenta como uso.
    """
    estado = (ini.estado_iniciador or "").strip().upper()
    if estado in inactive_estados():
        return False
    if estado in _ESTADOS_INICIADOR_USO_OPERATIVO:
        return True
    return _iniciador_tiene_ruta_item_activo(int(ini.id))


def _notificacion_acta_usada_en_circuito(notificacion_id: int) -> bool:
    """
    Notificación con reinspección completada o iniciador derivado ya en ruta/uso.

    No bloquea por la mera existencia del acta ni por iniciador ``PENDIENTE`` huérfano.
    """
    from app.domains.actuaciones.services.notificacion_plazo_expediente_edit_service import (
        notificacion_tiene_reinspeccion_operativamente_usada,
    )

    nid = int(notificacion_id)
    if notificacion_tiene_reinspeccion_operativamente_usada(nid):
        return True

    inis = IniciadorRuta.query.filter(
        IniciadorRuta.notificacion_id == nid,
        IniciadorRuta.deleted_at.is_(None),
        IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
    ).all()
    return any(_iniciador_derivado_en_uso(ini) for ini in inis)


def _comprobacion_tiene_expediente_u_oficio_activo(comprobacion_id: int) -> bool:
    """Expediente u oficio administrativo activo ligado a la comprobación."""
    cid = int(comprobacion_id)
    if (
        db.session.query(Expediente.id)
        .filter(Expediente.comprobacion_id == cid, Expediente.deleted_at.is_(None))
        .limit(1)
        .first()
        is not None
    ):
        return True
    return (
        db.session.query(Oficio.id)
        .filter(Oficio.comprobacion_id == cid, Oficio.deleted_at.is_(None))
        .limit(1)
        .first()
        is not None
    )


def _comprobacion_iniciador_derivado_en_uso(comprobacion_id: int) -> bool:
    """Iniciador de ruta derivado de la comprobación ya planificado, en curso o cumplido."""
    cid = int(comprobacion_id)
    inis = IniciadorRuta.query.filter(
        IniciadorRuta.comprobacion_id == cid,
        IniciadorRuta.deleted_at.is_(None),
    ).all()
    return any(_iniciador_derivado_en_uso(ini) for ini in inis)


def _acta_usada_en_circuito_posterior_bloquea(act: Actuaciones) -> bool:
    """
    Bloquea solo si notificación/comprobación ya participó de un circuito posterior.

    No bloquea por inspección base ni por actas recién cargadas sin uso operativo.
    """
    if act.notificacion_id is not None and _notificacion_acta_usada_en_circuito(
        int(act.notificacion_id)
    ):
        return True
    if act.comprobacion_id is not None:
        cid = int(act.comprobacion_id)
        if _comprobacion_tiene_expediente_u_oficio_activo(cid):
            return True
        if _comprobacion_iniciador_derivado_en_uso(cid):
            return True
    return False


def puede_editar_domicilio_actuacion(
    act: Actuaciones,
    iniciador: IniciadorRuta | None = None,
) -> tuple[bool, str | None]:
    """
    Indica si el domicilio puede editarse desde CRUD Actuaciones.

    Parámetros:
        act: actuación persistida.
        iniciador: iniciador operativo (opcional; se resuelve si falta).

    Retorno:
        Tupla ``(permitido, motivo_bloqueo)``.
    """
    ini = iniciador if iniciador is not None else resolve_iniciador_operativo_actuacion(int(act.id))

    motivo_ini = _iniciador_bloquea_domicilio(ini)
    if motivo_ini:
        return False, motivo_ini

    if _tipo_actuacion_posterior_bloqueado(act):
        return False, MSG_REINSPECCION

    if _acta_usada_en_circuito_posterior_bloquea(act):
        return False, MSG_ACTAS_DOCUMENTALES

    if ini is None:
        return True, None

    if (ini.tipo_iniciador or "").strip().upper() == "RELEVAMIENTO":
        return True, None

    return False, MSG_SOLO_RELEVAMIENTO


def puede_editar_rubro_actuacion(
    act: Actuaciones,
    iniciador: IniciadorRuta | None = None,
    *,
    editable_override: dict[str, object] | None = None,
) -> tuple[bool, str | None]:
    """
    Indica si el rubro operativo puede editarse desde CRUD Actuaciones.

    Parámetros:
        act: actuación persistida.
        iniciador: iniciador operativo (opcional; se resuelve si falta).
        editable_override: mapa precargado ``{actuacion_editable, motivo_bloqueo_edicion}``.

    Retorno:
        Tupla ``(permitido, motivo_bloqueo)``.
    """
    from app.domains.actuaciones.services.actuacion_reencolado_service import (
        actuacion_bloqueada_por_intento_posterior,
    )

    if editable_override is not None:
        editable = bool(editable_override.get("actuacion_editable", True))
        motivo = editable_override.get("motivo_bloqueo_edicion")
        if motivo is not None:
            motivo = str(motivo)
    else:
        bloqueada, motivo = actuacion_bloqueada_por_intento_posterior(int(act.id))
        editable = not bloqueada

    if not editable:
        return False, motivo or MSG_RUBRO_BLOQUEADO

    ini = iniciador if iniciador is not None else resolve_iniciador_operativo_actuacion(int(act.id))
    tipo_ini = (ini.tipo_iniciador or "").strip().upper() if ini is not None else ""

    if tipo_ini == "DENUNCIA":
        return True, None

    return puede_editar_domicilio_actuacion(act, ini)


def assert_puede_editar_rubro_actuacion(
    act: Actuaciones,
    iniciador: IniciadorRuta | None = None,
    *,
    editable_override: dict[str, object] | None = None,
) -> None:
    """
    Valida edición de rubro; lanza ``ValueError`` con mensaje claro si no aplica.

    Errores:
        ValueError: rubro no editable (FIX.6 / PR7.15).
    """
    puede, motivo = puede_editar_rubro_actuacion(
        act, iniciador, editable_override=editable_override
    )
    if not puede:
        raise ValueError(motivo or MSG_RUBRO_BLOQUEADO)


def assert_puede_editar_domicilio_actuacion(
    act: Actuaciones,
    iniciador: IniciadorRuta | None = None,
) -> None:
    """
    Valida edición de domicilio; lanza ``ValueError`` con mensaje claro si no aplica.

    Errores:
        ValueError: domicilio no editable según PR7.15.
    """
    puede, motivo = puede_editar_domicilio_actuacion(act, iniciador)
    if not puede:
        raise ValueError(motivo or "No se puede editar el domicilio de esta actuación.")

