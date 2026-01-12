import type { IActuacion } from "../types/actuaciones";
import type { IRelevamiento } from "../types/relevamientos";

const isRequired = (value: unknown) =>
  typeof value === "string"
    ? value.trim().length > 0
    : value !== undefined && value !== null;

const isNumber = (value: unknown) =>
  value !== null && value !== undefined && value !== "" && !isNaN(Number(value));

// Fecha YYYY-MM-DD
const isValidDate = (value: string) =>
  /^\d{4}-\d{2}-\d{2}$/.test(value);

const isValidRealDate = (value: string) => {
  const d = new Date(value);
  return !isNaN(d.getTime()) && value === d.toISOString().split('T')[0];
};




// Validaciones Actuaciones

export const validateActuacion = (a: Partial<IActuacion>) => {
  const errors: Record<string, string | undefined> = {};

  // --- CAMPOS OBLIGATORIOS REALES DE TU INTERFAZ ---

  if (!isRequired(a.orden_trabajo_numero))
    errors.orden_trabajo_numero = "Número OT requerido";

  if (!isRequired(a.fecha_actuacion))
    errors.fecha_actuacion = "Fecha requerida";

  if (!isRequired(a.rubro_nombre))
    errors.rubro_nombre = "Rubro requerido";

  if (!isRequired(a.inspector1))
    errors.inspector1 = "Inspector 1 requerido";

  if (!isRequired(a.inspector2))
    errors.inspector2 = "Inspector 2 requerido";

  if (!isRequired(a.inspector3))
    errors.inspector2 = "Inspector 3 requerido";

  if (!isRequired(a.calle))
    errors.calle = "Calle requerida";

  if (!isRequired(a.numero))
    errors.numero = "Número requerido";

  if (!isRequired(a.doc_tipo_codigo))
    errors.doc_tipo_codigo = "Tipo doc requerido";

  if (!isRequired(a.doc_nro))
    errors.doc_nro = "Documento requerido";

  if (!isRequired(a.contrib_apellido))
    errors.contrib_apellido = "Apellido requerido";

  if (!isRequired(a.contrib_nombre))
    errors.contrib_apellido = "Nombre requerido";

  // --- VALIDACIONES OPCIONALES ---
  if (a.decomiso_kilos_total != null && !isNumber(a.decomiso_kilos_total))
    errors.decomiso_kilos_total = "Kilos debe ser numérico";

  if (a.expediente_anio != null && !isNumber(a.expediente_anio))
    errors.expediente_anio = "Año inválido";

  if (a.oficio_anio != null && !isNumber(a.oficio_anio))
    errors.oficio_anio = "Año inválido";

  return errors;
};



// Validaciones Relevamientos

export const validateRelevamiento = (r: IRelevamiento) => {
  const errors: Record<string, string | undefined> = {};

  if (!isValidDate(r.fecha))
    errors.fecha = "Formato de fecha incorrecto (YYYY-MM-DD)";

  if (!isValidRealDate(r.fecha))
    errors.fecha = "Fecha inválida";

  if (!isRequired(r.inspector))
    errors.inspector = "Ingresa un inspector";

  if (!isRequired(r.direccion))
    errors.direccion = "Dirección requerida";

  if (!isRequired(r.rubro))
    errors.rubro = "Rubro requerido";

  return errors;
};
