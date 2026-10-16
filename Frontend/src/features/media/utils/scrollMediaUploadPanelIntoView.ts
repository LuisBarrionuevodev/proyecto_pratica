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

function findScrollableAncestor(node: HTMLElement | null): HTMLElement | null {
  let el: HTMLElement | null = node?.parentElement ?? null;
  while (el) {
    const style = getComputedStyle(el);
    const overflowY = style.overflowY;
    if (
      (overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay") &&
      el.scrollHeight > el.clientHeight + 1
    ) {
      return el;
    }
    el = el.parentElement;
  }
  return null;
}

function isElementFullyVisibleInContainer(container: HTMLElement, target: HTMLElement): boolean {
  const cRect = container.getBoundingClientRect();
  const tRect = target.getBoundingClientRect();
  const pad = 6;
  return tRect.top >= cRect.top + pad && tRect.bottom <= cRect.bottom - pad;
}

/**
 * Desplaza el contenedor scrolleable del modal hasta el panel de progreso.
 * `block: nearest` evita saltos en desktop si el panel ya está visible.
 */
export function scrollMediaUploadPanelIntoView(
  panel: HTMLElement | null | undefined,
  scrollContainer?: HTMLElement | null
): void {
  if (!panel) return;
  const behavior = resolveMediaUploadPanelScrollBehavior();
  const container = scrollContainer ?? findScrollableAncestor(panel);

  if (container) {
    if (isElementFullyVisibleInContainer(container, panel)) return;
    const panelTop = panel.getBoundingClientRect().top;
    const containerTop = container.getBoundingClientRect().top;
    const delta = panelTop - containerTop + container.scrollTop - 8;
    container.scrollTo({ top: Math.max(0, delta), behavior });
    return;
  }

  panel.scrollIntoView({
    block: "nearest",
    inline: "nearest",
    behavior,
  });
}

/** Espera al paint de React antes de desplazar el panel (p. ej. tras click en Subir). */
export function scheduleScrollMediaUploadPanelIntoView(
  panel: HTMLElement | null | undefined,
  scrollContainer?: HTMLElement | null
): void {
  if (!panel) return;
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      scrollMediaUploadPanelIntoView(panel, scrollContainer ?? undefined);
    });
  });
}
