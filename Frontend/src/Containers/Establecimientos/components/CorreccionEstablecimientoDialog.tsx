import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { Alert, Box, Stack, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
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
import { CSS_VAR_NAMES as V } from "../../../theme/applyCssVariables";
import {
  aplicarCorreccionEstablecimiento,
  previewCorreccionEstablecimiento,
  type ICorreccionEstablecimientoPayload,
  type ICorreccionEstablecimientoPreview,
  type IEstablecimientoOperativoDetail,
} from "../../../api/establecimientosOperativosApi";
import {
  fetchRubrosCatalogoCached,
  mergeLegacyRubroNames,
  rubroItemsToNombres,
} from "../../../utils/rubrosCatalogCache";
import {
  CORRECCION_CONTRIBUYENTE_HINT,
  CORRECCION_DOMICILIO_HINT,
  CORRECCION_LOCAL_HINT,
  CORRECCION_TITULAR_MODO_AMBOS_HINT,
  VINCULACION_ACCION,
  VINCULACION_DOCUMENTO_AJENO_CTA,
  inferTitularCorreccionModo,
  type TitularCorreccionModo,
} from "../utils/correccionEstablecimientoCopy";

export type CorreccionEstablecimientoKind = "contribuyente" | "domicilio" | "local";

type NumeroModo = "NUMERO" | "ESQUINA";

type Props = {
  open: boolean;
  kind: CorreccionEstablecimientoKind;
  establecimientoId: number;
  detalle: IEstablecimientoOperativoDetail;
  onClose: () => void;
  onApplied: () => void;
  onVincularDocumento?: (documento: string) => void;
};

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

function ConteoLine({ label, cantidad }: { label: string; cantidad?: number }) {
  return (
    <Typography sx={{ fontSize: "13px", color: GLASS_COLORS.textPrimary, fontFamily: FONT_FAMILY_UI }}>
      {label}: <strong>{cantidad ?? 0}</strong>
    </Typography>
  );
}

function titleForKind(kind: CorreccionEstablecimientoKind): string {
  if (kind === "contribuyente") return "Corregir contribuyente";
  if (kind === "domicilio") return "Corregir domicilio";
  return "Corregir rubro y nombre del local";
}

function hintForKind(kind: CorreccionEstablecimientoKind): string {
  if (kind === "contribuyente") return CORRECCION_CONTRIBUYENTE_HINT;
  if (kind === "domicilio") return CORRECCION_DOMICILIO_HINT;
  return CORRECCION_LOCAL_HINT;
}

/**
 * Canal controlado: corrige contribuyente, domicilio o datos del local con preview y confirmación.
 */
export function CorreccionEstablecimientoDialog({
  open,
  kind,
  establecimientoId,
  detalle,
  onClose,
  onApplied,
  onVincularDocumento,
}: Props) {
  const [documento, setDocumento] = useState(detalle.documento ?? "");
  const [apellido, setApellido] = useState(detalle.contrib_apellido ?? "");
  const [nombre, setNombre] = useState(detalle.contrib_nombre ?? "");
  const [razonSocial, setRazonSocial] = useState(detalle.razon_social ?? "");
  const [titularModo, setTitularModo] = useState<TitularCorreccionModo>(() =>
    inferTitularCorreccionModo({
      apellido: detalle.contrib_apellido,
      nombre: detalle.contrib_nombre,
      razonSocial: detalle.razon_social,
    })
  );
  const [calle, setCalle] = useState(detalle.calle ?? "");
  const [numero, setNumero] = useState(
    (detalle.numero_tipo ?? "NUMERO").toUpperCase() === "ESQUINA" ? "" : detalle.numero ?? ""
  );
  const [esquina, setEsquina] = useState(
    (detalle.numero_tipo ?? "").toUpperCase() === "ESQUINA"
      ? detalle.esquina_raw ?? detalle.numero ?? ""
      : detalle.esquina_raw ?? ""
  );
  const [numeroTipo, setNumeroTipo] = useState<NumeroModo>(
    (detalle.numero_tipo ?? "NUMERO").toUpperCase() === "ESQUINA" ? "ESQUINA" : "NUMERO"
  );
  const [rubroNombre, setRubroNombre] = useState(detalle.rubro_nombre ?? "");
  const [nombreLocal, setNombreLocal] = useState(detalle.nombre_local ?? "");
  const [rubroOptions, setRubroOptions] = useState<string[]>(() =>
    mergeLegacyRubroNames([], detalle.rubro_nombre)
  );

  const [preview, setPreview] = useState<ICorreccionEstablecimientoPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (kind !== "local" || !open) return;
    let cancelled = false;
    void fetchRubrosCatalogoCached()
      .then((items) => {
        if (cancelled) return;
        setRubroOptions(mergeLegacyRubroNames(rubroItemsToNombres(items), detalle.rubro_nombre));
      })
      .catch(() => {
        if (!cancelled) setRubroOptions(mergeLegacyRubroNames([], detalle.rubro_nombre));
      });
    return () => {
      cancelled = true;
    };
  }, [kind, open, detalle.rubro_nombre]);

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
    if (kind === "local") {
      return {
        local: {
          rubro_nombre: rubroNombre.trim() || null,
          nombre_local: nombreLocal.trim() || null,
        },
      };
    }
    if (numeroTipo === "ESQUINA") {
      const cruce = esquina.trim() || numero.trim();
      return {
        domicilio: {
          calle: calle.trim() || null,
          numero: cruce || null,
          numero_tipo: "ESQUINA",
          esquina: cruce || null,
        },
      };
    }
    return {
      domicilio: {
        calle: calle.trim() || null,
        numero: numero.trim() || null,
        numero_tipo: "NUMERO",
      },
    };
  }, [
    kind,
    documento,
    apellido,
    nombre,
    razonSocial,
    calle,
    numero,
    numeroTipo,
    esquina,
    rubroNombre,
    nombreLocal,
  ]);

  const handleClose = () => {
    if (loadingPreview || loadingApply) return;
    setPreview(null);
    setError(null);
    onClose();
  };

  const handleTitularModo = (_: MouseEvent<HTMLElement>, next: TitularCorreccionModo | null) => {
    if (!next) return;
    setTitularModo(next);
  };

  const handleNumeroModo = (_: MouseEvent<HTMLElement>, next: NumeroModo | null) => {
    if (!next) return;
    setNumeroTipo(next);
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

  const showPersonaFields = titularModo === "persona" || titularModo === "ambos";
  const showRazonFields = titularModo === "razon_social" || titularModo === "ambos";

  return (
    <>
      <AppDialog
        open={open && preview == null}
        onClose={handleClose}
        title={titleForKind(kind)}
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
            {hintForKind(kind)}
          </Typography>
          {error ? <Alert severity="warning">{error}</Alert> : null}
          {kind === "contribuyente" ? (
            <>
              <Typography variant="caption" sx={{ color: GLASS_COLORS.textSecondary }}>
                Titular
              </Typography>
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
                {titularModo === "ambos" ? (
                  <ToggleButton value="ambos">Ambos (datos actuales)</ToggleButton>
                ) : null}
              </ToggleButtonGroup>
              {titularModo === "ambos" ? (
                <Alert severity="info">{CORRECCION_TITULAR_MODO_AMBOS_HINT}</Alert>
              ) : null}
              {showPersonaFields ? (
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
              ) : null}
              {showRazonFields ? (
                <AppTextField
                  appearance="glass"
                  label="Razón social"
                  value={razonSocial}
                  onChange={(e) => setRazonSocial(e.target.value)}
                  fullWidth
                />
              ) : null}
              <AppTextField
                appearance="glass"
                label="CUIT / DNI"
                value={documento}
                onChange={(e) => setDocumento(e.target.value)}
                inputProps={{ maxLength: 11 }}
                fullWidth
              />
            </>
          ) : null}
          {kind === "domicilio" ? (
            <>
              <AppTextField
                appearance="glass"
                label="Calle"
                value={calle}
                onChange={(e) => setCalle(e.target.value)}
                fullWidth
              />
              <Typography variant="caption" sx={{ color: GLASS_COLORS.textSecondary }}>
                Numeración
              </Typography>
              <ToggleButtonGroup
                exclusive
                value={numeroTipo}
                onChange={handleNumeroModo}
                size="small"
                fullWidth
                sx={modalToggleGroupSx}
                aria-label="Número o esquina"
              >
                <ToggleButton value="NUMERO">Número</ToggleButton>
                <ToggleButton value="ESQUINA">Esquina</ToggleButton>
              </ToggleButtonGroup>
              {numeroTipo === "NUMERO" ? (
                <AppTextField
                  appearance="glass"
                  label="Número"
                  value={numero}
                  onChange={(e) => setNumero(e.target.value)}
                  fullWidth
                />
              ) : (
                <AppTextField
                  appearance="glass"
                  label="Esquina"
                  value={esquina}
                  onChange={(e) => setEsquina(e.target.value)}
                  fullWidth
                />
              )}
              <Alert severity="warning">
                Las coordenadas y el distrito no se recalculan. Pueden no coincidir con la dirección
                corregida.
              </Alert>
            </>
          ) : null}
          {kind === "local" ? (
            <>
              <AppSelect
                appearance="glass"
                label="Rubro"
                value={rubroNombre}
                onChange={(e) => setRubroNombre(String(e.target.value))}
                options={["", ...rubroOptions].map((n) => ({ value: n, label: n || "—" }))}
                fullWidth
              />
              <AppTextField
                appearance="glass"
                label="Nombre del local"
                value={nombreLocal}
                onChange={(e) => setNombreLocal(e.target.value)}
                fullWidth
              />
            </>
          ) : null}
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
          {preview?.conflicto?.codigo === "DOCUMENTO_AJENO" && onVincularDocumento ? (
            <Box>
              <Typography sx={{ fontSize: "13px", color: GLASS_COLORS.textSecondary, fontFamily: FONT_FAMILY_UI, mb: 1 }}>
                {VINCULACION_DOCUMENTO_AJENO_CTA}
              </Typography>
              <AppButton
                dsVariant="primary"
                onClick={() => onVincularDocumento(documento.trim())}
              >
                {VINCULACION_ACCION}
              </AppButton>
            </Box>
          ) : null}

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

          {preview?.local ? (
            <Box>
              <Typography sx={{ fontWeight: 700, fontSize: "12px", letterSpacing: "0.08em", mb: 0.75 }}>
                RUBRO Y NOMBRE DEL LOCAL
              </Typography>
              <Typography sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI }}>
                Rubro actual: {dash(preview.local.actual?.rubro_nombre as string)} → propuesto:{" "}
                {dash(preview.local.propuesto?.rubro_nombre as string)}
              </Typography>
              <Typography sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI }}>
                Nombre del local actual: {dash(preview.local.actual?.nombre_local as string)} → propuesto:{" "}
                {dash(preview.local.propuesto?.nombre_local as string)}
              </Typography>
              <ConteoLine label="Establecimiento seleccionado" cantidad={1} />
              <ConteoLine
                label="Actuaciones que leen este rubro"
                cantidad={preview.local.actuaciones_que_leen_rubro?.cantidad}
              />
              <ConteoLine
                label="Otros establecimientos del titular (no se modifican)"
                cantidad={preview.local.otros_establecimientos_contribuyente?.cantidad}
              />
              <Alert severity="info" sx={{ mt: 1 }}>
                {preview.local.advertencia}
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
