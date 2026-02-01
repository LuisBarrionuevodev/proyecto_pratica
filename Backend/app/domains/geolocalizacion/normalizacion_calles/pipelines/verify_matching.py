from __future__ import annotations

from app.main import create_app
from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import match_calle


def main() -> None:
    app = create_app()
    with app.app_context():
        cases = [
            "las heras",
            "Av araoz",
            "san martin",
        ]
        for c in cases:
            result = match_calle(c)
            print(c, "=>", result)


if __name__ == "__main__":
    main()
