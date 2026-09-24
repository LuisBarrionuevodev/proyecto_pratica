from __future__ import annotations

import re
from typing import Any

from app.domains.relevamientos.utils.relevamiento_campos_normalizers import (
    normalizar_angulo_esquina,
    normalizar_nombre_fantasia,
)

_SPACE_RE = re.compile(r"\s+")


def _clean_str(v: Any) -> str:
    s = ("" if v is None else str(v)).strip()
    return s


def normalizar_campos_establecimiento_para_clave(
    nombre_fantasia: str | None,
    angulo_esquina: str | None,
) -> tuple[str | None, str | None]:
    """
    Normaliza nombre fantasía y ángulo para claves de duplicado (comparación estable).

    Parámetros:
        nombre_fantasia, angulo_esquina: valores crudos o persistidos.

    Retorno:
        Tupla (nombre_clave, angulo_clave); ambos None si vacíos.
    """
    nf = normalizar_nombre_fantasia(nombre_fantasia)
    nf_key = None if nf is None else _SPACE_RE.sub(" ", nf).upper()
    ang_key = None
    if angulo_esquina is not None and str(angulo_esquina).strip():
        try:
            ang_key = normalizar_angulo_esquina(angulo_esquina)
        except ValueError:
            ang_key = None
    return nf_key, ang_key


def build_relevamiento_location_key(calle: str, numero: str) -> str:
    """
    Clave estable para comparar “misma ubicación” en grilla/lote (calle + número o texto de esquina).
    """
    c = _clean_str(calle).upper()
    c = _SPACE_RE.sub(" ", c)
    n = _clean_str(numero).upper()
    n = _SPACE_RE.sub(" ", n)
    return f"{c}|{n}"


def _period_suffix(mes: int, anio: int) -> str:
    return f"|M{mes}|Y{anio}"


def build_relevamiento_establishment_key(
    calle: str,
    numero: str,
    *,
    mes: int,
    anio: int,
    rubro_id: int | None = None,
    nombre_fantasia: str | None = None,
    angulo_esquina: str | None = None,
    es_esquina: bool = True,
) -> str:
    """
    Clave compuesta de establecimiento para grilla/lote.

    - ESQUINA: ubicación + rubro + nombre + ángulo + mes/año.
    - NUMERO/OTRO: ubicación + rubro + nombre + mes/año (sin ángulo).
    """
    base = build_relevamiento_location_key(calle, numero)
    nf_key, ang_key = normalizar_campos_establecimiento_para_clave(nombre_fantasia, angulo_esquina)
    rub = "" if rubro_id is None else str(rubro_id)
    nf = "" if nf_key is None else nf_key
    period = _period_suffix(mes, anio)
    if es_esquina:
        ang = "" if ang_key is None else ang_key
        return f"{base}|R{rub}|NF{nf}|A{ang}{period}"
    return f"{base}|R{rub}|NF{nf}|NUM{period}"


def build_relevamiento_establishment_key_domicilio(
    domicilio_id: int,
    *,
    mes: int,
    anio: int,
    rubro_id: int | None = None,
    nombre_fantasia: str | None = None,
    angulo_esquina: str | None = None,
    es_esquina: bool = True,
) -> str:
    """
    Clave de establecimiento por domicilio_id (persistencia / auditoría).

    Parámetros:
        domicilio_id: id del domicilio.
        mes, anio: período operativo del relevamiento.
        rubro_id, nombre_fantasia, angulo_esquina: discriminadores normalizados.
        es_esquina: True incluye ángulo; False clave NUMERO/OTRO.

    Retorno:
        Clave estable para agrupar o detectar colisiones.
    """
    nf_key, ang_key = normalizar_campos_establecimiento_para_clave(nombre_fantasia, angulo_esquina)
    rub = "" if rubro_id is None else str(rubro_id)
    nf = "" if nf_key is None else nf_key
    period = _period_suffix(mes, anio)
    if es_esquina:
        ang = "" if ang_key is None else ang_key
        return f"D{domicilio_id}|R{rub}|NF{nf}|A{ang}{period}"
    return f"D{domicilio_id}|R{rub}|NF{nf}|NUM{period}"
