/**
 * Convierte un input file a lista de forma segura (galería móvil puede devolver null).
 */
export function safeFilesFromFileList(files: FileList | null | undefined): File[] {
  if (files == null || files.length === 0) {
    return [];
  }
  return Array.from(files);
}
