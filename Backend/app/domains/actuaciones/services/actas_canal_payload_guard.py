"""
Guardas de payload para **canales de actas** (CargarActuacion / CompletarTrabajo).

La documentación administrativa posterior (expediente de comprobación, oficio,
expediente de respuesta de oficio) solo entra por los endpoints especializados
(Esperando expediente / Esperando oficio), no por el dict canónico de actas.
"""

from __future__ import annotations

from typing import Any, Dict


def rechazar_oficio_expediente_en_payload_canal_actas(payload: Dict[str, Any]) -> None:
    """
    Falla si el payload canónico de actas incluye claves de circuitos documentales.

    Es defensa en profundía además de Pydantic en rutas; no altera datos: solo valida.

    Raises:
        ValueError: si `payload` contiene `oficio` o `expediente` con valor truthy
            (objetos/dicts no vacíos cuentan como presentes).
    """
    if payload.get("oficio"):
        raise ValueError(
            "Este flujo no admite oficio. Use el flujo específico de oficio (Esperando oficio)."
        )
    if payload.get("expediente"):
        raise ValueError(
            "Este flujo no admite expediente. "
            "Use el flujo específico de expediente (Esperando expediente)."
        )
