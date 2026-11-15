import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import LogoutIcon from '@mui/icons-material/Logout'
import {
  Avatar,
  Box,
  Button,
  CircularProgress,
  IconButton,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useSnackbar } from 'notistack'
import { useEffect, useState } from 'react'
import { Form, useFetcher } from 'react-router'
import { useCurrentUser, userInitial } from '@/features/auth/currentUser'
import { MAX_NAME_LENGTH, type NameActionData } from './actions'
import { useAppVersion } from './useAppVersion'

function NameHeading({ currentName }: { currentName: string }) {
  const fetcher = useFetcher<NameActionData>()
  const { enqueueSnackbar } = useSnackbar()
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(currentName)

  const saving = fetcher.state !== 'idle'
  const error = fetcher.data && 'error' in fetcher.data ? fetcher.data.error : null
  const saved = !saving && fetcher.data !== undefined && 'success' in fetcher.data

  useEffect(() => {
    if (!saved) return
    setEditing(false)
    enqueueSnackbar('Nombre actualizado', { variant: 'success' })
  }, [saved, enqueueSnackbar])

  if (!editing) {
    return (
      <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center', mt: 1 }}>
        <Typography variant="h2">{currentName}</Typography>
        <IconButton
          size="small"
          aria-label="Editar nombre"
          onClick={() => {
            setName(currentName)
            setEditing(true)
          }}
          sx={{ color: 'text.disabled' }}
        >
          <EditOutlinedIcon fontSize="inherit" />
        </IconButton>
      </Stack>
    )
  }

  return (
    <fetcher.Form method="post">
      <Stack direction="row" spacing={0.5} sx={{ alignItems: 'flex-start', mt: 1 }}>
        <TextField
          name="name"
          variant="standard"
          autoFocus
          disabled={saving}
          slotProps={{
            htmlInput: { maxLength: MAX_NAME_LENGTH, style: { textAlign: 'center' } },
          }}
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={error !== null}
          helperText={error}
          sx={{ width: 200 }}
        />
        <IconButton
          type="submit"
          size="small"
          color="primary"
          aria-label="Guardar nombre"
          disabled={saving || name.trim() === ''}
        >
          {saving ? <CircularProgress size={18} /> : <CheckIcon fontSize="inherit" />}
        </IconButton>
        <IconButton
          size="small"
          aria-label="Cancelar"
          disabled={saving}
          onClick={() => setEditing(false)}
          sx={{ color: 'text.disabled' }}
        >
          <CloseIcon fontSize="inherit" />
        </IconButton>
      </Stack>
    </fetcher.Form>
  )
}

export function ProfilePage() {
  const user = useCurrentUser()
  const { data: version } = useAppVersion()
  if (!user) return null

  const name = user.name?.trim() ?? ''
  const initial = userInitial(user)

  return (
    <Box
      sx={{
        p: 2,
        maxWidth: 600,
        mx: 'auto',
        minHeight: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Stack spacing={1} sx={{ alignItems: 'center', textAlign: 'center', py: 2 }}>
        <Avatar
          sx={{
            width: 80,
            height: 80,
            fontSize: 32,
            fontWeight: 600,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
          }}
        >
          {initial}
        </Avatar>
        <NameHeading currentName={name} />
        <Typography variant="body2" color="text.secondary">
          {user.email}
        </Typography>
      </Stack>

      <Box sx={{ mt: 'auto', pt: 3 }}>
        <Form method="post" action="/logout">
          <Button
            type="submit"
            variant="outlined"
            color="error"
            size="large"
            fullWidth
            startIcon={<LogoutIcon />}
          >
            Cerrar sesión
          </Button>
        </Form>
      </Box>

      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ display: 'block', textAlign: 'center', mt: 2 }}
      >
        Versión {version ?? '—'}
      </Typography>
    </Box>
  )
}
