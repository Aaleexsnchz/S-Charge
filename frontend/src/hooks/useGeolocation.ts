import { useCallback, useEffect, useState } from 'react'

export type Coords = { lat: number; lng: number }

export type GeolocationStatus = 'idle' | 'prompting' | 'granted' | 'denied' | 'unavailable'

type GeolocationState = {
  coords: Coords | null
  status: GeolocationStatus
}

const GEO_OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  timeout: 10_000,
  maximumAge: 5 * 60 * 1000,
}

export function useGeolocation() {
  const [state, setState] = useState<GeolocationState>({ coords: null, status: 'idle' })

  const request = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setState({ coords: null, status: 'unavailable' })
      return
    }
    setState((prev) => ({ ...prev, status: 'prompting' }))
    navigator.geolocation.getCurrentPosition(
      (position) =>
        setState({
          coords: { lat: position.coords.latitude, lng: position.coords.longitude },
          status: 'granted',
        }),
      (error) =>
        setState({
          coords: null,
          status: error.code === error.PERMISSION_DENIED ? 'denied' : 'unavailable',
        }),
      GEO_OPTIONS,
    )
  }, [])

  useEffect(() => {
    request()
  }, [request])

  return { ...state, request }
}
