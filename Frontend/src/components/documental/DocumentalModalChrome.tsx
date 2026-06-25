import { Box } from "@mui/material";
import type { ReactNode } from "react";

import { docModalFooterButtonsSx, docModalFooterRowSx } from "../../styles/documentalModalTokens";

export type DocumentalModalTitleStackProps = {
  /** Texto del chip de dominio (p. ej. «Notificación», «Comprobación»). */
  dominioChip: string;
  titulo: string;
  subtitulo?: string | null;
  /** @deprecated No mostrar IDs en modales CRUD. Ignorado. */
  actuacionId?: number | null;
};

/**
 * Cabecera estándar de modales documentales (chip dominio → título → subtítulo).
 */
export function DocumentalModalTitleStack({
  dominioChip,
  titulo,
  subtitulo,
}: DocumentalModalTitleStackProps) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.5, width: "100%" }}>
      <Box component="span" sx={{ fontSize: "0.6875rem", fontWeight: 600, opacity: 0.86 }}>
        {dominioChip}
      </Box>
      <Box component="span" sx={{ fontWeight: 700, fontSize: "1.05rem", lineHeight: 1.25 }}>
        {titulo}
      </Box>
      {subtitulo ? (
        <Box component="span" sx={{ fontSize: "0.875rem", opacity: 0.86, lineHeight: 1.4 }}>
          {subtitulo}
        </Box>
      ) : null}
    </Box>
  );
}

export type DocumentalModalFooterProps = {
  /** @deprecated Cierre solo con la X del header. */
  onCerrar?: () => void;
  cerrarDisabled?: boolean;
  children?: ReactNode;
};

/**
 * Pie documental: acciones custom alineadas a la derecha. Sin botón Cerrar (cierre vía X).
 */
export function DocumentalModalFooter({ children }: DocumentalModalFooterProps) {
  if (!children) return null;
  return (
    <Box sx={docModalFooterRowSx}>
      <Box sx={{ flex: "1 1 120px", minWidth: 0 }} />
      <Box sx={docModalFooterButtonsSx}>{children}</Box>
    </Box>
  );
}
