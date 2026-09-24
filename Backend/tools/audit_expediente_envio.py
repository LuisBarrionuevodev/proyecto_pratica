#!/usr/bin/env python3
"""
Auditoría: comprobaciones con más de un expediente de envío (oficio_id NULL).

Ejecución (desde la carpeta ``Backend/``, con el entorno que cargue ``app``):

    python tools/audit_expediente_envio.py

Salida: lista de ``comprobacion_id`` y cantidad; opcionalmente ids de expediente por fila duplicada.
"""

from __future__ import annotations

import os
import sys

# Raíz del paquete ``app``
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> None:
    from app import create_app
    from app.domains.actuaciones.services.expediente_envio_audit import (
        fetch_comprobaciones_con_multiples_expedientes_envio,
        fetch_expedientes_envio_por_comprobacion,
    )

    app = create_app()
    with app.app_context():
        dup = fetch_comprobaciones_con_multiples_expedientes_envio()
        print(f"Comprobaciones con >1 expediente envío (oficio_id NULL, no borrados): {len(dup)}")
        for cid, cnt in dup:
            print(f"  comprobacion_id={cid}  expedientes_envio={cnt}")
            det = fetch_expedientes_envio_por_comprobacion(cid)
            for ex in det:
                print(
                    f"      expediente id={ex.id}  nº/año={ex.numero_expediente}/{ex.anio}  "
                    f"tipo={ex.tipo_expediente}"
                )


if __name__ == "__main__":
    main()
