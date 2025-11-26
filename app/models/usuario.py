from app.database import db


class Usuario(db.Model):
    _tablename_ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nulleable=False)
    email = db.Column(db.String(150), unique=True, nulleable=False)
    activo = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "email": self.email,
            "activo": self.activo,
        }
