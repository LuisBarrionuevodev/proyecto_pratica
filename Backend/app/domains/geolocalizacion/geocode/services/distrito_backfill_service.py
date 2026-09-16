from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Query

from app.database import db
from app.domains.geolocalizacion.geocode.services.domicilio_district_consistency import (
    log_barrio_distrito_consistency,
)
from app.domains.geolocalizacion.geocode.services.district_events import log_district_event
from app.domains.geolocalizacion.geocode.services.distritos_service import (
    resolve_distrito_id,
)
from app.models import Domicilio, DomicilioGeocode, Distrito


def run_distrito_backfill(*, limit: Optional[int] = None, force: bool = False) -> Dict[str, Any]:
    """
    Ejecuta backfill de distrito para domicilios geocodificados en estado OK.

    Reglas:
    - Solo domicilios no eliminados.
    - Solo geocode no eliminado, con status OK y lat/lng presentes.
    - En modo incremental (force=False), procesa solo domicilios sin distrito_id.
    - En modo force=True, recalcula todos los elegibles.

    Args:
        limit: máximo de registros a procesar.
        force: si True recalcula aunque el domicilio ya tenga distrito_id.

    Returns:
        Resumen de corrida con métricas de resultado.
    """
    summary: Dict[str, Any] = {
        "processed": 0,
        "assigned": 0,
        "updated": 0,
        "no_match": 0,
        "errors": 0,
        "skipped": 0,
        "force": force,
        "limit": limit,
    }

    query = (
        db.session.query(Domicilio, DomicilioGeocode)
        .join(
            DomicilioGeocode,
            Domicilio.id == DomicilioGeocode.domicilio_id,
        )
        .filter(
            Domicilio.deleted_at.is_(None),
            DomicilioGeocode.deleted_at.is_(None),
            DomicilioGeocode.geo_status == "OK",
            DomicilioGeocode.lat.isnot(None),
            DomicilioGeocode.lng.isnot(None),
        )
        .order_by(Domicilio.id.asc())
    )
    if not force:
        query = query.filter(Domicilio.distrito_id.is_(None))
    if limit is not None:
        query = query.limit(limit)

    rows = query.all()
    for domicilio, geo in rows:
        summary["processed"] += 1
        lat = float(geo.lat)
        lng = float(geo.lng)
        geo_status = str(geo.geo_status or "")
        try:
            resolved_distrito_id = resolve_distrito_id(lat, lng)
        except Exception as exc:
            summary["errors"] += 1
            log_district_event(
                event="district_error",
                domicilio_id=int(domicilio.id),
                lat=lat,
                lng=lng,
                source="BACKFILL",
                geo_status=geo_status,
                distrito_id=None,
                error=str(exc),
            )
            continue

        previous_distrito_id = domicilio.distrito_id
        if resolved_distrito_id is None:
            summary["no_match"] += 1
            log_district_event(
                event="district_no_match",
                domicilio_id=int(domicilio.id),
                lat=lat,
                lng=lng,
                source="BACKFILL",
                geo_status=geo_status,
                distrito_id=None,
            )
            if force and previous_distrito_id is not None:
                domicilio.distrito_id = None
                db.session.add(domicilio)
                summary["updated"] += 1
            continue

        if previous_distrito_id is None:
            domicilio.distrito_id = resolved_distrito_id
            db.session.add(domicilio)
            log_barrio_distrito_consistency(
                domicilio=domicilio,
                source="BACKFILL",
                lat=lat,
                lng=lng,
            )
            summary["assigned"] += 1
            log_district_event(
                event="district_assigned",
                domicilio_id=int(domicilio.id),
                lat=lat,
                lng=lng,
                source="BACKFILL",
                geo_status=geo_status,
                distrito_id=int(resolved_distrito_id),
            )
            continue

        if int(previous_distrito_id) != int(resolved_distrito_id):
            domicilio.distrito_id = resolved_distrito_id
            db.session.add(domicilio)
            log_barrio_distrito_consistency(
                domicilio=domicilio,
                source="BACKFILL",
                lat=lat,
                lng=lng,
            )
            summary["updated"] += 1
            log_district_event(
                event="district_assigned",
                domicilio_id=int(domicilio.id),
                lat=lat,
                lng=lng,
                source="BACKFILL",
                geo_status=geo_status,
                distrito_id=int(resolved_distrito_id),
            )
            continue

        summary["skipped"] += 1

    db.session.commit()
    return summary


