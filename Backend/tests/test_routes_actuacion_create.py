import importlib
from datetime import date

def _patch_create_function(monkeypatch, module, fake_fn):
    candidates = [
        "crear_actuacion_desde_payload",
        "create_actuacion_from_payload",
        "crear_actuacion_from_payload",
        "crear_actuacion",  # por si
    ]
    for name in candidates:
        if hasattr(module, name):
            monkeypatch.setattr(module, name, fake_fn)
            return name
    raise AssertionError(f"No encontré función create en route. Busqué: {candidates}")





def _parse_iso_date(s: str) -> date:
    # payload["fecha_actuacion"] viene como "YYYY-MM-DD"
    return date.fromisoformat(s)


from datetime import date


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



def test_post_actuaciones_create_ok(client, monkeypatch):
    actuacion_mod = importlib.import_module("app.routes.actuacion")

    def fake_create(payload):
        return DummyActuacion(payload)  # ✅ ahora tiene to_dict()

    _patch_create_function(monkeypatch, actuacion_mod, fake_create)

    resp = client.post(
        "/actuaciones/",
        json={
            "tipo_actuacion": "INSPECCION",
            "orden_trabajo_numero": "123",
            "fecha_actuacion": "31/12/2025",
        },
    )

    assert resp.status_code in (200, 201), resp.get_data(as_text=True)
    data = resp.get_json()

    # según tu route, puede devolver dict directo o envolverlo
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    assert data["tipo_actuacion"] == "INSPECCION"
    assert data["orden_trabajo_numero"] in ("000123", "123")
    assert data["fecha_actuacion"] == "2025-12-31"


def test_post_actuaciones_validation_error_returns_422(client):
    resp = client.post(
        "/actuaciones/",
        json={
            "orden_trabajo_numero": "123",
            "fecha_actuacion": "31/12/2025",
        },
    )

    assert resp.status_code in (400, 422), resp.get_data(as_text=True)
    data = resp.get_json()
    assert data is not None
