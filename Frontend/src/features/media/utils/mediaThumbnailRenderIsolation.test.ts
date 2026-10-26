import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");
import type { MediaArchivoListItem } from "../mediaTypes";
import {
  mediaArchivoListItemsArrayEqual,
  mediaThumbnailTilePropsAreEqual,
} from "./mediaThumbnailTileProps";
import { LazyThumbnailUrlSession } from "./lazyThumbnailUrlSession";

function archivo(id: number): MediaArchivoListItem {
  return {
    archivo_id: id,
    original_filename: `foto-${id}.jpg`,
    content_type: "image/jpeg",
    byte_size: 1000,
    categoria: "foto_inspeccion",
  };
}

describe("mediaThumbnailRenderIsolation PERF.5", () => {
  it("progreso de un hermano no cambia la firma visual de otros ítems READY", () => {
    const a = archivo(1);
    const b = archivo(2);
    expect(
      mediaThumbnailTilePropsAreEqual(
        { item: a, deleting: false, hasDelete: true },
        { item: a, deleting: false, hasDelete: true }
      )
    ).toBe(true);
    expect(mediaArchivoListItemsArrayEqual([a, b], [a, b])).toBe(true);
    expect(mediaArchivoListItemsArrayEqual([a, b], [a, archivo(2)])).toBe(true);
    expect(mediaArchivoListItemsArrayEqual([a, b], [a])).toBe(false);
  });

  it("reintentar una miniatura no reinicia sesión de otra", async () => {
    const fetchA = vi.fn().mockResolvedValue({ download_url: "https://cdn/a.jpg" });
    const fetchB = vi
      .fn()
      .mockRejectedValueOnce(new Error("net"))
      .mockResolvedValueOnce({ download_url: "https://cdn/b.jpg" });

    const sessionA = new LazyThumbnailUrlSession(1, fetchA);
    const sessionB = new LazyThumbnailUrlSession(2, fetchB);

    await sessionA.onVisible();
    await sessionB.onVisible();
    expect(sessionA.getPhase()).toBe("ok");
    expect(sessionB.getPhase()).toBe("error");

    await sessionB.retry();
    expect(sessionB.getPhase()).toBe("ok");
    expect(sessionA.getPhase()).toBe("ok");
    expect(sessionA.getUrl()).toBe("https://cdn/a.jpg");
    expect(fetchA).toHaveBeenCalledTimes(1);
    expect(fetchB).toHaveBeenCalledTimes(2);
  });

  it("eliminar un archivo no altera la comparación de los restantes", () => {
    const remaining = [archivo(10), archivo(12)];
    const sameRemaining = [archivo(10), archivo(12)];
    expect(mediaArchivoListItemsArrayEqual(remaining, sameRemaining)).toBe(true);
    expect(mediaArchivoListItemsArrayEqual(remaining, [archivo(10), archivo(11)])).toBe(false);
  });

  it("las tres entradas comparten galería y miniaturas memoizadas", () => {
    const gallery = read("src/features/media/components/ActuacionMediaGallery.tsx");
    const category = read("src/features/media/components/MediaGalleryCategoryBlock.tsx");
    const upload = read("src/features/media/components/MediaUploadSection.tsx");
    const completar = read("src/Containers/CompletarTrabajos/components/CompletarTrabajoModal.tsx");
    const inspector = read("src/Containers/Actuaciones/Components/InspectorCargarFotosDialog.tsx");
    const editar = read("src/Containers/Actuaciones/Components/ActuacionDetalleDialog.tsx");
    expect(gallery).toContain("MediaGalleryCategoryBlock");
    expect(category).toContain("MediaGalleryServerThumbnails");
    expect(upload).toContain("MediaGalleryServerThumbnails");
    expect(completar).toContain("MediaUploadSection");
    expect(inspector).toContain("ActuacionMediaGallery");
    expect(editar).toContain("ActuacionMediaGallery");
  });

  it("reconciliación READY de un ítem no invalida firma de otros en lista", () => {
    const before = [archivo(5), archivo(6)];
    const after = [archivo(5), { ...archivo(6), byte_size: 1000 }];
    expect(mediaArchivoListItemsArrayEqual(before, after)).toBe(true);
    const changed = [archivo(5), { ...archivo(6), original_filename: "otro.jpg" }];
    expect(mediaArchivoListItemsArrayEqual(before, changed)).toBe(false);
  });
});
