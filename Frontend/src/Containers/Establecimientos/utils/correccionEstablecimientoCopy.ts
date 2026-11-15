/**
 * Textos de alcance/advertencia alineados al canal de corrección controlada.
 */
export const CORRECCION_CONTRIBUYENTE_HINT =
  "Corrige datos del mismo contribuyente. No cambia el titular ni fusiona registros.";

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
