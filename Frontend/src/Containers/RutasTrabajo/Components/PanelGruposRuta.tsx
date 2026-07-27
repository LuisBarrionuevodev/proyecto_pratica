import { memo, useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import type {
  IRutaGrupoInspector,
  IRutaGrupoMin,
  IRutaIniciadorPendienteRow,
  IRutaItemMin,
} from "../../../api/rutasTrabajoApi";
import { AppButton } from "../../../ui";
import { MIN_INSPECTORES_POR_GRUPO_PUBLICAR } from "../utils/rutaPublicarReadiness";
import {
  asignacionItemOtTextFieldRootSx,
  asignacionItemRowNeutralButtonSx,
  rutasAsignacionNeutralContainedButtonSx,
  rutasInstitutionalDividerSx,
  rutasInstitutionalGrupoPaperSx,
  rutasInstitutionalItemPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";
import {
  distritoOperativoDesdeItemYPool,
  etiquetaDomicilioDesdeItemYPool,
  rubroOperativoDesdeItemYPool,
  tipoEtiquetaDesdeItemYPool,
} from "../utils/rutaItemOperativoDesdeItemYPool";
import type { GuardarOtItemResult } from "../hooks/useRutaTrabajoBorradorActions";

interface Props {
  grupos: IRutaGrupoMin[];
  items: IRutaItemMin[];
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => Promise<void>;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => Promise<void>;
  onGuardarOtItem: (item: IRutaItemMin, numeroOt: string) => GuardarOtItemResult | Promise<GuardarOtItemResult>;
}

type OtUiKind = "sin_guardar" | "pendiente_guardar" | "guardada";

function otUiState(
  item: IRutaItemMin,
  draftRaw: string
): { kind: OtUiKind; chipLabel: string; chipColor: "default" | "warning" | "success"; helperText: string } {
  const persisted = (item.orden_trabajo?.numero_acta ?? "").trim();
  const draft = draftRaw.trim();
  const hasPersistedId = item.orden_trabajo_id != null;

  if (hasPersistedId && draft === persisted) {
    return {
      kind: "guardada",
      chipLabel: "OT guardada",
      chipColor: "success",
      helperText: "Guardada en servidor.",
    };
  }
  if (draft !== persisted) {
    return {
      kind: "pendiente_guardar",
      chipLabel: "OT pendiente de guardar",
      chipColor: "warning",
      helperText: "Confirmar con «Guardar OT».",
    };
  }
  return {
    kind: "sin_guardar",
    chipLabel: "OT no guardada",
    chipColor: "default",
    helperText: "Solo números. Requiere guardar para continuar.",
  };
}

const OT_FIELD_SX = {
  width: { xs: "100%", sm: 168 },
  minWidth: 0,
  ...asignacionItemOtTextFieldRootSx,
} as const;

const MOVER_A_FIELD_SX = {
  ...asignacionItemOtTextFieldRootSx,
} as const;

const OT_FORM_HELPER_PROPS = { sx: { maxWidth: 320, m: 0, mt: 0.5 } } as const;

/** Nombre o legajo; sin IDs en UI operativa. */
function etiquetaInspectorEnLinea(ins: IRutaGrupoInspector): string {
  const nom = ins.inspector_nombre?.trim();
  if (nom) return nom;
  const leg = ins.inspector_legajo?.trim();
  if (leg) return `Leg. ${leg}`;
  return "Inspector";
}

type RutaGrupoItemRowProps = {
  item: IRutaItemMin;
  iniciador: IRutaIniciadorPendienteRow | undefined;
  otDraft: string;
  target: number | "";
  savingThis: boolean;
  canMove: boolean;
  moveTargets: IRutaGrupoMin[];
  onOtDraftChange: (itemId: number, value: string) => void;
  onMoveTargetChange: (itemId: number, value: number | "") => void;
  onGuardarOt: (item: IRutaItemMin, otDraft: string) => void;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
  /** Error de guardado OT (p. ej. 409) mostrado bajo el campo en este ítem. */
  otInlineError?: string;
};

/**
 * Fila de ítem expandida: memoizada para no re-renderizar el resto de ítems al editar OT de uno solo.
 */
type GrupoRutaSectionProps = {
  grupo: IRutaGrupoMin;
  groupItems: IRutaItemMin[];
  expanded: boolean;
  moveTargets: IRutaGrupoMin[];
  canMove: boolean;
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  /** Solo borradores/targets de ítems de este grupo (comparación fina en memo). */
  otDraftForItem: Record<number, string>;
  targetForItem: Record<number, number | "">;
  /** `savingOtItemId` acotado a este grupo (evita re-render en otros grupos al guardar). */
  savingItemIdInSection: number | null;
  onToggleExpanded: (grupoId: number) => void;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => Promise<void>;
  onOtDraftChange: (itemId: number, value: string) => void;
  onMoveTargetChange: (itemId: number, value: number | "") => void;
  onGuardarOt: (item: IRutaItemMin, otDraft: string) => void;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
  /** Mensaje de error inline por ítem (conflicto OT, etc.). */
  otInlineErrorByItem: Record<number, string>;
};

function grupoRutaSectionPropsAreEqual(prev: GrupoRutaSectionProps, next: GrupoRutaSectionProps): boolean {
  if (prev.grupo !== next.grupo) return false;
  if (prev.groupItems !== next.groupItems) return false;
  if (prev.expanded !== next.expanded) return false;
  if (prev.moveTargets !== next.moveTargets) return false;
  if (prev.canMove !== next.canMove) return false;
  if (prev.iniciadorById !== next.iniciadorById) return false;
  if (prev.savingItemIdInSection !== next.savingItemIdInSection) return false;
  if (prev.onToggleExpanded !== next.onToggleExpanded) return false;
  if (prev.onEditarInspectores !== next.onEditarInspectores) return false;
  if (prev.onEliminarGrupo !== next.onEliminarGrupo) return false;
  if (prev.onOtDraftChange !== next.onOtDraftChange) return false;
  if (prev.onMoveTargetChange !== next.onMoveTargetChange) return false;
  if (prev.onGuardarOt !== next.onGuardarOt) return false;
  if (prev.onMoverItem !== next.onMoverItem) return false;
  if (prev.onQuitarItem !== next.onQuitarItem) return false;
  for (const it of prev.groupItems) {
    const id = it.id;
    if ((prev.otDraftForItem[id] ?? "") !== (next.otDraftForItem[id] ?? "")) return false;
    if ((prev.targetForItem[id] ?? "") !== (next.targetForItem[id] ?? "")) return false;
    if ((prev.otInlineErrorByItem[id] ?? "") !== (next.otInlineErrorByItem[id] ?? "")) return false;
  }
  return true;
}

/**
 * Un grupo del panel: memo con igualdad por ítem para no re-ejecutar cabecera/lista de otros grupos al tipear OT.
 */
const GrupoRutaSection = memo(function GrupoRutaSection({
  grupo,
  groupItems,
  expanded,
  moveTargets,
  canMove,
  iniciadorById,
  otDraftForItem,
  targetForItem,
  savingItemIdInSection,
  onToggleExpanded,
  onEditarInspectores,
  onEliminarGrupo,
  onOtDraftChange,
  onMoveTargetChange,
  onGuardarOt,
  onMoverItem,
  onQuitarItem,
  otInlineErrorByItem,
}: GrupoRutaSectionProps) {
  const accent = `hsl(${(grupo.id * 61) % 360} 75% 58%)`;

  return (
    <Paper elevation={0} sx={rutasInstitutionalGrupoPaperSx(accent)}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "center" }}
        spacing={1}
      >
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {grupo.nombre}
          </Typography>
          <Stack direction="row" spacing={0.75} sx={{ mt: 0.5 }}>
            <Chip size="small" label={`${groupItems.length} items`} color="primary" variant="outlined" />
            <Chip
              size="small"
              label={`${grupo.inspectores.length} inspectores`}
              variant="outlined"
              color={grupo.inspectores.length < MIN_INSPECTORES_POR_GRUPO_PUBLICAR ? "warning" : "default"}
            />
          </Stack>
        </Box>
        <Stack
          direction="row"
          spacing={0.75}
          flexWrap="wrap"
          useFlexGap
          justifyContent={{ xs: "flex-start", sm: "flex-end" }}
          alignItems="center"
        >
          <Button
            type="button"
            variant="contained"
            size="small"
            disableElevation
            onClick={() => onToggleExpanded(grupo.id)}
            sx={rutasAsignacionNeutralContainedButtonSx}
          >
            {expanded ? "Ocultar items" : "Gestionar items"}
          </Button>
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => onEditarInspectores(grupo)}>
            Inspectores
          </AppButton>
          <AppButton dsVariant="danger" dsSize="sm" onClick={() => void onEliminarGrupo(grupo)}>
            Eliminar
          </AppButton>
        </Stack>
      </Stack>
      <Divider sx={{ my: 1.2, ...rutasInstitutionalDividerSx }} />

      <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.4 }}>
        {grupo.inspectores.length > 0 ? grupo.inspectores.map((i) => etiquetaInspectorEnLinea(i)).join(", ") : "Sin inspectores"}
      </Typography>

      <Stack spacing={1} sx={{ mt: 1.5 }}>
        {groupItems.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            Sin items asignados.
          </Typography>
        ) : expanded ? (
          groupItems.map((item) => {
            const iniciador = iniciadorById[item.iniciador_ruta_id];
            const otDraft = otDraftForItem[item.id] ?? "";
            const target = targetForItem[item.id] ?? "";
            const savingThis = savingItemIdInSection === item.id;
            const otInlineError = otInlineErrorByItem[item.id];
            return (
              <RutaGrupoItemRow
                key={item.id}
                item={item}
                iniciador={iniciador}
                otDraft={otDraft}
                target={target}
                savingThis={savingThis}
                canMove={canMove}
                moveTargets={moveTargets}
                otInlineError={otInlineError}
                onOtDraftChange={onOtDraftChange}
                onMoveTargetChange={onMoveTargetChange}
                onGuardarOt={onGuardarOt}
                onMoverItem={onMoverItem}
                onQuitarItem={onQuitarItem}
              />
            );
          })
        ) : null}
      </Stack>
    </Paper>
  );
}, grupoRutaSectionPropsAreEqual);

