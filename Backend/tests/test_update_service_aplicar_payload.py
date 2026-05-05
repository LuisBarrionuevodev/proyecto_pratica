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


def test_aplicar_payload_sincroniza_act_domicilio_tras_get_or_create() -> None:
    """Evita desincronía ORM: FK nuevo + relación `act.domicilio` vieja (F1.6 edición actuación)."""
    act = MagicMock()
    act.orden_trabajo_id = 1
    act.domicilio_id = None
    dom_nuevo = MagicMock()
    dom_nuevo.id = 42

    payload = {
        "domicilio": {"calle": "Nueva", "numero": "500", "numero_tipo": None},
        "rubro_nombre": "BAR",
        "contribuyente": {"doc_nro": "30123456", "apellido": "Pérez", "nombre": "Juan", "razon_social": None},
    }

    with (
        patch(
            "app.domains.actuaciones.services.update_service.get_rubro_o_falla",
            return_value=MagicMock(),
        ),
        patch(
            "app.domains.actuaciones.services.update_service.resolve_contribuyente",
            return_value=MagicMock(),
        ),
        patch(
            "app.domains.actuaciones.services.update_service.get_or_create_domicilio",
            return_value=dom_nuevo,
        ),
        patch(
            "app.domains.actuaciones.services.update_service.normalizar_domicilio_en_sesion"
        ) as mock_norm,
        patch(
            "app.domains.actuaciones.services.update_service.resolver_previas"
        ),
    ):
        aplicar_payload_actuacion(act, payload, ejecutar_resolver_previas=False)

    assert act.domicilio_id == 42
    assert act.domicilio is dom_nuevo
    mock_norm.assert_called_once()
