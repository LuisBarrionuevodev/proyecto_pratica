from __future__ import annotations

from datetime import date
from typing import Optional

from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    count_mapa_operativo_pendientes_cola,
)
from app.domains.indicadores.schemas.pendientes_out import (
    IndicadoresPendientesOut,
    PendientesKpis,
)


def build_indicadores_pendientes(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresPendientesOut:
    """
    Bloque pendientes: cola planificable por tipo de iniciador (geo OK).

    Parámetros:
        desde, hasta: rango sobre ``IniciadorRuta.fecha_origen`` (cola).
        distrito_id: filtro opcional.
        inspector_id: ignorado en cola (sin grupo asignado); reservado para extensión.

    Retorno:
        KPIs por tipo y tabla de distritos (vacía en D1d.4; agregación en D1d.6).

    Notas:
        ``pendientes_geolocalizacion`` devuelve 0 hasta D1d.6 (sin inventar conteos).
        ``distritos_con_mas_pendientes`` lista vacía en D1d.4.
    """
    _ = inspector_id
    desde_s = desde.isoformat()
    hasta_s = hasta.isoformat()

    return IndicadoresPendientesOut(
        kpis=PendientesKpis(
            relevamientos_pendientes=count_mapa_operativo_pendientes_cola(
                desde=desde_s,
                hasta=hasta_s,
                distrito_id=distrito_id,
                tipo="RELEVAMIENTOS",
            ),
            reinspecciones_oficio_pendientes=count_mapa_operativo_pendientes_cola(
                desde=desde_s,
                hasta=hasta_s,
                distrito_id=distrito_id,
                tipo="REINSPECCION_OFICIO",
            ),
            reinspecciones_notificacion_pendientes=count_mapa_operativo_pendientes_cola(
                desde=desde_s,
                hasta=hasta_s,
                distrito_id=distrito_id,
                tipo="NOTIFICACION_VENCIDA",
            ),
            denuncias_pendientes=count_mapa_operativo_pendientes_cola(
                desde=desde_s,
                hasta=hasta_s,
                distrito_id=distrito_id,
                tipo="DENUNCIAS",
            ),
            pendientes_geolocalizacion=0,
        ),
        distritos_con_mas_pendientes=[],
    )
