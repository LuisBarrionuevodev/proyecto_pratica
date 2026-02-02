import { Box, Typography, IconButton, Tooltip } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { deleteActuacion, updateActuacion } from "../../../api/actuacionesApi";
import {
  fetchInspectores,
  fetchMotivos,
  fetchRubros,
  fetchTiposActuacion,
  fetchContraproducencias,
  fetchMotivosComprobacion,
  validateRow,
} from "../../../api/gridApi";
import NumeroEsquinaEditor from "../../../components/shared/NumeroEsquinaEditor";
import { useCallesCatalogo } from "../../../hooks/useCallesCatalogo";
import { TablaExportButtons } from "./TableButtons";
import { GridLegend } from "./GridLegend";
import { AnimatedTable, useTableRefresh } from "../../../animations";

import {
  loadingStyles,
  DARK_TABLE_CONFIG,
  COLORS,
} from "../styles/actuacionesTableStyles";

import { getDropdownOptions } from "../../CargarActuaciones/config/dropdownOptions";

interface TablaActuacionesProps {
  data?: IActuacionListItem[];
  loading?: boolean;
  onRefresh?: () => void;
  initialColumnVisibility?: Record<string, boolean>;
  enableEditing?: boolean;
  hideRowActions?: boolean;
  extraColumns?: MRT_ColumnDef<IActuacionListItem>[];
  onBeforeSave?: (fullRow: IActuacionListItem) => Promise<void>;
  onAfterSave?: (fullRow: IActuacionListItem) => Promise<void>;
}

// ✅ UUID fijo válido para validar filas desde esta vista
const UI_BATCH_ID = "00000000-0000-0000-0000-000000000001";

// Mapeo de errores (backend -> snake_case de esta tabla)
const ERROR_KEY_MAP: Record<string, string> = {
  "Orden de trabajo": "orden_trabajo_numero",
  "Fecha actuación": "fecha_actuacion",
  "Tipo actuación": "tipo_actuacion",
  "Contraproducencia": "contraproducencia",
  "Inspector 1": "inspector1",
  "Inspector 2": "inspector2",
  "Inspector 3": "inspector3",
  "Calle": "calle",
  "Número": "numero",
  "Rubro": "rubro_nombre",
  "Apellido": "contrib_apellido",
  "Nombre": "contrib_nombre",
  "DNI": "doc_nro",
  "Acta inspección": "acta_inspeccion_num",
  "Acta notificación": "acta_notificacion_num",
  "Motivo notif 1": "notificacion_motivo_1",
  "Motivo notif 2": "notificacion_motivo_2",
  "Motivo notif 3": "notificacion_motivo_3",
  "Acta comprobación": "acta_comprobacion_num",
  "Motivo comprobación": "comprobacion_motivo",
  "Acta clausura": "acta_clausura_num",
  "Acta decomiso": "acta_decomiso_num",
  "Kilos decomiso": "decomiso_kilos_total",
  "Acta notificación previa": "notificacion_previa_num",
  "Acta comprobación previa": "comprobacion_previa_num",
  "Expediente año": "expediente_anio",
  "Expediente número": "expediente_numero",
  "Oficio año": "oficio_anio",
  "Oficio número": "oficio_numero",
  "Oficio causa": "oficio_causa",
};

const normalizeErrors = (errors?: Record<string, string>) => {
  if (!errors) return {};
  const mapped: Record<string, string> = {};
  Object.entries(errors).forEach(([key, msg]) => {
    const targetKey = ERROR_KEY_MAP[key] || key;
    mapped[targetKey] = msg;
  });
  return mapped;
};

