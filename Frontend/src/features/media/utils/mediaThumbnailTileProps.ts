import type { MediaArchivoListItem } from "../mediaTypes";

export type MediaThumbnailTilePropsComparable = {
  item: MediaArchivoListItem;
  deleting?: boolean;
  hasDelete: boolean;
};

export function mediaArchivoListItemVisualKey(item: MediaArchivoListItem): string {
  return `${item.archivo_id}|${item.content_type}|${item.original_filename}|${item.byte_size}`;
}

/**
 * Comparación para `React.memo` de miniaturas: ignora callbacks inestables del padre.
 */
export function mediaThumbnailTilePropsAreEqual(
  prev: MediaThumbnailTilePropsComparable,
  next: MediaThumbnailTilePropsComparable
): boolean {
  if (prev.deleting !== next.deleting) return false;
  if (prev.hasDelete !== next.hasDelete) return false;
  return mediaArchivoListItemVisualKey(prev.item) === mediaArchivoListItemVisualKey(next.item);
}

export function mediaArchivoListItemsArrayEqual(
  a: MediaArchivoListItem[],
  b: MediaArchivoListItem[]
): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (mediaArchivoListItemVisualKey(a[i]) !== mediaArchivoListItemVisualKey(b[i])) {
      return false;
    }
  }
  return true;
}
