"""Texto de calle/esquina para UI modal (sin exponer claves técnicas)."""

from __future__ import annotations

from typing import Any

from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key


def _strip(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def calle_cargada_desde_domicilio(dom) -> str | None:
    """
    Texto humano editable de calle (calle cargada / raw).

    Prioriza ``calle_raw``. No usa ``calle_key`` como valor mostrable salvo que
    no haya alternativa en ``calle``.
    """
    if dom is None:
        return None
    raw = _strip(getattr(dom, "calle_raw", None))
    calle = _strip(getattr(dom, "calle", None))
    key = _strip(getattr(dom, "calle_key", None))
    if raw:
        return raw
    if calle and key and calle.lower() == key.lower():
        return calle
    return calle


def calle_vigente_desde_domicilio(dom) -> str | None:
    """
    Calle operativa vigente para lectura (ficha / Ver actuación).

    Prioridad: ``calle_normalizada`` si el estado es OK → ``calle`` corregida →
    texto cargado. No usa ``calle_raw`` si ya hay calle vigente (el raw es el
    valor ingresado original y puede quedar desfasado tras una corrección).

    Parámetros:
        dom: instancia de domicilio o None.

    Retorno:
        Texto de calle para UI, o None si no hay dato.
    """
    if dom is None:
        return None
    estado = (_strip(getattr(dom, "calle_norm_status", None)) or "").upper()
    norm = _strip(getattr(dom, "calle_normalizada", None))
    if estado == "OK" and norm:
        return norm
    calle = _strip(getattr(dom, "calle", None))
    if calle:
        return calle
    return calle_cargada_desde_domicilio(dom)


def esquina_key_desde_domicilio(dom) -> str | None:
    """Clave técnica slug de esquina (campo ``numero`` cuando ``numero_tipo=ESQUINA``)."""
    if dom is None or getattr(dom, "numero_tipo", None) != "ESQUINA":
        return None
    num = _strip(getattr(dom, "numero", None))
    if num:
        return slug_key(num)
    raw = _strip(getattr(dom, "esquina_raw", None))
    return slug_key(raw) if raw else None


def _esquina_valor_es_clave(val: str | None, key: str | None) -> bool:
    if not val or not key:
        return False
    return val.lower() == key.lower() or slug_key(val) == key


def esquina_cargada_desde_domicilio(dom) -> str | None:
    """
    Texto humano editable de esquina para ``numero_tipo=ESQUINA``.

    Prioridad: esquina_normalizada → numero (si no es clave) → esquina_raw.
    """
    if dom is None or getattr(dom, "numero_tipo", None) != "ESQUINA":
        return None
    norm = _strip(getattr(dom, "esquina_normalizada", None))
    if norm:
        return norm
    key = esquina_key_desde_domicilio(dom)
    num = _strip(getattr(dom, "numero", None))
    raw = _strip(getattr(dom, "esquina_raw", None))
    if num and not _esquina_valor_es_clave(num, key):
        return num
    if raw and not _esquina_valor_es_clave(raw, key):
        return raw
    return None
