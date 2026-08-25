# S-Charge: PWA para la gestión unificada de la recarga de vehículos eléctricos en España

Trabajo de Fin de Máster · Universidad Carlos III de Madrid · Escuela Politécnica Superior
Autor: Alejandro Sánchez Bardera

> **PENDIENTE:** completar la portada según la normativa de la UC3M — máster cursado, curso
> académico, nombre del tutor y fecha de defensa. La página I es la portada y la II una página
> de cortesía en blanco; este resumen va en la página III y no debe superar una página.

## Resumen

La recarga pública de vehículo eléctrico en España está repartida entre decenas de operadores y,
sobre ellos, un ecosistema de aplicaciones parciales: unas descubren puntos y activan la sesión
en redes ajenas, otras planifican rutas, otras calculan la hora más barata para cargar en casa y
otras permiten que un particular ofrezca su enchufe. Cada capacidad tiene ya al menos un producto
que la sirve; lo que no existe es una aplicación que las reúna, de modo que el conductor acaba
con varias instaladas y uniendo a mano lo que ninguna une: la recarga pública con la doméstica, y
el precio por kWh con lo que esa recarga concreta va a costarle a su coche concreto. El mapa
oficial del Estado —dirigido por el Ministerio para la Transición Ecológica y el Reto Demográfico
y operado por Red Eléctrica de España— resuelve el descubrimiento de puntos y la planificación de
rutas, pero no la gestión de la recarga, y no puede resolverla: su mandato es informativo y su
operador tiene vedado competir en el mercado.

Este trabajo propone *S-Charge*, la aplicación web progresiva que ocuparía ese hueco, y la
construye, despliega y argumenta hasta donde alcanza un trabajo de fin de máster. El sistema
replica en base de datos propia el catálogo nacional de puntos
de recarga publicado por el registro oficial —142 operadores, unos 13.700 puntos de carga,
42.000 equipos de suministro y 47.000 conectores— respetando el límite de cinco peticiones por
hora de su API pública, restricción que condiciona toda la arquitectura: el catálogo se siembra
en unos doce días de procesos por lotes acotados e idempotentes y a partir de ahí es propiedad
de la aplicación. Sobre esa base se añaden la ingesta diaria del precio regulado horario de la
electricidad, un catálogo curado de vehículos y una simulación de recarga previa que estima
energía, duración y coste a partir de las especificaciones del coche y del conector.

La aplicación está desplegada y accesible públicamente bajo HTTPS, es instalable en el móvil y
se entrega mediante una cadena de integración y despliegue continuos. La memoria documenta
también lo que queda diseñado y no implementado —la optimización del momento de la recarga
contra la curva de precios, los puntos aportados por particulares, las sesiones de recarga cobradas
contra un monedero simulado y la capa de asistencia conversacional—, el marco regulador que
aplica al sistema, su viabilidad económica y las carencias conocidas frente a una explotación
real. Un criterio recorre el trabajo: distinguir de forma explícita qué parte es dato real, qué
parte es estimación y qué parte no existe todavía. Por eso el estado real de la red pública, que
hoy no publica ninguna fuente accesible, no se simula: la aplicación muestra la ocupación que
ella misma genera y declara el resto como desconocido.

**Palabras clave:** vehículo eléctrico; infraestructura de recarga; aplicación web progresiva;
OCPI; PVPC; optimización de la recarga; ingeniería web.

---

## Abstract

*S-Charge: A Progressive Web App for Unified Electric-Vehicle Charging Management in Spain*

Public electric-vehicle charging in Spain is split across dozens of operators and, on top of
them, an ecosystem of partial applications: some find charging points and start sessions on other
networks, some plan long trips, some work out the cheapest hour to charge at home, and some let a
private owner offer their socket. Every one of those capabilities already has at least one
product serving it; what does not exist is a single application bringing them together, so the
driver ends up with several installed and joining by hand what none of them joins: public
charging with home charging, and the price per kWh with what this particular charge will actually
cost this particular car. The state publishes an official map of the infrastructure —overseen by
the Ministry for the Ecological Transition and operated by Red Eléctrica de España— which solves
point discovery and route planning, but not charge management, and cannot solve it: its mandate
is informational and its operator is barred from competing in the market.

This work proposes *S-Charge*, the progressive web application that would fill that gap, and
builds, deploys and argues it as far as a master's thesis reaches. The system mirrors the
national charging-point catalogue
published by the official registry into its own database —142 operators, some 13,700 charging
points, 42,000 supply equipment units and 47,000 connectors— under the five-requests-per-hour cap
of its public API, a constraint that shapes the entire architecture: the catalogue is seeded over
roughly twelve days of bounded, idempotent batch runs and is owned by the application from then
on. On that foundation it adds daily ingestion of the regulated hourly electricity price, a
curated vehicle catalogue, and a pre-charge simulation that estimates energy, duration and cost
from the specifications of the car and the connector.

The application is deployed and publicly reachable over HTTPS, installable on a phone, and
delivered through a continuous integration and deployment pipeline. The report also documents
what remains designed but not implemented —charge-schedule optimisation against the price curve,
privately contributed charging points, booking, the wallet and a conversational assistance
layer— together with the regulatory framework that applies to the
system, its economic viability and its known gaps against real-world operation. One criterion
runs throughout: stating explicitly which part is real data, which part is an estimate and which
part does not exist yet. That is why the real-time state of the public network, which no
accessible source publishes today, is not simulated: the application shows the occupancy it
generates itself and declares the rest unknown.

**Keywords:** electric vehicle; charging infrastructure; progressive web app; OCPI; PVPC; charge
scheduling optimisation; web engineering.
