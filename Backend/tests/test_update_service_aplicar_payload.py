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
    act.id = 1
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
            "app.domains.actuaciones.services.update_service.aplicar_edicion_domicilio_operativo",
        ) as mock_aplicar,
        patch(
            "app.domains.actuaciones.services.update_service.relevamiento_id_desde_actuacion",
            return_value=None,
        ),
        patch(
            "app.domains.actuaciones.services.update_service.resolve_iniciador_operativo_actuacion",
            return_value=None,
        ),
        patch(
            "app.domains.actuaciones.services.update_service.assert_puede_editar_domicilio_actuacion",
        ),
        patch(
            "app.domains.actuaciones.services.update_service.puede_editar_domicilio_actuacion",
            return_value=(True, None),
        ),
        patch(
            "app.domains.actuaciones.services.update_service.resolver_previas"
        ),
    ):
        from app.domains.domicilios.services.domicilio_update_service import AplicarDomicilioOutcome
        from app.domains.domicilios.schemas.domicilio_edit_policy import EditDomicilioPolicy

        mock_aplicar.return_value = AplicarDomicilioOutcome(
            domicilio=dom_nuevo,
            policy=EditDomicilioPolicy(modo="CREAR_NUEVO", motivo="test"),
            domicilio_id_anterior=None,
            domicilio_id_cambio=True,
        )
        aplicar_payload_actuacion(act, payload, ejecutar_resolver_previas=False)

    assert act.domicilio_id == 42
    assert act.domicilio is dom_nuevo
    mock_aplicar.assert_called_once()


def test_aplicar_payload_rechaza_domicilio_si_bloqueado() -> None:
    """PR7.15d: payload con calle/número falla si el domicilio no es editable."""
    import pytest

    act = MagicMock()
    act.id = 1
    act.orden_trabajo_id = 1
    act.domicilio_id = 10

    payload = {
        "domicilio": {"calle": "Otra", "numero": "9"},
        "rubro_nombre": "BAR",
        "contribuyente": {"doc_nro": "30123456", "apellido": "Pérez", "nombre": "Juan"},
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
            "app.domains.actuaciones.services.update_service.resolve_iniciador_operativo_actuacion",
            return_value=None,
        ),
        patch(
            "app.domains.actuaciones.services.update_service.puede_editar_domicilio_actuacion",
            return_value=(False, "El domicilio no puede modificarse porque el acta ya fue utilizada en un circuito posterior."),
        ),
        patch("app.domains.actuaciones.services.update_service.db") as mock_db,
    ):
        mock_db.session.get.return_value = MagicMock(calle="Vieja", numero="1")
        with pytest.raises(ValueError, match="circuito posterior"):
            aplicar_payload_actuacion(act, payload, ejecutar_resolver_previas=False)
