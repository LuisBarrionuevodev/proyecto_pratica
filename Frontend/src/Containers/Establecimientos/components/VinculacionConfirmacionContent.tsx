import { useState } from "react";
import { Alert, Box, Collapse, Stack, Typography } from "@mui/material";

import type { IVinculacionEstablecimientoPreview } from "../../../api/establecimientosOperativosApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import { AppButton } from "../../../ui";
import {
  VINCULACION_ANTECEDENTES_JUNTOS,
  VINCULACION_DETALLE_ALCANCE,
  VINCULACION_DOCUMENTOS_EMITIDOS,
  VINCULACION_OTROS_NO_CAMBIAN,
  VINCULACION_PREGUNTA_ASOCIAR,
  mensajeConflictoVinculacionInseguro,
  titularVinculacionTexto,
} from "../utils/correccionEstablecimientoCopy";

type Props = {
  preview: IVinculacionEstablecimientoPreview;
  error?: string | null;
};

const lineSx = {
  fontSize: "13px",
  color: GLASS_COLORS.textPrimary,
  fontFamily: FONT_FAMILY_UI,
} as const;

const mutedSx = {
  fontSize: "12px",
  color: GLASS_COLORS.textSecondary,
  fontFamily: FONT_FAMILY_UI,
} as const;

function ConteoLine({ label, cantidad }: { label: string; cantidad?: number }) {
  if (typeof cantidad !== "number") return null;
  return (
    <Typography sx={lineSx}>
      {label}: <strong>{cantidad}</strong>
    </Typography>
  );
}

/**
 * Confirmación amigable de vinculación: datos encontrados, alcance y detalle opcional.
 *
 * No muestra IDs ni términos técnicos de entrada. No inventa valores ausentes.
 */
export function VinculacionConfirmacionContent({ preview, error }: Props) {
  const [detalleOpen, setDetalleOpen] = useState(false);
  const dest = preview.contribuyente_destino;
  const nombre = titularVinculacionTexto(dest);
  const documento = dest?.documento?.trim() ?? "";
  const domicilio = preview.establecimiento?.domicilio_texto?.trim() ?? "";
  const historial = preview.alcance?.actuaciones?.cantidad;
  const puedeAsociar = Boolean(preview.puede_aplicar && dest && !preview.conflicto);
  const conflictoMsg =
    error ??
    (preview.conflicto
      ? mensajeConflictoVinculacionInseguro(preview.conflicto.detail)
      : null);

  return (
    <Stack spacing={1.5}>
      {conflictoMsg ? <Alert severity="warning">{conflictoMsg}</Alert> : null}

      {puedeAsociar ? (
        <>
          {nombre ? (
            <Typography sx={{ ...lineSx, fontWeight: 700, fontSize: "15px" }}>{nombre}</Typography>
          ) : null}
          {documento ? <Typography sx={lineSx}>CUIT/DNI: {documento}</Typography> : null}
          <Typography sx={lineSx}>{VINCULACION_PREGUNTA_ASOCIAR}</Typography>
          {domicilio ? (
            <Typography sx={lineSx}>
              <strong>Establecimiento:</strong> {domicilio}
            </Typography>
          ) : null}
          {typeof historial === "number" ? (
            <Typography sx={lineSx}>
              <strong>Historial:</strong> {historial} actuaciones
            </Typography>
          ) : null}
          <Typography sx={lineSx}>{VINCULACION_OTROS_NO_CAMBIAN}</Typography>
          {preview.ficha_logica_destino?.existe ? (
            <Alert severity="info">{VINCULACION_ANTECEDENTES_JUNTOS}</Alert>
          ) : null}
          <Typography sx={mutedSx}>{VINCULACION_DOCUMENTOS_EMITIDOS}</Typography>
        </>
      ) : null}

      <Box>
        <AppButton dsVariant="ghost" dsSize="sm" onClick={() => setDetalleOpen((open) => !open)}>
          {VINCULACION_DETALLE_ALCANCE}
        </AppButton>
        <Collapse in={detalleOpen}>
          <Stack spacing={0.5} sx={{ mt: 1 }}>
            <ConteoLine label="Actuaciones" cantidad={preview.alcance?.actuaciones?.cantidad} />
            <ConteoLine label="Notificaciones" cantidad={preview.alcance?.notificaciones?.cantidad} />
            <ConteoLine label="Comprobaciones" cantidad={preview.alcance?.comprobaciones?.cantidad} />
            <ConteoLine label="Oficios" cantidad={preview.alcance?.oficios?.cantidad} />
            <ConteoLine
              label="Tareas de inspección pendientes"
              cantidad={preview.alcance?.iniciadores?.cantidad}
            />
            <ConteoLine
              label="Visitas en recorridos"
              cantidad={preview.alcance?.ruta_items?.cantidad}
            />
            <ConteoLine
              label="Otros establecimientos del contribuyente anterior"
              cantidad={preview.otros_locales_contribuyente_anterior?.cantidad}
            />
            <ConteoLine
              label="Otros establecimientos del contribuyente encontrado"
              cantidad={preview.otros_locales_contribuyente_destino?.cantidad}
            />
          </Stack>
        </Collapse>
      </Box>
    </Stack>
  );
}
