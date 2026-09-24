import { Box } from "@mui/material";
import type { ReactNode } from "react";

import { CrudDialogSection } from "../crudDialog";
import { crudFieldGridSx } from "../../styles/crudDialogTokens";

/** Ocupa el ancho completo dentro de una grilla CRUD de 2 columnas. */
export function DocumentalCrudFullSpan({ children }: { children: ReactNode }) {
  return <Box sx={{ gridColumn: "1 / -1", width: "100%" }}>{children}</Box>;
}

export type DocumentalCrudSectionProps = {
  title: string;
  children: ReactNode;
  /** `grid`: campos en 2 columnas (sm+). `stack`: columna simple para listas/acciones. */
  layout?: "grid" | "stack";
  resumen?: string;
};

/** Sección liviana al estilo Actuaciones / Completar Trabajo (sin card documental pesada). */
export function DocumentalCrudSection({
  title,
  children,
  layout = "grid",
  resumen,
}: DocumentalCrudSectionProps) {
  return (
    <CrudDialogSection title={title} variant="plain">
      {resumen ? (
        <Box component="p" sx={{ m: 0, mb: 1.5, opacity: 0.88, fontSize: "0.8125rem", lineHeight: 1.45 }}>
          {resumen}
        </Box>
      ) : null}
      <Box sx={layout === "grid" ? crudFieldGridSx : { display: "flex", flexDirection: "column", gap: 2, width: "100%" }}>
        {children}
      </Box>
    </CrudDialogSection>
  );
}
