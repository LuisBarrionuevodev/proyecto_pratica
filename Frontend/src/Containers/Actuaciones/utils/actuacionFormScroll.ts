/**
 * Desplaza el contenido del modal al primer control con error MUI visible.
 * Complementa helperText inline sin Alert duplicado dentro del modal.
 */
export function scrollActuacionFormToFirstFieldError(
  container: HTMLElement | null | undefined,
  fieldErrors: Record<string, string>,
  behavior: ScrollBehavior = "smooth"
): void {
  const hasErrors = Object.values(fieldErrors).some((msg) => msg?.trim());
  if (!container || !hasErrors) return;

  const firstErrorControl = container.querySelector(
    ".Mui-error input, .Mui-error textarea, .Mui-error .MuiAutocomplete-input"
  ) as HTMLElement | null;

  if (firstErrorControl) {
    firstErrorControl.scrollIntoView({ behavior, block: "center" });
    if (typeof firstErrorControl.focus === "function") {
      firstErrorControl.focus({ preventScroll: true });
    }
    return;
  }

  container.scrollTo({ top: 0, behavior });
}
