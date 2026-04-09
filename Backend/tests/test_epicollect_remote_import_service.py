"""Orquestador fetch API + import_epicollect_entry (mocks)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.domains.actuaciones.services.epicollect_remote_import_service import (
    fetch_and_import_epicollect_entry,
)


def test_fetch_and_import_validates_uuid_mismatch():
    mock_client = MagicMock()
    mock_client.fetch_entry_dict_by_uuid.return_value = {
        "ec5_uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "x": 1,
    }

    with pytest.raises(ValueError, match="no coincide"):
        fetch_and_import_epicollect_entry(
            1,
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            client=mock_client,
        )


@patch("app.domains.actuaciones.services.epicollect_remote_import_service.import_epicollect_entry")
def test_fetch_and_import_delegates(mock_import):
    act = MagicMock()
    mock_import.return_value = (act, 2)
    mock_client = MagicMock()
    u = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    mock_client.fetch_entry_dict_by_uuid.return_value = {"ec5_uuid": u, "f": 1}

    out_act, n = fetch_and_import_epicollect_entry(5, u, client=mock_client)

    assert out_act is act and n == 2
    mock_import.assert_called_once_with(5, {"ec5_uuid": u, "f": 1})
