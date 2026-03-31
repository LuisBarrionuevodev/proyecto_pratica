import pytest
from pydantic import ValidationError

from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)


def test_completo_in_rechaza_actas_con_contraproducencia(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                contraproducencia="LOCAL CERRADO",
                acta_inspeccion_num="123456",
            )
    assert "contraproducencia" in str(exc.value).lower() or "actas" in str(exc.value).lower()


def test_completo_in_permite_actas_sin_contra(app) -> None:
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            tipo_actuacion="INSPECCION",
            acta_inspeccion_num="123456",
        )
    assert m.acta_inspeccion_num == "123456"


def test_completo_in_exige_motivo_si_acta_comprobacion(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                tipo_actuacion="INSPECCION",
                acta_comprobacion_num="123456",
            )
    assert "motivo" in str(exc.value).lower()


def test_completo_in_permite_comprobacion_con_motivo(app) -> None:
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            tipo_actuacion="INSPECCION",
            acta_comprobacion_num="123456",
            comprobacion_motivo="Falta de higiene",
        )
    assert m.acta_comprobacion_num == "123456"
    assert m.comprobacion_motivo == "Falta de higiene"


def test_completo_in_exige_motivo_si_acta_notificacion(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                tipo_actuacion="INSPECCION",
                acta_notificacion_num="123456",
            )
    assert "motivo" in str(exc.value).lower()


def test_completo_in_permite_notificacion_con_motivo(app) -> None:
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            tipo_actuacion="INSPECCION",
            acta_notificacion_num="123456",
            notificacion_motivo_1="Cualquier",
        )
    assert m.acta_notificacion_num == "123456"
    assert m.notificacion_motivo_1 == "Cualquier"
