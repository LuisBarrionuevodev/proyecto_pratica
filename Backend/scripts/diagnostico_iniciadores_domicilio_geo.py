"""
R4/F4/GEO-precheck — Diagnóstico iniciadores vs domicilio/geocode/distrito.

Solo lectura. No modifica datos.

Uso:
    cd Backend
    set PYTHONPATH=.
    python scripts/diagnostico_iniciadores_domicilio_geo.py
    python scripts/diagnostico_iniciadores_domicilio_geo.py --limite-ejemplos 15
"""

from __future__ import annotations

import argparse
from collections import defaultdict

from sqlalchemy import and_, func, or_

from app import create_app
from app.database import db
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.models import (
    Actuaciones,
    Comprobacion,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Notificacion,
    Oficio,
    Relevamiento,
)

_TIPOS_OPERATIVOS = (
    "RELEVAMIENTO",
    "REINSPECCION_NOTIFICACION",
    "REINSPECCION_OFICIO",
    "DENUNCIA",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)

_GEO_OK = ("OK", "MANUAL", "REVIEW")


def _activo_iniciador():
    return and_(
        IniciadorRuta.deleted_at.is_(None),
        IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
    )


def _tiene_geocode_valido(domicilio_id: int | None) -> bool:
    if not domicilio_id:
        return False
    g = (
        DomicilioGeocode.query.filter(
            DomicilioGeocode.domicilio_id == domicilio_id,
            DomicilioGeocode.deleted_at.is_(None),
        )
        .first()
    )
    if not g:
        return False
    return g.geo_status in _GEO_OK and g.lat is not None and g.lng is not None


def _domicilio_origen_actuacion(ini: IniciadorRuta) -> int | None:
    if ini.actuacion_id:
        act = db.session.get(Actuaciones, ini.actuacion_id)
        return int(act.domicilio_id) if act and act.domicilio_id else None
    return None


def _domicilio_origen_relevamiento(ini: IniciadorRuta) -> int | None:
    if ini.relevamiento_id:
        rel = db.session.get(Relevamiento, ini.relevamiento_id)
        return int(rel.domicilio_id) if rel and rel.domicilio_id else None
    return None


def _domicilio_origen_notificacion(ini: IniciadorRuta) -> int | None:
    if not ini.notificacion_id:
        return None
    act = (
        Actuaciones.query.filter(
            Actuaciones.notificacion_id == ini.notificacion_id,
            Actuaciones.tipo == "INSPECCION",
        )
        .order_by(Actuaciones.id.desc())
        .first()
    )
    return int(act.domicilio_id) if act and act.domicilio_id else None


def _domicilio_origen_comprobacion(ini: IniciadorRuta) -> int | None:
    cid = ini.comprobacion_id
    if not cid and ini.oficio_id:
        ofi = db.session.get(Oficio, ini.oficio_id)
        cid = ofi.comprobacion_id if ofi else None
    if not cid:
        return None
    act = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id == cid)
        .order_by(Actuaciones.id.desc())
        .first()
    )
    return int(act.domicilio_id) if act and act.domicilio_id else None


def _origen_domicilio_id(ini: IniciadorRuta) -> int | None:
    if ini.tipo_iniciador == "RELEVAMIENTO":
        return _domicilio_origen_relevamiento(ini)
    if ini.tipo_iniciador == "REINSPECCION_NOTIFICACION":
        return _domicilio_origen_notificacion(ini)
    if ini.tipo_iniciador == "REINSPECCION_OFICIO":
        return _domicilio_origen_comprobacion(ini) or _domicilio_origen_actuacion(ini)
    if ini.tipo_iniciador == "DENUNCIA":
        return _domicilio_origen_actuacion(ini)
    return _domicilio_origen_actuacion(ini)


