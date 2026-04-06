import {
  Box,
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
import PanelGruposRuta from "../Components/PanelGruposRuta";
import ResumenRutaTrabajo from "../Components/ResumenRutaTrabajo";
import TablaIniciadoresPendientes, {
  type AsignacionPoolFilters,
  type TablaIniciadoresPendientesProps,
} from "../Components/TablaIniciadoresPendientes";
import { rutasInstitutionalDividerSx, rutasInstitutionalPanelPaperSx } from "../styles/institutionalVisual";

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
        Pool del día no cargado en esta sesión
      </Typography>
      {poolVacioSinItems ? (
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 420, mx: "auto", lineHeight: 1.55, mb: 2 }}>
          No hay ítems en el pool ni trabajos en la ruta. Suele pasar si abriste Asignación directo o recargaste la página
          (el pool vive en memoria hasta asignarlo a grupos). Volvé a Planificación y armá el pool del día.
        </Typography>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 440, mx: "auto", lineHeight: 1.55, mb: 2 }}>
          El navegador no tiene el pool (por ejemplo tras un F5), pero a la derecha podés seguir viendo grupos e ítems ya
          guardados en el borrador. Podés sincronizar con el servidor o volver a Planificación para armar de nuevo el
          pool.
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
          Si los grupos ya tienen trabajos asignados, usá &quot;Continuar a mapa final&quot; (arriba) para revisar el mapa;
          no necesitás el pool en pantalla para avanzar.
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
 * Etapa Asignación: ítems del pool del día y reparto entre grupos (sin universo global ni catálogo de calles).
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

  const sectionTitleSx = { mb: 1, fontWeight: 700, letterSpacing: "0.01em" } as const;
  const sectionCaptionSx = { display: "block", mb: 1.5, lineHeight: 1.45 } as const;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      <ResumenRutaTrabajo ruta={ruta} grupos={grupos} itemsCount={itemsCount} />

      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "center" }}
        sx={{ flexWrap: "wrap", rowGap: 1 }}
      >
        <AppButton dsVariant="ghost" dsSize="sm" onClick={onVolverPlanificacion} sx={{ alignSelf: { xs: "stretch", sm: "auto" } }}>
          Volver a planificación
        </AppButton>
        <Tooltip
          title={
            hayTrabajoParaMapa
              ? "Avanzar al mapa operativo de la ruta."
              : "Agregá iniciadores al pool en Planificación o sincronizá el borrador si ya hay ítems en grupos."
          }
        >
          <Box sx={{ display: "flex", justifyContent: { xs: "stretch", sm: "flex-end" }, width: { xs: "100%", sm: "auto" } }}>
            <AppButton
              dsVariant="primary"
              dsSize="md"
              onClick={onContinuarMapaFinal}
              disabled={!hayTrabajoParaMapa}
              sx={{ width: { xs: "100%", sm: "auto" } }}
            >
              Continuar a mapa final
            </AppButton>
          </Box>
        </Tooltip>
      </Stack>

      <Divider sx={rutasInstitutionalDividerSx} />

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
            <Typography variant="subtitle1" sx={sectionTitleSx}>
              Ítems del pool del día
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={sectionCaptionSx}>
              Mismo pool que armaste en Planificación: asigná estos trabajos a grupos y completá inspectores u OT en el
              panel derecho.
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
            <Typography variant="subtitle1" sx={sectionTitleSx}>
              Grupos
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={sectionCaptionSx}>
              Equipos de la ruta: inspectores, trabajos asignados y orden de trabajo por ítem.
            </Typography>
            <AppButton
              dsVariant="secondary"
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
