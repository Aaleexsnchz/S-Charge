import { useEffect, useMemo, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Alert, Box, CircularProgress, Paper, Typography } from '@mui/material'
import { filterFeatures } from './filters'
import { MapFilterBar } from './MapFilterBar'
import { MAP_STYLE_URL, SPAIN_CENTER, SPAIN_ZOOM, STATUS_COLORS } from './mapConfig'
import { PointSheet } from './PointSheet'
import { EMPTY_FILTERS, type MapFilters } from './types'
import { useMapPoints } from './useMapPoints'

const SOURCE_ID = 'charging-points'
const EMPTY_COLLECTION = { type: 'FeatureCollection', features: [] } as const

type SourceData = Parameters<maplibregl.GeoJSONSource['setData']>[0]

function addPointLayers(map: maplibregl.Map, onSelect: (id: string) => void) {
  map.addSource(SOURCE_ID, {
    type: 'geojson',
    data: EMPTY_COLLECTION as unknown as SourceData,
    cluster: true,
    clusterMaxZoom: 13,
    clusterRadius: 50,
  })

  map.addLayer({
    id: 'clusters',
    type: 'circle',
    source: SOURCE_ID,
    filter: ['has', 'point_count'],
    paint: {
      'circle-color': [
        'step',
        ['get', 'point_count'],
        '#42a5f5',
        50,
        '#1e88e5',
        250,
        '#1565c0',
      ],
      'circle-radius': ['step', ['get', 'point_count'], 16, 50, 21, 250, 27],
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffffff',
    },
  })

  map.addLayer({
    id: 'cluster-count',
    type: 'symbol',
    source: SOURCE_ID,
    filter: ['has', 'point_count'],
    layout: {
      'text-field': ['get', 'point_count_abbreviated'],
      'text-font': ['Noto Sans Regular'],
      'text-size': 12,
    },
    paint: { 'text-color': '#ffffff' },
  })

  map.addLayer({
    id: 'unclustered-point',
    type: 'circle',
    source: SOURCE_ID,
    filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-color': [
        'match',
        ['get', 'aggregate_status'],
        'operational',
        STATUS_COLORS.operational,
        'partial',
        STATUS_COLORS.partial,
        'inoperative',
        STATUS_COLORS.inoperative,
        STATUS_COLORS.unknown,
      ],
      'circle-radius': 7,
      'circle-stroke-width': 1.5,
      'circle-stroke-color': '#ffffff',
    },
  })

  map.on('click', 'clusters', (event) => {
    const feature = map.queryRenderedFeatures(event.point, {
      layers: ['clusters'],
    })[0]
    const geometry = feature?.geometry
    if (!feature || geometry.type !== 'Point') return
    const source = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource
    void source
      .getClusterExpansionZoom(feature.properties.cluster_id as number)
      .then((zoom) => {
        map.easeTo({
          center: geometry.coordinates as [number, number],
          zoom,
        })
      })
  })

  map.on('click', 'unclustered-point', (event) => {
    const id = event.features?.[0]?.properties?.id as string | undefined
    if (id) onSelect(id)
  })

  for (const layer of ['clusters', 'unclustered-point']) {
    map.on('mouseenter', layer, () => {
      map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', layer, () => {
      map.getCanvas().style.cursor = ''
    })
  }
}

export function MapPage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [filters, setFilters] = useState<MapFilters>(EMPTY_FILTERS)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data, isPending, isError } = useMapPoints()

  const filtered = useMemo(
    () => (data ? filterFeatures(data, filters) : null),
    [data, filters],
  )

  useEffect(() => {
    if (!containerRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
      center: SPAIN_CENTER,
      zoom: SPAIN_ZOOM,
    })
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      'top-right',
    )
    map.addControl(
      new maplibregl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
      }),
      'top-right',
    )
    map.on('load', () => {
      addPointLayers(map, setSelectedId)
      setMapLoaded(true)
    })

    mapRef.current = map
    return () => {
      mapRef.current = null
      setMapLoaded(false)
      map.remove()
    }
  }, [])

  useEffect(() => {
    if (!mapLoaded || !filtered) return
    const source = mapRef.current?.getSource(SOURCE_ID) as
      | maplibregl.GeoJSONSource
      | undefined
    source?.setData(filtered as unknown as SourceData)
  }, [mapLoaded, filtered])

  return (
    <Box sx={{ position: 'relative', height: '100%', overflow: 'hidden' }}>
      <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />

      <MapFilterBar filters={filters} onChange={setFilters} />

      {isPending && (
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            display: 'grid',
            placeItems: 'center',
            zIndex: 3,
            pointerEvents: 'none',
          }}
        >
          <CircularProgress />
        </Box>
      )}

      {isError && (
        <Box sx={{ position: 'absolute', top: 48, left: 0, right: 0, px: 2, zIndex: 3 }}>
          <Alert severity="error">
            No se pudieron cargar los puntos de carga. Inténtalo de nuevo.
          </Alert>
        </Box>
      )}

      {filtered && filtered.features.length === 0 && (
        <Paper
          elevation={3}
          sx={{
            position: 'absolute',
            top: 56,
            left: '50%',
            transform: 'translateX(-50%)',
            px: 2,
            py: 1,
            zIndex: 2,
          }}
        >
          <Typography variant="body2">
            Ningún punto coincide con los filtros
          </Typography>
        </Paper>
      )}

      <PointSheet pointId={selectedId} onClose={() => setSelectedId(null)} />
    </Box>
  )
}
