"""Mapa operativo: pendientes / realizados (GeoJSON)."""

from datetime import date

import pytest

from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    TIPOS_OFICIO_MAPA_OPERATIVO,
    _normalize_filtro_tipo_realizados,
    _realizado_coincide_filtro_tipo_operativo,
    _tipos_filtro_mapa_operativo,
    list_mapa_operativo_pendientes_geo,
    list_mapa_operativo_realizados_geo,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    BUCKET_RATIFICACION_CLAUSURA,
    BUCKET_RATIFICACION_DECOMISO,
    BUCKET_REINSPECCION_NOTIFICACION,
    BUCKET_REINSPECCION_OFICIO,
    BUCKET_VERIFICAR_INFORMAR,
    bucket_operativo,
)


def test_normalize_filtro_tipo_realizados() -> None:
    assert _normalize_filtro_tipo_realizados(None) is None
    assert _normalize_filtro_tipo_realizados("") is None
    assert _normalize_filtro_tipo_realizados("TODOS") is None
    assert _normalize_filtro_tipo_realizados("REINSPECCION") == "REINSPECCION"


def test_realizado_filtro_reinspeccion_oficio_generica() -> None:
    assert _realizado_coincide_filtro_tipo_operativo(
        "REINSPECCION", "REINSPECCION_OFICIO", "REINSPECCION"
    )
    assert bucket_operativo("REINSPECCION_OFICIO", "REINSPECCION") == BUCKET_REINSPECCION_OFICIO


def test_realizado_filtro_reinspeccion_notificacion() -> None:
    assert _realizado_coincide_filtro_tipo_operativo(
        "REINSPECCION", "REINSPECCION_NOTIFICACION", "REINSPECCION"
    )
    assert bucket_operativo("REINSPECCION_NOTIFICACION", "REINSPECCION") == BUCKET_REINSPECCION_NOTIFICACION


def test_realizado_filtro_ratificacion_clausura() -> None:
    assert _realizado_coincide_filtro_tipo_operativo(
        "RATIFICACION_CLAUSURA", "REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA"
    )
    assert _realizado_coincide_filtro_tipo_operativo(
        "RATIFICACION_CLAUSURA", "RATIFICACION_CLAUSURA_OFICIO", "REINSPECCION"
    )


def test_realizado_filtro_verificar_informar() -> None:
    assert _realizado_coincide_filtro_tipo_operativo(
        "VERIFICAR_INFORMAR", "VERIFICAR_INFORMAR_OFICIO", "REINSPECCION"
    )
    assert _realizado_coincide_filtro_tipo_operativo(
        "VERIFICAR_INFORMAR", "REINSPECCION_OFICIO", "VERIFICAR E INFORMAR"
    )


def test_realizado_filtro_inspeccion_relevamiento() -> None:
    assert _realizado_coincide_filtro_tipo_operativo("INSPECCION", "RELEVAMIENTO", "INSPECCION")


def test_realizado_filtro_reinspeccion_excluye_ratificacion_y_verificar() -> None:
    assert not _realizado_coincide_filtro_tipo_operativo(
        "REINSPECCION", "REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA"
    )
    assert not _realizado_coincide_filtro_tipo_operativo(
        "REINSPECCION", "REINSPECCION_OFICIO", "RATIFICACION DE DECOMISO"
    )
    assert not _realizado_coincide_filtro_tipo_operativo(
        "REINSPECCION", "REINSPECCION_OFICIO", "VERIFICAR E INFORMAR"
    )
    assert not _realizado_coincide_filtro_tipo_operativo(
        "REINSPECCION", "RATIFICACION_CLAUSURA_OFICIO", "REINSPECCION"
    )
    assert not _realizado_coincide_filtro_tipo_operativo(
        "REINSPECCION", "RATIFICACION_DECOMISO_OFICIO", "REINSPECCION"
    )
    assert not _realizado_coincide_filtro_tipo_operativo(
        "REINSPECCION", "VERIFICAR_INFORMAR_OFICIO", "REINSPECCION"
    )
    assert bucket_operativo("REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA") == BUCKET_RATIFICACION_CLAUSURA
    assert bucket_operativo("REINSPECCION_OFICIO", "RATIFICACION DE DECOMISO") == BUCKET_RATIFICACION_DECOMISO
    assert bucket_operativo("REINSPECCION_OFICIO", "VERIFICAR E INFORMAR") == BUCKET_VERIFICAR_INFORMAR


