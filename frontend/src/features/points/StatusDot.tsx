import { Box, type SxProps, type Theme } from '@mui/material'
import type { AggregateStatus } from '@/features/map/types'
import { STATUS_DOT_COLOR, STATUS_DOT_GLOW, STATUS_LABELS } from './display'

type Props = {
  status: AggregateStatus
  /** Announce the status to assistive tech; leave off when a visible label sits beside the dot. */
  labelled?: boolean
  sx?: SxProps<Theme>
}

export function StatusDot({ status, labelled = false, sx = [] }: Props) {
  return (
    <Box
      {...(labelled ? { role: 'img', 'aria-label': STATUS_LABELS[status] } : {})}
      sx={[
        {
          width: 7,
          height: 7,
          borderRadius: '50%',
          bgcolor: STATUS_DOT_COLOR[status],
          boxShadow: STATUS_DOT_GLOW[status],
        },
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    />
  )
}
