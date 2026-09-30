/**
 * Cierra edición en el elemento enfocado y espera un par de frames para que
 * handlers de blur / `onCellEdited` actualicen estado antes de validar o guardar.
 */
export async function flushActiveElementBeforeAction(): Promise<void> {
  const active = document.activeElement;
  if (active instanceof HTMLElement && active !== document.body) {
    active.blur();
  }
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve());
    });
  });
  await new Promise<void>((resolve) => {
    setTimeout(resolve, 0);
  });
}