const TablaActuaciones = ({
  data: externalData,
  loading: externalLoading,
  onRefresh,
  initialColumnVisibility,
  enableEditing = true,
  hideRowActions = false,
  extraColumns = [],
  onBeforeSave,
  onAfterSave,
}: TablaActuacionesProps) => {
  const [data, setData] = useState<IActuacionListItem[]>(externalData || []);
  const loading = externalLoading || false;

  const { isRefreshing, triggerRefresh } = useTableRefresh();

  const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
  const [catalogMotivos, setCatalogMotivos] = useState<string[]>([]);
  const [catalogRubros, setCatalogRubros] = useState<string[]>([]);
  const [catalogTipos, setCatalogTipos] = useState<string[]>([]);
  const [catalogContras, setCatalogContras] = useState<string[]>([]);
  const [catalogMotivosComprobacion, setCatalogMotivosComprobacion] = useState<string[]>([]);
  const { calles: callesCatalogo } = useCallesCatalogo();

  // ✅ errores por celda por idActuacion
  const [rowErrors, setRowErrors] = useState<Record<number, Record<string, string>>>({});

  useEffect(() => {
    if (externalData) setData(externalData);
  }, [externalData]);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [inspectores, motivos, rubros, tipos, contras, motivosComp] = await Promise.all([
          fetchInspectores(),
          fetchMotivos(),
          fetchRubros(),
          fetchTiposActuacion(),
          fetchContraproducencias(),
          fetchMotivosComprobacion(),
        ]);
        // Deduplicar catálogos para evitar nombres repetidos
        setCatalogInspectores([...new Set(inspectores.items.map((i: any) => i.nombre))]);
        setCatalogMotivos([...new Set(motivos.items.map((m: any) => m.nombre))]);
        setCatalogRubros([...new Set(rubros.items.map((r: any) => r.nombre))]);
        setCatalogTipos([...new Set(tipos.items.map((t: any) => t.nombre))]);
        setCatalogContras([...new Set(contras.items.map((c: any) => c.nombre))]);
        setCatalogMotivosComprobacion([...new Set(motivosComp.items.map((m: any) => m.nombre))]);
      } catch (error) {
        console.error("Error cargando catálogos:", error);
      }
    };
    loadCatalogs();
  }, []);

  // Catálogos combinados (reusa helper del grid)
  const catalogs = useMemo(() => ({
    inspectores: catalogInspectores,
    motivos: catalogMotivos,
    rubros: catalogRubros,
    tipos: catalogTipos,
    contraproducencias: catalogContras,
    motivosComprobacion: catalogMotivosComprobacion,
  }), [catalogInspectores, catalogMotivos, catalogRubros, catalogTipos, catalogContras, catalogMotivosComprobacion]);

  const handleDeleteRow = useCallback(async (id: number) => {
    if (!window.confirm("¿Estás seguro de eliminar este registro?")) return;

    const prev = [...data];
    setData(prevData => prevData.filter(item => item.id !== id));

    try {
      await deleteActuacion(id);
      onRefresh?.();
    } catch (error) {
      console.error("Error al eliminar:", error);
      alert("No se pudo eliminar el registro. Se restaurará la lista.");
      setData(prev);
    }
  }, [data, onRefresh]);

  const handleSaveRow = useCallback(async ({ exitEditingMode, row, values }: any) => {
    const id = Number(row.original.id);

    // ✅ PUT: mandamos fila completa (merge original + values editados)
    const fullRow = { ...row.original, ...values };

    try {
      // ✅ Validación previa (pinta celdas rojas si hay errores)
      const v = await validateRow({
        batch_id: UI_BATCH_ID,
        row_id: `act_${id}`,
        row: fullRow as any, // importante: fullRow debe coincidir con lo que espera tu backend
      });

      if (!v.ok) {
        setRowErrors(prev => ({ ...prev, [id]: normalizeErrors(v.errors || {}) }));
        return; // NO salimos del modo edición
      }

      // ✅ si OK, limpiar errores de esa fila
      setRowErrors(prev => ({ ...prev, [id]: {} }));

      if (onBeforeSave) {
        await onBeforeSave(fullRow as IActuacionListItem);
      }

      // ✅ guardar con PUT (tu api ya debe usar put, no patch)
      await updateActuacion(id, fullRow as any);

      if (onAfterSave) {
        await onAfterSave(fullRow as IActuacionListItem);
      }

      exitEditingMode();

      triggerRefresh();
      setTimeout(() => onRefresh?.(), 100);
    } catch (error: any) {
      console.error("Error al actualizar:", error);

      // Si el backend devuelve 422 con errors por campo, podés mapearlos también:
      const backendErrors = error?.response?.data?.errors;
      if (backendErrors && typeof backendErrors === "object") {
        setRowErrors(prev => ({ ...prev, [id]: normalizeErrors(backendErrors) }));
        return;
      }

      const msg = error?.response?.data?.detail || "No se pudo actualizar el registro.";
      alert(msg);
    }
  }, [onRefresh, triggerRefresh, onBeforeSave, onAfterSave]);

  const columns = useMemo<MRT_ColumnDef<IActuacionListItem>[]>(() => {
    const baseColumns: MRT_ColumnDef<IActuacionListItem>[] = [
    { accessorKey: "id", header: "ID", enableHiding: true, enableEditing: false, size: 80 },

    {
      accessorKey: "orden_trabajo_numero",
      header: "OT",
      size: 100,
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["orden_trabajo_numero"];
        return { required: true, error: !!err, helperText: err ?? "" };
      },
    },

    {
      accessorKey: "fecha_actuacion",
      header: "Fecha",
      size: 120,
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["fecha_actuacion"];
        return { type: "date", required: true, error: !!err, helperText: err ?? "" };
      },
    },

    {
      accessorKey: "tipo_actuacion",
      header: "Tipo",
      size: 180,
      editVariant: "select",
      // Opciones desde catálogo (backend)
      editSelectOptions: getDropdownOptions("Tipo actuación", catalogs),
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["tipo_actuacion"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },

    {
      accessorKey: "contraproducencia",
      header: "Contraproducencia",
      size: 180,
      editVariant: "select",
      // Opciones desde catálogo (backend)
      editSelectOptions: getDropdownOptions("Contraproducencia", catalogs),
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["contraproducencia"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },

    {
      accessorKey: "rubro_nombre",
      header: "Rubro",
      size: 200,
      editVariant: "select",
      editSelectOptions: ["", ...catalogRubros],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["rubro_nombre"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },

    {
      accessorKey: "inspector1",
      header: "Inspector 1",
      size: 150,
      editVariant: "select",
      editSelectOptions: ["", ...catalogInspectores],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["inspector1"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },
    {
      accessorKey: "inspector2",
      header: "Inspector 2",
      size: 150,
      editVariant: "select",
      editSelectOptions: ["", ...catalogInspectores],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["inspector2"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },
    {
      accessorKey: "inspector3",
      header: "Inspector 3",
      size: 150,
      editVariant: "select",
      editSelectOptions: ["", ...catalogInspectores],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["inspector3"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },

    {
      accessorKey: "calle",
      header: "Calle",
      size: 200,
      Cell: ({ row }) => {
        if (row.original.calle_estado === "OK" && row.original.calle_normalizada) {
          return row.original.calle_normalizada;
        }
        return row.original.calle ?? "";
      },
    },
    {
      accessorKey: "numero",
      header: "Número",
      size: 400,
      Cell: ({ row }) => {
        if (
          row.original.numero_tipo === "ESQUINA" &&
          row.original.esquina_status === "OK" &&
          row.original.esquina_normalizada
        ) {
          return row.original.esquina_normalizada;
        }
        return row.original.numero ?? "";
      },
      Edit: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["numero"];
        const currentValue =
          (row as any)?._valuesCache?.numero ?? row.original.numero ?? null;

        return (
          <NumeroEsquinaEditor
            value={currentValue}
            onChange={(newValue) => {
              (row as any)._valuesCache = {
                ...(row as any)._valuesCache,
                numero: newValue,
              };
            }}
            onModeChange={(mode) => {
              (row as any)._valuesCache = {
                ...(row as any)._valuesCache,
                numero_tipo: mode,
              };
            }}
            calles={callesCatalogo}
            label="Número"
            error={!!err}
            helperText={err ?? ""}
          />
        );
      },
    },

    { accessorKey: "doc_nro", header: "Doc. Nro", size: 120 },
    { accessorKey: "contrib_apellido", header: "Contribuyente Apellido", size: 180 },
    { accessorKey: "contrib_nombre", header: "Contribuyente Nombre", size: 180 },

    { accessorKey: "acta_inspeccion_num", header: "Acta Inspección", size: 150 },
    { accessorKey: "acta_notificacion_num", header: "Acta Notificación", size: 150 },

    {
      accessorKey: "notificacion_motivo_1",
      header: "Motivo Notif. 1",
      size: 180,
      editVariant: "select",
      editSelectOptions: ["", ...catalogMotivos],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["notificacion_motivo_1"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },
    {
      accessorKey: "notificacion_motivo_2",
      header: "Motivo Notif. 2",
      size: 180,
      editVariant: "select",
      editSelectOptions: ["", ...catalogMotivos],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["notificacion_motivo_2"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },
    {
      accessorKey: "notificacion_motivo_3",
      header: "Motivo Notif. 3",
      size: 180,
      editVariant: "select",
      editSelectOptions: ["", ...catalogMotivos],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["notificacion_motivo_3"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },

    { accessorKey: "acta_comprobacion_num", header: "Acta Comprobación", size: 150 },
    {
      accessorKey: "comprobacion_motivo",
      header: "Motivo Comprob.",
      size: 180,
      editVariant: "select",
      // Opciones desde catálogo (backend)
      editSelectOptions: getDropdownOptions("Motivo comprobación", catalogs),
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["comprobacion_motivo"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },

    { accessorKey: "acta_clausura_num", header: "Acta Clausura", size: 150 },
    { accessorKey: "acta_decomiso_num", header: "Acta Decomiso", size: 150 },
    { accessorKey: "decomiso_kilos_total", header: "Kilos Decomisados", size: 150 },

    { accessorKey: "expediente_numero", header: "Expediente Nro", size: 150 },
    { accessorKey: "expediente_anio", header: "Expediente Año", size: 120 },

    { accessorKey: "oficio_numero", header: "Oficio Nro", size: 120 },
    { accessorKey: "oficio_anio", header: "Oficio Año", size: 120 },
    { accessorKey: "oficio_causa", header: "Oficio Causa", size: 180 },

    { accessorKey: "notificacion_previa_num", header: "Notificación Previa", size: 150 },
    { accessorKey: "comprobacion_previa_num", header: "Comprobación Previa", size: 150 },

    ];
    return [...baseColumns, ...extraColumns];
  }, [catalogInspectores, catalogMotivos, catalogRubros, catalogs, rowErrors, extraColumns, callesCatalogo]);

  const columnOrder = useMemo(() => ([
    "mrt-row-select",
    ...(hideRowActions ? [] : ["mrt-row-actions"]),
    ...columns.map((col) => col.accessorKey as string),
  ]), [columns, hideRowActions]);

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data,
    enableEditing,
    editDisplayMode: "row",
    enableSorting: true,
    enableColumnFilters: true,
    enableGlobalFilter: true,
    enableRowActions: !hideRowActions,
    // Acciones al inicio (después del checkbox de selección)
    positionActionsColumn: "first",
    enableHiding: true,

    // ✅ pintar celdas con error incluso fuera de edición
    muiTableBodyCellProps: ({ row, column }) => {
      const rid = Number(row.original.id);
      const err = rowErrors[rid]?.[column.id];
      return err ? { sx: { backgroundColor: "rgba(255, 68, 68, 0.15)" } } : {};
    },

    initialState: {
      columnOrder,
      columnVisibility: {
        id: false,
        inspector2: false,
        inspector3: false,
        doc_nro: false,
        contrib_apellido: false,
        contrib_nombre: false,
        notificacion_motivo_2: false,
        notificacion_motivo_3: false,
        comprobacion_motivo: false,
        acta_clausura_num: false,
        acta_decomiso_num: false,
        decomiso_kilos_total: false,
        expediente_numero: false,
        expediente_anio: false,
        oficio_numero: false,
        oficio_anio: false,
        oficio_causa: false,
        notificacion_previa_num: false,
        comprobacion_previa_num: false,
        ...initialColumnVisibility,
      },
      density: "compact",
    },

    onEditingRowSave: handleSaveRow,

    renderRowActions: hideRowActions ? undefined : ({ row, table }) => (
      <Box sx={{ display: "flex", gap: "0.5rem" }}>
        <Tooltip title="Editar">
          <IconButton
            sx={{
              color: COLORS.white,
              transition: "color 0.2s ease, background-color 0.2s ease",
              "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
            }}
            onClick={() => table.setEditingRow(row)}
          >
            <EditIcon />
          </IconButton>
        </Tooltip>

        <Tooltip title="Eliminar">
          <IconButton
            sx={{
              color: COLORS.white,
              transition: "color 0.2s ease, background-color 0.2s ease",
              "&:hover": { color: "#ff4444", backgroundColor: "rgba(255, 68, 68, 0.15)" },
            }}
            onClick={() => handleDeleteRow(Number(row.original.id))}
          >
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      </Box>
    ),

    renderTopToolbarCustomActions: ({ table }) => (
      <TablaExportButtons data={data} table={table} />
    ),
  });

  if (loading) {
    return (
      <Box sx={{ padding: "40px", textAlign: "center" }}>
        <Typography sx={loadingStyles}>Cargando actuaciones...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <AnimatedTable isRefreshing={isRefreshing}>
        <MaterialReactTable table={table} />
      </AnimatedTable>
      <GridLegend />
    </Box>
  );
};

export default TablaActuaciones;
