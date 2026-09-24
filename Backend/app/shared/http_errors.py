"""
Manejadores HTTP globales para respuestas JSON en producción.

Qué hace: evita HTML/traceback en 404/405/500 hacia clientes API.
Parámetros: instancia Flask.
Errores: no lanza; serializa errores estándar.
"""

from __future__ import annotations

from flask import Flask, jsonify


def register_json_error_handlers(app: Flask) -> None:
    """
    Registra handlers JSON para rutas no encontradas y errores del servidor.

    Parámetros:
        app: aplicación Flask.

    Retorno:
        None.
    """

    @app.errorhandler(404)
    def not_found(_error):  # type: ignore[no-untyped-def]
        return jsonify({"detail": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):  # type: ignore[no-untyped-def]
        return jsonify({"detail": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(_error):  # type: ignore[no-untyped-def]
        return jsonify({"detail": "Internal server error"}), 500
