"""Quick win perf: canal notificacion omite build_posterior_comprobacion en pendientes/expediente."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.domains.actuaciones.routes.pendientes_expediente import pendientes_expediente_list


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app


def test_pendientes_expediente_notificacion_no_llama_posterior_comprobacion(app_ctx) -> None:
    with app_ctx.test_request_context(
        "/actuaciones/pendientes/expediente?source_type=notificacion&omitir_rango_fecha=true"
    ):
        with patch(
            "app.domains.actuaciones.routes.pendientes_expediente.get_pendientes_expediente",
            return_value=[],
        ) as mock_get:
            with patch(
                "app.domains.actuaciones.routes.pendientes_expediente.build_posterior_comprobacion_por_actuacion_id",
            ) as mock_posterior:
                with patch(
                    "app.domains.actuaciones.routes.pendientes_expediente.build_notificacion_expediente_bandeja_metrics",
                    return_value=({}, {}, {}),
                ):
                    with patch(
                        "app.domains.actuaciones.routes.pendientes_expediente.build_counts_by_eo_from_actuaciones",
                        return_value={},
                    ):
                        with patch(
                            "app.domains.actuaciones.routes.pendientes_expediente.build_reinspeccion_comprobacion_por_actuacion_id",
                            return_value={},
                        ):
                            resp, code = pendientes_expediente_list()
    assert code == 200
    mock_get.assert_called_once()
    mock_posterior.assert_not_called()


def test_pendientes_expediente_comprobacion_si_llama_posterior_comprobacion(app_ctx) -> None:
    with app_ctx.test_request_context(
        "/actuaciones/pendientes/expediente?source_type=comprobacion&omitir_rango_fecha=true"
    ):
        with patch(
            "app.domains.actuaciones.routes.pendientes_expediente.get_pendientes_expediente",
            return_value=[],
        ):
            with patch(
                "app.domains.actuaciones.routes.pendientes_expediente.build_posterior_comprobacion_por_actuacion_id",
                return_value={},
            ) as mock_posterior:
                with patch(
                    "app.domains.actuaciones.routes.pendientes_expediente.build_notificacion_expediente_bandeja_metrics",
                    return_value=({}, {}, {}),
                ):
                    with patch(
                        "app.domains.actuaciones.routes.pendientes_expediente.build_counts_by_eo_from_actuaciones",
                        return_value={},
                    ):
                        with patch(
                            "app.domains.actuaciones.routes.pendientes_expediente.build_reinspeccion_comprobacion_por_actuacion_id",
                            return_value={},
                        ):
                            _resp, code = pendientes_expediente_list()
    assert code == 200
    mock_posterior.assert_called_once()
