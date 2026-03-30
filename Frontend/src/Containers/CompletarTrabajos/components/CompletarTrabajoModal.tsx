import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, Typography } from "@mui/material";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";
import { submitCompletarTrabajoCierreFromRow } from "../completion/submitCompletarTrabajoCierre";
import type { CompletarTrabajoCatalogs } from "../hooks/completarTrabajoCatalogsCache";
import { getContraproducenciaUxHint } from "../utils/contraproducenciaUxHint";
import {
  applyCompletarTrabajoFieldErrorsFromApi,
  COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY,
} from "../utils/completarTrabajoErrors";

const ACTA_KEYS_EMPTY = {
  acta_inspeccion_num: "",
  acta_notificacion_num: "",
  notificacion_motivo_1: "",
  notificacion_motivo_2: "",
  notificacion_motivo_3: "",
  acta_comprobacion_num: "",
  comprobacion_motivo: "",
  acta_clausura_num: "",
  acta_decomiso_num: "",
  decomiso_kilos_total: "",
} as const;

function mergeCatalogOpts(catalog: string[], current: string | null | undefined): { value: string; label: string }[] {
  const set = new Set<string>(catalog);
  const c = (current ?? "").trim();
  if (c) set.add(c);
  return [{ value: "", label: "—" }, ...[...set].sort().map((v) => ({ value: v, label: v }))];
}

function domicilioResumen(r: ICompletarTrabajoPendienteRow): string {
  return r.domicilio_texto?.trim() || [r.calle, r.numero].filter(Boolean).join(" ").trim() || "—";
}

function inspectoresLinea(r: ICompletarTrabajoPendienteRow): string {
  const t = r.inspectores_texto?.trim();
  if (t) return t;
  const parts = [r.inspector1, r.inspector2, r.inspector3].filter((x) => x?.trim());
  return parts.length ? parts.join(", ") : "—";
}

