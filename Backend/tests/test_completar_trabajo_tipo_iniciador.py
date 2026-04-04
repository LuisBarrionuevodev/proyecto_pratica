import pytest

from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
    tipo_actuacion_esperado_para_iniciador,
    validar_tipo_actuacion_para_iniciador,
)


@pytest.mark.parametrize(
    ("ini", "esperado"),
    [
        ("RELEVAMIENTO", "INSPECCION"),
        ("DENUNCIA", "INSPECCION"),
        ("REINSPECCION_OFICIO", "REINSPECCION"),
        ("REINSPECCION_NOTIFICACION", "REINSPECCION"),
        ("VERIFICAR_INFORMAR_OFICIO", "VERIFICAR E INFORMAR"),
        ("RATIFICACION_CLAUSURA_OFICIO", "RATIFICACION DE CLAUSURA"),
        ("RATIFICACION_DECOMISO_OFICIO", "RATIFICACION DE DECOMISO"),
    ],
)
def test_tipo_esperado(ini: str, esperado: str) -> None:
    assert tipo_actuacion_esperado_para_iniciador(ini) == esperado


def test_validar_ok_cuando_coincide() -> None:
    validar_tipo_actuacion_para_iniciador(
        tipo_iniciador="RELEVAMIENTO",
        tipo_actuacion="INSPECCION",
    )


def test_validar_none_tipo_no_op() -> None:
    validar_tipo_actuacion_para_iniciador(tipo_iniciador="RELEVAMIENTO", tipo_actuacion=None)


def test_validar_falla_si_distinto() -> None:
    with pytest.raises(ValueError, match="tipo de actuación debe ser"):
        validar_tipo_actuacion_para_iniciador(
            tipo_iniciador="RELEVAMIENTO",
            tipo_actuacion="REINSPECCION",
        )


@pytest.mark.parametrize(
    "tipo",
    [
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
    ],
)
def test_validar_reinspeccion_oficio_acepta_tipos_canonicos(tipo: str) -> None:
    validar_tipo_actuacion_para_iniciador(
        tipo_iniciador="REINSPECCION_OFICIO",
        tipo_actuacion=tipo,
    )


def test_validar_reinspeccion_oficio_rechaza_reinspeccion() -> None:
    with pytest.raises(ValueError, match="REINSPECCION_OFICIO"):
        validar_tipo_actuacion_para_iniciador(
            tipo_iniciador="REINSPECCION_OFICIO",
            tipo_actuacion="REINSPECCION",
        )
