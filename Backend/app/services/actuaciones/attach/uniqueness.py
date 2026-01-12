from __future__ import annotations

from typing import Any, Protocol


class _QueryProtocol(Protocol):
    def filter_by(self, **kwargs: Any) -> Any: ...

    def first(self) -> Any: ...


class _ModelWithQueryProtocol(Protocol):
    """
    Protocolo mínimo para modelos SQLAlchemy usados en estas validaciones.

    Requiere:
    - `.query` con `filter_by(...).first()`
    - columnas/atributos `numero_acta` y `anio` (usados en el filter_by)
    - instancia con atributo opcional `actuacion_id` (usado para comparar asociación)
    """

    query: _QueryProtocol


def asegurar_acta_no_usada_en_otra(model_cls: type[_ModelWithQueryProtocol], numero_acta: str, anio: int, actuacion_id: int) -> None:
    """
    Valida unicidad dura de un acta principal en modo creación.

    Se usa para actas principales como `Inspeccion`, `Clausura`, `Decomiso`.

    Reglas:
    - Busca un registro existente por `(numero_acta, anio)`.
    - Si existe y su `actuacion_id` NO coincide con `actuacion_id` -> levanta `ValueError`.

    Args:
        model_cls: modelo SQLAlchemy con `.query` y columnas `numero_acta`, `anio` (y, en instancias, opcional `actuacion_id`).
        numero_acta: número de acta (normalizado).
        anio: año de la actuación.
        actuacion_id: id de la actuación que se está creando/asociando.

    Raises:
        ValueError: si el acta ya está asociada a otra actuación.
    """
    existente = model_cls.query.filter_by(numero_acta=numero_acta, anio=anio).first()
    if existente and getattr(existente, "actuacion_id", None) != actuacion_id:
        raise ValueError("Acta ya asociada a otra actuación.")


def asegurar_acta_libre_para_actuacion(model_cls: type[_ModelWithQueryProtocol], numero_acta: str, anio: int, actuacion_id: int) -> None:
    """
    Valida unicidad dura de un acta principal en modo update.

    Reglas:
    - Busca un registro existente por `(numero_acta, anio)`.
    - Si existe y su `actuacion_id` pertenece a OTRA actuación (ni `None` ni `actuacion_id`) -> `ValueError`.

    Args:
        model_cls: modelo SQLAlchemy con `.query` y columnas `numero_acta`, `anio` (y, en instancias, opcional `actuacion_id`).
        numero_acta: número de acta (normalizado).
        anio: año de la actuación.
        actuacion_id: id de la actuación que se está editando/asociando.

    Raises:
        ValueError: si el acta ya está asociada a otra actuación.
    """
    existente = model_cls.query.filter_by(numero_acta=numero_acta, anio=anio).first()
    if existente and getattr(existente, "actuacion_id", None) not in (None, actuacion_id):
        raise ValueError("Acta ya asociada a otra actuación.")
