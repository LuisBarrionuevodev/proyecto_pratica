import pytest

from app.domains.rutas_trabajo.services.ruta_publicar_service import tipo_actuacion_para_iniciador


@pytest.mark.parametrize(
    ("tipo_iniciador", "esperado"),
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
def test_tipo_actuacion_para_iniciador_map(tipo_iniciador: str, esperado: str) -> None:
    assert tipo_actuacion_para_iniciador(tipo_iniciador) == esperado


def test_tipo_actuacion_para_iniciador_desconocido() -> None:
    with pytest.raises(KeyError):
        tipo_actuacion_para_iniciador("TIPO_FANTASMA")
