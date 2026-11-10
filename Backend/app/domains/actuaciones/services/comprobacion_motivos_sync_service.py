from __future__ import annotations

from app.domains.actuaciones.catalogs.motivo_comprobacion import (
    get_catalog_motivo_comprobacion_exacto_o_none,
)
from app.models import CatalogMotivoComprobacion, Comprobacion

_MSG_DUPLICADO = "El mismo motivo de comprobación no puede repetirse."
_MSG_CATALOGO = "Motivo de comprobación no existe en catálogo: {nombre}"


def sync_unico_vinculo_desde_texto_historico(comp: Comprobacion) -> None:
    """
    Sincroniza el vínculo relacional 0..1 con el texto legado `comp.motivo`.

    Si el texto coincide exactamente con un motivo del catálogo, deja un único
    vínculo a esa fila. Si está vacío, es NULL, PENDIENTE o no coincide, deja
    la relación vacía. Nunca modifica la columna histórica `motivo`.

    Parámetros:
        comp: comprobación ya persistida (necesita `id` para el secondary).

    Returns:
        None

    Errores:
        No lanza por texto desconocido (el legado admite texto libre).
    """
    catalogo = get_catalog_motivo_comprobacion_exacto_o_none(comp.motivo)
    ids_actuales = [int(m.id) for m in (comp.motivos_catalogo or []) if m is not None]
    if catalogo is None:
        if ids_actuales:
            comp.motivos_catalogo = []
        return
    if ids_actuales != [int(catalogo.id)]:
        comp.motivos_catalogo = [catalogo]


def set_motivos_catalogo(comp: Comprobacion, nombres: list[str]) -> None:
    """
    Reemplaza el conjunto de vínculos 1:N (uso futuro MOTIVOS.2 / tests).

    No escribe ni concatena `comp.motivo`. Cada nombre debe existir en el
    catálogo. El mismo motivo no puede repetirse.

    Parámetros:
        comp: comprobación destino.
        nombres: nombres de catálogo (se hace strip).

    Returns:
        None

    Errores:
        ValueError: nombre vacío, duplicado o ausente del catálogo.
    """
    vistos: set[str] = set()
    filas: list[CatalogMotivoComprobacion] = []
    for raw in nombres:
        s = (raw or "").strip()
        if not s:
            raise ValueError("Motivo de comprobación inválido (vacío).")
        if s in vistos:
            raise ValueError(_MSG_DUPLICADO)
        vistos.add(s)
        fila = get_catalog_motivo_comprobacion_exacto_o_none(s)
        if fila is None:
            raise ValueError(_MSG_CATALOGO.format(nombre=s))
        filas.append(fila)
    comp.motivos_catalogo = filas
