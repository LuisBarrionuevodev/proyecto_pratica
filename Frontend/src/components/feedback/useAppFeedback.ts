import { useContext } from "react";

import { GlobalFeedbackContext, type AppFeedback } from "./GlobalFeedbackProvider";

/**
 * Obtiene las funciones globales `success`/`error`/`warning`/`info` montadas por `GlobalFeedbackProvider`.
 *
 * @throws Error si no hay Provider en el árbol (mensaje orientativo a desarrolladores).
 */
export function useAppFeedback(): AppFeedback {
  const ctx = useContext(GlobalFeedbackContext);
  if (!ctx) {
    throw new Error("useAppFeedback debe usarse dentro de GlobalFeedbackProvider.");
  }
  return ctx;
}
