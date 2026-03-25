from __future__ import annotations

from typing import Any

from sqlalchemy.orm import joinedload, selectinload

from app.models import Actuaciones, Domicilio, IniciadorRuta, Relevamiento, RutaGrupo, RutaGrupoInspector, RutaItem, RutaTrabajo

from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_detalle,
)
from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
    tipo_actuacion_esperado_para_iniciador,
)


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
        ValueError: ruta no PUBLICADA o ítem no EN_PROCESO.
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
            ),
            joinedload(RutaItem.iniciador_ruta).options(
                joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
                joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
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
    if item.estado_ruta_item != "EN_PROCESO":
        raise ValueError(
            f"El ítem no está EN_PROCESO (estado actual: {item.estado_ruta_item})."
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

    return ruta_item_completar_trabajo_detalle(
        item,
        inspectores_grupo=inspectores_grupo,
        tipo_actuacion_esperado=tipo_esperado,
    )
