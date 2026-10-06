import { Component, type ErrorInfo, type ReactNode } from "react";
import { Alert, Stack, Typography } from "@mui/material";
import { AppButton } from "../../../ui";

type Props = {
  resetKey: string | number;
  rutaItemId: number | null;
  onClosePanel: () => void;
  children: ReactNode;
};

type State = {
  hasError: boolean;
  message: string;
};

/**
 * Fallback local del panel de fotos (MEDIA.2C.2). No sustituye corregir la causa raíz.
 */
export class MediaUploadPanelErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: unknown): State {
    const message = error instanceof Error ? error.message : "Error desconocido";
    return { hasError: true, message };
  }

  componentDidUpdate(prevProps: Props): void {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, message: "" });
    }
  }

  componentDidCatch(error: unknown, info: ErrorInfo): void {
    console.error("[MediaUploadPanel]", {
      action: "render",
      message: error instanceof Error ? error.message : String(error),
      rutaItemId: this.props.rutaItemId,
      categoria: null,
      fileCount: null,
      componentStack: info.componentStack,
    });
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <Alert severity="error" sx={{ borderRadius: 2 }}>
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            No se pudieron preparar las fotos.
          </Typography>
          <Stack direction="row" spacing={1}>
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              onClick={() => this.setState({ hasError: false, message: "" })}
            >
              Reintentar
            </AppButton>
            <AppButton dsVariant="ghost" dsSize="sm" onClick={this.props.onClosePanel}>
              Cerrar
            </AppButton>
          </Stack>
        </Alert>
      );
    }
    return this.props.children;
  }
}
