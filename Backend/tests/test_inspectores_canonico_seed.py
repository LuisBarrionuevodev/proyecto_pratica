"""Constantes y unicidad del seed de inspectores canónicos."""

from app.domains.grid.seeds.inspectores_canonicos import INSPECTORES_CANONICO


def test_inspectores_canonico_cantidad_y_legajos_unicos() -> None:
    legajos = [t[1] for t in INSPECTORES_CANONICO]
    assert len(INSPECTORES_CANONICO) == 24
    assert len(legajos) == len(set(legajos))
    for nombre, legajo, turno_id in INSPECTORES_CANONICO:
        assert nombre.strip() == nombre
        assert legajo.isdigit() and len(legajo) == 5
        assert turno_id == 1
    assert INSPECTORES_CANONICO[0][0] == "Accardi Jos\u00e9"
