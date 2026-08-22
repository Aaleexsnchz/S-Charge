---
status: borrador (redacción de la memoria, nivel conceptual)
---

# Precios de recarga: frescura del catálogo y estimación

## El problema

REVE se siembra una sola vez en Postgres bajo el límite de 5 peticiones/hora
(véase [seed-scheduling.md](planificacion-de-siembra.md)). De ahí surgían tres dudas
sobre el precio que mostramos:

1. Si la tarifa se obtiene una vez, ¿no quedará permanentemente desactualizada?
2. El precio mayorista (PVPC) varía cada hora; ¿deberíamos perseguir un precio
   "en tiempo real" del CPO?
3. ¿Merece la pena gastar parte de la cuota en el estado operativo de los EVSE?

## Lo que dicen los datos

Una muestra re-descargada de REVE y el catálogo ya sembrado resuelven las dudas:

- **La tarifa de REVE es un precio comercial plano, no un precio horario.** Cientos
  de tarifas coinciden en valores redondos idénticos (0.2975, 0.4545…). Los CPO
  reprecian en lotes esporádicos (meses entre cambios), de forma **desacoplada del
  PVPC** — no existe un precio de REVE "en tiempo real" que perseguir.
- **El margen del CPO es estable por tipo de recarga.** Frente a un PVPC de
  referencia de ~0.12 €/kWh: AC ≈ +0.22 €/kWh, DC ≈ +0.32 €/kWh (mediana sobre
  ~27 000 tarifas reales). Varía entre CPO, pero el valor por tipo basta como
  estimación.
- **El estado operativo no aporta valor:** la disponibilidad no se modela
  (véase [modelo-de-datos.md](modelo-de-datos.md)), así que gastar cuota en
  `/evses/operational_status` no se justifica.

## La solución

**1. Servir el precio real almacenado.** La app nunca llama a REVE al abrir un
punto: sirve siempre desde Postgres, con su fecha de actualización. La cuota se
gasta solo en la ingesta de fondo, nunca en el tráfico de usuario.

**2. Refresco incremental tras la siembra** ([refresh_reve.py](../../backend/scripts/refresh_reve.py)).
Una vez completada la siembra inicial, cada tick refresca **solo
`/connectors/tariffs`**: el precio es el único campo que cambia con la frecuencia
suficiente para importar. El catálogo físico (`/cpos`, `/locations`) se congela en
la instantánea de la siembra —no contiene precios, varía rara vez y refrescarlo
solo robaría presupuesto a las tarifas; el coste asumido es que las estaciones
añadidas a REVE tras la siembra no aparecerán. El endpoint solo acepta `date_from`
(más `page`/`limit`): **no existe `date_to`**, y devuelve todos los conectores cuya
tarifa cambió desde ese instante. Cada tick fija `date_from` en la marca de agua,
pagina el resultado (entre ticks bajo presupuesto) y, al drenarlo, avanza la marca
de agua al instante en que arrancó el ciclo, de modo que el siguiente recoge todo
lo posterior. Como solo trae lo cambiado, son decenas de tarifas al día frente a
una capacidad de ~12 000/día; los `upsert` idempotentes absorben cualquier
reproceso en el borde y una página mayor que el presupuesto se reanuda en el
siguiente tick.

**Por qué la marca de agua no puede quedarse atrás.** Lo que pesa no es la
antigüedad absoluta de `date_from`, sino cuánto ha cambiado **entre `date_from` y
ahora**: una marca de agua reciente es un resultado pequeño y barato; una que ha
quedado días atrás obliga a REVE a recorrer/devolver demasiado y el gateway agota
el tiempo (`504`). Lo confirmamos con pruebas controladas (mismas condiciones,
variando un solo parámetro): `date_from` de hace ~100 h, ~20 h y horas intermedias
daban `504`, mientras que `date_from = ahora − 3 h` respondía `200`; y `date_to`,
al no ser un parámetro, no cambiaba nada. En junio de 2026 un fallo puntual de REVE
congeló la marca de agua y, al no avanzar, el hueco creció día a día hasta volverse
irrecuperable (cada consulta abarcaba ya días de cambios).

**Un `504` nunca mueve la marca de agua.** El tick registra el error y deja la
posición intacta, tenga la antigüedad que tenga. Un `429` detiene el tick. El
reintento del cliente se desactiva aquí (`max_retries=0`): bajo 5 llamadas/hora no
compensa gastar una segunda llamada en un `504`.

