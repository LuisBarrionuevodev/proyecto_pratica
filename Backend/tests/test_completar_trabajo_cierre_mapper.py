from unittest.mock import MagicMock

from app.domains.actuaciones.mappers.completar_trabajo_cierre_mapper import (
    map_completar_trabajo_cierre_to_aplicar_payload,
    map_no_permite_inspeccion_actas_to_aplicar_payload,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)


def test_mapper_sin_ot_fecha_inspectores_ni_previas() -> None:
    row = CompletarTrabajoCierreCompletoIn.model_construct(
        tipo_actuacion="INSPECCION",
        acta_inspeccion_num="000042",
    )
    act = MagicMock()
    act.domicilio = None
    ini = MagicMock()
    ini.domicilio = None

    m = map_completar_trabajo_cierre_to_aplicar_payload(row, act=act, ini=ini)

    assert "orden_trabajo_numero" not in m
    assert "fecha_actuacion" not in m
    assert "inspectores" not in m
    assert "notificacion_previa_num" not in m
    assert "comprobacion_previa_num" not in m
    assert m.get("contraproducencia") is None
    assert m.get("tipo_actuacion") == "INSPECCION"
    assert m.get("acta_inspeccion_num") == "000042"


def test_mapper_incluye_razon_social_en_contribuyente() -> None:
    row = CompletarTrabajoCierreCompletoIn.model_construct(
        tipo_actuacion="INSPECCION",
        doc_nro="30123456789",
        contrib_apellido=None,
        contrib_nombre=None,
        razon_social="  Panadería del Sur SRL  ",
    )
    act = MagicMock()
    act.domicilio = None
    ini = MagicMock()
    ini.domicilio = None

    m = map_completar_trabajo_cierre_to_aplicar_payload(row, act=act, ini=ini)

    assert m.get("contribuyente") == {
        "doc_nro": "30123456789",
        "apellido": None,
        "nombre": None,
        "razon_social": "Panadería del Sur SRL",
    }


def test_mapper_incluye_inspectores_cuando_vienen_en_body() -> None:
    row = CompletarTrabajoCierreCompletoIn.model_construct(
        tipo_actuacion="INSPECCION",
        inspectores=["Pérez, Juan", "García, Ana"],
    )
    act = MagicMock()
    act.domicilio = None
    ini = MagicMock()
    ini.domicilio = None

    m = map_completar_trabajo_cierre_to_aplicar_payload(row, act=act, ini=ini)

    assert m.get("inspectores") == ["Pérez, Juan", "García, Ana"]


def test_map_no_permite_inspeccion_solo_comprobacion_y_clausura() -> None:
    row = CompletarTrabajoCierreCompletoIn.model_construct(
        acta_comprobacion_num="12",
        comprobacion_motivo="Falta de Higiene",
        acta_clausura_num="99",
    )
    m = map_no_permite_inspeccion_actas_to_aplicar_payload(row)
    assert "comprobacion" in m and "clausura" in m
    assert m["comprobacion"]["motivo"] == "Falta de Higiene"
