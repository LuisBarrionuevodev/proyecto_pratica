import { Box, Chip, Typography } from "@mui/material";

import { crudDialogHeaderChipSx, CRUD_DIALOG_TEXT } from "../../styles/crudDialogTokens";

export type CrudDialogMode = "view" | "edit" | "create";

const MODE_LABEL: Record<CrudDialogMode, string> = {
  view: "Vista",
  edit: "Edición",
  create: "Alta",
};

export type CrudDialogHeaderProps = {
  /** Chip de dominio/módulo (p. ej. «Relevamientos»). */
  domainChip?: string | null;
  titulo: string;
  subtitulo?: string | null;
  /** Chip de estado operativo opcional (p. ej. «Pendiente»). */
  statusChip?: string | null;
  mode?: CrudDialogMode;
};

/**
 * Cabecera estándar para modales CRUD (dentro de `DialogTitle` / `CrudGlassDialog.title`).
 */
export function CrudDialogHeader({
  domainChip,
  titulo,
  subtitulo,
  statusChip,
  mode,
}: CrudDialogHeaderProps) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.5, minWidth: 0 }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, alignItems: "center" }}>
        {domainChip ? (
          <Chip label={domainChip} size="small" variant="outlined" sx={crudDialogHeaderChipSx.domain} />
        ) : null}
        {mode ? (
          <Chip label={MODE_LABEL[mode]} size="small" sx={crudDialogHeaderChipSx.mode} />
        ) : null}
        {statusChip ? (
          <Chip label={statusChip} size="small" variant="outlined" sx={crudDialogHeaderChipSx.status} />
        ) : null}
      </Box>
      <Typography
        component="span"
        variant="h6"
        sx={{ fontWeight: 700, fontSize: "1.05rem", lineHeight: 1.25, color: CRUD_DIALOG_TEXT.primary, mt: 0.25 }}
      >
        {titulo}
      </Typography>
      {subtitulo ? (
        <Typography variant="body2" sx={{ color: CRUD_DIALOG_TEXT.primary, fontWeight: 500, lineHeight: 1.4, opacity: 0.92 }}>
          {subtitulo}
        </Typography>
      ) : null}
    </Box>
  );
}

/** Etiqueta legible del modo (tests / UI externa). */
export function crudDialogModeLabel(mode: CrudDialogMode): string {
  return MODE_LABEL[mode];
}
