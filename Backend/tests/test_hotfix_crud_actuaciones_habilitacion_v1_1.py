"""HOTFIX V1.1-CRUD-ACTUACIONES.1 — habilitación en PUT /actuaciones."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.actuaciones.utils.circuito_operativo import CIRCUITO_REINSPECCION_NOTIFICACION
from app.models import Inspeccion

from tests.test_inspeccion_checklist import (
    _base_create_payload,
    _item_id,
    _legacy_put_row_dict,
    _put_actuacion,
    items_catalogo,
)


def test_put_inspeccion_con_habilitacion_persistida_edita_otro_campo_ok(
    app_ctx, items_catalogo
) -> None:
    id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
    act = crear_actuacion_desde_payload(
        _base_create_payload(
            contraproducencia=None,
            items_acta_inspeccion=[{"item_id": id_hab, "valor_si_no": True}],
        )
    )
    _put_actuacion(act)


def test_put_inspeccion_modifica_checklist_sin_habilitacion_422(
    app_ctx, items_catalogo
) -> None:
    id_bano = _item_id(items_catalogo, "TIENE_BANO")
    act = crear_actuacion_desde_payload(_base_create_payload(contraproducencia=None))
    with pytest.raises(ValidationError) as exc:
        _put_actuacion(
            act,
            items_acta_inspeccion=[{"item_id": id_bano, "estado": "BIEN"}],
        )
    assert "habilitación" in str(exc.value).lower()


def test_put_inspeccion_modifica_checklist_mantiene_habilitacion_persistida_ok(
    app_ctx, items_catalogo
) -> None:
    id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
    id_bano = _item_id(items_catalogo, "TIENE_BANO")
    act = crear_actuacion_desde_payload(
        _base_create_payload(
            contraproducencia=None,
            items_acta_inspeccion=[{"item_id": id_hab, "valor_si_no": True}],
        )
    )
    _put_actuacion(
        act,
        items_acta_inspeccion=[{"item_id": id_bano, "estado": "BIEN"}],
    )


def test_put_inspeccion_habilitacion_si_y_no_ok(app_ctx, items_catalogo) -> None:
    id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
    act = crear_actuacion_desde_payload(_base_create_payload(contraproducencia=None))
    _put_actuacion(act, items_acta_inspeccion=[{"item_id": id_hab, "valor_si_no": True}])
    _put_actuacion(act, items_acta_inspeccion=[{"item_id": id_hab, "valor_si_no": False}])


def test_put_reinspeccion_notificacion_sin_exigir_habilitacion(
    app_ctx, items_catalogo, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.domains.actuaciones.utils.inspeccion_habilitacion_validation.circuito_desde_actuacion_id",
        lambda _aid: CIRCUITO_REINSPECCION_NOTIFICACION,
    )
    act = crear_actuacion_desde_payload(
        _base_create_payload(contraproducencia=None, tipo_actuacion="REINSPECCION")
    )
    id_bano = _item_id(items_catalogo, "TIENE_BANO")
    _put_actuacion(
        act,
        items_acta_inspeccion=[{"item_id": id_bano, "estado": "BIEN"}],
    )
    ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
    assert ins is not None
