"""Presenter: agrupación de actuacion_media epicollect.* para grilla/modal."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.domains.actuaciones.presenters.actuacion_presenters import (
    _epicollect_evidencias_for_grid,
)


def test_evidencias_vacias_sin_items():
    act = MagicMock()
    act.actuacion_media_items = []
    out = _epicollect_evidencias_for_grid(act)
    assert out["epicollect_evidencias_total"] == 0
    assert out["epicollect_evidencias_grupos"] == []


def test_evidencias_agrupa_y_ordena():
    m1 = MagicMock()
    m1.categoria = "epicollect.salon"
    m1.url = "https://a.example/1.jpg"
    m1.orden = 1
    m1.id = 10
    m1.mime_type = "image/jpeg"
    m0 = MagicMock()
    m0.categoria = "epicollect.salon"
    m0.url = "https://a.example/0.jpg"
    m0.orden = 0
    m0.id = 9
    m0.mime_type = "image/jpeg"
    mx = MagicMock()
    mx.categoria = "epicollect.deposito"
    mx.url = "https://a.example/d.jpg"
    mx.orden = 0
    mx.id = 3
    mx.mime_type = None

    act = MagicMock()
    act.actuacion_media_items = [m1, m0, mx]

    out = _epicollect_evidencias_for_grid(act)
    assert out["epicollect_evidencias_total"] == 3
    grupos = out["epicollect_evidencias_grupos"]
    assert len(grupos) == 2
    assert grupos[0]["categoria"] == "epicollect.salon"
    assert grupos[0]["count"] == 2
    assert grupos[0]["items"][0]["url"].endswith("0.jpg")
    assert grupos[0]["items"][1]["url"].endswith("1.jpg")
    assert grupos[1]["label"] == "Depósito"


def test_ignora_categorias_no_epicollect():
    m = MagicMock()
    m.categoria = "otra.cosa"
    m.url = "x"
    m.orden = 0
    m.id = 1
    m.mime_type = None
    act = MagicMock()
    act.actuacion_media_items = [m]
    out = _epicollect_evidencias_for_grid(act)
    assert out["epicollect_evidencias_total"] == 0
