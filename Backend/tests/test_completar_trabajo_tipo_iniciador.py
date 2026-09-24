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


@pytest.mark.parametrize(
    ("tipo_actuacion", "tipo_iniciador"),
    [
        ("VERIFICAR E INFORMAR", "VERIFICAR_INFORMAR_OFICIO"),
        ("RATIFICACION DE CLAUSURA", "RATIFICACION_CLAUSURA_OFICIO"),
        ("RATIFICACION DE DECOMISO", "RATIFICACION_DECOMISO_OFICIO"),
    ],
)
def test_tipo_iniciador_oficio_desde_tipo_actuacion(tipo_actuacion: str, tipo_iniciador: str) -> None:
    from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
        tipo_iniciador_oficio_desde_tipo_actuacion,
    )

    assert tipo_iniciador_oficio_desde_tipo_actuacion(tipo_actuacion) == tipo_iniciador


@pytest.mark.parametrize(
    ("tipo_iniciador", "esperado"),
    [
        ("RATIFICACION_CLAUSURA_OFICIO", "RATIFICACION DE CLAUSURA"),
        ("RATIFICACION_DECOMISO_OFICIO", "RATIFICACION DE DECOMISO"),
        ("VERIFICAR_INFORMAR_OFICIO", "VERIFICAR E INFORMAR"),
    ],
)
def test_validar_tipo_especifico_oficio_promovido(tipo_iniciador: str, esperado: str) -> None:
    from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
        validar_tipo_actuacion_para_iniciador,
    )

    validar_tipo_actuacion_para_iniciador(
        tipo_iniciador=tipo_iniciador,
        tipo_actuacion=esperado,
    )


def test_es_flujo_cumplimiento_oficio_ratificaciones() -> None:
    from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
        es_flujo_cumplimiento_oficio,
    )

    assert es_flujo_cumplimiento_oficio("RATIFICACION_CLAUSURA_OFICIO")
    assert es_flujo_cumplimiento_oficio("RATIFICACION_DECOMISO_OFICIO")
    assert es_flujo_cumplimiento_oficio("REINSPECCION_OFICIO")
    assert not es_flujo_cumplimiento_oficio("VERIFICAR_INFORMAR_OFICIO")


def test_es_flujo_verificar_informar() -> None:
    from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
        es_flujo_verificar_informar,
    )

    assert es_flujo_verificar_informar("VERIFICAR_INFORMAR_OFICIO")
    assert es_flujo_verificar_informar("REINSPECCION_OFICIO", "VERIFICAR E INFORMAR")
    assert not es_flujo_verificar_informar("REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA")
    assert not es_flujo_verificar_informar("RATIFICACION_CLAUSURA_OFICIO")