def test_realizado_filtro_ratificacion_decomiso() -> None:
    assert _realizado_coincide_filtro_tipo_operativo(
        "RATIFICACION_DECOMISO", "REINSPECCION_OFICIO", "RATIFICACION DE DECOMISO"
    )
    assert _realizado_coincide_filtro_tipo_operativo(
        "RATIFICACION_DECOMISO", "RATIFICACION_DECOMISO_OFICIO", "REINSPECCION"
    )


def test_tipos_filtro_oficio_agrupa_circuito_oficio() -> None:
    tipos = _tipos_filtro_mapa_operativo("OFICIO")
    assert tipos == TIPOS_OFICIO_MAPA_OPERATIVO


def test_pendientes_geo_exige_rango(app) -> None:
    with app.app_context():
        with pytest.raises(ValueError, match="obligatorios"):
            list_mapa_operativo_pendientes_geo(desde=None, hasta="2026-01-31")
        with pytest.raises(ValueError, match="obligatorios"):
            list_mapa_operativo_pendientes_geo(desde="2026-01-01", hasta=None)


def test_pendientes_geo_rango_vacio_ok(app) -> None:
    with app.app_context():
        out = list_mapa_operativo_pendientes_geo(
            desde="2099-01-01",
            hasta="2099-01-31",
            distrito_id=None,
            tipo=None,
            inspector_id=None,
        )
    assert out == []


def test_realizados_geo_rango_vacio_ok(app) -> None:
    with app.app_context():
        out = list_mapa_operativo_realizados_geo(
            desde=date(2099, 1, 1).isoformat(),
            hasta=date(2099, 1, 31).isoformat(),
        )
    assert out == []


def test_http_operativo_pendientes_sin_fechas_400(client, auth_headers) -> None:
    resp = client.get("/map/operativo/pendientes", headers=auth_headers)
    assert resp.status_code == 400


def test_http_operativo_pendientes_vacio_fc_200(client, auth_headers) -> None:
    resp = client.get(
        "/map/operativo/pendientes?desde=2099-01-01&hasta=2099-01-07",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("type") == "FeatureCollection"
    assert data.get("features") == []


def test_http_operativo_realizados_con_definicion_vacio_fc_200(client, auth_headers) -> None:
    """Filtro definición debe aceptarse sin error (sin datos en rango lejano)."""
    resp = client.get(
        "/map/operativo/realizados?desde=2099-01-01&hasta=2099-01-07&definicion=CLAUSURA",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("type") == "FeatureCollection"
    assert data.get("features") == []


def test_http_operativo_realizados_tipo_reinspeccion_200(client, auth_headers) -> None:
    resp = client.get(
        "/map/operativo/realizados?desde=2099-01-01&hasta=2099-01-07&tipo=REINSPECCION",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json().get("type") == "FeatureCollection"


def test_http_operativo_realizados_rubro_id_200(client, auth_headers) -> None:
    resp = client.get(
        "/map/operativo/realizados?desde=2099-01-01&hasta=2099-01-07&rubro_id=1",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("type") == "FeatureCollection"
    assert isinstance(data.get("features"), list)


def test_http_operativo_realizados_tipo_y_rubro_200(client, auth_headers) -> None:
    resp = client.get(
        "/map/operativo/realizados?desde=2099-01-01&hasta=2099-01-07"
        "&tipo=INSPECCION&rubro_id=99",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json().get("type") == "FeatureCollection"


def test_rubro_id_operativo_relevamiento_prioriza_relevamiento() -> None:
    from unittest.mock import MagicMock

    from app.domains.rutas_trabajo.utils.rubro_operativo import rubro_id_operativo_para_iniciador

    ini = MagicMock()
    ini.tipo_iniciador = "RELEVAMIENTO"
    ini.relevamiento = MagicMock(rubro_id=7)
    dom = MagicMock(rubro_id=3)
    assert rubro_id_operativo_para_iniciador(ini, dom) == 7


def test_rubro_id_operativo_domicilio_sin_relevamiento() -> None:
    from unittest.mock import MagicMock

    from app.domains.rutas_trabajo.utils.rubro_operativo import rubro_id_operativo_para_iniciador

    ini = MagicMock()
    ini.tipo_iniciador = "REINSPECCION_NOTIFICACION"
    ini.relevamiento = None
    dom = MagicMock(rubro_id=11)
    assert rubro_id_operativo_para_iniciador(ini, dom) == 11


def test_http_operativo_realizados_tipo_ratificacion_clausura_200(client, auth_headers) -> None:
    resp = client.get(
        "/map/operativo/realizados?desde=2099-01-01&hasta=2099-01-07&tipo=RATIFICACION_CLAUSURA",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json().get("type") == "FeatureCollection"

