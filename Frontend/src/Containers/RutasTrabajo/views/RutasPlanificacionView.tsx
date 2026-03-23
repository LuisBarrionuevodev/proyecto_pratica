import { Box, CircularProgress, Grid, Paper, Typography } from "@mui/material";
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
  type IniciadoresPendientesFilters,
} from "../Components/TablaIniciadoresPendientes";
import { rutasInstitutionalPanelPaperSx } from "../styles/institutionalVisual";

export type RutasPlanificacionFilters = IniciadoresPendientesFilters;

export type RutasPlanificacionViewProps = {
  ruta: IRutaTrabajo;
  grupos: IRutaGrupoMin[];
  itemsActivos: IRutaItemMin[];
  itemsCount: number;
  iniciadores: IRutaIniciadorPendienteRow[];
  iniciadoresMeta: { total: number; page: number; perPage: number };
  selectedIniciadorIds: number[];
  filters: RutasPlanificacionFilters;
  /** Solo carga inicial / refresco explícito del detail; no usar para PATCH de ítem. */
  detailLoading: boolean;
  loadingPendientes: boolean;
  canCreateGrupo: boolean;
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  onChangeFilters: (next: RutasPlanificacionFilters) => void;
  /** Tabla de pendientes visible (tras interactuar con catálogos). */
  pendientesTablaVisible: boolean;
  onRefrescarPendientes: () => void;
  onPageChange: (nextPage: number) => void;
  onPerPageChange: (nextPerPage: number) => void;
  onSelectionChange: (ids: number[]) => void;
  onAssignSelected: () => void;
  onOpenCrearGrupo: () => void;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => void | Promise<void>;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
  onGuardarOtItem: (item: IRutaItemMin, numeroOt: string) => boolean | Promise<boolean>;
};

/**
 * Composición de la planificación TABLA: resumen + iniciadores pendientes + grupos.
 * Sin lógica de negocio; el contenedor orquesta estado y handlers.
 */
export function RutasPlanificacionView({
  ruta,
  grupos,
  itemsActivos,
  itemsCount,
  iniciadores,
  iniciadoresMeta,
  selectedIniciadorIds,
  filters,
  detailLoading,
  loadingPendientes,
  canCreateGrupo,
  iniciadorById,
  onChangeFilters,
  pendientesTablaVisible,
  onRefrescarPendientes,
  onPageChange,
  onPerPageChange,
  onSelectionChange,
  onAssignSelected,
  onOpenCrearGrupo,
  onEditarInspectores,
  onEliminarGrupo,
  onMoverItem,
  onQuitarItem,
  onGuardarOtItem,
}: RutasPlanificacionViewProps) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.2 }}>
      <ResumenRutaTrabajo ruta={ruta} grupos={grupos} itemsCount={itemsCount} />
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Iniciadores pendientes
            </Typography>
            <TablaIniciadoresPendientes
              tablaVisible={pendientesTablaVisible}
              rows={iniciadores}
              total={iniciadoresMeta.total}
              page={iniciadoresMeta.page}
              perPage={iniciadoresMeta.perPage}
              loading={loadingPendientes}
              selectedIds={selectedIniciadorIds}
              filters={filters}
              onChangeFilters={onChangeFilters}
              onRefrescar={onRefrescarPendientes}
              onPageChange={onPageChange}
              onPerPageChange={onPerPageChange}
              onSelectionChange={onSelectionChange}
              onAssignSelected={onAssignSelected}
            />
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
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
