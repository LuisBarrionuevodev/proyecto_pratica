import pytest

from app.database import db
from app.models import Actuaciones
from tests.utils_seed import seed_basicos

from app.services.actuacion_service import create_actuacion_from_payload


def test_create_actuacion_ok(app):
    with app.app_context():
        seed_basicos()

        payload = {
            "orden_trabajo_numero": "2241",
            "fecha_actuacion": "12/11/2025",
            "tipo_actuacion": "INSPECCION",
            "contraproducencia": "NO_HUBO",

            "rubro_nombre": "Transporte",
            "inspectores": ["Gómez", "Luna"],

            "contribuyente": {
                "doc_nro": "30123456",
                "apellido": "Pérez",
                "nombre": "Juan",
            },

            "domicilio": {
                "calle": "Av Roca",
                "numero": "123",
            },

            "acta_inspeccion_num": "000111",

            "notificacion": {
                "acta_num": "000222",
                "motivos": ["Falta de higiene"],
            },

            "comprobacion": {
                "acta_num": "000333",
                "motivo": "Reinspección negativa",
            },

            "decomiso": {
                "acta_num": "000444",
                "kilos_total": 16.0,
            },
        }

        act = create_actuacion_from_payload(payload, mode="create")

        assert act.id is not None
        assert act.orden_trabajo_id is not None
        assert act.domicilio_id is not None
        assert len(act.inspector) == 2

        # Confirmamos persistencia real
        saved = Actuaciones.query.get(act.id)
        assert saved is not None


def test_create_actuacion_rechaza_duplicado_por_ot(app):
    with app.app_context():
        seed_basicos()

        payload = {
            "orden_trabajo_numero": "2241",
            "fecha_actuacion": "12/11/2025",
            "contraproducencia": "NO_HUBO",  # valor válido del Enum
            "rubro_nombre": "Transporte",
            "inspectores": ["Gómez"],
            "contribuyente": {"doc_nro": "30123456"},
            "domicilio": {"calle": "Av Roca", "numero": "123"},
}

        create_actuacion_from_payload(payload, mode="create")

        with pytest.raises(ValueError):
            create_actuacion_from_payload(payload, mode="create")
