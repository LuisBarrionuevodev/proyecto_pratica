import { useCallback, useEffect, useMemo, useState } from "react";
import { CircularProgress, Stack, Typography } from "@mui/material";

import {
  createRutaGrupo,
  createRutaTrabajo,
  getRutaTrabajoDetail,
  listRutasBorrador,
  type IRutaGrupoMin,
  type IRutaTrabajo,
  type RutaTurno,
} from "../../api/rutasTrabajoApi";
import { agregarDesdePoolRuta, createRutaPoolDia, listRutaPoolDia } from "../../api/rutaPoolDiaApi";
import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudFormSlot,
  CrudGlassDialog,
} from "../../components/crudDialog";
import { DocumentalCrudSection } from "../../components/documental/documentalCrudLayout";
import { DOC_MODAL_BLOCK_STACK_SPACING } from "../../styles/documentalModalTokens";
import { AppButton, AppSelect, AppTextField } from "../../ui";
import { fechaLocalHoyIso } from "../../utils/dateRange";
import { parseApiError } from "../../utils/parseApiError";
import {
  normalizarEstadoOperativoPool,
  OPER_RUTA_LABELS,
  type OperRutaPoolFila,
} from "../../utils/operRutaPoolAcciones";

export type AgregarARutaOperDialogProps = {
  open: boolean;
  iniciadorId: number | null;
  estadoOperativoPool?: string | null;
  /** Contexto pool/ruta de la fila para pre-cargar fecha, turno, ruta y grupo. */
  operContext?: OperRutaPoolFila | null;
  fechaOperativa?: string;
  onClose: () => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
};

function suggestedGrupoNombre(grupos: IRutaGrupoMin[]): string {
  const nums = grupos.map((g) => {
    const m = /^Grupo\s+(\d+)$/i.exec((g.nombre ?? "").trim());
    return m ? Number(m[1]) : 0;
  });
  const next = nums.length ? Math.max(...nums) + 1 : 1;
  return `Grupo ${next}`;
}

async function resolverPoolId(
  iniciadorId: number,
  fecha: string,
  estadoOperativo: string | null | undefined
): Promise<number> {
  const estado = normalizarEstadoOperativoPool(estadoOperativo);
  if (estado === "en_pool") {
    const resp = await listRutaPoolDia({ fecha, estado: "EN_POOL", per_page: 100 });
    const match = (resp.items ?? []).find(
      (item) => Number(item.iniciador_id ?? item.iniciador_ruta_id) === iniciadorId
    );
    if (match?.pool_id) return match.pool_id;
    throw new Error("No se encontró el ítem en el pool del día.");
  }
  const created = await createRutaPoolDia({
    origen_tipo: "INICIADOR",
    iniciador_ruta_id: iniciadorId,
    fecha,
  });
  return created.item.pool_id;
}

/**
 * Modal operativo: fecha → turno → ruta → solo ruta o asignar a grupo.
 */
