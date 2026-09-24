/**
 * Tipos para animaciones
 */

export interface AnimationConfig {
  duration?: number;
  delay?: number;
  ease?: number[] | string;
}

export interface TransitionConfig {
  type?: 'spring' | 'tween' | 'inertia';
  stiffness?: number;
  damping?: number;
  mass?: number;
  duration?: number;
  ease?: string | number[];
}
