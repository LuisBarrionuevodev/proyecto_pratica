import type { ReactNode } from "react";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import LocationOnOutlinedIcon from "@mui/icons-material/LocationOnOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import StorefrontOutlinedIcon from "@mui/icons-material/StorefrontOutlined";
import SwapHorizOutlinedIcon from "@mui/icons-material/SwapHorizOutlined";
import { Box, Paper, Stack, Typography } from "@mui/material";

import type { IEstablecimientoOperativoDetail } from "../../../api/establecimientosOperativosApi";
import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";
import { glassCard, GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import { AppButton } from "../../../ui";
import { establecimientoDomicilioLineaVisible } from "../utils/establecimientoDomicilioVisible";
import {
  CORRECCION_CONTRIBUYENTE_FICHA_ACCION,
  CORRECCION_CONTRIBUYENTE_FICHA_HINT,
  CORRECCION_DATOS_CONTRIBUYENTE_ACCION,
} from "../utils/correccionEstablecimientoCopy";
import {
  establecimientoFichaContribuyenteNombre,
  establecimientoFichaDocumentoVisible,
  establecimientoFichaNombreLocalEsPlaceholder,
  establecimientoFichaNombreLocalVisible,
  establecimientoFichaRubroVisible,
} from "../utils/establecimientoFichaDisplay";
import type { CorreccionEstablecimientoKind } from "./CorreccionEstablecimientoDialog";

type Props = {
  detalle: IEstablecimientoOperativoDetail;
  canCorrect: boolean;
  onCorregir: (kind: CorreccionEstablecimientoKind) => void;
  onCorregirContribuyenteFicha: () => void;
};

const labelSx = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "10px",
  fontWeight: 700,
  letterSpacing: "0.1em",
  textTransform: "uppercase" as const,
  color: GLASS_COLORS.textMuted,
};

const primarySx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  fontSize: { xs: "16px", sm: "20px" },
  color: GLASS_COLORS.textPrimary,
  letterSpacing: "0.02em",
  lineHeight: 1.3,
  overflowWrap: "anywhere" as const,
  wordBreak: "break-word" as const,
};

const secondarySx = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "12px",
  fontWeight: 600,
  color: GLASS_COLORS.textSecondary,
  letterSpacing: "0.04em",
  lineHeight: 1.4,
  overflowWrap: "anywhere" as const,
  wordBreak: "break-word" as const,
};

const iconSx = { color: COLORS.primary, fontSize: 20, flexShrink: 0 };

const blockBaseSx = {
  minWidth: 0,
  p: { xs: 2, md: 2.5 },
  display: "flex",
  flexDirection: "column" as const,
  gap: 1,
};

const correctActionSx = {
  color: COLORS.primary,
  alignSelf: "flex-start",
  minHeight: 40,
  px: 1,
  mt: 0.5,
  fontWeight: 600,
  textTransform: "none" as const,
  "&:hover": {
    backgroundColor: "rgba(1, 102, 255, 0.08)",
    color: COLORS.primary,
  },
  "&.Mui-focusVisible": {
    outline: `2px solid ${COLORS.primary}`,
    outlineOffset: 2,
  },
};

const hintSx = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "11px",
  fontWeight: 500,
  color: GLASS_COLORS.textMuted,
  letterSpacing: "0.02em",
  lineHeight: 1.4,
  overflowWrap: "anywhere" as const,
};

