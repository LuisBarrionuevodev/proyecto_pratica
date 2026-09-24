"""
Clasificación compuesta read-only de domicilios (nomenclatura + geocode + score).

No modifica persistencia ni dispara geocode. Pensado para Gestión Domicilios (PR2).
"""

from __future__ import annotations

from typing import Any

from app.models import Domicilio, DomicilioGeocode

SLICE_NOMENCLATURA_PENDIENTE = "nomenclatura_pendiente"
SLICE_GEO_PENDIENTE = "geo_pendiente"
SLICE_BAJA_CONFIANZA = "baja_confianza"
SLICE_OK = "ok"
SLICE_VALIDADO_MANUAL = "validado_manual"
SLICE_ERROR = "error"
SLICE_ALL = "all"

SLICES_VALIDOS = frozenset(
    {
        SLICE_NOMENCLATURA_PENDIENTE,
        SLICE_GEO_PENDIENTE,
        SLICE_BAJA_CONFIANZA,
        SLICE_OK,
        SLICE_VALIDADO_MANUAL,
        SLICE_ERROR,
        SLICE_ALL,
    }
)


def _norm_status(value: str | None) -> str:
    return (value or "").strip().upper()


def _es_esquina(dom: Domicilio) -> bool:
    return _norm_status(getattr(dom, "numero_tipo", None)) == "ESQUINA"


def _esquina_bloquea_nomenclatura(dom: Domicilio) -> bool:
    """True si la calle puede estar OK pero la esquina impide nomenclatura plena."""
    if not _es_esquina(dom):
        return False
    esquina_status = _norm_status(getattr(dom, "esquina_norm_status", None))
    if not esquina_status:
        return True
    return esquina_status in {"PENDIENTE", "REVIEW", "NO_MATCH"}


def _nomenclatura_manual(dom: Domicilio) -> bool:
    return _norm_status(getattr(dom, "calle_norm_status", None)) == "OK" and (
        (getattr(dom, "calle_norm_error", None) or "").strip().upper() == "MANUAL"
    )


def _resolver_nomenclatura_estado(dom: Domicilio) -> str:
    """
    Mapea ``calle_norm_status`` (+ esquina) a estado de nomenclatura compuesto.

    Parámetros:
        dom: instancia ``Domicilio`` (con relación ``geocode`` opcional).

    Retorno:
        ``NOMENCLATURA_OK`` | ``NOMENCLATURA_REVISAR`` | ``NOMENCLATURA_PENDIENTE`` | ``VALIDADO_MANUAL``.
    """
    if _nomenclatura_manual(dom):
        return "VALIDADO_MANUAL"

    calle_status = _norm_status(getattr(dom, "calle_norm_status", None)) or "PENDIENTE"

    if calle_status == "OK":
        if _esquina_bloquea_nomenclatura(dom):
            esquina_status = _norm_status(getattr(dom, "esquina_norm_status", None)) or "PENDIENTE"
            if esquina_status == "REVIEW":
                return "NOMENCLATURA_REVISAR"
            return "NOMENCLATURA_PENDIENTE"
        return "NOMENCLATURA_OK"

    if calle_status == "REVIEW":
        return "NOMENCLATURA_REVISAR"

    return "NOMENCLATURA_PENDIENTE"


def _resolver_geocode_estado(dom: Domicilio, geo: DomicilioGeocode | None) -> str:
    """
    Mapea fila ``domicilio_geocode`` a estado compuesto de geocode.

    Parámetros:
        dom: domicilio (para contexto; no muta).
        geo: fila geocode o None.

    Retorno:
        Estado geocode compuesto o ``VALIDADO_MANUAL`` si pin manual OK.
    """
    _ = dom
    if geo is None or getattr(geo, "deleted_at", None) is not None:
        return "GEOCODE_PENDIENTE"

    source = (getattr(geo, "source", None) or "").strip().upper()
    geo_status = _norm_status(getattr(geo, "geo_status", None)) or "PENDING"

    if source == "MANUAL" and geo_status == "OK":
        return "VALIDADO_MANUAL"

    mapping = {
        "OK": "GEOCODE_OK",
        "GEO_PENDING": "GEOCODE_REVISAR",
        "REVIEW": "GEOCODE_REVISAR",
        "PENDING": "GEOCODE_PENDIENTE",
        "NORM_PENDING": "GEOCODE_PENDIENTE",
        "NO_MATCH": "GEOCODE_ERROR",
        "ERROR": "GEOCODE_ERROR",
    }
    return mapping.get(geo_status, "GEOCODE_PENDIENTE")


