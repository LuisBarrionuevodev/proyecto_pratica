"""
PR11.1d — Script de diagnóstico para bloqueos al publicar ruta.

Uso:
    cd Backend
    set PYTHONPATH=.
    py scripts/debug_publicar_iniciador.py --iniciador-id 123
    py scripts/debug_publicar_iniciador.py --orden-trabajo-id 456
    py scripts/debug_publicar_iniciador.py --numero-ot 001002 --anio 2026
"""

from __future__ import annotations

import argparse
import json
import sys

from app import create_app
from app.domains.rutas_trabajo.utils.ruta_publicar_diagnostico import (
    diagnosticar_iniciador_publicar,
    diagnosticar_orden_trabajo,
)


def _print_section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PR11.1d — Diagnóstico de bloqueos al publicar ruta"
    )
    parser.add_argument("--iniciador-id", type=int, help="PK de iniciador_ruta")
    parser.add_argument("--orden-trabajo-id", type=int, help="PK de orden_trabajo")
    parser.add_argument("--numero-ot", type=str, help="Número de OT (con --anio)")
    parser.add_argument("--anio", type=int, help="Año de la OT")
    parser.add_argument("--json", action="store_true", help="Salida JSON cruda")
    args = parser.parse_args()

    if not args.iniciador_id and not args.orden_trabajo_id and not args.numero_ot:
        parser.error("Indicá --iniciador-id o --orden-trabajo-id o --numero-ot con --anio")

    app = create_app()
    with app.app_context():
        if args.iniciador_id:
            informe = diagnosticar_iniciador_publicar(args.iniciador_id)
        else:
            informe = diagnosticar_orden_trabajo(
                orden_trabajo_id=args.orden_trabajo_id,
                numero=args.numero_ot,
                anio=args.anio,
            )

        if args.json:
            print(json.dumps(informe, indent=2, ensure_ascii=False, default=str))
            return 0

        if "error" in informe:
            print(informe["error"])
            return 1

        if args.iniciador_id:
            _print_iniciador(informe)
        else:
            _print_orden_trabajo(informe)

    return 0


def _print_iniciador(informe: dict) -> None:
    ini = informe["iniciador"]
    _print_section(f"Iniciador {ini['id']}")
    print(f"  tipo:    {ini['tipo']}")
    print(f"  estado:  {ini['estado']}")
    print(f"  fuentes: {json.dumps(ini['fuentes'], ensure_ascii=False)}")
    print(f"  actuacion_reintento_detectada: {informe.get('actuacion_reintento_detectada')}")

    _print_section("RutaItems asociados")
    for row in informe.get("ruta_items", []):
        print(
            f"  item={row['item_id']} ruta={row['ruta_id']} fecha={row['ruta_fecha']} "
            f"estado_ruta={row['estado_ruta']} item={row['estado_item']}/"
            f"{row['estado_ejecucion']} deleted={row['deleted_at']} "
            f"OT={row['numero_ot']}({row['orden_trabajo_id']}) act={row['actuacion_id']} "
            f"reserva_ot={row['reserva_ot_en_item']}"
        )

    _print_section("Actuaciones asociadas")
    for row in informe.get("actuaciones", []):
        print(
            f"  act={row['actuacion_id']} tipo={row['tipo']} "
            f"contra={row['contraproducencia']!r} OT={row['numero_ot']} "
            f"noti={row['notificacion_id']} reserva_ot={row['reserva_ot']}"
        )

    bloqueos = informe.get("bloqueos_ot_en_borrador") or []
    _print_section(f"Bloqueos OT en borrador ({len(bloqueos)})")
    if not bloqueos:
        print("  (ninguno detectado por buscar_conflicto_orden_trabajo_al_publicar)")
    for b in bloqueos:
        c = b["conflicto"]
        print(
            f"  borrador item={b['item_borrador_id']} ruta={b['ruta_borrador_id']} "
            f"OT={b['numero_ot']} -> bloquea act={c['actuacion_bloqueante_id']} "
            f"item={c['item_bloqueante_id']} estado={c['estado_item']}/{c['estado_ejecucion']} "
            f"contra={c['contraproducencia']!r} deberia_bloquear={c['deberia_bloquear_pr11_1c']}"
        )

    sims = informe.get("simulacion_resolver_borrador") or []
    _print_section(f"Simulación resolver (PR11.1f) — {len(sims)} ítem(s) borrador")
    for sim in sims:
        if "error" in sim:
            print(f"  item={sim['item_id']}: {sim['error']}")
            continue
        print(f"\n  Resolver para item {sim['item_id']} / OT {sim['orden_trabajo_id']}:")
        act_ot = sim.get("actuacion_con_ot_objetivo")
        if act_ot:
            print(
                f"    - actuación con OT objetivo: {act_ot['actuacion_id']} "
                f"(contra={act_ot['contraproducencia']!r})"
            )
        else:
            print("    - actuación con OT objetivo: (ninguna)")
        print(f"    - reintento detectado: {sim.get('actuacion_reintento')}")
        print(f"    - resuelta por resolver: {sim.get('actuacion_resuelta_id')}")
        print(f"    - decisión: {sim.get('decision')}")
        occ = sim.get("actuacion_ocupante_ot")
        if occ:
            print(
                f"    - ocupante OT: act={occ['actuacion_id']} "
                f"mismo_iniciador={occ['mismo_iniciador']} "
                f"contra={occ['contraproducencia']!r}"
            )
        for cand in sim.get("candidatas_reutilizables") or []:
            print(
                f"    - candidata act={cand['actuacion_id']} OT={cand['orden_trabajo_id']} "
                f"reusable={cand['reusable']} mismo_ini={cand['mismo_iniciador']} "
                f"contra={cand['contraproducencia']!r}"
            )


def _print_orden_trabajo(informe: dict) -> None:
    ot = informe["orden_trabajo"]
    _print_section(f"Orden de trabajo {ot['numero_acta']} / {ot['anio']} (id={ot['id']})")
    _print_section("Actuaciones con esta OT")
    for row in informe.get("actuaciones", []):
        print(
            f"  act={row['id']} tipo={row['tipo']} contra={row['contraproducencia']!r} "
            f"noti={row['notificacion_id']} reserva_ot={row['reserva_ot']}"
        )
    _print_section("RutaItems con esta OT")
    for row in informe.get("ruta_items", []):
        print(
            f"  item={row['id']} ruta={row['ruta_id']} ini={row['iniciador_id']} "
            f"estado={row['estado_item']}/{row['estado_ejecucion']} "
            f"deleted={row['deleted_at']} reserva_ot={row['reserva_ot']}"
        )


if __name__ == "__main__":
    sys.exit(main())
