import type { MediaCategoria1A } from "./mediaConstants";

export type MediaUploadFilePhase =
  | "pending"
  | "preparing"
  | "uploading"
  | "verifying"
  | "ready"
  | "error";

export type MediaQueuedFile = {
  localId: string;
  file: File;
  categoria: MediaCategoria1A;
  tipoDocumento: string | null;
  phase: MediaUploadFilePhase;
  progressPct: number;
  errorMessage: string | null;
  archivoId: number | null;
  previewUrl: string | null;
};

export type MediaArchivoListItem = {
  archivo_id: number;
  original_filename: string;
  content_type: string;
  byte_size: number;
  uploaded_at: string;
  tipo_documento?: string | null;
  categoria: MediaCategoria1A;
};

export type RutaItemArchivosListResponse = {
  foto_acta: MediaArchivoListItem[];
  foto_documentacion_local: MediaArchivoListItem[];
};

export type MediaUploadProgress = {
  globalPct: number;
  activeLabel: string | null;
};
