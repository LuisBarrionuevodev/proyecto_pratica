import { useCallback, useEffect, useMemo, useState } from "react";
import type { DialogProps } from "@mui/material/Dialog";
import {
  Alert,
  Box,
  FormControl,
  FormControlLabel,
  FormLabel,
  Radio,
  RadioGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";

import {
  dialogFormActionsRowSx,
  formDialogContentStackSx,
  formDialogShortContentSx,
} from "../styles/formDialogStyles";
import { GLASS_COLORS } from "../styles/GlassStyles";
import {
  exportPeriodModeLabel,
  formatExportDatePreview,
  getMonthRange,
  getWorkweekRange,
  resolveExportPeriodRange,
  validateCustomExportRange,
} from "../utils/exportPeriodRange";
import { AppButton } from "./AppButton";
import { AppDialog } from "./AppDialog";
import { AppTextField } from "./AppTextField";
import type {
  ExportDataDialogProps,
  ExportFormat,
  ExportPeriodMode,
} from "./exportDataDialog.types";

export type { ExportDataDialogProps, ExportFormat, ExportPeriodMode, ExportDateRange } from "./exportDataDialog.types";

const DEFAULT_PERIOD_MODES: ExportPeriodMode[] = ["workweek", "month", "custom"];
const DEFAULT_FORMATS: ExportFormat[] = ["excel", "pdf"];

const sectionLabelSx = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "0.75rem",
  fontWeight: 700,
  letterSpacing: "0.08em",
  textTransform: "uppercase" as const,
  color: GLASS_COLORS.textPrimary,
  mb: 0.85,
};

const radioLabelSx = {
  "& .MuiFormControlLabel-label": {
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "0.92rem",
    fontWeight: 600,
    color: GLASS_COLORS.textPrimary,
    lineHeight: 1.35,
  },
};

const radioSx = {
  color: "rgba(255,255,255,0.45)",
  "&.Mui-checked": {
    color: GLASS_COLORS.primary,
  },
};

const formatLabel: Record<ExportFormat, string> = {
  excel: "Excel (.xlsx)",
  pdf: "PDF",
};

function FormatIcon({ format }: { format: ExportFormat }) {
  if (format === "pdf") {
    return <PictureAsPdfOutlinedIcon sx={{ fontSize: 19, mr: 0.5, verticalAlign: "middle", opacity: 0.95 }} />;
  }
  return <FileDownloadOutlinedIcon sx={{ fontSize: 19, mr: 0.5, verticalAlign: "middle", opacity: 0.95 }} />;
}

/**
 * Modal común de exportación (período + formato).
 * El padre implementa `onExport` (fetch backend, generación Excel/PDF) y controla `loading` / `error`.
 */
