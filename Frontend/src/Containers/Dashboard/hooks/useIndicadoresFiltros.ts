import { useCallback, useMemo, useState } from "react";

import type { Periodo } from "../../../types/periodos";
import {
  buildIndicadoresFiltrosEfectivos,
  type IndicadoresFiltrosEfectivos,
} from "../utils/indicadoresEffectiveFilters";
import type { IndicadoresMonthSelection } from "../utils/indicadoresMonthYearRange";

const PERIODOS: Periodo[] = ["Semanal", "Mensual", "Trimestral", "Anual"];

export function useIndicadoresFiltros(isInspectorIndicadores: boolean) {
  const [periodo, setPeriodoState] = useState<Periodo>("Mensual");
  const [monthOverride, setMonthOverride] = useState<IndicadoresMonthSelection | null>(null);
  const [distritoId, setDistritoId] = useState<string>("");
  const [inspectorId, setInspectorId] = useState<string>("");

  const setPeriodo = useCallback((next: Periodo) => {
    setMonthOverride(null);
    setPeriodoState(next);
  }, []);

  const applyMonthSelection = useCallback((sel: IndicadoresMonthSelection) => {
    setMonthOverride(sel);
  }, []);

  const clearMonthOverride = useCallback(() => {
    setMonthOverride(null);
  }, []);

  const effective = useMemo(
    () =>
      buildIndicadoresFiltrosEfectivos({
        periodo,
        monthOverride,
        distritoId,
        inspectorId,
        isInspectorIndicadores,
      }),
    [periodo, monthOverride, distritoId, inspectorId, isInspectorIndicadores]
  );

  const indicadoresParams: IndicadoresFiltrosEfectivos = useMemo(
    () => ({
      desde: effective.desde,
      hasta: effective.hasta,
      ...(effective.distrito_id != null ? { distrito_id: effective.distrito_id } : {}),
      ...(effective.inspector_id != null ? { inspector_id: effective.inspector_id } : {}),
    }),
    [effective]
  );

  const periodoTabIndex = PERIODOS.indexOf(periodo);

  return {
    periodos: PERIODOS,
    periodo,
    setPeriodo,
    monthOverride,
    applyMonthSelection,
    clearMonthOverride,
    distritoId,
    setDistritoId,
    inspectorId,
    setInspectorId,
    indicadoresParams,
    periodoUiLabel: effective.periodoUiLabel,
    monthOverrideActive: effective.monthOverrideActive,
    periodoTabIndex,
    desde: effective.desde,
    hasta: effective.hasta,
  };
}
