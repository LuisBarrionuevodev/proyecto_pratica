import { createContext, useCallback, useMemo, useState, type ReactNode } from "react";

import { Alert, Snackbar } from "@mui/material";

import { documentalGlassAlertSx } from "../../styles/documentalModalTokens";
import { layoutShell } from "../../theme/tokens";

export type FeedbackSeverity = "success" | "error" | "warning" | "info";

/**
 * API de notificaciones no bloqueantes (toast institucional).
 *
 * Pensado para rutina post-acción; errores de formulario siguen como campos locales (UX1c).
 */
export type AppFeedback = {
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
};

type ToastState =
  | {
      readonly id: number;
      readonly message: string;
      readonly severity: FeedbackSeverity;
    }
  | null;

/** Context interno para `useAppFeedback`. Exportado solo por si algún consumer avanzado lo necesita. */
export const GlobalFeedbackContext = createContext<AppFeedback | null>(null);

const DEFAULT_AUTO_HIDE_MS = 5500;
const TOP_OFFSET_PX = layoutShell.topBarHeightPx + 12;

/**
 * Provider global que renderiza un único `Snackbar` con `Alert` estilo glass (alineado a modales documentales).
 *
 * Debe montarse **dentro** de `ThemeProvider` de MUI.
 */
export function GlobalFeedbackProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState>(null);

  const push = useCallback((severity: FeedbackSeverity, message: string) => {
    const trimmed = message.trim();
    if (!trimmed) return;
    setToast((prev) => ({
      id: (prev?.id ?? 0) + 1,
      message: trimmed,
      severity,
    }));
  }, []);

  const value = useMemo<AppFeedback>(
    () => ({
      success: (m) => push("success", m),
      error: (m) => push("error", m),
      warning: (m) => push("warning", m),
      info: (m) => push("info", m),
    }),
    [push]
  );

  const dismiss = useCallback((_event?: unknown, reason?: string) => {
    if (reason === "clickaway") return;
    setToast(null);
  }, []);

  return (
    <GlobalFeedbackContext.Provider value={value}>
      {children}
      <Snackbar
        key={toast?.id ?? "closed"}
        open={toast !== null}
        autoHideDuration={DEFAULT_AUTO_HIDE_MS}
        onClose={dismiss}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        sx={{ top: `${TOP_OFFSET_PX}px` }}
      >
        {toast !== null ? (
          <Alert
            severity={toast.severity}
            onClose={dismiss}
            sx={{
              width: "100%",
              minWidth: { xs: 280, sm: 360 },
              maxWidth: 560,
              boxShadow: "0 8px 32px rgba(0, 0, 0, 0.45)",
              ...documentalGlassAlertSx,
            }}
          >
            {toast.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </GlobalFeedbackContext.Provider>
  );
}
