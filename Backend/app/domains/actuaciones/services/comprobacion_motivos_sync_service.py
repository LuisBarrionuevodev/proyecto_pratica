from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.catalogs.motivo_comprobacion import (
    get_catalog_motivo_comprobacion_exacto_o_none,
)
from app.models import CatalogMotivoComprobacion, Comprobacion
from app.models.comprobacion import SEPARADOR_TEXTO_MOTIVOS_COMPROBACION
from app.models.comprobacion_motivo import comprobacion_motivo

_MSG_DUPLICADO = "El mismo motivo de comprobación no puede repetirse."
_MSG_CATALOGO = "Motivo de comprobación no existe en catálogo: {nombre}"
_MSG_VACIO = "Si cargás acta de comprobación, elegí al menos un motivo de comprobación."
_MSG_LEGADO_NO_REDUCE = (
    "Esta comprobación ya tiene varios motivos. Enviá motivos_comprobacion con la "
    "lista completa; un único motivo legado no puede reducirla."
)


def _raise_motivos_field_error(field: str, msg: str) -> None:
    """Lanza ValidationError 422 con loc de campo (celda-friendly)."""
    raise ValidationError.from_exception_data(
        "ComprobacionMotivos",
        [
            {
                "type": "value_error",
                "loc": (field,),
                "msg": "Value error",
                "input": None,
                "ctx": {"error": msg},
            }
        ],
    )


def sync_unico_vinculo_desde_texto_historico(comp: Comprobacion) -> None:
    """
    Sincroniza el vínculo relacional 0..1 con el texto legado `comp.motivo`.

    Si el acta ya tiene dos o más motivos relacionales, no reduce la lista:
    lanza ValidationError 422.

    Parámetros:
        comp: comprobación ya persistida.

    Returns:
        None

    Errores:
        ValidationError: intento de reducir varios motivos con payload legado.
    """
    ids_actuales = [int(m.id) for m in (comp.motivos_catalogo or []) if m is not None]
    if len(ids_actuales) >= 2:
        _raise_motivos_field_error("motivos_comprobacion", _MSG_LEGADO_NO_REDUCE)
    catalogo = get_catalog_motivo_comprobacion_exacto_o_none(comp.motivo)
    if catalogo is None:
        if ids_actuales:
            comp.motivos_catalogo = []
        return
    if ids_actuales != [int(catalogo.id)]:
        comp.motivos_catalogo = [catalogo]


def set_motivos_catalogo(comp: Comprobacion, nombres: list[str]) -> None:
    """
    Reemplaza de forma atómica el conjunto de vínculos 1:N.

    Conserva el orden de `nombres` (created_at creciente). No deja restos de
    una edición previa. Cada nombre debe existir en el catálogo y no repetirse.

    Parámetros:
        comp: comprobación destino (con `id`).
        nombres: nombres de catálogo en el orden de carga.

    Returns:
        None

    Errores:
        ValueError: nombre vacío, duplicado o ausente del catálogo.
        ValidationError: lista vacía cuando el caller ya validó acta presente.
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

    comp.motivos_catalogo = []
    db.session.flush()
    if not filas:
        return
    if comp.id is None:
        db.session.flush()
    now = datetime.utcnow()
    for i, fila in enumerate(filas):
        db.session.execute(
            comprobacion_motivo.insert().values(
                comprobacion_id=int(comp.id),
                catalog_motivo_comprobacion_id=int(fila.id),
                created_at=now + timedelta(seconds=i),
                updated_at=now + timedelta(seconds=i),
            )
        )
    db.session.expire(comp, ["motivos_catalogo"])


def apply_motivos_desde_payload(comp: Comprobacion, data: dict) -> None:
    """
    Aplica motivos desde el dict de attach (`motivos` lista o `motivo` legado).

    Si llega `motivos` (lista), reemplaza la relación completa y escribe el
    texto derivado en `comp.motivo`. Si solo llega el escalar, sincroniza 0..1
    sin tocar un conjunto de 2+ (422).

    Parámetros:
        comp: comprobación persistida.
        data: payload de attach (`motivos` y/o `motivo`).

    Returns:
        None

    Errores:
        ValueError: catálogo / duplicados.
        ValidationError: lista vacía con acta, o reducción legado.
    """
    raw_list = data.get("motivos")
    if isinstance(raw_list, list):
        nombres = [(str(x) if x is not None else "").strip() for x in raw_list]
        nombres = [n for n in nombres if n]
        if not nombres:
            _raise_motivos_field_error("motivos_comprobacion", _MSG_VACIO)
        set_motivos_catalogo(comp, nombres)
        derived = SEPARADOR_TEXTO_MOTIVOS_COMPROBACION.join(nombres)
        comp.motivo = derived
        return
    sync_unico_vinculo_desde_texto_historico(comp)