function dashIfEmpty(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export type CompletarTrabajoModalProps = {
  open: boolean;
  row: ICompletarTrabajoPendienteRow | null;
  catalogs: CompletarTrabajoCatalogs | null;
  catalogsReady: boolean;
  onClose: () => void;
  onSuccess: (rutaItemId: number) => void;
};

/**
 * Cierre Completar trabajo: cabecera fija, editables en orden cerrado, actas solo sin contraproducencia.
 */
export function CompletarTrabajoModal({
  open,
  row,
  catalogs,
  catalogsReady,
  onClose,
  onSuccess,
}: CompletarTrabajoModalProps) {
  const cat = catalogs ?? { motivos: [], motivosComprobacion: [], contraproducencias: [] };
  const [contraproducencia, setContraproducencia] = useState("");
  const [calle, setCalle] = useState("");
  const [numero, setNumero] = useState("");
  const [rubroNombre, setRubroNombre] = useState("");
  const [docNro, setDocNro] = useState("");
  const [contribApellido, setContribApellido] = useState("");
  const [contribNombre, setContribNombre] = useState("");
  const [nombreLocal, setNombreLocal] = useState("");
  const [actaInspeccion, setActaInspeccion] = useState("");
  const [actaNotificacion, setActaNotificacion] = useState("");
  const [notifM1, setNotifM1] = useState("");
  const [notifM2, setNotifM2] = useState("");
  const [notifM3, setNotifM3] = useState("");
  const [actaComprobacion, setActaComprobacion] = useState("");
  const [comprobacionMotivo, setComprobacionMotivo] = useState("");
  const [actaClausura, setActaClausura] = useState("");
  const [actaDecomiso, setActaDecomiso] = useState("");
  const [decomisoKilos, setDecomisoKilos] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** Claves alineadas al payload / errores 422 del backend (pydantic field names). */
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open || !row) return;
    setContraproducencia(row.contraproducencia ?? "");
    setCalle(row.calle ?? "");
    setNumero(row.numero ?? "");
    setRubroNombre(row.rubro_nombre ?? "");
    setDocNro(row.doc_nro ?? "");
    setContribApellido(row.contrib_apellido ?? "");
    setContribNombre(row.contrib_nombre ?? "");
    setNombreLocal(row.nombre_local ?? "");
    setActaInspeccion(row.acta_inspeccion_num ?? "");
    setActaNotificacion(row.acta_notificacion_num ?? "");
    setNotifM1(row.notificacion_motivo_1 ?? "");
    setNotifM2(row.notificacion_motivo_2 ?? "");
    setNotifM3(row.notificacion_motivo_3 ?? "");
    setActaComprobacion(row.acta_comprobacion_num ?? "");
    setComprobacionMotivo(row.comprobacion_motivo ?? "");
    setActaClausura(row.acta_clausura_num ?? "");
    setActaDecomiso(row.acta_decomiso_num ?? "");
    const k = row.decomiso_kilos_total;
    setDecomisoKilos(k == null || k === "" ? "" : String(k));
    setError(null);
    setFieldErrors({});
  }, [open, row]);

  const fe = useCallback((apiField: string) => fieldErrors[apiField], [fieldErrors]);
  const clearFe = useCallback((apiField: string) => {
    setFieldErrors((prev) => {
      if (!(apiField in prev)) return prev;
      const next = { ...prev };
      delete next[apiField];
      return next;
    });
  }, []);

  const contraHint = useMemo(() => getContraproducenciaUxHint(contraproducencia), [contraproducencia]);
  const visitaRealizada = !contraproducencia.trim();

  const inspectoresMostrar = useMemo(() => (row ? inspectoresLinea(row) : "—"), [row]);

  const contraOpts = useMemo(
    () => [
      { value: "", label: "Sin contraproducencia (visita realizada)" },
      ...mergeCatalogOpts(cat.contraproducencias, row?.contraproducencia).filter((o) => o.value !== ""),
    ],
    [cat.contraproducencias, row?.contraproducencia]
  );
  const motivoNotifOpts = useMemo(() => mergeCatalogOpts(cat.motivos, undefined), [cat.motivos]);
  const motivoCompOpts = useMemo(
    () => mergeCatalogOpts(cat.motivosComprobacion, undefined),
    [cat.motivosComprobacion]
  );

  const handleClose = useCallback(() => {
    if (saving) return;
    onClose();
  }, [saving, onClose]);

  const handleSubmit = async () => {
    if (!row) return;
    setFieldErrors({});
    setError(null);
    if (visitaRealizada && actaComprobacion.trim() && !comprobacionMotivo.trim()) {
      setFieldErrors({
        comprobacion_motivo: "Si cargás acta de comprobación, elegí un motivo de comprobación.",
      });
      setError(COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY);
      return;
    }
    setSaving(true);
    try {
      const values: Record<string, unknown> = {
        contraproducencia,
        rubro_nombre: rubroNombre,
        calle,
        numero,
        doc_nro: docNro,
        contrib_apellido: contribApellido,
        contrib_nombre: contribNombre,
        nombre_local: nombreLocal,
        ...ACTA_KEYS_EMPTY,
      };

      if (visitaRealizada) {
        Object.assign(values, {
          acta_inspeccion_num: actaInspeccion,
          acta_notificacion_num: actaNotificacion,
          notificacion_motivo_1: notifM1,
          notificacion_motivo_2: notifM2,
          notificacion_motivo_3: notifM3,
          acta_comprobacion_num: actaComprobacion,
          comprobacion_motivo: comprobacionMotivo,
          acta_clausura_num: actaClausura,
          acta_decomiso_num: actaDecomiso,
          decomiso_kilos_total: decomisoKilos,
        });
      }

      await submitCompletarTrabajoCierreFromRow(row, values, { omitPrecargadoPr2: true });
      onSuccess(row.ruta_item_id);
      onClose();
    } catch (e) {
      const { fieldErrors: nextFe, generalMessage } = applyCompletarTrabajoFieldErrorsFromApi(e);
      setFieldErrors(nextFe);
      setError(generalMessage);
    } finally {
      setSaving(false);
    }
  };

  const col = { display: "flex", flexDirection: "column" as const, gap: 1.5 };
  const labelMuted = { color: "rgba(255,255,255,0.5)", fontFamily: '"Tactic Sans", sans-serif' } as const;

  return (
    <AppDialog
      open={open && row != null}
      onClose={handleClose}
      onCloseButtonClick={handleClose}
      title="Completar trabajo"
      maxWidth="sm"
      fullWidth
      showCloseButton
      contentSx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
      actions={
        <>
          <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
            Cancelar
          </AppButton>
          <AppButton dsVariant="primary" onClick={() => void handleSubmit()} disabled={saving} loading={saving}>
            Guardar cierre
          </AppButton>
        </>
      }
    >
      {row && (
        <Box
          sx={{
            ...col,
            p: 1.5,
            borderRadius: 2,
            bgcolor: "rgba(255,255,255,0.06)",
            fontFamily: '"Tactic Sans", sans-serif',
          }}
        >
          <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.5)", textTransform: "uppercase" }}>
            Solo lectura
          </Typography>
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
            Fecha: {dashIfEmpty(row.fecha_actuacion)}
          </Typography>
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
            Tipo de iniciador: {dashIfEmpty(row.tipo_iniciador)}
          </Typography>
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)" }}>
            OT {row.orden_trabajo_numero ?? "—"}
          </Typography>
          <Box>
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block" }}>
              Domicilio actual
            </Typography>
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
              {domicilioResumen(row)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block" }}>
              Inspectores
            </Typography>
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
              {inspectoresMostrar}
            </Typography>
          </Box>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ borderRadius: 2, whiteSpace: "pre-line" }}>
          {error}
        </Alert>
      )}

      <Box sx={col}>
        <AppSelect
          label="Contraproducencia"
          value={contraproducencia}
          onChange={(e) => {
            setContraproducencia(e.target.value as string);
            clearFe("contraproducencia");
          }}
          fullWidth
          disabled={!catalogsReady}
          options={contraOpts}
          error={Boolean(fe("contraproducencia"))}
          helperText={fe("contraproducencia") || undefined}
        />
        {contraHint === "cierra_sin_reingreso" && (
          <Alert severity="warning" sx={{ borderRadius: 2 }}>
            Este motivo cierra el iniciador: no vuelve a pendientes.
          </Alert>
        )}
        {contraHint === "reingreso_prioridad_alta" && (
          <Alert severity="info" sx={{ borderRadius: 2 }}>
            El trabajo vuelve a pendientes con prioridad alta.
          </Alert>
        )}

        <Typography variant="caption" sx={labelMuted}>
          Domicilio
        </Typography>
        <AppTextField
          appearance="dense"
          label="Calle"
          value={calle}
          onChange={(e) => {
            setCalle(e.target.value);
            clearFe("calle");
          }}
          fullWidth
          error={Boolean(fe("calle"))}
          helperText={fe("calle") || undefined}
        />
        <AppTextField
          appearance="dense"
          label="Número"
          value={numero}
          onChange={(e) => {
            setNumero(e.target.value);
            clearFe("numero");
          }}
          fullWidth
          error={Boolean(fe("numero"))}
          helperText={fe("numero") || undefined}
        />

        <AppTextField
          appearance="dense"
          label="Rubro"
          value={rubroNombre}
          onChange={(e) => {
            setRubroNombre(e.target.value);
            clearFe("rubro_nombre");
          }}
          fullWidth
          error={Boolean(fe("rubro_nombre"))}
          helperText={fe("rubro_nombre") || undefined}
        />
        <AppTextField
          appearance="dense"
          label="Contribuyente apellido / razón social"
          value={contribApellido}
          onChange={(e) => {
            setContribApellido(e.target.value);
            clearFe("contrib_apellido");
          }}
          fullWidth
          error={Boolean(fe("contrib_apellido"))}
          helperText={fe("contrib_apellido") || undefined}
        />
        <AppTextField
          appearance="dense"
          label="Contribuyente nombre"
          value={contribNombre}
          onChange={(e) => {
            setContribNombre(e.target.value);
            clearFe("contrib_nombre");
          }}
          fullWidth
          error={Boolean(fe("contrib_nombre"))}
          helperText={fe("contrib_nombre") || undefined}
        />
        <AppTextField
          appearance="dense"
          label="DNI"
          value={docNro}
          onChange={(e) => {
            setDocNro(e.target.value);
            clearFe("doc_nro");
          }}
          fullWidth
          error={Boolean(fe("doc_nro"))}
          helperText={fe("doc_nro") || undefined}
        />
        <AppTextField
          appearance="dense"
          label="Nombre del local"
          value={nombreLocal}
          onChange={(e) => {
            setNombreLocal(e.target.value);
            clearFe("nombre_local");
          }}
          fullWidth
          inputProps={{ maxLength: 255 }}
          error={Boolean(fe("nombre_local"))}
          helperText={fe("nombre_local") || undefined}
        />
      </Box>

      {visitaRealizada && (
        <Box sx={{ ...col, pt: 0.5 }}>
          <AppTextField
            appearance="dense"
            label="N° acta de inspección"
            value={actaInspeccion}
            onChange={(e) => {
              setActaInspeccion(e.target.value);
              clearFe("acta_inspeccion_num");
            }}
            fullWidth
            error={Boolean(fe("acta_inspeccion_num"))}
            helperText={fe("acta_inspeccion_num") || undefined}
          />
          <AppTextField
            appearance="dense"
            label="N° acta de notificación"
            value={actaNotificacion}
            onChange={(e) => {
              setActaNotificacion(e.target.value);
              clearFe("acta_notificacion_num");
            }}
            fullWidth
            error={Boolean(fe("acta_notificacion_num"))}
            helperText={fe("acta_notificacion_num") || undefined}
          />
          <AppSelect
            label="Motivo notificación 1"
            value={notifM1}
            onChange={(e) => {
              setNotifM1(e.target.value);
              clearFe("notificacion_motivo_1");
            }}
            fullWidth
            disabled={!catalogsReady}
            options={motivoNotifOpts}
            error={Boolean(fe("notificacion_motivo_1"))}
            helperText={fe("notificacion_motivo_1") || undefined}
          />
          <AppSelect
            label="Motivo notificación 2"
            value={notifM2}
            onChange={(e) => {
              setNotifM2(e.target.value);
              clearFe("notificacion_motivo_2");
            }}
            fullWidth
            disabled={!catalogsReady}
            options={motivoNotifOpts}
            error={Boolean(fe("notificacion_motivo_2"))}
            helperText={fe("notificacion_motivo_2") || undefined}
          />
          <AppSelect
            label="Motivo notificación 3"
            value={notifM3}
            onChange={(e) => {
              setNotifM3(e.target.value);
              clearFe("notificacion_motivo_3");
            }}
            fullWidth
            disabled={!catalogsReady}
            options={motivoNotifOpts}
            error={Boolean(fe("notificacion_motivo_3"))}
            helperText={fe("notificacion_motivo_3") || undefined}
          />
          <AppTextField
            appearance="dense"
            label="N° acta de comprobación"
            value={actaComprobacion}
            onChange={(e) => {
              setActaComprobacion(e.target.value);
              clearFe("acta_comprobacion_num");
            }}
            fullWidth
            error={Boolean(fe("acta_comprobacion_num"))}
            helperText={fe("acta_comprobacion_num") || undefined}
          />
          <AppSelect
            label="Motivo de comprobación"
            value={comprobacionMotivo}
            onChange={(e) => {
              setComprobacionMotivo(e.target.value);
              clearFe("comprobacion_motivo");
            }}
            fullWidth
            disabled={!catalogsReady}
            options={motivoCompOpts}
            error={Boolean(fe("comprobacion_motivo"))}
            helperText={fe("comprobacion_motivo") || undefined}
          />
          <AppTextField
            appearance="dense"
            label="N° acta de clausura"
            value={actaClausura}
            onChange={(e) => {
              setActaClausura(e.target.value);
              clearFe("acta_clausura_num");
            }}
            fullWidth
            error={Boolean(fe("acta_clausura_num"))}
            helperText={fe("acta_clausura_num") || undefined}
          />
          <AppTextField
            appearance="dense"
            label="N° acta de decomiso"
            value={actaDecomiso}
            onChange={(e) => {
              setActaDecomiso(e.target.value);
              clearFe("acta_decomiso_num");
            }}
            fullWidth
            error={Boolean(fe("acta_decomiso_num"))}
            helperText={fe("acta_decomiso_num") || undefined}
          />
          <AppTextField
            appearance="dense"
            label="Kilos decomisados"
            value={decomisoKilos}
            onChange={(e) => {
              setDecomisoKilos(e.target.value);
              clearFe("decomiso_kilos_total");
            }}
            fullWidth
            error={Boolean(fe("decomiso_kilos_total"))}
            helperText={fe("decomiso_kilos_total") || undefined}
          />
        </Box>
      )}
    </AppDialog>
  );
}
