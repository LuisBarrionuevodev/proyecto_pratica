from __future__ import annotations

from flask import jsonify
from sqlalchemy.exc import IntegrityError

from app.domains.rutas_trabajo.presenters.ruta_presenters import (
    ruta_item_to_min_dict,
    ruta_trabajo_to_dict,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import (
    json_409_publicar,
    log_publicar_debug,
)

from . import rutas_trabajo


@rutas_trabajo.post("/<int:ruta_id>/publicar")
def publicar_ruta(ruta_id: int):
    """
    Publica una ruta en BORRADOR: validaciones, actuaciones mínimas por ítem, estado PUBLICADA.

    Sin cuerpo JSON. El usuario efectivo se audita en capas inferiores si aplica.

    Errores:
        404: ruta inexistente.
        409: reglas de negocio (RuntimeError del service) con bloque ``debug`` en QA.
    """
    log_publicar_debug(
        conflicto_detectado_por="publicar_ruta.endpoint",
        mensaje_conflicto=None,
        ruta_id=ruta_id,
        fase="request_in",
    )
    try:
        ruta, items = publicar_ruta_trabajo(ruta_id=ruta_id)
        return (
            jsonify(
                {
                    "ruta": ruta_trabajo_to_dict(ruta),
                    "items": [ruta_item_to_min_dict(i) for i in items],
                }
            ),
            200,
        )
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        body, status = json_409_publicar(e)
        return jsonify(body), status
    except IntegrityError as e:
        body, status = json_409_publicar(e)
        return jsonify(body), status
