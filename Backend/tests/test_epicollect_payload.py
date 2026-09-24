"""Utilidades de parseo EpiCollect (sin DB)."""

from __future__ import annotations

import pytest

from app.domains.actuaciones.utils.epicollect_payload import (
    build_payload_non_media_envelope,
    coalesce_epicollect_entry_payload,
    extract_ec5_entry_uuid,
    guess_mime_type_from_url,
    iter_media_urls,
)


def test_extract_uuid_from_root():
    u = "550e8400-e29b-41d4-a716-446655440000"
    assert extract_ec5_entry_uuid({"uuid": u}) == u.lower()


def test_extract_uuid_from_data_nested():
    u = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    assert extract_ec5_entry_uuid({"data": {"uuid": u}}) == u.lower()


def test_coalesce_data_list_to_first_entry():
    u = "64118497-e26b-4bef-bbed-20cd62f0b388"
    wrapped = {"data": [{"ec5_uuid": u, "1_Fecha": "07/04/2026"}]}
    flat = coalesce_epicollect_entry_payload(wrapped)
    assert flat == {"ec5_uuid": u, "1_Fecha": "07/04/2026"}
    assert extract_ec5_entry_uuid(flat) == u.lower()


def test_coalesce_passthrough_when_data_is_dict():
    inner = {"campo": 1}
    assert coalesce_epicollect_entry_payload({"data": inner}) == {"data": inner}



def test_extract_uuid_missing():
    with pytest.raises(ValueError, match="UUID"):
        extract_ec5_entry_uuid({"foo": "bar"})


def test_iter_media_urls_string():
    assert list(iter_media_urls("https://cdn.example.com/a.jpg")) == ["https://cdn.example.com/a.jpg"]


def test_iter_media_urls_list_ignora_none_y_vacio():
    assert list(iter_media_urls([None, "", "  ", "https://z.com/x.png"])) == ["https://z.com/x.png"]


def test_iter_media_urls_list_and_dict():
    urls = list(
        iter_media_urls(
            [
                "https://x.com/1.png",
                {"url": "https://x.com/2.png"},
            ]
        )
    )
    assert urls == ["https://x.com/1.png", "https://x.com/2.png"]


def test_guess_mime_jpg():
    assert guess_mime_type_from_url("https://h/x.JPG") == "image/jpeg"


def test_build_payload_non_media_quita_allowlist_en_data():
    media = frozenset({"9_Foto_de_la_fachada", "x"})
    payload = {
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "data": {
            "9_Foto_de_la_fachada": "https://cdn/a.jpg",
            "campo_texto": "ok",
            "n": 1,
        },
    }
    out = build_payload_non_media_envelope(payload, media)
    assert out == {"data": {"campo_texto": "ok", "n": 1}}
