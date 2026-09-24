"""Cliente HTTP EpiCollect (parseo y requests mockeados)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from app.integrations.epicollect.client import EpicollectApiClient, parse_export_entries_response
from app.integrations.epicollect.config import EpicollectClientConfig
from app.integrations.epicollect.errors import (
    EpicollectAuthError,
    EpicollectEntryNotFoundError,
    EpicollectHttpError,
    EpicollectNetworkError,
)


def test_parse_export_entries_official_shape():
    body = {
        "data": {
            "entries": [
                {"ec5_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "1_x": "a"},
                {"ec5_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"},
            ]
        }
    }
    assert len(parse_export_entries_response(body)) == 2


def test_parse_export_entries_data_list():
    body = {"data": [{"ec5_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}]}
    assert len(parse_export_entries_response(body)) == 1


def test_fetch_entry_by_uuid_success():
    cfg = EpicollectClientConfig(
        base_url="https://five.epicollect.net",
        project_slug="test-proj",
        form_ref=None,
        client_id=None,
        client_secret=None,
        timeout_seconds=10.0,
    )
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "data": {"entries": [{"ec5_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "k": 1}]}
    }
    session.get.return_value = response

    client = EpicollectApiClient(cfg, session=session)
    entry = client.fetch_entry_dict_by_uuid("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert entry["ec5_uuid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    session.get.assert_called_once()
    call_kw = session.get.call_args
    assert "api/export/entries/test-proj" in call_kw[0][0]
    assert call_kw[1]["params"]["uuid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_fetch_entry_by_uuid_empty_raises():
    cfg = EpicollectClientConfig(
        base_url="https://five.epicollect.net",
        project_slug="test-proj",
        form_ref=None,
        client_id=None,
        client_secret=None,
        timeout_seconds=10.0,
    )
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"data": {"entries": []}}
    session.get.return_value = response

    client = EpicollectApiClient(cfg, session=session)
    with pytest.raises(EpicollectEntryNotFoundError):
        client.fetch_entry_dict_by_uuid("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def test_fetch_entry_http_error():
    cfg = EpicollectClientConfig(
        base_url="https://five.epicollect.net",
        project_slug="test-proj",
        form_ref=None,
        client_id=None,
        client_secret=None,
        timeout_seconds=10.0,
    )
    session = MagicMock()
    response = MagicMock()
    response.status_code = 429
    session.get.return_value = response

    client = EpicollectApiClient(cfg, session=session)
    with pytest.raises(EpicollectHttpError) as ei:
        client.fetch_entry_dict_by_uuid("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert ei.value.status_code == 429


def test_fetch_entry_network_timeout():
    cfg = EpicollectClientConfig(
        base_url="https://five.epicollect.net",
        project_slug="test-proj",
        form_ref=None,
        client_id=None,
        client_secret=None,
        timeout_seconds=10.0,
    )
    session = MagicMock()
    session.get.side_effect = requests.Timeout("boom")

    client = EpicollectApiClient(cfg, session=session)
    with pytest.raises(EpicollectNetworkError):
        client.fetch_entry_dict_by_uuid("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def test_oauth_token_missing_access_token():
    cfg = EpicollectClientConfig(
        base_url="https://five.epicollect.net",
        project_slug="test-proj",
        form_ref=None,
        client_id="1",
        client_secret="secret",
        timeout_seconds=10.0,
    )
    session = MagicMock()
    post_resp = MagicMock()
    post_resp.status_code = 200
    post_resp.json.return_value = {}
    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = {"data": {"entries": [{"ec5_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}]}}

    session.post.return_value = post_resp
    session.get.return_value = get_resp

    client = EpicollectApiClient(cfg, session=session)
    with pytest.raises(EpicollectAuthError):
        client.fetch_entry_dict_by_uuid("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
