import { memo, useCallback, useMemo, useRef, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  Divider,
  Grid,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import type {
  IRutaGrupoMin,
  IRutaIniciadorPendienteRow,
  IRutaItemMin,
  IRutaTrabajo,
} from "../../../api/rutasTrabajoApi";
import ModalAsignarSeleccionAGrupo from "../Components/ModalAsignarSeleccionAGrupo";
import PanelGruposRuta from "../Components/PanelGruposRuta";
import ResumenRutaTrabajo from "../Components/ResumenRutaTrabajo";
import TablaIniciadoresPendientes, {
  type AsignacionPoolFilters,
  type TablaIniciadoresPendientesProps,
} from "../Components/TablaIniciadoresPendientes";
import {
  planificacionPanelTitleSx,
  rutasAsignacionNeutralContainedButtonSx,
  rutasInstitutionalDividerSx,
  rutasInstitutionalPanelPaperSx,
} from "../styles/institutionalVisual";

export type RutasPlanificacionFilters = AsignacionPoolFilters;

type AsignacionPoolEmptyStateProps = {
  poolVacioSinItems: boolean;
  poolVacioConItemsEnRuta: boolean;
  onVolverPlanificacion: () => void;
  onSincronizarDetalle: () => void;
  detailLoading: boolean;
};

/** Pool vacío en memoria (p. ej. F5): mensaje mínimo + acciones. */
function AsignacionPoolEmptyState({
  poolVacioSinItems,
  poolVacioConItemsEnRuta,
  onVolverPlanificacion,
  onSincronizarDetalle,
  detailLoading,
}: AsignacionPoolEmptyStateProps) {
  return (
    <Box
      sx={{
        py: 2.5,
        px: 2,
        borderRadius: 2,
        border: `1px dashed ${GLASS_COLORS.borderMedium}`,
        bgcolor: "rgba(0,0,0,0.18)",
        textAlign: "center",
      }}
    >
      <Inventory2OutlinedIcon sx={{ fontSize: 36, color: GLASS_COLORS.primary, opacity: 0.85, mb: 0.75 }} aria-hidden />
      <Typography sx={{ ...planificacionPanelTitleSx, fontSize: "0.9375rem", mb: 1, display: "block" }}>
        Pool no disponible en esta sesión
      </Typography>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ maxWidth: 360, mx: "auto", lineHeight: 1.45, mb: 2, fontSize: "0.8125rem" }}
      >
        {poolVacioSinItems
          ? "Ir a Planificación para armar el pool."
          : poolVacioConItemsEnRuta
            ? "Sincronizar o volver a Planificación. Los grupos siguen a la derecha."
            : null}
      </Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} justifyContent="center" alignItems="center">
        <AppButton dsVariant="primary" dsSize="sm" onClick={onVolverPlanificacion}>
          Ir a planificación
        </AppButton>
        <Button
          variant="contained"
          size="small"
          disableElevation
          disabled={detailLoading}
          onClick={() => onSincronizarDetalle()}
          sx={rutasAsignacionNeutralContainedButtonSx}
        >
          {detailLoading ? "Sincronizando…" : "Sincronizar borrador"}
        </Button>
      </Stack>
    </Box>
  );
}

export type RutasPlanificacionViewProps = {
  ruta: IRutaTrabajo;
  grupos: IRutaGrupoMin[];
  itemsActivos: IRutaItemMin[];
  itemsCount: number;
  /** Filas del pool del día (orden fijo), ya filtradas para la tabla. */
  iniciadoresTabla: IRutaIniciadorPendienteRow[];
  totalEnPool: number;
  assignedIniciadorIds: Set<number>;
  filters: RutasPlanificacionFilters;
  /** Solo carga inicial / refresco explícito del detail; no usar para PATCH de ítem. */
  detailLoading: boolean;
  canCreateGrupo: boolean;
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  onChangeFilters: (next: RutasPlanificacionFilters) => void;
  onSincronizarDetalle: () => void;
  distritoFilterOptions: TablaIniciadoresPendientesProps["distritoOptions"];
  onOpenCrearGrupo: () => void;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => void | Promise<void>;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
  onGuardarOtItem: (item: IRutaItemMin, numeroOt: string) => boolean | Promise<boolean>;
  onContinuarMapaFinal: () => void;
  onVolverPlanificacion: () => void;
  onAssignIniciadoresToGrupo: (grupoId: number, iniciadorIds: number[]) => Promise<boolean>;
};

