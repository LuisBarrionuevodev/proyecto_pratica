import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/lato/400.css";
import "@fontsource/lato/700.css";
import "./index.css";
import "leaflet/dist/leaflet.css";
import "react-leaflet-markercluster";

import App from "./App.tsx";
import { GlobalFeedbackProvider } from "./components/feedback/GlobalFeedbackProvider";
import { DigitalizaThemeProvider, setDocumentThemeMode } from "./theme/DigitalizaThemeProvider";
import { applyDigitalizaCssVariables } from "./theme/applyCssVariables";
import { getSemanticColors } from "./theme/colors";
import { readStoredThemeMode } from "./theme/themeStorage";

const initialThemeMode = readStoredThemeMode();
applyDigitalizaCssVariables(getSemanticColors(initialThemeMode));
setDocumentThemeMode(initialThemeMode);

createRoot(document.getElementById("root")!).render(
  <DigitalizaThemeProvider initialMode={initialThemeMode}>
    <GlobalFeedbackProvider>
      <StrictMode>
        <App />
      </StrictMode>
    </GlobalFeedbackProvider>
  </DigitalizaThemeProvider>
);
