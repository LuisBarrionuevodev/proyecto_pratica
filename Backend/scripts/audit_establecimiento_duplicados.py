"""CLI: auditoría de fichas ``establecimiento_operativo`` duplicadas por identidad lógica (FIX.7)."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.database import db
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    agrupar_eo_por_identidad_logica,
    business_key_str,
    seleccionar_eo_canonico_del_grupo,
)
from app.models import Actuaciones, Domicilio, EstablecimientoOperativo


def auditar_establecimiento_duplicados() -> list[dict]:
    """
    Agrupa fichas por business key lógica y reporta duplicados históricos.

    Retorno:
        Lista de dicts con business_key, canonical_eo_id, duplicate_eo_ids,
        actuaciones_por_eo, domicilio_ids, contribuyente_ids.
    """
    eos = (
        EstablecimientoOperativo.query.join(
            Domicilio, EstablecimientoOperativo.domicilio_id == Domicilio.id
        )
        .filter(Domicilio.deleted_at.is_(None))
        .all()
    )
    groups = agrupar_eo_por_identidad_logica(eos)
    report: list[dict] = []

    for key, group in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        if len(group) < 2:
            continue
        canon = seleccionar_eo_canonico_del_grupo(group)
        dom = canon.domicilio
        bk = business_key_str(dom) if dom is not None else str(key)
        eo_ids = sorted(int(e.id) for e in group)
        domicilio_ids = sorted({int(e.domicilio_id) for e in group if e.domicilio_id})
        contrib_ids = sorted(
            {
                int(e.domicilio.contribuyente_id)
                for e in group
                if e.domicilio is not None and e.domicilio.contribuyente_id is not None
            }
        )
        actuaciones_por_eo: dict[str, int] = {}
        for eid in eo_ids:
            n = (
                db.session.query(Actuaciones.id)
                .filter(Actuaciones.establecimiento_operativo_id == eid)
                .count()
            )
            actuaciones_por_eo[str(eid)] = n

        contrib_warning = None
        if len(contrib_ids) > 1:
            contrib_warning = (
                f"Mismo documento lógico con contribuyente_id distintos: {contrib_ids}"
            )

        report.append(
            {
                "business_key": bk,
                "canonical_eo_id": int(canon.id),
                "duplicate_eo_ids": [eid for eid in eo_ids if eid != int(canon.id)],
                "all_eo_ids": eo_ids,
                "actuaciones_por_eo": actuaciones_por_eo,
                "domicilio_ids": domicilio_ids,
                "contribuyente_ids": contrib_ids,
                "contribuyente_duplicado_warning": contrib_warning,
            }
        )
    return report


app = create_app()

with app.app_context():
    rows = auditar_establecimiento_duplicados()
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(
        f"\nResumen: {len(rows)} grupos con duplicados lógicos.",
        file=sys.stderr,
    )
