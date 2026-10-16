export type AppWebUpdateMode = "service_worker_update" | "hard_reload";

/**
 * Detecta si hay un service worker en espera (actualización PWA) o solo recarga dura.
 */
export async function detectAppWebUpdateMode(): Promise<AppWebUpdateMode> {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) {
    return "hard_reload";
  }
  try {
    const registration = await navigator.serviceWorker.getRegistration();
    if (!registration?.waiting) return "hard_reload";
    return "service_worker_update";
  } catch {
    return "hard_reload";
  }
}

export function appWebUpdateButtonLabel(mode: AppWebUpdateMode): string {
  return mode === "service_worker_update" ? "Actualizar aplicación" : "Recargar aplicación";
}

/**
 * Activa la nueva versión del SW si existe; si no, recarga la página sin tocar almacenamiento local.
 */
export async function runAppWebUpdate(mode: AppWebUpdateMode): Promise<void> {
  if (mode === "service_worker_update" && "serviceWorker" in navigator) {
    const registration = await navigator.serviceWorker.getRegistration();
    const waiting = registration?.waiting;
    if (waiting) {
      waiting.postMessage({ type: "SKIP_WAITING" });
      await new Promise<void>((resolve) => {
        const onChange = () => {
          navigator.serviceWorker.removeEventListener("controllerchange", onChange);
          resolve();
        };
        navigator.serviceWorker.addEventListener("controllerchange", onChange);
      });
      window.location.reload();
      return;
    }
  }
  window.location.reload();
}
