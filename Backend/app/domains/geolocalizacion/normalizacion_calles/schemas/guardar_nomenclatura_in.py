from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator


class CalleNomenclaturaIn(BaseModel):
    """
    Entrada para calle en guardado híbrido de nomenclatura.

    - ``CATALOGO``: requiere ``calle_catalogo_id``; no debe enviarse texto como fuente de verdad.
    - ``MANUAL``: requiere ``calle_texto``; no debe enviarse ``calle_catalogo_id``.
    """

    model_config = ConfigDict(extra="forbid")

    mode: Literal["CATALOGO", "MANUAL"]
    calle_catalogo_id: Optional[int] = None
    calle_texto: Optional[str] = None

    @model_validator(mode="after")
    def _validate_calle(self) -> CalleNomenclaturaIn:
        if self.mode == "CATALOGO":
            if not self.calle_catalogo_id:
                raise ValueError("calle_catalogo_id es obligatorio cuando calle.mode es CATALOGO.")
            if self.calle_texto is not None and str(self.calle_texto).strip():
                raise ValueError("No enviar calle_texto cuando calle.mode es CATALOGO.")
        else:
            if self.calle_catalogo_id is not None:
                raise ValueError("No enviar calle_catalogo_id cuando calle.mode es MANUAL.")
            t = (self.calle_texto or "").strip()
            if not t:
                raise ValueError("calle_texto es obligatorio cuando calle.mode es MANUAL.")
            self.calle_texto = t
        return self


class EsquinaNomenclaturaIn(BaseModel):
    """
    Entrada para esquina cuando ``numero_tipo`` es ESQUINA.

    El texto de la intersección operativa vive en ``numero`` del payload raíz.
    """

    model_config = ConfigDict(extra="forbid")

    mode: Literal["CATALOGO", "MANUAL"]
    esquina_catalogo_id: Optional[int] = None

    @model_validator(mode="after")
    def _validate_esquina(self) -> EsquinaNomenclaturaIn:
        if self.mode == "CATALOGO":
            if not self.esquina_catalogo_id:
                raise ValueError(
                    "esquina_catalogo_id es obligatorio cuando esquina.mode es CATALOGO."
                )
        else:
            if self.esquina_catalogo_id is not None:
                raise ValueError("No enviar esquina_catalogo_id cuando esquina.mode es MANUAL.")
        return self


class GuardarNomenclaturaIn(BaseModel):
    """
    Contrato unificado para guardar nomenclatura (calle × catálogo/manual y esquina si aplica).
    """

    model_config = ConfigDict(extra="forbid")

    calle: CalleNomenclaturaIn
    numero: str
    numero_tipo: Literal["NUMERO", "ESQUINA"]
    esquina: Optional[EsquinaNomenclaturaIn] = None

    @model_validator(mode="after")
    def _validate_raiz(self) -> GuardarNomenclaturaIn:
        nt = self.numero_tipo.strip().upper()
        if nt not in ("NUMERO", "ESQUINA"):
            raise ValueError("numero_tipo debe ser NUMERO o ESQUINA.")
        self.numero_tipo = nt  # type: ignore[assignment]
        if nt == "NUMERO":
            if self.esquina is not None:
                raise ValueError("No debe enviarse esquina cuando numero_tipo es NUMERO.")
        elif self.esquina is None:
            raise ValueError("esquina es obligatoria cuando numero_tipo es ESQUINA.")
        n = (self.numero or "").strip()
        if not n:
            raise ValueError("numero es obligatorio.")
        self.numero = n
        return self
