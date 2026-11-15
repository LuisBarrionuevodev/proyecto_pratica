/**
 * Textos de alcance/advertencia alineados al canal de corrección controlada.
 */
export const CORRECCION_CONTRIBUYENTE_HINT =
  "Corrige nombre, apellido, razón social o un CUIT/DNI mal cargado de la misma persona. " +
  "Si el documento ya pertenece a otro contribuyente, se propone asociar solo este establecimiento.";

export const CORRECCION_DOCUMENTO_CONFIRMACION_TITULO =
  "Esta corrección se aplicará a todos los establecimientos asociados.";

export const CORRECCION_DOCUMENTO_CONFIRMACION_DETALLE =
  "Confirmá que se trata del mismo contribuyente y que el CUIT/DNI anterior estaba mal cargado.";

export const CORRECCION_DOCUMENTO_MISMA_PERSONA =
  "Todos los establecimientos seguirán vinculados a la misma persona, ahora con los datos corregidos.";

export const CORRECCION_DOMICILIO_HINT =
  "Corrige la dirección de origen de este establecimiento. No se recalculan coordenadas ni distrito.";

export const CORRECCION_LOCAL_HINT =
  "Corrige el rubro y el nombre del local de este establecimiento. No modifica otros locales del mismo contribuyente ni reescribe actuaciones históricas.";

export const CORRECCION_SIN_CAMBIOS_HINT =
  "No hay cambios. No se desvincula el contribuyente ni se modifica ningún dato.";

export const CORRECCION_TITULAR_MODO_AMBOS_HINT =
  "Este registro tiene persona y razón social. Se muestran ambos para no perder datos históricos.";

export const VINCULACION_HINT =
  "Esta operación cambia el vínculo de esta ficha al contribuyente encontrado. No edita sus datos personales.";

export const VINCULACION_BUSCAR_HINT =
  "Ingresá el CUIT o DNI correcto. Si ya pertenece a un contribuyente registrado, Digitaliza lo muestra para vincular este establecimiento.";

export const VINCULACION_ACCION = "Vincular este establecimiento";

export const VINCULACION_FICHA_ACCION = "Vincular a contribuyente existente";

export const VINCULACION_DOCUMENTO_AJENO_CTA =
  "Si el documento ya pertenece a otra persona registrada, usá Vincular este establecimiento. Corregir contribuyente no cambia el titular.";

export const VINCULACION_REGISTRADO_TITULO = "Este contribuyente ya está registrado";

export const VINCULACION_PREGUNTA_ASOCIAR =
  "¿Querés asociar este establecimiento a este contribuyente?";

export const VINCULACION_OTROS_NO_CAMBIAN = "Los demás establecimientos no se modificarán.";

export const VINCULACION_ANTECEDENTES_JUNTOS =
  "Las actuaciones de este domicilio se mostrarán juntas.";

export const VINCULACION_DOCUMENTOS_EMITIDOS = "Los documentos ya emitidos no se modifican.";

export const VINCULACION_DOCUMENTOS_CONSERVAN =
  "Los documentos ya emitidos conservarán sus datos.";

export const VINCULACION_DATOS_DESTINO_CONSERVAN =
  "Los datos personales del contribuyente encontrado se conservan. " +
  "No se aplican el nombre o la razón social que escribiste en Corregir contribuyente.";

export const VINCULACION_HISTORIAL_TITULO = "Historial que se asociará";

export const VINCULACION_CONFLICTO_INSEGURO =
  "No pudimos identificar el vínculo con seguridad. Revisá los datos antes de continuar.";

export const VINCULACION_DETALLE_ALCANCE = "Ver detalle del alcance";

export const VINCULACION_OCULTAR_DETALLE = "Ocultar detalle del alcance";

export const VINCULACION_ASOCIAR = "Sí, asociar";

export const VINCULACION_VOLVER = "Volver";

