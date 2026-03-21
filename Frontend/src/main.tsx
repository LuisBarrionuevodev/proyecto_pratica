import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from '@mui/material/styles'
import { appTheme } from './configs/theme.ts'
import "leaflet/dist/leaflet.css";
import "react-leaflet-markercluster"

createRoot(document.getElementById('root')!).render(
  <ThemeProvider theme={appTheme}>
    <StrictMode>
      <App />
    </StrictMode>
  </ThemeProvider>
)
