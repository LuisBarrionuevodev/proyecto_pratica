"""
Orquestación: API EpiCollect → payload entry → ``import_epicollect_entry``.

No duplica reglas de ``ec5_uuid``, media ni detalle; solo fetch HTTP y validación mínima.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from app.domains.actuaciones.services.epicollect_import_service import import_epicollect_entry
from app.domains.actuaciones.utils.epicollect_payload import (
    extract_ec5_entry_uuid,
    normalize_uuid_string,
)
from app.models import Actuaciones


def fetch_and_import_epicollect_entry(
    actuacion_id: int,
    ec5_uuid: str,
    *,
    client: Any | None = None,
    app_config: Dict[str, Any] | None = None,
) -> Tuple[Actuaciones, int]:
    """
    Descarga un entry desde EpiCollect y lo importa sobre la actuación indicada.

    El matching sigue siendo solo por ``actuacion_id``; ``ec5_uuid`` identifica qué entry traer.

    Args:
        actuacion_id: Actuación destino (explícita).
        ec5_uuid: UUID solicitado a la API (debe coincidir con el entry devuelto).
        client: Cliente inyectable (tests); si es None se construye con ``app_config``.
        app_config: Dict tipo ``current_app.config``; obligatorio si ``client`` es None.

    Returns:
        Misma tupla que ``import_epicollect_entry``: (actuación, cantidad media).

    Raises:
        ValueError: ``ec5_uuid`` inválido o discrepancia entry vs UUID pedido.
        EpicollectClientError: red, auth, HTTP o entry no encontrado en EpiCollect.
    """
    requested = normalize_uuid_string(ec5_uuid)
    if not requested:
        raise ValueError("ec5_uuid inválido o vacío.")

    if client is None:
        if app_config is None:
            raise ValueError("fetch_and_import_epicollect_entry: falta client o app_config.")
        from app.integrations.epicollect.client import EpicollectApiClient

        client = EpicollectApiClient.from_app_config(app_config)

    payload = client.fetch_entry_dict_by_uuid(requested)
    resolved = normalize_uuid_string(extract_ec5_entry_uuid(payload))
    if not resolved:
        raise ValueError("EpiCollect: el entry devuelto no contiene un UUID de entry válido.")
    if resolved != requested:
        raise ValueError(
            "EpiCollect: el entry devuelto no coincide con el ec5_uuid solicitado "
            f"(esperado {requested}, obtenido {resolved})."
        )

    return import_epicollect_entry(actuacion_id, payload)
