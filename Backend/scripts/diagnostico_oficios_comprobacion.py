"""
PR3 — Diagnóstico de oficios por comprobación (solo lectura).

Uso:
    cd Backend
    set PYTHONPATH=.
    python scripts/diagnostico_oficios_comprobacion.py
    python scripts/diagnostico_oficios_comprobacion.py --limite-ejemplos 10
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from sqlalchemy import func

from app import create_app
from app.database import db
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.models import Comprobacion, Expediente, IniciadorRuta, Oficio


def _oficios_activos_por_comprobacion() -> dict[int, list[Oficio]]:
    rows = (
        Oficio.query.filter(Oficio.deleted_at.is_(None), Oficio.comprobacion_id.isnot(None))
        .order_by(Oficio.comprobacion_id.asc(), Oficio.id.asc())
        .all()
    )
    by_comp: dict[int, list[Oficio]] = defaultdict(list)
    for row in rows:
        by_comp[int(row.comprobacion_id)].append(row)
    return by_comp


def _iniciadores_activos_por_oficio() -> dict[int, list[IniciadorRuta]]:
    rows = (
        IniciadorRuta.query.filter(
            IniciadorRuta.oficio_id.isnot(None),
            IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
        )
        .order_by(IniciadorRuta.oficio_id.asc(), IniciadorRuta.id.asc())
        .all()
    )
    by_oficio: dict[int, list[IniciadorRuta]] = defaultdict(list)
    for row in rows:
        by_oficio[int(row.oficio_id)].append(row)
    return by_oficio


def _expedientes_respuesta_sin_oficio() -> list[Expediente]:
    return (
        Expediente.query.filter(
            Expediente.deleted_at.is_(None),
            Expediente.oficio_id.is_(None),
            Expediente.tipo_expediente == "RESPUESTA_OFICIO",
        )
        .order_by(Expediente.id.asc())
        .all()
    )


def _duplicados_numero_anio_comprobacion(
    by_comp: dict[int, list[Oficio]],
) -> list[tuple[int, str, int, int]]:
    """(comprobacion_id, numero_oficio, anio, cantidad) con cantidad > 1."""
    dupes: list[tuple[int, str, int, int]] = []
    for comp_id, oficios in by_comp.items():
        counter = Counter((o.numero_oficio, o.anio) for o in oficios)
        for (numero, anio), count in counter.items():
            if count > 1:
                dupes.append((comp_id, numero, anio, count))
    return dupes


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico oficios por comprobación (solo lectura)")
    parser.add_argument("--limite-ejemplos", type=int, default=8, help="Máximo de ejemplos por sección")
    args = parser.parse_args()
    lim = max(1, int(args.limite_ejemplos))

    app = create_app()
    with app.app_context():
        total_comprobaciones = Comprobacion.query.count()
        by_comp = _oficios_activos_por_comprobacion()
        comps_con_oficios = set(by_comp.keys())

        count_0 = total_comprobaciones - len(comps_con_oficios)
        count_1 = sum(1 for ofs in by_comp.values() if len(ofs) == 1)
        count_n = sum(1 for ofs in by_comp.values() if len(ofs) > 1)

        print("=== PR3 — Oficios por comprobación ===")
        print(f"Comprobaciones totales: {total_comprobaciones}")
        print(f"Comprobaciones con 0 oficios activos: {count_0}")
        print(f"Comprobaciones con 1 oficio activo: {count_1}")
        print(f"Comprobaciones con >1 oficios activos: {count_n}")

        if count_n:
            print(f"\nEjemplos comprobaciones con >1 oficio (hasta {lim}):")
            shown = 0
            for comp_id, ofs in sorted(by_comp.items()):
                if len(ofs) <= 1:
                    continue
                labels = ", ".join(f"{o.numero_oficio}/{o.anio}(id={o.id})" for o in ofs)
                print(f"  comprobacion_id={comp_id}: {labels}")
                shown += 1
                if shown >= lim:
                    break

        iniciadores_by_oficio = _iniciadores_activos_por_oficio()
        oficios_sin_iniciador: list[Oficio] = []
        oficios_multiples_iniciadores: list[tuple[Oficio, list[IniciadorRuta]]] = []
        for ofs in by_comp.values():
            for oficio in ofs:
                inis = iniciadores_by_oficio.get(int(oficio.id), [])
                if not inis:
                    oficios_sin_iniciador.append(oficio)
                elif len(inis) > 1:
                    oficios_multiples_iniciadores.append((oficio, inis))

        print(f"\nOficios activos sin iniciador REINSPECCION_OFICIO activo: {len(oficios_sin_iniciador)}")
        for oficio in oficios_sin_iniciador[:lim]:
            print(
                f"  oficio_id={oficio.id} {oficio.numero_oficio}/{oficio.anio} "
                f"comprobacion_id={oficio.comprobacion_id}"
            )

        print(f"\nOficios con >1 iniciador activo: {len(oficios_multiples_iniciadores)}")
        for oficio, inis in oficios_multiples_iniciadores[:lim]:
            ids = ", ".join(str(i.id) for i in inis)
            print(
                f"  oficio_id={oficio.id} {oficio.numero_oficio}/{oficio.anio} "
                f"iniciadores=[{ids}]"
            )

        dupes = _duplicados_numero_anio_comprobacion(by_comp)
        print(f"\nDuplicados activos (mismo numero/año en misma comprobación): {len(dupes)}")
        for comp_id, numero, anio, count in dupes[:lim]:
            print(f"  comprobacion_id={comp_id} {numero}/{anio} x{count}")

        exp_sin_oficio = _expedientes_respuesta_sin_oficio()
        print(f"\nExpedientes RESPUESTA_OFICIO activos sin oficio_id: {len(exp_sin_oficio)}")
        for ex in exp_sin_oficio[:lim]:
            print(
                f"  expediente_id={ex.id} {ex.numero_expediente}/{ex.anio} "
                f"comprobacion_id={ex.comprobacion_id}"
            )

        global_dup = (
            db.session.query(
                Oficio.numero_oficio,
                Oficio.anio,
                func.count(Oficio.id),
            )
            .filter(Oficio.deleted_at.is_(None))
            .group_by(Oficio.numero_oficio, Oficio.anio)
            .having(func.count(Oficio.id) > 1)
            .all()
        )
        print(f"\nClaves globales numero/año con >1 oficio activo (anomalía): {len(global_dup)}")
        for numero, anio, count in global_dup[:lim]:
            print(f"  {numero}/{anio} x{count}")


if __name__ == "__main__":
    main()
