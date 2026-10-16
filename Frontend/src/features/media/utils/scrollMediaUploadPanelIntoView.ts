/** Scroll suave si el navegador lo soporta y el usuario no pidió reducir movimiento. */
export function resolveMediaUploadPanelScrollBehavior(): ScrollBehavior {
  if (typeof window === "undefined") return "auto";
  try {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return "auto";
    return "smooth";
  } catch {
    return "auto";
  }
}

/**
 * Desplaza el contenedor scrolleable del modal hasta el panel de progreso.
 * `block: nearest` evita saltos en desktop si el panel ya está visible.
 */
export function scrollMediaUploadPanelIntoView(panel: HTMLElement | null | undefined): void {
  if (!panel) return;
  panel.scrollIntoView({
    block: "nearest",
    inline: "nearest",
    behavior: resolveMediaUploadPanelScrollBehavior(),
  });
}
