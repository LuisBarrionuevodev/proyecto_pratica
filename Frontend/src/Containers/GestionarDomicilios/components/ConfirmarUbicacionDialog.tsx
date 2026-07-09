import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";

export const CONFIRMAR_UBICACION_MENSAJE =
  "¿Estás seguro de dejar el punto en esta ubicación?";

export type ConfirmarUbicacionDialogProps = {
  open: boolean;
  domicilioLinea: string;
  lat: number;
  lng: number;
  onConfirm: () => void;
  onClose: () => void;
  confirming?: boolean;
};

/**
 * Confirmación antes de persistir un pin manual en el mapa.
 */
const ConfirmarUbicacionDialog = ({
  open,
  domicilioLinea,
  lat,
  lng,
  onConfirm,
  onClose,
  confirming = false,
}: ConfirmarUbicacionDialogProps) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Confirmar ubicación</DialogTitle>
      <DialogContent>
        <DialogContentText component="div">
          <strong>{domicilioLinea}</strong>
          <br />
          {CONFIRMAR_UBICACION_MENSAJE}
        </DialogContentText>
        <DialogContentText
          variant="caption"
          color="text.secondary"
          sx={{ mt: 1, display: "block" }}
          aria-hidden
        >
          Referencia interna: {lat.toFixed(5)}, {lng.toFixed(5)}
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
