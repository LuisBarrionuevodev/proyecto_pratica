from __future__ import annotations

from datetime import date

from flask import jsonify, request

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_trabajo_to_dict
from app.domains.rutas_trabajo.services.ruta_list_service import list_rutas_borrador, list_rutas_trabajo

from . import rutas_trabajo


def _parse_estados_query(raw: str | None) -> tuple[str, ...] | None:
    """
    Parsea ``estado_ruta`` del query string.

    - None o vacío → None (el listado usa solo BORRADOR, comportamiento por defecto).
    - Un valor: ``PUBLICADA``.
    - Varios separados por coma: ``PUBLICADA,EN_CURSO,CERRADA`` (espacios tolerados).

    Returns:
        Tupla de estados en mayúsculas o None.

    Raises:
        ValueError: si no queda ningún token válido tras el parseo.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    parts = [p.strip().upper() for p in s.split(",") if p.strip()]
    if not parts:
        return None
    return tuple(parts)


@rutas_trabajo.get("")
@rutas_trabajo.get("/")
def list_rutas():
    """
    Lista rutas de trabajo paginadas.

    **Por defecto** (sin ``estado_ruta``): solo rutas en **BORRADOR** (planificación / reabrir borrador).

    **Rutas publicadas / histórico:** enviar ``estado_ruta`` con uno o más valores del enum, por ejemplo:
    - ``?estado_ruta=PUBLICADA`` — solo publicadas
    - ``?estado_ruta=PUBLICADA,EN_CURSO,CERRADA`` — varios estados no-borrador

    **Filtro por día exacto:**
    - ``?fecha=YYYY-MM-DD`` — ``RutaTrabajo.fecha`` igual a ese día (prioridad: si viene ``fecha``,
      se ignoran ``fecha_desde`` y ``fecha_hasta``).

    **Rango de fechas** (solo si no hay ``fecha``):
    - ``fecha_desde``, ``fecha_hasta`` (YYYY-MM-DD), mismo criterio inclusivo que antes.

    Query: ``page``, ``per_page`` (enteros).

    Response:
        ``items`` (mismo presenter ``ruta_trabajo_to_dict``), ``meta`` con ``total``, ``page``,
        ``per_page``, ``estados`` (lista aplicada), ``fecha``, ``fecha_desde``, ``fecha_hasta``.
    """
    raw_page = request.args.get("page", "1")
    raw_per = request.args.get("per_page", "50")
    try:
        page = int(raw_page)
        per_page = int(raw_per)
    except ValueError:
        return jsonify({"detail": "page y per_page deben ser enteros"}), 400

    fecha_exacta: date | None = None
    fecha_param = request.args.get("fecha")
    if fecha_param:
        try:
            fecha_exacta = date.fromisoformat(str(fecha_param).strip())
        except ValueError:
            return jsonify({"detail": "fecha debe ser YYYY-MM-DD"}), 400

    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    fd = request.args.get("fecha_desde")
    fh = request.args.get("fecha_hasta")
    if not fecha_exacta:
        if fd:
            try:
                fecha_desde = date.fromisoformat(str(fd).strip())
            except ValueError:
                return jsonify({"detail": "fecha_desde debe ser YYYY-MM-DD"}), 400
        if fh:
            try:
                fecha_hasta = date.fromisoformat(str(fh).strip())
            except ValueError:
                return jsonify({"detail": "fecha_hasta debe ser YYYY-MM-DD"}), 400

    estados_arg = _parse_estados_query(request.args.get("estado_ruta"))

    try:
        if estados_arg is None:
            rows, total, per_efectivo = list_rutas_borrador(
                fecha=fecha_exacta,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                page=page,
                per_page=per_page,
            )
            estados_aplicados: tuple[str, ...] = ("BORRADOR",)
        else:
            rows, total, per_efectivo, estados_aplicados = list_rutas_trabajo(
                estados=estados_arg,
                fecha=fecha_exacta,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                page=page,
                per_page=per_page,
            )
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

    return jsonify(
        {
            "items": [ruta_trabajo_to_dict(r) for r in rows],
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_efectivo,
                "estados": list(estados_aplicados),
                "fecha": fecha_exacta.isoformat() if fecha_exacta else None,
                "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
            },
        }
    ), 200
