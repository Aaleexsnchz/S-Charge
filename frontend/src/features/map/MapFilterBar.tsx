import { Box, Chip } from '@mui/material'
import { standardLabel } from '@/features/points/display'
import type { MapFilters } from './types'

const STANDARD_OPTIONS = ['IEC_62196_T2', 'IEC_62196_T2_COMBO', 'CHADEMO']
const PRICE_OPTIONS = [0.4, 0.6]

type Props = {
  filters: MapFilters
  onChange: (filters: MapFilters) => void
}

export function MapFilterBar({ filters, onChange }: Props) {
  return (
    <Box
      sx={{
        position: 'absolute',
        top: 8,
        left: 0,
        right: 0,
        zIndex: 2,
        display: 'flex',
        gap: 1,
        px: 1.5,
        overflowX: 'auto',
        scrollbarWidth: 'none',
        '& .MuiChip-root': {
          flexShrink: 0,
          bgcolor: 'rgba(18,24,33,0.9)',
          backdropFilter: 'blur(12px)',
          border: (t) => `1px solid ${t.palette.tokens.border}`,
        },
        '& .MuiChip-root.MuiChip-colorPrimary': {
          bgcolor: 'primary.main',
          border: 'none',
        },
      }}
    >
      <Chip
        label="Disponibles"
        size="small"
        color={filters.onlyAvailable ? 'primary' : 'default'}
        onClick={() => onChange({ ...filters, onlyAvailable: !filters.onlyAvailable })}
      />
      {STANDARD_OPTIONS.map((standard) => (
        <Chip
          key={standard}
          label={standardLabel(standard)}
          size="small"
          color={filters.standard === standard ? 'primary' : 'default'}
          onClick={() =>
            onChange({
              ...filters,
              standard: filters.standard === standard ? null : standard,
            })
          }
        />
      ))}
      {PRICE_OPTIONS.map((price) => (
        <Chip
          key={price}
          label={`≤ ${price.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €/kWh`}
          size="small"
          color={filters.maxPrice === price ? 'primary' : 'default'}
          onClick={() =>
            onChange({
              ...filters,
              maxPrice: filters.maxPrice === price ? null : price,
            })
          }
        />
      ))}
    </Box>
  )
}
