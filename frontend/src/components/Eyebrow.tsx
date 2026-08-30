import { Typography } from '@mui/material'
import type { ReactNode } from 'react'

/** The app's section voice: the mono utility face, tracked wide and small. It
 *  labels without competing with the figure or heading it introduces. */
export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <Typography
      variant="numeric"
      component="p"
      sx={{
        fontSize: 11,
        fontWeight: 600,
        lineHeight: 1.5,
        letterSpacing: '0.16em',
        textTransform: 'uppercase',
        color: 'text.secondary',
      }}
    >
      {children}
    </Typography>
  )
}
