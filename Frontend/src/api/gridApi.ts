import { apiClient } from "./apiClient";

// ============= TYPES =============

export interface GridRow {
  // Metadata
  _rowId?: string;
  _state?: "PENDIENTE" | "OK" | "ERROR" | "VALIDANDO";
  _cellErrors?: Record<string, string>; // Errores por celda: { "columnId": "mensaje de error" }
  _normalized?: GridRow;
  _validation_history?: number[]; // Para gráficos sparkline (demo)
  _rowError?: string | null; // Error de fila completa (ej: duplicado)
  _touched?: boolean;
  _needsCommit?: boolean;

  // Data columns (with spaces, as backend expects)
  "ID"?: number | null;
  "Fecha actuación"?: string | null;
  "Fecha"?: string | null;
  "Tipo actuación"?: string | null;
  "Contraproducencia"?: string | null;
  "Orden de trabajo"?: string | null;
  "Inspector"?: string | null;
  "Inspector 1"?: string | null;
  "Inspector 2"?: string | null;
  "Inspector 3"?: string | null;
  "Calle"?: string | null;
  "Número"?: string | null;
  "Numero"?: string | null;
  "Turno"?: string | null;
  "Está abierto"?: string | boolean | null;
  "Rubro"?: string | null;
  "Apellido"?: string | null;
  "Nombre"?: string | null;
  "DNI"?: string | null;
  "Acta inspección"?: string | null;
  "Acta notificación"?: string | null;
  "Motivo notif 1"?: string | null;
  "Motivo notif 2"?: string | null;
  "Motivo notif 3"?: string | null;
  "Acta comprobación"?: string | null;
  "Motivo comprobación"?: string | null;
  "Acta clausura"?: string | null;
  "Acta decomiso"?: string | null;
  "Kilos decomiso"?: number | null;
  "Acta notificación previa"?: string | null;
  "Acta comprobación previa"?: string | null;
  "Expediente año"?: number | null;
  "Expediente número"?: string | null;
  "Oficio año"?: number | null;
  "Oficio número"?: string | null;
  "Oficio causa"?: number | null;
}

export interface StartBatchResponse {
  batch_id: string;
}

export interface StartBatchRequest {
  kind?: string;
}

export interface ValidateRowResponse {
  batch_id: string;
  row_id: string;
  ok: boolean;
  errors?: Record<string, string>; // { "columna": "mensaje de error" }
  normalized?: GridRow;
}

export interface ValidateBatchResponse {
  batch_id: string;
  results: ValidateRowResponse[];
}

export interface CommitRowResponse {
  batch_id: string;
  row_id: string;
  ok: boolean;
  errors?: Record<string, string>;
  persisted?: {
    id: number;
    [key: string]: any;
  };
}

export interface CommitBatchResponse {
  batch_id: string;
  results: CommitRowResponse[];
}

// === Catálogos para dropdowns (backend) ===
export interface CatalogItem {
  id: number;
  nombre: string;
  legajo?: string;
}

export interface CatalogResponse {
  items: CatalogItem[];
}

export interface ValidateRowRequest {
  batch_id: string;
  row_id: string;
  row: GridRow;
}

export interface ValidateBatchRequest {
  batch_id: string;
  rows: Array<{ row_id: string; row: GridRow }>;
}

export interface CommitRowRequest {
  batch_id: string;
  row_id: string;
  normalized: GridRow; // Backend expects normalized data, not raw row
}

export interface CommitBatchRequest {
  batch_id: string;
  rows: Array<{ row_id: string; normalized: GridRow }>; // Backend expects normalized data
}

// ============= API FUNCTIONS =============

/**
 * Inicia un nuevo batch de carga
 */
export const startBatch = async (
  kind: string = "actuaciones"
): Promise<StartBatchResponse> => {
  const payload: StartBatchRequest = { kind };
  const { data } = await apiClient.post<StartBatchResponse>("/grid/start", payload);
  return data;
};

/**
 * Valida una sola fila
 */
export const validateRow = async (
  request: ValidateRowRequest
): Promise<ValidateRowResponse> => {
  const { data } = await apiClient.post<ValidateRowResponse>(
    "/grid/validate-row",
    request
  );
  return data;
};

/**
 * Valida un batch completo (todas las filas)
 */
export const validateBatch = async (
  request: ValidateBatchRequest
): Promise<ValidateBatchResponse> => {
  const { data } = await apiClient.post<ValidateBatchResponse>(
    "/grid/validate-batch",
    request
  );
  return data;
};

/**
 * Confirma/persiste una sola fila
 */
export const commitRow = async (
  request: CommitRowRequest
): Promise<CommitRowResponse> => {
  const { data } = await apiClient.post<CommitRowResponse>(
    "/grid/commit-row",
    request
  );
  return data;
};

/**
 * Confirma/persiste un batch completo (intenta todas las filas)
 */
export const commitBatch = async (
  request: CommitBatchRequest
): Promise<CommitBatchResponse> => {
  try {
    const { data } = await apiClient.post<CommitBatchResponse>(
      "/grid/commit-batch",
      request
    );
    return data;
  } catch (error: any) {
    // Si el endpoint no existe (404), fallback a commit-row iterativo
    if (error?.response?.status === 404) {
      console.warn("Endpoint /grid/commit-batch no existe, usando commit-row iterativo");
      throw new Error("FALLBACK_TO_INDIVIDUAL");
    }
    throw error;
  }
};

/**
 * Catálogo de inspectores (para dropdowns)
 */
export const fetchInspectores = async (): Promise<CatalogResponse> => {
  const { data } = await apiClient.get<CatalogResponse>("/grid/catalogs/inspectores");
  return data;
};

/**
 * Catálogo de motivos (para dropdowns)
 */
export const fetchMotivos = async (): Promise<CatalogResponse> => {
  const { data } = await apiClient.get<CatalogResponse>("/grid/catalogs/motivos");
  return data;
};

/**
 * Catálogo de rubros (para dropdowns)
 */
export const fetchRubros = async (): Promise<CatalogResponse> => {
  const { data } = await apiClient.get<CatalogResponse>("/grid/catalogs/rubros");
  return data;
};

/**
 * Catálogo de tipos de actuación (para dropdowns)
 */
export const fetchTiposActuacion = async (): Promise<CatalogResponse> => {
  const { data } = await apiClient.get<CatalogResponse>("/grid/catalogs/tipos");
  return data;
};

/**
 * Catálogo de contraproducencias (para dropdowns)
 */
export const fetchContraproducencias = async (): Promise<CatalogResponse> => {
  const { data } = await apiClient.get<CatalogResponse>("/grid/catalogs/contraproducencias");
  return data;
};

/**
 * Catálogo de motivos de comprobación (para dropdowns)
 */
export const fetchMotivosComprobacion = async (): Promise<CatalogResponse> => {
  const { data } = await apiClient.get<CatalogResponse>("/grid/catalogs/motivos-comprobacion");
  return data;
};
