"""Resolución de IDs protegidos y expansión indirecta."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import ROUTE_ENTITIES_NO_AUTO_PROTECT
from app.domains.predeploy_cleanup.manifest_io import entity_ids


def load_protected_sets(protected_manifest: dict[str, Any]) -> dict[str, set[int]]:
    """Carga sets de IDs protegidos por entidad desde manifest."""
    entities = protected_manifest.get("entities", {})
    return {name: entity_ids(protected_manifest, name) for name in entities}


def expand_protected_indirect(conn: Connection, protected: dict[str, set[int]]) -> dict[str, set[int]]:
    """
    Expande protección administrativa indirecta vía FK reales.

    No protege estructuras de ruta por contener actuación real.
    """
    expanded = {k: set(v) for k, v in protected.items()}
    act_ids = expanded.get("actuaciones", set())

    # OT protegida → actuaciones que la usan
    ot_ids = expanded.get("orden_trabajo", set())
    if ot_ids:
        ph = ",".join(str(i) for i in sorted(ot_ids))
        rows = conn.execute(
            text(f"SELECT id FROM actuaciones WHERE orden_trabajo_id IN ({ph})")
        ).fetchall()
        act_ids.update(r[0] for r in rows)

    # Notificación / comprobación protegida → actuaciones padre
    for col, key in (("notificacion_id", "notificacion"), ("comprobacion_id", "comprobacion")):
        pids = expanded.get(key, set())
        if pids:
            ph = ",".join(str(i) for i in sorted(pids))
            rows = conn.execute(
                text(f"SELECT id FROM actuaciones WHERE {col} IN ({ph})")
            ).fetchall()
            act_ids.update(r[0] for r in rows)

    # Inspección protegida → actuación padre
    insp_ids = expanded.get("inspeccion", set())
    if insp_ids:
        ph = ",".join(str(i) for i in sorted(insp_ids))
        rows = conn.execute(
            text(f"SELECT actuacion_id FROM inspeccion WHERE id IN ({ph})")
        ).fetchall()
        act_ids.update(r[0] for r in rows)

    # Oficio → expediente + actuaciones vía comprobación
    oficio_ids = expanded.get("oficio", set())
    if oficio_ids:
        ph = ",".join(str(i) for i in sorted(oficio_ids))
        rows = conn.execute(
            text(f"SELECT id FROM expediente WHERE oficio_id IN ({ph})")
        ).fetchall()
        expanded.setdefault("expediente", set()).update(r[0] for r in rows)
        comp_rows = conn.execute(
            text(f"SELECT comprobacion_id FROM oficio WHERE id IN ({ph}) AND comprobacion_id IS NOT NULL")
        ).fetchall()
        comp_ids = {r[0] for r in comp_rows}
        expanded.setdefault("comprobacion", set()).update(comp_ids)
        if comp_ids:
            cph = ",".join(str(i) for i in sorted(comp_ids))
            act_rows = conn.execute(
                text(f"SELECT id FROM actuaciones WHERE comprobacion_id IN ({cph})")
            ).fetchall()
            act_ids.update(r[0] for r in act_rows)

    expanded["actuaciones"] = act_ids
    return expanded


def hard_conflict_check(
    cleanup: dict[str, set[int]],
    protected: dict[str, set[int]],
    *,
    critical_entities: frozenset[str],
) -> list[dict[str, Any]]:
    """
    Intersección cleanup ∩ protected en entidades críticas.

    Retorna conflictos; lista vacía = OK.
    """
    conflicts: list[dict[str, Any]] = []
    for entity in critical_entities:
        c = cleanup.get(entity, set())
        p = protected.get(entity, set())
        inter = c & p
        if inter:
            conflicts.append(
                {
                    "entity": entity,
                    "intersection_count": len(inter),
                    "sample_ids": sorted(inter)[:20],
                    "status": "HARD_CONFLICT_ABORT",
                }
            )
    return conflicts


def is_route_entity(entity: str) -> bool:
    return entity in ROUTE_ENTITIES_NO_AUTO_PROTECT
