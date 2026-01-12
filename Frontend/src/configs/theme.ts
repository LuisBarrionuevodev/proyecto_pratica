import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  typography: {
    fontFamily: `"Tactic Sans", "Roboto", "Arial", sans-serif`,}
});

export const darkTheme = createTheme({
  palette:{
    mode: 'dark'
  }
})
