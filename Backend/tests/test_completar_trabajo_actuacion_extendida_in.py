import pytest
from pydantic import ValidationError

from app.domains.actuaciones.schemas.completar_trabajo_actuacion_extendida_in import (
    CompletarTrabajoActuacionExtendidaIn,
)


def test_extendida_sin_contra_permite_acta() -> None:
    m = CompletarTrabajoActuacionExtendidaIn(
        contraproducencia=None,
        acta_inspeccion_num="123456",
    )
    assert m.acta_inspeccion_num == "123456"


def test_extendida_con_contra_rechaza_actas() -> None:
    with pytest.raises(ValidationError) as exc:
        CompletarTrabajoActuacionExtendidaIn(
            contraproducencia="LOCAL CERRADO",
            acta_inspeccion_num="123456",
        )
    assert "contraproducencia" in str(exc.value).lower() or "actas" in str(exc.value).lower()