export function AgregarARutaOperDialog({
  open,
  iniciadorId,
  estadoOperativoPool,
  operContext,
  fechaOperativa,
  onClose,
  onSuccess,
  onError,
}: AgregarARutaOperDialogProps) {
  const [fecha, setFecha] = useState(() => fechaOperativa ?? fechaLocalHoyIso());
  const [turno, setTurno] = useState<RutaTurno>("MANIANA");
  const [loadingRutas, setLoadingRutas] = useState(false);
  const [loadingGrupos, setLoadingGrupos] = useState(false);
  const [creatingRuta, setCreatingRuta] = useState(false);
  const [creatingGrupo, setCreatingGrupo] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [rutas, setRutas] = useState<IRutaTrabajo[]>([]);
  const [grupos, setGrupos] = useState<IRutaGrupoMin[]>([]);
  const [rutaId, setRutaId] = useState("");
  const [grupoId, setGrupoId] = useState("");
  const [modoGrupo, setModoGrupo] = useState(false);

  const rutasFiltradas = useMemo(
    () => rutas.filter((r) => r.turno === turno),
    [rutas, turno]
  );

  const handleClose = useCallback(() => {
    if (submitting || creatingRuta || creatingGrupo) return;
    onClose();
  }, [submitting, creatingRuta, creatingGrupo, onClose]);

  const loadGrupos = useCallback(
    async (targetRutaId: number) => {
      setLoadingGrupos(true);
      try {
        const detail = await getRutaTrabajoDetail(targetRutaId);
        const gs = detail.grupos ?? [];
        setGrupos(gs);
        setGrupoId(gs.length === 1 ? String(gs[0].id) : "");
      } catch (err) {
        onError(parseApiError(err, "No se pudieron cargar los grupos de la ruta.").message);
        setGrupos([]);
        setGrupoId("");
      } finally {
        setLoadingGrupos(false);
      }
    },
    [onError]
  );

  useEffect(() => {
    if (!open) return;
    const ctx = operContext ?? null;
    const estado = normalizarEstadoOperativoPool(ctx?.estado_operativo_pool ?? estadoOperativoPool);
    let initFecha = fechaOperativa?.trim() || fechaLocalHoyIso();
    let initTurno: RutaTurno = "MANIANA";
    let initRutaId = "";
    let initGrupoId = "";
    let initModoGrupo = false;

    if (estado === "en_pool" || estado === "en_ruta_borrador") {
      const poolFecha = ctx?.pool_fecha ?? ctx?.ruta_fecha;
      if (poolFecha?.trim()) initFecha = poolFecha.trim().slice(0, 10);
      const turnoRaw = (ctx?.ruta_turno ?? "").trim().toUpperCase();
      if (turnoRaw === "MANIANA" || turnoRaw === "TARDE") initTurno = turnoRaw;
      if (ctx?.ruta_trabajo_id != null) initRutaId = String(ctx.ruta_trabajo_id);
      if (estado === "en_ruta_borrador" && ctx?.grupo_id != null) {
        initGrupoId = String(ctx.grupo_id);
        initModoGrupo = true;
      }
    }

    setFecha(initFecha);
    setTurno(initTurno);
    setRutaId(initRutaId);
    setGrupoId(initGrupoId);
    setGrupos([]);
    setRutas([]);
    setModoGrupo(initModoGrupo);
  }, [open, fechaOperativa, operContext, estadoOperativoPool]);

  useEffect(() => {
    if (!open || !fecha) return;
    let cancelled = false;
    setLoadingRutas(true);
    void listRutasBorrador({ fecha, per_page: 50 })
      .then((resp) => {
        if (cancelled) return;
        setRutas(resp.items ?? []);
      })
      .catch((err) => {
        if (cancelled) return;
        onError(parseApiError(err, "No se pudieron cargar rutas borrador.").message);
        setRutas([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingRutas(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, fecha, onError]);

  useEffect(() => {
    if (!open) return;
    if (rutasFiltradas.length === 1) {
      setRutaId(String(rutasFiltradas[0].id));
    } else if (rutaId && !rutasFiltradas.some((r) => String(r.id) === rutaId)) {
      setRutaId("");
      setGrupos([]);
      setGrupoId("");
      setModoGrupo(false);
    }
  }, [open, rutasFiltradas, rutaId]);

  useEffect(() => {
    if (!open || !rutaId || !modoGrupo) {
      if (!modoGrupo) {
        setGrupos([]);
        setGrupoId("");
      }
      return;
    }
    void loadGrupos(Number(rutaId));
  }, [open, rutaId, modoGrupo, loadGrupos]);

  const rutaOptions = useMemo(
    () => [
      { value: "", label: "Seleccioná ruta" },
      ...rutasFiltradas.map((r) => ({
        value: String(r.id),
        label: r.display_name?.trim() || `Ruta #${r.numero} · ${r.fecha}`,
      })),
    ],
    [rutasFiltradas]
  );

  const grupoOptions = useMemo(
    () => [
      { value: "", label: "Seleccioná grupo" },
      ...grupos.map((g) => ({ value: String(g.id), label: g.nombre?.trim() || `Grupo #${g.id}` })),
    ],
    [grupos]
  );

  const sinRutas = !loadingRutas && rutasFiltradas.length === 0;
  const listoParaAcciones = Boolean(rutaId) && !loadingRutas;

  const handleCrearRuta = useCallback(async () => {
    if (!fecha) return;
    setCreatingRuta(true);
    try {
      const resp = await createRutaTrabajo({ fecha, turno });
      setRutas((prev) => [...prev, resp.item]);
      setRutaId(String(resp.item.id));
      setGrupos([]);
      setGrupoId("");
      setModoGrupo(false);
    } catch (err) {
      onError(parseApiError(err, "No se pudo crear la ruta borrador.").message);
    } finally {
      setCreatingRuta(false);
    }
  }, [fecha, turno, onError]);

  const handleCrearGrupo = useCallback(async () => {
    if (!rutaId) return;
    setCreatingGrupo(true);
    try {
      const nombre = suggestedGrupoNombre(grupos);
      const resp = await createRutaGrupo(Number(rutaId), { nombre });
      setGrupos((prev) => [...prev, resp.item]);
      setGrupoId(String(resp.item.id));
    } catch (err) {
      onError(parseApiError(err, "No se pudo crear el grupo.").message);
    } finally {
      setCreatingGrupo(false);
    }
  }, [rutaId, grupos, onError]);

  const handleSoloPool = useCallback(async () => {
    if (iniciadorId == null) {
      onError("No se encontró el iniciador de la fila.");
      return;
    }
    setSubmitting(true);
    try {
      const estado = normalizarEstadoOperativoPool(estadoOperativoPool);
      if (estado === "en_pool") {
        onSuccess("Ya está en la ruta.");
        handleClose();
        return;
      }
      await createRutaPoolDia({
        origen_tipo: "INICIADOR",
        iniciador_ruta_id: iniciadorId,
        fecha,
        ruta_trabajo_id: rutaId ? Number(rutaId) : undefined,
      });
      onSuccess("Agregado a la ruta.");
      handleClose();
    } catch (err) {
      onError(parseApiError(err, "No se pudo agregar a la ruta.").message);
    } finally {
      setSubmitting(false);
    }
  }, [iniciadorId, fecha, rutaId, estadoOperativoPool, onSuccess, handleClose, onError]);

  const handleAgregarAGrupo = useCallback(async () => {
    if (iniciadorId == null) {
      onError("No se encontró el iniciador de la fila.");
      return;
    }
    if (!rutaId) {
      onError("Seleccioná o creá una ruta borrador.");
      return;
    }
    if (!grupoId) {
      onError("Seleccioná o creá un grupo.");
      return;
    }
    setSubmitting(true);
    let poolCreated = false;
    try {
      const poolId = await resolverPoolId(iniciadorId, fecha, estadoOperativoPool);
      poolCreated = normalizarEstadoOperativoPool(estadoOperativoPool) === "pendiente";
      await agregarDesdePoolRuta(Number(rutaId), {
        pool_ids: [poolId],
        grupo_id: Number(grupoId),
      });
      onSuccess("Agregado al grupo de la ruta.");
      handleClose();
    } catch (err) {
      if (poolCreated) {
        onError("Se agregó a la ruta, pero no se pudo asignar al grupo.");
      } else {
        onError(parseApiError(err, "No se pudo agregar al grupo.").message);
      }
    } finally {
      setSubmitting(false);
    }
  }, [iniciadorId, fecha, estadoOperativoPool, rutaId, grupoId, onSuccess, handleClose, onError]);

  return (
    <CrudGlassDialog
      open={open}
      onClose={handleClose}
      onCloseButtonClick={handleClose}
      maxWidth="md"
      title={
        <CrudDialogHeader
          domainChip="Ruta de trabajo"
          titulo={OPER_RUTA_LABELS.MODAL_TITULO}
          subtitulo="Elegí fecha, turno y ruta para planificar el pendiente"
        />
      }
      actions={
        modoGrupo && grupoId ? (
          <CrudDialogActions
            mode="edit"
            onSave={() => void handleAgregarAGrupo()}
            loading={submitting}
            saveLabel={OPER_RUTA_LABELS.CONFIRMAR_GRUPO}
          />
        ) : undefined
      }
    >
      <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
        <DocumentalCrudSection title="Planificación" layout="stack">
          <CrudFormSlot label="Fecha" mode="edit" required>
            <AppTextField
              appearance="glass"
              label="Fecha"
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              InputLabelProps={{ shrink: true }}
              fullWidth
              data-testid="oper-ruta-fecha"
            />
          </CrudFormSlot>
          <CrudFormSlot label="Turno" mode="edit" required>
            <AppSelect
              appearance="glass"
              label="Turno"
              value={turno}
              onChange={(e) => setTurno(e.target.value as RutaTurno)}
              options={[
                { value: "MANIANA", label: "Mañana" },
                { value: "TARDE", label: "Tarde" },
              ]}
              fullWidth
            />
          </CrudFormSlot>

          {loadingRutas ? (
            <Stack direction="row" alignItems="center" spacing={1}>
              <CircularProgress size={20} />
              <Typography variant="body2">Cargando rutas…</Typography>
            </Stack>
          ) : sinRutas ? (
            <Stack spacing={1.25}>
              <Typography variant="body2" data-testid="oper-ruta-sin-ruta">
                No hay ruta borrador para esta fecha y turno. ¿Deseás crear una ruta nueva?
              </Typography>
              <AppButton
                dsVariant="primary"
                dsSize="sm"
                onClick={() => void handleCrearRuta()}
                disabled={creatingRuta}
              >
                {creatingRuta ? "Creando…" : OPER_RUTA_LABELS.CREAR_RUTA}
              </AppButton>
            </Stack>
          ) : (
            <CrudFormSlot label="Ruta" mode="edit" required>
              <AppSelect
                appearance="glass"
                label="Ruta"
                value={rutaId}
                onChange={(e) => setRutaId(String(e.target.value))}
                options={rutaOptions}
                fullWidth
              />
            </CrudFormSlot>
          )}
        </DocumentalCrudSection>

        {listoParaAcciones ? (
          <DocumentalCrudSection title="Acciones" layout="stack">
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1} useFlexGap flexWrap="wrap">
              <AppButton
                dsVariant="primary"
                dsSize="sm"
                onClick={() => void handleSoloPool()}
                disabled={submitting}
                data-testid="oper-ruta-solo-pool"
              >
                {submitting ? "Agregando…" : OPER_RUTA_LABELS.AGREGAR_SOLO_A_LA_RUTA}
              </AppButton>
              <AppButton
                dsVariant="primary"
                dsSize="sm"
                onClick={() => setModoGrupo((v) => !v)}
                disabled={submitting}
                data-testid="oper-ruta-modo-grupo"
              >
                {OPER_RUTA_LABELS.AGREGAR_A_GRUPO}
              </AppButton>
            </Stack>
          </DocumentalCrudSection>
        ) : null}

        {modoGrupo && Boolean(rutaId) ? (
          <DocumentalCrudSection title="Grupo" layout="stack">
            {loadingGrupos ? (
              <Stack direction="row" alignItems="center" spacing={1}>
                <CircularProgress size={20} />
                <Typography variant="body2">Cargando grupos…</Typography>
              </Stack>
            ) : grupos.length === 0 ? (
              <Stack spacing={1.25}>
                <Typography variant="body2">
                  La ruta no tiene grupos. Creá uno para asignar el pendiente.
                </Typography>
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  onClick={() => void handleCrearGrupo()}
                  disabled={creatingGrupo}
                >
                  {creatingGrupo ? "Creando…" : OPER_RUTA_LABELS.CREAR_GRUPO}
                </AppButton>
              </Stack>
            ) : (
              <Stack spacing={1.25}>
                <CrudFormSlot label="Grupo" mode="edit" required>
                  <AppSelect
                    appearance="glass"
                    label="Grupo"
                    value={grupoId}
                    onChange={(e) => setGrupoId(String(e.target.value))}
                    options={grupoOptions}
                    fullWidth
                  />
                </CrudFormSlot>
                <AppButton
                  dsVariant="secondary"
                  dsSize="sm"
                  onClick={() => void handleCrearGrupo()}
                  disabled={creatingGrupo}
                >
                  {creatingGrupo ? "Creando…" : OPER_RUTA_LABELS.CREAR_GRUPO_NUEVO}
                </AppButton>
              </Stack>
            )}
          </DocumentalCrudSection>
        ) : null}
      </Stack>
    </CrudGlassDialog>
  );
}
