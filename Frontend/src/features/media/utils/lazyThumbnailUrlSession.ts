export type LazyThumbnailUrlPhase = "idle" | "loading" | "ok" | "error";

/** Margen para prefetch de miniaturas próximas al viewport (PERF.2). */
export const LAZY_MEDIA_THUMBNAIL_ROOT_MARGIN = "200px 0px";

export type LazyThumbnailUrlFetch = (
  archivoId: number
) => Promise<{ download_url: string }>;

/**
 * Sesión de carga de URL firmada para una miniatura (un montaje de tile).
 * No cachea entre desmontajes (PERF.3).
 */
export class LazyThumbnailUrlSession {
  private phase: LazyThumbnailUrlPhase = "idle";
  private url: string | null = null;
  private inFlight = false;
  private readonly archivoId: number;
  private readonly fetchUrl: LazyThumbnailUrlFetch;

  constructor(archivoId: number, fetchUrl: LazyThumbnailUrlFetch) {
    this.archivoId = archivoId;
    this.fetchUrl = fetchUrl;
  }

  getPhase(): LazyThumbnailUrlPhase {
    return this.phase;
  }

  getUrl(): string | null {
    return this.url;
  }

  /** Indica si conviene pedir download-url al intersectar el tile. */
  shouldFetchOnVisible(): boolean {
    if (this.phase === "ok" || this.phase === "loading" || this.inFlight) {
      return false;
    }
    return this.phase === "idle";
  }

  /**
   * Llamar cuando el tile entra (o está por entrar) al viewport.
   *
   * @returns true si se inició un fetch en esta llamada.
   */
  async onVisible(): Promise<boolean> {
    if (!this.shouldFetchOnVisible()) return false;
    this.inFlight = true;
    this.phase = "loading";
    try {
      const res = await this.fetchUrl(this.archivoId);
      this.url = res.download_url;
      this.phase = "ok";
      return true;
    } catch {
      this.inFlight = false;
      this.phase = "error";
      return true;
    }
  }

  /** Reintento manual tras error de download-url. */
  async retry(): Promise<void> {
    this.inFlight = false;
    this.url = null;
    this.phase = "idle";
    await this.onVisible();
  }
}
