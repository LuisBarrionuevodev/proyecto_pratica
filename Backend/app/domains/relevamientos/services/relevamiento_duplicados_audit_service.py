"""
Auditoría de duplicados en relevamientos activos (PR7.5 ESQUINA / PR7.6 NUMERO).

Solo lectura: no modifica datos.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.grid.services.relevamiento_dup_key import (
    build_relevamiento_establishment_key_domicilio,
    normalizar_campos_establecimiento_para_clave,
)
from app.models import Domicilio, Relevamiento, Rubro


@dataclass
class GrupoDuplicadoAudit:
    """Grupo sospechoso detectado en la auditoría."""

    tipo: str
    domicilio_id: int
    calle: str | None
    numero: str | None
    cantidad: int
    relevamiento_ids: list[int] = field(default_factory=list)
    rubro_id: int | None = None
    rubro: str | None = None
    nombre_fantasia: str | None = None
    angulo_esquina: str | None = None
    recomendacion: str = ""


@dataclass
class AuditoriaDuplicadosResult:
    """Resultado agregado de la auditoría."""

    total_grupos_revisados: int
    grupos_con_colision: int
    grupos: list[GrupoDuplicadoAudit] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializa para CLI o logs."""
        return {
            "total_grupos_revisados": self.total_grupos_revisados,
            "grupos_con_colision": self.grupos_con_colision,
            "grupos": [
                {
                    "tipo": g.tipo,
                    "domicilio_id": g.domicilio_id,
                    "calle": g.calle,
                    "numero": g.numero,
                    "rubro_id": g.rubro_id,
                    "rubro": g.rubro,
                    "cantidad": g.cantidad,
                    "relevamiento_ids": g.relevamiento_ids,
                    "nombre_fantasia": g.nombre_fantasia,
                    "angulo_esquina": g.angulo_esquina,
                    "recomendacion": g.recomendacion,
                }
                for g in self.grupos
            ],
        }


def _rubro_nombre(rel: Relevamiento) -> str | None:
    if rel.rubro is not None:
        return rel.rubro.nombre
    return None


def _activos_por_domicilio(dom: Domicilio) -> list[Relevamiento]:
    return (
        Relevamiento.query.options(joinedload(Relevamiento.rubro))
        .filter(
            Relevamiento.domicilio_id == dom.id,
            Relevamiento.deleted_at.is_(None),
        )
        .all()
    )


def _auditar_esquinas() -> list[GrupoDuplicadoAudit]:
    grupos: list[GrupoDuplicadoAudit] = []

    domicilios_esquina = (
        Domicilio.query.filter(
            Domicilio.deleted_at.is_(None),
            Domicilio.numero_tipo == "ESQUINA",
        )
        .all()
    )

    establecimiento_index: dict[str, list[Relevamiento]] = {}
    legacy_vacio_index: dict[tuple[int, int | None], list[Relevamiento]] = {}
    por_domicilio: dict[int, list[Relevamiento]] = {}

    for dom in domicilios_esquina:
        activos = _activos_por_domicilio(dom)
        if not activos:
            continue
        por_domicilio[dom.id] = activos

        for rel in activos:
            est_key = build_relevamiento_establishment_key_domicilio(
                dom.id,
                mes=rel.mes,
                anio=rel.anio,
                rubro_id=rel.rubro_id,
                nombre_fantasia=rel.nombre_fantasia,
                angulo_esquina=rel.angulo_esquina,
                es_esquina=True,
            )
            establecimiento_index.setdefault(est_key, []).append(rel)

            nf_key, ang_key = normalizar_campos_establecimiento_para_clave(
                rel.nombre_fantasia,
                rel.angulo_esquina,
            )
            if nf_key is None and ang_key is None and rel.rubro_id is not None:
                legacy_key = (dom.id, rel.rubro_id, rel.mes, rel.anio)
                legacy_vacio_index.setdefault(legacy_key, []).append(rel)

    for rels in establecimiento_index.values():
        if len(rels) <= 1:
            continue
        dom = rels[0].domicilio
        nf_key, ang_key = normalizar_campos_establecimiento_para_clave(
            rels[0].nombre_fantasia,
            rels[0].angulo_esquina,
        )
        if nf_key is None and ang_key is None:
            continue
        grupos.append(
            GrupoDuplicadoAudit(
                tipo="colision_exacta",
                domicilio_id=dom.id if dom else rels[0].domicilio_id,
                calle=dom.calle if dom else None,
                numero=dom.numero if dom else None,
                rubro_id=rels[0].rubro_id,
                rubro=_rubro_nombre(rels[0]),
                cantidad=len(rels),
                relevamiento_ids=[r.id for r in rels],
                nombre_fantasia=rels[0].nombre_fantasia,
                angulo_esquina=rels[0].angulo_esquina,
                recomendacion=(
                    "Colisión exacta: revise si son duplicados reales o complete ángulo/nombre "
                    "para diferenciarlos."
                ),
            )
        )

    for (dom_id, rubro_id, _mes, _anio), rels in legacy_vacio_index.items():
        if len(rels) <= 1:
            continue
        dom = db.session.get(Domicilio, dom_id)
        grupos.append(
            GrupoDuplicadoAudit(
                tipo="legacy_vacio",
                domicilio_id=dom_id,
                calle=dom.calle if dom else None,
                numero=dom.numero if dom else None,
                rubro_id=rubro_id,
                rubro=_rubro_nombre(rels[0]),
                cantidad=len(rels),
                relevamiento_ids=[r.id for r in rels],
                recomendacion=(
                    "Legacy sin ángulo ni nombre fantasía: complete discriminadores o fusione "
                    "manualmente si son duplicados."
                ),
            )
        )

    for dom_id, rels in por_domicilio.items():
        rubro_ids = {r.rubro_id for r in rels if r.rubro_id is not None}
        if len(rubro_ids) <= 1:
            continue
        dom = db.session.get(Domicilio, dom_id)
        grupos.append(
            GrupoDuplicadoAudit(
                tipo="multi_rubro",
                domicilio_id=dom_id,
                calle=dom.calle if dom else None,
                numero=dom.numero if dom else None,
                cantidad=len(rels),
                relevamiento_ids=[r.id for r in rels],
                recomendacion=(
                    "Varios rubros en la misma esquina: válido si son locales distintos; "
                    "verifique ángulo o nombre fantasía si hace falta distinguirlos."
                ),
            )
        )

    for dom in domicilios_esquina:
        activos = por_domicilio.get(dom.id) or []
        if not activos:
            continue
        rubros_activos = {r.rubro_id for r in activos if r.rubro_id is not None}
        if dom.rubro_id is None:
            continue
        if dom.rubro_id in rubros_activos and len(rubros_activos) == 1:
            continue
        if len(rubros_activos) > 1 or (
            len(rubros_activos) == 1 and dom.rubro_id not in rubros_activos
        ):
            grupos.append(
                GrupoDuplicadoAudit(
                    tipo="rubro_domicilio_inconsistente",
                    domicilio_id=dom.id,
                    calle=dom.calle,
                    numero=dom.numero,
                    rubro_id=dom.rubro_id,
                    rubro=dom.rubro.nombre if dom.rubro else None,
                    cantidad=len(activos),
                    relevamiento_ids=[r.id for r in activos],
                    recomendacion=(
                        "domicilio.rubro_id no refleja todos los rubros activos en la esquina; "
                        "revisar coherencia (PR7.3 no pisa rubro en multi-rubro)."
                    ),
                )
            )

    return grupos


