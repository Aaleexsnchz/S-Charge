import { CssBaseline, ThemeProvider, createTheme, Container, Typography } from '@mui/material'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

const theme = createTheme({
  palette: {
    primary: { main: '#1976d2' },
    secondary: { main: '#4caf50' },
  },
})

function Dashboard() {
  return <Typography variant="h4">Dashboard — coming soon</Typography>
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Container maxWidth="lg" sx={{ mt: 4 }}>
          <Typography variant="h3" gutterBottom>
            EV Charging Manager
          </Typography>
          <Routes>
            <Route path="/" element={<Dashboard />} />
          </Routes>
        </Container>
      </BrowserRouter>
    </ThemeProvider>
  )
}
