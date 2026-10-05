import type { Periodo } from "../../../types/periodos";
import type { IndicadoresMonthSelection } from "./indicadoresMonthYearRange";
import {
  formatIndicadoresMonthYearLabel,
  monthYearToIndicadoresDateRange,
} from "./indicadoresMonthYearRange";
import { periodoToDateRange } from "./periodoDateRange";

/** Estado efectivo compartido por hooks de indicadores, UI y export PDF. */
export type IndicadoresFiltrosEfectivos = {
  desde: string;
  hasta: string;
  distrito_id?: number;
  inspector_id?: number;
};

export type ResolveIndicadoresRangeInput = {
  periodo: Periodo;
  monthOverride: IndicadoresMonthSelection | null;
  ref?: Date;
};

export function resolveIndicadoresDateRange(
  input: ResolveIndicadoresRangeInput
): { desde: string; hasta: string; monthOverrideActive: boolean; periodoUiLabel: string } {
  const ref = input.ref ?? new Date();
  if (input.monthOverride) {
    const range = monthYearToIndicadoresDateRange(input.monthOverride, ref);
    return {
      ...range,
      monthOverrideActive: true,
      periodoUiLabel: formatIndicadoresMonthYearLabel(input.monthOverride),
    };
  }
  const range = periodoToDateRange(input.periodo, ref);
  return {
    ...range,
    monthOverrideActive: false,
    periodoUiLabel: input.periodo,
  };
}

export function buildIndicadoresFiltrosEfectivos(args: {
  periodo: Periodo;
  monthOverride: IndicadoresMonthSelection | null;
  distritoId: string;
  inspectorId: string;
  isInspectorIndicadores: boolean;
  ref?: Date;
}): IndicadoresFiltrosEfectivos & {
  periodoUiLabel: string;
  monthOverrideActive: boolean;
} {
  const { periodoUiLabel, monthOverrideActive, desde, hasta } = resolveIndicadoresDateRange({
    periodo: args.periodo,
    monthOverride: args.monthOverride,
    ref: args.ref,
  });
  const filtros: IndicadoresFiltrosEfectivos = { desde, hasta };
  if (!args.isInspectorIndicadores) {
    if (args.distritoId !== "") {
      filtros.distrito_id = Number(args.distritoId);
    }
    if (args.inspectorId !== "") {
      filtros.inspector_id = Number(args.inspectorId);
    }
  }
  return { ...filtros, periodoUiLabel, monthOverrideActive };
}
