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

- **La tarifa de REVE es un precio comercial, desacoplado del PVPC.** Cientos de
  tarifas coinciden en valores redondos idénticos (0.2975, 0.4545…) y los CPO
  reprecian en lotes esporádicos, con meses entre cambios: no existe un precio de
  REVE "en tiempo real" que perseguir. Lo que sí existe, y se pasó por alto
  durante meses, es que **una parte del catálogo tarifica por franjas** —por hora
  del día y por potencia del conector—; el precio no sigue al mercado, pero
  tampoco es un único número (véase el punto 3).
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

**3. El precio no es un número: es una franja.** Durante meses el ETL guardaba un
solo `price_per_kwh` por tarifa, tomando el **primer** componente `ENERGY` que
encontraba y descartando las restricciones. Una tarifa real medida el 2026-08-22
muestra por qué eso no puede funcionar:

| Potencia del conector | 00:00–06:59 | 07:00–22:59 | 23:00–23:59 |
| --- | --- | --- | --- |
| ≤ 22 kW | 0,25 | 0,29 | 0,25 |
| ≤ 100 kW | 0,31 | 0,37 | 0,31 |
| ≤ 450 kW | 0,40 | **0,47** | 0,40 |

El precio varía en **dos ejes**, y solo el segundo es decisivo. Que varíe por
**hora del día** hace que guardar la primera franja sea *impreciso*: elegir mejor
la franja lo arregla. Que varíe por **potencia del conector** hace que no haya
ninguna elección correcta, porque **una misma tarifa la comparten conectores de
distinta potencia**. Sobre el catálogo sembrado, **7.175 de los 41.963 conectores
con tarifa** están en una tarifa que publica más de un precio de energía; para
ellos, un número en la fila de la tarifa no es una aproximación, es una
imposibilidad estructural. El grano en el que la respuesta es única es el
**conector**.

**Los dos ejes son disjuntos, y eso decide qué puede ofrecerse al conductor.**
Ninguna tarifa del catálogo varía a la vez por hora y por potencia: de los 38.548
conectores con precio de energía, **4.297 (11 %) varían solo por potencia**,
**1.547 (4 %) varían solo por hora** y **31.426 (82 %) tienen un único precio
constante**. La distinción no es estadística sino práctica: la variación por
potencia es la diferencia entre *dos conectores de la misma estación* y no se
puede esperar a que pase, mientras que la variación por hora sí admite la
decisión *vuelvo más tarde y me cuesta menos*. Solo el 4 % del parque tarificado
la ofrece —y ninguno de esos conectores supera las **seis franjas** diarias—, de
modo que la tabla horaria que la app enseña debe desaparecer limpiamente en el
96 % restante en lugar de repetir el mismo número tres veces. Que el argumento
del optimizador se apoye en una minoría medida, y no en una impresión, es
justamente lo que permite dimensionar la interfaz.

De ahí el modelo actual: las franjas se almacenan como filas consultables
(`tariff_elements`, una por componente de precio con las restricciones que lo
condicionan) y el precio resuelto vive en el conector, junto a un `pricing_kind`
que distingue `energy · time · flat · free · unknown`. El razonamiento completo y
las alternativas descartadas están en [be-0003](../decisions/be-0003-price-on-the-connector.md).

**No hizo falta volver a descargar nada.** Las 2.126 tarifas ya guardaban su array
`elements` completo en `raw_data`: el aplanamiento ocurría **a la salida, nunca a
la entrada**. Reconstruir el modelo fue una migración de 1,7 s contra la base de
datos, sin gastar una sola llamada del presupuesto.

**«Gratis» tiene que ser una afirmación de la fuente, no la ausencia de una.**
`price_per_kwh IS NULL` confundía cuatro hechos distintos: gratis, tarificado por
tiempo, tarificado por sesión, y dato erróneo en origen (un conector publica
`ENERGY 9110,66 €/kWh`). Sobre el modelo aplanado, 1.152 conectores no tenían
precio por kWh y se leyeron como gratuitos. Convertidas las franjas en filas, la
lectura se cae: **1.144 de ellos llevan un único `FLAT 0.0` sin IVA, con
`step_size` 0 y sin ninguna franja de energía** —una ficha sin rellenar, no un
cargador gratuito—. La prueba está en quién los publica: Etecnic tiene 685 de
esos junto a 1.084 conectores correctamente tarificados, y ELECTROMAPS 148 frente
a 1.742. Son CPO que saben publicar precios; los ceros son huecos en su feed.
**Gratuitos de verdad hay 30**, cada uno con un `ENERGY 0.0` explícito, con IVA y
`step_size` rellenos. Etiquetar los otros 1.144 como *gratis* habría mandado
conductores a cargadores que les cobran.

**Una tarifa caducada no tarifica.** 2.138 conectores se estaban valorando con una
tarifa pasada su propio `valid_to`. No son valores por defecto sin mantener: las
caducadas promedian **0,1129 €/kWh frente a 0,3517** de las vigentes, es decir,
promociones terminadas. Servir una manda al conductor a un punto esperando pagar
un tercio de lo que le cobrarán. 2.115 de las 2.138 ya llegaron caducadas, así que
REVE las sirve como vigentes de todos modos: la ventana de validez hay que
comprobarla en casa.

