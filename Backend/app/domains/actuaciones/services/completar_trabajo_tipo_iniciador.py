from __future__ import annotations

from app.domains.rutas_trabajo.services.ruta_publicar_service import tipo_actuacion_para_iniciador

# Al cerrar `REINSPECCION_OFICIO`, el inspector elige el tipo concreto (catálogo `Actuaciones.tipo`).
_REINSPECCION_OFICIO_TIPOS_PERMITIDOS: frozenset[str] = frozenset(
    {
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
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
    esperado = tipo_actuacion_para_iniciador(tipo_iniciador)
    a = _normalizar_tipo_actuacion_catalogo(tipo_actuacion)
    b = _normalizar_tipo_actuacion_catalogo(esperado)
    if a != b:
        raise ValueError(
            f"Para tipo_iniciador {tipo_iniciador!r} el tipo de actuación debe ser {esperado!r} "
            f"(recibido {tipo_actuacion!r})."
        )
