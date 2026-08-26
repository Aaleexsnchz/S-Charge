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

**El sesgo tiene signo conocido, y es el signo favorable.** Las dos aproximaciones
que afectan al coste lo desvían siempre en la misma dirección: la factura real queda
*por encima* de la estimación, nunca por debajo. La energía que se calcula es la que
entra en la batería (`batería · ΔSoC`), mientras que el poste factura la que
entrega por el cable —entre un 5 % y un 10 % más en DC, entre un 10 % y un 15 % en
AC—; y el IVA que la fuente publica en cada componente de tarifa no se aplica. Que un
error de modelado tenga signo conocido no lo convierte en correcto, pero sí decide
cuál de los dos errores posibles se comete: un conductor que acepta un importe nunca
se encuentra con uno mayor por culpa del modelo.

**El IVA es además una ambigüedad de la fuente, no una decisión propia.** OCPI define
`price` como importe sin IVA y añade el porcentaje en un campo aparte, que aquí se
almacena pero no se aplica; la práctica de los operadores españoles es publicar
directamente el precio de venta al público. Los datos no distinguen ambos casos —una
tarifa de 0,45 €/kWh es plausible como precio final y como base imponible— y ninguna
consulta sobre el propio catálogo puede resolverlo: hace falta contrastar con un poste
cuyo cartel de precios sea visible. Se documenta como pendiente en lugar de elegir una
interpretación, porque elegir mal desplaza *todas* las estimaciones un 21 %.

## Lo que la simulación revela sin proponérselo

La estimación produce con frecuencia importes superiores a **10 €** por sesión, y esa
cifra sorprende a quien asocia el vehículo eléctrico al ahorro. No es un defecto del
cálculo: sobre las medianas del propio catálogo —0,322 €/kWh en AC y 0,447 €/kWh en DC
sobre 38 552 conectores con precio— una batería de 60 kWh cargada del 20 % al 80 %
cuesta 11,60 € en AC y 16,09 € en DC. Son los precios reales de la recarga pública
española.

Traducido a coste por distancia, con un consumo realista de unos 17,5 kWh/100 km, la
recarga rápida en DC sale a unos **7,8 €/100 km** frente a los **10 €/100 km** de un
gasolina equivalente: un ahorro estrecho, y prácticamente nulo frente a un diésel. La
misma energía tomada en casa a precio PVPC ronda los **2 €/100 km**. **El ahorro del
vehículo eléctrico vive en la recarga doméstica, no en la pública**, y la brecha entre
ambas es de un factor cercano a cuatro.

Este es un resultado que la aplicación expone por construcción y que el conductor
suele descubrir solo al final de la sesión, delante del poste. Sostener aquí la
decisión de no inventar precios (la casilla vacía del apartado anterior) tiene por
tanto una consecuencia que va más allá del rigor: la señal de precio que la aplicación
muestra antes de enchufar es exactamente la información que hace falta para elegir
entre cargar ahora y esperar a llegar a casa.
