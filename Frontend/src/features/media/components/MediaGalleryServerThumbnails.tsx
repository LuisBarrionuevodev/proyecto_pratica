import { memo } from "react";
import { ImageList } from "@mui/material";
import type { MediaArchivoListItem } from "../mediaTypes";
import { mediaArchivoListItemsArrayEqual } from "../utils/mediaThumbnailTileProps";
import { MediaThumbnailTile } from "./MediaThumbnailTile";

type Props = {
  items: MediaArchivoListItem[];
  deletingId: number | null;
  readOnly: boolean;
  onOpenById: (archivoId: number) => void;
  onDeleteById?: (archivoId: number) => void;
};

function MediaGalleryServerThumbnailsInner({
  items,
  deletingId,
  readOnly,
  onOpenById,
  onDeleteById,
}: Props) {
  if (items.length === 0) return null;
  return (
    <ImageList cols={3} gap={8} sx={{ m: 0, mb: 1 }}>
      {items.map((item) => (
        <MediaThumbnailTile
          key={item.archivo_id}
          item={item}
          onOpenById={onOpenById}
          onDeleteById={readOnly ? undefined : onDeleteById}
          deleting={deletingId === item.archivo_id}
        />
      ))}
    </ImageList>
  );
}

function propsAreEqual(prev: Props, next: Props): boolean {
  if (prev.readOnly !== next.readOnly) return false;
  if (prev.deletingId !== next.deletingId) return false;
  if (prev.onOpenById !== next.onOpenById) return false;
  if (prev.onDeleteById !== next.onDeleteById) return false;
  return mediaArchivoListItemsArrayEqual(prev.items, next.items);
}

/** Grilla READY del servidor aislada del progreso de cola local (PERF.5). */
export const MediaGalleryServerThumbnails = memo(MediaGalleryServerThumbnailsInner, propsAreEqual);
