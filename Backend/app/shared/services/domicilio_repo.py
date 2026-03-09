from __future__ import annotations

from app.database import db
from app.models import Domicilio


def get_or_create_domicilio_basico(calle: str, numero: str) -> Domicilio:
    """
    Obtiene o crea un Domicilio básico identificado por (calle, numero).

    Qué hace:
    - Normaliza `calle` y `numero` (strip).
    - Si existe un Domicilio con esas claves, lo retorna.
    - Si no existe, lo crea y hace add+flush (sin commit).

    Parámetros:
    - calle: nombre de calle (str no vacío).
    - numero: número de puerta (str no vacío).

    Retorno:
    - Domicilio existente o nuevo.
    """
    calle_norm = (calle or "").strip()
    numero_norm = (numero or "").strip()
    dom = (
        Domicilio.query.filter_by(calle=calle_norm, numero=numero_norm)
        .filter(Domicilio.deleted_at.is_(None))
        .first()
    )
    if dom:
        return dom

    dom = Domicilio(calle=calle_norm, numero=numero_norm)
    db.session.add(dom)
    db.session.flush()
    return dom
