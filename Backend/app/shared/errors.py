from __future__ import annotations

from typing import Dict
from pydantic import ValidationError


def pydantic_errors_to_cell_map(e: ValidationError) -> Dict[str, str]:
    """
    Convierte ValidationError -> dict celda-friendly:
      {"campo": "mensaje", "_row": "mensaje global"}
    """
    out: Dict[str, str] = {}
    for err in e.errors():
        loc = err.get("loc", ())
        ctx = err.get("ctx") or {}
        raw_msg = ctx.get("error") or err.get("msg", "Error")
        msg = raw_msg if isinstance(raw_msg, str) else str(raw_msg)


        # Si viene anidado como ('row','campo'), nos quedamos con 'campo'
        if loc and loc[0] == "row" and len(loc) >= 2:
            field = str(loc[1])
            out.setdefault(field, msg)
            continue

        if loc:
            field = str(loc[0])
            out.setdefault(field, msg)
        else:
            out.setdefault("_row", msg)

    return out