type AsignacionTopSectionProps = {
  ruta: IRutaTrabajo;
  grupos: IRutaGrupoMin[];
  itemsCount: number;
  itemsSinOtCount: number;
  hayTrabajoParaMapa: boolean;
  puedeContinuarAMapaFinal: boolean;
  continuarMapaFinalTooltip: string;
  onVolverPlanificacion: () => void;
  onContinuarMapaFinal: () => void;
};

/** Resumen + barra de acciones: no depende de la selección del pool. */
const AsignacionTopSection = memo(function AsignacionTopSection({
  ruta,
  grupos,
  itemsCount,
  itemsSinOtCount,
  hayTrabajoParaMapa,
  puedeContinuarAMapaFinal,
  continuarMapaFinalTooltip,
  onVolverPlanificacion,
  onContinuarMapaFinal,
}: AsignacionTopSectionProps) {
  return (
    <>
      <ResumenRutaTrabajo ruta={ruta} grupos={grupos} itemsCount={itemsCount} />

      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "center" }}
        sx={{ flexWrap: "wrap", rowGap: 1 }}
      >
        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={onVolverPlanificacion}
          sx={{ alignSelf: { xs: "stretch", sm: "auto" } }}
        >
          Volver a planificación
        </AppButton>
        <Stack
          spacing={0.5}
          alignItems={{ xs: "stretch", sm: "flex-end" }}
          sx={{ width: { xs: "100%", sm: "auto" } }}
        >
          <Tooltip title={continuarMapaFinalTooltip}>
            <Box
              sx={{ display: "flex", justifyContent: { xs: "stretch", sm: "flex-end" }, width: { xs: "100%", sm: "auto" } }}
            >
              <AppButton
                dsVariant="primary"
                dsSize="md"
                onClick={onContinuarMapaFinal}
                disabled={!puedeContinuarAMapaFinal}
                sx={{ width: { xs: "100%", sm: "auto" } }}
              >
                Continuar a mapa final
              </AppButton>
            </Box>
          </Tooltip>
          {itemsSinOtCount > 0 ? (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                display: "block",
                lineHeight: 1.4,
                textAlign: { xs: "left", sm: "right" },
                maxWidth: 280,
                fontSize: "0.7rem",
              }}
            >
              {itemsSinOtCount} ítem{itemsSinOtCount === 1 ? "" : "s"} sin OT guardada.
            </Typography>
          ) : null}
        </Stack>
      </Stack>

      <Divider sx={rutasInstitutionalDividerSx} />
    </>
  );
});

type AsignacionPoolColumnProps = {
  totalEnPool: number;
  poolVacioSinItems: boolean;
  poolVacioConItemsEnRuta: boolean;
  iniciadoresTabla: IRutaIniciadorPendienteRow[];
  selectedIniciadorIds: number[];
  assignedIniciadorIds: Set<number>;
  filters: RutasPlanificacionFilters;
  onChangeFilters: (next: AsignacionPoolFilters) => void;
  onSelectionChange: (ids: number[]) => void;
  onAssignSelected: () => void;
  distritoFilterOptions: TablaIniciadoresPendientesProps["distritoOptions"];
  onSincronizarDetalle: () => void;
  detailLoading: boolean;
  onVolverPlanificacion: () => void;
};

