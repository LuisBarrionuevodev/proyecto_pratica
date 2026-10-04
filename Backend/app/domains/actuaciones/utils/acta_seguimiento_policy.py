from __future__ import annotations

from app.domains.actuaciones.services.completar_trabajo_contraproducencia import ContrapBucket
from app.models import IniciadorRuta


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
    Bloque de solicitud de carnet aplica en Relevamiento con visita realizada y acta de inspección.
    """
    if bucket != ContrapBucket.NONE or not labra_inspeccion:
        return False
    return (ini.tipo_iniciador or "").strip() == "RELEVAMIENTO"


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
