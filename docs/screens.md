# Screen Prompts — Google Stitch Reference

Per-screen prompts for generating UI mockups via Google Stitch. Mobile-first (375px baseline), MUI Material 3 style, PWA.

**Tip:** prepend each prompt with _"Mobile-first React app screen, MUI components, clean minimal design, 375px viewport"_ for consistent output.

---

## Shared shell

Apply to all authenticated screens: top AppBar with app name left, profile avatar right; bottom navigation bar with 4 tabs — Map, Sessions, Simulate, Profile. Light/dark theme support, rounded corners, MUI Material 3 look.

---

## /login

Centered card on neutral background. App logo + tagline ("Charge smarter"). Primary "Continue with Google" button at top (white background, Google G icon left, subtle border, full-width). Horizontal divider with "or" label. Email + password fields below. Primary "Sign in" button, secondary "Create account" link. Small "Continue as guest" text link at bottom.

## / (Dashboard)

Greeting ("Hello, Alejandro"). Four stat tiles in 2×2 grid: total sessions, kWh this month, avg cost/kWh, CO₂ saved. Below: "Upcoming booking" card (station name, time, countdown) or empty state. Then: "Nearby available points" horizontal scroll of 3 cards (name, distance, price, availability dot). CTA button "Open map".

## /map

Full-viewport Leaflet map. Floating horizontal filter chips at top (Availability, Connector type, Max price, Private points toggle). FAB bottom-right for "my location". Tapping a marker opens a bottom sheet (40% height) with station summary: name, operator, status badge (green/yellow/red), connectors list, price per kWh, "View details" + "Navigate" buttons.

## /points/:id

Scrollable detail. Hero: small map snippet showing point location. Below: station name, operator, status chip, address with copy icon. Card with connectors table (type, power kW, availability). Card with price breakdown. Card with recent availability pattern (small bar chart, 24h). Sticky bottom bar: "Book a slot" primary button → opens booking modal (date + time range picker, confirm).

## /sessions

Top: summary bar (total sessions, total kWh, total spent this month). Segmented filter (All / REVE / Private). List of session rows: date, station name, duration, energy (kWh), cost. Tap row → expandable detail with charging curve (line chart from ACN profile) and cost breakdown.

## /simulate

Form card: station selector (searchable), arrival SOC slider (0–100%), target SOC slider, arrival time picker, connector type. Primary "Simulate" button. Results section below: three big stat tiles (predicted duration, predicted energy, predicted cost). Line chart of predicted charging curve. Confidence interval shown as shaded band. "Save as plan" secondary button.

## /statistics

ACN analytics dashboard. Tab bar: Energy / Utilization / Heatmap / Cross-site. Each tab renders 2–3 Recharts visualizations full-width, stacked, with title + short explainer caption under each. Date range selector fixed at top.

## /my-points

Header "My charging points" + FAB "+". Grid of cards (1 column mobile, 2 on tablet): point name, address, public/private toggle switch, status (available/occupied/offline), total bookings this month, revenue. Empty state: illustration + "Register your first point" CTA.

## /new (Register private point)

Multi-step form (stepper at top: Location → Specs → Pricing → Review). Step 1: map picker (tap to drop pin) + address autocomplete. Step 2: connector type, max power kW, access rules. Step 3: €/kWh, commission %. Step 4: summary + "Publish" button with public/private toggle.

## /bookings

Tabs: Upcoming / Past. Upcoming list: card per booking (station, date/time, countdown, cost estimate, "Cancel" button with confirm). Past list: card per booking (station, date, actual cost, "View session" link). Empty states for both.

## /profile

Avatar + name + email at top. List sections: Account (edit profile, change password), Preferences (theme, language, units), Data (export sessions CSV), About (version, PLAN.md link), Sign out button at bottom (destructive color).
