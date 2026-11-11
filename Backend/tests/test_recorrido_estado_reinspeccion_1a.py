"""HOTFIX V1.1-RECORRIDO-COMP.1A — filtro Estado de reinspección sobre filas presentadas."""

from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    filtrar_recorrido_por_estado_reinspeccion,
)


def test_realizada_incluye_cumple_y_no_cumple_simple() -> None:
    items = [
        {
            "id": 1,
            "oficios_resumen": [
                {"estado_iniciador": "CUMPLIDO", "estado_ejecucion": "REALIZADO", "resultado": "CUMPLE"}
            ],
        },
        {
            "id": 2,
            "oficios_resumen": [
                {"estado_iniciador": "CUMPLIDO", "estado_ejecucion": "REALIZADO", "resultado": "NO_CUMPLE"}
            ],
        },
        {
            "id": 3,
            "oficios_resumen": [
                {"estado_iniciador": "PENDIENTE", "estado_ejecucion": "NO_REALIZADO", "resultado": "NO_CUMPLE"}
            ],
        },
        {"id": 4, "oficios_resumen": []},
    ]
    got = filtrar_recorrido_por_estado_reinspeccion(items, "REALIZADA")
    assert {r["id"] for r in got} == {1, 2}


def test_pendiente_incluye_inicial_y_contra_aunque_haya_visita_historica() -> None:
    items = [
        {"id": 10, "oficios_resumen": []},
        {
            "id": 11,
            "oficios_resumen": [
                {
                    "estado_iniciador": "PENDIENTE",
                    "estado_ejecucion": "NO_REALIZADO",
                    "ejecucion_reinspeccion": {"orden_trabajo_numero": "08888"},
                    "resultado": "NO_CUMPLE",
                }
            ],
        },
        {
            "id": 12,
            "oficios_resumen": [
                {"estado_iniciador": "CUMPLIDO", "estado_ejecucion": "REALIZADO", "resultado": "CUMPLE"}
            ],
        },
    ]
    got = filtrar_recorrido_por_estado_reinspeccion(items, "PENDIENTE")
    assert {r["id"] for r in got} == {10, 11}


def test_todos_no_filtra() -> None:
    items = [{"id": 1, "oficios_resumen": []}, {"id": 2, "oficios_resumen": []}]
    assert filtrar_recorrido_por_estado_reinspeccion(items, "") == items
    assert filtrar_recorrido_por_estado_reinspeccion(items, None) == items


def test_prefiltro_lote_sin_filas_no_consulta(app_ctx) -> None:
    from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
        prefiltrar_actuaciones_por_estado_reinspeccion,
    )

    assert prefiltrar_actuaciones_por_estado_reinspeccion([], "PENDIENTE") == []
    assert prefiltrar_actuaciones_por_estado_reinspeccion([], "REALIZADA") == []
