import { useMemo, useState } from "react";
import axios from "axios";
import { Alert, Box, Stack, Typography } from "@mui/material";
import ClearIcon from "@mui/icons-material/Clear";
import AddIcon from "@mui/icons-material/Add";

import { createDenuncia } from "../../../api/denunciasApi";
import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudDialogSection,
  CrudFormErrorSummary,
  CrudFormSlot,
  CrudGlassDialog,
} from "../../../components/crudDialog";
import { getCurrentMonthRange } from "../../../utils/dateRange";
import { DOC_MODAL_BLOCK_STACK_SPACING } from "../../../styles/documentalModalTokens";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton, AppTextField, CardGlass } from "../../../ui";
import { alertBaseStyles, errorAlertStyles } from "../../Actuaciones/styles/filtroStyles";
import { DENUNCIA_MODAL_LABELS } from "../../Relevamientos/utils/denunciaModalLabels";

const tactic = '"Tactic Sans", sans-serif' as const;

const denunciaDialogFormGridSx = {
  display: "grid",
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
  gap: 2,
  width: "100%",
  minWidth: 0,
} as const;

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
    setErrorMsg(null);
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
      setSuccessMsg("Listo: la denuncia quedó registrada.");
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
    <Box
      sx={{
        width: "100%",
        minWidth: 0,
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      {showTitle && (
        <Typography
          sx={{
            fontFamily: tactic,
            fontWeight: 700,
            fontSize: "1.1rem",
            color: GLASS_COLORS.textPrimary,
          }}
        >
          Carga de denuncias
        </Typography>
      )}

      {errorMsg && !open && (
        <Alert severity="error" sx={errorAlertStyles} onClose={() => setErrorMsg(null)}>
          <strong>Error:</strong> {errorMsg}
        </Alert>
      )}

      {successMsg && (
        <Alert severity="success" sx={alertBaseStyles} onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      )}

      <CardGlass sx={{ width: "100%", minWidth: 0 }}>
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            justifyContent: "space-between",
            alignItems: { xs: "stretch", sm: "center" },
            gap: 2,
            minWidth: 0,
          }}
        >
          <Box sx={{ minWidth: 0, flex: { sm: "1 1 auto" } }}>
            <Typography
              sx={{
                fontFamily: tactic,
                fontWeight: 700,
                fontSize: "1rem",
                color: GLASS_COLORS.textPrimary,
                letterSpacing: "0.02em",
              }}
            >
              ¿Querés registrar una denuncia?
            </Typography>
            <Typography
              sx={{
                fontFamily: tactic,
                mt: 0.5,
                fontSize: "0.875rem",
                color: GLASS_COLORS.textMuted,
                lineHeight: 1.45,
              }}
            >
              Fecha, domicilio y motivo en un solo paso. Después queda en cola para planificación.
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
            sx={{ flexShrink: 0, alignSelf: { xs: "stretch", sm: "center" } }}
            data-testid="denuncia-abrir-agregar"
          >
            {DENUNCIA_MODAL_LABELS.AGREGAR_DENUNCIA}
          </AppButton>
        </Box>
      </CardGlass>

      <CrudGlassDialog
        open={open}
        onClose={() => tryCloseModal()}
        onCloseButtonClick={() => tryCloseModal()}
        maxWidth="md"
        title={
          <CrudDialogHeader
            domainChip="Denuncias"
            mode="create"
            titulo={DENUNCIA_MODAL_LABELS.AGREGAR_DENUNCIA}
            subtitulo="Fecha, domicilio y motivo del reporte"
          />
        }
        actions={
          <CrudDialogActions
            mode="create"
            onSave={() => void handleSubmit()}
            loading={loading}
            saveLabel={DENUNCIA_MODAL_LABELS.GUARDAR_DENUNCIA}
            extraActions={
              <AppButton
                dsVariant="ghost"
                dsSize="sm"
                onClick={handleClear}
                startIcon={<ClearIcon />}
                disabled={loading}
              >
                {DENUNCIA_MODAL_LABELS.LIMPIAR}
              </AppButton>
            }
          />
        }
      >
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          <CrudFormErrorSummary message={errorMsg} />
          <CrudDialogSection title="Datos de la denuncia" variant="plain">
            <Box sx={denunciaDialogFormGridSx}>
              <CrudFormSlot label="Fecha" mode="edit" required error={!!errors.fecha} helperText={errors.fecha}>
                <AppTextField
                  appearance="glass"
                  fullWidth
                  required
                  type="date"
                  label="Fecha"
                  value={fecha}
                  onChange={(e) => setFecha(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  error={!!errors.fecha}
                  helperText={errors.fecha || undefined}
                />
              </CrudFormSlot>
              <CrudFormSlot label="Calle" mode="edit" required error={!!errors.calle} helperText={errors.calle}>
                <AppTextField
                  appearance="glass"
                  fullWidth
                  required
                  label="Calle"
                  value={calle}
                  onChange={(e) => setCalle(e.target.value)}
                  error={!!errors.calle}
                  helperText={errors.calle || undefined}
                />
              </CrudFormSlot>
              <CrudFormSlot
                label="Número o esquina"
                mode="edit"
                required
                error={!!errors.numeroOEsquina}
                helperText={errors.numeroOEsquina}
              >
                <AppTextField
                  appearance="glass"
                  fullWidth
                  required
                  label="Número o esquina"
                  value={numeroOEsquina}
                  onChange={(e) => setNumeroOEsquina(e.target.value)}
                  error={!!errors.numeroOEsquina}
                  helperText={errors.numeroOEsquina || undefined}
                />
              </CrudFormSlot>
              <CrudFormSlot
                label="Motivo"
                mode="edit"
                required
                error={!!errors.motivo}
                helperText={errors.motivo}
                sx={{ gridColumn: { sm: "1 / -1" } }}
              >
                <AppTextField
                  appearance="glass"
                  fullWidth
                  required
                  label="Motivo"
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  multiline
                  minRows={3}
                  error={!!errors.motivo}
                  helperText={errors.motivo || undefined}
                />
              </CrudFormSlot>
            </Box>
          </CrudDialogSection>
        </Stack>
      </CrudGlassDialog>
    </Box>
  );
};

export default DenunciaForm;
