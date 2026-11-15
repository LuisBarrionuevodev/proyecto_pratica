import { useId, useState } from "react";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Alert, Box, Collapse, Stack, Typography } from "@mui/material";

import type { IVinculacionEstablecimientoPreview } from "../../../api/establecimientosOperativosApi";
import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import { AppButton } from "../../../ui";
import {
  VINCULACION_ANTECEDENTES_JUNTOS,
  VINCULACION_DETALLE_ALCANCE,
  VINCULACION_DOCUMENTOS_CONSERVAN,
  VINCULACION_HISTORIAL_TITULO,
  VINCULACION_OCULTAR_DETALLE,
  VINCULACION_OTROS_NO_CAMBIAN,
  mensajeConflictoVinculacionInseguro,
  preguntaAsociarEstablecimiento,
  resumenHistorialAsociar,
  titularVinculacionTexto,
} from "../utils/correccionEstablecimientoCopy";

type Props = {
  preview: IVinculacionEstablecimientoPreview;
  error?: string | null;
};

const wrapSx = {
  overflowWrap: "anywhere" as const,
  wordBreak: "break-word" as const,
};

const labelSx = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "10px",
  fontWeight: 700,
  letterSpacing: "0.1em",
  textTransform: "uppercase" as const,
  color: GLASS_COLORS.textMuted,
};

const nameSx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  fontSize: "16px",
  color: GLASS_COLORS.textPrimary,
  lineHeight: 1.3,
  ...wrapSx,
};

const addressSx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  fontSize: "15px",
  color: GLASS_COLORS.textPrimary,
  lineHeight: 1.35,
  ...wrapSx,
};

const lineSx = {
  fontSize: "13px",
  color: GLASS_COLORS.textPrimary,
  fontFamily: FONT_FAMILY_UI,
  ...wrapSx,
};

const mutedSx = {
  fontSize: "12px",
  color: GLASS_COLORS.textSecondary,
  fontFamily: FONT_FAMILY_UI,
  ...wrapSx,
};

function DetalleCelda({ label, cantidad }: { label: string; cantidad?: number }) {
  if (typeof cantidad !== "number") return null;
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography sx={mutedSx}>{label}</Typography>
      <Typography sx={{ ...lineSx, fontWeight: 700 }}>{cantidad}</Typography>
    </Box>
  );
}

/**
 * Confirmación amigable de vinculación: jerarquía visual, historial compacto y detalle colapsable.
 *
 * No calcula alcance ni aplica cambios. No inventa nombre ni cantidades ausentes.
 */
export function VinculacionConfirmacionContent({ preview, error }: Props) {
  const [detalleOpen, setDetalleOpen] = useState(false);
  const detalleId = useId();
  const dest = preview.contribuyente_destino;
  const nombre = titularVinculacionTexto(dest);
  const documento = dest?.documento?.trim() ?? "";
  const domicilio = preview.establecimiento?.domicilio_texto?.trim() ?? "";
  const historialPartes = resumenHistorialAsociar({
    actuaciones: preview.alcance?.actuaciones?.cantidad,
    notificaciones: preview.alcance?.notificaciones?.cantidad,
    comprobaciones: preview.alcance?.comprobaciones?.cantidad,
  });
  const puedeAsociar = Boolean(preview.puede_aplicar && dest && !preview.conflicto);
  const conflictoMsg =
    error ??
    (preview.conflicto
      ? mensajeConflictoVinculacionInseguro(preview.conflicto.detail)
      : null);

  return (
    <Stack spacing={1.75}>
      {conflictoMsg ? <Alert severity="warning">{conflictoMsg}</Alert> : null}

      {puedeAsociar ? (
        <>
          <Box>
            <Typography sx={{ ...labelSx, mb: 0.5 }}>Contribuyente encontrado</Typography>
            {nombre ? <Typography sx={nameSx}>{nombre}</Typography> : null}
            {documento ? (
              <Typography sx={{ ...mutedSx, mt: nombre ? 0.35 : 0 }}>CUIT/DNI: {documento}</Typography>
            ) : null}
          </Box>

          <Typography sx={{ ...lineSx, fontSize: "14px" }}>
            {preguntaAsociarEstablecimiento(nombre)}
          </Typography>

          {domicilio ? (
            <Box>
              <Typography sx={{ ...labelSx, mb: 0.5 }}>Establecimiento</Typography>
              <Typography sx={addressSx}>{domicilio}</Typography>
            </Box>
          ) : null}

          {historialPartes.length > 0 ? (
            <Box>
              <Typography sx={{ ...labelSx, mb: 0.5 }}>{VINCULACION_HISTORIAL_TITULO}</Typography>
              <Typography sx={lineSx}>{historialPartes.join(" · ")}</Typography>
            </Box>
          ) : null}
        </>
      ) : null}

      <Box>
        <AppButton
          dsVariant="ghost"
          dsSize="sm"
          type="button"
          aria-expanded={detalleOpen}
          aria-controls={detalleId}
          onClick={() => setDetalleOpen((open) => !open)}
          endIcon={
            <ExpandMoreIcon
              fontSize="small"
              sx={{
                transform: detalleOpen ? "rotate(180deg)" : "none",
                transition: "transform 0.2s ease",
              }}
            />
          }
          sx={{
            color: COLORS.primary,
            justifyContent: "flex-start",
            alignSelf: "flex-start",
            px: 0.5,
            ml: -0.5,
            minHeight: 36,
            fontWeight: 600,
            textTransform: "none",
            "&:hover": {
              backgroundColor: "rgba(1, 102, 255, 0.08)",
              color: COLORS.primary,
            },
          }}
        >
          {detalleOpen ? VINCULACION_OCULTAR_DETALLE : VINCULACION_DETALLE_ALCANCE}
        </AppButton>
        <Collapse in={detalleOpen} id={detalleId}>
          <Box
            sx={{
              mt: 1,
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "minmax(0, 1fr) minmax(0, 1fr)" },
              columnGap: 2,
              rowGap: 1.25,
            }}
          >
            <DetalleCelda label="Actuaciones" cantidad={preview.alcance?.actuaciones?.cantidad} />
            <DetalleCelda label="Notificaciones" cantidad={preview.alcance?.notificaciones?.cantidad} />
            <DetalleCelda label="Comprobaciones" cantidad={preview.alcance?.comprobaciones?.cantidad} />
            <DetalleCelda label="Oficios" cantidad={preview.alcance?.oficios?.cantidad} />
            <DetalleCelda
              label="Tareas de inspección pendientes"
              cantidad={preview.alcance?.iniciadores?.cantidad}
            />
            <DetalleCelda
              label="Visitas en recorridos"
              cantidad={preview.alcance?.ruta_items?.cantidad}
            />
            <DetalleCelda
              label="Otros establecimientos del contribuyente anterior"
              cantidad={preview.otros_locales_contribuyente_anterior?.cantidad}
            />
            <DetalleCelda
              label="Otros establecimientos del contribuyente encontrado"
              cantidad={preview.otros_locales_contribuyente_destino?.cantidad}
            />
          </Box>
        </Collapse>
      </Box>

      {puedeAsociar ? (
        <Stack spacing={0.75}>
          <Typography sx={mutedSx}>{VINCULACION_OTROS_NO_CAMBIAN}</Typography>
          {preview.ficha_logica_destino?.existe ? (
            <Alert severity="info">{VINCULACION_ANTECEDENTES_JUNTOS}</Alert>
          ) : null}
          <Typography sx={mutedSx}>{VINCULACION_DOCUMENTOS_CONSERVAN}</Typography>
        </Stack>
      ) : null}
    </Stack>
  );
}
