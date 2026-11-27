import type { ManualMediaSaveOutcome } from "../../../features/media/utils/actuacionManualMediaSave";

export const EDIT_GUARDAR_CAMBIOS_LABEL = "Guardar cambios";
export const EDIT_CONTINUAR_SUBIDA_LABEL = "Continuar subida";

export const MENSAJE_EDIT_DATOS_OK_FOTOS_PENDIENTES =
  "La actuación se guardó. Algunas fotos todavía no se subieron. Podés continuar la carga.";

export const MENSAJE_EDIT_DATOS_INCERTOS =
  "No pudimos confirmar si se guardó. Revisá la actuación antes de volver a guardar.";

export const MENSAJE_EDIT_FOTOS_INCERTAS =
  "No pudimos confirmar si algunas fotos quedaron guardadas. Revisá la galería antes de reintentar.";

export const MENSAJE_EDIT_FOTOS_CIERRE_SIN_RECUPERAR =
  "La actuación ya está guardada. Las fotos que no terminaron de subir no se recuperan al cerrar.";

export const EDIT_FOTOS_PENDIENTES_ALERT =
  "La actuación se guardó. Algunas fotos todavía no se subieron. El formulario queda bloqueado hasta terminar la carga o cerrar (las fotos no subidas no se recuperan).";

export type EditSaveSessionOutcome = "success" | "aborted";

export type EditSavePrimaryAction = "save_data" | "continue_photos";

/**
 * Tras un PUT confirmado con fotos incompletas, el botón principal reintenta solo fotos.
 * Si el usuario pudiera editar datos (no es el caso: el formulario se bloquea), se usaría Guardar cambios.
 */
export function resolveEditSavePrimaryAction(datosConfirmadosConFotosPendientes: boolean): EditSavePrimaryAction {
  return datosConfirmadosConFotosPendientes ? "continue_photos" : "save_data";
}

export function editSavePrimaryLabel(action: EditSavePrimaryAction): string {
  return action === "continue_photos" ? EDIT_CONTINUAR_SUBIDA_LABEL : EDIT_GUARDAR_CAMBIOS_LABEL;
}

export function shouldCloseEditModalAfterMedia(
  outcome: ManualMediaSaveOutcome
): boolean {
  return outcome === "success";
}

/**
 * Orden de Editar: PUT una vez → fotos; reintento posterior solo fotos.
 * No cierra como éxito si queda alguna foto no READY.
 */
export async function runEditActuacionSaveFlow(deps: {
  datosYaConfirmados: boolean;
  fotosIncompletas: () => boolean;
  putSave: () => Promise<boolean>;
  uploadPhotos: () => Promise<ManualMediaSaveOutcome>;
}): Promise<{
  didPut: boolean;
  didUpload: boolean;
  sessionOutcome: EditSaveSessionOutcome;
  awaitingPhotos: boolean;
}> {
  let didPut = false;
  if (!deps.datosYaConfirmados) {
    const putOk = await deps.putSave();
    if (!putOk) {
      return { didPut: false, didUpload: false, sessionOutcome: "aborted", awaitingPhotos: false };
    }
    didPut = true;
  }

  if (!deps.fotosIncompletas()) {
    return { didPut, didUpload: false, sessionOutcome: "success", awaitingPhotos: false };
  }

  const media = await deps.uploadPhotos();
  if (media === "success") {
    return { didPut, didUpload: true, sessionOutcome: "success", awaitingPhotos: false };
  }
  return { didPut, didUpload: true, sessionOutcome: "aborted", awaitingPhotos: true };
}
