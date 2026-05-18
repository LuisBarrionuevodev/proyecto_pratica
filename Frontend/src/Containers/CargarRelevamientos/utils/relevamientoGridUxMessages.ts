/**
 * Mensajes operativos en español para la grilla Glide de relevamiento y el rail de errores.
 * Mapea textos del backend (y residuos en inglés) a copy usable por inspectores.
 */

export function humanizeRelevamientoColumnLabel(glideKey: string): string {
  const map: Record<string, string> = {
    Fecha: "Fecha",
    Inspector: "Inspector",
    Calle: "Calle",
    Numero: "Número o esquina",
    Número: "Número o esquina",
    Rubro: "Rubro",
    Turno: "Turno",
    "Está abierto": "¿Está abierto?",
    ID: "Identificador",
    id: "Identificador",
  };
  return map[glideKey] ?? glideKey;
}

/**
 * Traduce un mensaje suelto (celda, `_row`, error global).
 */
export function translateRelevamientoValidationMessage(raw: string): string {
  const s = (raw || "").trim();
  if (!s) return s;

  const exactPairs: Array<[string, string]> = [
    ["Calle obligatoria.", "Completá la calle."],
    ["Número obligatorio.", "Completá el número o la esquina."],
    ["Inspector obligatorio.", "Elegí un inspector."],
    ["Rubro obligatorio.", "Completá el rubro."],
    ["Fecha obligatoria.", "Completá la fecha."],
    ["Inspector inválido.", "El inspector no está en el catálogo."],
    ["Rubro inválido.", "El rubro no existe en el catálogo."],
    ["Formato de fecha inválido. Use DD/MM/YYYY o YYYY-MM-DD.", "La fecha no es válida. Usá DD/MM/AAAA o AAAA-MM-DD."],
    [
      "Turno inválido (Mañana/MANIANA o Tarde/TARDE, o vacío).",
      "Turno inválido: elegí Mañana o Tarde (o dejalo vacío).",
    ],
    ["Fecha requerida.", "Completá la fecha."],
    ["id inválido", "El identificador del relevamiento no es válido."],
    ["numero_tipo inválido.", "El tipo de numeración no es válido."],
    ["No hay filas válidas para confirmar.", "No hay filas listas para guardar. Revisá los datos o los avisos por fila."],
    ["No hay filas para validar.", "No se pudo validar el lote. Intentá de nuevo o revisá la conexión."],
  ];

  for (const [from, to] of exactPairs) {
    if (s === from) return to;
  }

  if (s.startsWith("Duplicado en el lote: la misma calle y altura ya está cargada")) {
    const m = s.match(/\(fila ([^)]+)\)/);
    const ref = m ? ` Coincidencia con la fila técnica «${m[1]}».` : "";
    return `Ya cargaste la misma calle y altura en otra fila de este lote.${ref} En esquinas podés repetir el mismo cruce.`;
  }

  if (s.includes("Ya existe un relevamiento activo para esta dirección")) {
    return "Ya existe un relevamiento activo para esta dirección.";
  }

  if (/field required/i.test(s)) return "Campo obligatorio.";
  if (/invalid json/i.test(s)) return "No se pudo interpretar la respuesta del servidor.";

  return s;
}

/**
 * Línea para el rail: etiqueta humana + mensaje traducido.
 */
export function formatRelevamientoRailCellLine(columnKey: string, message: string): string {
  const label = humanizeRelevamientoColumnLabel(columnKey);
  const msg = translateRelevamientoValidationMessage(message);
  return `${label}: ${msg}`;
}

export function translateRelevamientoGlobalMessage(raw: string | null): string | null {
  if (!raw) return null;
  return translateRelevamientoValidationMessage(raw);
}
