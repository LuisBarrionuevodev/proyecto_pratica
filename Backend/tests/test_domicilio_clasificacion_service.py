"""Tests unitarios de clasificación compuesta de domicilios (PR2)."""

from __future__ import annotations

import pytest

from app.domains.geolocalizacion.geocode.services.domicilio_clasificacion_service import (
    SLICE_BAJA_CONFIANZA,
    SLICE_ERROR,
    SLICE_GEO_PENDIENTE,
    SLICE_NOMENCLATURA_PENDIENTE,
    SLICE_OK,
    SLICE_VALIDADO_MANUAL,
    clasificar_domicilio,
)
from app.models import Domicilio, DomicilioGeocode


def _dom(**kwargs) -> Domicilio:
    d = Domicilio(calle="Calle Test", numero="100")
    for k, v in kwargs.items():
        setattr(d, k, v)
    return d


def _geo(**kwargs) -> DomicilioGeocode:
    g = DomicilioGeocode(domicilio_id=1, geo_status="PENDING")
    for k, v in kwargs.items():
        setattr(g, k, v)
    return g


def test_calle_ok_geocode_ok_alto_score_slice_ok() -> None:
    dom = _dom(
        calle_norm_status="OK",
        calle_norm_score=1.0,
        calle_norm_error=None,
        distrito_id=3,
    )
    geo = _geo(
        geo_status="OK",
        source="AUTO",
        score=0.95,
        lat=-26.824,
        lng=-65.222,
    )
    out = clasificar_domicilio(dom, geo=geo)
    assert out["nomenclatura_estado"] == "NOMENCLATURA_OK"
    assert out["geocode_estado"] == "GEOCODE_OK"
    assert out["score_unificado"] >= 90
    assert out["slice"] == SLICE_OK


def test_calle_pendiente_slice_nomenclatura_pendiente() -> None:
    dom = _dom(calle_norm_status="PENDIENTE")
    out = clasificar_domicilio(dom, geo=None)
    assert out["nomenclatura_estado"] == "NOMENCLATURA_PENDIENTE"
    assert out["slice"] == SLICE_NOMENCLATURA_PENDIENTE


def test_calle_review_slice_nomenclatura_pendiente() -> None:
    dom = _dom(calle_norm_status="REVIEW", calle_norm_score=0.72)
    out = clasificar_domicilio(dom, geo=None)
    assert out["nomenclatura_estado"] == "NOMENCLATURA_REVISAR"
    assert out["slice"] == SLICE_NOMENCLATURA_PENDIENTE


def test_calle_ok_sin_geocode_slice_geo_pendiente() -> None:
    dom = _dom(calle_norm_status="OK", calle_norm_score=0.9)
    out = clasificar_domicilio(dom, geo=None)
    assert out["nomenclatura_estado"] == "NOMENCLATURA_OK"
    assert out["geocode_estado"] == "GEOCODE_PENDIENTE"
    assert out["slice"] == SLICE_GEO_PENDIENTE


def test_calle_ok_geocode_geo_pending_slice_baja_confianza() -> None:
    dom = _dom(calle_norm_status="OK", calle_norm_score=1.0, distrito_id=1)
    geo = _geo(
        geo_status="GEO_PENDING",
        source="AUTO",
        score=0.5,
        lat=-26.824,
        lng=-65.222,
    )
    out = clasificar_domicilio(dom, geo=geo)
    assert out["geocode_estado"] == "GEOCODE_REVISAR"
    assert 60 <= out["score_unificado"] <= 89
    assert out["slice"] == SLICE_BAJA_CONFIANZA


def test_geocode_error_slice_error() -> None:
    dom = _dom(calle_norm_status="OK", calle_norm_score=1.0)
    geo = _geo(geo_status="ERROR", source="AUTO", error_msg="api fail")
    out = clasificar_domicilio(dom, geo=geo)
    assert out["geocode_estado"] == "GEOCODE_ERROR"
    assert out["slice"] == SLICE_ERROR


def test_geocode_manual_ok_slice_validado_manual() -> None:
    dom = _dom(calle_norm_status="OK", calle_norm_score=1.0)
    geo = _geo(
        geo_status="OK",
        source="MANUAL",
        lat=-26.824,
        lng=-65.222,
    )
    out = clasificar_domicilio(dom, geo=geo)
    assert out["geocode_estado"] == "VALIDADO_MANUAL"
    assert out["slice"] == SLICE_VALIDADO_MANUAL


def test_calle_manual_ok_slice_validado_manual() -> None:
    dom = _dom(
        calle_norm_status="OK",
        calle_norm_error="MANUAL",
        calle_normalizada="Calle libre",
    )
    geo = _geo(geo_status="PENDING", source="AUTO")
    out = clasificar_domicilio(dom, geo=geo)
    assert out["nomenclatura_estado"] == "VALIDADO_MANUAL"
    assert out["slice"] == SLICE_VALIDADO_MANUAL
    assert "calle_manual" in out["motivos"]


def test_esquina_pendiente_slice_nomenclatura_pendiente() -> None:
    dom = _dom(
        calle_norm_status="OK",
        calle_norm_score=1.0,
        numero_tipo="ESQUINA",
        esquina_norm_status="PENDIENTE",
    )
    out = clasificar_domicilio(dom, geo=None)
    assert out["nomenclatura_estado"] == "NOMENCLATURA_PENDIENTE"
    assert out["slice"] == SLICE_NOMENCLATURA_PENDIENTE
    assert "esquina_pendiente" in out["motivos"]


@pytest.mark.parametrize(
    "calle_status,geo_status,source,distrito,geo_score",
    [
        ("PENDIENTE", None, None, None, None),
        ("OK", "OK", "AUTO", 1, 0.99),
        ("OK", "GEO_PENDING", "AUTO", None, 0.4),
        ("NO_MATCH", "ERROR", "AUTO", None, None),
    ],
)
def test_score_siempre_entre_0_y_100(
    calle_status: str,
    geo_status: str | None,
    source: str | None,
    distrito: int | None,
    geo_score: float | None,
) -> None:
    dom = _dom(
        calle_norm_status=calle_status,
        calle_norm_score=0.88 if calle_status == "OK" else None,
        distrito_id=distrito,
    )
    geo = None
    if geo_status is not None:
        geo = _geo(
            geo_status=geo_status,
            source=source or "AUTO",
            score=geo_score,
            lat=-26.8 if geo_status != "ERROR" else None,
            lng=-65.2 if geo_status != "ERROR" else None,
        )
    out = clasificar_domicilio(dom, geo=geo)
    assert 0 <= out["score_unificado"] <= 100
