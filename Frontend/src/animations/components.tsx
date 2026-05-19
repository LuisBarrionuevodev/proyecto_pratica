/**
 * Componentes animados reutilizables
 */

import { motion, type HTMLMotionProps } from 'framer-motion';
import { Box } from '@mui/material';
import { dataTableMrtTypographyScopeSx } from '../styles/mrtGlassDataTablePreset';
import { fadeInUp, fadeIn, tableRefresh } from './variants';

/**
 * Box animado genérico con fadeInUp
 */
export const AnimatedBox = ({ children, ...props }: HTMLMotionProps<'div'>) => (
  <motion.div
    variants={fadeInUp}
    initial="initial"
    animate="animate"
    exit="exit"
    {...props}
  >
    {children}
  </motion.div>
);

/**
 * Tabla animada con refresh suave
 * Ideal para Material React Table o cualquier tabla
 */
export const AnimatedTable = ({ 
  children, 
  isRefreshing,
  ...props 
}: HTMLMotionProps<'div'> & { isRefreshing?: boolean }) => (
  <motion.div
    variants={tableRefresh}
    initial={false}
    animate={isRefreshing ? "initial" : "animate"}
    {...props}
  >
    <Box sx={{ width: "100%", ...dataTableMrtTypographyScopeSx }}>{children}</Box>
  </motion.div>
);

/**
 * Fade simple para transiciones sutiles
 */
export const AnimatedFade = ({ children, ...props }: HTMLMotionProps<'div'>) => (
  <motion.div
    variants={fadeIn}
    initial="initial"
    animate="animate"
    exit="exit"
    {...props}
  >
    {children}
  </motion.div>
);
