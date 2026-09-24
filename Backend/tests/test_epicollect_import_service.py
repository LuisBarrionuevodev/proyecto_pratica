"""Servicio import EpiCollect (mocks, sin DB real)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.domains.actuaciones.services.epicollect_import_service import (
    EpicollectImportConflictError,
    import_epicollect_entry,
)

ENTRY_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
PAYLOAD = {
    "uuid": ENTRY_UUID,
    "data": {
        "foto_test": "https://cdn.example.com/evidence.jpg",
    },
}


def _mock_act(id_: int = 1, ec5: str | None = None):
    a = MagicMock()
    a.id = id_
    a.ec5_uuid = ec5
    return a


@patch("app.domains.actuaciones.services.epicollect_import_service.ActuacionEpicollectDetalle")
@patch("app.domains.actuaciones.services.epicollect_import_service.db.session")
@patch("app.domains.actuaciones.services.epicollect_import_service.ActuacionMedia")
@patch("app.domains.actuaciones.services.epicollect_import_service.Actuaciones")
def test_import_sets_ec5_and_inserts_media(mock_act_cls, mock_media_cls, mock_session, mock_det_cls):
    act = _mock_act()
    mock_act_cls.query.get.return_value = act

    fq = MagicMock()
    fq.first.return_value = None
    mock_act_cls.query.filter.return_value = fq

    mock_media_cls.query.filter.return_value.delete.return_value = 0
    mock_det_cls.query.filter_by.return_value.first.return_value = None

    with patch(
        "app.domains.actuaciones.services.epicollect_import_service.EPICOLLECT_MEDIA_FIELDS",
        (("foto_test", "test_cat"),),
    ):
        out_act, n = import_epicollect_entry(1, PAYLOAD)

    assert out_act is act
    assert act.ec5_uuid == ENTRY_UUID
    assert n == 1
    mock_session.add.assert_called()
    mock_session.commit.assert_called_once()


@patch("app.domains.actuaciones.services.epicollect_import_service.ActuacionEpicollectDetalle")
@patch("app.domains.actuaciones.services.epicollect_import_service.db.session")
@patch("app.domains.actuaciones.services.epicollect_import_service.ActuacionMedia")
@patch("app.domains.actuaciones.services.epicollect_import_service.Actuaciones")
def test_import_accepts_api_export_data_array(
    mock_act_cls, mock_media_cls, mock_session, mock_det_cls,
):
    """Export tipo API: ``{"data": [<entry con ec5_uuid y campos>]}``."""
    act = _mock_act()
    mock_act_cls.query.get.return_value = act
    mock_act_cls.query.filter.return_value.first.return_value = None
    mock_media_cls.query.filter.return_value.delete.return_value = 0
    mock_det_cls.query.filter_by.return_value.first.return_value = None

    wrapped = {
        "data": [
            {
                "ec5_uuid": ENTRY_UUID,
                "foto_test": "https://cdn.example.com/evidence.jpg",
            }
        ],
    }
    with patch(
        "app.domains.actuaciones.services.epicollect_import_service.EPICOLLECT_MEDIA_FIELDS",
        (("foto_test", "test_cat"),),
    ):
        out_act, n = import_epicollect_entry(1, wrapped)

    assert out_act.ec5_uuid == ENTRY_UUID
    assert n == 1


@patch("app.domains.actuaciones.services.epicollect_import_service.db.session")
@patch("app.domains.actuaciones.services.epicollect_import_service.ActuacionMedia")
@patch("app.domains.actuaciones.services.epicollect_import_service.Actuaciones")
def test_import_rejects_different_ec5_already_set(mock_act_cls, mock_media_cls, mock_session):
    act = _mock_act(ec5="11111111-1111-1111-1111-111111111111")
    mock_act_cls.query.get.return_value = act
    mock_act_cls.query.filter.return_value.first.return_value = None

    with pytest.raises(EpicollectImportConflictError):
        import_epicollect_entry(1, PAYLOAD)


@patch("app.domains.actuaciones.services.epicollect_import_service.db.session")
@patch("app.domains.actuaciones.services.epicollect_import_service.ActuacionMedia")
@patch("app.domains.actuaciones.services.epicollect_import_service.Actuaciones")
def test_import_rejects_uuid_owned_by_other_act(mock_act_cls, mock_media_cls, mock_session):
    act = _mock_act()
    mock_act_cls.query.get.return_value = act

    other = MagicMock()
    other.id = 99
    fq = MagicMock()
    fq.first.return_value = other
    mock_act_cls.query.filter.return_value = fq

    with pytest.raises(EpicollectImportConflictError):
        import_epicollect_entry(1, PAYLOAD)


@patch("app.domains.actuaciones.services.epicollect_import_service.ActuacionEpicollectDetalle")
@patch("app.domains.actuaciones.services.epicollect_import_service.db.session")
@patch("app.domains.actuaciones.services.epicollect_import_service.ActuacionMedia")
@patch("app.domains.actuaciones.services.epicollect_import_service.Actuaciones")
def test_import_same_uuid_reallowed(mock_act_cls, mock_media_cls, mock_session, mock_det_cls):
    act = _mock_act(ec5=ENTRY_UUID)
    mock_act_cls.query.get.return_value = act
    mock_act_cls.query.filter.return_value.first.return_value = None
    mock_media_cls.query.filter.return_value.delete.return_value = 1
    mock_det_cls.query.filter_by.return_value.first.return_value = None

    with patch(
        "app.domains.actuaciones.services.epicollect_import_service.EPICOLLECT_MEDIA_FIELDS",
        (),
    ):
        out_act, n = import_epicollect_entry(1, PAYLOAD)

    assert out_act.ec5_uuid == ENTRY_UUID
    assert n == 0


def test_build_media_rows_ordenes_comparten_categoria():
    from app.domains.actuaciones.services.epicollect_import_service import _build_media_rows

    payload = {
        "data": {
            "c1": "https://x.com/a.jpg",
            "c2": ["https://x.com/b.jpg", None, ""],
            "c3": "https://x.com/c.jpg",
        }
    }
    with patch(
        "app.domains.actuaciones.services.epicollect_import_service.EPICOLLECT_MEDIA_FIELDS",
        (
            ("c1", "salon_principal"),
            ("c2", "salon_principal"),
            ("c3", "acta"),
        ),
    ):
        rows = _build_media_rows(payload, 42)

    assert len(rows) == 3
    assert rows[0].categoria == "epicollect.salon_principal" and rows[0].orden == 0
    assert rows[1].categoria == "epicollect.salon_principal" and rows[1].orden == 1
    assert rows[2].categoria == "epicollect.acta" and rows[2].orden == 0
