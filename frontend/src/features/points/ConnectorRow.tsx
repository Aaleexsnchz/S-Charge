import { Stack, Typography } from '@mui/material'
import type { components } from '@/lib/api/schema'
import { connectorLabel, pricingState, shortPriceLabel } from './display'

type Props = {
  connector: components['schemas']['ConnectorRead']
  showPowerType?: boolean
}

export function ConnectorRow({ connector, showPowerType = false }: Props) {
  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{ alignItems: 'center', justifyContent: 'space-between' }}
    >
      <Typography variant="body2">{connectorLabel(connector, { showPowerType })}</Typography>
      <Typography variant="numeric" sx={{ fontSize: 13 }} color="text.secondary">
        {shortPriceLabel(pricingState(connector))}
      </Typography>
    </Stack>
  )
}