def _nomenclatura_plena_ok(nomenclatura_estado: str) -> bool:
    return nomenclatura_estado == "NOMENCLATURA_OK"


def _geocode_tiene_punto(geo: DomicilioGeocode | None) -> bool:
    if geo is None or getattr(geo, "deleted_at", None) is not None:
        return False
    return geo.lat is not None and geo.lng is not None


def _clamp_score_unit(value: float | None) -> float:
    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v < 0:
        return 0.0
    if v > 1:
        return 1.0
    return v


def calcular_score_unificado(
    dom: Domicilio,
    geo: DomicilioGeocode | None,
    *,
    nomenclatura_estado: str,
    geocode_estado: str,
) -> int:
    """
    Score conservador 0–100 a partir de campos existentes (sin Google).

    Parámetros:
        dom: domicilio evaluado.
        geo: geocode asociado o None.
        nomenclatura_estado: estado ya resuelto.
        geocode_estado: estado geocode ya resuelto.

    Retorno:
        Entero entre 0 y 100.
    """
    score = 0.0

    if _nomenclatura_plena_ok(nomenclatura_estado):
        score += 40.0
        calle_norm_score = getattr(dom, "calle_norm_score", None)
        score += 20.0 * _clamp_score_unit(calle_norm_score)

    if geocode_estado == "GEOCODE_OK" and _geocode_tiene_punto(geo):
        score += 25.0
        if geo is not None:
            score += 10.0 * _clamp_score_unit(getattr(geo, "score", None))

    if getattr(dom, "distrito_id", None) is not None:
        score += 5.0
    elif _geocode_tiene_punto(geo):
        score += 5.0

    return max(0, min(100, int(round(score))))


def _resolver_estado_compuesto(nomenclatura_estado: str, geocode_estado: str) -> str:
    if nomenclatura_estado == "VALIDADO_MANUAL" or geocode_estado == "VALIDADO_MANUAL":
        return "VALIDADO_MANUAL"
    if geocode_estado == "GEOCODE_ERROR":
        return "GEOCODE_ERROR"
    if nomenclatura_estado in {"NOMENCLATURA_PENDIENTE", "NOMENCLATURA_REVISAR"}:
        return nomenclatura_estado
    if geocode_estado == "GEOCODE_PENDIENTE":
        return "GEOCODE_PENDIENTE"
    if geocode_estado == "GEOCODE_REVISAR":
        return "GEOCODE_REVISAR"
    if nomenclatura_estado == "NOMENCLATURA_OK" and geocode_estado == "GEOCODE_OK":
        return "OK"
    return f"{nomenclatura_estado}|{geocode_estado}"


def _resolver_slice(
    *,
    nomenclatura_estado: str,
    geocode_estado: str,
    score_unificado: int,
    geo: DomicilioGeocode | None,
) -> str:
    """
    Slice operativo con prioridad fija (PR2).

    Orden:
        1. validado_manual
        2. error
        3. nomenclatura_pendiente
        4. geo_pendiente
        5. baja_confianza
        6. ok
    """
    if nomenclatura_estado == "VALIDADO_MANUAL" or geocode_estado == "VALIDADO_MANUAL":
        return SLICE_VALIDADO_MANUAL

    if geocode_estado == "GEOCODE_ERROR":
        return SLICE_ERROR

    if nomenclatura_estado in {"NOMENCLATURA_PENDIENTE", "NOMENCLATURA_REVISAR"}:
        return SLICE_NOMENCLATURA_PENDIENTE

    if geocode_estado == "GEOCODE_PENDIENTE":
        return SLICE_GEO_PENDIENTE

    if 60 <= score_unificado <= 89:
        return SLICE_BAJA_CONFIANZA

    if score_unificado >= 90 and geocode_estado == "GEOCODE_OK":
        return SLICE_OK

    if geocode_estado == "GEOCODE_REVISAR":
        return SLICE_BAJA_CONFIANZA

    if nomenclatura_estado == "NOMENCLATURA_OK" and geocode_estado == "GEOCODE_OK":
        return SLICE_OK if score_unificado >= 90 else SLICE_BAJA_CONFIANZA

    return SLICE_GEO_PENDIENTE