const RutaGrupoItemRow = memo(function RutaGrupoItemRow({
  item,
  iniciador,
  otDraft,
  target,
  savingThis,
  canMove,
  moveTargets,
  otInlineError,
  onOtDraftChange,
  onMoveTargetChange,
  onGuardarOt,
  onMoverItem,
  onQuitarItem,
}: RutaGrupoItemRowProps) {
  const otUi = useMemo(() => otUiState(item, otDraft), [item, otDraft]);
  const puedeGuardarOt = otDraft.trim().length > 0 && !savingThis;
  const otErrorMsg = otInlineError?.trim() ?? "";
  const hasOtInlineError = Boolean(otErrorMsg);

  /** Snapshot del ítem (GET detail) primero; pool de planificación como enriquecimiento. */
  const direccion = etiquetaDomicilioDesdeItemYPool(item, iniciador);
  const rubro = rubroOperativoDesdeItemYPool(item, iniciador);
  const distritoNombre = distritoOperativoDesdeItemYPool(item, iniciador);
  const tipoLabel = tipoEtiquetaDesdeItemYPool(item, iniciador);

  return (
    <Paper elevation={0} sx={rutasInstitutionalItemPaperSx}>
      <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
        {direccion}
      </Typography>
      <Stack direction="row" spacing={0.7} sx={{ mt: 0.6 }} alignItems="center" flexWrap="wrap">
        <Typography variant="caption" color="text.secondary">
          {distritoNombre ? `${rubro} · ${distritoNombre}` : rubro}
        </Typography>
        <Chip label={tipoLabel} size="small" variant="outlined" />
        <Chip label={otUi.chipLabel} size="small" color={otUi.chipColor} variant="outlined" />
      </Stack>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        sx={{ mt: 0.8 }}
        alignItems={{ xs: "stretch", sm: "flex-start" }}
        flexWrap="wrap"
        useFlexGap
      >
        <Box
          sx={{
            width: { xs: "100%", sm: "auto" },
            minWidth: { sm: 168 },
            maxWidth: { sm: 220 },
            flex: { sm: "0 0 auto" },
          }}
        >
          <TextField
            fullWidth
            size="small"
            label="OT"
            value={otDraft}
            onChange={(e) => onOtDraftChange(item.id, e.target.value)}
            sx={OT_FIELD_SX}
            error={hasOtInlineError}
            helperText={hasOtInlineError ? otErrorMsg : otUi.helperText}
            FormHelperTextProps={{
              sx: {
                ...OT_FORM_HELPER_PROPS.sx,
                ...(hasOtInlineError
                  ? { color: "error.light", fontWeight: 600, fontFamily: '"Tactic Sans", sans-serif' }
                  : {}),
              },
            }}
          />
        </Box>
        <AppButton
          dsVariant="primary"
          dsSize="md"
          loading={savingThis}
          disabled={!puedeGuardarOt}
          onClick={() => onGuardarOt(item, otDraft)}
          sx={{ alignSelf: { xs: "stretch", sm: "flex-start" }, width: { xs: "100%", sm: "auto" }, flexShrink: 0 }}
        >
          {savingThis ? "Guardando…" : "Guardar OT"}
        </AppButton>
        <Box sx={{ width: { xs: "100%", sm: "auto" }, minWidth: { sm: 180 }, maxWidth: { sm: 280 }, flex: { sm: "0 0 auto" } }}>
          <TextField
            select
            fullWidth
            size="small"
            label="Mover a"
            value={target}
            onChange={(e) => {
              const val = e.target.value ? Number(e.target.value) : "";
              onMoveTargetChange(item.id, val);
            }}
            sx={MOVER_A_FIELD_SX}
            disabled={!canMove}
          >
            <MenuItem value="">Seleccionar</MenuItem>
            {moveTargets.map((g) => (
              <MenuItem key={g.id} value={g.id}>
                {g.nombre}
              </MenuItem>
            ))}
          </TextField>
        </Box>
        <Button
          type="button"
          variant="contained"
          size="medium"
          disableElevation
          onClick={() => {
            if (typeof target === "number") void onMoverItem(item, target);
          }}
          disabled={!canMove || typeof target !== "number"}
          sx={asignacionItemRowNeutralButtonSx}
        >
          Mover
        </Button>
        <AppButton
          dsVariant="danger"
          dsSize="md"
          onClick={() => void onQuitarItem(item)}
          sx={{ flexShrink: 0, width: { xs: "100%", sm: "auto" } }}
        >
          Quitar
        </AppButton>
      </Stack>
    </Paper>
  );
});

