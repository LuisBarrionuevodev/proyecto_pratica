import { Box, Stack, Typography } from "@mui/material";
import { AppButton, CardGlass } from "../../../ui";

export type RutasEmptyViewProps = {
  /** Abre el modal de creación de ruta (mismo flujo que el botón histórico "Crear borrador"). */
  onCrearBorrador: () => void;
};

/**
 * Estado vacío cuando no hay borrador de ruta en la pestaña TABLA.
 */
export function RutasEmptyView({ onCrearBorrador }: RutasEmptyViewProps) {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 2, px: 1 }}>
      <CardGlass sx={{ maxWidth: 520, width: "100%" }} contentPadding="md">
        <Stack spacing={2} alignItems="stretch">
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            No hay borrador activo en esta sesión
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center">
            Creá una ruta en BORRADOR para comenzar a asignar iniciadores y grupos.
          </Typography>
          <AppButton dsVariant="primary" fullWidth onClick={onCrearBorrador}>
            Crear borrador
          </AppButton>
        </Stack>
      </CardGlass>
    </Box>
  );
}
