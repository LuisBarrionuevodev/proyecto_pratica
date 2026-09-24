from __future__ import annotations

from app.domains.indicadores.schemas.resumen_query import IndicadoresResumenQuery

# Alias compartido para bloques del dashboard (mismos query params que /resumen).
IndicadoresFiltrosQuery = IndicadoresResumenQuery

__all__ = ["IndicadoresFiltrosQuery"]
