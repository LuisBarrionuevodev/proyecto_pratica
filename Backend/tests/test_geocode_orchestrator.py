from app.models import Domicilio
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    compute_addr_hash,
    is_ready_for_geocode,
)


def test_compute_addr_hash_changes_when_address_changes():
    dom = Domicilio(
        calle_normalizada="Calle San Martin",
        numero="123",
        ciudad="Tucuman",
        provincia="Tucuman",
        pais="Argentina",
    )
    h1 = compute_addr_hash(dom)
    dom.numero = "124"
    h2 = compute_addr_hash(dom)
    assert h1 != h2


def test_is_ready_for_geocode_numero():
    dom = Domicilio(
        calle_normalizada="Calle San Martin",
        calle_norm_status="OK",
        numero="123",
        numero_tipo="NUMERO",
    )
    assert is_ready_for_geocode(dom) is True


def test_is_ready_for_geocode_esquina():
    dom = Domicilio(
        calle_normalizada="Calle San Martin",
        calle_norm_status="OK",
        numero_tipo="ESQUINA",
        esquina_norm_status="OK",
        esquina_catalogo_id=10,
    )
    assert is_ready_for_geocode(dom) is True


def test_is_ready_for_geocode_not_ready():
    dom = Domicilio(
        calle_normalizada="Calle San Martin",
        calle_norm_status="REVIEW",
        numero="123",
        numero_tipo="NUMERO",
    )
    assert is_ready_for_geocode(dom) is False
