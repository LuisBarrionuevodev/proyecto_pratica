import { useEffect } from "react";

import { useAppFeedback } from "../feedback";

/**
 * Muestra errores generales de modal vía popup superior (sin Alert inline duplicado).
 */
export function useNotifyModalApiError(apiError: string | null | undefined, enabled = true): void {
  const feedback = useAppFeedback();
  useEffect(() => {
    if (!enabled || !apiError) return;
    feedback.error(apiError);
  }, [apiError, enabled, feedback]);
}
