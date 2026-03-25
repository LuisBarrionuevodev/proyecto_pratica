from __future__ import annotations

from app.domains.rutas_trabajo.services.ruta_publicar_service import tipo_actuacion_para_iniciador


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

    Si `tipo_actuacion` es None, no valida (se mantiene el tipo ya persistido en la actuación).

    Parámetros:
        tipo_iniciador: iniciador del ítem.
        tipo_actuacion: valor ya normalizado contra catálogo (o None).

    Errores:
        ValueError: si hay desalineación iniciador ↔ tipo.
    """
    if not tipo_iniciador or tipo_actuacion is None:
        return
    esperado = tipo_actuacion_para_iniciador(tipo_iniciador)
    a = tipo_actuacion.strip().upper().replace("_", " ")
    b = esperado.strip().upper().replace("_", " ")
    a = " ".join(a.split())
    b = " ".join(b.split())
    if a != b:
        raise ValueError(
            f"Para tipo_iniciador {tipo_iniciador!r} el tipo de actuación debe ser {esperado!r} "
            f"(recibido {tipo_actuacion!r})."
        )
