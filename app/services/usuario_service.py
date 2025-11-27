from app.database import db
from app.models import Usuario


def crear_usuario(data):
    usuario = Usuario(**data)
    db.session.add(usuario)
    db.session.commit()
    return usuario


def obtener_usuarios():
    return Usuario.query.all()


def obtener_usuario(id):
    return Usuario.query.get(id)


def eliminar_usuario(id):
    usuario = Usuario.query.get(id)

    if not usuario:
        return False
    db.session.delete(usuario)
    db.session.commit()
    return True
