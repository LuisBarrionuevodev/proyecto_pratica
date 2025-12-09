import pytest

from app.schemas.grid.actuacion_row import ActuacionGridRowIn
from app.mappers.grid.actuacion_row_mapper import map_actuacion_row


def base_data():
    return {
        "orden_trabajo_numero": "2241",
        "fecha_actuacion": "12/11/2025",
    }


def test_domicilio_exige_rubro_y_doc():
    data = base_data()
    data.update({
        "calle": "San Martín",
        "numero": "123",
    })
    with pytest.raises(ValueError):
        ActuacionGridRowIn(**data)


def test_notificacion_motivo_sin_acta_falla():
    data = base_data()
    data.update({
        "notificacion_motivo_1": "Falta de higiene",
    })
    with pytest.raises(ValueError):
        ActuacionGridRowIn(**data)


def test_comprobacion_motivo_sin_acta_falla():
    data = base_data()
    data.update({
        "comprobacion_motivo": "Reinspección negativa",
    })
    with pytest.raises(ValueError):
        ActuacionGridRowIn(**data)


def test_decomiso_con_acta_sin_kilos_falla():
    data = base_data()
    data.update({
        "acta_decomiso_num": "000888",
    })
    with pytest.raises(ValueError):
        ActuacionGridRowIn(**data)


def test_expediente_parcial_falla():
    data = base_data()
    data.update({
        "expediente_numero": "999",
    })
    with pytest.raises(ValueError):
        ActuacionGridRowIn(**data)


def test_mapper_no_crea_notificacion_si_no_hay_acta():
    data = base_data()
    data.update({
        "contraproducencia": "X",
        "notificacion_motivo_1": None,  # sin acta
    })
    row = ActuacionGridRowIn(**data)
    payload = map_actuacion_row(row)
    assert payload["notificacion"] is None
