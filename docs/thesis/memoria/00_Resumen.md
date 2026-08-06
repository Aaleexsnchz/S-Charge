# Resumen

La recarga pública de vehículo eléctrico en España está repartida entre decenas de operadores,
cada uno con su propia aplicación, su propio registro de usuario y su propia tarifa. El Estado
publica un mapa oficial de la infraestructura —dirigido por el Ministerio para la Transición
Ecológica y el Reto Demográfico y operado por Red Eléctrica de España— que resuelve el
descubrimiento de puntos y la planificación de rutas, pero no la gestión de la recarga: no
reserva, no estima lo que costará y durará una sesión para un modelo concreto de coche, no
propone cuándo conviene cargar según el precio de la electricidad y no da cabida al punto de un
particular.

Este trabajo diseña, construye, despliega y argumenta *S-Charge*, una aplicación web progresiva
que ocupa ese hueco. El sistema replica en base de datos propia el catálogo nacional de puntos
de recarga publicado por el registro oficial —142 operadores, unos 13.700 puntos de carga,
42.000 equipos de suministro y 47.000 conectores— respetando el límite de cinco peticiones por
hora de su API pública, restricción que condiciona toda la arquitectura: el catálogo se siembra
en unos doce días de procesos por lotes acotados e idempotentes y a partir de ahí es propiedad
de la aplicación. Sobre esa base se añaden la ingesta diaria del precio regulado horario de la
electricidad, un catálogo curado de vehículos y una simulación de recarga previa que estima
energía, duración y coste a partir de las especificaciones del coche y del conector.

La aplicación está desplegada y accesible públicamente bajo HTTPS, es instalable en el móvil y
se entrega mediante una cadena de integración y despliegue continuos. La memoria documenta
también lo que queda formulado y no implementado —la optimización del momento de la recarga
contra la curva de precios y la capa de asistencia conversacional—, el marco regulador que
aplica al sistema, su viabilidad económica y las carencias conocidas frente a una explotación
real. Un criterio recorre el trabajo: distinguir de forma explícita qué parte es dato real, qué
parte es estimación y qué parte no existe todavía. Por eso la disponibilidad en tiempo real de
los puntos no se modela ni se simula, y se declara.

**Palabras clave:** vehículo eléctrico; infraestructura de recarga; aplicación web progresiva;
OCPI; PVPC; optimización de la recarga; ingeniería web.

---

# Abstract

Public electric-vehicle charging in Spain is split across dozens of operators, each with its own
app, its own sign-up and its own tariff. The state publishes an official map of the
infrastructure —overseen by the Ministry for the Ecological Transition and operated by Red
Eléctrica de España— which solves point discovery and route planning, but not charge management:
it does not book, it does not estimate what a session will cost and how long it will take for a
specific car model, it does not suggest when to charge based on the price of electricity, and it
has no place for a privately owned charging point.

This work designs, builds, deploys and argues the viability of *S-Charge*, a progressive web
application that fills that gap. The system mirrors the national charging-point catalogue
published by the official registry into its own database —142 operators, some 13,700 charging
points, 42,000 supply equipment units and 47,000 connectors— under the five-requests-per-hour cap
of its public API, a constraint that shapes the entire architecture: the catalogue is seeded over
roughly twelve days of bounded, idempotent batch runs and is owned by the application from then
on. On that foundation it adds daily ingestion of the regulated hourly electricity price, a
curated vehicle catalogue, and a pre-charge simulation that estimates energy, duration and cost
from the specifications of the car and the connector.

The application is deployed and publicly reachable over HTTPS, installable on a phone, and
delivered through a continuous integration and deployment pipeline. The report also documents
what remains formulated but not implemented —charge-schedule optimisation against the price curve
and a conversational assistance layer— together with the regulatory framework that applies to the
system, its economic viability and its known gaps against real-world operation. One criterion
runs throughout: stating explicitly which part is real data, which part is an estimate and which
part does not exist yet. That is why real-time availability of charging points is neither
modelled nor simulated, and is declared as such.

**Keywords:** electric vehicle; charging infrastructure; progressive web app; OCPI; PVPC; charge
scheduling optimisation; web engineering.