def _auditar_numero_otro() -> list[GrupoDuplicadoAudit]:
    grupos: list[GrupoDuplicadoAudit] = []

    domicilios_numero = (
        Domicilio.query.filter(
            Domicilio.deleted_at.is_(None),
            or_(
                Domicilio.numero_tipo.is_(None),
                Domicilio.numero_tipo.in_(["NUMERO", "OTRO"]),
            ),
        )
        .all()
    )

    for dom in domicilios_numero:
        activos = _activos_por_domicilio(dom)
        if len(activos) <= 1:
            continue

        est_index: dict[str, list[Relevamiento]] = defaultdict(list)
        for rel in activos:
            key = build_relevamiento_establishment_key_domicilio(
                dom.id,
                mes=rel.mes,
                anio=rel.anio,
                rubro_id=rel.rubro_id,
                nombre_fantasia=rel.nombre_fantasia,
                es_esquina=False,
            )
            est_index[key].append(rel)

        for rels in est_index.values():
            if len(rels) <= 1:
                continue
            nf_key, _ = normalizar_campos_establecimiento_para_clave(
                rels[0].nombre_fantasia,
                None,
            )
            tipo = "legacy_vacio" if nf_key is None else "colision_exacta"
            grupos.append(
                GrupoDuplicadoAudit(
                    tipo=tipo,
                    domicilio_id=dom.id,
                    calle=dom.calle,
                    numero=dom.numero,
                    rubro_id=rels[0].rubro_id,
                    rubro=_rubro_nombre(rels[0]),
                    cantidad=len(rels),
                    relevamiento_ids=[r.id for r in rels],
                    nombre_fantasia=rels[0].nombre_fantasia,
                    recomendacion=(
                        "Colisión en domicilio con número: mismo rubro y nombre fantasía."
                        if tipo == "colision_exacta"
                        else "Mismo rubro sin nombre fantasía: indique nombre o revise duplicado."
                    ),
                )
            )

        if len(est_index) > 1:
            grupos.append(
                GrupoDuplicadoAudit(
                    tipo="multi_establecimiento_numero",
                    domicilio_id=dom.id,
                    calle=dom.calle,
                    numero=dom.numero,
                    cantidad=len(activos),
                    relevamiento_ids=[r.id for r in activos],
                    recomendacion=(
                        "Varios establecimientos activos en el mismo domicilio con número "
                        "(rubros o nombres distintos): válido si hubo recambio de rubro/local."
                    ),
                )
            )

    return grupos


def auditar_relevamientos_duplicados() -> AuditoriaDuplicadosResult:
    """
    Audita relevamientos activos en domicilios ESQUINA y NUMERO/OTRO.

    Retorno:
        ``AuditoriaDuplicadosResult`` con totales y detalle por grupo.
    """
    grupos = _auditar_esquinas() + _auditar_numero_otro()
    colision_tipos = {"colision_exacta", "legacy_vacio"}
    grupos_con_colision = sum(1 for g in grupos if g.tipo in colision_tipos)

    return AuditoriaDuplicadosResult(
        total_grupos_revisados=len(grupos),
        grupos_con_colision=grupos_con_colision,
        grupos=grupos,
    )


def auditar_relevamientos_esquina_duplicados() -> AuditoriaDuplicadosResult:
    """
    Alias retrocompatible: ejecuta auditoría completa (ESQUINA + NUMERO/OTRO).
    """
    return auditar_relevamientos_duplicados()
