import { useCallback, useMemo, useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";
import { Alert, Box, Stack, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_PaginationState,
  type MRT_Updater,
} from "material-react-table";

import { AppButton, AppTextField } from "../../ui";
import { DataTableMrtShell } from "../../components/dataTable/DataTableMrtShell";
import {
  BANDEJA_MRT_SPINNER_LOADING_STATE,
  BandejaTableSpinner,
} from "../../components/dataTable/bandejaTableLoading";
import {
  BandejaTableSummary,
  BandejaTableSummaryItem,
} from "../../components/dataTable/BandejaTableSummary";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";
import { BANDEJA_MRT_READ_ONLY_TABLE_PROPS } from "../Actuaciones/Components/bandejaTableCells";
import {
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroTitleStyles,
} from "../Actuaciones/styles/filtroStyles";
import { FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING } from "../../styles/functionalPageShell";
import type { IHistorialContribuyenteRow } from "../../api/historialContribuyenteApi";
import { buildHistorialContribuyenteColumns } from "./historialContribuyenteColumns";
import { useHistorialContribuyente } from "./hooks/useHistorialContribuyente";

const DEFAULT_PAGE_SIZE = 20;

type HistorialContribuyenteResultsProps = {
  rows: IHistorialContribuyenteRow[];
  total: number;
  loading: boolean;
  pagination: MRT_PaginationState;
  onPaginationChange: (updater: MRT_Updater<MRT_PaginationState>) => void;
};

function HistorialContribuyenteResults({
  rows,
  total,
  loading,
  pagination,
  onPaginationChange,
}: HistorialContribuyenteResultsProps) {
  const columns = useMemo(() => buildHistorialContribuyenteColumns(), []);

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
    columns,
    data: rows,
    getRowId: (row) => String(row.id),
    enableEditing: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    manualPagination: true,
    rowCount: total,
    state: {
      pagination,
      ...BANDEJA_MRT_SPINNER_LOADING_STATE,
    },
    onPaginationChange,
  });

  if (loading) {
    return <BandejaTableSpinner />;
  }

  return (
    <DataTableMrtShell loadingMode="none">
      <MaterialReactTable table={table} />
    </DataTableMrtShell>
  );
}

/**
 * Consulta histórica por DNI/CUIT (solo lectura; no alimenta prefill operativo).
 */
export default function HistorialContribuyentePage() {
  const {
    rows,
    meta,
    loading,
    error,
    validationError,
    hasSearched,
    lastDocumentoInput,
    buscar,
    limpiar,
  } = useHistorialContribuyente();

  const [documentoInput, setDocumentoInput] = useState("");
  const [pagination, setPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  });

  const onBuscar = useCallback(() => {
    setPagination((p) => ({ ...p, pageIndex: 0 }));
    void buscar({
      documento: documentoInput,
      page: 1,
      limit: pagination.pageSize,
    });
  }, [buscar, documentoInput, pagination.pageSize]);

  const onLimpiar = useCallback(() => {
    setDocumentoInput("");
    setPagination({ pageIndex: 0, pageSize: DEFAULT_PAGE_SIZE });
    limpiar();
  }, [limpiar]);

  const onPaginationChange = useCallback(
    (updater: MRT_Updater<MRT_PaginationState>) => {
      setPagination((prev) => {
        const next = typeof updater === "function" ? updater(prev) : updater;
        if (hasSearched && lastDocumentoInput.trim()) {
          void buscar({
            documento: lastDocumentoInput,
            page: next.pageIndex + 1,
            limit: next.pageSize,
          });
        }
        return next;
      });
    },
    [buscar, hasSearched, lastDocumentoInput]
  );

  const documentoConsultado = meta?.documento_normalizado?.trim() || lastDocumentoInput.trim();
  const total = meta?.total ?? 0;
  const page = meta?.page ?? pagination.pageIndex + 1;

  return (
    <Stack spacing={FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING} sx={{ width: "100%", maxWidth: "100%" }}>
      <Box sx={filtroContainerStyles}>
        <Typography sx={filtroTitleStyles}>Búsqueda por documento</Typography>
        <Box sx={filtroGridStyles}>
          <Box sx={{ ...filtroItemStyles, gridColumn: { xs: "1 / -1", md: "span 2" } }}>
            <AppTextField
              appearance="dense"
              fullWidth
              label="DNI/CUIT"
              placeholder="Ej. 42006775, 42.006.775, 20-33344455-5"
              value={documentoInput}
              onChange={(e) => setDocumentoInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onBuscar();
              }}
              variant="outlined"
            />
          </Box>
        </Box>
        <Box sx={filtroButtonsStyles}>
          <AppButton
            dsVariant="ghost"
            dsSize="sm"
            startIcon={<ClearIcon sx={{ fontSize: 18 }} />}
            onClick={onLimpiar}
            sx={filtroButtonSecondaryStyles}
          >
            Limpiar
          </AppButton>
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            startIcon={<SearchIcon sx={{ fontSize: 18 }} />}
            onClick={onBuscar}
            sx={filtroButtonPrimaryStyles}
          >
            Buscar
          </AppButton>
        </Box>
      </Box>

      {validationError ? (
        <Alert severity="warning">{validationError}</Alert>
      ) : null}

      {error && hasSearched ? (
        <Alert severity="error" onClose={() => undefined}>
          {error}
        </Alert>
      ) : null}

      {hasSearched && meta ? (
        <BandejaTableSummary>
          <BandejaTableSummaryItem label="Total" value={total} />
          <BandejaTableSummaryItem
            label="Mostrando"
            value={loading ? "…" : `${rows.length} de ${total}`}
          />
          <BandejaTableSummaryItem label="Página" value={page} />
          {documentoConsultado ? (
            <BandejaTableSummaryItem label="DNI/CUIT" value={documentoConsultado} />
          ) : null}
        </BandejaTableSummary>
      ) : null}

      {hasSearched && !loading && meta && rows.length === 0 && !error ? (
        <Typography
          sx={{
            fontFamily: '"Tactic Sans", sans-serif',
            fontSize: "14px",
            color: "rgba(255,255,255,0.55)",
            py: 2,
          }}
        >
          No se encontraron actuaciones para este DNI/CUIT.
        </Typography>
      ) : null}

      {hasSearched && (loading || rows.length > 0) ? (
        <HistorialContribuyenteResults
          rows={rows}
          total={total}
          loading={loading}
          pagination={pagination}
          onPaginationChange={onPaginationChange}
        />
      ) : null}
    </Stack>
  );
}
