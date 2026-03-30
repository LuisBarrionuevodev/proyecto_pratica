from __future__ import annotations

from enum import Enum


class ContrapBucket(str, Enum):
    """Clasificación operativa tras normalizar contraproducencia."""

    NONE = "none"
    NO_EXISTE_LOCAL = "no_existe_local"
    REINGRESO_PRIORIDAD_ALTA = "reingreso_prioridad_alta"


# Valor persistido en `actuaciones.contraproducencia` para cierre sin reingreso.
STORED_NO_EXISTE_LOCAL = "NO_EXISTE_LOCAL"

# Nombre en `CatalogContraproducencia` (seed `run.py`) al que se mapean alias viejos antes del coerce Pydantic.
CATALOG_CONTRAPRODUCCION_NO_EXISTE_CANONICAL = "NO EXISTE/NO ES EL RUBRO"

# Valores de catálogo (seed `run.py`) para reingreso con prioridad alta.
STORED_REINGRESO_ALTA = frozenset(
    {
        "LOCAL CERRADO",
        "CLIMA",
        "ZONA ROJA",
        "NO_HUBO",
        "OTROS",
    }
)


def _loose_key(s: str) -> str:
    """Normaliza para comparar alias (mayúsculas, sin barra extra, espacios únicos)."""
    x = s.upper().replace("_", " ").replace("/", " ")
    return " ".join(x.split())


_NO_EXISTE_ALIAS_KEYS = frozenset(
    {
        _loose_key("NO EXISTE"),
        _loose_key("NO EXISTE / NO COINCIDE RUBRO"),
        _loose_key("NO EXISTE/NO COINCIDE RUBRO"),
        _loose_key("NO EXISTE/NO ES EL RUBRO"),
        _loose_key("NO EXISTE NO ES EL RUBRO"),
        _loose_key("NO_EXISTE_LOCAL"),
        _loose_key("NO EXISTE LOCAL"),
    }
)


def contraproducencia_es_familia_no_existe_local(raw: str) -> bool:
    """
    True si el texto pertenece a la familia operativa NO EXISTE LOCAL (misma clave suelta que `normalize_contraproducencia`).

    Sirve para emparejar el canónico seed con filas de catálogo que solo guardan p. ej. `NO_EXISTE_LOCAL`.
    """
    t = (raw or "").strip()
    if not t:
        return False
    return _loose_key(t) in _NO_EXISTE_ALIAS_KEYS


def map_contraproducencia_alias_to_catalog_nombre(raw: str) -> str:
    """
    Convierte texto legacy (p. ej. \"NO EXISTE / NO COINCIDE RUBRO\") al nombre válido en catálogo
    para que pase `CompletarTrabajoCierreIn` antes de `normalize_contraproducencia` (que persiste `NO_EXISTE_LOCAL`).
    """
    key = _loose_key(raw)
    if key in _NO_EXISTE_ALIAS_KEYS:
        return CATALOG_CONTRAPRODUCCION_NO_EXISTE_CANONICAL
    return raw


def normalize_contraproducencia(raw: str | None) -> tuple[str | None, ContrapBucket]:
    """
    Normaliza texto de contraproducencia y clasifica el bucket operativo.

    Parámetros:
        raw: valor ingresado por el usuario (puede traer guiones bajos o alias viejos).

    Retorno:
        Tupla (valor_a_persistir_en_actuacion, bucket).

    Errores:
        ValueError: si hay texto no vacío que no se puede clasificar.
    """
    if raw is None:
        return None, ContrapBucket.NONE
    s = str(raw).strip()
    if not s:
        return None, ContrapBucket.NONE

    key = _loose_key(s)
    if key in _NO_EXISTE_ALIAS_KEYS:
        return STORED_NO_EXISTE_LOCAL, ContrapBucket.NO_EXISTE_LOCAL

    # Sinónimos reingreso alta (acepta LOCAL_CERRADO, ZONA_ROJA, etc.)
    candidates = {
        _loose_key("LOCAL CERRADO"): "LOCAL CERRADO",
        _loose_key("LOCAL_CERRADO"): "LOCAL CERRADO",
        _loose_key("CLIMA"): "CLIMA",
        _loose_key("ZONA ROJA"): "ZONA ROJA",
        _loose_key("ZONA_ROJA"): "ZONA ROJA",
        _loose_key("NO HUBO"): "NO_HUBO",
        _loose_key("NO_HUBO"): "NO_HUBO",
        _loose_key("OTROS"): "OTROS",
    }
    if key in candidates:
        stored = candidates[key]
        if stored not in STORED_REINGRESO_ALTA:
            raise ValueError("Valor de contraproducencia inválido tras normalizar.")
        return stored, ContrapBucket.REINGRESO_PRIORIDAD_ALTA

    raise ValueError(
        f"Contraproducencia no reconocida: {raw!r}. "
        "Usá valores del catálogo (p. ej. LOCAL CERRADO, CLIMA, ZONA ROJA, NO_HUBO, OTROS) "
        "o variantes de no existe local normalizables."
    )


def motivo_no_realizado_para_ruta_item(stored_contra: str, bucket: ContrapBucket) -> str:
    """
    Mapea contraproducencia persistida a `RutaItem.motivo_no_realizado` (enum DB).

    Parámetros:
        stored_contra: valor guardado en actuación.
        bucket: clasificación lógica.

    Retorno:
        Uno de LOCAL_CERRADO | INCLEMENCIA_TIEMPO | NO_EXISTE_LOCAL | OTRO.
    """
    if bucket == ContrapBucket.NO_EXISTE_LOCAL:
        return "NO_EXISTE_LOCAL"
    if stored_contra == "LOCAL CERRADO":
        return "LOCAL_CERRADO"
    if stored_contra == "CLIMA":
        return "INCLEMENCIA_TIEMPO"
    if stored_contra in ("ZONA ROJA", "NO_HUBO", "OTROS"):
        return "OTRO"
    raise ValueError("No se pudo derivar motivo_no_realizado para la contraproducencia indicada.")
