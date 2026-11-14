import { useMemo, useState } from "react";
import { Alert, Box, Stack, Typography } from "@mui/material";
import { isAxiosError } from "axios";

import {
  AppButton,
  AppDialog,
  AppSelect,
  AppTextField,
  ConfirmDialog,
} from "../../../ui";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { dialogFormActionsRowSx } from "../../../styles/formDialogStyles";
import {
  aplicarCorreccionEstablecimiento,
  previewCorreccionEstablecimiento,
  type ICorreccionEstablecimientoPayload,
  type ICorreccionEstablecimientoPreview,
  type IEstablecimientoOperativoDetail,
} from "../../../api/establecimientosOperativosApi";

export type CorreccionEstablecimientoKind = "contribuyente" | "domicilio";

type Props = {
  open: boolean;
  kind: CorreccionEstablecimientoKind;
  establecimientoId: number;
  detalle: IEstablecimientoOperativoDetail;
  onClose: () => void;
  onApplied: () => void;
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

function ConteoLine({ label, cantidad }: { label: string; cantidad?: number }) {
  return (
    <Typography sx={{ fontSize: "13px", color: GLASS_COLORS.textPrimary, fontFamily: FONT_FAMILY_UI }}>
      {label}: <strong>{cantidad ?? 0}</strong>
    </Typography>
  );
}

/**
 * Canal controlado: corrige contribuyente o domicilio de la ficha con preview y confirmación.
 */
export function CorreccionEstablecimientoDialog({
  open,
  kind,
  establecimientoId,
  detalle,
  onClose,
  onApplied,
}: Props) {
  const [documento, setDocumento] = useState(detalle.documento ?? "");
  const [apellido, setApellido] = useState(detalle.contrib_apellido ?? "");
  const [nombre, setNombre] = useState(detalle.contrib_nombre ?? "");
  const [razonSocial, setRazonSocial] = useState(detalle.razon_social ?? "");
  const [calle, setCalle] = useState(detalle.calle ?? "");
  const [numero, setNumero] = useState(detalle.numero ?? "");
  const [numeroTipo, setNumeroTipo] = useState(detalle.numero_tipo ?? "NUMERO");
  const [esquina, setEsquina] = useState(detalle.esquina_raw ?? "");

  const [preview, setPreview] = useState<ICorreccionEstablecimientoPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const title = kind === "contribuyente" ? "Corregir contribuyente" : "Corregir domicilio";

  const payload = useMemo((): ICorreccionEstablecimientoPayload => {
    if (kind === "contribuyente") {
      return {
        contribuyente: {
          documento: documento.trim() || null,
          apellido: apellido.trim() || null,
          nombre: nombre.trim() || null,
          razon_social: razonSocial.trim() || null,
        },
      };
    }
    const nt = (numeroTipo || "NUMERO").toUpperCase();
    return {
      domicilio: {
        calle: calle.trim() || null,
        numero: numero.trim() || null,
        numero_tipo: nt === "ESQUINA" || nt === "OTRO" || nt === "NUMERO" ? nt : "NUMERO",
        esquina: nt === "ESQUINA" ? esquina.trim() || numero.trim() || null : null,
      },
    };
  }, [kind, documento, apellido, nombre, razonSocial, calle, numero, numeroTipo, esquina]);

  const handleClose = () => {
    if (loadingPreview || loadingApply) return;
    setPreview(null);
    setError(null);
    onClose();
  };

  const handlePreview = async () => {
    setError(null);
    setLoadingPreview(true);
    try {
      const res = await previewCorreccionEstablecimiento(establecimientoId, payload);
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
    if (!preview?.puede_aplicar) return;
    setError(null);
    setLoadingApply(true);
    try {
      await aplicarCorreccionEstablecimiento(establecimientoId, payload);
      setPreview(null);
      onApplied();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoadingApply(false);
    }
  };

  return (
    <>
      <AppDialog
        open={open && preview == null}
        onClose={handleClose}
        title={title}
        maxWidth="sm"
        fullWidth
        contentDividers
        actions={
          <Box sx={dialogFormActionsRowSx}>
            <AppButton dsVariant="ghost" onClick={handleClose} disabled={loadingPreview}>
              Cancelar
            </AppButton>
            <AppButton dsVariant="primary" onClick={() => void handlePreview()} loading={loadingPreview}>
              Ver alcance
            </AppButton>
          </Box>
        }
      >
        <Stack spacing={2}>
          <Typography sx={{ fontSize: "13px", color: GLASS_COLORS.textSecondary, fontFamily: FONT_FAMILY_UI }}>
            {kind === "contribuyente"
              ? "Corrige datos del mismo contribuyente. No cambia el titular ni fusiona registros."
              : "Corrige la dirección de origen de este establecimiento. No se recalculan coordenadas ni distrito."}
          </Typography>
          {error ? <Alert severity="warning">{error}</Alert> : null}
          {kind === "contribuyente" ? (
            <>
              <AppTextField
                appearance="glass"
                label="CUIT / documento"
                value={documento}
                onChange={(e) => setDocumento(e.target.value)}
                inputProps={{ maxLength: 11 }}
                fullWidth
              />
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
              <AppTextField
                appearance="glass"
                label="Razón social"
                value={razonSocial}
                onChange={(e) => setRazonSocial(e.target.value)}
                fullWidth
              />
            </>
          ) : (
            <>
              <AppTextField
                appearance="glass"
                label="Calle"
                value={calle}
                onChange={(e) => setCalle(e.target.value)}
                fullWidth
              />
              <AppTextField
                appearance="glass"
                label="Número / altura"
                value={numero}
                onChange={(e) => setNumero(e.target.value)}
                fullWidth
              />
              <AppSelect
                appearance="glass"
                label="Tipo de numeración"
                value={numeroTipo || "NUMERO"}
                onChange={(e) => setNumeroTipo(String(e.target.value))}
                options={[
                  { value: "NUMERO", label: "Número" },
                  { value: "ESQUINA", label: "Esquina" },
                  { value: "OTRO", label: "Otro" },
                ]}
                fullWidth
              />
              {numeroTipo === "ESQUINA" ? (
                <AppTextField
                  appearance="glass"
                  label="Intersección / esquina"
                  value={esquina}
                  onChange={(e) => setEsquina(e.target.value)}
                  fullWidth
                />
              ) : null}
            </>
          )}
        </Stack>
      </AppDialog>

      <ConfirmDialog
        open={open && preview != null}
        onClose={() => {
          if (loadingApply) return;
          setPreview(null);
        }}
        onConfirm={() => void handleApply()}
        title="Confirmar corrección"
        confirmLabel="Guardar corrección"
        confirmDisabled={!preview?.puede_aplicar || Boolean(preview?.conflicto)}
        loading={loadingApply}
        maxWidth="sm"
      >
        <Stack spacing={1.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}
          {preview?.sin_cambios ? (
            <Alert severity="info">No hay cambios. No se desvincula el contribuyente ni se modifica ningún dato.</Alert>
          ) : null}
          {preview?.conflicto?.detail ? <Alert severity="warning">{preview.conflicto.detail}</Alert> : null}

          {preview?.contribuyente ? (
            <Box>
              <Typography sx={{ fontWeight: 700, fontSize: "12px", letterSpacing: "0.08em", mb: 0.75 }}>
                CONTRIBUYENTE
              </Typography>
              <Typography sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI }}>
                Actual: {dash(preview.contribuyente.actual?.documento as string)} —{" "}
                {dash(preview.contribuyente.actual?.razon_social as string) !== "—"
                  ? dash(preview.contribuyente.actual?.razon_social as string)
                  : `${dash(preview.contribuyente.actual?.apellido as string)} ${dash(preview.contribuyente.actual?.nombre as string)}`}
              </Typography>
              <Typography sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI }}>
                Propuesto: {dash(preview.contribuyente.propuesto?.documento as string)} —{" "}
                {dash(preview.contribuyente.propuesto?.razon_social as string) !== "—"
                  ? dash(preview.contribuyente.propuesto?.razon_social as string)
                  : `${dash(preview.contribuyente.propuesto?.apellido as string)} ${dash(preview.contribuyente.propuesto?.nombre as string)}`}
              </Typography>
              <ConteoLine
                label="Establecimientos vinculados"
                cantidad={preview.contribuyente.establecimientos_afectados.cantidad}
              />
              <ConteoLine
                label="Actuaciones vinculadas"
                cantidad={preview.contribuyente.actuaciones_afectadas.cantidad}
              />
              <Alert severity="info" sx={{ mt: 1 }}>
                {preview.contribuyente.advertencia}
              </Alert>
            </Box>
          ) : null}

          {preview?.domicilio ? (
            <Box>
              <Typography sx={{ fontWeight: 700, fontSize: "12px", letterSpacing: "0.08em", mb: 0.75 }}>
                DOMICILIO
              </Typography>
              <Typography sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI }}>
                Actual: {dash(preview.domicilio.actual_texto)}
              </Typography>
              <Typography sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI }}>
                Propuesto: {dash(preview.domicilio.propuesto?.calle as string)}{" "}
                {dash(preview.domicilio.propuesto?.numero as string)}
              </Typography>
              <ConteoLine label="Establecimiento seleccionado" cantidad={1} />
              <ConteoLine label="Actuaciones" cantidad={preview.domicilio.actuaciones.cantidad} />
              <ConteoLine label="Notificaciones" cantidad={preview.domicilio.notificaciones.cantidad} />
              <ConteoLine label="Comprobaciones" cantidad={preview.domicilio.comprobaciones.cantidad} />
              <ConteoLine label="Oficios" cantidad={preview.domicilio.oficios.cantidad} />
              <ConteoLine label="Iniciadores" cantidad={preview.domicilio.iniciadores.cantidad} />
              <ConteoLine label="Ítems de ruta" cantidad={preview.domicilio.ruta_items.cantidad} />
              <Alert severity="warning" sx={{ mt: 1 }}>
                {preview.domicilio.advertencia}
              </Alert>
            </Box>
          ) : null}

          {preview?.snapshots_y_pdf ? (
            <Typography sx={{ fontSize: "12px", color: GLASS_COLORS.textSecondary, fontFamily: FONT_FAMILY_UI }}>
              {preview.snapshots_y_pdf.detalle}
            </Typography>
          ) : null}
        </Stack>
      </ConfirmDialog>
    </>
  );
}
