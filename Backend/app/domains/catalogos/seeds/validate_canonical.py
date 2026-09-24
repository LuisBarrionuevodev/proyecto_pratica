"""
Validación post-seed: todos los canónicos existen (no exige COUNT tabla == N).

Qué hace: verifica presencia por clave natural en DB.
Errores: ValueError con lista de faltantes.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.domains.catalogos.canonical.contraproducencias import CONTRAPRODUCENCIAS_CANONICAS
from app.domains.catalogos.canonical.items_inspeccion import ITEMS_INSPECCION_CANONICOS
from app.domains.catalogos.canonical.juzgados import JUZGADOS_CANONICOS
from app.domains.catalogos.canonical.manifest import EXPECTED_COUNTS
from app.domains.catalogos.canonical.motivos import (
    MOTIVOS_COMPROBACION_CANONICOS,
    MOTIVOS_NOTIFICACION_CANONICOS,
)
from app.domains.catalogos.canonical.relevadores import RELEVADORES_CANONICOS
from app.domains.catalogos.canonical.rubros import RUBROS_CANONICOS
from app.domains.catalogos.canonical.tipos_actuacion import TIPOS_ACTUACION_CANONICOS
from app.domains.catalogos.seeds.calles_canonical_seed import iter_canonical_calles_from_csv
from app.domains.catalogos.seeds.catalog_matchers import (
    build_calle_indexes,
    build_rubro_identity_index,
    exists_calle,
    exists_nombre_catalog,
    exists_rubro,
)
from app.domains.grid.seeds.inspectores_canonicos import INSPECTORES_CANONICO
from app.models import (
    CatalogContraproducencia,
    CatalogMotivoComprobacion,
    CatalogTipoActuacion,
    Distrito,
    Inspector,
    ItemActaInspeccion,
    JuzgadoCatalogo,
    Motivo,
    Relevador,
    Turno,
)

CALLES_CANONICAS_CSV = (
    Path(__file__).resolve().parent.parent / "canonical" / "data" / "calles_canonicas.csv"
)


def validate_canonical_catalogs(session: Session) -> dict[str, bool]:
    """
    Verifica que cada valor canónico exista en DB.

    Returns:
        Dict catálogo → True si completo.

    Raises:
        ValueError: si falta algún canónico.
    """
    missing: list[str] = []
    rubro_index = build_rubro_identity_index(session)
    calle_indexes = build_calle_indexes(session)

    for nombre in RUBROS_CANONICOS:
        if not exists_rubro(session, nombre, index=rubro_index):
            missing.append(f"rubro:{nombre}")

    for nombre in RELEVADORES_CANONICOS:
        if not exists_nombre_catalog(session, Relevador, nombre):
            missing.append(f"relevador:{nombre}")

    for codigo, nombre in JUZGADOS_CANONICOS:
        row = session.query(JuzgadoCatalogo).filter(JuzgadoCatalogo.codigo == codigo).first()
        if row is None:
            missing.append(f"juzgado:{codigo}")
        if "IIX" in (codigo, nombre):
            missing.append("juzgado:IIX_no_permitido")

    for nombre in MOTIVOS_NOTIFICACION_CANONICOS:
        if not exists_nombre_catalog(session, Motivo, nombre):
            missing.append(f"motivo_notif:{nombre}")

    for nombre in MOTIVOS_COMPROBACION_CANONICOS:
        if not exists_nombre_catalog(session, CatalogMotivoComprobacion, nombre):
            missing.append(f"motivo_comp:{nombre}")

    for nombre in CONTRAPRODUCENCIAS_CANONICAS:
        if not exists_nombre_catalog(session, CatalogContraproducencia, nombre):
            missing.append(f"contraproducencia:{nombre}")

    items_estado = 0
    items_si_no = 0
    for item in ITEMS_INSPECCION_CANONICOS:
        row = (
            session.query(ItemActaInspeccion)
            .filter(ItemActaInspeccion.codigo == item["codigo"])
            .first()
        )
        if row is None:
            missing.append(f"item_inspeccion:{item['codigo']}")
            continue
        if str(row.tipo_respuesta or "ESTADO") != str(item["tipo_respuesta"]):
            missing.append(f"item_inspeccion_tipo:{item['codigo']}")
        if item["tipo_respuesta"] == "ESTADO":
            items_estado += 1
        elif item["tipo_respuesta"] == "SI_NO":
            items_si_no += 1

    if items_estado != 5:
        missing.append("item_inspeccion:estado_count")
    if items_si_no != 1:
        missing.append("item_inspeccion:si_no_count")

    for nombre in TIPOS_ACTUACION_CANONICOS:
        if not exists_nombre_catalog(session, CatalogTipoActuacion, nombre):
            missing.append(f"tipo_actuacion:{nombre}")

    legajos_db = {str(i.legajo) for i in session.query(Inspector).all()}
    for _nombre, legajo, _turno in INSPECTORES_CANONICO:
        if legajo not in legajos_db:
            missing.append(f"inspector:{legajo}")

    if session.query(Turno).count() < EXPECTED_COUNTS["turnos"]:
        missing.append("turnos:insuficientes")

    if session.query(Distrito).count() < EXPECTED_COUNTS["distritos"]:
        missing.append("distritos:insuficientes")

    for canon in iter_canonical_calles_from_csv(CALLES_CANONICAS_CSV):
        if not exists_calle(canon, calle_indexes):
            missing.append(f"calle:{canon}")
            if len([m for m in missing if m.startswith("calle:")]) > 5:
                break

    if missing:
        raise ValueError("Faltan catálogos canónicos: " + "; ".join(missing[:30]))

    return {
        "rubros": len(RUBROS_CANONICOS) == EXPECTED_COUNTS["rubros"],
        "relevadores": len(RELEVADORES_CANONICOS) == EXPECTED_COUNTS["relevadores"],
        "juzgados": len(JUZGADOS_CANONICOS) == EXPECTED_COUNTS["juzgados"],
        "calles": len(iter_canonical_calles_from_csv(CALLES_CANONICAS_CSV)) == EXPECTED_COUNTS["calles"],
        "items_inspeccion_seed": len(ITEMS_INSPECCION_CANONICOS)
        == EXPECTED_COUNTS["items_inspeccion_seed"],
        "items_inspeccion_tiene_habilitacion": (
            session.query(ItemActaInspeccion)
            .filter(ItemActaInspeccion.codigo == "TIENE_HABILITACION")
            .count()
            == 1
        ),
    }
