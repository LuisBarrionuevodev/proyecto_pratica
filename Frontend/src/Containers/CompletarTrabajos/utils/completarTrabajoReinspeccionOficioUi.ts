/** UI helpers para Completar trabajo — REINSPECCION_OFICIO (labels humanos, filtros). */

export const TIPO_ACTUACION_REINSPECCION_OFICIO = [
  "RATIFICACION DE CLAUSURA",
  "RATIFICACION DE DECOMISO",
  "VERIFICAR E INFORMAR",
] as const;

export type TipoActuacionReinspeccionOficio = (typeof TIPO_ACTUACION_REINSPECCION_OFICIO)[number];

const TIPO_ACTUACION_LABELS: Record<TipoActuacionReinspeccionOficio, string> = {
  "RATIFICACION DE CLAUSURA": "Ratificación de clausura",
  "RATIFICACION DE DECOMISO": "Ratificación de decomiso",
  "VERIFICAR E INFORMAR": "Verificar e informar",
};

export const CONTRAPRODUCCION_NO_SE_RATIFICO = "NO SE RATIFICÓ";
export const CONTRAPRODUCCION_NO_PAGO_DECOMISO = "NO PAGÓ TODAVÍA EL DECOMISO";

function looseKey(s: string): string {
  return s
    .toUpperCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/_/g, " ")
    .replace(/\//g, " ")
    .split(/\s+/)
    .join(" ")
    .trim();
}

/** Valor inicial del select de tipo si ya viene en fila/detalle. */
export function tipoActuacionInicialReinspeccionOficio(tipo: string | null | undefined): string {
  const t = (tipo ?? "").trim();
  return (TIPO_ACTUACION_REINSPECCION_OFICIO as readonly string[]).includes(t) ? t : "";
}

export function labelTipoActuacionReinspeccionOficio(value: string): string {
  const t = (value ?? "").trim();
  if (!t) return "—";
  return TIPO_ACTUACION_LABELS[t as TipoActuacionReinspeccionOficio] ?? t;
}

export function tipoActuacionReinspeccionOficioOpts(): { value: string; label: string }[] {
  return [
    { value: "", label: "—" },
    ...TIPO_ACTUACION_REINSPECCION_OFICIO.map((v) => ({
      value: v,
      label: TIPO_ACTUACION_LABELS[v],
    })),
  ];
}

export const OFICIO_CUMPLE_OPTS: { value: string; label: string }[] = [
  { value: "", label: "—" },
  { value: "CUMPLE", label: "Sí" },
  { value: "NO_CUMPLE", label: "No" },
];

/** Filtra contras de oficio según subtipo elegido (ratificación clausura / decomiso). */
export function filtrarContraproducenciaOficioPorTipoActuacion(
  nombres: string[],
  tipoActuacionOficio: string | null | undefined
): string[] {
  const tipo = looseKey(tipoActuacionOficio ?? "");
  return nombres.filter((n) => {
    const key = looseKey(n);
    if (key === looseKey(CONTRAPRODUCCION_NO_SE_RATIFICO)) {
      return tipo === looseKey("RATIFICACION DE CLAUSURA");
    }
    if (key === looseKey(CONTRAPRODUCCION_NO_PAGO_DECOMISO)) {
      return tipo === looseKey("RATIFICACION DE DECOMISO");
    }
    return true;
  });
}
