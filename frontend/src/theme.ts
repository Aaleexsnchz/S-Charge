import { createTheme } from '@mui/material/styles'

const monoFont = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace'

export const theme = createTheme({
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        code: {
          fontFamily: monoFont,
        },
      },
    },
  },
})
