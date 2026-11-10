from __future__ import annotations

from typing import Any

from app.models.comprobacion import SEPARADOR_TEXTO_MOTIVOS_COMPROBACION


def payload_motivos_comprobacion(comp: Any | None) -> dict[str, Any]:
    """
    Arma el contrato de lectura de motivos de comprobación (MOTIVOS.2).

    Fuente canónica: relación `motivos_catalogo`. El escalar legado
    `comprobacion_motivo` replica el texto derivado si hay vínculos; si no,
    conserva el histórico (`PENDIENTE`, vacío o texto no catalogado).

    Parámetros:
        comp: instancia `Comprobacion` o None.

    Returns:
        Dict con `motivos_comprobacion`, `motivos_comprobacion_texto` y
        `comprobacion_motivo`.
    """
    if comp is None:
        return {
            "motivos_comprobacion": [],
            "motivos_comprobacion_texto": None,
            "comprobacion_motivo": None,
        }
    nombres = [
        str(m.nombre).strip()
        for m in (comp.motivos_comprobacion_ordenados() or [])
        if getattr(m, "nombre", None)
    ]
    texto = SEPARADOR_TEXTO_MOTIVOS_COMPROBACION.join(nombres) if nombres else None
    legado = texto if nombres else getattr(comp, "motivo", None)
    return {
        "motivos_comprobacion": nombres,
        "motivos_comprobacion_texto": texto,
        "comprobacion_motivo": legado,
    }