def backfill_distrito_for_domicilio_if_needed(domicilio_id: int) -> bool:
    """
    Asigna ``distrito_id`` a un domicilio si tiene geocode OK con coordenadas y distrito nulo.

    No hace commit: el caller persiste en su transacción.

    Args:
        domicilio_id: id del domicilio a evaluar.

    Returns:
        True si se asignó distrito en esta llamada; False en caso contrario.

    Raises:
        ValueError: si el domicilio no existe o está eliminado.
    """
    domicilio = db.session.get(Domicilio, domicilio_id)
    if not domicilio or domicilio.deleted_at is not None:
        raise ValueError("Domicilio no encontrado.")

    if domicilio.distrito_id is not None:
        return False

    geo = (
        DomicilioGeocode.query.filter(
            DomicilioGeocode.domicilio_id == domicilio_id,
            DomicilioGeocode.deleted_at.is_(None),
            DomicilioGeocode.geo_status == "OK",
            DomicilioGeocode.lat.isnot(None),
            DomicilioGeocode.lng.isnot(None),
        )
        .first()
    )
    if not geo:
        return False

    lat = float(geo.lat)
    lng = float(geo.lng)
    geo_status = str(geo.geo_status or "")
    try:
        resolved_distrito_id = resolve_distrito_id(lat, lng)
    except Exception as exc:
        log_district_event(
            event="district_error",
            domicilio_id=int(domicilio.id),
            lat=lat,
            lng=lng,
            source="BACKFILL",
            geo_status=geo_status,
            distrito_id=None,
            error=str(exc),
        )
        return False

    if resolved_distrito_id is None:
        log_district_event(
            event="district_no_match",
            domicilio_id=int(domicilio.id),
            lat=lat,
            lng=lng,
            source="BACKFILL",
            geo_status=geo_status,
            distrito_id=None,
        )
        return False

    domicilio.distrito_id = resolved_distrito_id
    db.session.add(domicilio)
    log_barrio_distrito_consistency(
        domicilio=domicilio,
        source="BACKFILL",
        lat=lat,
        lng=lng,
    )
    log_district_event(
        event="district_assigned",
        domicilio_id=int(domicilio.id),
        lat=lat,
        lng=lng,
        source="BACKFILL",
        geo_status=geo_status,
        distrito_id=int(resolved_distrito_id),
    )
    return True