**El camino no tomado: saltar la marca de agua.** Una versión anterior resolvía el
`504` de una marca vieja **saltándola a `ahora − 2 h`** —un tamaño que sí responde
`200`— y siguiendo. Mantenía el refresco en marcha, y el tramo saltado se daba por
perdido con el argumento de que era «justo un periodo en el que apenas cambió
nada». El argumento resultó ser circular: nadie había medido cuánto cambiaba.

Se retiró en la Fase 6. Al no existir `date_to`, una marca adelantada no se puede
volver a apuntar hacia atrás, de modo que el salto es **silencioso e
irreversible**: la única traza es una entrada de auditoría en un log que nadie
lee. Es exactamente el mecanismo que habría convertido la parada de julio de 2026
en una pérdida definitiva. Hoy el `504` deja la marca donde está y lo dice en
`last_error`; el coste es que una ventana que REVE no sirve gasta una llamada por
tick hasta que alguien interviene, y ese es el intercambio buscado: **quedarse
parado es recuperable, saltar no lo es.** La intervención se hace con
`--date-from`, que apunta una sonda sin escribir el cursor.

**El estado congelado, para que conste.** La parada dejó el cursor en este punto,
medido el 2026-08-22 antes de reactivar nada:

| Campo | Valor |
| --- | --- |
| `refresh_watermark` | `2026-07-08 19:30:03.120191+00` |
| `last_attempted_at` | `2026-07-08 21:30:32.375417+00` |
| `last_error` | `504 Gateway Timeout` sobre `date_from=2026-07-08T19:30:03` |
| `refresh_cycle_end` | vacío (ningún ciclo a medias) |

Sobrevivió precisamente porque el `504` llegó cuando la marca tenía dos horas y se
clasificó como transitorio. Con la regla del salto, una marca de 45 días se habría
descartado en el primer tick desatendido.

Un matiz en el traspaso siembra→refresco: como la siembra es **no atómica** (con
presupuesto de 5 llamadas/hora pagina durante días), una tarifa de la página 1
refleja el estado de REVE del primer día, no del último. Por eso el `date_from`
del primer ciclo de refresco debe ser la captura **más antigua**
(`min(last_refreshed_at)`), no `completed_at`: arrancar en la fecha de
finalización se saltaría cualquier precio que cambiara durante la propia siembra.
Una vez drenado ese primer barrido, la marca de agua salta a «ahora» y todas las
filas comparten un mismo instante de captura, de modo que el modelo de marca de
agua única ya es correcto en adelante.

Como el `upsert` reescribe toda fila descargada —cambie o no su precio—, el
recuento de filas tocadas sobrestima el movimiento real. Por eso la línea de
auditoría `reve_etl_tariffs` registra, además de `rows`, un campo `changed`: las
tarifas cuyo `last_tariff_updated` cae dentro de `[date_from, date_to]`, es decir,
las que de verdad cambiaron en origen. Así el log distingue "descargadas" de
"realmente actualizadas" en cada tick.

**3. Estimación de respaldo.** Para un conector sin tarifa, el precio se estima
como `PVPC(hora) + margen[tipo]` (AC +0.22 / DC +0.32 €/kWh) y se etiqueta como
*estimado*. Dos constantes calibradas con el mercado real cubren también los
puntos privados de usuario, que no tienen CPO. Este margen es solo el valor
**recomendado**: en la aplicación, el propietario de un punto fija el precio o el
margen que quiera (PVPC + margen, o precio fijo).

**4. Estado operativo frente a disponibilidad.** Son cosas distintas. El *estado
operativo* (funciona / averiado) se asume siempre operativo y no se modela: se
elimina `/evses/operational_status` del ETL y su cursor. La *disponibilidad*
(libre / en uso) la da en REVE el endpoint por EVSE `/evses/{evse_id}/status`,
que tampoco se consulta por coste de cuota. El plan original era simularla;
finalmente **no se modela** y los puntos se muestran disponibles por defecto —el
razonamiento completo, en [modelo-de-datos.md](modelo-de-datos.md)—. El EVSE
conserva la columna `status` (valor OCPI, p. ej. `AVAILABLE`) y el mapa la sigue
agregando a *disponible* / *ocupado* / *desconocido*, lista para una fuente real.

## Operación

El cron sigue lanzando `seed_reve` hasta que las tres fuentes del catálogo
(`/cpos`, `/locations`, `/connectors/tariffs`) quedan completas. A partir de ese
momento, `seed_reve` no hace nada y la línea de cron se cambia para invocar
`refresh_reve`; ambos comparten cursor, presupuesto y patrón de tick. `refresh_reve`
es un no-op mientras la siembra no esté completa, de modo que el cambio es seguro
en cualquier orden.
