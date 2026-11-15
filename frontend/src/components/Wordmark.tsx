import { Box } from '@mui/material'
import { BOLT_PATH, BOLT_VIEWBOX } from '@/lib/bolt'

type WordmarkProps = {
  size?: number
  accent?: boolean
}

export function Wordmark({ size = 18, accent = true }: WordmarkProps) {
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        fontWeight: 700,
        fontSize: size,
        lineHeight: 1,
        letterSpacing: '-0.02em',
        textTransform: 'lowercase',
        userSelect: 'none',
        color: accent ? 'primary.main' : 'text.primary',
      }}
    >
      s
      <Box
        component="span"
        aria-hidden
        sx={{
          display: 'inline-block',
          width: '0.55em',
          height: '1em',
          transform: 'translateY(0.05em)',
        }}
      >
        <svg
          viewBox={BOLT_VIEWBOX}
          fill="none"
          width="100%"
          height="100%"
          aria-hidden="true"
          style={{ display: 'block' }}
        >
          <path d={BOLT_PATH} fill="currentColor" />
        </svg>
      </Box>
      charge
    </Box>
  )
}
