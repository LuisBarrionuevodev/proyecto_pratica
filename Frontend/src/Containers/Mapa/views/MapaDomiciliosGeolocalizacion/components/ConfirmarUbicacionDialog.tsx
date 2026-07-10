import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";

export const CONFIRMAR_UBICACION_TITULO = "Confirmar ubicación";

export const CONFIRMAR_UBICACION_MENSAJE =
  "¿Confirmás esta ubicación para el domicilio seleccionado?";

export const CONFIRMAR_UBICACION_SECUNDARIO =
  "Se guardará este punto como ubicación del domicilio.";

export type ConfirmarUbicacionDialogProps = {
  open: boolean;
  onConfirm: () => void;
  onClose: () => void;
  confirming?: boolean;
};

/**
 * Confirmación antes de persistir un pin manual en el mapa.
 */
const ConfirmarUbicacionDialog = ({
  open,
  onConfirm,
  onClose,
  confirming = false,
}: ConfirmarUbicacionDialogProps) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{CONFIRMAR_UBICACION_TITULO}</DialogTitle>
      <DialogContent>
        <DialogContentText>{CONFIRMAR_UBICACION_MENSAJE}</DialogContentText>
        <DialogContentText color="text.secondary" sx={{ mt: 1.5 }}>
          {CONFIRMAR_UBICACION_SECUNDARIO}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={confirming}>
          Cancelar
        </Button>
        <Button variant="contained" onClick={onConfirm} disabled={confirming}>
          Confirmar ubicación
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConfirmarUbicacionDialog;
