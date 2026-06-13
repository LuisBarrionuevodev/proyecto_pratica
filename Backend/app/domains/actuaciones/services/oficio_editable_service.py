"""
Política de edición por oficio (PR4b / STAB-3): un oficio es editable salvo bloqueo operativo.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, exists, select

from app.database import db
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.models import IniciadorRuta, Oficio, RutaItem, RutaTrabajo

_ESTADOS_RUTA_OCULTAN_BANDEJA = ("PUBLICADA", "EN_CURSO")
_ESTADOS_RUTA_BLOQUEAN_EDICION = ("PUBLICADA", "EN_CURSO", "CERRADA")
_ESTADOS_INICIADOR_BLOQUEAN_EDICION = ("CUMPLIDO",) + inactive_estados()
_ESTADOS_EJECUCION_BLOQUEAN_EDICION = ("REALIZADO", "NO_REALIZADO")


def _iniciador_reinspeccion_oficio(oficio_id: int) -> IniciadorRuta | None:
    return (
        IniciadorRuta.query.filter_by(oficio_id=int(oficio_id))
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _ruta_item_vigente_por_iniciador(iniciador_id: int) -> RutaItem | None:
    return (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == int(iniciador_id),
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.desc())
        .first()
    )


def _ruta_item_en_estados(iniciador_id: int, estados_ruta: tuple[str, ...]) -> RutaItem | None:
    return (
        RutaItem.query.join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.iniciador_ruta_id == int(iniciador_id),
            RutaItem.deleted_at.is_(None),
            RutaTrabajo.estado_ruta.in_(estados_ruta),
        )
        .order_by(RutaItem.id.desc())
        .first()
    )


def iniciador_en_ruta_borrador(ini: IniciadorRuta | None) -> bool:
    """
    True si el iniciador tiene un ``RutaItem`` activo en ruta ``BORRADOR``.

    No bloquea edición documental; puede mostrarse como advertencia en UI.
    """
    if ini is None:
        return False
    return _ruta_item_en_estados(ini.id, ("BORRADOR",)) is not None


def iniciador_en_ruta_operativa(ini: IniciadorRuta | None) -> bool:
    """
    True si el iniciador está en ruta ``PUBLICADA`` o ``EN_CURSO``.

    Usado para ocultar filas de bandeja reinspección (STAB-3: ``BORRADOR`` no oculta).
    """
    if ini is None:
        return False
    return _ruta_item_en_estados(ini.id, _ESTADOS_RUTA_OCULTAN_BANDEJA) is not None


def iniciador_en_ruta_activa(ini: IniciadorRuta | None) -> bool:
    """Alias legacy: misma semántica que ``iniciador_en_ruta_operativa`` (STAB-3)."""
    return iniciador_en_ruta_operativa(ini)


def _estado_operativo_y_acciones(
    *,
    editable: bool,
    ini: IniciadorRuta | None,
    ruta_estado: str | None,
    en_ruta_borrador: bool,
) -> tuple[str, list[str]]:
    acciones: list[str] = ["agregar_otro_oficio"]
    if editable:
        acciones.append("editar_oficio")

    if ini is None:
        return "sin_iniciador", acciones
    if en_ruta_borrador:
        return "ruta_borrador", acciones
    if ruta_estado in ("PUBLICADA", "EN_CURSO"):
        return "en_ruta", acciones
    if ruta_estado == "CERRADA":
        return "cerrado", acciones
    if ini.estado_iniciador == "CUMPLIDO":
        return "cumplido", acciones
    if ini.estado_iniciador in inactive_estados():
        return "bloqueado", acciones
    if (ini.estado_iniciador or "").upper() == "PENDIENTE":
        return "pendiente", acciones
    return "pendiente", acciones


def evaluar_editable_oficio(oficio_id: int) -> dict[str, Any]:
    """
    Evalúa si un oficio y su expediente de respuesta pueden editarse/eliminarse.

    Parámetros:
        oficio_id: PK de ``Oficio``.

    Retorno:
        Dict con ``editable``, ``bloqueado_motivo``, campos de ruta/iniciador,
        ``en_ruta_borrador``, ``estado_operativo`` y ``acciones_permitidas``.

    Errores esperados:
        Ninguno; oficio inexistente → ``editable=False``.
    """
    motivos: list[str] = []
    ofi = db.session.get(Oficio, int(oficio_id))
    if ofi is None or ofi.deleted_at is not None:
        return {
            "editable": False,
            "bloqueado_motivo": "Oficio no encontrado o eliminado.",
            "iniciador_id": None,
            "iniciador_estado": None,
            "ruta_item_id": None,
            "ruta_estado": None,
            "estado_ejecucion": None,
            "en_ruta_borrador": False,
            "estado_operativo": "bloqueado",
            "acciones_permitidas": [],
        }

    ini = _iniciador_reinspeccion_oficio(ofi.id)
    ruta_item_id: int | None = None
    ruta_estado: str | None = None
    estado_ejecucion: str | None = None
    iniciador_id: int | None = None
    iniciador_estado: str | None = None
    en_ruta_borrador = False

    if ini is not None:
        iniciador_id = ini.id
        iniciador_estado = ini.estado_iniciador
        if ini.estado_iniciador in _ESTADOS_INICIADOR_BLOQUEAN_EDICION:
            motivos.append(f"Iniciador en estado {ini.estado_iniciador}.")

        ri = _ruta_item_vigente_por_iniciador(ini.id)
        if ri is not None:
            ruta_item_id = ri.id
            estado_ejecucion = ri.estado_ejecucion
            ruta = db.session.get(RutaTrabajo, ri.ruta_trabajo_id)
            if ruta is not None:
                ruta_estado = ruta.estado_ruta
                if ruta.estado_ruta in _ESTADOS_RUTA_BLOQUEAN_EDICION:
                    motivos.append(f"Oficio incorporado en ruta {ruta.estado_ruta}.")
                elif ruta.estado_ruta == "BORRADOR":
                    en_ruta_borrador = True
            if ri.estado_ejecucion in _ESTADOS_EJECUCION_BLOQUEAN_EDICION:
                motivos.append("Trabajo ya ejecutado en ruta.")

    editable = len(motivos) == 0
    estado_operativo, acciones = _estado_operativo_y_acciones(
        editable=editable,
        ini=ini,
        ruta_estado=ruta_estado,
        en_ruta_borrador=en_ruta_borrador,
    )
    return {
        "editable": editable,
        "bloqueado_motivo": motivos[0] if motivos else None,
        "iniciador_id": iniciador_id,
        "iniciador_estado": iniciador_estado,
        "ruta_item_id": ruta_item_id,
        "ruta_estado": ruta_estado,
        "estado_ejecucion": estado_ejecucion,
        "en_ruta_borrador": en_ruta_borrador,
        "estado_operativo": estado_operativo,
        "acciones_permitidas": acciones,
    }


def existe_iniciador_en_ruta_activa_para_actuacion(actuacion_id: int) -> bool:
    """¿Algún REINSPECCION_OFICIO de la actuación está en ruta PUBLICADA/EN_CURSO?"""
    return db.session.query(
        exists(
            select(1)
            .select_from(RutaItem)
            .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
            .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
            .where(
                and_(
                    IniciadorRuta.actuacion_id == int(actuacion_id),
                    IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
                    IniciadorRuta.deleted_at.is_(None),
                    RutaItem.deleted_at.is_(None),
                    RutaTrabajo.estado_ruta.in_(_ESTADOS_RUTA_OCULTAN_BANDEJA),
                )
            )
        )
    ).scalar()
