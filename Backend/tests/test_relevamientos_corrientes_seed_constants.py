"""Constantes de la seed de relevamientos corrientes (sin BD)."""

from app.domains.relevamientos.seeds.relevamientos_corrientes_chico import (
    DIRECCIONES_SEED,
    DIRECCION_PENDIENTE_ESQUINA_MONTE_COLOMBIA,
    RUBRO_NOMBRE,
    SEED_RELEVAMIENTOS_CORRIENTES_FECHA,
)


def test_seed_cantidad_direcciones_y_rubro() -> None:
    assert len(DIRECCIONES_SEED) == 23
    assert RUBRO_NOMBRE == "Panadería"
    assert SEED_RELEVAMIENTOS_CORRIENTES_FECHA.year == 2026
    assert DIRECCION_PENDIENTE_ESQUINA_MONTE_COLOMBIA == "Monte esquina Colombia"


def test_seed_direcciones_unicas_calle_numero() -> None:
    claves = [f"{c}|{n}" for c, n in DIRECCIONES_SEED]
    assert len(claves) == len(set(claves))


def test_seed_direcciones_formato_calle_numero() -> None:
    assert DIRECCIONES_SEED[0] == ("Corrientes", "1802")
    assert DIRECCIONES_SEED[1] == ("Santa Fe", "1261")
    assert DIRECCIONES_SEED[2] == ("Av. Ejército del Norte", "840")
    assert DIRECCIONES_SEED[3] == ("Ejército del Norte", "596")
