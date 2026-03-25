from unittest.mock import MagicMock

from app.domains.actuaciones.mappers.completar_trabajo_cierre_mapper import (
    map_completar_trabajo_cierre_to_aplicar_payload,
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
