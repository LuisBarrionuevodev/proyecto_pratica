import { useMemo, useState } from "react";
import axios from "axios";
import { Alert, Box, Paper, Typography } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ClearIcon from "@mui/icons-material/Clear";
import AddIcon from "@mui/icons-material/Add";

import { createDenuncia } from "../../../api/denunciasApi";
import { getCurrentMonthRange } from "../../../utils/dateRange";
import {
  dialogFormActionsRowSx,
  dialogFormGridSx,
  formDialogShortContentSx,
} from "../../../styles/formDialogStyles";
import { AppButton, AppDialog, AppTextField } from "../../../ui";
import {
  alertBaseStyles,
  errorAlertStyles,
  filtroContainerStyles,
  filtroTitleStyles,
  filtroButtonPrimaryStyles,
  COLORS,
} from "../../Actuaciones/styles/filtroStyles";

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
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        const data = err.response?.data as { detail?: string; msg?: string } | undefined;
        const serverText = data?.detail ?? data?.msg;
        if (status === 401) {
          setErrorMsg(
            "Sesión vencida o no iniciaste sesión. Volvé a iniciar sesión (te redirigimos al login si es necesario)."
          );
          return;
        }
        if (status === 403) {
          setErrorMsg(serverText ?? "Tu usuario no puede realizar esta acción (inactivo o sin permiso).");
          return;
        }
        setErrorMsg(serverText ?? "No se pudo crear la denuncia.");
        return;
      }
      setErrorMsg("No se pudo crear la denuncia.");
    } finally {
      setLoading(false);
    }
  };

  const tryCloseModal = () => {
    if (!loading) setOpen(false);
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
        <Alert severity="success" sx={alertBaseStyles} onClose={() => setSuccessMsg(null)}>
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
          backgroundColor: COLORS.grayDark,
          borderRadius: "8px",
          border: `1px solid ${COLORS.border}`,
          boxShadow:
            "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
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
        <AppButton
          dsVariant="primary"
          onClick={() => {
            setErrorMsg(null);
            setErrors({});
            setOpen(true);
          }}
          startIcon={<AddIcon />}
          sx={filtroButtonPrimaryStyles}
        >
          Nueva denuncia
        </AppButton>
      </Paper>

      <AppDialog
        open={open}
        onClose={() => tryCloseModal()}
        onCloseButtonClick={() => tryCloseModal()}
        title="Nueva denuncia"
        contentDividers
        contentSx={formDialogShortContentSx}
        actions={
          <Box sx={dialogFormActionsRowSx}>
            <AppButton
              dsVariant="ghost"
              onClick={handleClear}
              startIcon={<ClearIcon />}
              disabled={loading}
            >
              Limpiar
            </AppButton>
            <AppButton
              dsVariant="primary"
              onClick={handleSubmit}
              startIcon={<SendIcon />}
              loading={loading}
            >
              Guardar denuncia
            </AppButton>
          </Box>
        }
      >
        <Box sx={dialogFormGridSx}>
          <AppTextField
            appearance="glass"
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

          <AppTextField
            appearance="glass"
            fullWidth
            required
            label="Calle"
            value={calle}
            onChange={(e) => setCalle(e.target.value)}
            variant="outlined"
            error={!!errors.calle}
            helperText={errors.calle || ""}
          />

          <AppTextField
            appearance="glass"
            fullWidth
            required
            label="Número o esquina"
            value={numeroOEsquina}
            onChange={(e) => setNumeroOEsquina(e.target.value)}
            variant="outlined"
            error={!!errors.numeroOEsquina}
            helperText={errors.numeroOEsquina || ""}
          />

          <AppTextField
            appearance="glass"
            fullWidth
            required
            label="Motivo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            variant="outlined"
            multiline
            minRows={3}
            sx={{ gridColumn: "1 / -1" }}
            error={!!errors.motivo}
            helperText={errors.motivo || ""}
          />
        </Box>
      </AppDialog>
    </Box>
  );
};

export default DenunciaForm;