def _recomendacion(ini: IniciadorRuta, origen_id: int | None) -> str:
    if not ini.domicilio_id:
        if origen_id:
            return f"COPIAR domicilio_id={origen_id} desde origen"
        return "SIN_ORIGEN_RESOLUBLE"
    if origen_id and origen_id != ini.domicilio_id:
        return f"DESALINEADO: ini={ini.domicilio_id} origen={origen_id}"
    dom = db.session.get(Domicilio, ini.domicilio_id)
    if dom and not dom.distrito_id and _tiene_geocode_valido(ini.domicilio_id):
        return "BACKFILL_DISTRITO desde geocode"
    if dom and not dom.distrito_id:
        return "PENDIENTE_GEO_O_DISTRITO"
    if dom and dom.deleted_at is not None:
        return "DOMICILIO_SOFT_DELETED"
    return "OK"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite-ejemplos", type=int, default=10)
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        q = IniciadorRuta.query.filter(_activo_iniciador())
        rows = q.all()

        stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        print("tipo_iniciador | total | con domicilio | con distrito | con geocode | recuperables origen | sin resolver")
        for ini in rows:
            t = str(ini.tipo_iniciador)
            stats[t]["total"] += 1
            if ini.domicilio_id:
                stats[t]["con_domicilio"] += 1
            dom = db.session.get(Domicilio, ini.domicilio_id) if ini.domicilio_id else None
            if dom and dom.distrito_id:
                stats[t]["con_distrito"] += 1
            if _tiene_geocode_valido(ini.domicilio_id):
                stats[t]["con_geocode"] += 1
            origen = _origen_domicilio_id(ini)
            rec = _recomendacion(ini, origen)
            if origen and (not ini.domicilio_id or origen != ini.domicilio_id):
                stats[t]["recuperables_origen"] += 1
            if rec not in ("OK",):
                stats[t]["sin_resolver"] += 1

        for tipo in sorted(stats.keys()):
            s = stats[tipo]
            print(
                f"{tipo} | {s['total']} | {s['con_domicilio']} | {s['con_distrito']} | "
                f"{s['con_geocode']} | {s['recuperables_origen']} | {s['sin_resolver']}"
            )

        print()
        print("Ejemplos con problema (no OK):")
        ejemplos = []
        for ini in rows:
            origen = _origen_domicilio_id(ini)
            rec = _recomendacion(ini, origen)
            if rec == "OK":
                continue
            dom = db.session.get(Domicilio, ini.domicilio_id) if ini.domicilio_id else None
            orig_dom = db.session.get(Domicilio, origen) if origen else None
            ejemplos.append(
                {
                    "iniciador_id": ini.id,
                    "tipo": ini.tipo_iniciador,
                    "estado": ini.estado_iniciador,
                    "domicilio_actual": f"{dom.calle} {dom.numero}" if dom else None,
                    "distrito_actual": dom.distrito_id if dom else None,
                    "geocode_ok": _tiene_geocode_valido(ini.domicilio_id),
                    "actuacion_origen": ini.actuacion_id,
                    "domicilio_origen": f"{orig_dom.calle} {orig_dom.numero}" if orig_dom else None,
                    "distrito_origen": orig_dom.distrito_id if orig_dom else None,
                    "geocode_origen_ok": _tiene_geocode_valido(origen),
                    "recomendacion": rec,
                }
            )
        for ex in ejemplos[: args.limite_ejemplos]:
            print(ex)

        dup_q = (
            db.session.query(
                Domicilio.calle,
                Domicilio.numero,
                func.count(Domicilio.id),
            )
            .filter(Domicilio.deleted_at.is_(None))
            .group_by(Domicilio.calle, Domicilio.numero)
            .having(func.count(Domicilio.id) > 1)
            .order_by(func.count(Domicilio.id).desc())
            .limit(10)
        )
        print()
        print("Top domicilios activos duplicados (calle+numero):")
        for calle, numero, cnt in dup_q.all():
            print(f"  {calle} {numero} -> {cnt} filas")

        multi_ofi = (
            db.session.query(Oficio.comprobacion_id, func.count(Oficio.id))
            .filter(Oficio.deleted_at.is_(None), Oficio.comprobacion_id.isnot(None))
            .group_by(Oficio.comprobacion_id)
            .having(func.count(Oficio.id) > 1)
            .all()
        )
        print()
        print(f"Comprobaciones con mas de un oficio activo: {len(multi_ofi)}")
        for cid, cnt in multi_ofi[:5]:
            print(f"  comprobacion_id={cid} oficios={cnt}")


if __name__ == "__main__":
    main()