export function ExportDataDialog({
  open,
  onClose,
  title = "Exportar datos",
  subtitle,
  defaultPeriod = "month",
  defaultFormat = "excel",
  periodModes = DEFAULT_PERIOD_MODES,
  formats = DEFAULT_FORMATS,
  disabledFormats,
  initialCustomRange,
  minDate,
  maxDate,
  loading = false,
  error = null,
  onClearError,
  showPeriod = true,
  scopeHint,
  onExport,
  maxWidth = "sm",
  fullWidth = true,
}: ExportDataDialogProps & Pick<DialogProps, "maxWidth" | "fullWidth">) {
  const [periodMode, setPeriodMode] = useState<ExportPeriodMode>(defaultPeriod);
  const [format, setFormat] = useState<ExportFormat>(defaultFormat);
  const [customDesde, setCustomDesde] = useState("");
  const [customHasta, setCustomHasta] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [desdeFieldError, setDesdeFieldError] = useState<string | undefined>();
  const [hastaFieldError, setHastaFieldError] = useState<string | undefined>();

  const enabledFormats = useMemo(
    () => formats.filter((f) => disabledFormats?.[f] == null),
    [formats, disabledFormats]
  );

  const resetForm = useCallback(() => {
    setPeriodMode(defaultPeriod);
    setFormat(enabledFormats.includes(defaultFormat) ? defaultFormat : enabledFormats[0] ?? defaultFormat);
    setCustomDesde(initialCustomRange?.desde ?? "");
    setCustomHasta(initialCustomRange?.hasta ?? "");
    setLocalError(null);
    setDesdeFieldError(undefined);
    setHastaFieldError(undefined);
  }, [defaultPeriod, defaultFormat, enabledFormats, initialCustomRange?.desde, initialCustomRange?.hasta]);

  useEffect(() => {
    if (open) {
      resetForm();
      onClearError?.();
    }
  }, [open, resetForm, onClearError]);

  useEffect(() => {
    if (!enabledFormats.includes(format) && enabledFormats.length > 0) {
      setFormat(enabledFormats[0]);
    }
  }, [enabledFormats, format]);

  const presetPreview = useMemo(() => {
    if (periodMode === "workweek") return getWorkweekRange();
    if (periodMode === "month") return getMonthRange();
    return null;
  }, [periodMode]);

  const customValidation = useMemo(() => {
    if (periodMode !== "custom") return { ok: true as const };
    return validateCustomExportRange(customDesde, customHasta, minDate, maxDate);
  }, [periodMode, customDesde, customHasta, minDate, maxDate]);

  const displayError = error ?? localError;

  const handleUserChange = useCallback(() => {
    setLocalError(null);
    setDesdeFieldError(undefined);
    setHastaFieldError(undefined);
    onClearError?.();
  }, [onClearError]);

  const handlePeriodChange = (value: ExportPeriodMode) => {
    handleUserChange();
    setPeriodMode(value);
  };

  const handleFormatChange = (value: ExportFormat) => {
    if (disabledFormats?.[value]) return;
    handleUserChange();
    setFormat(value);
  };

  const handleExport = () => {
    if (loading) return;
    if (disabledFormats?.[format]) return;

    const resolved = resolveExportPeriodRange(periodMode, {
      customRange: { desde: customDesde, hasta: customHasta },
      minDate,
      maxDate,
    });

    if (!resolved.ok) {
      setLocalError(resolved.error);
      if (periodMode === "custom") {
        const v = validateCustomExportRange(customDesde, customHasta, minDate, maxDate);
        if (!v.ok) {
          setDesdeFieldError(v.desdeError);
          setHastaFieldError(v.hastaError);
        }
      }
      return;
    }

    void onExport({
      format,
      periodMode,
      desde: resolved.range.desde,
      hasta: resolved.range.hasta,
    });
  };

  const exportDisabled =
    loading ||
    enabledFormats.length === 0 ||
    Boolean(disabledFormats?.[format]) ||
    (periodMode === "custom" && !customValidation.ok);

  const blockClose = loading;

  const handleDialogClose: DialogProps["onClose"] = (_event, _reason) => {
    if (blockClose) return;
    onClose();
  };

  const handleCloseButton = () => {
    if (blockClose) return;
    onClose();
  };

  return (
    <AppDialog
      open={open}
      onClose={handleDialogClose}
      onCloseButtonClick={handleCloseButton}
      title={title}
      maxWidth={maxWidth}
      fullWidth={fullWidth}
      contentDividers
      contentSx={formDialogShortContentSx}
      showCloseButton
      disableEscapeKeyDown={blockClose}
      disableBackdropClick={blockClose}
      actions={
        <Box sx={dialogFormActionsRowSx}>
          <AppButton dsVariant="ghost" onClick={handleCloseButton} disabled={loading}>
            Cancelar
          </AppButton>
          <AppButton
            dsVariant="primary"
            startIcon={<FileDownloadOutlinedIcon />}
            onClick={handleExport}
            disabled={exportDisabled}
            loading={loading}
          >
            Exportar
          </AppButton>
        </Box>
      }
    >
      <Box sx={formDialogContentStackSx}>
        {subtitle ? (
          <Typography
            variant="subtitle1"
            sx={{
              color: GLASS_COLORS.textPrimary,
              fontFamily: '"Tactic Sans", sans-serif',
              fontWeight: 600,
              lineHeight: 1.35,
            }}
          >
            {subtitle}
          </Typography>
        ) : null}

        {scopeHint ? (
          <Typography
            variant="caption"
            sx={{
              color: GLASS_COLORS.textSecondary,
              fontFamily: '"Tactic Sans", sans-serif',
              display: "block",
              fontWeight: 500,
            }}
          >
            {scopeHint}
          </Typography>
        ) : null}

        {showPeriod ? (
          <FormControl component="fieldset" disabled={loading}>
            <FormLabel component="legend" sx={sectionLabelSx}>
              Período
            </FormLabel>
            <RadioGroup value={periodMode} onChange={(_, value) => handlePeriodChange(value as ExportPeriodMode)}>
              {periodModes.map((mode) => (
                <FormControlLabel
                  key={mode}
                  value={mode}
                  control={<Radio size="small" sx={radioSx} />}
                  label={exportPeriodModeLabel(mode)}
                  sx={radioLabelSx}
                />
              ))}
            </RadioGroup>

            {presetPreview && periodMode !== "custom" ? (
              <Typography
                variant="body2"
                sx={{
                  mt: 0.75,
                  ml: 4,
                  color: GLASS_COLORS.textPrimary,
                  fontFamily: '"Tactic Sans", sans-serif',
                  fontWeight: 600,
                  fontSize: "0.9rem",
                }}
              >
                Del {formatExportDatePreview(presetPreview.desde)} al {formatExportDatePreview(presetPreview.hasta)}
              </Typography>
            ) : null}

            {periodMode === "custom" ? (
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "repeat(2, minmax(0, 1fr))" },
                  gap: 2,
                  mt: 1.5,
                  ml: { xs: 0, sm: 2 },
                }}
              >
                <AppTextField
                  appearance="glass"
                  label="Desde"
                  type="date"
                  value={customDesde}
                  onChange={(e) => {
                    handleUserChange();
                    setCustomDesde(e.target.value);
                  }}
                  disabled={loading}
                  error={
                    Boolean(desdeFieldError) ||
                    (periodMode === "custom" && !customValidation.ok && !customDesde.trim())
                  }
                  helperText={desdeFieldError}
                  slotProps={{ inputLabel: { shrink: true } }}
                  inputProps={{ min: minDate, max: maxDate }}
                  fullWidth
                />
                <AppTextField
                  appearance="glass"
                  label="Hasta"
                  type="date"
                  value={customHasta}
                  onChange={(e) => {
                    handleUserChange();
                    setCustomHasta(e.target.value);
                  }}
                  disabled={loading}
                  error={
                    Boolean(hastaFieldError) ||
                    (periodMode === "custom" && !customValidation.ok && !customHasta.trim())
                  }
                  helperText={hastaFieldError}
                  slotProps={{ inputLabel: { shrink: true } }}
                  inputProps={{ min: minDate, max: maxDate }}
                  fullWidth
                />
              </Box>
            ) : null}
            {periodMode === "custom" && customDesde.trim() && customHasta.trim() && customValidation.ok ? (
              <Typography
                variant="body2"
                sx={{
                  mt: 1,
                  ml: { xs: 0, sm: 2 },
                  color: GLASS_COLORS.textPrimary,
                  fontFamily: '"Tactic Sans", sans-serif',
                  fontWeight: 600,
                  fontSize: "0.9rem",
                }}
              >
                Del {formatExportDatePreview(customDesde)} al {formatExportDatePreview(customHasta)}
              </Typography>
            ) : null}
          </FormControl>
        ) : null}

        <FormControl component="fieldset" disabled={loading || enabledFormats.length === 0}>
          <FormLabel component="legend" sx={sectionLabelSx}>
            Formato
          </FormLabel>
          <RadioGroup value={format} onChange={(_, value) => handleFormatChange(value as ExportFormat)}>
            {formats.map((f) => {
              const disabledReason = disabledFormats?.[f];
              const label = (
                <Box component="span" sx={{ display: "inline-flex", alignItems: "center" }}>
                  <FormatIcon format={f} />
                  {formatLabel[f]}
                </Box>
              );
              const control = (
                <FormControlLabel
                  key={f}
                  value={f}
                  disabled={Boolean(disabledReason)}
                  control={<Radio size="small" sx={radioSx} />}
                  label={label}
                  sx={radioLabelSx}
                />
              );
              if (disabledReason) {
                return (
                  <Tooltip key={f} title={disabledReason} placement="right">
                    <span>{control}</span>
                  </Tooltip>
                );
              }
              return control;
            })}
          </RadioGroup>
        </FormControl>

        {displayError ? (
          <Alert severity="error" onClose={() => { setLocalError(null); onClearError?.(); }}>
            {displayError}
          </Alert>
        ) : null}
      </Box>
    </AppDialog>
  );
}
