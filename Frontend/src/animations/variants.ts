/**
 * Variantes de animación Neo-Brutalistas
 * Snappy, rápidas, sin bounce excesivo
 */

import type { Variants } from 'framer-motion';

/**
 * Fade in hacia arriba (entrada de elementos)
 * Neo-Brutal: rápido y directo, sin suavizado excesivo
 */
export const fadeInUp: Variants = {
  initial: {
    opacity: 0,
    y: 20,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.25, 0.1, 0.25, 1], // Easing más snappy
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: {
      duration: 0.2,
    },
  },
};

/**
 * Fade in simple (entrada suave)
 */
export const fadeIn: Variants = {
  initial: {
    opacity: 0,
  },
  animate: {
    opacity: 1,
    transition: {
      duration: 0.3,
      ease: 'easeOut',
    },
  },
  exit: {
    opacity: 0,
    transition: {
      duration: 0.2,
    },
  },
};

/**
 * Slide desde la derecha (entrada lateral)
 */
export const slideInRight: Variants = {
  initial: {
    x: 50,
    opacity: 0,
  },
  animate: {
    x: 0,
    opacity: 1,
    transition: {
      duration: 0.3,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
  exit: {
    x: -20,
    opacity: 0,
    transition: {
      duration: 0.2,
    },
  },
};

/**
 * Slide desde la izquierda
 */
export const slideInLeft: Variants = {
  initial: {
    x: -50,
    opacity: 0,
  },
  animate: {
    x: 0,
    opacity: 1,
    transition: {
      duration: 0.3,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
  exit: {
    x: 20,
    opacity: 0,
    transition: {
      duration: 0.2,
    },
  },
};

/**
 * Scale up (crecimiento desde el centro)
 * Ideal para modales o elementos emergentes
 */
export const scaleUp: Variants = {
  initial: {
    scale: 0.95,
    opacity: 0,
  },
  animate: {
    scale: 1,
    opacity: 1,
    transition: {
      duration: 0.25,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
  exit: {
    scale: 0.95,
    opacity: 0,
    transition: {
      duration: 0.2,
    },
  },
};

/**
 * Variante para refresh de tabla
 * Suave y casi imperceptible (no anticlimático)
 */
export const tableRefresh: Variants = {
  initial: {
    opacity: 0.5,
  },
  animate: {
    opacity: 1,
    transition: {
      duration: 0.4,
      ease: 'easeOut',
    },
  },
};

/**
 * Stagger para listas
 * Anima items de una lista con delay escalonado
 */
export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
};

export const staggerItem: Variants = {
  initial: {
    opacity: 0,
    y: 10,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
};
