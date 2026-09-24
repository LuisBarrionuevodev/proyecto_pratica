/** Slice operativo de la bandeja Actas de Comprobación. */
export type ComprobacionExportSlice = "expediente" | "oficio" | "reinspeccion" | "recorrido";

/** Fila canónica para Excel/PDF/indicadores (independiente del endpoint origen). */
export type ComprobacionExportRow = {
  actuacionId: number;
  comprobacionId: number | null;
  exportSlice: ComprobacionExportSlice;
  fechaActuacion: string;
  ordenTrabajo: string;
  actaComprobacionNum: string;
  contribuyente: string;
  documento: string;
  domicilio: string;
  calle: string;
  numero: string;
  rubro: string;
  comprobacionMotivo: string;
  expedienteEnvioNumero: string;
  expedienteEnvioAnio: string;
  fechaExpedienteEnvio: string;
  oficioNumero: string;
  oficioAnio: string;
  fechaOficio: string;
  causa: string;
  juzgado: string;
  expedienteRespuestaNumero: string;
  expedienteRespuestaAnio: string;
  fechaExpedienteRespuesta: string;
  /** CUMPLE / NO_CUMPLE cuando el backend lo expone en grid. */
  resultadoCumplimiento: string;
  estadoRecorrido: string;
  reinspeccionEstado: string;
  inspectores: string;
  /** Recorrido: todos los oficios (p. ej. `Oficio 3489/2026 · Oficio 3490/2026`). */
  oficiosAgregados: string;
  /** Recorrido: todos los expedientes asociados. */
  expedientesAgregados: string;
  /** Recorrido Excel compacto. */
  expedienteEnvioCompacto: string;
  oficiosNumeros: string;
  expedientesOficio: string;
  expedientesRespuesta: string;
  oficiosConRespuesta: string;
  causasAgregadas: string;
  juzgadosAgregados: string;
  estadoRecorridoVisitas: string;
};

export function sliceExportLabel(slice: ComprobacionExportSlice): string {
  switch (slice) {
    case "expediente":
      return "Pendiente expediente";
    case "oficio":
      return "Pendiente oficio";
    case "reinspeccion":
      return "Pendiente reinspección";
    case "recorrido":
      return "Recorrido";
    default:
      return slice;
  }
}

export function sliceTabLabel(slice: ComprobacionExportSlice): string {
  switch (slice) {
    case "expediente":
      return "Pendientes de expediente";
    case "oficio":
      return "Pendientes de oficio";
    case "reinspeccion":
      return "Pendientes de reinspección";
    case "recorrido":
      return "Recorrido";
    default:
      return slice;
  }
}
