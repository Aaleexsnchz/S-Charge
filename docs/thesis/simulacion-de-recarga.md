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

**La sesión se tarifica por la ventana que ocupa, no por el instante en que se
consulta.** Una recarga dura horas y las franjas cambian a hora en punto, así que
cobrarla entera al precio del momento de la simulación era exacto solo si empezaba
y terminaba dentro de la misma franja. Cada paso de SoC paga la franja que cubre el
minuto en que llega su energía, y la respuesta devuelve el **precio efectivo** —el
coste dividido entre la energía tarificada—, no una franja concreta: citar una sola
para una carga que cruzó dos sería un número que ningún contador marca. Sobre un
conector real, la misma recarga de 42 kWh cuesta **13,21 €** empezando a las 10:00 y
**14,86 €** empezando a las 21:00.

El reparto se hace **minuto a minuto** y no por intersección de intervalos, porque
la potencia en DC decae por encima del codo: la energía no se reparte
uniformemente entre las franjas que la sesión cruza, y hay que pesar cada minuto por
la energía que realmente entrega. Esto es distinto del optimizador (capítulo de
optimización de carga), que *elige* cuándo cargar; aquí solo se valora correctamente
una ventana que el conductor ya ha decidido.

**Un conector sin precio publicado no tiene coste, y esa casilla se queda vacía.**
Antes se rellenaba con `PVPC(hora) + margen[AC|DC]` y se etiquetaba la procedencia,
confiando en que el usuario leyera la etiqueta. Es la misma objeción que se le hace
a simular disponibilidad: *un número verosímil que se lee como real es peor que un
campo vacío*, y aquí además se atribuía una estimación propia a la tarifa de un
tercero. La estimación sobrevive, pero cambiada de sitio: es la que se **ofrece** al
propietario de un punto privado cuando fija su propio precio, donde sugerir un
número es justamente el objetivo y no una afirmación sobre nadie más.

## Honestidad del modelo

Es una predicción **basada en especificaciones**, no una medida. No modela
temperatura, degradación, pérdidas de conversión ni el perfil real de taper de cada
modelo (que el fabricante rara vez publica). Sirve para orientar la decisión previa a
la carga; se presenta como estimación, no como garantía.
