# Screens — Design generation prompt

A single, self-contained prompt for generating the full UI of **s-charge** (Smart Charge) in Google Stitch or Claude Design. Copy the block below verbatim and paste it into the generator. Dark-mode only, mobile-first, MUI Material 3 aesthetic, PWA.

---

```text
Design a complete, production-grade mobile-first web app called "s-charge" (short for "Smart Charge"). It is a PWA for managing EV charging that combines the REVE public charging network in Spain with user-contributed private charging points, plus analytics and simulation powered by real historical session data. Generate every screen listed below in one consistent visual pass.

## Global rules

- Viewport: design for 375 × 812 px (iPhone baseline). Layout must also flow cleanly at 768 px (tablet) and 1280 px (desktop). Use safe-area insets on mobile.
- Dark mode ONLY. No light theme. No theme toggle anywhere in the UI.
- Component library: MUI (Material UI) Material 3 primitives — AppBar, Card, Chip, TextField, Button, BottomNavigation, Dialog, Drawer, Tabs, Switch, Slider, Stepper, ToggleButtonGroup, Skeleton, Snackbar, List, ListItem, Avatar, Autocomplete.
- Iconography: Material Symbols (outlined style). 24 px default, 20 px inline.
- No generic stock photography. No gradient blobs. No lorem-ipsum placeholder text — use plausible EV-charging copy in Spanish (Castilian) for headings/labels with English acceptable for technical terms (kWh, SOC, CCS).

## Brand

- Wordmark: "s-charge", set in Inter 700, lowercase, with a subtle electric bolt glyph replacing the hyphen (a thin stylized ⚡). Accent colour (see palette).
- Full name: "Smart Charge". Used in the login tagline and on the install splash only.
- Personality: technical, calm, trustworthy, slightly futuristic — not playful, not glossy.

## Palette (dark mode, WCAG AA)

- Canvas background: #0A0E13 (near-black, faint blue undertone)
- Elevated surface (cards, sheets): #121821
- Higher elevation (modals, menus, popovers): #1A2230
- Hairline border / divider: #242C3A
- Primary text: #E7ECF2
- Secondary text: #9AA6B5
- Muted / placeholder text: #6A7686
- Accent (primary actions, active nav, focus ring, brand): #7FE7C4 (mint-electric)
- Text on accent fill: #0A0E13
- Status — available: #4ADE80 · occupied/partial: #FBBF24 · offline/error: #EF4444
- Info highlight: #60A5FA

## Typography

- Family: Inter (system stack fallback). Base 16 px.
- Scale: 12 / 14 / 16 / 18 / 22 / 28 / 34. Weights 400 / 500 / 600 / 700.
- Line height: 1.3 on headings, 1.5 on body.
- Tabular numerals on every metric, price, and stat value.

## Shape, elevation, density

- Radius: 12 px cards and inputs, 16 px bottom sheets and modals, 999 px chips and pill buttons. No sharp corners.
- Elevation: flat surfaces with a 1 px inner border rgba(255,255,255,0.04) instead of drop shadows. Modals and popovers use a soft shadow rgba(0,0,0,0.5) 24 px blur.
- Gutters 16 px, section spacing 24 px, hit target minimum 48 px. Comfortable density, not compact.
- Buttons: contained = accent fill + #0A0E13 text; outlined = 1 px accent border on transparent; text = accent text, no background. Destructive variants use #EF4444.

## App shell (all authenticated screens)

- Top AppBar (56 px): "s-charge" wordmark in accent on the left; circular profile avatar (user initial on accent background) on the right. Transparent over content with a bottom hairline border.
- Bottom navigation on mobile (64 px, safe-area inset): four tabs — Map (map icon), Sessions (history icon), Simulate (flash-auto icon), Profile (person icon). Active tab = accent icon + label; inactive = muted icon + label.
- At ≥ 768 px replace bottom nav with a 240 px left rail: wordmark top, four nav entries with labels, active entry has a 3 px accent left border and a subtle accent-tinted background.

## Data-surface states

Every surface that loads data MUST show three states:
1. Loading → Skeleton placeholders matching the real shape (no generic spinners).
2. Empty → centered line-art icon (thin 1.5 px strokes in accent), one-sentence explainer in secondary text, one primary CTA.
3. Error → inline alert at the top of the region, soft red tint background, one-line message, trailing retry icon button.

## Screens to generate

### 1. /login (unauthenticated)

Centered auth card (max width 400 px, 24 px padding) on the canvas.
- Wordmark "s-charge" at top (28 px, accent, 700) with tagline "Carga más inteligente" in secondary text directly below.
- "Continuar con Google" button: full-width, white fill, #0A0E13 text, Google G icon on the left, 48 px tall.
- Horizontal divider with "o" label in muted text, 24 px vertical margin.
- Email TextField (label "Correo electrónico").
- Password TextField (label "Contraseña", eye icon toggle on the right).
- "¿Olvidaste tu contraseña?" text link, right-aligned, below the password field.
- "Iniciar sesión" primary accent button, full-width, 48 px.
- Bottom copy: "¿Nuevo aquí? Crear cuenta" where the second part is an accent link.
- States: error shows inline alert above fields; loading disables fields and shows spinner in the button.

### 2. / (Dashboard)

Scrollable page, 16 px gutters.
- Greeting "Hola, Alejandro" (28 px, 600) over muted subtitle with today's date in long Spanish format.
- 2×2 stat grid, 12 px gap. Tiles: "Sesiones este mes", "kWh entregados", "€/kWh medio", "CO₂ evitado (kg)". Each tile: small secondary-text label, large value (22 px, 600), delta vs last month (accent if positive, red if negative, with up/down arrow).
- "Próxima reserva" card full-width. Filled state: station name (600), date/time, live countdown in accent, status chip, "Ver" text link. Empty: icon + "Sin reservas" + "Buscar estación" accent button.
- Section header "Puntos cercanos disponibles" with "Ver mapa" accent text link on the right.
- Horizontal snap-scroll of 3 point cards (72 % viewport width each): name, distance (km), €/kWh, connector chip, status dot.
- Sticky bottom CTA above bottom nav: full-width outlined accent "Abrir mapa".

### 3. /map

Full-viewport MapLibre GL map with dark Protomaps vector tiles (land #0A0E13, water #121821, roads #242C3A, labels in #9AA6B5).
- Top (safe-area inset): floating horizontal scroll of filter chips — "Disponible", "Type 2", "CCS", "CHAdeMO", "< €0.40/kWh", "Puntos privados". Active chip: accent fill + #0A0E13 text. Inactive: #121821 fill, primary text, 1 px border.
- Top-right: circular icon button (search) that opens a full-screen search sheet.
- Bottom-right FAB (above bottom nav): locate-me icon, accent fill, 56 px.
- Markers: REVE points as coloured circles (available/occupied/offline). Clusters: larger circles with count, accent stroke. Private points use a distinct square marker to differentiate from public ones.
- Tap marker → bottom sheet at 45 % height with drag handle: station name (600), operator (secondary), status chip, address row with copy icon, connector chips with power ("CCS 150 kW"), large price "€0.42 / kWh" (600), pair of side-by-side buttons: outlined "Detalles" + contained "Navegar" (opens Google Maps).
- Empty: centered card "No hay estaciones en esta zona" + "Restablecer filtros" accent text link. Error: top toast "No se pudieron cargar las estaciones" + retry icon. Loading: 2 px accent progress bar at top.

### 4. /points/:id

Scrollable detail page.
- Hero (200 px): small MapLibre snippet centred on the point, dark theme, non-interactive, marker pinned, radial fade at edges. Back chevron floats top-left.
- Header: station name (28 px, 600), operator (secondary), status chip.
- Address row: text + copy icon + "Abrir en Mapas" text link.
- Connectors card: list of rows — connector icon, type name, power (kW), availability dot. Unavailable rows dimmed.
- Price card: "€0.42 / kWh" (34 px, 700, accent); muted sub-line "IVA incluido · Tarificación por minuto tras el 80 % SOC".
- Availability card: 24 h pattern as an ECharts bar chart with dark tooltip, accent bars, muted axis. Caption "Últimos 30 días".
- Sticky bottom bar (72 px): full-width accent "Reservar" button opening a Dialog with date picker, start/end time, connector selector, summary row (duration + estimated cost), "Confirmar reserva" accent button, "Cancelar" text button.

### 5. /sessions

- Top summary strip: three inline stats ("Sesiones", "kWh", "€ gastado") with muted labels above and large values below, separated by vertical hairlines.
- Segmented ToggleButtonGroup full-width: "Todas / REVE / Privadas", 40 px, accent fill on selected.
- Date range text button on the right ("Últimos 30 días", opens a range calendar picker).
- Session rows: 12 px radius cards, 16 px padding, 8 px vertical gap. Top row: date (secondary, small) + station name (500) + trailing expand chevron. Bottom row: "1 h 24 min · 28.4 kWh · €11.92" — bullets in secondary, cost in primary on the far right.
- Expanded state: ECharts line chart of charging curve (power vs time, accent line with soft filled area below), muted axis, + cost breakdown (energía, comisión, total).
- Empty: illustration + "Aún no tienes sesiones" + "Buscar un cargador" accent button.

### 6. /simulate

Two-column layout at ≥ 768 px (form left, results right); stacked on mobile.
- Form card (16 px padding, 12 px radius):
  - Section title "Simular una carga"
  - Searchable Autocomplete "Estación" with recent stations listed first.
  - Slider "SOC de llegada" (0–100 %), accent track fill, value in accent badge on the right.
  - Slider "SOC objetivo" (0–100 %), same styling, lower bound = arrival SOC + 1.
  - "Hora de llegada" date + time picker.
  - Connector chip group (single select).
  - Primary accent "Simular" button, full-width, 48 px.
- Results section (hidden until first run):
  - Row of three big stat tiles: "Duración prevista" (min), "Energía prevista" (kWh), "Coste previsto" (€). Values 28 px 700, muted labels.
  - ECharts chart: predicted charging curve. Mean line in accent, 90 % confidence band as accent-transparent fill. X axis = tiempo, Y axis = potencia (kW). Tooltip shows SOC + power.
  - Plain-language caption under the chart: "La mayoría de sesiones en esta estación terminan entre 35 y 55 min en condiciones similares."
  - Outlined "Guardar como plan" + text "Compartir" buttons.

### 7. /statistics

ACN analytics dashboard. Sticky top region: pill-style date range picker on the left, segmented tab bar on the right: "Energía / Uso / Mapa de calor / Estaciones".
- Each tab shows 2–3 full-width ECharts cards stacked with 24 px gap. Every card: title (18 px, 600), one-line explainer caption in secondary text, chart (320 px tall mobile, 400 px ≥ 768 px), trailing "Descargar datos" text link.
- Energía tab: daily energy-delivered line chart + energy-by-hour-of-day bar chart.
- Uso tab: station utilization stacked-area over time + top-10 busiest stations bar chart.
- Mapa de calor tab: heatmap by hour × day-of-week (ramp #1A2230 → #7FE7C4) + GitHub-style calendar heatmap over the ACN sampling window.
- Estaciones tab: grouped bar chart comparing stations + scatter of session duration vs energy delivered.
- Chart theme: #0A0E13 background, #242C3A grid lines, #9AA6B5 axis labels, accent primary series, muted secondary series, tooltip uses #1A2230 background + primary text.

### 8. /my-points

- Header "Mis puntos de carga" (28 px, 600) + FAB "+" on the right (accent, 48 px, routes to /new).
- Grid of owner cards: 1 col mobile, 2 tablet, 3 desktop. Each card:
  - Map snippet (80 px tall) at top, rounded top corners, pin dropped.
  - Point name (600), address (secondary, max 2 lines with ellipsis).
  - Row of badges: público/privado Switch with label, status dot ("Disponible" / "Ocupado" / "Fuera de servicio").
  - Bottom stats: "Reservas este mes" and "Ingresos este mes" — small muted label + primary value.
  - Trailing kebab icon menu (editar, pausar, eliminar).
- Empty: centred thin-line plug illustration in accent + "Aún no has registrado ningún punto" + accent "Registrar mi primer punto".

### 9. /new (Register private point)

Multi-step form, horizontal Stepper at top (4 steps: Ubicación → Especificaciones → Precio → Revisión). Active step in accent, completed steps show a check.
- Step 1 Ubicación: MapLibre map 300 px tall with a draggable centre pin (tap to drop). Address autocomplete TextField below. Resulting address summary card with an "Editar" text link.
- Step 2 Especificaciones: connector type chip group (single-select, icons per type), "Potencia máxima" TextField (numeric, suffix "kW"), access-rules RadioGroup — "24/7", "Horario comercial", "Personalizado" (reveals a weekly availability editor).
- Step 3 Precio: "€/kWh" TextField (numeric, suffix), read-only commission card "Comisión de la plataforma: 8 %", accent-outlined estimated-earnings card with projected monthly revenue and caption "Basado en el uso medio de puntos similares cercanos".
- Step 4 Revisión: summary card listing all values with per-section "Editar" text links; público/privado Switch with helper text; full-width accent "Publicar punto" button + outlined "Guardar borrador".
- Each step has outlined "Atrás" (disabled on step 1) and accent "Siguiente" (disabled until the step validates). Field errors inline in red, summarised at the bottom.

### 10. /bookings

- Tabs full-width at top: "Próximas / Pasadas", accent underline on selected.
- Próximas cards: station (600) + status chip ("Confirmada" accent / "Pendiente" amber); middle row date and start–end time with live countdown in accent if < 24 h; bottom row estimated cost on the left + outlined red "Cancelar" text button on the right (opens confirm Dialog).
- Pasadas cards: station (500) · date (secondary); actual cost (600); trailing accent "Ver sesión" text link to /sessions?id=...
- Empty — Próximas: illustration + "No tienes reservas próximas" + accent "Buscar estación". Empty — Pasadas: "Aún no has utilizado ninguna reserva" + muted explainer.

### 11. /profile

- Top: circular avatar (80 px, initial on accent), name (22 px, 600), email (secondary), outlined accent "Editar perfil".
- Stat strip below avatar: three inline stats ("Sesiones", "kWh totales", "Miembro desde") separated by hairlines.
- MUI List with subheaders, each item has a leading icon, primary text, trailing chevron:
  - Cuenta: Editar perfil · Cambiar contraseña · Proveedores vinculados (muestra Google).
  - Preferencias: Idioma (actual: Español) · Unidades (km / kWh, read-only) · Notificaciones.
  - Datos: Exportar sesiones (CSV) · Descargar mis datos (RGPD) · Eliminar cuenta (rojo destructivo).
  - Información: Versión de la app (texto a la derecha) · Términos de uso · Privacidad.
- Bottom: full-width outlined red "Cerrar sesión" button.
- NO theme toggle — the app is dark-mode only.

## Output expectations

- Render every screen at 375 px width with the bottom navigation visible (except /login which has no shell).
- Also render the desktop variant (1280 px) for the three most visually complex screens: /map, /statistics, /simulate — showing the left-rail nav replacing the bottom nav.
- Use the exact colour tokens, typography, and radii above — do not introduce new palette colours.
- Copy is primarily in Spanish (Castilian). Technical units (kWh, SOC, CCS, Type 2, CHAdeMO) stay in their canonical form.
- Deliver consistent spacing and corner radii across every screen; the screens must feel like a single app, not a collage.
```

---

## Notes

- `/bookings` is a Phase 5 screen; generating it early is fine but the feature only becomes real once private-point bookings ship.
- If the generator drifts to iOS styling, append "Android Material 3, not iOS Human Interface Guidelines" to the prompt.
- For per-screen iteration after the first pass, isolate a single screen section from the block and re-prompt with "regenerate only this screen, keep all other tokens identical".