**Los finales son inclusivos, contra la especificación.** OCPI define `end_time` y
`end_date` como exclusivos. Quienes publican en REVE no: las franjas se escriben
`00:00–06:59` / `07:00–22:59`, y **275 de las 406 franjas con fecha fijan
`start_date = end_date`** para un único día —bajo una lectura exclusiva no
casarían *ningún* día—. Leer la especificación al pie de la letra habría dejado un
agujero de un minuto en cada frontera y habría hecho invisibles dos tercios de las
franjas fechadas. La cota de potencia sigue el mismo criterio: la restricción de
OCPI habla de la potencia de la *sesión*, aquí la sustituye la potencia nominal
del conector, y una sesión nunca alcanza exactamente su nominal, de modo que un
conector de 22 kW pertenece a la franja «hasta 22 kW».

**El `0` de REVE no es un cero.** El registro escribe `0` donde quiere decir «sin
definir», y leerlo al pie de la letra destruye información: una franja limitada a
`max_power = 0` no casa con **ningún** conector, y otra condicionada a
`min_duration = 0` no está condicionada a nada, pero parece depender de la sesión.
Guardar esos ceros tal cual dejaba **797 conectores en `unknown` teniendo precio**.
A esto se suma un problema de precedencia: **127 tarifas publican una franja sin
restricciones junto a las franjas reales**, y resolver por orden de aparición le
daba a 1.247 conectores el precio de respaldo dentro de la ventana que debía ser
más barata. La franja **más específica** gana sobre la de respaldo, y los ceros se
pliegan a nulo al ingerir; `raw_data` conserva el original. Ninguno de los dos
fallos era visible mientras el precio era un número suelto en la tarifa: solo se
ven cuando las franjas son filas que se pueden contar.

**Retrasar la marca de agua no rescata nada.** La tentación, ante 2.138
conectores con tarifa caducada, es mover `date_from` hacia atrás hasta
alcanzarlos. No funciona, y la razón es estructural: `date_from` filtra por
**cuándo cambió la fila en origen**, no por cuándo la vimos nosotros. Una fila que
no ha cambiado no se puede volver a descargar convertida en otra cosa —ya tenemos
exactamente lo que REVE publica—. Además, 2.060 de esas tarifas se modificaron por
última vez en diciembre de 2025: alcanzarlas exigiría una ventana de nueve meses
sobre un endpoint que agota el tiempo con ventanas de días. Y es innecesario por
construcción: si un CPO republica una de ellas, su `last_tariff_updated` avanza y
la marca de agua **actual** la recoge en el siguiente tick. Retrasarla solo gasta
presupuesto y aumenta el riesgo de `504`.

**Un ETL parado puede dejar sin precio, no solo con precio viejo —y la franja sin
restricciones es lo que lo evita.** Algunos CPO publican un **calendario fechado**:
una franja por cuarto de hora, válida para un día concreto. 1.532 conectores están
en tarifas así, congeladas el día en que se paró la marca de agua, y **todas esas
franjas han caducado**. A 1.485 de ellos los sigue tarificando la franja sin
restricciones de su propia tarifa; los 47 que no la tienen resuelven a `unknown`.
Esa es la razón por la que la franja de respaldo no es ruido: es lo que sostiene
el precio cuando el calendario caduca. Es la respuesta honesta, y es
información nueva: el modelo anterior seguía sirviendo para ellos el precio que
por casualidad llevara la primera franja. La frescura del espejo, por tanto, no
solo degrada la exactitud del precio; en parte del catálogo determina si hay
precio.

**El catálogo congelado no se queda quieto, y el propio refresco lo mide.** El
refresco solo pide `/connectors/tariffs`, así que *se encuentra* con estaciones
construidas después de la siembra sin poder guardarlas: la tarifa nombra un EVSE
que no existe en el espejo. **Una cuarta parte de cada página drenada es una fila
así** —30, 23 y 21 de cada 100 en las primeras páginas—, unos 1.900 conectores en
el drenaje completo, es decir un ~4 % de crecimiento del catálogo en dos meses y
medio. La cifra está inflada por la propia ventana, porque un conector añadido la
semana pasada siempre parece «recién cambiado» a un filtro `date_from`, y por eso
aflora aquí y en ningún otro sitio.

**Guardar esas filas no es contabilidad, es la única forma de que lleguen con
precio.** Una tarifa reaparece en el feed únicamente cuando su precio vuelve a
cambiar, y eso son **~243 días de media** (7.760 de 41.963 conectores tarificados
se movieron en una ventana de 45 días; 45 es la *ventana*, no la recurrencia). Una
reparación que importara la estación sin su precio la dejaría en blanco casi un
año. De ahí `reve_unmirrored_connectors`: los identificadores **y el payload de la
tarifa**, borrados en cuanto se siembran, de modo que el tamaño de la tabla
responde a *cuánto del catálogo nos falta* y vacía significa que no falta nada.

**Un log no es un registro.** Esas filas se venían anotando con un `warning` y
descartando. Recrear el contenedor del planificador durante un despliegue
ordinario destruyó las 262 líneas acumuladas: no hizo falta ni una rotación de
logs. La medición existe cuando está en una tabla, no cuando está en la salida
estándar de un proceso.

**4. Estimación de respaldo.** Para un conector sin tarifa, el precio se estima
como `PVPC(hora) + margen[tipo]` (AC +0.22 / DC +0.32 €/kWh) y se etiqueta como
*estimado*. Dos constantes calibradas con el mercado real cubren también los
puntos privados de usuario, que no tienen CPO. Este margen es solo el valor
**recomendado**: en la aplicación, el propietario de un punto fija el precio o el
margen que quiera (PVPC + margen, o precio fijo).

**5. Estado operativo frente a disponibilidad.** Son cosas distintas. El *estado
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
