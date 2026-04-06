import { Box, CircularProgress, Grid, Paper, Stack, Tooltip, Typography } from "@mui/material";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import type {
  IRutaGrupoMin,
  IRutaIniciadorPendienteRow,
  IRutaItemMin,
  IRutaTrabajo,
} from "../../../api/rutasTrabajoApi";
import PanelGruposRuta from "../Components/PanelGruposRuta";
import ResumenRutaTrabajo from "../Components/ResumenRutaTrabajo";
import TablaIniciadoresPendientes, {
  type AsignacionPoolFilters,
  type TablaIniciadoresPendientesProps,
} from "../Components/TablaIniciadoresPendientes";
import { rutasInstitutionalPanelPaperSx } from "../styles/institutionalVisual";

export type RutasPlanificacionFilters = AsignacionPoolFilters;

type AsignacionPoolEmptyStateProps = {
  poolVacioSinItems: boolean;
  poolVacioConItemsEnRuta: boolean;
  onVolverPlanificacion: () => void;
  onSincronizarDetalle: () => void;
  detailLoading: boolean;
};

/**
 * Sin pool en memoria (p. ej. F5 o acceso directo a Asignación): guía al usuario sin hablar de universo global.
 */
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
        py: 3,
        px: 2,
        borderRadius: 2,
        border: `1px dashed ${GLASS_COLORS.borderMedium}`,
        bgcolor: "rgba(0,0,0,0.18)",
        textAlign: "center",
      }}
    >
      <Inventory2OutlinedIcon sx={{ fontSize: 40, color: GLASS_COLORS.primary, opacity: 0.9, mb: 1 }} aria-hidden />
      <Typography sx={{ fontWeight: 700, fontSize: "1rem", mb: 1, color: GLASS_COLORS.textPrimary }}>
        Pool del día no disponible en esta sesión
      </Typography>
      {poolVacioSinItems ? (
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 420, mx: "auto", lineHeight: 1.55, mb: 2 }}>
          No hay iniciadores en el pool ni ítems cargados en la ruta. Suele pasar si entraste directo a Asignación o
          recargaste la página (el pool vive en memoria hasta asignar). Volvé a Planificación y armá el pool del día.
        </Typography>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 440, mx: "auto", lineHeight: 1.55, mb: 2 }}>
          El pool no está cargado en el navegador (por ejemplo tras un F5), pero podés tener ítems ya asignados en
          grupos a la derecha. Podés sincronizar el borrador con el servidor o volver a Planificación para volver a armar
          el pool.
        </Typography>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} justifyContent="center" alignItems="center">
        <AppButton dsVariant="primary" dsSize="sm" onClick={onVolverPlanificacion}>
          Ir a planificación
        </AppButton>
        <AppButton
          dsVariant="secondary"
          dsSize="sm"
          disabled={detailLoading}
          onClick={() => onSincronizarDetalle()}
        >
          {detailLoading ? "Sincronizando…" : "Sincronizar borrador"}
        </AppButton>
      </Stack>
      {poolVacioConItemsEnRuta ? (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2, lineHeight: 1.45 }}>
          Si ya tenés ítems en grupos, podés usar &quot;Continuar a mapa final&quot; arriba.
        </Typography>
      ) : null}
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
  selectedIniciadorIds: number[];
  assignedIniciadorIds: Set<number>;
  filters: RutasPlanificacionFilters;
  /** Solo carga inicial / refresco explícito del detail; no usar para PATCH de ítem. */
  detailLoading: boolean;
  canCreateGrupo: boolean;
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  onChangeFilters: (next: RutasPlanificacionFilters) => void;
  onSincronizarDetalle: () => void;
  distritoFilterOptions: TablaIniciadoresPendientesProps["distritoOptions"];
  onSelectionChange: (ids: number[]) => void;
  onAssignSelected: () => void;
  onOpenCrearGrupo: () => void;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => void | Promise<void>;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
  onGuardarOtItem: (item: IRutaItemMin, numeroOt: string) => boolean | Promise<boolean>;
  onContinuarMapaFinal: () => void;
  onVolverPlanificacion: () => void;
};

/**
 * Etapa Asignación: listado del pool del día y reparto entre grupos (sin universo global ni catálogo de calles).
 */
export function RutasPlanificacionView({
  ruta,
  grupos,
  itemsActivos,
  itemsCount,
  iniciadoresTabla,
  totalEnPool,
  selectedIniciadorIds,
  assignedIniciadorIds,
  filters,
  detailLoading,
  canCreateGrupo,
  iniciadorById,
  onChangeFilters,
  onSincronizarDetalle,
  distritoFilterOptions,
  onSelectionChange,
  onAssignSelected,
  onOpenCrearGrupo,
  onEditarInspectores,
  onEliminarGrupo,
  onMoverItem,
  onQuitarItem,
  onGuardarOtItem,
  onContinuarMapaFinal,
  onVolverPlanificacion,
}: RutasPlanificacionViewProps) {
  const hayTrabajoParaMapa = totalEnPool > 0 || itemsCount > 0;
  const poolVacioSinItems = totalEnPool === 0 && itemsCount === 0;
  const poolVacioConItemsEnRuta = totalEnPool === 0 && itemsCount > 0;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.2 }}>
      <ResumenRutaTrabajo ruta={ruta} grupos={grupos} itemsCount={itemsCount} />
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        justifyContent="flex-end"
        alignItems={{ xs: "stretch", sm: "center" }}
      >
        <AppButton dsVariant="ghost" dsSize="sm" onClick={onVolverPlanificacion}>
          Volver a planificación
        </AppButton>
        <Tooltip
          title={
            hayTrabajoParaMapa
              ? "Avanzar al mapa operativo de la ruta."
              : "Agregá iniciadores al pool en Planificación o sincronizá si ya hay ítems en grupos."
          }
        >
          <span>
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              onClick={onContinuarMapaFinal}
              disabled={!hayTrabajoParaMapa}
            >
              Continuar a mapa final
            </AppButton>
          </span>
        </Tooltip>
      </Stack>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
            <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>
              Listado del pool del día
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5, lineHeight: 1.45 }}>
              Iniciadores que sumaste al pool en Planificación (no es un listado global de pendientes). Asignalos a
              grupos y completá inspectores u OT en el panel derecho.
            </Typography>
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
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
            <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>
              Grupos
            </Typography>
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              disabled={!canCreateGrupo}
              onClick={onOpenCrearGrupo}
              sx={{ mb: 1.5 }}
            >
              + Nuevo grupo
            </AppButton>
            {detailLoading ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress />
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
      </Grid>
    </Box>
  );
}
