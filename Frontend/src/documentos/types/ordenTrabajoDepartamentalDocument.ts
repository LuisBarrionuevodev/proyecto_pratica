/**
 * Modelo canónico para PDF «Orden de Trabajo Departamental» (una OT por ítem de ruta).
 */

export type OrdenTrabajoDepartamentalFila = {
  itemId: number;
  numeroOt: string;
  domicilioLinea: string;
  inspectoresTexto: string;
  fechaLegible: string;
  turnoLegible: string;
};

export type OrdenTrabajoDepartamentalDocumentModel = {
  rutaId: number;
  numeroRuta: number;
  fechaLegible: string;
  turnoLegible: string;
  ordenes: OrdenTrabajoDepartamentalFila[];
};
