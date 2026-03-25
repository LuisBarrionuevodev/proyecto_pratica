"""Fase 2: `aplicar_payload_actuacion` reutilizable sin commit."""

from unittest.mock import MagicMock, patch

from app.domains.actuaciones.services.update_service import aplicar_payload_actuacion


def test_aplicar_payload_llama_resolver_previas_por_defecto() -> None:
    act = MagicMock()
    act.orden_trabajo_id = 1
    payload: dict = {}

    with patch(
        "app.domains.actuaciones.services.update_service.resolver_previas"
    ) as mock_rp:
        aplicar_payload_actuacion(act, payload)
        mock_rp.assert_called_once_with(act, payload)


def test_aplicar_payload_omite_resolver_previas_cuando_flag_false() -> None:
    act = MagicMock()
    act.orden_trabajo_id = 1
    payload: dict = {}

    with patch(
        "app.domains.actuaciones.services.update_service.resolver_previas"
    ) as mock_rp:
        aplicar_payload_actuacion(act, payload, ejecutar_resolver_previas=False)
        mock_rp.assert_not_called()
