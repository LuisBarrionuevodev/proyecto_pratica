"""
D1d.11fix-a7 — Diagnóstico no realizadas: KPI con contraproducencia vs cierre administrativo.

Uso:
    cd Backend
    set PYTHONPATH=.
    python scripts/diagnostico_no_realizadas_junio.py
    python scripts/diagnostico_no_realizadas_junio.py --desde 2026-06-01 --hasta 2026-06-30
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date

from sqlalchemy import and_, func

from app import create_app
from app.database import db
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    _contraproducencia_real_expr,
    _no_realizadas_administrativas_filters,
    _no_realizadas_base_query,
    _no_realizadas_operativo_filters,
    estados_iniciador_terminal_no_realizada,
    query_no_realizadas_por_tipo,
)
from app.domains.indicadores.services.indicadores_no_realizadas_service import (
    build_indicadores_no_realizadas,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    _fecha_periodo_operativo_expr,
)
from app.models import Actuaciones, Domicilio, IniciadorRuta, Rubro, RutaItem, RutaTrabajo

_CONTRAS_ESPECIALES = (
    "LOCAL CERRADO",
    "LOCAL_CERRADO",
    "NO_EXISTE_LOCAL",
    "NO SE ENCUENTRA",
    "NO_SE_ENCUENTRA",
    "DOMICILIO_INCORRECTO",
)


def _print_flujo_cierre() -> None:
    print("=" * 72)
    print("B. Flujo Completar trabajo — cierre NO_REALIZADO (código)")
    print("=" * 72)
    print(
        """
1. Campos que cambian: RutaItem.estado_ruta_item, estado_ejecucion, motivo_no_realizado,
   observaciones_ejecucion, ejecutado_at, ejecutado_por_user_id; Actuaciones.contraproducencia;
   IniciadorRuta.estado_iniciador (PENDIENTE o CERRADO_NO_EXISTE_LOCAL).
