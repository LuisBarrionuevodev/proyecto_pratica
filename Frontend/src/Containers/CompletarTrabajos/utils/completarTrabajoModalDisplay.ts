import { tipoIniciadorDesdeCodigoApi } from "../../RutasTrabajo/planificacion/utils/iniciadorDisplay";
import { showContribuyenteDomicilioEditableEnCompletarTrabajo } from "./completarTrabajoReinspeccionNotificacionUi";

/** Título del header: etiqueta humanizada del tipo de iniciador. */
export function completarTrabajoHeaderTitulo(tipoIniciador: string | null | undefined): string {
  return tipoIniciadorDesdeCodigoApi(tipoIniciador) ?? "—";
}

/** Subtítulo del header con fecha operativa. */
export function completarTrabajoHeaderSubtitulo(fecha: string | null | undefined): string {
  const f = fecha?.trim();
  return `Fecha: ${f || "—"}`;
}

/** Domicilio en bloque Detalle solo cuando no se edita abajo. */
export function completarTrabajoShowDomicilioEnDetalle(tipoIniciador: string | null | undefined): boolean {
  return !showContribuyenteDomicilioEditableEnCompletarTrabajo(tipoIniciador);
}
