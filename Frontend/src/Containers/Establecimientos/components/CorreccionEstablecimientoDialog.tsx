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
  aplicarVinculacionEstablecimiento,
  previewCorreccionEstablecimiento,
  previewVinculacionEstablecimiento,
  type ICorreccionEstablecimientoPayload,
  type ICorreccionEstablecimientoPreview,
  type IEstablecimientoOperativoDetail,
  type IVinculacionEstablecimientoPreview,
} from "../../../api/establecimientosOperativosApi";
import {
  fetchRubrosCatalogoCached,
  mergeLegacyRubroNames,
  rubroItemsToNombres,
} from "../../../utils/rubrosCatalogCache";
import {
  CORRECCION_CONTRIBUYENTE_HINT,
  CORRECCION_DATOS_CONTRIBUYENTE_ACCION,
  CORRECCION_DOCUMENTO_CONFIRMACION_DETALLE,
  CORRECCION_DOCUMENTO_CONFIRMACION_TITULO,
  CORRECCION_DOCUMENTO_MISMA_PERSONA,
  CORRECCION_DOMICILIO_HINT,
  CORRECCION_LOCAL_HINT,
  CORRECCION_TITULAR_MODO_AMBOS_HINT,
  VINCULACION_ASOCIAR,
  VINCULACION_DOCUMENTOS_EMITIDOS,
  VINCULACION_REGISTRADO_TITULO,
  VINCULACION_VOLVER,
  inferTitularCorreccionModo,
  mensajeConflictoVinculacionInseguro,
  ofreceVinculacionDesdeConflicto,
  type TitularCorreccionModo,
} from "../utils/correccionEstablecimientoCopy";
import { VinculacionConfirmacionContent } from "./VinculacionConfirmacionContent";

export type CorreccionEstablecimientoKind = "contribuyente" | "domicilio" | "local";

export type CorreccionAppliedResult = {
  establecimiento_operativo_canonico_id?: number | null;
};

type NumeroModo = "NUMERO" | "ESQUINA";

type Props = {
  open: boolean;
  kind: CorreccionEstablecimientoKind;
  establecimientoId: number;
  detalle: IEstablecimientoOperativoDetail;
  onClose: () => void;
  onApplied: (result?: CorreccionAppliedResult) => void;
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
    const data = e.response.data as { detail?: string; codigo?: string };
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
  if (kind === "contribuyente") return CORRECCION_DATOS_CONTRIBUYENTE_ACCION;
  if (kind === "domicilio") return "Corregir domicilio";
  return "Corregir rubro y nombre del local";
}

function hintForKind(kind: CorreccionEstablecimientoKind): string {
  if (kind === "contribuyente") return CORRECCION_CONTRIBUYENTE_HINT;
  if (kind === "domicilio") return CORRECCION_DOMICILIO_HINT;
  return CORRECCION_LOCAL_HINT;
}

function mensajeConflictoCorreccion(preview: ICorreccionEstablecimientoPreview): string | null {
  const conflicto = preview.conflicto;
  if (!conflicto) return null;
  if (
    conflicto.codigo === "DOCUMENTO_AJENO" ||
    conflicto.codigo === "DOCUMENTO_AMBIGUO" ||
    conflicto.codigo === "AMBIGUEDAD_DOMICILIO" ||
    conflicto.codigo === "PREVIEW_STALE"
  ) {
    return mensajeConflictoVinculacionInseguro(conflicto.detail);
  }
  return conflicto.detail ?? null;
}

function CampoCambio({
  label,
  actual,
  propuesto,
}: {
  label: string;
  actual: string | number | null | undefined;
  propuesto: string | number | null | undefined;
}) {
  const a = dash(actual);
  const b = dash(propuesto);
  if (a === b) return null;
  return (
    <Typography sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI }}>
      {label}: {a} → {b}
    </Typography>
  );
}