const AsignacionPoolColumn = memo(function AsignacionPoolColumn({
  totalEnPool,
  poolVacioSinItems,
  poolVacioConItemsEnRuta,
  iniciadoresTabla,
  selectedIniciadorIds,
  assignedIniciadorIds,
  filters,
  onChangeFilters,
  onSelectionChange,
  onAssignSelected,
  distritoFilterOptions,
  onSincronizarDetalle,
  detailLoading,
  onVolverPlanificacion,
}: AsignacionPoolColumnProps) {
  return (
    <Grid size={{ xs: 12, md: 7 }}>
      <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
        <Typography sx={{ ...planificacionPanelTitleSx, mb: 1 }}>Ítems del pool del día</Typography>
        {totalEnPool === 0 ? (
          <AsignacionPoolEmptyState
            poolVacioSinItems={poolVacioSinItems}
            poolVacioConItemsEnRuta={poolVacioConItemsEnRuta}
            onVolverPlanificacion={onVolverPlanificacion}
            onSincronizarDetalle={onSincronizarDetalle}
            detailLoading={detailLoading}
          />
        ) : (
          <TablaIniciadoresPendientes
            rows={iniciadoresTabla}
            totalEnPool={totalEnPool}
            selectedIds={selectedIniciadorIds}
            assignedIniciadorIds={assignedIniciadorIds}
            filters={filters}
            onChangeFilters={onChangeFilters}
            onSelectionChange={onSelectionChange}
            onAssignSelected={onAssignSelected}
            distritoOptions={distritoFilterOptions}
            onSincronizarDetalle={onSincronizarDetalle}
            detailLoading={detailLoading}
          />
        )}
      </Paper>
    </Grid>
  );
});

type AsignacionGruposColumnProps = {
  detailLoading: boolean;
  canCreateGrupo: boolean;
  onOpenCrearGrupo: () => void;
  grupos: IRutaGrupoMin[];
  itemsActivos: IRutaItemMin[];
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => void | Promise<void>;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
  onGuardarOtItem: (item: IRutaItemMin, numeroOt: string) => boolean | Promise<boolean>;
};

const AsignacionGruposColumn = memo(function AsignacionGruposColumn({
  detailLoading,
  canCreateGrupo,
  onOpenCrearGrupo,
  grupos,
  itemsActivos,
  iniciadorById,
  onEditarInspectores,
  onEliminarGrupo,
  onMoverItem,
  onQuitarItem,
  onGuardarOtItem,
}: AsignacionGruposColumnProps) {
  return (
    <Grid size={{ xs: 12, md: 5 }}>
      <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
        <Typography sx={{ ...planificacionPanelTitleSx, mb: 1 }}>Grupos</Typography>
        <Button
          variant="contained"
          size="small"
          disableElevation
          disabled={!canCreateGrupo}
          onClick={onOpenCrearGrupo}
          sx={[{ mb: 1.5 }, rutasAsignacionNeutralContainedButtonSx]}
        >
          + Nuevo grupo
        </Button>
        {detailLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={36} sx={{ color: GLASS_COLORS.primary }} />
          </Box>
        ) : (
          <PanelGruposRuta
            grupos={grupos}
            items={itemsActivos}
            iniciadorById={iniciadorById}
            onEditarInspectores={onEditarInspectores}
            onEliminarGrupo={onEliminarGrupo}
            onMoverItem={onMoverItem}
            onQuitarItem={onQuitarItem}
            onGuardarOtItem={onGuardarOtItem}
          />
        )}
      </Paper>
    </Grid>
  );
});

/**
 * Etapa Asignación: ítems del pool del día y reparto entre grupos (sin universo global ni catálogo de calles).
 * La selección del pool vive aquí para no re-renderizar `RutasTrabajo` ni la columna de grupos en cada click.
 */
