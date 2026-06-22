/**
 * Opciones de contraproducencia visibles en Completar trabajo según tipo de iniciador (STAB-4).
 * Alineado al seed backend `catalog_contraproducencia`; NO_HUBO queda fuera de este flujo.
 */

const BASE_INSPECCION = new Set([
  "LOCAL CERRADO",
  "CLIMA",
  "ZONA ROJA",
  "OTROS",
  "NO ES EL RUBRO",
  "DIRECCION INCORRECTA",
  "NO_EXISTE_LOCAL",
  "NO EXISTE/NO ES EL RUBRO",
  "NO PERMITE INSPECCION",
]);

const REINSPECCION = new Set([
  "LOCAL CERRADO",
  "CLIMA",
  "OTROS",
  "NO_EXISTE_LOCAL",
  "NO EXISTE/NO ES EL RUBRO",
  "NO PERMITE INSPECCION",
]);

const REINSPECCION_OFICIO = new Set([
  ...REINSPECCION,
  "NO SE RATIFICÓ",
  "NO PAGÓ TODAVÍA EL DECOMISO",
]);

const TIPO_A_SET: Record<string, Set<string>> = {
  RELEVAMIENTO: BASE_INSPECCION,
  DENUNCIA: BASE_INSPECCION,
  REINSPECCION_NOTIFICACION: REINSPECCION,
  REINSPECCION_OFICIO,
};

function looseKey(s: string): string {
  return s
    .toUpperCase()
    .replace(/_/g, " ")
    .replace(/\//g, " ")
    .split(/\s+/)
    .join(" ")
    .trim();
}

function keysPermitidos(tipoIniciador: string | null | undefined): Set<string> {
  const t = (tipoIniciador ?? "").trim().toUpperCase();
  const base = TIPO_A_SET[t] ?? BASE_INSPECCION;
  return new Set([...base].map(looseKey));
}

/** True si el valor puede mostrarse/seleccionarse en Completar trabajo para el tipo dado. */
export function contraproducenciaPermitidaCompletarTrabajo(
  tipoIniciador: string | null | undefined,
  nombre: string | null | undefined
): boolean {
  const n = (nombre ?? "").trim();
  if (!n) return true;
  if (looseKey(n) === looseKey("NO_HUBO")) return false;
  return keysPermitidos(tipoIniciador).has(looseKey(n));
}

/**
 * Filtra catálogo para el select; conserva valor legacy guardado aunque no esté en el set del tipo.
 * Para REINSPECCION_OFICIO, opcionalmente filtra contras específicas por subtipo de actuación.
 */
export function filtrarContraproducenciasPorTipoIniciador(
  catalog: string[],
  tipoIniciador: string | null | undefined,
  valorGuardado?: string | null,
  tipoActuacionOficio?: string | null
): string[] {
  const permitidos = keysPermitidos(tipoIniciador);
  let out = catalog.filter((n) => {
    const t = (n ?? "").trim();
    if (!t) return false;
    if (looseKey(t) === looseKey("NO_HUBO")) return false;
    return permitidos.has(looseKey(t));
  });
  const tIni = (tipoIniciador ?? "").trim().toUpperCase();
  if (tIni === "REINSPECCION_OFICIO" && tipoActuacionOficio) {
    const tipo = looseKey(tipoActuacionOficio);
    out = out.filter((n) => {
      const key = looseKey(n);
      if (key === looseKey("NO SE RATIFICÓ")) {
        return tipo === looseKey("RATIFICACION DE CLAUSURA");
      }
      if (key === looseKey("NO PAGÓ TODAVÍA EL DECOMISO")) {
        return tipo === looseKey("RATIFICACION DE DECOMISO");
      }
      return true;
    });
  }
  const legacy = (valorGuardado ?? "").trim();
  if (legacy && !out.some((x) => looseKey(x) === looseKey(legacy))) {
    out.push(legacy);
  }
  return out.sort((a, b) => a.localeCompare(b, "es"));
}
