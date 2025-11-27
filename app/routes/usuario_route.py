from flask import Blueprint, jsonify, request

from app.schemas import UsuarioCreate, UsuarioResponse
from app.services import (
    crear_usuario,
    eliminar_usuario,
    obtener_usuario,
    obtener_usuarios,
)

usuario = Blueprint("usuario", __name__)


@usuario.get("/")
def listar():
    usuarios = obtener_usuarios()
    return jsonify([u.to_dict() for u in usuarios])


@usuario.post("/")
def crear():
    data = request.json

    usuario_validado = UsuarioCreate(**data)

    nuevo = crear_usuario(usuario_validado.dict())
    return UsuarioResponse(**nuevo.to_dict).dict(), 200


eliminar_usuario
obtener_usuario
