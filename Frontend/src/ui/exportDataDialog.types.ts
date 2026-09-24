export type ExportFormat = "excel" | "pdf";

export type ExportPeriodMode = "workweek" | "month" | "custom";

export interface ExportDateRange {
  desde: string;
  hasta: string;
}

export interface ExportDataDialogProps {
  open: boolean;
  onClose: () => void;

  title?: string;
  subtitle?: string;

  defaultPeriod?: ExportPeriodMode;
  defaultFormat?: ExportFormat;

  periodModes?: ExportPeriodMode[];
  formats?: ExportFormat[];

  /** Si existe clave, el formato queda deshabilitado; el valor es el motivo (tooltip). */
  disabledFormats?: Partial<Record<ExportFormat, string>>;

  initialCustomRange?: Partial<ExportDateRange>;

  minDate?: string;
  maxDate?: string;

  loading?: boolean;
  error?: string | null;
  onClearError?: () => void;

  showPeriod?: boolean;
  scopeHint?: string;

  onExport: (options: {
    format: ExportFormat;
    periodMode: ExportPeriodMode;
    desde: string;
    hasta: string;
  }) => Promise<void> | void;
}
