"""
REL-DISTRITO.2C — diagnóstico: relevamiento geolocalizado sin distrito en Gestión.
Uso: python scripts/diag_rel_distrito_2c.py [--relevamiento-id N]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.database import db
from app.domains.domicilios.utils.domicilio_distrito_display import (
    domicilio_distrito_gestion_fields,
    domicilio_geocode_valido_para_distrito,
)
from app.domains.geolocalizacion.geocode.services.distrito_backfill_service import (
    backfill_distrito_for_domicilio_if_needed,
)
from app.domains.geolocalizacion.geocode.services.distritos_service import resolve_distrito_id
from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_to_row
from app.domains.relevamientos.services.list_service import (
    listar_relevamientos_operativos_con_filtros,
)
from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters
from app.models import Domicilio, DomicilioGeocode, Distrito, Relevamiento


def _pick_relevamiento(relevamiento_id: int | None) -> Relevamiento | None:
    if relevamiento_id:
        return (
            Relevamiento.query.filter(
                Relevamiento.id == relevamiento_id,
                Relevamiento.deleted_at.is_(None),
            )
            .first()
        )
    return (
        Relevamiento.query.filter(Relevamiento.deleted_at.is_(None))
        .join(Domicilio, Relevamiento.domicilio_id == Domicilio.id)
        .join(DomicilioGeocode, DomicilioGeocode.domicilio_id == Domicilio.id)
        .filter(
            DomicilioGeocode.deleted_at.is_(None),
            DomicilioGeocode.geo_status == "OK",
            DomicilioGeocode.lat.isnot(None),
            DomicilioGeocode.lng.isnot(None),
        )
        .order_by(Relevamiento.id.desc())
        .first()
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--relevamiento-id", type=int, default=None)
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        rel = _pick_relevamiento(args.relevamiento_id)
        if not rel:
            print("No se encontró relevamiento para diagnosticar.")
            return

        dom = rel.domicilio
        geo = dom.geocode if dom else None
        dist = dom.distrito if dom else None

        print("=== CASO RELEVAMIENTO ===")
        print(
            json.dumps(
                {
                    "relevamiento_id": rel.id,
                    "domicilio_id": rel.domicilio_id,
                    "calle": dom.calle if dom else None,
                    "numero": dom.numero if dom else None,
                    "numero_tipo": dom.numero_tipo if dom else None,
                },
                indent=2,
                ensure_ascii=False,
            )
        )

        print("\n=== MATRIZ GEO / DISTRITO ===")
        lat = float(geo.lat) if geo and geo.lat is not None else None
        lng = float(geo.lng) if geo and geo.lng is not None else None
        resolved = resolve_distrito_id(lat, lng) if lat is not None and lng is not None else None
        presenter_fields = domicilio_distrito_gestion_fields(dom)
        row = relevamiento_to_row(rel)

        matrix = {
            "geo_status": str(geo.geo_status) if geo else None,
            "lat": lat,
            "lng": lng,
            "source": str(geo.source) if geo and geo.source else None,
            "updated_at": str(geo.updated_at) if geo and geo.updated_at else None,
            "distrito_id": dom.distrito_id if dom else None,
            "distrito.nombre": dist.nombre if dist else None,
            "distrito.codigo": dist.codigo if dist else None,
            "resolve_distrito_id(lat,lng)": resolved,
            "geo_valido_para_distrito": domicilio_geocode_valido_para_distrito(geo),
            "distrito_mostrar (presenter)": presenter_fields.get("distrito_mostrar"),
            "distrito_mostrar (row API)": row.get("distrito_mostrar"),
        }
        print(json.dumps(matrix, indent=2, ensure_ascii=False))

        failing = []
        if not domicilio_geocode_valido_para_distrito(geo):
            failing.append("geo no válido (status/coords)")
        if dom and dom.distrito_id is None:
            failing.append("domicilio.distrito_id IS NULL")
        if presenter_fields.get("distrito_mostrar") is None:
            failing.append("distrito_mostrar NULL en presenter")
        print("\n=== CONDICIONES QUE FALLAN ===")
        print(failing or ["ninguna — debería mostrarse"])

        print("\n=== BACKFILL DIAGNÓSTICO (sin commit) ===")
        before = dom.distrito_id if dom else None
        changed = False
        if dom:
            changed = backfill_distrito_for_domicilio_if_needed(int(dom.id))
            after = dom.distrito_id
            db.session.rollback()
            print(json.dumps({"antes": before, "despues_simulado": after, "asignaria": changed}, indent=2))
        else:
            print("sin domicilio")

        print("\n=== API gestion-operativa (muestra) ===")
        filters = RelevamientosListFilters.model_validate(
            {"desde": "2020-01-01", "hasta": "2099-12-31", "page": 1, "page_size": 500}
        )
        result = listar_relevamientos_operativos_con_filtros(filters)
        api_item = None
        for r, _ini in result["items"]:
            if int(r.id) == int(rel.id):
                from app.domains.relevamientos.presenters.relevamiento_presenter import (
                    relevamiento_operativo_to_row,
                )

                api_item = relevamiento_operativo_to_row(r, 0, "PENDIENTE")
                break
        if api_item:
            print(
                json.dumps(
                    {
                        k: api_item.get(k)
                        for k in (
                            "id",
                            "domicilio_id",
                            "distrito_id",
                            "distrito_codigo",
                            "distrito_nombre",
                            "distrito_mostrar",
                        )
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print("relevamiento no está en gestion-operativa (sin iniciador PENDIENTE?)")


if __name__ == "__main__":
    main()