@dataclass
class BackfillDistritoGeoOkSummary:
    """Resumen de corrida de backfill para domicilios geolocalizados sin distrito."""

    mode: str
    candidatos: int = 0
    antes_geo_ok_sin_distrito: int = 0
    assigned: int = 0
    no_match: int = 0
    errors: int = 0
    despues_restantes: int = 0
    por_distrito: Dict[str, int] = field(default_factory=dict)
    error_details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el resumen para logging o salida de script."""
        return {
            "mode": self.mode,
            "candidatos": self.candidatos,
            "antes_geo_ok_sin_distrito": self.antes_geo_ok_sin_distrito,
            "assigned": self.assigned,
            "no_match": self.no_match,
            "errors": self.errors,
            "despues_restantes": self.despues_restantes,
            "por_distrito": dict(self.por_distrito),
            "error_details": list(self.error_details),
        }


def _candidatos_geo_ok_sin_distrito_query(
    *,
    domicilio_id: Optional[int] = None,
) -> Query:
    """
    Query base de domicilios elegibles para backfill de distrito.

    Criterio: domicilio activo, geocode OK con coordenadas y ``distrito_id`` nulo.
    """
    query = (
        db.session.query(Domicilio.id, DomicilioGeocode.lat, DomicilioGeocode.lng)
        .join(DomicilioGeocode, Domicilio.id == DomicilioGeocode.domicilio_id)
        .filter(
            Domicilio.deleted_at.is_(None),
            DomicilioGeocode.deleted_at.is_(None),
            DomicilioGeocode.geo_status == "OK",
            DomicilioGeocode.lat.isnot(None),
            DomicilioGeocode.lng.isnot(None),
            Domicilio.distrito_id.is_(None),
        )
        .order_by(Domicilio.id.asc())
    )
    if domicilio_id is not None:
        query = query.filter(Domicilio.id == int(domicilio_id))
    return query


def count_domicilios_geo_ok_sin_distrito(*, domicilio_id: Optional[int] = None) -> int:
    """
    Cuenta domicilios con geocode OK, coordenadas válidas y ``distrito_id`` nulo.

    Args:
        domicilio_id: si se indica, limita el conteo a ese domicilio.

    Returns:
        Cantidad de candidatos.
    """
    return int(_candidatos_geo_ok_sin_distrito_query(domicilio_id=domicilio_id).count())


def _fetch_candidatos_geo_ok_sin_distrito(
    *,
    limit: Optional[int] = None,
    domicilio_id: Optional[int] = None,
) -> List[Tuple[int, float, float]]:
    """Obtiene candidatos como tuplas ``(domicilio_id, lat, lng)``."""
    query = _candidatos_geo_ok_sin_distrito_query(domicilio_id=domicilio_id)
    if limit is not None:
        query = query.limit(int(limit))
    rows = query.all()
    return [(int(dom_id), float(lat), float(lng)) for dom_id, lat, lng in rows]


def _distrito_label(distrito_id: int) -> str:
    """Etiqueta legible de distrito para reportes."""
    distrito = db.session.get(Distrito, int(distrito_id))
    if distrito is None:
        return f"id:{distrito_id}"
    if distrito.nombre:
        return str(distrito.nombre)
    if distrito.codigo is not None:
        return f"Distrito {distrito.codigo}"
    return f"id:{distrito_id}"


def _classify_backfill_no_assign(lat: float, lng: float) -> str:
    """
    Clasifica un candidato no asignado por ``backfill_distrito_for_domicilio_if_needed``.

    Returns:
        ``no_match`` o ``error``.
    """
    try:
        resolved_distrito_id = resolve_distrito_id(float(lat), float(lng))
    except Exception:
        return "error"
    if resolved_distrito_id is None:
        return "no_match"
    return "error"


def run_backfill_domicilios_geo_ok_sin_distrito(
    *,
    apply: bool = False,
    limit: Optional[int] = None,
    domicilio_id: Optional[int] = None,
    batch_size: int = 50,
) -> BackfillDistritoGeoOkSummary:
    """
    Repara domicilios geolocalizados (geo OK + coords) sin ``distrito_id``.

    Usa ``backfill_distrito_for_domicilio_if_needed`` por domicilio. En modo dry-run
    no hace commit; en modo apply persiste por lotes.

    Args:
        apply: si True persiste cambios; si False solo simula y hace rollback final.
        limit: máximo de candidatos a procesar.
        domicilio_id: procesar solo un domicilio.
        batch_size: tamaño de lote para commits en modo apply.

    Returns:
        Resumen con métricas antes/después y desglose por distrito.
    """
    summary = BackfillDistritoGeoOkSummary(
        mode="apply" if apply else "dry_run",
        antes_geo_ok_sin_distrito=count_domicilios_geo_ok_sin_distrito(
            domicilio_id=domicilio_id
        ),
    )
    candidates = _fetch_candidatos_geo_ok_sin_distrito(
        limit=limit,
        domicilio_id=domicilio_id,
    )
    summary.candidatos = len(candidates)

    pending_successes = 0
    batch_size = max(1, int(batch_size))

    for dom_id, lat, lng in candidates:
        savepoint = db.session.begin_nested() if apply else None
        try:
            assigned = backfill_distrito_for_domicilio_if_needed(int(dom_id))
            if assigned:
                domicilio = db.session.get(Domicilio, int(dom_id))
                distrito_id = int(domicilio.distrito_id) if domicilio and domicilio.distrito_id else None
                if distrito_id is not None:
                    label = _distrito_label(distrito_id)
                    summary.por_distrito[label] = summary.por_distrito.get(label, 0) + 1
                summary.assigned += 1
                pending_successes += 1
                if apply:
                    savepoint.commit()
                    if pending_successes >= batch_size:
                        db.session.commit()
                        pending_successes = 0
            else:
                outcome = _classify_backfill_no_assign(lat, lng)
                if outcome == "error":
                    summary.errors += 1
                    summary.error_details.append(
                        {
                            "domicilio_id": int(dom_id),
                            "lat": lat,
                            "lng": lng,
                            "error": "resolve_distrito_id falló tras backfill sin asignar",
                        }
                    )
                else:
                    summary.no_match += 1
                if apply and savepoint is not None and not assigned:
                    savepoint.rollback()
        except ValueError as exc:
            summary.errors += 1
            summary.error_details.append(
                {
                    "domicilio_id": int(dom_id),
                    "lat": lat,
                    "lng": lng,
                    "error": str(exc),
                }
            )
            if apply and savepoint is not None:
                savepoint.rollback()
            continue
        except Exception as exc:  # noqa: BLE001 - un error no aborta el lote
            summary.errors += 1
            summary.error_details.append(
                {
                    "domicilio_id": int(dom_id),
                    "lat": lat,
                    "lng": lng,
                    "error": str(exc),
                }
            )
            if apply and savepoint is not None:
                savepoint.rollback()
            continue

    if apply:
        if pending_successes > 0:
            db.session.commit()
    else:
        db.session.rollback()

    summary.despues_restantes = count_domicilios_geo_ok_sin_distrito(
        domicilio_id=domicilio_id
    )
    return summary

