import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.models import CatalogContraproducencia, CatalogTipoActuacion

_TIPO_INSPECCION = "INSPECCION"


def _ensure_catalog_tipo_actuacion(app, nombre: str) -> None:
    """Idempotente: solo `digitaliza_test` vía fixture `app` del conftest."""
    with app.app_context():
        if CatalogTipoActuacion.query.filter_by(nombre=nombre).first() is None:
            db.session.add(CatalogTipoActuacion(nombre=nombre))
            db.session.commit()


def _ensure_catalog_contraproducencia(app, nombre: str) -> None:
    with app.app_context():
        if CatalogContraproducencia.query.filter_by(nombre=nombre).first() is None:
            db.session.add(CatalogContraproducencia(nombre=nombre))
            db.session.commit()


@pytest.fixture(autouse=True)
def _completar_cierre_schema_catalog_tipo(app) -> None:
    """
    El schema coerce `tipo_actuacion` contra `CatalogTipoActuacion` en BD.
    Sin este seed, los tests fallan antes de evaluar reglas de negocio del schema.
    """
    _ensure_catalog_tipo_actuacion(app, _TIPO_INSPECCION)
    yield


def test_completo_in_rechaza_actas_con_contraproducencia(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                contraproducencia="LOCAL CERRADO",
                acta_inspeccion_num="123456",
            )
    assert "contraproducencia" in str(exc.value).lower() or "actas" in str(exc.value).lower()


def test_completo_in_permite_actas_sin_contra(app) -> None:
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            tipo_actuacion="INSPECCION",
            acta_inspeccion_num="123456",
        )
    assert m.acta_inspeccion_num == "123456"


def test_completo_in_permite_razon_social_sin_apellido(app) -> None:
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            tipo_actuacion="INSPECCION",
            doc_nro="30123456789",
            razon_social="Empresa Demo SA",
        )
    assert m.razon_social == "Empresa Demo SA"
    assert m.contrib_apellido is None


def test_completo_in_exige_motivo_si_acta_comprobacion(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                tipo_actuacion="INSPECCION",
                acta_comprobacion_num="123456",
            )
    assert "motivo" in str(exc.value).lower()


def test_completo_in_permite_comprobacion_con_motivo(app) -> None:
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            tipo_actuacion="INSPECCION",
            acta_comprobacion_num="123456",
            comprobacion_motivo="Falta de higiene",
        )
    assert m.acta_comprobacion_num == "123456"
    assert m.comprobacion_motivo == "Falta de higiene"


def test_completo_in_exige_motivo_si_acta_notificacion(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                tipo_actuacion="INSPECCION",
                acta_notificacion_num="123456",
            )
    assert "motivo" in str(exc.value).lower()


def test_completo_in_permite_notificacion_con_motivo(app) -> None:
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            tipo_actuacion="INSPECCION",
            acta_notificacion_num="123456",
            notificacion_motivo_1="Cualquier",
        )
    assert m.acta_notificacion_num == "123456"
    assert m.notificacion_motivo_1 == "Cualquier"


def test_completo_in_no_permite_inspeccion_permite_comprobacion_y_clausura(app) -> None:
    _ensure_catalog_contraproducencia(app, "NO PERMITE INSPECCION")
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            contraproducencia="NO PERMITE INSPECCION",
            acta_comprobacion_num="111111",
            comprobacion_motivo="No Permite la Inspección",
            acta_clausura_num="222222",
        )
    assert m.acta_comprobacion_num == "111111"
    assert m.acta_clausura_num == "222222"


def test_completo_in_no_permite_inspeccion_sin_comprobacion_ok(app) -> None:
    _ensure_catalog_contraproducencia(app, "NO PERMITE INSPECCION")
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(contraproducencia="NO PERMITE INSPECCION")
    assert m.contraproducencia == "NO PERMITE INSPECCION"


def test_completo_in_no_permite_inspeccion_rechaza_inspeccion(app) -> None:
    _ensure_catalog_contraproducencia(app, "NO PERMITE INSPECCION")
    with app.app_context():
        with pytest.raises(ValidationError):
            CompletarTrabajoCierreCompletoIn(
                contraproducencia="NO PERMITE INSPECCION",
                acta_inspeccion_num="123456",
                acta_comprobacion_num="111111",
                comprobacion_motivo="No Permite la Inspección",
            )


def test_completo_in_no_permite_inspeccion_rechaza_comprobacion_incompleta(app) -> None:
    _ensure_catalog_contraproducencia(app, "NO PERMITE INSPECCION")
    with app.app_context():
        with pytest.raises(ValidationError):
            CompletarTrabajoCierreCompletoIn(
                contraproducencia="NO PERMITE INSPECCION",
                acta_comprobacion_num="111111",
            )


def test_completo_in_correctiva_rubro_exige_rubro_nombre(app) -> None:
    _ensure_catalog_contraproducencia(app, "NO ES EL RUBRO")
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(contraproducencia="NO ES EL RUBRO")
    assert "rubro" in str(exc.value).lower()


def test_completo_in_correctiva_rubro_ok(app) -> None:
    _ensure_catalog_contraproducencia(app, "NO ES EL RUBRO")
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            contraproducencia="NO ES EL RUBRO",
            rubro_nombre="Kiosco",
        )
    assert m.rubro_nombre == "Kiosco"


def test_completo_in_correctiva_direccion_exige_calle_numero(app) -> None:
    _ensure_catalog_contraproducencia(app, "DIRECCION INCORRECTA")
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                contraproducencia="DIRECCION INCORRECTA",
                rubro_nombre="Kiosco",
                calle="San Martín",
            )
    msg = str(exc.value).lower()
    assert "calle" in msg or "numero" in msg


def test_completo_in_correctiva_direccion_ok(app) -> None:
    _ensure_catalog_contraproducencia(app, "DIRECCION INCORRECTA")
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            contraproducencia="DIRECCION INCORRECTA",
            calle="San Martín",
            numero="1234",
        )
    assert m.calle == "San Martín"
    assert m.numero == "1234"
