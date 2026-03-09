import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ClearIcon from "@mui/icons-material/Clear";
import AddIcon from "@mui/icons-material/Add";

import { createDenuncia } from "../../../api/denunciasApi";
import { getCurrentMonthRange } from "../../../utils/dateRange";
import {
  errorAlertStyles,
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroTitleStyles,
} from "../../Actuaciones/styles/filtroStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

interface FormErrors {
  fecha?: string;
  calle?: string;
  numeroOEsquina?: string;
  motivo?: string;
}

interface DenunciaFormProps {
  showTitle?: boolean;
}

const DenunciaForm = ({ showTitle = true }: DenunciaFormProps) => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [open, setOpen] = useState(false);

  const [fecha, setFecha] = useState(defaultRange.hasta);
  const [calle, setCalle] = useState("");
  const [numeroOEsquina, setNumeroOEsquina] = useState("");
  const [motivo, setMotivo] = useState("");

  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const validate = (): boolean => {
    const nextErrors: FormErrors = {};

    const calleValue = calle.trim();
    const numeroValue = numeroOEsquina.trim();
    const motivoValue = motivo.trim();

    if (!fecha) nextErrors.fecha = "La fecha es obligatoria.";
    if (!calleValue) nextErrors.calle = "La calle es obligatoria.";
    if (!motivoValue) nextErrors.motivo = "El motivo es obligatorio.";
    if (!numeroValue) {
      nextErrors.numeroOEsquina = "Ingresá número o esquina.";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleClear = () => {
    setFecha(defaultRange.hasta);
    setCalle("");
    setNumeroOEsquina("");
    setMotivo("");
    setErrors({});
  };

  const handleSubmit = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);

    if (!validate()) return;

    try {
      setLoading(true);
      const numeroOrEsquina = numeroOEsquina.trim();
      const isNumero = /^\d+[a-zA-Z]?$/.test(numeroOrEsquina.replace(/\s+/g, ""));
      await createDenuncia({
        fecha,
        calle: calle.trim(),
        numero: isNumero ? numeroOrEsquina : null,
        interseccion: isNumero ? null : numeroOrEsquina,
        motivo: motivo.trim(),
      });
      setSuccessMsg("Denuncia creada correctamente.");
      handleClear();
      setOpen(false);
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        "No se pudo crear la denuncia.";
      setErrorMsg(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={filtroContainerStyles}>
      {showTitle && <Typography sx={filtroTitleStyles}>Carga de Denuncias</Typography>}

      {errorMsg && (
        <Alert severity="error" sx={errorAlertStyles} onClose={() => setErrorMsg(null)}>
          <strong>Error:</strong> {errorMsg}
        </Alert>
      )}

      {successMsg && (
        <Alert severity="success" sx={{ marginBottom: 2 }} onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      )}

      <Paper
        sx={{
          p: { xs: 2, sm: 3 },
          display: "flex",
          flexDirection: { xs: "column", sm: "row" },
          justifyContent: "space-between",
          alignItems: { xs: "flex-start", sm: "center" },
          gap: 2,
          backgroundColor: GLASS_COLORS.cardBg,
          borderRadius: "12px",
          border: `1px solid ${GLASS_COLORS.borderLight}`,
        }}
      >
        <Box>
          <Typography variant="h6" sx={{ color: "#fff", fontWeight: 700 }}>
            ¿Desea cargar una nueva denuncia?
          </Typography>
          <Typography sx={{ color: "rgba(255,255,255,0.75)" }}>
            Registrá una denuncia con una carga simple y rápida.
          </Typography>
        </Box>
        <Button
          onClick={() => {
            setErrorMsg(null);
            setErrors({});
            setOpen(true);
          }}
          startIcon={<AddIcon />}
          variant="contained"
          sx={filtroButtonPrimaryStyles}
        >
          Nueva denuncia
        </Button>
      </Paper>

      <Dialog open={open} onClose={() => !loading && setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Nueva denuncia</DialogTitle>
        <DialogContent dividers>
          <Box sx={filtroGridStyles}>
            <Box sx={filtroItemStyles}>
              <TextField
                fullWidth
                required
                type="date"
                label="Fecha"
                value={fecha}
                onChange={(e) => setFecha(e.target.value)}
                InputLabelProps={{ shrink: true }}
                variant="outlined"
                error={!!errors.fecha}
                helperText={errors.fecha || ""}
              />
            </Box>

            <Box sx={filtroItemStyles}>
              <TextField
                fullWidth
                required
                label="Calle"
                value={calle}
                onChange={(e) => setCalle(e.target.value)}
                variant="outlined"
                error={!!errors.calle}
                helperText={errors.calle || ""}
              />
            </Box>

            <Box sx={filtroItemStyles}>
              <TextField
                fullWidth
                required
                label="Número o esquina"
                value={numeroOEsquina}
                onChange={(e) => setNumeroOEsquina(e.target.value)}
                variant="outlined"
                error={!!errors.numeroOEsquina}
                helperText={errors.numeroOEsquina || ""}
              />
            </Box>

            <Box sx={filtroItemStyles}>
              <TextField
                fullWidth
                required
                label="Motivo"
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                variant="outlined"
                multiline
                minRows={3}
                error={!!errors.motivo}
                helperText={errors.motivo || ""}
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions sx={filtroButtonsStyles}>
          <Button
            onClick={handleClear}
            startIcon={<ClearIcon />}
            sx={filtroButtonSecondaryStyles}
            disabled={loading}
          >
            Limpiar
          </Button>
          <Button
            onClick={handleSubmit}
            startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
            sx={filtroButtonPrimaryStyles}
            variant="contained"
            disabled={loading}
          >
            {loading ? "Guardando..." : "Guardar denuncia"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DenunciaForm;
