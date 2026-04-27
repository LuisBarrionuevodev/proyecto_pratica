/**
 * Modelo canónico para documentos PDF de una ruta publicada.
 * Construido una sola vez desde API (`IRutaTrabajo`, grupos, ítems) y consumido
 * por los renderers de resumen y órdenes de salida (sin duplicar reglas de armado).
 */

export type RutaDocumentoInspector = {
  inspectorId: number;
  nombreCompleto: string;
  numeroAfiliado: string;
};

export type RutaDocumentoItemFila = {
  itemId: number;
  ordenVisita: number;
  domicilioTexto: string;
  distritoNombre: string | null;
  rubroNombre: string | null;
  ordenTrabajoLabel: string | null;
  tipoIniciador: string | null;
  lat: number | null;
  lng: number | null;
};

export type RutaDocumentoGrupo = {
  grupoId: number;
  nombreGrupo: string;
  inspectores: RutaDocumentoInspector[];
  items: RutaDocumentoItemFila[];
};

/** Inspectores únicos con direcciones agregadas (órdenes de salida). */
export type RutaDocumentoInspectorSalida = RutaDocumentoInspector & {
  direccionesRuta: string[];
};

/** Punto para mini-mapa del PDF (misma leyenda de colores que el mapa operativo por índice de grupo). */
export type RutaDocumentoMapaPunto = {
  lat: number;
  lng: number;
  /** Índice 0-based del grupo en el listado `grupos` de la petición (G1 → 0, G2 → 1, …). */
  grupoIx: number;
  /** Orden de visita dentro del grupo (1, 2, …). */
  ordenEnGrupo: number;
};

export type RutaPublicadaDocumentModel = {
  rutaId: number;
  numeroRuta: number;
  fechaIso: string;
  fechaLegible: string;
  turnoCodigo: string;
  turnoLegible: string;
  estadoRuta: string;
  observaciones: string | null;
  displayName: string | null;
  grupos: RutaDocumentoGrupo[];
  inspectoresSalida: RutaDocumentoInspectorSalida[];
  /** Puntos con coordenadas válidas para mini-mapa estático. */
  puntosMapa: RutaDocumentoMapaPunto[];
};
