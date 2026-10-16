from __future__ import annotations

from typing import Any

from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    ActaInspeccionItem,
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Inspeccion,
    Relevamiento,
    RutaGrupo,
    RutaGrupoInspector,
    RutaItem,
    RutaTrabajo,
)

from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_detalle,
)
from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
    tipo_actuacion_esperado_para_iniciador,
)
from app.domains.media.services.media_ruta_item_resumen_service import build_media_resumen_ruta_item


def get_completar_trabajo_detalle(*, ruta_item_id: int) -> dict[str, Any]:
    """
    Detalle para armar el formulario Completar trabajo (fase 1).

    Incluye la fila resumida, inspectores del grupo de ruta (solo lectura en UI) y políticas UX.

    Parámetros:
        ruta_item_id: ítem de ruta con actuación.

    Retorno:
        Dict con `row`, `inspectores_grupo`, `ui_policy`.

    Errores:
        LookupError: ítem inexistente o sin actuación.
        ValueError: ruta no PUBLICADA, ítem eliminado, estado no admitido o fotos cerradas por “finalizar por ahora”.
    """
    item = (
        RutaItem.query.filter(RutaItem.id == ruta_item_id)
        .options(
            joinedload(RutaItem.ruta_trabajo),
            joinedload(RutaItem.actuacion).options(
                joinedload(Actuaciones.orden_trabajo),
                joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
                joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
                selectinload(Actuaciones.inspector),
                joinedload(Actuaciones.inspeccion)
                .selectinload(Inspeccion.checklist_items)
                .joinedload(ActaInspeccionItem.item),
            ),
            joinedload(RutaItem.iniciador_ruta).options(
                joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
                joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
                joinedload(IniciadorRuta.notificacion),
            ),
            joinedload(RutaItem.ruta_grupo)
            .joinedload(RutaGrupo.grupo_inspectores)
            .joinedload(RutaGrupoInspector.inspector),
        )
        .first()
    )
    if not item:
        raise LookupError("Ruta ítem no encontrado")
    if not item.actuacion_id or item.actuacion is None:
        raise LookupError("El ítem no tiene actuación asociada")

    ruta = item.ruta_trabajo
    if not ruta or ruta.estado_ruta != "PUBLICADA":
        raise ValueError("La ruta debe estar PUBLICADA para ver el detalle de completar trabajo.")
    if item.deleted_at is not None:
        raise ValueError("El ítem está eliminado.")

    estado = item.estado_ruta_item
    if estado not in ("EN_PROCESO", "FINALIZADO"):
        raise ValueError(
            f"El ítem no está EN_PROCESO (estado actual: {item.estado_ruta_item})."
        )
    if estado == "FINALIZADO" and getattr(item, "fotos_pendientes_cerradas_at", None) is not None:
        raise ValueError(
            "Las evidencias pendientes fueron cerradas (finalizar por ahora); "
            "usá Mis trabajos para cargas adicionales."
        )

    grupo = item.ruta_grupo
    inspectores_grupo: list[dict[str, Any]] = []
    if grupo and grupo.grupo_inspectores:
        for gi in sorted(grupo.grupo_inspectores, key=lambda x: x.id):
            ins = gi.inspector
            inspectores_grupo.append(
                {
                    "ruta_grupo_inspector_id": gi.id,
                    "inspector_id": gi.inspector_id,
                    "nombre": ins.nombre if ins else None,
                    "legajo": ins.legajo if ins else None,
                }
            )

    ini = item.iniciador_ruta
    tipo_esperado: str | None = None
    if ini and ini.tipo_iniciador:
        try:
            tipo_esperado = tipo_actuacion_esperado_para_iniciador(ini.tipo_iniciador)
        except KeyError:
            tipo_esperado = None

    detalle = ruta_item_completar_trabajo_detalle(
        item,
        inspectores_grupo=inspectores_grupo,
        tipo_actuacion_esperado=tipo_esperado,
    )
    media_resumen = build_media_resumen_ruta_item(int(item.id))
    detalle["media_resumen"] = media_resumen

    if estado == "FINALIZADO":
        pending_total = int(media_resumen.get("evidencias_pendientes_total") or 0)
        tiene_oblig = bool(media_resumen.get("tiene_evidencias_pendientes"))
        flag_abiertas = bool(getattr(item, "evidencias_pendientes_abiertas", False))
        solo_fotos = flag_abiertas or pending_total > 0 or tiene_oblig
        detalle["ui_policy"] = {
            **detalle.get("ui_policy", {}),
            "solo_evidencias_pendientes": solo_fotos,
            "cierre_alfanumerico_readonly": True,
        }
        detalle["row"] = {
            **detalle["row"],
            "media_resumen": media_resumen,
            "trabajo_guardado_evidencias_pendientes": solo_fotos,
        }

    return detalle
