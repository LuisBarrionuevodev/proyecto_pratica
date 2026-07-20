/** Helpers de modo Completar trabajo según `tipo_iniciador` (PR10.2b / PR10.2c). */

export const TIPOS_RATIFICACION_OFICIO = [
  "RATIFICACION_CLAUSURA_OFICIO",
  "RATIFICACION_DECOMISO_OFICIO",
] as const;

export type TipoRatificacionOficio = (typeof TIPOS_RATIFICACION_OFICIO)[number];

export const TIPO_ACTUACION_VERIFICAR_INFORMAR = "VERIFICAR E INFORMAR";

export const REALIZO_NUEVA_INSPECCION_OPTS: { value: string; label: string }[] = [
  { value: "", label: "—" },
  { value: "si", label: "Sí" },
  { value: "no", label: "No" },
];

function normTipo(tipo: string | null | undefined): string {
  return (tipo ?? "").trim().toUpperCase();
}

function normTipoActuacion(tipo: string | null | undefined): string {
  return normTipo(tipo).replace(/_/g, " ").replace(/\s+/g, " ").trim();
}

/** Subtipo de actuación «Verificar e informar» (catálogo). */
export function esTipoActuacionVerificarInformar(tipoActuacion: string | null | undefined): boolean {
  return normTipoActuacion(tipoActuacion) === normTipoActuacion(TIPO_ACTUACION_VERIFICAR_INFORMAR);
}

/** Ratificación de clausura o decomiso (iniciador ya promovido tras PR10.2). */
export function esRatificacionOficio(tipo: string | null | undefined): boolean {
  return (TIPOS_RATIFICACION_OFICIO as readonly string[]).includes(normTipo(tipo));
}

/** Verificar e informar promovido: actuación/inspección normal. */
export function esVerificarInformarOficio(tipo: string | null | undefined): boolean {
  return normTipo(tipo) === "VERIFICAR_INFORMAR_OFICIO";
}

/**
 * Cierre por oficio/ratificación: cumplimiento sí/no, sin actas de inspección normal.
 * Incluye `REINSPECCION_OFICIO` genérico y ratificaciones promovidas.
 */
export function esFlujoCierreOficio(tipo: string | null | undefined): boolean {
  const t = normTipo(tipo);
  return t === "REINSPECCION_OFICIO" || esRatificacionOficio(t);
}

/** Solo el genérico que aún exige elegir subtipo en UI. */
export function esReinspeccionOficioGenerico(tipo: string | null | undefined): boolean {
  return normTipo(tipo) === "REINSPECCION_OFICIO";
}

/** Tipo de actuación fijo cuando el iniciador ya es específico (post-promoción). */
export function tipoActuacionFijoDesdeIniciadorOficio(
  tipoIniciador: string | null | undefined
): string | null {
  const t = normTipo(tipoIniciador);
  if (t === "RATIFICACION_CLAUSURA_OFICIO") return "RATIFICACION DE CLAUSURA";
  if (t === "RATIFICACION_DECOMISO_OFICIO") return "RATIFICACION DE DECOMISO";
  if (t === "VERIFICAR_INFORMAR_OFICIO") return "VERIFICAR E INFORMAR";
  return null;
}

/** Tipo efectivo para filtros de contraproducencia en oficio/ratificación. */
export function tipoActuacionEfectivoOficio(
  tipoIniciador: string | null | undefined,
  tipoActuacionOficio?: string | null
): string | null {
  return tipoActuacionFijoDesdeIniciadorOficio(tipoIniciador) ?? tipoActuacionOficio?.trim() ?? null;
}

/**
 * Flujo Verificar e informar: pregunta «¿Realizó nueva inspección?» antes de actas normales.
 * Aplica a iniciador promovido o a `REINSPECCION_OFICIO` con subtipo verificar elegido.
 */
export function esFlujoVerificarInformar(
  tipoIniciador: string | null | undefined,
  tipoActuacion?: string | null
): boolean {
  if (esVerificarInformarOficio(tipoIniciador)) return true;
  if (esReinspeccionOficioGenerico(tipoIniciador) && esTipoActuacionVerificarInformar(tipoActuacion)) {
    return true;
  }
  return false;
}

/**
 * Cierre por cumplimiento sí/no (ratificación clausura/decomiso).
 * En `REINSPECCION_OFICIO` genérico solo aplica si el subtipo elegido no es verificar e informar.
 */
export function esFlujoCumplimientoRatificacion(
  tipoIniciador: string | null | undefined,
  tipoActuacion?: string | null
): boolean {
  if (esRatificacionOficio(tipoIniciador)) return true;
  if (esReinspeccionOficioGenerico(tipoIniciador)) {
    const t = (tipoActuacion ?? "").trim();
    if (!t) return false;
    return !esTipoActuacionVerificarInformar(t);
  }
  return false;
}