def _resolver_motivos(
    *,
    dom: Domicilio,
    geo: DomicilioGeocode | None,
    nomenclatura_estado: str,
    geocode_estado: str,
    score_unificado: int,
) -> list[str]:
    motivos: list[str] = []

    if _nomenclatura_manual(dom):
        motivos.append("calle_manual")
    if _esquina_bloquea_nomenclatura(dom):
        motivos.append("esquina_pendiente")
    if nomenclatura_estado == "NOMENCLATURA_REVISAR":
        motivos.append("calle_revision")
    if nomenclatura_estado == "NOMENCLATURA_PENDIENTE":
        motivos.append("calle_pendiente")
    if geo is None:
        motivos.append("sin_fila_geocode")
    elif geocode_estado == "GEOCODE_PENDIENTE":
        motivos.append("geocode_pendiente")
    elif geocode_estado == "GEOCODE_REVISAR":
        motivos.append("geocode_revision")
    elif geocode_estado == "GEOCODE_ERROR":
        motivos.append("geocode_error")
    if geo is not None and (geo.source or "").upper() == "MANUAL" and geocode_estado == "VALIDADO_MANUAL":
        motivos.append("geocode_manual")
    if 60 <= score_unificado <= 89:
        motivos.append("score_baja_confianza")
    if score_unificado >= 90 and geocode_estado == "GEOCODE_OK":
        motivos.append("score_alto")

    return motivos


def clasificar_domicilio(
    domicilio: Domicilio,
    geo: DomicilioGeocode | None = None,
) -> dict[str, Any]:
    """
    Clasifica un domicilio en estados compuestos, score y slice operativo.

    Parámetros:
        domicilio: instancia ORM ``Domicilio`` (``geocode`` opcional vía relación).
        geo: fila geocode explícita; si se omite, usa ``domicilio.geocode``.

    Retorno:
        Dict con ``nomenclatura_estado``, ``geocode_estado``, ``estado_compuesto``,
        ``score_unificado``, ``slice``, ``motivos``.
    """
    if geo is None:
        geo = getattr(domicilio, "geocode", None)
    if geo is not None and getattr(geo, "deleted_at", None) is not None:
        geo = None

    nomenclatura_estado = _resolver_nomenclatura_estado(domicilio)
    geocode_estado = _resolver_geocode_estado(domicilio, geo)
    score_unificado = calcular_score_unificado(
        domicilio,
        geo,
        nomenclatura_estado=nomenclatura_estado,
        geocode_estado=geocode_estado,
    )
    estado_compuesto = _resolver_estado_compuesto(nomenclatura_estado, geocode_estado)
    slice_val = _resolver_slice(
        nomenclatura_estado=nomenclatura_estado,
        geocode_estado=geocode_estado,
        score_unificado=score_unificado,
        geo=geo,
    )
    motivos = _resolver_motivos(
        dom=domicilio,
        geo=geo,
        nomenclatura_estado=nomenclatura_estado,
        geocode_estado=geocode_estado,
        score_unificado=score_unificado,
    )

    return {
        "nomenclatura_estado": nomenclatura_estado,
        "geocode_estado": geocode_estado,
        "estado_compuesto": estado_compuesto,
        "score_unificado": score_unificado,
        "slice": slice_val,
        "motivos": motivos,
    }


def clasificacion_coincide_slice(clasificacion: dict[str, Any], slice_param: str | None) -> bool:
    """
    True si la clasificación pertenece al slice solicitado.

    Parámetros:
        clasificacion: salida de ``clasificar_domicilio``.
        slice_param: valor de query ``slice`` o None / ``all``.

    Retorno:
        True si debe incluirse en la respuesta filtrada.
    """
    if not slice_param or slice_param == SLICE_ALL:
        return True
    if slice_param not in SLICES_VALIDOS:
        return True
    return clasificacion.get("slice") == slice_param
