import { Box, type SxProps, type Theme, Typography } from '@mui/material'
import { Eyebrow } from './Eyebrow'

type StatValueProps = {
  value: string
  unit?: string
  sx?: SxProps<Theme>
}

export function StatValue({ value, unit, sx }: StatValueProps) {
  return (
    <Typography variant="numeric" sx={sx}>
      {value}
      {unit && (
        <Box component="span" sx={{ fontSize: 11, color: 'text.secondary', ml: 0.4 }}>
          {unit}
        </Box>
      )}
    </Typography>
  )
}

type StatProps = StatValueProps & {
  label: string
  valueSx?: SxProps<Theme>
}

/** A labelled figure: eyebrow above, value and unit below. */
export function Stat({ label, value, unit, sx, valueSx }: StatProps) {
  return (
    <Box sx={sx}>
      <Eyebrow>{label}</Eyebrow>
      <StatValue value={value} unit={unit} sx={valueSx} />
    </Box>
  )
}