function PanelGruposRutaInner({
  grupos,
  items,
  iniciadorById,
  onEditarInspectores,
  onEliminarGrupo,
  onMoverItem,
  onQuitarItem,
  onGuardarOtItem,
}: Props) {
  const [targetByItem, setTargetByItem] = useState<Record<number, number | "">>({});
  const [expandedByGrupo, setExpandedByGrupo] = useState<Record<number, boolean>>({});
  const [otDraftByItem, setOtDraftByItem] = useState<Record<number, string>>({});
  const [savingOtItemId, setSavingOtItemId] = useState<number | null>(null);
  /** Conflicto OT u otro 409: mensaje por `item.id`, solo en la card del ítem. */
  const [otInlineErrorByItem, setOtInlineErrorByItem] = useState<Record<number, string>>({});

  useEffect(() => {
    const ids = new Set(items.filter((i) => !i.deleted_at).map((i) => i.id));
    setOtInlineErrorByItem((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const idStr of Object.keys(next)) {
        const id = Number(idStr);
        if (!ids.has(id)) {
          delete next[id];
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [items]);

  const itemsSinOtPersistida = useMemo(
    () => items.filter((i) => !i.deleted_at && i.orden_trabajo_id == null),
    [items]
  );

  /** Un solo paso O(n): evita `items.filter` por grupo en cada render. */
  const itemsByGrupoId = useMemo(() => {
    const m = new Map<number, IRutaItemMin[]>();
    for (const i of items) {
      if (i.deleted_at) continue;
      const list = m.get(i.ruta_grupo_id);
      if (list) list.push(i);
      else m.set(i.ruta_grupo_id, [i]);
    }
    return m;
  }, [items]);

  /** Lista de destino para el select «Mover a» por grupo (misma referencia mientras `grupos` no cambie). */
  const moveTargetsByGrupoId = useMemo(() => {
    const map = new Map<number, IRutaGrupoMin[]>();
    for (const g of grupos) {
      map.set(
        g.id,
        grupos.filter((x) => x.id !== g.id)
      );
    }
    return map;
  }, [grupos]);

  const canMove = grupos.length > 1;

  const handleOtDraftChange = useCallback((itemId: number, value: string) => {
    setOtInlineErrorByItem((prev) => {
      if (prev[itemId] == null) return prev;
      const next = { ...prev };
      delete next[itemId];
      return next;
    });
    setOtDraftByItem((prev) => ({ ...prev, [itemId]: value }));
  }, []);

  const handleMoveTargetChange = useCallback((itemId: number, value: number | "") => {
    setTargetByItem((prev) => ({ ...prev, [itemId]: value }));
  }, []);

  const handleGuardarOt = useCallback(
    (item: IRutaItemMin, otDraft: string) => {
      void (async () => {
        setSavingOtItemId(item.id);
        try {
          const result = await onGuardarOtItem(item, otDraft);
          if (result.ok) {
            setOtInlineErrorByItem((prev) => {
              if (prev[item.id] == null) return prev;
              const next = { ...prev };
              delete next[item.id];
              return next;
            });
            setOtDraftByItem((prev) => {
              const next = { ...prev };
              delete next[item.id];
              return next;
            });
          } else if (result.scope === "inline") {
            setOtInlineErrorByItem((prev) => ({ ...prev, [item.id]: result.message }));
            setOtDraftByItem((prev) => ({
              ...prev,
              [item.id]: item.orden_trabajo?.numero_acta ?? "",
            }));
          }
        } finally {
          setSavingOtItemId((id) => (id === item.id ? null : id));
        }
      })();
    },
    [onGuardarOtItem]
  );

  const toggleGrupoExpanded = useCallback((grupoId: number) => {
    setExpandedByGrupo((prev) => ({
      ...prev,
      [grupoId]: !(prev[grupoId] ?? false),
    }));
  }, []);

  return (
    <Box
      sx={{
        maxHeight: { xs: "none", md: "min(52vh, 560px)" },
        overflowY: { xs: "visible", md: "auto" },
        overflowX: "hidden",
        pr: { md: 0.5 },
        ...rutasInstitutionalScrollSx,
      }}
    >
      <Stack spacing={1.2}>
        {itemsSinOtPersistida.length > 0 ? (
          <Alert severity="info" variant="outlined" sx={{ borderRadius: 2, py: 0.5 }}>
            <Typography variant="body2" component="span" sx={{ lineHeight: 1.4, fontSize: "0.8125rem" }}>
              {itemsSinOtPersistida.length} ítem{itemsSinOtPersistida.length === 1 ? "" : "s"} sin OT guardada. Expandir
              grupo y usar «Guardar OT».
            </Typography>
          </Alert>
        ) : null}
        {grupos.map((grupo) => {
          const groupItems = itemsByGrupoId.get(grupo.id) ?? [];
          const expanded = expandedByGrupo[grupo.id] ?? false;
          const moveTargets = moveTargetsByGrupoId.get(grupo.id) ?? [];
          const otDraftForItem: Record<number, string> = {};
          const targetForItem: Record<number, number | ""> = {};
          for (const it of groupItems) {
            otDraftForItem[it.id] = otDraftByItem[it.id] ?? it.orden_trabajo?.numero_acta ?? "";
            targetForItem[it.id] = targetByItem[it.id] ?? "";
          }
          const savingItemIdInSection =
            savingOtItemId != null && groupItems.some((i) => i.id === savingOtItemId) ? savingOtItemId : null;

          return (
            <GrupoRutaSection
              key={grupo.id}
              grupo={grupo}
              groupItems={groupItems}
              expanded={expanded}
              moveTargets={moveTargets}
              canMove={canMove}
              iniciadorById={iniciadorById}
              otDraftForItem={otDraftForItem}
              targetForItem={targetForItem}
              otInlineErrorByItem={otInlineErrorByItem}
              savingItemIdInSection={savingItemIdInSection}
              onToggleExpanded={toggleGrupoExpanded}
              onEditarInspectores={onEditarInspectores}
              onEliminarGrupo={onEliminarGrupo}
              onOtDraftChange={handleOtDraftChange}
              onMoveTargetChange={handleMoveTargetChange}
              onGuardarOt={handleGuardarOt}
              onMoverItem={onMoverItem}
              onQuitarItem={onQuitarItem}
            />
          );
        })}
      </Stack>
    </Box>
  );
}

const PanelGruposRuta = memo(PanelGruposRutaInner);
export default PanelGruposRuta;