2. estado_ruta_item = NO_REALIZADO (no FINALIZADO).
3. estado_ejecucion = NO_REALIZADO.
4. ejecutado_at = datetime.utcnow() al cerrar.
5. actuacion_id ya estaba seteado al publicar la ruta (no se asigna en el cierre).
6. Contraproducencia en Actuaciones.contraproducencia (stored_contra).
7. IniciadorRuta: PENDIENTE (reencola) salvo NO_EXISTE_LOCAL -> CERRADO_NO_EXISTE_LOCAL.
8. Período Dashboard: RutaTrabajo.fecha (día operativo de la ruta).
9. KPI Dashboard (a7): todos los NO_REALIZADO con contra real (sin filtro ini).
10. Cierre administrativo final (a6 helper): solo iniciador terminal (inactive_estados).
"""
    )
    terminales = estados_iniciador_terminal_no_realizada()
    print(f"Estados terminales KPI: {', '.join(terminales)}")


def _junio_rutas_items_q(desde: date, hasta: date):
    fecha_periodo = _fecha_periodo_operativo_expr()
    return (
        db.session.query(
            RutaItem.id.label("ruta_item_id"),
            RutaItem.ruta_trabajo_id,
            RutaTrabajo.fecha.label("ruta_fecha"),
            RutaTrabajo.estado_ruta,
            RutaItem.estado_ruta_item,
            RutaItem.estado_ejecucion,
            RutaItem.ejecutado_at,
            RutaItem.actuacion_id,
            Actuaciones.id.label("act_id"),
            Actuaciones.fecha.label("act_fecha"),
            Actuaciones.tipo.label("act_tipo"),
            Actuaciones.contraproducencia,
            IniciadorRuta.id.label("iniciador_id"),
            IniciadorRuta.tipo_iniciador,
            IniciadorRuta.estado_iniciador,
            Domicilio.calle,
            Domicilio.numero,
            Rubro.nombre.label("rubro_nombre"),
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .outerjoin(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .outerjoin(Rubro, Domicilio.rubro_id == Rubro.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            RutaTrabajo.estado_ruta == "PUBLICADA",
            fecha_periodo >= desde,
            fecha_periodo <= hasta,
        )
        .order_by(RutaItem.id)
    )


def _count_criterio(
    desde: date,
    hasta: date,
    *,
    estado_ruta_item: str | None = "NO_REALIZADO",
    estado_ejecucion: str | None = "NO_REALIZADO",
    solo_contra_real: bool = True,
    requiere_actuacion: bool = True,
) -> tuple[int, int]:
    fecha_periodo = _fecha_periodo_operativo_expr()
    q = (
        db.session.query(
            func.count(func.distinct(RutaItem.id)),
            func.count(func.distinct(Actuaciones.id)),
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            RutaTrabajo.estado_ruta == "PUBLICADA",
            fecha_periodo >= desde,
            fecha_periodo <= hasta,
        )
    )
    if requiere_actuacion:
        q = q.filter(RutaItem.actuacion_id.isnot(None))
    if estado_ruta_item is not None:
        q = q.filter(RutaItem.estado_ruta_item == estado_ruta_item)
    if estado_ejecucion is not None:
        q = q.filter(RutaItem.estado_ejecucion == estado_ejecucion)
    if solo_contra_real:
        q = q.filter(_contraproducencia_real_expr())
    row = q.one()
    return int(row[0]), int(row[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico no realizadas junio")
    parser.add_argument("--desde", default="2026-06-01")
    parser.add_argument("--hasta", default="2026-06-30")
    args = parser.parse_args()
    desde = date.fromisoformat(args.desde)
    hasta = date.fromisoformat(args.hasta)

    app = create_app()
    with app.app_context():
        _print_flujo_cierre()

        print("=" * 72)
        print(f"C. RutaItems en rutas PUBLICADAS con fecha {desde}..{hasta}")
        print("=" * 72)
        rows = _junio_rutas_items_q(desde, hasta).all()
        print(f"Total ítems en rutas del período: {len(rows)}")
        for r in rows:
            ej = r.ejecutado_at.date().isoformat() if r.ejecutado_at else None
            dom = f"{r.calle or ''} {r.numero or ''}".strip() or "—"
            rub = r.rubro_nombre or "—"
            print(
                f"  ri={r.ruta_item_id} rt={r.ruta_trabajo_id} ruta_fecha={r.ruta_fecha} "
                f"estado_ruta={r.estado_ruta} eri={r.estado_ruta_item} ee={r.estado_ejecucion} "
                f"ejecutado_at={ej} act={r.actuacion_id} contra={r.contraproducencia!r} "
                f"ini={r.iniciador_id} tipo_ini={r.tipo_iniciador} est_ini={r.estado_iniciador} "
                f"dom={dom} rubro={rub}"
            )

        print()
        print("Agrupación: estado_ruta_item | estado_ejecucion | contraproducencia | cantidad")
        groups: dict[tuple[str, str, str], int] = defaultdict(int)
        for r in rows:
            eri = r.estado_ruta_item or "—"
            ee = r.estado_ejecucion or "—"
            cp = (r.contraproducencia or "—").strip() or "—"
            groups[(eri, ee, cp)] += 1
        for key in sorted(groups.keys(), key=lambda k: (-groups[k], k)):
            print(f"  {key[0]} | {key[1]} | {key[2]} | {groups[key]}")

        terminales = set(estados_iniciador_terminal_no_realizada())

        def _cuenta_intento(r) -> bool:
            return (
                r.estado_ruta_item == "NO_REALIZADO"
                and r.estado_ejecucion == "NO_REALIZADO"
                and r.contraproducencia
                and str(r.contraproducencia).strip().upper() not in {"NO HUBO", "NO_HUBO"}
            )

        def _cuenta_final(r) -> bool:
            return _cuenta_intento(r) and str(r.estado_iniciador) in terminales

        print()
        print("Tabla: contraproducencia | estado_iniciador | ruta_items | cuenta_como_final")
        admin_groups: dict[tuple[str, str], int] = defaultdict(int)
        for r in rows:
            if not _cuenta_intento(r):
                continue
            cp = (r.contraproducencia or "—").strip() or "—"
            est = str(r.estado_iniciador or "—")
            admin_groups[(cp, est)] += 1
        for (cp, est), cnt in sorted(admin_groups.items(), key=lambda x: (-x[1], x[0])):
            final = "SI" if est in terminales else "NO"
            print(f"  {cp} | {est} | {cnt} | {final}")

        print()
        print("Filas con contraproducencias operativas frecuentes:")
        for r in rows:
            raw = (r.contraproducencia or "").strip().upper().replace("_", " ")
            if any(
                raw == c.upper().replace("_", " ") or (r.contraproducencia or "") == c
                for c in _CONTRAS_ESPECIALES
            ):
                print(
                    f"  ri={r.ruta_item_id} eri={r.estado_ruta_item} ee={r.estado_ejecucion} "
                    f"contra={r.contraproducencia!r} est_ini={r.estado_iniciador} "
                    f"cuenta_intento={_cuenta_intento(r)} cuenta_final={_cuenta_final(r)}"
                )

        print()
        print("=" * 72)
        print("D. Comparación de criterios")
        print("=" * 72)
        endpoint = build_indicadores_no_realizadas(desde, hasta)
        endpoint_total = sum(
            (
                endpoint.por_tipo.inspeccion,
                endpoint.por_tipo.reinspeccion_oficio,
                endpoint.por_tipo.reinspeccion_notificacion,
                endpoint.por_tipo.denuncia,
            )
        )
        actual_q = _no_realizadas_base_query(desde, hasta).with_entities(
            func.count(func.distinct(RutaItem.id))
        ).scalar() or 0

        crit_a = _count_criterio(
            desde, hasta, estado_ruta_item="NO_REALIZADO", estado_ejecucion="NO_REALIZADO"
        )
        crit_b = _count_criterio(
            desde,
            hasta,
            estado_ruta_item="FINALIZADO",
            estado_ejecucion="NO_REALIZADO",
        )
        crit_c = _count_criterio(
            desde, hasta, estado_ruta_item=None, estado_ejecucion="NO_REALIZADO"
        )
        intento_q = (
            db.session.query(func.count(func.distinct(RutaItem.id)))
            .select_from(RutaItem)
            .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
            .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
            .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
            .filter(*_no_realizadas_operativo_filters(desde, hasta))
            .scalar()
            or 0
        )

        print("criterio | count ruta_items | actuaciones distinct | observación")
        print(
            f"actual (endpoint KPI contraproducencia) | {endpoint_total} | {actual_q} | "
            f"por_tipo={query_no_realizadas_por_tipo(desde, hasta)}"
        )
        print(
            f"intento operativo (sin filtro ini) | {intento_q} | {intento_q} | "
            "todos los NO_REALIZADO con contra real"
        )
        print(
            f"A: NO_REALIZADO+NO_REALIZADO+contra | {crit_a[0]} | {crit_a[1]} | "
            "igual a intento operativo"
        )
        print(
            f"B: FINALIZADO+NO_REALIZADO+contra | {crit_b[0]} | {crit_b[1]} | "
            "no usado en cierre real"
        )
        print(
            f"C: solo estado_ejecucion=NO_REALIZADO+contra | {crit_c[0]} | {crit_c[1]} | "
            "equivalente a intento si eri siempre NO_REALIZADO"
        )
        print()
        print(f"Endpoint inspeccion={endpoint.por_tipo.inspeccion}")
        print(f"Top contraproducencias: {endpoint.top_contraproducencias}")
        print(
            f"Filtros administrativos: {len(_no_realizadas_administrativas_filters(desde, hasta))} cláusulas"
        )


if __name__ == "__main__":
    main()
