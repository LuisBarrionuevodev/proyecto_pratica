"""
Campos de resultado operativo para filas Procesados (Relevamiento / Denuncia).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domains.iniciadores.services.procesados_cierre_context_service import ProcesadosCierreContext
from app.domains.iniciadores.utils.procesados_bandeja import resolver_resultado_procesado_bandeja
from app.models import IniciadorRuta
from app.utils.iniciador_estado import normalize_estado_iniciador


def _iso_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def enrich_row_procesados_bandeja(
    row: dict[str, Any],
    iniciador: IniciadorRuta,
    cierre: ProcesadosCierreContext | None,
) -> dict[str, Any]:
    """
    Agrega campos de resultado procesado a un DTO de fila existente.

    Parámetros:
        row: dict base del presenter de relevamiento/denuncia.
        iniciador: iniciador_ruta determinístico de la fila.
        cierre: último cierre del iniciador (opcional).

    Retorno:
        Copia del row con claves de bandeja Procesados.
    """
    out = dict(row)
    res = resolver_resultado_procesado_bandeja(iniciador.estado_iniciador)
    estado_norm = normalize_estado_iniciador(iniciador.estado_iniciador)
    out["iniciador_ruta_id"] = iniciador.id
    out["iniciador_estado"] = estado_norm
    out["editable"] = False
    if res:
        out["resultado_codigo"] = res.resultado_codigo
        out["resultado_label"] = res.resultado_label
    else:
        out["resultado_codigo"] = estado_norm
        out["resultado_label"] = estado_norm or "—"
    if cierre:
        out["motivo_no_realizado"] = cierre.motivo_no_realizado
        out["contraproducencia"] = cierre.contraproducencia
        out["fecha_cierre"] = _iso_dt(cierre.fecha_cierre)
        out["ejecutado_at"] = out["fecha_cierre"]
    else:
        out["motivo_no_realizado"] = None
        out["contraproducencia"] = None
        fecha_ini = iniciador.cerrado_at
        out["fecha_cierre"] = _iso_dt(fecha_ini)
        out["ejecutado_at"] = out["fecha_cierre"]
    return out