/**
 * Canal controlado: corrige contribuyente, domicilio o datos del local con preview y confirmación.
 * Si Ver alcance detecta DOCUMENTO_AJENO con ofrece_vinculacion, continúa por el canal de vinculación
 * (preview + confirmación explícita). No aplica cambios al abrir la vista previa.
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
  const [vinculacionPreview, setVinculacionPreview] = useState<IVinculacionEstablecimientoPreview | null>(
    null
  );
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
    razonSocial,
    nombre,
    calle,
    numero,
    numeroTipo,
    esquina,
    rubroNombre,
    nombreLocal,
  ]);

  const resetAlcance = () => {
    setPreview(null);
    setVinculacionPreview(null);
    setError(null);
  };

  const handleClose = () => {
    if (loadingPreview || loadingApply) return;
    resetAlcance();
    onClose();
  };

  const handleVolverAlcance = () => {
    if (loadingApply) return;
    resetAlcance();
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
    setPreview(null);
    setVinculacionPreview(null);
    setLoadingPreview(true);
    try {
      const res = await previewCorreccionEstablecimiento(establecimientoId, payload);
      if (ofreceVinculacionDesdeConflicto(res.conflicto)) {
        const vinc = await previewVinculacionEstablecimiento(establecimientoId, {
          documento: documento.trim(),
        });
        setVinculacionPreview(vinc);
        if (!vinc.puede_aplicar || vinc.conflicto) {
          setError(
            mensajeConflictoVinculacionInseguro(vinc.conflicto?.detail ?? null)
          );
        }
        return;
      }
      setPreview(res);
      const conflictoMsg = mensajeConflictoCorreccion(res);
      if (conflictoMsg) setError(conflictoMsg);
    } catch (e) {
      setError(apiErrorMessage(e));
      setPreview(null);
      setVinculacionPreview(null);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleApplyCorreccion = async () => {
    if (!preview?.puede_aplicar) return;
    setError(null);
    setLoadingApply(true);
    try {
      await aplicarCorreccionEstablecimiento(establecimientoId, {
        ...payload,
        fingerprint: preview.fingerprint ?? null,
      });
      setPreview(null);
      onApplied();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoadingApply(false);
    }
  };

  const handleApplyVinculacion = async () => {
    if (!vinculacionPreview?.puede_aplicar || !vinculacionPreview.fingerprint) return;
    setError(null);
    setLoadingApply(true);
    try {
      const res = await aplicarVinculacionEstablecimiento(establecimientoId, {
        documento: documento.trim(),
        fingerprint: vinculacionPreview.fingerprint,
      });
      setVinculacionPreview(null);
      onApplied({
        establecimiento_operativo_canonico_id: res.establecimiento_operativo_canonico_id,
      });
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoadingApply(false);
    }
  };

  const showPersonaFields = titularModo === "persona" || titularModo === "ambos";
  const showRazonFields = titularModo === "razon_social" || titularModo === "ambos";
  const formOpen = open && preview == null && vinculacionPreview == null;
  const correccionConfirmOpen = open && preview != null && vinculacionPreview == null;
  const vinculacionConfirmOpen = open && vinculacionPreview != null;
  const puedeAsociar = Boolean(
    vinculacionPreview?.puede_aplicar &&
      vinculacionPreview.fingerprint &&
      !vinculacionPreview.conflicto
  );

  return (
    <>
      <AppDialog
        open={formOpen}
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
        open={correccionConfirmOpen}
        onClose={handleVolverAlcance}
        onConfirm={() => void handleApplyCorreccion()}
        title="Confirmar corrección"
        cancelLabel={VINCULACION_VOLVER}
        confirmLabel="Guardar corrección"
        confirmDisabled={
          !preview?.puede_aplicar ||
          Boolean(preview?.conflicto) ||
          (preview?.contribuyente?.cambia_documento_identidad === true && !preview.fingerprint)
        }
        loading={loadingApply}
        maxWidth="sm"
      >
        <Stack spacing={1.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}
          {preview?.sin_cambios ? (
            <Alert severity="info">No hay cambios. No se desvincula el contribuyente ni se modifica ningún dato.</Alert>
          ) : null}

          {preview?.contribuyente ? (
            <Box>
              <Typography sx={{ fontWeight: 700, fontSize: "12px", letterSpacing: "0.08em", mb: 0.75 }}>
                CONTRIBUYENTE
              </Typography>
              <CampoCambio
                label="CUIT/DNI"
                actual={preview.contribuyente.actual?.documento as string}
                propuesto={preview.contribuyente.propuesto?.documento as string}
              />
              <CampoCambio
                label="Apellido"
                actual={preview.contribuyente.actual?.apellido as string}
                propuesto={preview.contribuyente.propuesto?.apellido as string}
              />
              <CampoCambio
                label="Nombre"
                actual={preview.contribuyente.actual?.nombre as string}
                propuesto={preview.contribuyente.propuesto?.nombre as string}
              />
              <CampoCambio
                label="Razón social"
                actual={preview.contribuyente.actual?.razon_social as string}
                propuesto={preview.contribuyente.propuesto?.razon_social as string}
              />
              {preview.contribuyente.establecimientos_asociados &&
              preview.contribuyente.establecimientos_asociados.length > 0 ? (
                <Box sx={{ mt: 1 }}>
                  <Typography sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI, fontWeight: 700 }}>
                    Establecimientos que se actualizan
                  </Typography>
                  {preview.contribuyente.establecimientos_asociados.map((est, idx) => (
                    <Typography
                      key={`${est.domicilio_texto ?? "local"}-${idx}`}
                      sx={{ fontSize: "13px", fontFamily: FONT_FAMILY_UI }}
                    >
                      {dash(est.domicilio_texto)}
                      {est.nombre_local ? ` · ${est.nombre_local}` : ""}
                      {typeof est.actuaciones_cantidad === "number"
                        ? ` · ${est.actuaciones_cantidad} actuación${est.actuaciones_cantidad === 1 ? "" : "es"}`
                        : ""}
                    </Typography>
                  ))}
                </Box>
              ) : (
                <ConteoLine
                  label="Establecimientos vinculados"
                  cantidad={preview.contribuyente.establecimientos_afectados.cantidad}
                />
              )}
              <ConteoLine
                label="Actuaciones vinculadas"
                cantidad={preview.contribuyente.actuaciones_afectadas.cantidad}
              />
              {preview.conflicto ? null : preview.contribuyente.cambia_documento_identidad ? (
                <Alert severity="warning" sx={{ mt: 1 }}>
                  <Typography sx={{ fontWeight: 700, fontSize: "13px", mb: 0.5 }}>
                    {CORRECCION_DOCUMENTO_CONFIRMACION_TITULO}
                  </Typography>
                  {CORRECCION_DOCUMENTO_CONFIRMACION_DETALLE} {CORRECCION_DOCUMENTO_MISMA_PERSONA}
                </Alert>
              ) : (
                <Alert severity="info" sx={{ mt: 1 }}>
                  {preview.contribuyente.advertencia}
                </Alert>
              )}
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
              {VINCULACION_DOCUMENTOS_EMITIDOS}
            </Typography>
          ) : null}
        </Stack>
      </ConfirmDialog>

      <ConfirmDialog
        open={vinculacionConfirmOpen}
        onClose={handleVolverAlcance}
        onConfirm={() => void handleApplyVinculacion()}
        title={puedeAsociar ? VINCULACION_REGISTRADO_TITULO : "Revisá los datos"}
        cancelLabel={VINCULACION_VOLVER}
        confirmLabel={VINCULACION_ASOCIAR}
        confirmDisabled={!puedeAsociar}
        loading={loadingApply}
        maxWidth="sm"
      >
        {vinculacionPreview ? (
          <VinculacionConfirmacionContent preview={vinculacionPreview} error={error} />
        ) : null}
      </ConfirmDialog>
    </>
  );
}
