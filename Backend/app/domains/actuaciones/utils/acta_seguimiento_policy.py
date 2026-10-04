from __future__ import annotations

from app.domains.actuaciones.services.completar_trabajo_contraproducencia import ContrapBucket
from app.models import Actuaciones, IniciadorRuta, Inspeccion

TIPOS_INICIADOR_SOLICITUD_CARNET = frozenset({"RELEVAMIENTO", "DENUNCIA"})


def labra_acta_inspeccion_en_cierre(acta_inspeccion_num: str | None) -> bool:
    """True si el cierre incluye número de acta de inspección."""
    return bool(acta_inspeccion_num and str(acta_inspeccion_num).strip())


def contexto_solicitud_carnet_relevamiento(
    ini: IniciadorRuta,
    *,
    bucket: ContrapBucket,
    labra_inspeccion: bool,
) -> bool:
    """
    Bloque de solicitud de carnet aplica en Relevamiento o Denuncia con visita realizada y acta de inspección.
    """
    if bucket != ContrapBucket.NONE or not labra_inspeccion:
        return False
    return (ini.tipo_iniciador or "").strip() in TIPOS_INICIADOR_SOLICITUD_CARNET


def contexto_subsanacion_reinspeccion_notificacion(
    ini: IniciadorRuta,
    *,
    bucket: ContrapBucket,
    labra_inspeccion: bool,
) -> bool:
    """
    Bloque de subsanación aplica en Reinspección por Notificación con notificación origen válida.
    """
    if bucket != ContrapBucket.NONE or not labra_inspeccion:
        return False
    if (ini.tipo_iniciador or "").strip() != "REINSPECCION_NOTIFICACION":
        return False
    return ini.notificacion_id is not None


def actuacion_tiene_inspeccion_persistida(act: Actuaciones) -> bool:
    """True si la actuación tiene acta de inspección persistida en BD."""
    insp: Inspeccion | None = getattr(act, "inspeccion", None)
    if insp is None and getattr(act, "id", None):
        from app.database import db

        insp = Inspeccion.query.filter(Inspeccion.actuacion_id == int(act.id)).first()
    if insp is None:
        return False
    num = getattr(insp, "numero_acta", None)
    return bool(num and str(num).strip())


def contexto_solicitud_carnet_gestion(
    ini: IniciadorRuta | None,
    act: Actuaciones,
) -> bool:
    """
    Bloque de carnet en Gestión de Actuaciones: Relevamiento/Denuncia con inspección persistida.
    """
    if ini is None or not actuacion_tiene_inspeccion_persistida(act):
        return False
    return (ini.tipo_iniciador or "").strip() in TIPOS_INICIADOR_SOLICITUD_CARNET


def contexto_subsanacion_gestion(
    ini: IniciadorRuta | None,
    act: Actuaciones,
) -> bool:
    """
    Bloque de subsanación en Gestión: Reinspección por Notificación vía iniciador de ruta.
    """
    if ini is None or not actuacion_tiene_inspeccion_persistida(act):
        return False
    if (ini.tipo_iniciador or "").strip() != "REINSPECCION_NOTIFICACION":
        return False
    return ini.notificacion_id is not None