function RutasPlanificacionView({
  ruta,
  grupos,
  itemsActivos,
  itemsCount,
  iniciadoresTabla,
  totalEnPool,
  assignedIniciadorIds,
  filters,
  detailLoading,
  canCreateGrupo,
  iniciadorById,
  onChangeFilters,
  onSincronizarDetalle,
  distritoFilterOptions,
  onOpenCrearGrupo,
  onEditarInspectores,
  onEliminarGrupo,
  onMoverItem,
  onQuitarItem,
  onGuardarOtItem,
  onContinuarMapaFinal,
  onVolverPlanificacion,
  onAssignIniciadoresToGrupo,
}: RutasPlanificacionViewProps) {
  const [selectedIniciadorIds, setSelectedIniciadorIds] = useState<number[]>([]);
  const [openAsignarGrupo, setOpenAsignarGrupo] = useState(false);
  const selectedIniciadorIdsRef = useRef<number[]>([]);
  selectedIniciadorIdsRef.current = selectedIniciadorIds;

  const hayTrabajoParaMapa = totalEnPool > 0 || itemsCount > 0;
  const poolVacioSinItems = totalEnPool === 0 && itemsCount === 0;
  const poolVacioConItemsEnRuta = totalEnPool === 0 && itemsCount > 0;

  const itemsSinOt = useMemo(
    () => itemsActivos.filter((it) => it.orden_trabajo_id == null),
    [itemsActivos]
  );
  const puedeContinuarAMapaFinal =
    hayTrabajoParaMapa && (itemsActivos.length === 0 || itemsSinOt.length === 0);

  const continuarMapaFinalTooltip = useMemo(() => {
    if (!hayTrabajoParaMapa) {
      return "Sin ítems en pool ni en la ruta.";
    }
    if (itemsActivos.length > 0 && itemsSinOt.length > 0) {
      return "Guardá la OT en cada ítem antes de continuar.";
    }
    return "Mapa operativo.";
  }, [hayTrabajoParaMapa, itemsActivos.length, itemsSinOt.length]);

  const handleChangeFilters = useCallback(
    (next: AsignacionPoolFilters) => {
      onChangeFilters(next);
      setSelectedIniciadorIds([]);
    },
    [onChangeFilters]
  );

  const handleOpenAssignModal = useCallback(() => setOpenAsignarGrupo(true), []);

  const handleCloseAssignModal = useCallback(() => setOpenAsignarGrupo(false), []);

  /** Ref evita que `onConfirm` del modal cambie en cada tick de selección (memo del modal aprovecha). */
  const handleModalConfirm = useCallback(
    async (grupoId: number) => {
      const ok = await onAssignIniciadoresToGrupo(grupoId, selectedIniciadorIdsRef.current);
      if (ok) {
        setSelectedIniciadorIds([]);
        setOpenAsignarGrupo(false);
      }
    },
    [onAssignIniciadoresToGrupo]
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      <AsignacionTopSection
        ruta={ruta}
        grupos={grupos}
        itemsCount={itemsCount}
        itemsSinOtCount={itemsSinOt.length}
        hayTrabajoParaMapa={hayTrabajoParaMapa}
        puedeContinuarAMapaFinal={puedeContinuarAMapaFinal}
        continuarMapaFinalTooltip={continuarMapaFinalTooltip}
        onVolverPlanificacion={onVolverPlanificacion}
        onContinuarMapaFinal={onContinuarMapaFinal}
      />

      <Grid container spacing={2.5}>
        <AsignacionPoolColumn
          totalEnPool={totalEnPool}
          poolVacioSinItems={poolVacioSinItems}
          poolVacioConItemsEnRuta={poolVacioConItemsEnRuta}
          iniciadoresTabla={iniciadoresTabla}
          selectedIniciadorIds={selectedIniciadorIds}
          assignedIniciadorIds={assignedIniciadorIds}
          filters={filters}
          onChangeFilters={handleChangeFilters}
          onSelectionChange={setSelectedIniciadorIds}
          onAssignSelected={handleOpenAssignModal}
          distritoFilterOptions={distritoFilterOptions}
          onSincronizarDetalle={onSincronizarDetalle}
          detailLoading={detailLoading}
          onVolverPlanificacion={onVolverPlanificacion}
        />
        <AsignacionGruposColumn
          detailLoading={detailLoading}
          canCreateGrupo={canCreateGrupo}
          onOpenCrearGrupo={onOpenCrearGrupo}
          grupos={grupos}
          itemsActivos={itemsActivos}
          iniciadorById={iniciadorById}
          onEditarInspectores={onEditarInspectores}
          onEliminarGrupo={onEliminarGrupo}
          onMoverItem={onMoverItem}
          onQuitarItem={onQuitarItem}
          onGuardarOtItem={onGuardarOtItem}
        />
      </Grid>

      <ModalAsignarSeleccionAGrupo
        open={openAsignarGrupo}
        onClose={handleCloseAssignModal}
        grupos={grupos}
        selectedCount={selectedIniciadorIds.length}
        onConfirm={handleModalConfirm}
      />
    </Box>
  );
}

const RutasPlanificacionViewMemo = memo(RutasPlanificacionView);
export { RutasPlanificacionViewMemo as RutasPlanificacionView };
