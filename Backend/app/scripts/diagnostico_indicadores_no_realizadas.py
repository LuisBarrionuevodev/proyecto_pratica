"""
Diagnóstico IND-NR.3 — no realizadas en indicadores vs base real.

Uso:
    cd Backend
    set PYTHONPATH=.
    python -m app.scripts.diagnostico_indicadores_no_realizadas
    python -m app.scripts.diagnostico_indicadores_no_realizadas --desde 2026-04-01 --hasta 2026-05-19
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date

from sqlalchemy import and_, func, or_

from app import create_app
from app.database import db
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    _contraproducencia_real_expr,
    _intentos_no_realizados_con_contraproducencia_filters,
    _no_realizadas_base_query,
    _ruta_item_cerrado_no_realizado_expr,
)
from app.domains.indicadores.services.indicadores_no_realizadas_service import (
    build_indicadores_no_realizadas,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    _fecha_periodo_operativo_expr,
)
from app.domains.indicadores.utils.contraproducencia_indicador_buckets import (
    BUCKET_ORDER,
    classify_contraproducencia_indicador,
)
from app.models import (
    Actuaciones,
    IniciadorRuta,
    Inspector,
    RutaItem,
    RutaTrabajo,
    actuaciones_inspector,
)


def _count_base(desde: date, hasta: date, extra_filters: list | None = None) -> int:
    fecha_periodo = _fecha_periodo_operativo_expr()
    clauses = [
        RutaItem.deleted_at.is_(None),
        IniciadorRuta.deleted_at.is_(None),
        RutaTrabajo.estado_ruta == "PUBLICADA",
        fecha_periodo >= desde,
        fecha_periodo <= hasta,
    ]
    if extra_filters:
        clauses.extend(extra_filters)
    return (
        db.session.query(func.count(func.distinct(RutaItem.id)))
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .outerjoin(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .filter(*clauses)
        .scalar()
        or 0
    )


def _sample_rows(desde: date, hasta: date, limit: int = 5):
    return (
        db.session.query(
            RutaItem.id,
            RutaItem.ruta_trabajo_id,
            RutaTrabajo.fecha,
            RutaItem.estado_ruta_item,
            RutaItem.estado_ejecucion,
            RutaItem.motivo_no_realizado,
            Actuaciones.contraproducencia,
            IniciadorRuta.tipo_iniciador,
            Inspector.nombre,
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .outerjoin(
            actuaciones_inspector,
            actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
        )
        .outerjoin(Inspector, Inspector.id == actuaciones_inspector.c.inspector_id)
        .filter(*_intentos_no_realizados_con_contraproducencia_filters(desde, hasta))
        .order_by(RutaItem.id)
        .limit(limit)
        .all()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico no realizadas indicadores")
    parser.add_argument("--desde", default="2026-04-01")
    parser.add_argument("--hasta", default="2026-05-19")
    args = parser.parse_args()
    desde = date.fromisoformat(args.desde)
    hasta = date.fromisoformat(args.hasta)

    app = create_app()
    with app.app_context():
        print("=" * 72)
        print(f"Período: {desde} .. {hasta}")
        print("=" * 72)

        total_ee_nr = _count_base(
            desde,
            hasta,
            [RutaItem.estado_ejecucion == "NO_REALIZADO"],
        )
        total_legacy = _count_base(
            desde,
            hasta,
            [
                RutaItem.estado_ruta_item == "NO_REALIZADO",
                RutaItem.estado_ejecucion == "NO_REALIZADO",
            ],
        )
        total_canonico = _count_base(
            desde,
            hasta,
            [
                RutaItem.estado_ruta_item == "FINALIZADO",
                RutaItem.estado_ejecucion == "NO_REALIZADO",
            ],
        )
        total_cerrado = _count_base(
            desde,
            hasta,
            [_ruta_item_cerrado_no_realizado_expr()],
        )
        total_con_actuacion = _count_base(
            desde,
            hasta,
            [
                _ruta_item_cerrado_no_realizado_expr(),
                RutaItem.actuacion_id.isnot(None),
            ],
        )
        total_kpi = (
            _no_realizadas_base_query(desde, hasta)
            .with_entities(func.count(func.distinct(RutaItem.id)))
            .scalar()
            or 0
        )

        print("\nConteos por criterio:")
        print(f"  estado_ejecucion=NO_REALIZADO (cualquier eri):     {total_ee_nr}")
        print(f"  legado eri+ee=NO_REALIZADO:                        {total_legacy}")
        print(f"  canónico FINALIZADO+NO_REALIZADO:                  {total_canonico}")
        print(f"  cerrado no realizado (expr indicadores):           {total_cerrado}")
        print(f"  + actuacion_id no nulo:                            {total_con_actuacion}")
        print(f"  + contraproducencia real (KPI endpoint):           {total_kpi}")

        excluido_no_hubo = _count_base(
            desde,
            hasta,
            [
                _ruta_item_cerrado_no_realizado_expr(),
                RutaItem.actuacion_id.isnot(None),
                or_(
                    Actuaciones.contraproducencia.is_(None),
                    func.trim(Actuaciones.contraproducencia) == "",
                    func.upper(
                        func.replace(
                            func.replace(func.trim(Actuaciones.contraproducencia), "_", " "),
                            "/",
                            " ",
                        )
                    ).in_(("NO HUBO", "NO_HUBO")),
                ),
            ],
        )
        print(f"  excluidos por NO_HUBO/vacío (con cierre NR):       {excluido_no_hubo}")

        endpoint = build_indicadores_no_realizadas(desde, hasta)
        print("\nEndpoint /no-realizadas:")
        print(f"  total: {endpoint.total}")
        print(f"  por_tipo: {endpoint.por_tipo}")
        print(f"  contraproducencias_resumen: {endpoint.contraproducencias_resumen}")

        bucket_counts: dict[str, int] = defaultdict(int)
        motivo_counts: dict[str, int] = defaultdict(int)
        rows_motivo = (
            db.session.query(
                RutaItem.motivo_no_realizado,
                Actuaciones.contraproducencia,
                func.count(func.distinct(RutaItem.id)),
            )
            .select_from(RutaItem)
            .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
            .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
            .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
            .filter(*_intentos_no_realizados_con_contraproducencia_filters(desde, hasta))
            .group_by(RutaItem.motivo_no_realizado, Actuaciones.contraproducencia)
            .all()
        )
        for motivo, contra, cnt in rows_motivo:
            motivo_counts[str(motivo or "—")] += int(cnt)
            bucket = classify_contraproducencia_indicador(contra)
            if bucket:
                bucket_counts[bucket] += int(cnt)

        print("\nPor motivo_no_realizado (KPI):")
        for k, v in sorted(motivo_counts.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")

        print("\nPor bucket contraproducencia (KPI):")
        for k, v in sorted(bucket_counts.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")

        print("\nEjemplos (hasta 5 registros KPI):")
        for row in _sample_rows(desde, hasta):
            (
                ri_id,
                rt_id,
                rt_fecha,
                eri,
                ee,
                motivo,
                contra,
                tipo_ini,
                insp,
            ) = row
            print(
                f"  ruta_item_id={ri_id} ruta_id={rt_id} fecha_ruta={rt_fecha} "
                f"eri={eri} ee={ee} motivo={motivo} contra={contra!r} "
                f"tipo_iniciador={tipo_ini} inspector={insp or '—'}"
            )

        print("\n" + "=" * 72)
        print("Productividad — no realizadas por inspector")
        print("=" * 72)
        from app.domains.indicadores.services.indicadores_productividad_queries import (
            _no_realizadas_inspector_visita_pairs,
            query_inspectores_no_realizadas,
        )

        pairs = _no_realizadas_inspector_visita_pairs(desde, hasta)
        pair_keys = [(ri, iid) for ri, iid, *_ in pairs]
        dup_counts: dict[tuple[int, int], int] = defaultdict(int)
        for key in pair_keys:
            dup_counts[key] += 1
        dups = [(k, v) for k, v in dup_counts.items() if v > 1]

        print(f"  total general (KPI): {endpoint.total}")
        print(f"  pares únicos (ruta_item_id, inspector_id): {len(dup_counts)}")
        print(f"  pares duplicados (bug): {len(dups)}")
        if dups:
            for (ri, iid), cnt in sorted(dups, key=lambda x: -x[1])[:5]:
                print(f"    ri={ri} inspector_id={iid} count={cnt}")

        by_ri: dict[int, set[int]] = defaultdict(set)
        for ri, iid, *_ in pairs:
            by_ri[ri].add(iid)
        multi = [(ri, ins) for ri, ins in by_ri.items() if len(ins) > 1]
        print(f"  visitas con 2+ inspectores: {len(multi)}")
        for ri, ins in sorted(multi, key=lambda x: -len(x[1]))[:5]:
            print(f"    ruta_item_id={ri} inspectores={sorted(ins)}")

        prod_rows = query_inspectores_no_realizadas(desde, hasta)
        suma_insp = sum(r.total_no_realizadas for r in prod_rows)
        print(f"  suma totales por inspector: {suma_insp}")
        print("  conteo por inspector (total | local | no_existe | no_rat | clima | otras):")
        for r in prod_rows[:10]:
            print(
                f"    {r.inspector}: {r.total_no_realizadas} | "
                f"{r.local_cerrado} | {r.no_existe} | {r.no_se_ratifico} | "
                f"{r.clima} | {r.otras}"
            )
        if suma_insp > endpoint.total:
            print(
                "  nota: suma por inspector > total general es esperable si hay "
                "visitas con varios inspectores asignados."
            )

        print("\nValidación invariante por bucket (inspector <= general):")
        general_buckets = {r.bucket: r.cantidad for r in endpoint.contraproducencias_resumen}
        violations: list[str] = []
        for r in prod_rows:
            for bucket in BUCKET_ORDER:
                attr = bucket
                inspector_val = getattr(r, attr)
                general_val = int(general_buckets.get(bucket, 0))
                if inspector_val > general_val:
                    violations.append(
                        f"  [BUG] bucket={bucket} total_general={general_val} "
                        f"inspector={r.inspector} valor={inspector_val}"
                    )
        if violations:
            for line in violations:
                print(line)
        else:
            print("  OK — ningún inspector supera el total general de su bucket.")

        print("\nTotal general por bucket (visitas únicas ruta_item_id):")
        bucket_ri: dict[str, set[int]] = {b: set() for b in BUCKET_ORDER}
        from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
            fetch_no_realizadas_visita_rows,
        )

        for row in fetch_no_realizadas_visita_rows(desde, hasta):
            bucket = classify_contraproducencia_indicador(row.contraproducencia)
            if bucket:
                bucket_ri[bucket].add(row.ruta_item_id)
        for bucket in BUCKET_ORDER:
            print(f"  {bucket}: {len(bucket_ri[bucket])}")


if __name__ == "__main__":
    main()
