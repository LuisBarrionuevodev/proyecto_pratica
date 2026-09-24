"""CLI: auditoría de duplicados en relevamientos ESQUINA (PR7.5). Solo lectura."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.domains.relevamientos.services.relevamiento_duplicados_audit_service import (
    auditar_relevamientos_esquina_duplicados,
)

app = create_app()

with app.app_context():
    result = auditar_relevamientos_esquina_duplicados()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    print(
        f"\nResumen: {result.total_grupos_revisados} grupos revisados, "
        f"{result.grupos_con_colision} con colisión.",
        file=sys.stderr,
    )
