from app.database import db
from app.models import Inspector, Rubro, Turno


def seed_basicos():
    # Turno mínimo
    turno = Turno(turno="Mañana")  # <-- antes tenías nombre="Mañana"
    db.session.add(turno)
    db.session.flush()

    # Inspectores precargados
    db.session.add_all([
        Inspector(nombre="Gómez", legajo="1", turno_id=turno.id),
        Inspector(nombre="Luna", legajo="2", turno_id=turno.id),
    ])

    # Rubro catálogo
    db.session.add(Rubro(nombre="Transporte"))

    db.session.commit()

