import { useEffect, type RefObject } from "react";
import { Alert } from "@mui/material";

import { useCrudDialogScrollContainer } from "./CrudGlassDialog";

export type CrudFormErrorSummaryProps = {
  /** Mensaje global (400/422 sin campo o resumen). */
  message?: string | null;
  /** Contenedor scrolleable; por defecto el de `CrudGlassDialog`. */
  scrollContainerRef?: RefObject<HTMLElement | null>;
  /** Desplazar al top al mostrar error. */
  scrollOnShow?: boolean;
};

/** Desplaza el contenedor al inicio (helper testeable). */
export function scrollCrudDialogToTop(container: HTMLElement | null | undefined, behavior: ScrollBehavior = "smooth") {
  if (!container) return;
  container.scrollTo({ top: 0, behavior });
}

/**
 * Alerta de error global arriba del formulario.
 * Al aparecer un mensaje, hace scroll al top del contenido del modal.
 */
export function CrudFormErrorSummary({
  message,
  scrollContainerRef,
  scrollOnShow = true,
}: CrudFormErrorSummaryProps) {
  const ctxRef = useCrudDialogScrollContainer();
  const containerRef = scrollContainerRef ?? ctxRef;

  useEffect(() => {
    if (!message || !scrollOnShow) return;
    scrollCrudDialogToTop(containerRef?.current ?? null);
  }, [message, scrollOnShow, containerRef]);

  if (!message?.trim()) return null;

  return (
    <Alert severity="error" sx={{ width: "100%", borderRadius: 2 }}>
      {message}
    </Alert>
  );
}
