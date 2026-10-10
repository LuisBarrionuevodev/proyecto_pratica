import { apiClient } from "./apiClient";
import type {
  MediaCategoria,
  TIPOS_DOCUMENTO_FOTO_ACTA,
  TIPOS_DOCUMENTO_FOTO_LOCAL,
} from "../features/media/mediaConstants";
import type { MediaUploadOrigin } from "../features/media/mediaUploadOrigin";
import type { RutaItemArchivosListResponse } from "../features/media/mediaTypes";

export type UploadIntentBody = {
  categoria: MediaCategoria;
  tipo_documento?: string | null;
  filename: string;
  content_type: string;
  byte_size: number;
  sha256: string;
  upload_origin?: MediaUploadOrigin;
};

export type UploadIntentResponse = {
  archivo_id: number;
  upload_url: string;
  expires_at: string;
  status?: "PENDING" | "READY";
};

export async function postMediaUploadIntent(
  rutaItemId: number,
  body: UploadIntentBody
): Promise<UploadIntentResponse> {
  const { data } = await apiClient.post<UploadIntentResponse>(
    `/ruta-items/${rutaItemId}/archivos/upload-intents`,
    body
  );
  return data;
}

export async function postMediaComplete(archivoId: number): Promise<{ archivo_id: number; status: string }> {
  const { data } = await apiClient.post(`/archivos/${archivoId}/complete`);
  return data;
}

export async function getMediaDownloadUrl(archivoId: number): Promise<{ download_url: string; expires_at: string }> {
  const { data } = await apiClient.get(`/archivos/${archivoId}/download-url`);
  return data;
}

export async function getRutaItemArchivos(rutaItemId: number): Promise<RutaItemArchivosListResponse> {
  const { data } = await apiClient.get<RutaItemArchivosListResponse>(
    `/ruta-items/${rutaItemId}/archivos`
  );
  return data;
}

export async function deleteArchivo(archivoId: number): Promise<{ archivo_id: number; status: string }> {
  const { data } = await apiClient.delete(`/archivos/${archivoId}`);
  return data;
}

export async function postFinalizarFotosPorAhora(rutaItemId: number): Promise<{
  ruta_item_id: number;
  fotos_pendientes_cerradas_at: string;
  already_closed?: boolean;
}> {
  const { data } = await apiClient.post(
    `/ruta-items/${rutaItemId}/fotos/finalizar-por-ahora`
  );
  return data;
}

export type TipoDocumentoFotoActa = (typeof TIPOS_DOCUMENTO_FOTO_ACTA)[number];
export type TipoDocumentoFotoLocal = (typeof TIPOS_DOCUMENTO_FOTO_LOCAL)[number];
