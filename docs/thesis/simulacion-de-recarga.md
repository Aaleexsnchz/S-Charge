---
status: borrador (redacción de la memoria, nivel conceptual)
---

# Simulación de recarga previa

Antes de enchufar, el conductor quiere saber **cuánto tardará, cuánta energía
añadirá y cuánto costará** cargar su coche en un punto concreto. La simulación
responde a esas tres preguntas a partir de las especificaciones del vehículo y del
conector, sin depender de ninguna fuente externa en tiempo de petición.

## Entradas

- **Vehículo** del catálogo curado (`vehicles`): capacidad útil de batería (kWh),
  potencia máxima en AC y en DC (kW).
- **Conector** real de un punto sembrado (`connectors`): `power_type` (AC/DC) y
  potencia máxima (`max_electric_power`, en vatios), más su tarifa si la tiene.
- **Ventana de carga**: estado de carga inicial y final (`soc_from`, `soc_to`),
  por defecto 20 % → 80 % (el tramo realista de una sesión rápida).

## Modelo físico

**Potencia de pico.** La carga está limitada por el eslabón más débil entre coche
y poste: `pico = min(potencia_vehículo, potencia_conector)`, donde la potencia del
vehículo es su máximo en AC o en DC según el tipo del conector. Si el conector es DC
y el vehículo no admite DC, la simulación se rechaza.

**Curva de potencia.** La AC se modela como **plana**: el cargador de a bordo
mantiene la potencia constante prácticamente hasta el final. La DC **decae (taper)**
por encima de un codo de SoC: se mantiene al pico hasta el `80 %` y luego desciende
linealmente hasta un `20 %` del pico al `100 %`, reflejando la protección de la
batería a SoC alto. Ambos parámetros (codo y fracción de cola) son constantes
documentadas y ajustables.

**Energía y duración.** La energía entregada es `batería · (soc_to − soc_from)`.
La duración se obtiene **integrando la ventana de SoC en pasos de 1 %**: en cada
paso el tiempo es la energía del tramo dividida por la potencia instantánea de la
curva. Para la AC (curva plana) esto equivale a `energía / pico`; para la DC que
cruza el codo, el promedio resultante queda por debajo del pico. Se reporta también
la **potencia media** (`energía / tiempo`) como resumen interpretable.

## Coste

El coste reutiliza el servicio de precios (véase
[precios-y-actualizacion.md](precios-y-actualizacion.md)): se cobra la tarifa real
del conector si existe y, si no, se estima `PVPC(hora) + margen[AC|DC]`. El coste es
`energía · precio`. La respuesta indica la **procedencia del precio** (tarifa real o
estimación), de modo que la interfaz es explícita sobre qué parte es dato real y qué
parte es estimación. La sesión se valora a un único precio horario (el del momento de
la simulación); el reparto por tramos horarios es competencia del optimizador
(capítulo de optimización de carga), no de la simulación.

## Honestidad del modelo

Es una predicción **basada en especificaciones**, no una medida. No modela
temperatura, degradación, pérdidas de conversión ni el perfil real de taper de cada
modelo (que el fabricante rara vez publica). Sirve para orientar la decisión previa a
la carga; se presenta como estimación, no como garantía.
