import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined'
import { Chip } from '@mui/material'

export function PlaceholderBadge({ label = 'Datos de ejemplo' }: { label?: string }) {
  return (
    <Chip
      size="small"
      icon={<ScienceOutlinedIcon />}
      label={label}
      sx={{
        height: 22,
        fontSize: 11,
        fontWeight: 500,
        color: 'warning.main',
        bgcolor: 'rgba(251,191,36,0.12)',
        border: 'none',
        '& .MuiChip-icon': { color: 'warning.main', fontSize: 15, ml: 0.5 },
      }}
    />
  )
}
