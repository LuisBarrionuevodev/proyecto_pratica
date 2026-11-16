import { useEffect, useState, type MouseEvent } from "react";
import { Alert, Box, Stack, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { isAxiosError } from "axios";

import {
  aplicarVinculacionEstablecimiento,
  previewVinculacionEstablecimiento,
  type IEstablecimientoOperativoDetail,
  type IVinculacionAltaIn,
  type IVinculacionContribuyentePublico,
  type IVinculacionEstablecimientoPreview,
} from "../../../api/establecimientosOperativosApi";
import { dialogFormActionsRowSx } from "../../../styles/formDialogStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import { CSS_VAR_NAMES as V } from "../../../theme/applyCssVariables";
import { AppButton, AppDialog, AppTextField, ConfirmDialog } from "../../../ui";
import {
  CORRECCION_CONTRIBUYENTE_FICHA_ACCION,
  CORRECCION_CONTRIBUYENTE_FICHA_HINT,
  VINCULACION_ACCION,
  VINCULACION_ALTA_CONFIRMAR,
  VINCULACION_ASOCIAR,
  VINCULACION_BUSCAR_HINT,
  VINCULACION_CARGAR,
  VINCULACION_HINT,
  VINCULACION_NO_ENCONTRADO_DETALLE,
  VINCULACION_NO_ENCONTRADO_TITULO,
  VINCULACION_REGISTRADO_TITULO,
  VINCULACION_SIN_ALTA_HINT,
  VINCULACION_VOLVER,
  type TitularCorreccionModo,
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

type Paso = "buscar" | "alta";

const modalToggleGroupSx = {
  "& .MuiToggleButton-root": {
    flex: 1,
    textTransform: "none" as const,
    fontFamily: FONT_FAMILY_UI,
    fontSize: "0.8125rem",
    color: GLASS_COLORS.textSecondary,
    borderColor: GLASS_COLORS.borderMedium,
  },
  "& .Mui-selected": {
    bgcolor: `var(${V.actionSelected}) !important`,
    color: `${GLASS_COLORS.textPrimary} !important`,
  },
} as const;

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

function puedeCrearDesdePreview(preview: IVinculacionEstablecimientoPreview | null): boolean {
  if (!preview) return false;
  return preview.conflicto?.codigo === "SIN_DESTINO" && preview.conflicto.puede_crear === true;
}

/**
 * Canal de vinculación de esta ficha: asocia un contribuyente existente o crea uno y lo vincula.
 *
 * Qué hace: búsqueda, alta opcional, preview y confirmación. Persistencia solo al confirmar.
 * Parámetros: ficha abierta, detalle visible y callbacks de cierre/aplicación.
 * Retorno: diálogos de búsqueda, alta y confirmación.
 * Errores: SIN_DESTINO (ofrece alta), DOCUMENTO_AMBIGUO, PREVIEW_STALE y restantes conflictos se muestran sin persistir.
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
  const [paso, setPaso] = useState<Paso>("buscar");
  const [titularModo, setTitularModo] = useState<TitularCorreccionModo>("persona");
  const [apellido, setApellido] = useState("");
  const [nombre, setNombre] = useState("");
  const [razonSocial, setRazonSocial] = useState("");
  const [preview, setPreview] = useState<IVinculacionEstablecimientoPreview | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setDocumento(documentoInicial);
    setPaso("buscar");
    setTitularModo("persona");
    setApellido("");
    setNombre("");
    setRazonSocial("");
    setPreview(null);
    setConfirmOpen(false);
    setError(null);
  }, [open, documentoInicial]);

  const altaPayload = (): IVinculacionAltaIn | undefined => {
    if (titularModo === "razon_social") {
      return { razon_social: razonSocial.trim() || null };
    }
    return {
      apellido: apellido.trim() || null,
      nombre: nombre.trim() || null,
    };
  };

  const altaLista =
    titularModo === "razon_social"
      ? Boolean(razonSocial.trim())
      : Boolean(apellido.trim() && nombre.trim());

  const handleClose = () => {
    if (loadingPreview || loadingApply) return;
    setPreview(null);
    setConfirmOpen(false);
    setError(null);
    onClose();
  };

  const handlePreview = async (conAlta: boolean) => {
    setError(null);
    setConfirmOpen(false);
    setLoadingPreview(true);
    try {
      const res = await previewVinculacionEstablecimiento(establecimientoId, {
        documento: documento.trim(),
        alta: conAlta ? altaPayload() : undefined,
      });
      setPreview(res);
      if (res.puede_aplicar && res.fingerprint && !res.conflicto) {
        setConfirmOpen(true);
        return;
      }
      if (res.conflicto?.detail && res.conflicto.codigo !== "SIN_DESTINO") {
        setError(res.conflicto.detail);
      }
    } catch (e) {
      setError(apiErrorMessage(e));
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
        alta: preview.crea_contribuyente ? altaPayload() : undefined,
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

  const matchListo = Boolean(preview?.puede_aplicar && preview.contribuyente_destino && !preview.crea_contribuyente);
  const ofreceAlta = puedeCrearDesdePreview(preview);
  const formOpen = open && !confirmOpen;

  const handleTitularModo = (_: MouseEvent<HTMLElement>, next: TitularCorreccionModo | null) => {
    if (!next) return;
    setTitularModo(next);
  };

  return (
    <>
      <AppDialog
        open={formOpen}
        onClose={handleClose}
        title={paso === "alta" ? VINCULACION_CARGAR : CORRECCION_CONTRIBUYENTE_FICHA_ACCION}
        maxWidth="sm"
        fullWidth
        contentDividers
        actions={
          <Box sx={dialogFormActionsRowSx}>
            {paso === "alta" ? (
              <>
                <AppButton
                  dsVariant="ghost"
                  onClick={() => {
                    setPaso("buscar");
                    setConfirmOpen(false);
                    setError(null);
                  }}
                  disabled={loadingPreview}
                >
                  {VINCULACION_VOLVER}
                </AppButton>
                <AppButton
                  dsVariant="primary"
                  onClick={() => void handlePreview(true)}
                  loading={loadingPreview}
                  disabled={!altaLista}
                >
                  Ver alcance
                </AppButton>
              </>
            ) : ofreceAlta ? (
              <>
                <AppButton
                  dsVariant="ghost"
                  onClick={() => {
                    setPreview(null);
                    setError(null);
                  }}
                  disabled={loadingPreview}
                >
                  {VINCULACION_VOLVER}
                </AppButton>
                <AppButton dsVariant="primary" onClick={() => setPaso("alta")} disabled={loadingPreview}>
                  {VINCULACION_CARGAR}
                </AppButton>
              </>
            ) : (
              <>
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
                  <AppButton dsVariant="primary" onClick={() => void handlePreview(false)} loading={loadingPreview}>
                    Buscar contribuyente
                  </AppButton>
                )}
              </>
            )}
          </Box>
        }
      >
        <Stack spacing={2}>
          <Typography sx={{ fontSize: "13px", color: GLASS_COLORS.textSecondary, fontFamily: FONT_FAMILY_UI }}>
            {CORRECCION_CONTRIBUYENTE_FICHA_HINT}
          </Typography>
          <Typography sx={{ fontSize: "13px", color: GLASS_COLORS.textSecondary, fontFamily: FONT_FAMILY_UI }}>
            {paso === "alta" ? VINCULACION_SIN_ALTA_HINT : VINCULACION_BUSCAR_HINT}
          </Typography>
          {paso === "buscar" ? (
            <Typography sx={{ fontSize: "13px", color: GLASS_COLORS.textSecondary, fontFamily: FONT_FAMILY_UI }}>
              {VINCULACION_HINT}
            </Typography>
          ) : null}
          {error ? <Alert severity="warning">{error}</Alert> : null}
          {ofreceAlta && paso === "buscar" ? (
            <Alert severity="info">
              <strong>{VINCULACION_NO_ENCONTRADO_TITULO}</strong>
              <br />
              {VINCULACION_NO_ENCONTRADO_DETALLE}
            </Alert>
          ) : null}
          <AppTextField
            appearance="glass"
            label="CUIT / DNI correcto"
            value={documento}
            onChange={(e) => {
              setDocumento(e.target.value);
              setPreview(null);
              setError(null);
              setPaso("buscar");
            }}
            inputProps={{ maxLength: 11 }}
            fullWidth
          />
          {paso === "alta" ? (
            <>
              <ToggleButtonGroup
                exclusive
                value={titularModo}
                onChange={handleTitularModo}
                size="small"
                fullWidth
                sx={modalToggleGroupSx}
              >
                <ToggleButton value="persona">Contribuyente</ToggleButton>
                <ToggleButton value="razon_social">Razón social</ToggleButton>
              </ToggleButtonGroup>
              {titularModo === "persona" ? (
                <>
                  <AppTextField
                    appearance="glass"
                    label="Apellido"
                    value={apellido}
                    onChange={(e) => setApellido(e.target.value)}
                    fullWidth
                  />
                  <AppTextField
                    appearance="glass"
                    label="Nombre"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    fullWidth
                  />
                </>
              ) : (
                <AppTextField
                  appearance="glass"
                  label="Razón social"
                  value={razonSocial}
                  onChange={(e) => setRazonSocial(e.target.value)}
                  fullWidth
                />
              )}
            </>
          ) : null}
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
        title={preview?.crea_contribuyente ? VINCULACION_CARGAR : VINCULACION_REGISTRADO_TITULO}
        cancelLabel={VINCULACION_VOLVER}
        confirmLabel={preview?.crea_contribuyente ? VINCULACION_ALTA_CONFIRMAR : VINCULACION_ASOCIAR}
        confirmDisabled={!preview?.puede_aplicar || Boolean(preview?.conflicto) || !preview?.fingerprint}
        loading={loadingApply}
        maxWidth="sm"
      >
        {preview ? <VinculacionConfirmacionContent preview={preview} error={error} /> : null}
      </ConfirmDialog>
    </>
  );
}
