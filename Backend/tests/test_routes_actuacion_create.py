from datetime import date
from unittest.mock import MagicMock


def _patch_create_function(monkeypatch, fake_fn):
    monkeypatch.setattr(
        "app.domains.actuaciones.routes.create.crear_actuacion_desde_payload",
        fake_fn,
    )





def _parse_iso_date(s: str) -> date:
    # payload["fecha_actuacion"] viene como "YYYY-MM-DD"
    return date.fromisoformat(s)


class DummyOT:
    def __init__(self, numero_acta: str):
        self.numero_acta = numero_acta


class DummyActuacion:
    def __init__(self, payload):
        self.payload = payload
        self.id = 1

        # presenter usa act.fecha
        fa = payload.get("fecha_actuacion")  # viene "YYYY-MM-DD" del mapper
        self.fecha = date.fromisoformat(fa) if fa else None

        # presenter usa act.tipo (NO act.tipo_actuacion)
        self.tipo = payload.get("tipo_actuacion")

        # presenter usa act.orden_trabajo.numero_acta
        ot_num = payload.get("orden_trabajo_numero")
        self.orden_trabajo = DummyOT(ot_num) if ot_num else None

        # por si el presenter toca esto (no molesta)
        self.contraproducencia = payload.get("contraproducencia")

        # relaciones opcionales que el presenter consulta con getattr(..., None)
        self.domicilio = None
        self.inspector = []
        self.inspeccion = None
        self.clausura = None
        self.decomiso = None
        self.notificacion = None
        self.comprobacion = None
        self.comprobacion_id = None



def test_post_actuaciones_create_ok(client, monkeypatch, auth_headers):
    """Bypass Pydantic grid row para probar la ruta + presenter con payload canon mínimo."""
    row = MagicMock()
    monkeypatch.setattr(
        "app.domains.actuaciones.routes.create.ActuacionGridRowIn.model_validate",
        lambda data: row,
    )
    monkeypatch.setattr(
        "app.domains.actuaciones.routes.create.map_actuacion_row",
        lambda r: {
            "tipo_actuacion": "INSPECCION",
            "orden_trabajo_numero": "123",
            "fecha_actuacion": "2025-12-31",
        },
    )

    def fake_create(payload):
        return DummyActuacion(payload)

    _patch_create_function(monkeypatch, fake_create)

    resp = client.post(
        "/actuaciones/",
        headers=auth_headers,
        json={"_test": "ignored_by_mock"},
    )

    assert resp.status_code in (200, 201), resp.get_data(as_text=True)
    data = resp.get_json()

    # según tu route, puede devolver dict directo o envolverlo
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    assert data["tipo_actuacion"] == "INSPECCION"
    assert data["orden_trabajo_numero"] in ("000123", "123")
    assert data["fecha_actuacion"] == "2025-12-31"


def test_post_actuaciones_validation_error_returns_422(client, auth_headers):
    resp = client.post(
        "/actuaciones/",
        headers=auth_headers,
        json={
            "orden_trabajo_numero": "123",
            "fecha_actuacion": "31/12/2025",
        },
    )

    assert resp.status_code in (400, 422), resp.get_data(as_text=True)
    data = resp.get_json()
    assert data is not None