function FichaBloque({
  icon,
  label,
  primary,
  primaryMuted,
  secondary,
  hideSecondary,
  actionLabel,
  extraActionLabel,
  extraActionHint,
  extraActionHintId,
  canCorrect,
  onCorrect,
  onExtraCorrect,
  showEndDivider,
}: {
  icon: ReactNode;
  label: string;
  primary: string;
  primaryMuted?: boolean;
  secondary: string;
  hideSecondary?: boolean;
  actionLabel: string;
  extraActionLabel?: string;
  extraActionHint?: string;
  extraActionHintId?: string;
  canCorrect: boolean;
  onCorrect: () => void;
  onExtraCorrect?: () => void;
  showEndDivider: boolean;
}) {
  return (
    <Box
      sx={{
        ...blockBaseSx,
        borderRight: {
          xs: "none",
          md: showEndDivider ? `1px solid ${GLASS_COLORS.borderLight}` : "none",
        },
        borderBottom: {
          xs: showEndDivider ? `1px solid ${GLASS_COLORS.borderLight}` : "none",
          md: "none",
        },
      }}
    >
      <Stack direction="row" spacing={0.75} alignItems="center">
        {icon}
        <Typography component="h2" sx={labelSx}>
          {label}
        </Typography>
      </Stack>
      <Typography
        sx={{
          ...primarySx,
          ...(primaryMuted
            ? {
                color: GLASS_COLORS.textSecondary,
                fontStyle: "italic",
                fontWeight: 600,
              }
            : null),
        }}
      >
        {primary}
      </Typography>
      {hideSecondary ? null : <Typography sx={secondarySx}>{secondary}</Typography>}
      {canCorrect ? (
        <Stack spacing={0.25} sx={{ mt: 0.5 }}>
          <AppButton
            dsVariant="ghost"
            dsSize="sm"
            startIcon={<EditOutlinedIcon sx={{ fontSize: 18 }} />}
            onClick={onCorrect}
            aria-label={actionLabel}
            sx={{ ...correctActionSx, mt: 0 }}
          >
            {actionLabel}
          </AppButton>
          {extraActionLabel && onExtraCorrect ? (
            <>
              <AppButton
                dsVariant="ghost"
                dsSize="sm"
                startIcon={<SwapHorizOutlinedIcon sx={{ fontSize: 18 }} />}
                onClick={onExtraCorrect}
                aria-label={extraActionLabel}
                aria-describedby={extraActionHint ? extraActionHintId : undefined}
                sx={{ ...correctActionSx, mt: 0 }}
              >
                {extraActionLabel}
              </AppButton>
              {extraActionHint ? (
                <Typography id={extraActionHintId} sx={hintSx}>
                  {extraActionHint}
                </Typography>
              ) : null}
            </>
          ) : null}
        </Stack>
      ) : null}
    </Box>
  );
}

/**
 * Tarjeta superior de Ver establecimiento: contribuyente, local y domicilio.
 *
 * Qué hace: presenta datos vigentes y dispara corrección global, vinculación de ficha o corrección de local/domicilio.
 * Parámetros: detalle, permiso, callback de kind y callback de vinculación de esta ficha.
 * Retorno: Paper con tres bloques (columnas en desktop, apilados en celular).
 */
export function EstablecimientoFichaHeader({
  detalle,
  canCorrect,
  onCorregir,
  onCorregirContribuyenteFicha,
}: Props) {
  const contribuyenteNombre = establecimientoFichaContribuyenteNombre(detalle);
  const documento = establecimientoFichaDocumentoVisible(detalle.documento);
  const nombreLocal = establecimientoFichaNombreLocalVisible(detalle.nombre_local);
  const nombreLocalPlaceholder = establecimientoFichaNombreLocalEsPlaceholder(detalle.nombre_local);
  const rubro = establecimientoFichaRubroVisible(detalle.rubro_nombre);
  const domicilioLinea = establecimientoDomicilioLineaVisible(detalle);
  const distrito = detalle.distrito_nombre?.trim() ?? "";

  return (
    <Paper elevation={0} sx={{ ...glassCard, overflow: "hidden", p: 0, width: "100%", maxWidth: "100%" }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)" },
          width: "100%",
          maxWidth: "100%",
        }}
      >
        <FichaBloque
          icon={<PersonOutlineIcon sx={iconSx} />}
          label="Contribuyente"
          primary={contribuyenteNombre}
          secondary={`DNI/CUIT: ${documento}`}
          actionLabel={CORRECCION_DATOS_CONTRIBUYENTE_ACCION}
          extraActionLabel={CORRECCION_CONTRIBUYENTE_FICHA_ACCION}
          extraActionHint={CORRECCION_CONTRIBUYENTE_FICHA_HINT}
          extraActionHintId="ficha-contribuyente-equivocado-hint"
          canCorrect={canCorrect}
          onCorrect={() => onCorregir("contribuyente")}
          onExtraCorrect={onCorregirContribuyenteFicha}
          showEndDivider
        />
        <FichaBloque
          icon={<StorefrontOutlinedIcon sx={iconSx} />}
          label="Establecimiento"
          primary={nombreLocal}
          primaryMuted={nombreLocalPlaceholder}
          secondary={`Rubro: ${rubro}`}
          actionLabel="Corregir datos del local"
          canCorrect={canCorrect}
          onCorrect={() => onCorregir("local")}
          showEndDivider
        />
        <FichaBloque
          icon={<LocationOnOutlinedIcon sx={iconSx} />}
          label="Domicilio"
          primary={domicilioLinea}
          secondary={`Distrito: ${distrito}`}
          hideSecondary={!distrito}
          actionLabel="Corregir domicilio"
          canCorrect={canCorrect}
          onCorrect={() => onCorregir("domicilio")}
          showEndDivider={false}
        />
      </Box>
    </Paper>
  );
}
