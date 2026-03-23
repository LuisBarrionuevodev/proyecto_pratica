/**
 * Tipos UI del módulo Establecimientos (mock hasta backend).
 * Dominio independiente de Domicilios.
 */

export type EstablecimientoEstadoAdmin = "HABILITADO" | "INHABILITADO" | "PENDIENTE";

export interface IEstablecimientoListRow {
  id: string;
  calle: string;
  interseccion: string;
  rubro: string;
  rubroSlug: "gastronomia" | "industrial" | "minorista" | "servicios" | "otro";
  nombre: string;
  apellido: string;
  dni: string;
  distrito: string;
  /** Mock: para filtro de rango (YYYY-MM-DD). */
  fechaUltimaInspeccion: string;
  /** Texto comercial / fantasía (detalle) */
  razonSocial: string;
  rubroDetalle: string;
  estadoAdmin: EstablecimientoEstadoAdmin;
  direccionCompleta: string;
}

export type ResultadoInspeccionUi = "CONFORME" | "APROBADO" | "OBSERVADO" | "INFRACCION";

export interface IHistorialInspeccionRow {
  id: string;
  fecha: string;
  tipoInspeccion: string;
  ordenTrabajo: string;
  inspectoresIniciales: string;
  resultado: ResultadoInspeccionUi;
}

export interface IActuacionEstablecimientoRow {
  id: string;
  fecha: string;
  tipo: string;
  resumen: string;
}

export interface IEstablecimientoDetalle extends IEstablecimientoListRow {
  historialInspecciones: IHistorialInspeccionRow[];
  actuaciones: IActuacionEstablecimientoRow[];
  documentosMock: { nombre: string; tipo: "pdf" | "img" }[];
  alertaTitulo: string | null;
  alertaSubtitulo: string | null;
}
