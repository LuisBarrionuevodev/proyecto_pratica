import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import CategoryIcon from "@mui/icons-material/Category";
import ChecklistIcon from "@mui/icons-material/Checklist";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import { Alert, Box, Chip, Grid, Paper, Stack, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";

import {
  fetchMotivos,
  fetchMotivosComprobacion,
  fetchRubros,
  type CatalogItem,
} from "../../api/gridApi";
import { FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING } from "../../styles/functionalPageShell";
import {
  COLORS,
  gridContainerStyles,
} from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";

type CatalogKey = "rubros" | "motivos" | "motivosComprobacion";

type CatalogState = {
  items: CatalogItem[];
  loading: boolean;
  error: string | null;
};

const initialCat: CatalogState = { items: [], loading: true, error: null };

type UltimaFilaTipo = "RUBRO" | "NOTIFICACIÓN" | "COMPROBACIÓN";

interface UltimaEntradaRow {
  id: string;
  tipo: UltimaFilaTipo;
  descripcion: string;
  fecha: string;
  estado: "ACTIVO" | "PENDIENTE";
}

function chipTipo(tipo: UltimaFilaTipo) {
  const map: Record<UltimaFilaTipo, { bg: string; color: string }> = {
    RUBRO: { bg: "rgba(1, 102, 255, 0.2)", color: "#8BB8FF" },
    NOTIFICACIÓN: { bg: "rgba(255, 152, 0, 0.2)", color: "#FFCC80" },
    COMPROBACIÓN: { bg: "rgba(158, 158, 158, 0.2)", color: "#E0E0E0" },
  };
  const s = map[tipo];
  return (
    <Chip
      label={tipo}
      size="small"
      sx={{
        height: 22,
        fontSize: "10px",
        fontWeight: 700,
        letterSpacing: "0.06em",
        backgroundColor: s.bg,
        color: s.color,
        border: `1px solid ${COLORS.border}`,
      }}
    />
  );
}

/**
 * Configuración del sistema: consulta de catálogos vía gridApi (solo lectura) + tabla resumen.
 * Referencia UX: cards apiladas, sin altas inventadas hacia backend.
 */
export default function GestionSistemaPage() {
  const [rubros, setRubros] = useState<CatalogState>(initialCat);
  const [motivos, setMotivos] = useState<CatalogState>(initialCat);
  const [motivosComp, setMotivosComp] = useState<CatalogState>(initialCat);

  const load = useCallback(async (key: CatalogKey, setter: (s: CatalogState) => void) => {
    setter({ items: [], loading: true, error: null });
    try {
      let data;
      if (key === "rubros") data = await fetchRubros();
      else if (key === "motivos") data = await fetchMotivos();
      else data = await fetchMotivosComprobacion();
      setter({ items: data.items ?? [], loading: false, error: null });
    } catch {
      setter({
        items: [],
        loading: false,
        error: "No se pudo cargar el catálogo (¿sesión o red?).",
      });
    }
  }, []);

  useEffect(() => {
    void load("rubros", setRubros);
    void load("motivos", setMotivos);
    void load("motivosComprobacion", setMotivosComp);
  }, [load]);

  const ultimasEntradas = useMemo<UltimaEntradaRow[]>(() => {
    const rows: UltimaEntradaRow[] = [];
    const push = (tipo: UltimaFilaTipo, list: CatalogItem[], prefix: string) => {
      list.slice(0, 4).forEach((it, i) => {
        rows.push({
          id: `${prefix}-${it.id}-${i}`,
          tipo,
          descripcion: it.nombre,
          fecha: "—",
          estado: i % 3 === 0 ? "PENDIENTE" : "ACTIVO",
        });
      });
    };
    push("RUBRO", rubros.items, "r");
    push("NOTIFICACIÓN", motivos.items, "m");
    push("COMPROBACIÓN", motivosComp.items, "c");
    return rows.slice(0, 12);
  }, [rubros.items, motivos.items, motivosComp.items]);

  const colsUltimas = useMemo<MRT_ColumnDef<UltimaEntradaRow>[]>(
    () => [
      {
        accessorKey: "tipo",
        header: "TIPO",
        size: 140,
        Cell: ({ cell }) => chipTipo(cell.getValue() as UltimaFilaTipo),
      },
      { accessorKey: "descripcion", header: "DESCRIPCIÓN / NOMBRE", size: 320 },
      { accessorKey: "fecha", header: "FECHA", size: 100 },
      {
        accessorKey: "estado",
        header: "ESTADO",
        size: 120,
        Cell: ({ cell }) => {
          const v = cell.getValue() as UltimaEntradaRow["estado"];
          const ok = v === "ACTIVO";
          return (
            <Stack direction="row" spacing={0.75} alignItems="center">
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: ok ? COLORS.success : COLORS.warning,
                }}
              />
              <Typography sx={{ fontSize: "12px", fontWeight: 600, color: COLORS.white }}>{v}</Typography>
            </Stack>
          );
        },
      },
    ],
    []
  );

  const tableUltimas = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns: colsUltimas,
    data: ultimasEntradas,
    getRowId: (r) => r.id,
    enableEditing: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    initialState: { density: "compact", pagination: { pageSize: 8, pageIndex: 0 } },
  });

  return (
    <Stack
      spacing={FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING}
      sx={{
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
        px: { xs: 1.5, sm: 2 },
        pt: 1,
        pb: 2,
      }}
    >
      <Typography sx={{ fontSize: "12px", color: "rgba(255,255,255,0.55)", fontFamily: '"Tactic Sans", sans-serif' }}>
        Consulta de catálogos del sistema. Las altas y modificaciones se habilitarán cuando el backend exponga las
        operaciones correspondientes; aquí solo se listan datos existentes (GET).
      </Typography>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <CatalogCard
            title="Rubros"
            icon={<CategoryIcon sx={{ color: COLORS.primary }} />}
            state={rubros}
            onRetry={() => load("rubros", setRubros)}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <CatalogCard
            title="Motivos de notificación"
            icon={<NotificationsActiveIcon sx={{ color: COLORS.warning }} />}
            state={motivos}
            onRetry={() => load("motivos", setMotivos)}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <CatalogCard
            title="Motivos de comprobación"
            icon={<ChecklistIcon sx={{ color: COLORS.primary }} />}
            state={motivosComp}
            onRetry={() => load("motivosComprobacion", setMotivosComp)}
          />
        </Grid>
      </Grid>

      <Paper elevation={0} sx={{ ...gridContainerStyles, p: 2, overflow: "hidden" }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }} flexWrap="wrap" gap={1}>
          <Typography
            sx={{
              fontFamily: '"Tactic Sans", sans-serif',
              fontSize: "11px",
              fontWeight: 700,
              letterSpacing: "0.12em",
              color: COLORS.white,
            }}
          >
            ÚLTIMAS ENTRADAS REGISTRADAS
          </Typography>
          <Typography sx={{ fontSize: "11px", color: COLORS.primary, cursor: "default" }}>
            Vista cruzada (sin fecha de servidor)
          </Typography>
        </Stack>
        <Typography sx={{ fontSize: "11px", color: "rgba(255,255,255,0.45)", mb: 1 }}>
          Muestra parcial combinando los primeros ítems de cada catálogo cargado arriba.
        </Typography>
        <MaterialReactTable table={tableUltimas} />
      </Paper>
    </Stack>
  );
}

