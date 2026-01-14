/**
 * Custom Renderers para Glide Data Grid
 * 
 * Este módulo exporta todos los custom renderers disponibles
 * para usar en el DataEditor de Glide.
 */

export { badgeRenderer, createBadgeCell, type BadgeCell } from "./BadgeCell";
export {
    sparklineRenderer,
    createSparklineCell,
    generateRandomSparklineData,
    type SparklineCell,
} from "./SparklineCell";

/**
 * Array con todos los renderers disponibles
 * Usar este array en la prop customRenderers del DataEditor
 */
import { badgeRenderer } from "./BadgeCell";
import { sparklineRenderer } from "./SparklineCell";

export const allCustomRenderers = [badgeRenderer, sparklineRenderer];
