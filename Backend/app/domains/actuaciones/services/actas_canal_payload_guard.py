"""
Guardas de payload para **canales de actas** (CargarActuacion / CompletarTrabajo).

La documentación administrativa posterior (expediente de comprobación, oficio,
expediente de respuesta de oficio) solo entra por los endpoints especializados
(Esperando expediente / Esperando oficio), no por el dict canónico de actas.
"""

from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Actuaciones, IniciadorRuta

MSG_OFICIO_OPERATIVO_PUT = (
    "Los campos operativos de una Reinspección por Oficio deben corregirse "
    "mediante el canal de corrección de cierre."
)

_OFICIO_OPERATIONAL_PUT_KEYS: frozenset[str] = frozenset(
    {
        "contraproducencia",
        "limpiar_contraproducencia",
        "resultado_cumplimiento_oficio",
        "realizo_nueva_inspeccion",
    }
)


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


def _payload_intenta_modificar_campo_operativo_oficio(payload: Dict[str, Any]) -> bool:
    """True si el payload incluye algún campo operativo de reinspección por oficio."""
    if payload.get("limpiar_contraproducencia"):
        return True
    if "contraproducencia" in payload:
        return True
    if payload.get("resultado_cumplimiento_oficio") is not None:
        return True
    if "realizo_nueva_inspeccion" in payload:
        return True
    return False


def rechazar_campos_operativos_oficio_en_put_canal_actas(
    act: "Actuaciones",
    payload: Dict[str, Any],
    *,
    iniciador: "IniciadorRuta | None" = None,
) -> None:
    """
    Impide modificar campos operativos de reinspección por oficio vía PUT genérico.

    Parámetros:
        act: actuación persistida a actualizar.
        payload: dict canónico del mapper de grilla.
        iniciador: iniciador operativo ya resuelto (evita query duplicada).

    Errores:
        ValueError: si la actuación es de circuito oficio y el payload toca campos operativos.
    """
    from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
        resolve_iniciador_operativo_actuacion,
    )
    from app.domains.actuaciones.services.oficio_circuito_service import (
        es_iniciador_reinspeccion_oficio,
    )

    if not _payload_intenta_modificar_campo_operativo_oficio(payload):
        return

    ini = iniciador
    if ini is None and getattr(act, "id", None):
        ini = resolve_iniciador_operativo_actuacion(int(act.id))

    if not es_iniciador_reinspeccion_oficio(getattr(ini, "tipo_iniciador", None) if ini else None):
        return

    raise ValueError(MSG_OFICIO_OPERATIVO_PUT)
