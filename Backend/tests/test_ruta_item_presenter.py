"""Contrato mínimo del presenter de ítems de ruta (detalle / mapa)."""

from unittest.mock import MagicMock

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_item_to_min_dict


def test_ruta_item_to_min_dict_includes_tipo_iniciador_desde_relacion():
    ini = MagicMock()
    ini.tipo_iniciador = "DENUNCIA"
    ini.domicilio = None

    item = MagicMock()
    item.id = 42
    item.ruta_trabajo_id = 1
    item.ruta_grupo_id = 2
    item.iniciador_ruta_id = 10
    item.iniciador_ruta = ini
    item.orden_trabajo_id = None
    item.actuacion_id = None
    item.orden_trabajo = None
    item.estado_ruta_item = "ASIGNADO"
    item.deleted_at = None

    d = ruta_item_to_min_dict(item)
    assert d["tipo_iniciador"] == "DENUNCIA"
    assert d["iniciador_ruta_id"] == 10


def test_ruta_item_to_min_dict_tipo_iniciador_none_sin_iniciador():
    item = MagicMock()
    item.id = 1
    item.ruta_trabajo_id = 1
    item.ruta_grupo_id = 1
    item.iniciador_ruta_id = 99
    item.iniciador_ruta = None
    item.orden_trabajo_id = None
    item.actuacion_id = None
    item.orden_trabajo = None
    item.estado_ruta_item = "ASIGNADO"
    item.deleted_at = None

    d = ruta_item_to_min_dict(item)
    assert d.get("tipo_iniciador") is None
