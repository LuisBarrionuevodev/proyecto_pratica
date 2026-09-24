from __future__ import annotations

from app.domains.rutas_trabajo.services.ruta_publicar_service import tipo_actuacion_para_iniciador
from app.models import IniciadorRuta

# Al cerrar `REINSPECCION_OFICIO`, el inspector elige el tipo concreto (catálogo `Actuaciones.tipo`).
_REINSPECCION_OFICIO_TIPOS_PERMITIDOS: frozenset[str] = frozenset(
    {
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
    }
)

_TIPO_ACTUACION_A_INICIADOR_OFICIO: dict[str, str] = {
    "VERIFICAR E INFORMAR": "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION DE CLAUSURA": "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION DE DECOMISO": "RATIFICACION_DECOMISO_OFICIO",
}

_TIPOS_CUMPLIMIENTO_OFICIO: frozenset[str] = frozenset(
    {
        "REINSPECCION_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    }
)

_TIPOS_INICIADOR_OFICIO_PROMOVIDO_RESET: frozenset[str] = frozenset(
    {
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    }
)


def _normalizar_tipo_actuacion_catalogo(s: str) -> str:
    a = s.strip().upper().replace("_", " ")
    return " ".join(a.split())


def tipo_actuacion_esperado_para_iniciador(tipo_iniciador: str) -> str:
    """
    Tipo de actuación (nombre de catálogo) que corresponde al iniciador según publicación de ruta.

    Parámetros:
        tipo_iniciador: valor de `IniciadorRuta.tipo_iniciador`.

    Retorno:
        Nombre canónico persistible en `Actuaciones.tipo`.

    Errores:
        KeyError: si el tipo de iniciador no está mapeado.
    """
    return tipo_actuacion_para_iniciador(tipo_iniciador)


def tipo_iniciador_oficio_desde_tipo_actuacion(tipo_actuacion: str | None) -> str | None:
    """
    Resuelve el enum específico de iniciador para un subtipo de actuación de oficio.

    Parámetros:
        tipo_actuacion: valor de catálogo (p. ej. ``VERIFICAR E INFORMAR``).

    Retorno:
        ``VERIFICAR_INFORMAR_OFICIO``, ``RATIFICACION_CLAUSURA_OFICIO``,
        ``RATIFICACION_DECOMISO_OFICIO`` o ``None`` si no es un subtipo reconocido.
    """
    if not tipo_actuacion:
        return None
    normalizado = _normalizar_tipo_actuacion_catalogo(tipo_actuacion)
    for tipo_cat, tipo_ini in _TIPO_ACTUACION_A_INICIADOR_OFICIO.items():
        if _normalizar_tipo_actuacion_catalogo(tipo_cat) == normalizado:
            return tipo_ini
    return None


def es_flujo_cumplimiento_oficio(tipo_iniciador: str | None) -> bool:
    """
    True si el iniciador usa cierre por cumplimiento de oficio/ratificación (Completar trabajo).

    Parámetros:
        tipo_iniciador: valor de ``IniciadorRuta.tipo_iniciador``.

    Retorno:
        True para ``REINSPECCION_OFICIO`` genérico y ratificaciones promovidas.
    """
    if not tipo_iniciador:
        return False
    return str(tipo_iniciador).strip().upper() in _TIPOS_CUMPLIMIENTO_OFICIO


def es_flujo_verificar_informar(
    tipo_iniciador: str | None,
    tipo_actuacion: str | None = None,
) -> bool:
    """
    True si el cierre corresponde a Verificar e informar (PR10.2c).

    Parámetros:
        tipo_iniciador: valor de ``IniciadorRuta.tipo_iniciador``.
        tipo_actuacion: subtipo elegido cuando el iniciador es ``REINSPECCION_OFICIO`` genérico.

    Retorno:
        True para iniciador promovido o subtipo verificar e informar.
    """
    if not tipo_iniciador:
        return False
    t = str(tipo_iniciador).strip().upper()
    if t == "VERIFICAR_INFORMAR_OFICIO":
        return True
    if t == "REINSPECCION_OFICIO" and tipo_actuacion:
        return (
            _normalizar_tipo_actuacion_catalogo(tipo_actuacion)
            == _normalizar_tipo_actuacion_catalogo("VERIFICAR E INFORMAR")
        )
    return False


def tipo_actuacion_fijo_para_iniciador_oficio(tipo_iniciador: str | None) -> str | None:
    """
    Tipo de actuación canónico cuando el iniciador ya es específico (post-promoción PR10.2).

    Retorno:
        Nombre de catálogo o ``None`` si el iniciador no fija subtipo.
    """
    if not tipo_iniciador:
        return None
    try:
        return tipo_actuacion_para_iniciador(str(tipo_iniciador).strip().upper())
    except KeyError:
        return None


def es_subtipo_actuacion_oficio(tipo_actuacion: str | None) -> bool:
    """
    True si ``tipo_actuacion`` es uno de los subtipos válidos de reinspección por oficio.

    Parámetros:
        tipo_actuacion: valor de catálogo ``Actuaciones.tipo``.

    Retorno:
        False si es None, vacío o no reconocido.
    """
    if not tipo_actuacion:
        return False
    normalizado = _normalizar_tipo_actuacion_catalogo(tipo_actuacion)
    permitidos = {_normalizar_tipo_actuacion_catalogo(x) for x in _REINSPECCION_OFICIO_TIPOS_PERMITIDOS}
    return normalizado in permitidos


def es_subtipo_verificar_informar(tipo_actuacion: str | None) -> bool:
    """True si el subtipo corresponde a Verificar e informar."""
    if not tipo_actuacion:
        return False
    return (
        _normalizar_tipo_actuacion_catalogo(tipo_actuacion)
        == _normalizar_tipo_actuacion_catalogo("VERIFICAR E INFORMAR")
    )


def es_subtipo_ratificacion_oficio(tipo_actuacion: str | None) -> bool:
    """True si el subtipo es ratificación de clausura o decomiso."""
    if not tipo_actuacion:
        return False
    n = _normalizar_tipo_actuacion_catalogo(tipo_actuacion)
    return n.startswith("RATIFICACION")


def sincronizar_tipo_iniciador_con_tipo_actuacion_oficio(
    ini: IniciadorRuta,
    tipo_actuacion: str,
) -> None:
    """
    Alinea ``tipo_iniciador`` con el subtipo de actuación de oficio (promoción o corrección).

    Parámetros:
        ini: iniciador persistido (mutado in-place, sin commit).
        tipo_actuacion: subtipo destino (catálogo ``Actuaciones.tipo``).

    Errores:
        ValueError: subtipo no reconocido para oficio.
    """
    if not es_subtipo_actuacion_oficio(tipo_actuacion):
        raise ValueError(
            "El tipo de actuación debe ser uno de "
            f"{sorted(_REINSPECCION_OFICIO_TIPOS_PERMITIDOS)!r} (recibido {tipo_actuacion!r})."
        )
    nuevo = tipo_iniciador_oficio_desde_tipo_actuacion(tipo_actuacion)
    if not nuevo:
        raise ValueError(f"Subtipo de actuación no reconocido para oficio: {tipo_actuacion!r}")
    ini.tipo_iniciador = nuevo


def es_iniciador_circuito_reinspeccion_oficio(tipo_iniciador: str | None) -> bool:
    """
    True si el iniciador pertenece al circuito de reinspección por oficio (genérico o promovido).

    Parámetros:
        tipo_iniciador: valor de ``IniciadorRuta.tipo_iniciador``.

    Retorno:
        False si es None, vacío o no es oficio.
    """
    if not tipo_iniciador:
        return False
    t = str(tipo_iniciador).strip().upper()
    return t == "REINSPECCION_OFICIO" or t in _TIPOS_INICIADOR_OFICIO_PROMOVIDO_RESET


def reset_iniciador_reinspeccion_oficio_generico(ini: IniciadorRuta) -> None:
    """
    Restaura ``tipo_iniciador`` al genérico tras contraproducencia reencolable (GESTIÓN-FIX.5).

    Solo transforma subtipos promovidos; si ya es ``REINSPECCION_OFICIO`` no hace nada.

    Parámetros:
        ini: iniciador persistido (mutado in-place, sin commit).
    """
    t = (ini.tipo_iniciador or "").strip().upper()
    if t in _TIPOS_INICIADOR_OFICIO_PROMOVIDO_RESET:
        ini.tipo_iniciador = "REINSPECCION_OFICIO"


def promover_iniciador_reinspeccion_oficio_segun_tipo(
    ini: IniciadorRuta,
    tipo_actuacion: str | None,
) -> None:
    """
    Si el iniciador es ``REINSPECCION_OFICIO`` genérico y el cierre fijó un subtipo concreto,
    actualiza ``tipo_iniciador`` al enum específico para conservarlo al reencolar/republicar.

    Parámetros:
        ini: iniciador del ítem cerrado (mutado in-place, sin commit).
        tipo_actuacion: subtipo elegido en Completar trabajo (catálogo ``Actuaciones.tipo``).

    Retorno:
        None.
    """
    if ini.tipo_iniciador != "REINSPECCION_OFICIO" or not tipo_actuacion:
        return
    sincronizar_tipo_iniciador_con_tipo_actuacion_oficio(ini, tipo_actuacion)


def validar_tipo_actuacion_para_iniciador(
    *,
    tipo_iniciador: str | None,
    tipo_actuacion: str | None,
) -> None:
    """
    Exige que, si se envía `tipo_actuacion`, coincida con el esperado para `tipo_iniciador`.

    Para `REINSPECCION_OFICIO` acepta uno de: ratificación clausura/decomiso o verificar e informar
    (catálogo de `Actuaciones.tipo`), no solo el tipo genérico de publicación.

    Si `tipo_actuacion` es None, no valida (se mantiene el tipo ya persistido en la actuación).

    Parámetros:
        tipo_iniciador: iniciador del ítem.
        tipo_actuacion: valor ya normalizado contra catálogo (o None).

    Errores:
        ValueError: si hay desalineación iniciador ↔ tipo.
    """
    if not tipo_iniciador or tipo_actuacion is None:
        return
    if tipo_iniciador == "REINSPECCION_OFICIO":
        a = _normalizar_tipo_actuacion_catalogo(tipo_actuacion)
        permitidos = {_normalizar_tipo_actuacion_catalogo(x) for x in _REINSPECCION_OFICIO_TIPOS_PERMITIDOS}
        if a in permitidos:
            return
        raise ValueError(
            "Para tipo_iniciador 'REINSPECCION_OFICIO' el tipo de actuación debe ser uno de "
            f"{sorted(_REINSPECCION_OFICIO_TIPOS_PERMITIDOS)!r} (recibido {tipo_actuacion!r})."
        )
    if tipo_iniciador in (
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    ):
        esperado = tipo_actuacion_para_iniciador(tipo_iniciador)
        a = _normalizar_tipo_actuacion_catalogo(tipo_actuacion)
        b = _normalizar_tipo_actuacion_catalogo(esperado)
        if a != b:
            raise ValueError(
                f"Para tipo_iniciador {tipo_iniciador!r} el tipo de actuación debe ser {esperado!r} "
                f"(recibido {tipo_actuacion!r})."
            )
        return
    esperado = tipo_actuacion_para_iniciador(tipo_iniciador)
    a = _normalizar_tipo_actuacion_catalogo(tipo_actuacion)
    b = _normalizar_tipo_actuacion_catalogo(esperado)
    if a != b:
        raise ValueError(
            f"Para tipo_iniciador {tipo_iniciador!r} el tipo de actuación debe ser {esperado!r} "
            f"(recibido {tipo_actuacion!r})."
        )