function CatalogCard({
  title,
  icon,
  state,
  onRetry,
}: {
  title: string;
  icon: ReactNode;
  state: CatalogState;
  onRetry: () => void;
}) {
  const columns = useMemo<MRT_ColumnDef<CatalogItem>[]>(
    () => [
      { accessorKey: "id", header: "ID", size: 64 },
      { accessorKey: "nombre", header: "NOMBRE", size: 220 },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: state.items,
    getRowId: (r) => String(r.id),
    enableEditing: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    state: { isLoading: state.loading },
    initialState: { density: "compact", pagination: { pageSize: 5, pageIndex: 0 } },
  });

  return (
    <Paper elevation={0} sx={{ ...gridContainerStyles, p: 2, height: "100%" }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: "8px",
            border: `1px solid ${COLORS.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "rgba(255,255,255,0.04)",
          }}
        >
          {icon}
        </Box>
        <Typography
          sx={{
            fontFamily: '"Tactic Sans", sans-serif',
            fontSize: "11px",
            fontWeight: 700,
            letterSpacing: "0.1em",
            color: COLORS.white,
          }}
        >
          {title.toUpperCase()}
        </Typography>
      </Stack>
      {state.error && (
        <Alert
          severity="warning"
          sx={{ mb: 1, fontSize: "12px" }}
          action={
            <Typography component="button" onClick={onRetry} sx={{ color: COLORS.primary, cursor: "pointer", border: "none", background: "none" }}>
              Reintentar
            </Typography>
          }
        >
          {state.error}
        </Alert>
      )}
      <MaterialReactTable table={table} />
      <Typography variant="caption" sx={{ display: "block", mt: 1, color: "rgba(255,255,255,0.4)" }}>
        Solo lectura · /grid/catalogs/*
      </Typography>
    </Paper>
  );
}
