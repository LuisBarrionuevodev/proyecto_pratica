import { useEffect, useState } from "react";
import { Alert, Box, Stack, Typography } from "@mui/material";
import { isAxiosError } from "axios";

import {
  aplicarVinculacionEstablecimiento,
  previewVinculacionEstablecimiento,
  type IEstablecimientoOperativoDetail,
  type IVinculacionContribuyentePublico,
  type IVinculacionEstablecimientoPreview,
} from "../../../api/establecimientosOperativosApi";
import { dialogFormActionsRowSx } from "../../../styles/formDialogStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import { AppButton, AppDialog, AppTextField, ConfirmDialog } from "../../../ui";
import {
  VINCULACION_ACCION,
  VINCULACION_ASOCIAR,
  VINCULACION_BUSCAR_HINT,
  VINCULACION_HINT,
  VINCULACION_REGISTRADO_TITULO,
  VINCULACION_VOLVER,
} from "../utils/correccionEstablecimientoCopy";
import { VinculacionConfirmacionContent } from "./VinculacionConfirmacionContent";

type Props = {
  open: boolean;
  establecimientoId: number;
  detalle: IEstablecimientoOperativoDetail;
  documentoInicial?: string;
  onClose: () => void;
  onApplied: (preview: IVinculacionEstablecimientoPreview) => void;
};

function apiErrorMessage(e: unknown): string {
  if (isAxiosError(e) && e.response?.data && typeof e.response.data === "object") {
    const data = e.response.data as { detail?: string };
    if (data.detail) return String(data.detail);
  }
  return "No se pudo completar la operación.";
}

function dash(v: string | number | null | undefined): string {
  if (v == null) return "—";
  const t = String(v).trim();
  return t ? t : "—";
}

function titularTexto(c: IVinculacionContribuyentePublico | null | undefined): string {
  if (!c) return "—";
  const razon = dash(c.razon_social);
  if (razon !== "—") return razon;
  const persona = `${dash(c.apellido)} ${dash(c.nombre)}`.trim();
  return persona || "—";
}

/**
 * Canal de vinculación: busca un contribuyente existente por documento y reasigna la ficha.
 */
export function VinculacionEstablecimientoDialog({
  open,
  establecimientoId,
  detalle,
  documentoInicial = "",
  onClose,
  onApplied,
}: Props) {
  const [documento, setDocumento] = useState(documentoInicial);
  const [preview, setPreview] = useState<IVinculacionEstablecimientoPreview | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setDocumento(documentoInicial);
    setPreview(null);
    setConfirmOpen(false);
    setError(null);
  }, [open, documentoInicial]);

  const handleClose = () => {
    if (loadingPreview || loadingApply) return;
    setPreview(null);
    setConfirmOpen(false);
    setError(null);
    onClose();
  };

  const handlePreview = async () => {
    setError(null);
    setConfirmOpen(false);
    setLoadingPreview(true);
    try {
      const res = await previewVinculacionEstablecimiento(establecimientoId, {
        documento: documento.trim(),
      });
      setPreview(res);
      if (res.conflicto?.detail) {
        setError(res.conflicto.detail);
      }
    } catch (e) {
      setError(apiErrorMessage(e));
      setPreview(null);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleApply = async () => {
    if (!preview?.puede_aplicar || !preview.fingerprint) return;
    setError(null);
    setLoadingApply(true);
    try {
      const res = await aplicarVinculacionEstablecimiento(establecimientoId, {
        documento: documento.trim(),
        fingerprint: preview.fingerprint,
      });
      setPreview(null);
      setConfirmOpen(false);
      onApplied(res);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoadingApply(false);
    }
  };

  const matchListo = Boolean(preview?.puede_aplicar && preview.contribuyente_destino);
  const formOpen = open && !confirmOpen;

  return (
    <>
      <AppDialog
        open={formOpen}
        onClose={handleClose}
        title="Vincular a contribuyente existente"
        maxWidth="sm"
        fullWidth
        contentDividers
        actions={
          <Box sx={dialogFormActionsRowSx}>
            <AppButton dsVariant="ghost" onClick={handleClose} disabled={loadingPreview}>
              Cancelar
            </AppButton>
            {matchListo ? (
              <AppButton
                dsVariant="primary"
                onClick={() => setConfirmOpen(true)}
                disabled={loadingPreview}
              >
                {VINCULACION_ACCION}
              </AppButton>
            ) : (
              <AppButton dsVariant="primary" onClick={() => void handlePreview()} loading={loadingPreview}>
                Buscar contribuyente
              </AppButton>
            )}
          </Box>
        }
      >
        <Stack spacing={2}>
          <Typography sx={{ fontSize: "13px", color: GLASS_COLORS.textSecondary, fontFamily: FONT_FAMILY_UI }}>
            {VINCULACION_BUSCAR_HINT}
          </Typography>
          <Typography sx={{ fontSize: "13px", color: GLASS_COLORS.textSecondary, fontFamily: FONT_FAMILY_UI }}>
            {VINCULACION_HINT}
          </Typography>
          {error ? <Alert severity="warning">{error}</Alert> : null}
          <AppTextField
            appearance="glass"
            label="CUIT / DNI correcto"
            value={documento}
            onChange={(e) => {
              setDocumento(e.target.value);
              setPreview(null);
              setError(null);
            }}
            inputProps={{ maxLength: 11 }}
            fullWidth
          />
          <Typography sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI }}>
            Ficha actual: {dash(detalle.domicilio_texto)} — {dash(detalle.documento)}
          </Typography>
          {matchListo && preview?.contribuyente_destino ? (
            <Alert severity="info">
              Encontrado: {dash(preview.contribuyente_destino.documento)} —{" "}
              {titularTexto(preview.contribuyente_destino)}. Esta operación cambia el vínculo de la
              ficha, no los datos personales de esa persona.
            </Alert>
          ) : null}
        </Stack>
      </AppDialog>

      <ConfirmDialog
        open={open && confirmOpen && preview != null}
        onClose={() => {
          if (loadingApply) return;
          setConfirmOpen(false);
        }}
        onConfirm={() => void handleApply()}
        title={VINCULACION_REGISTRADO_TITULO}
        cancelLabel={VINCULACION_VOLVER}
        confirmLabel={VINCULACION_ASOCIAR}
        confirmDisabled={!preview?.puede_aplicar || Boolean(preview?.conflicto) || !preview?.fingerprint}
        loading={loadingApply}
        maxWidth="sm"
      >
        {preview ? <VinculacionConfirmacionContent preview={preview} error={error} /> : null}
      </ConfirmDialog>
    </>
  );
}
