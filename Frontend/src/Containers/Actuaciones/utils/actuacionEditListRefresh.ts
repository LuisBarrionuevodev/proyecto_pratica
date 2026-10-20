/**
 * Refresco del listado tras guardar edición. Si el modal queda abierto para subir fotos, no refetch aún.
 */
export function scheduleActuacionListRefreshAfterSave(
  deferDialogClose: boolean,
  triggerRefresh: () => void,
  onRefresh?: () => void
): void {
  if (deferDialogClose) return;
  triggerRefresh();
  setTimeout(() => onRefresh?.(), 100);
}
