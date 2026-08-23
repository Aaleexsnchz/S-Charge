---
status: borrador (redacción de la memoria, nivel conceptual)
---

# Modelo de datos — CPOs, puntos de carga, EVSEs y conectores

El catálogo real de la red de carga procede de la [API REVE](https://www.mapareve.es), el directorio público OCPI 2.2.1 de España. El esquema replica la jerarquía de cuatro niveles de OCPI: un operador gestiona muchas ubicaciones, cada ubicación tiene muchas plazas físicas y cada plaza tiene uno o dos enchufes. La disponibilidad en tiempo real deliberadamente no se retransmite —el límite de 5 peticiones/hora de la API pública de REVE hace inviable un proxy en vivo— y **tampoco se modela**: los puntos se muestran disponibles por defecto, un valor ilustrativo que la memoria declara en lugar de disimular. El catálogo, una vez sembrado, es propiedad de la aplicación en Postgres.

## La jerarquía

```text
Cpo                   la empresa operadora (Iberdrola, Endesa X, Wenea, ...)
 └── ChargingPoint    una ubicación física en el mapa (lat/lng, dirección, horario)
      └── Evse        una plaza de aparcamiento dentro de un punto de carga
           └── Connector   el enchufe real (Type 2, CCS, CHAdeMO) + potencia + tarifa
```

En la instantánea del catálogo REVE en el momento de la siembra, España cuenta con 142 CPOs repartidos en unos 13.700 puntos de carga, que se expanden a unos 42.000 EVSEs y 47.000 conectores — un punto de carga tiene de media tres EVSEs, y la mayoría de los EVSEs llevan un único conector.

## CPO — Charge Point Operator

La entidad legal que gestiona el hardware. Identificada por un `party_id` OCPI (un código alfanumérico corto como `"IBE"`) más el `cif` español. Identificadores estables — los operadores apenas rotan — por lo que `/cpos` es el endpoint más ligero y se agota en dos páginas.

## Punto de carga (Charging Point)

Una ubicación física. La "estación" a la que navega el conductor. Contiene los datos que importan para el mapa y la pantalla de detalle: latitud, longitud, dirección, tipo de aparcamiento, horario de apertura (con el atajo `opening_24_7`) y servicios (comida, aseos, wifi). Cada punto de carga pertenece a un CPO — la FK `charging_points.party_id → cpos.party_id` enlaza con la fila del operador en el catálogo.

Una decisión de nomenclatura que merece registrarse: OCPI llama a estas entidades "**locations**" (de ahí que el endpoint de REVE sea `/locations`). El esquema de la aplicación las renombra a `charging_points` porque se lee con más naturalidad en rutas de código como `GET /api/points` y `usePoint(id)` que el término OCPI, más abstracto. El esquema espejo conserva la semántica OCPI; solo cambia el nombre de la tabla.

La columna `source` distingue los puntos sembrados desde REVE (`reve_seed`) de los puntos privados aportados por usuarios (`user`). Compartir la tabla mantiene la consulta del mapa con una única fuente — ambos tipos de punto aterrizan en la misma forma de respuesta.

## EVSE — Electric Vehicle Supply Equipment

Una plaza física dentro de un punto de carga. Una ubicación con cuatro plazas de aparcamiento tiene cuatro filas EVSE. El EVSE es la unidad de **disponibilidad**: la columna `status` guarda el estado OCPI (`AVAILABLE`, `OCCUPIED`, …).

Esa columna existe, pero **ninguna fuente la alimenta**. REVE no publica un feed continuo de estado, y su endpoint por EVSE `/evses/{evse_id}/status` no se consulta: con unos 42.000 EVSEs en el país, el límite de peticiones de la API pública lo haría inviable. El **estado operativo** (funciona / averiado) es una dimensión distinta, se asume siempre operativo y tampoco se modela. En consecuencia, el `aggregate_status` que colorea el marcador del mapa —`available` si algún EVSE figura disponible, `occupied` si todos los conocidos están ocupados, `unknown` si no hay dato— resuelve hoy a *disponible por defecto*: un valor **ilustrativo, no real**, y así se declara.

**Camino no tomado: la ocupación simulada.** El plan original sí preveía poblar `status`. En su primera versión, calibrando un modelo de ocupación con ACN-Data, el conjunto histórico de sesiones de carga de Caltech; descartado ese conjunto, la segunda versión lo sustituía por un modelo sintético ligero que generase ocupación verosímil por franja horaria. Ambas se abandonaron por la misma razón: producían un dato que quien usara la aplicación leería como real sin serlo, y sostener esa distinción en la defensa costaba más de lo que aportaba la demostración. Se prefirió no modelar la disponibilidad y decirlo abiertamente. La estructura permanece intacta —columna `status`, agregación por punto, colores del marcador—, de modo que una fuente real, ya sea un acuerdo con un CPO o el propio REVE si algún día publicase el feed, encajaría sin tocar el esquema.

## Conector (Connector)

El enchufe real, con las características técnicas por las que filtran los conductores: `standard` (Type 2, CCS, CHAdeMO, etc.), `power_type` (AC monofásico, AC trifásico, DC) y el trío `max_electric_power`, `max_voltage`, `max_amperage`. Una FK anulable `connectors.tariff_id` enlaza con la tabla `tariffs` — REVE devuelve las tarifas por un endpoint separado (`/connectors/tariffs`), razón por la cual los datos de tarifas van por detrás del resto del catálogo durante la siembra.

El conector es además **el grano en el que el precio es único**. Una tarifa OCPI no lleva un precio sino un array de `elements`, cada uno con sus componentes y sus restricciones, y una misma tarifa la comparten conectores de distinta potencia que legítimamente pagan distinto. Por eso las franjas viven en `tariff_elements` —una fila por componente de precio, con las restricciones que lo condicionan— y el precio resuelto para *ahora* se desnormaliza en `connectors.current_price_per_kwh`, junto a `connectors.pricing_kind` (`energy · time · flat · free · unknown`). La tabla `tariffs` conserva solo la identidad de la tarifa y su `raw_data`. El razonamiento está en [precios-y-actualizacion.md](precios-y-actualizacion.md) y en [be-0003](../decisions/be-0003-price-on-the-connector.md).

## Por qué espejo en lugar de proxy

La decisión arquitectónica — poseer el catálogo en Postgres en lugar de hacer proxy en vivo de REVE — viene dictada íntegramente por el límite de peticiones. Cinco peticiones por hora está por debajo del suelo de cualquier experiencia en tiempo real; una carga fría del mapa consumiría la cuota de toda la hora. El espejo permite además añadir puntos privados de los usuarios a la misma tabla, evolucionar el esquema sin coordinarse con el proveedor, y seguir funcionando durante caídas de REVE. El coste es una siembra inicial de ~12 días y un trabajo diario de refresco del catálogo — ambos desatendidos en un tick de cron. Véase [plan.md](../plan.md) para el diagrama de arquitectura y [phases/phase-2.md](../phases/phase-2.md) para la slice de la siembra.
