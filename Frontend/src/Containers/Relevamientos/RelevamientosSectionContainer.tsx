import type { JSX } from "react";
import { useState } from "react";
import { Box, Tab, Tabs, ThemeProvider } from "@mui/material";

import { darkTheme } from "../../configs/theme";
import RelevamientosContainer from "./RelevamientosContainer";
import DenunciasCrudPlaceholder from "./Components/DenunciasCrudPlaceholder";
import { wrapperStyles } from "../Actuaciones/styles/filtroStyles";

const RelevamientosSectionContainer = (): JSX.Element => {
  const [section, setSection] = useState<"relevamientos" | "denuncias">("relevamientos");

  return (
    <ThemeProvider theme={darkTheme}>
      <Box sx={wrapperStyles}>
        <Tabs
          value={section}
          onChange={(_, value) => setSection(value)}
          sx={{ marginBottom: 2 }}
        >
          <Tab label="Relevamientos" value="relevamientos" />
          <Tab label="Denuncias" value="denuncias" />
        </Tabs>

        {section === "relevamientos" ? <RelevamientosContainer /> : <DenunciasCrudPlaceholder />}
      </Box>
    </ThemeProvider>
  );
};

export default RelevamientosSectionContainer;