export type VinculacionConflictoInput = {
  codigo?: string | null;
  detail?: string | null;
  ofrece_vinculacion?: boolean;
};

/**
 * Transición a vinculación: solo si la API marca DOCUMENTO_AJENO + ofrece_vinculacion.
 * No usa el texto de `detail`.
 */
export function ofreceVinculacionDesdeConflicto(
  conflicto: VinculacionConflictoInput | null | undefined
): boolean {
  return conflicto?.codigo === "DOCUMENTO_AJENO" && conflicto.ofrece_vinculacion === true;
}

/**
 * Un solo mensaje de conflicto inseguro: texto general + detalle útil del backend.
 */
export function mensajeConflictoVinculacionInseguro(detail?: string | null): string {
  const extra = (detail ?? "").trim();
  if (!extra) return VINCULACION_CONFLICTO_INSEGURO;
  if (extra === VINCULACION_CONFLICTO_INSEGURO) return extra;
  if (extra.startsWith(VINCULACION_CONFLICTO_INSEGURO)) return extra;
  return `${VINCULACION_CONFLICTO_INSEGURO} ${extra}`;
}

type TitularVinculacionInput = {
  razon_social?: string | null;
  apellido?: string | null;
  nombre?: string | null;
};

/**
 * Nombre visible del contribuyente encontrado. Vacío si no hay datos (no inventa).
 */
export function titularVinculacionTexto(c: TitularVinculacionInput | null | undefined): string {
  if (!c) return "";
  const razon = (c.razon_social ?? "").trim();
  if (razon) return razon;
  const persona = [(c.nombre ?? "").trim(), (c.apellido ?? "").trim()].filter(Boolean).join(" ");
  return persona;
}

/**
 * Pregunta de asociación. Si no hay nombre, usa la fórmula genérica (no inventa titular).
 */
export function preguntaAsociarEstablecimiento(nombre?: string | null): string {
  const n = (nombre ?? "").trim();
  if (!n) return VINCULACION_PREGUNTA_ASOCIAR;
  return `¿Querés asociar este establecimiento a ${n}?`;
}

/**
 * Etiqueta de cantidad con singular/plural. `0` y `>1` usan plural.
 */
export function etiquetaCantidad(cantidad: number, singular: string, plural: string): string {
  return `${cantidad} ${cantidad === 1 ? singular : plural}`;
}

export type ResumenHistorialAsociar = {
  actuaciones?: number;
  notificaciones?: number;
  comprobaciones?: number;
};

/**
 * Resumen compacto del historial a asociar. Omite un rubro si la preview no envió cantidad.
 */
export function resumenHistorialAsociar(resumen: ResumenHistorialAsociar): string[] {
  const partes: string[] = [];
  if (typeof resumen.actuaciones === "number") {
    partes.push(etiquetaCantidad(resumen.actuaciones, "actuación", "actuaciones"));
  }
  if (typeof resumen.notificaciones === "number") {
    partes.push(etiquetaCantidad(resumen.notificaciones, "notificación", "notificaciones"));
  }
  if (typeof resumen.comprobaciones === "number") {
    partes.push(etiquetaCantidad(resumen.comprobaciones, "comprobación", "comprobaciones"));
  }
  return partes;
}

export type TitularCorreccionModo = "persona" | "razon_social" | "ambos";

function hasText(value: string | null | undefined): boolean {
  return Boolean((value ?? "").trim());
}

/**
 * Infere el selector visual sin borrar valores. Si hay persona y razón social, usa «ambos».
 */
export function inferTitularCorreccionModo(params: {
  apellido?: string | null;
  nombre?: string | null;
  razonSocial?: string | null;
}): TitularCorreccionModo {
  const persona = hasText(params.apellido) || hasText(params.nombre);
  const razon = hasText(params.razonSocial);
  if (persona && razon) return "ambos";
  if (razon && !persona) return "razon_social";
  return "persona";
}
