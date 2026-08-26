# 5. Modelo de datos y fuentes

La aplicación genera muy poco dato propio. Casi todo lo que muestra viene de fuera, y buena parte
del trabajo consiste en traerlo, conciliarlo y servirlo sin que la latencia dependa del proveedor.
Cuatro fuentes, con papeles distintos.

**REVE** aporta el catálogo real de la red pública española: quién opera, dónde está cada estación,
qué enchufes tiene y a qué precio. Es el directorio oficial, dirigido por el MITECO y operado por
Red Eléctrica de España [6], y su sistema intercambia información con los operadores mediante OCPI
(*Open Charge Point Interface*) 2.2.1 [11][29].

**REE** aporta la economía: la curva del PVPC (Precio Voluntario para el Pequeño Consumidor), única
referencia horaria del coste de la energía que el sistema maneja.

**El catálogo de vehículos** aporta la entrada de la simulación. Sin capacidad útil de batería ni
potencias máximas no hay forma de convertir una tarifa en un tiempo y un coste de recarga.

**El usuario** aporta lo que ninguna de las tres puede: su cuenta, su vehículo y —en el diseño
previsto para la fase 7— sus propios puntos de carga con el precio al que los ofrece. Esa cuarta
fuente es la aportación de la plataforma frente a un simple visor del catálogo oficial.

| Fuente | Qué aporta | Acceso | Estado |
| --- | --- | --- | --- |
| REVE (MITECO / REE) | Catálogo OCPI: operadores, ubicaciones, EVSEs, conectores, tarifas | API con credencial, 5 peticiones/hora | Espejado en Postgres |
| REE — REData | Curva horaria del PVPC, indicador 1001 | API pública, sin token | Ingesta diaria |
| Catálogo de vehículos | 31 modelos con batería útil y potencias máximas | Curado a mano | Semilla en el repositorio |
| Usuarios | Cuenta y perfil; puntos privados y su precio | Alta en la aplicación | Cuenta construida; puntos privados en fase 7 |

**Tabla 5.1.** Las cuatro fuentes de datos y su papel.

## La jerarquía OCPI, espejada

OCPI encadena tres entidades: el *connector* es el enchufe o cable concreto que el vehículo usa, el
*EVSE* (*Electric Vehicle Supply Equipment*) es la parte que controla el suministro a un único
vehículo en una única sesión, y la *location* agrupa los EVSEs que están juntos en el espacio [28].
El manual de integración del sistema español lo confirma y añade el detalle que más confunde a
quien llega de fuera: el «punto de recarga» de la regulación equivale al objeto EVSE de OCPI, y no
existe objeto para «estación de recarga» [29]. Por encima de la ubicación, REVE añade el CPO
(*Charge Point Operator*), la empresa que gestiona el hardware; por debajo del conector cuelga la
tarifa.

El esquema replica esa cadena. Un CPO agrupa muchas ubicaciones; una ubicación tiene latitud,
longitud, dirección y horario; dentro de ella hay una fila por plaza de aparcamiento; y cada plaza
expone uno o dos enchufes con su estándar (Type 2, CCS, CHAdeMO), su tipo de corriente y su terna
de potencia, tensión e intensidad máximas. La instantánea española tomada durante la siembra
contiene **142 operadores**, **13.654 puntos de carga**, unos **42.000 EVSEs** y unos **47.000
conectores**: tres plazas por ubicación de media y, en la mayoría de ellas, un único enchufe.

> **[FIGURA 5.1]** — *Diagrama entidad-relación del esquema.* Debe mostrar las doce tablas y sus
> relaciones: `cpos` (1—N) `charging_points` por la clave ajena `party_id`, que apunta al
> identificador OCPI del operador y no a la clave primaria; `charging_points` (1—N) `evses` y
> `evses` (1—N) `connectors`, ambas con borrado en cascada; `connectors` (N—1) `tariffs` por una
> clave ajena anulable; `tariffs` (1—N) `tariff_elements`, que es donde viven las franjas de
> precio; `charging_points` (N—1) `users` por `owner_user_id`, anulable y con `ON DELETE SET NULL`,
> que es el enganche de los puntos privados; `users` (1—N) `oauth_account`; y, sin relación con las
> anteriores, `vehicles`, `electricity_prices`, `reve_etl_cursor` y
> `reve_unmirrored_connectors`. Marcar en cada tabla espejada la restricción de unicidad sobre el
> identificador de origen —`(source, source_id)` en `charging_points`, `source_id` en `cpos` y
> `tariffs`— porque es la clave de la idempotencia del ETL. **Cómo obtenerla:** diagrama a dibujar
> en Mermaid (`erDiagram`) a partir de los modelos de `backend/app/models/`.

Dos decisiones se apartan del vocabulario de OCPI. La primera es de nomenclatura: OCPI llama
*locations* a las ubicaciones —de ahí que el *endpoint* de REVE se llame `/locations`—, pero la
tabla se llama `charging_points`. El término OCPI es más abstracto de lo que la aplicación necesita
y se lee peor en el código, donde «ubicación» compite además con la posición del usuario en el
mapa; `GET /api/points` y `usePoint(id)` no admiten esa ambigüedad. La semántica OCPI queda intacta:
solo cambia la etiqueta.

La segunda es la columna `source`, que distingue las filas sembradas desde REVE de las que
registrará un usuario. Compartir tabla en lugar de separar catálogo oficial y catálogo privado
mantiene una sola consulta para el mapa: los dos tipos de punto salen con la misma forma de
respuesta, los mismos filtros los alcanzan y ninguna funcionalidad posterior tiene que decidir
dónde buscar. El precio es un par de columnas anulables y una restricción de unicidad compuesta,
`(source, source_id)`, que impide que un identificador de REVE colisione con uno de usuario.

## Espejo, no proxy

**La API de REVE admite cinco peticiones por hora.** Ese único número decide la arquitectura de
datos del proyecto. Una carga en frío del mapa consumiría la cuota de una hora entera, de modo que
un *proxy* en tiempo de petición no puede servir ni a un usuario. La alternativa es poseer el
catálogo: copiarlo a Postgres con un ETL por cursor y servirlo siempre desde ahí, sin llamar nunca
a REVE mientras se atiende a alguien.

El espejo compra tres cosas que un *proxy* no daría. Los puntos aportados por usuarios viven en las
mismas tablas y salen en la misma consulta. El esquema evoluciona sin coordinarse con el proveedor:
añadir una columna o un índice es una migración propia. Y la aplicación sigue funcionando cuando
REVE no responde, que no es una hipótesis sino algo observado: el fallo descrito más abajo mantuvo
el refresco detenido durante cuarenta y cinco días sin que el mapa ni el detalle de un punto
dejaran de servirse.

El coste es el de un activo que no se puede regenerar barato. La siembra completa consumió **unos
12 días** de *ticks* desatendidos, así que repetirla para poblar un entorno nuevo no es una opción:
producción y cualquier entorno reconstruido arrancan desde un archivo `pg_dump`. Con ello, la
custodia del dato —copias de seguridad, copias fuera del servidor, verificación de la
restauración— pasa a ser responsabilidad propia.

Se descartaron cuatro alternativas. El *proxy* directo, por la cuota y porque ataría la
disponibilidad de la aplicación a la de REVE. El *proxy* con caché agresiva, que no es más que un
espejo con peores garantías: sin control del esquema, sin sitio para los puntos de usuario y con la
caché fría excediendo igualmente la cuota. Reducir el ámbito a una comunidad autónoma, que habría
abaratado la siembra a costa de la afirmación central del producto, la vista nacional unificada. Y
raspar el mapa público en lugar de usar la API: más volumen y sin límite declarado, pero sin
contrato estable y, sobre todo, indefendible en un trabajo académico, donde la procedencia del dato
tiene que poder citarse. Las condiciones de uso de la API de REVE son además una cuestión abierta
que se trata en el capítulo 10, «Marco regulador».

## La siembra: el contrato por tick

Con cinco llamadas por hora y un catálogo que necesita cientos de páginas, ni el *proxy* ni el
*script* único sirven. Un programa de arranque de larga duración solo tiene dos comportamientos
posibles: ignorar el límite y estrangularse a base de respuestas `429`, o dormir doce minutos entre
llamadas durante doce días siendo un punto único de fallo. Un planificador en proceso dentro de
FastAPI pierde su estado en cada reinicio del contenedor, y darle un almacén de trabajos en base de
datos duplicaría la tabla de cursores que el ETL ya necesita. Cron es la primitiva más pequeña que
cumple la restricción: planificación declarativa, persistente entre reinicios, un proceso
independiente por *tick* y sin estado compartido.

Que «un proceso corto cada hora» sea la abstracción correcta, y no un apaño, depende de tres
propiedades del *tick*.

**Acotado.** Cada ejecución gasta como mucho cinco llamadas, elige el siguiente *endpoint* no
completado respetando el orden de dependencia `/cpos → /locations → /connectors/tariffs` —una
tarifa no se puede enganchar a un conector que todavía no existe— y termina limpiamente ante un
`429`, dejando el cursor donde estaba. Las páginas son de 100 registros, luego el techo teórico de
ingesta son 12.000 filas al día.

**Idempotente.** Las importaciones escriben con `INSERT … ON CONFLICT DO UPDATE`, y el objetivo del
conflicto es siempre el identificador de origen, nunca la clave primaria interna:

```sql
INSERT INTO tariffs (id, source_id, last_refreshed_at, ...) VALUES (...)
ON CONFLICT (source_id) DO UPDATE SET
  raw_data = excluded.raw_data,
  last_refreshed_at = excluded.last_refreshed_at;
```

Reejecutar una página ya descargada actualiza las filas en su sitio en vez de duplicarlas. Un
*tick* perdido lo recupera el siguiente, un *tick* fallido no cuesta nada, y un portátil cerrado
ocho horas cuesta ocho *ticks* de progreso y ninguna corrupción.

**Único.** Dos procesos que ticaran a la vez se repartirían el mismo presupuesto de cinco llamadas
y avanzarían el mismo cursor desde estados distintos. Un *lock* consultivo de PostgreSQL, tomado
sobre su propia conexión al arrancar el *tick*, cierra esa carrera: el segundo ejecutor sale sin
hacer ninguna llamada a REVE y sin escribir nada. Es la primitiva adecuada precisamente porque no
sobrevive a la caída del proceso que lo tomó, de modo que un contenedor que muere no deja el ETL
bloqueado.

> **[FIGURA 5.2]** — *Flujo de un tick del ETL.* Diagrama de flujo de una sola ejecución: tomar el
> *lock* consultivo → leer los cursores → ¿siembra completa? → si no, elegir el primer *endpoint*
> sin `completed_at` y paginar desde `next_page` con presupuesto de 5 llamadas; si sí, recorrer los
> tres objetivos de refresco por orden de prioridad, dando a cada uno lo que el anterior dejó
> libre. Debe mostrar las tres salidas del *tick* —página corta (marca `completed_at` o avanza la
> marca de agua), presupuesto agotado (guarda `next_page`) y `429` (corte limpio sin tocar el
> cursor)— y la rama de `504`, que reintenta con la última ventana servida y **nunca** mueve la
> marca de agua. **Cómo obtenerla:** diagrama a dibujar en Mermaid (`flowchart`) a partir de
> `backend/scripts/seed_reve.py` y `refresh_reve.py`.

## El refresco incremental y la marca de agua

Terminada la siembra, el cron deja de sembrar y pasa a refrescar. El *endpoint* de tarifas acepta
`date_from`, `page` y `limit`, y devuelve todos los conectores cuya tarifa cambió desde ese
instante. **No existe `date_to`.** Esa ausencia gobierna todo lo demás. Cada *tick* fija
`date_from` en la marca de agua (*watermark*), pagina el resultado —a lo largo de varios *ticks* si
hace falta— y, al drenarlo, adelanta la marca al instante en que arrancó el ciclo.

**Dos llamadas bastaron para dimensionar el drenaje.** Bajo un límite de cinco peticiones por hora,
planificar un trabajo largo sin gastar presupuesto en medirlo es en sí un problema. Se resolvió
extrapolando desde la cobertura del espacio de identificadores: la página 1 abarcaba el 1,303 % y
la 77 terminaba en el 99,18 %, dos estimaciones independientes que coincidían en unas 7.760 filas y
78 páginas. El drenaje real fueron **7.774 filas en 78 páginas**, un error del 0,2 %. La técnica es
reutilizable para cualquier fuente paginada con clave ordenada y cuota restrictiva, y es un
resultado del trabajo tanto como el propio catálogo.

**Qué significa realmente un `504`.** Lo que pesa no es la antigüedad absoluta de `date_from`, sino
cuánto ha cambiado entre `date_from` y ahora, y el modo de fallo no es el que uno esperaría: una
marca de agua atrasada no devuelve un resultado grande, devuelve un `504`. Esa era la explicación
que se dedujo en junio de 2026 —«las ventanas de una hora o más agotan el tiempo»—, deducida
*después* de que el fallo se curara solo y sin haberlo sondeado nunca mientras ocurría. En agosto de
2026 sí se pudo sondear, y la medición la contradice:

| `date_from` | Intentos | Resultado |
| --- | --- | --- |
| `2026-08-24T09:00:04Z` | **27** | todos `504`, a unos 29 s |
| `2026-08-24T08:00:05Z` | **2** | ambos `200`, en 14,8 s y 15 s |

**Tabla 5.2.** La misma consulta con dos marcas de agua, una contenida en la otra.

La segunda ventana es una hora **más ancha** y contiene a la primera. Con la misma probabilidad de
fallo, veintisiete fallos seguidos en un valor mientras su superconjunto no falla nunca es del
orden de uno entre 134 millones: no es carga ni azar, es una propiedad de esa ventana concreta. Y
sin `date_from` el *endpoint* responde en 1,7 s, mientras `/cpos` y `/locations` responden en 1,2 s
y 3,9 s con la misma clave y el mismo *host*, de modo que ni la credencial ni la IP estaban
bloqueadas.

**El fallo tampoco empieza por una ventana ancha: el primero pidió sesenta minutos.** La anchura es
la *consecuencia* y no la causa. Como la marca de agua solo avanza cuando la llamada tiene éxito,
un refresco atascado ensancha su propia ventana una hora por cada hora que pasa. Ese trinquete es
lo que convierte una hora mala en REVE en un hueco que ya no se puede cerrar, y explica la parada
de julio de 2026 mucho mejor que «se dejó el portátil apagado».

**De ahí la recuperación: ensanchar a propósito, nunca saltar.** Ante un `504`, el *tick* reintenta
con la última ventana que REVE sí sirvió, guardada en el cursor. Una ventana más ancha devuelve
todo lo que devolvería la estrecha, así que no se pierde nada. Si esa también falla, el *tick* se
detiene y lo dice: la única opción más ancha es el drenaje sin filtro, 469 páginas y unos cuatro
días, demasiado grande para lanzarlo solo ante un fallo que nadie ha mirado. Un `504` **nunca**
mueve la marca de agua, tenga la antigüedad que tenga; un `429` detiene el *tick*; y el reintento
inmediato del cliente se desactiva en este camino, porque bajo cinco llamadas por hora no compensa
gastar una segunda en un `504`.

**El camino no tomado: saltar la marca de agua.** Una versión anterior resolvía el `504` de una
marca vieja saltándola a `ahora − 2 h` —un tamaño que sí responde `200`— y siguiendo. Mantenía el
refresco en marcha, y el tramo saltado se daba por perdido con el argumento de que era «justo un
periodo en el que apenas cambió nada». El argumento resultó ser circular, porque nadie había medido
cuánto cambiaba. Se retiró: al no existir `date_to`, una marca adelantada no se puede volver a
apuntar hacia atrás, de modo que el salto es **silencioso e irreversible** y su única traza es una
línea en un registro que nadie lee. Es exactamente el mecanismo que habría convertido la parada de
julio de 2026 en una pérdida definitiva. El coste de la regla nueva es que una ventana que REVE no
sirve gasta una llamada por *tick* hasta que alguien interviene, y ese es el intercambio buscado:
**quedarse parado es recuperable, saltar no lo es.**

La parada, para que conste, dejó el cursor con la marca de agua en el `2026-07-08 19:30:03 UTC` y
un `504` como último error, y sobrevivió cuarenta y cinco días precisamente porque el fallo llegó
cuando la marca tenía dos horas y se clasificó como transitorio. Con la regla del salto, una marca
de cuarenta y cinco días se habría descartado en el primer *tick* desatendido.

Queda un detalle del traspaso entre siembra y refresco del que depende la corrección del precio
mostrado. **La siembra no es atómica**: pagina durante doce días, así que una tarifa capturada en la
página 1 refleja el estado de REVE del primer día y no del último. Si el primer refresco arrancara
en `completed_at`, se saltaría en silencio cualquier precio que hubiera cambiado durante la propia
siembra. Por eso la primera marca de agua es `min(last_refreshed_at)` sobre las tarifas, la captura
más antigua. Drenado ese primer barrido, todas las filas comparten un mismo instante de captura y
el modelo de marca única ya es correcto en adelante.

La auditoría distingue además dos recuentos que es fácil confundir. Como el *upsert* reescribe toda
fila descargada cambie o no su precio, el número de filas tocadas sobrestima el movimiento real; la
línea `reve_etl_tariffs` registra por eso `rows` —lo descargado— junto a `changed`, las tarifas
cuyo `last_tariff_updated` cae dentro de la ventana consultada, es decir, las que de verdad
cambiaron en origen.

**El estado del espejo se declara, no se disimula.** Durante los cuarenta y cinco días de marca
congelada la aplicación siguió sirviendo las tarifas de la última captura buena, que es exactamente
lo que el diseño de espejo promete: quedarse desactualizado en lugar de caerse. El planificador se
desplegó además detenido a propósito, para poder inspeccionar el cursor antes de que un *tick* lo
moviera.

## El catálogo se mueve, y el propio refresco lo mide

El diseño inicial congelaba el catálogo físico en la instantánea de la siembra: no contiene
precios, cambia rara vez, y dedicarle presupuesto se lo robaría a lo único que sí se mueve. El
coste asumido era que las estaciones incorporadas por REVE después de la siembra no aparecerían. La
medición obligó a revisarlo.

El refresco de tarifas *se encuentra* con esas estaciones sin poder guardarlas: la tarifa nombra un
conector que no existe en el espejo. **Una cuarta parte de cada página drenada es una fila así**
—30, 23 y 21 de cada 100 en las primeras páginas—, **1.837 conectores** tras el drenaje completo,
es decir en torno a un 4 % de crecimiento del catálogo en dos meses y medio. La cifra está inflada
por la propia ventana, porque un conector añadido la semana pasada siempre parece «recién cambiado»
a un filtro `date_from`, y por eso aflora aquí y en ningún otro sitio.

**Guardar esas filas no es contabilidad, es la única forma de que la estación llegue con precio.**
Una tarifa reaparece en el *feed* únicamente cuando su precio vuelve a cambiar, y eso son unos
**243 días de media**. Una reparación que importara la estación sin su precio la dejaría en blanco
casi un año. De ahí la tabla `reve_unmirrored_connectors`: guarda los identificadores **y el
contenido de la tarifa**, y borra la fila en cuanto la estación se siembra, de modo que su tamaño
responde a *cuánto del catálogo falta* y vacía significa que no falta nada.

**La reparación tiene que entrar por la estación y no por el EVSE, y eso no es una preferencia sino
un callejón cerrado.** Lo natural sería pedir el EVSE que falta: `/evses/{evse_id}` existe. Pero su
respuesta **no menciona su ubicación** —ni identificador, ni dirección, ni operador— mientras que
en el espejo la clave ajena del EVSE hacia su punto de carga no admite nulos. El EVSE de una
estación nueva no tiene dónde colgarse ni forma de encontrar a su padre, y ese es el caso de 23 de
cada 30 filas del registro. Tampoco cabe filtrar por operador, porque el identificador de EVSE que
viaja en el *feed* de tarifas es el UUID interno de REVE y no un identificador eMI3. Queda una sola
vía, `/locations`, y resulta ser la eficiente: un elemento de esa respuesta trae el anidamiento
completo —estación, EVSEs y conectores—, de modo que **una llamada siembra un centenar de
estaciones enteras**.

**Y aquí el filtro incremental deja de servir, que es lo interesante.** Sobre `/locations`, un
`date_from` que cubriera los 77 días transcurridos desde la siembra devolvía páginas llenas hasta
la 68: más de 6.800 de las 13.654 ubicaciones «habían cambiado», porque el campo de última
actualización se mueve por casi cualquier cosa. A esa distancia el filtro no filtra —pedir lo
cambiado cuesta más que pedirlo todo, y encima devuelve un resultado parcial—, mientras que a seis
horas es excelente, con unas 88 ubicaciones cambiando al día. La conclusión no es que el filtro sea
malo, sino que **su utilidad depende del ancho de la ventana**: el catálogo se pone al día con un
drenaje liso y se mantiene después con ventanas estrechas.

De ahí la forma final del refresco: tres objetivos que comparten el mismo presupuesto por orden de
prioridad, y no tres trabajos independientes. Las tarifas van primero porque son lo que la
aplicación sirve; `/cpos` se conforma con una ventana diaria, porque de los 142 operadores uno
cambió en junio y otro en marzo; y `/locations` con una de seis horas. El presupuesto se reparte de
arriba abajo, de modo que una puesta al día del catálogo no puede retrasar nunca un precio.

**Un registro en la salida estándar no es una medición.** Esas filas huérfanas se venían anotando
con un aviso y descartando. Recrear el contenedor del planificador durante un despliegue ordinario
destruyó las 262 líneas acumuladas, sin que hiciera falta ni una rotación de registros. La medición
existe cuando está en una tabla, no cuando está en la salida estándar de un proceso; es un
resultado pequeño y es el que justifica la tabla del párrafo anterior.

## El precio no es un número: es una franja

Antes de decidir cómo mostrar un precio hubo que mirar qué son realmente las tarifas del catálogo.
Y no son lo que el nombre sugiere: **la tarifa de REVE es un precio comercial, no un precio
horario**. Cientos de tarifas coinciden en los mismos valores redondos, y los operadores reprecian
en lotes esporádicos, con meses entre cambios, de forma desacoplada del mercado mayorista. No hay
un «precio de REVE en tiempo real» que perseguir, lo que justifica que baste con refrescar tarifas
una vez por hora.

Lo que sí hay, y se pasó por alto durante meses, es que **una parte del catálogo tarifica por
franjas**. Durante ese tiempo el ETL guardaba un solo precio por tarifa, tomando el primer
componente de energía que encontraba y descartando las restricciones que lo condicionaban. Una
tarifa real medida sobre el catálogo muestra por qué eso no puede funcionar:

| Potencia del conector | 00:00–06:59 | 07:00–22:59 | 23:00–23:59 |
| --- | --- | --- | --- |
| ≤ 22 kW | 0,25 | 0,29 | 0,25 |
| ≤ 100 kW | 0,31 | 0,37 | 0,31 |
| ≤ 450 kW | 0,40 | **0,47** | 0,40 |

**Tabla 5.3.** Una tarifa real del catálogo, en €/kWh, con sus dos ejes de variación.

El precio varía en **dos ejes**, y solo el segundo es decisivo. Que varíe por **hora del día** hace
que guardar la primera franja sea *impreciso*: elegir mejor la franja lo arregla. Que varíe por
**potencia del conector** hace que no haya ninguna elección correcta, porque una misma tarifa la
comparten conectores de distinta potencia. Sobre el catálogo sembrado, **7.175 de los 41.963
conectores con tarifa** están en una tarifa que publica más de un precio de energía; para ellos, un
número en la fila de la tarifa no es una aproximación, es una imposibilidad estructural. El grano
en el que la respuesta es única es el **conector**.

De ahí el modelo actual: las franjas se almacenan como filas consultables —una por componente de
precio, con las restricciones que lo condicionan— y el precio resuelto para *ahora* se desnormaliza
en el conector, junto a una etiqueta que distingue si se tarifica por energía, por tiempo, por
sesión, si es gratis o si no se sabe. La desnormalización se recalcula en el mismo *tick* horario,
que es exactamente el ritmo al que puede cambiar la franja que resume; lo que necesite otro
instante —la simulación, que conoce la ventana entera de la recarga— lee las franjas directamente.
**No hizo falta volver a descargar nada**: las 2.126 tarifas guardadas ya llevaban su array de
elementos completo en el campo de datos en bruto, porque el aplanamiento ocurría a la salida y
nunca a la entrada. Reconstruir el modelo fue una migración de 1,7 s contra la base de datos, sin
gastar una sola llamada del presupuesto.

**Los dos ejes son disjuntos, y eso decide qué puede ofrecerse al conductor.** Ninguna tarifa del
catálogo varía a la vez por hora y por potencia: de los 38.548 conectores con precio de energía,
**4.297 (11 %) varían solo por potencia**, **1.547 (4 %) varían solo por hora** y **31.426 (82 %)
tienen un único precio constante**. La distinción no es estadística sino práctica: la variación por
potencia es la diferencia entre dos conectores de la misma estación y no se puede esperar a que
pase, mientras que la variación por hora sí admite la decisión *vuelvo más tarde y me cuesta
menos*. Solo el 4 % del parque tarificado la ofrece —y ninguno de esos conectores supera las seis
franjas diarias—, de modo que la tabla horaria que la aplicación enseña debe desaparecer
limpiamente en el 96 % restante en lugar de repetir el mismo número tres veces. Que el argumento
del optimizador se apoye en una minoría medida, y no en una impresión, es justamente lo que permite
dimensionar la interfaz.

Convertir las franjas en filas contables refutó de paso tres creencias, y las tres afectaban a lo
que el conductor veía.

**«Gratis» tiene que ser una afirmación de la fuente, no la ausencia de una.** Un precio nulo
confundía cuatro hechos distintos: gratis, tarificado por tiempo, tarificado por sesión y dato
erróneo en origen —hay un conector que publica 9.110,66 €/kWh—. Sobre el modelo aplanado, 1.152
conectores no tenían precio por kWh y se leían como gratuitos. Como filas, **1.144 de ellos llevan
un único componente plano de valor cero, sin IVA, sin escalón y sin ninguna franja de energía**: una
ficha sin rellenar, no un cargador gratuito. La prueba está en quién los publica, operadores que
tarifican correctamente el resto de su parque. **Gratuitos de verdad hay 30**, cada uno con un
componente de energía a cero explícito y completo. Etiquetar a los otros 1.144 como *gratis* habría
mandado conductores a cargadores que les cobran.

**Una tarifa caducada no tarifica.** 2.138 conectores se estaban valorando con una tarifa pasada su
propia fecha de validez. No son valores por defecto sin mantener: las caducadas promedian **0,1129
€/kWh frente a 0,3517** de las vigentes, es decir, promociones terminadas. Servir una manda al
conductor a un punto esperando pagar un tercio de lo que le cobrarán. Y 2.115 de las 2.138 ya
llegaron caducadas, así que REVE las sirve como vigentes de todos modos: la ventana de validez hay
que comprobarla en casa. La aplicación dice *la tarifa publicada caducó el 12/08/2026* en lugar de
un guion, porque «caducado» es un hecho distinto de «ausente» y decir cuál de los dos es no cuesta
nada ni afirma ningún precio.

**El `0` de REVE no es un cero.** El registro escribe `0` donde quiere decir «sin definir», y leerlo
al pie de la letra destruye información: una franja limitada a potencia máxima cero no casa con
**ningún** conector, y otra condicionada a duración mínima cero no está condicionada a nada pero
parece depender de la sesión. Guardar esos ceros tal cual dejaba **797 conectores sin precio
teniéndolo**. A esto se suma un problema de precedencia: **127 tarifas publican una franja sin
restricciones junto a las franjas reales**, y resolver por orden de aparición le daba a 1.247
conectores el precio de respaldo dentro de la ventana que debía ser más barata. La franja **más
específica** gana sobre la de respaldo, y los ceros se pliegan a nulo al ingerir, conservando el
original en los datos en bruto. Ninguno de los dos fallos era visible mientras el precio era un
número suelto en la tarifa.

Esa franja de respaldo, que parecía ruido, resultó ser lo que sostiene el precio cuando el
calendario caduca. Algunos operadores publican un **calendario fechado**, una franja por cuarto de
hora válida para un día concreto; 1.532 conectores están en tarifas así, congeladas el día en que
se paró la marca de agua, y todas esas franjas han caducado. A 1.485 de ellos los sigue tarificando
la franja sin restricciones de su propia tarifa, y los 47 que no la tienen resuelven a «sin
precio», que es la respuesta honesta. Es información nueva sobre lo que cuesta un espejo
desactualizado: **la frescura no solo degrada la exactitud del precio, en parte del catálogo
determina si hay precio**.

Un último resultado negativo, porque ahorra trabajo a quien venga después. **Retrasar la marca de
agua no rescata nada.** La tentación, ante 2.138 conectores con tarifa caducada, es mover
`date_from` hacia atrás hasta alcanzarlos. No funciona, y la razón es estructural: `date_from`
filtra por *cuándo cambió la fila en origen*, no por cuándo la vimos nosotros, y una fila que no ha
cambiado no se puede volver a descargar convertida en otra cosa. Además, 2.060 de esas tarifas se
modificaron por última vez en diciembre de 2025, de modo que alcanzarlas exigiría una ventana de
nueve meses sobre un *endpoint* que agota el tiempo con ventanas de días. Y es innecesario por
construcción: si un operador republica una de ellas, su marca de modificación avanza y la ventana
**actual** la recoge en el siguiente *tick*.

> **[FIGURA 5.3]** — *De la tarifa publicada al precio que se enseña.* Árbol de decisión sobre la
> etiqueta de tarificación: franja de energía resuelta para la potencia del conector y la hora,
> *gratis*, tarificado por tiempo o por sesión, tarifa caducada con su fecha, y sin precio
> publicado. Debe verse qué mensaje sale en cada rama y que **ninguna produce una cifra estimada**,
> con la rama de sugerencia al propietario (fase 7) dibujada aparte para dejar claro que no
> alimenta esta pantalla. **Cómo obtenerla:** diagrama a dibujar en Mermaid (`flowchart`) sobre
> `backend/app/services/tariff_pricing.py`.

## La estimación que dejó de mostrarse

Los datos dicen además algo aprovechable: el margen del operador sobre el coste de la energía es
estable por tipo de recarga. Frente a un PVPC de referencia de unos **0,12 €/kWh**, la mediana
sobre unas **27.000 tarifas reales** da **+0,22 €/kWh en corriente alterna** y **+0,32 €/kWh en
corriente continua**. Varía entre operadores, pero el valor por tipo basta como estimación.

De ahí salió una **cascada de tres escalones**, que se construyó y luego se retiró de la pantalla.
Si el conector tenía tarifa real almacenada se servía esa; si no, se estimaba como
`PVPC(hora) + margen[tipo]`; y la respuesta viajaba etiquetada con su procedencia para que la
interfaz distinguiera un dato de una estimación. La apuesta era que **etiquetar la procedencia
permite estimar sin engañar**.

**No se sostiene, y es un camino no tomado que merece contarse.** Un número verosímil colocado donde
el usuario espera un precio se lee como un precio, lea o no la etiqueta que lo acompaña: la cifra
ocupa el lugar destacado y la procedencia es letra pequeña. El fallo es el mismo que se le reprocha
a simular la disponibilidad —*un dato inventado que se lee como real es peor que un campo vacío*—,
con un agravante que la disponibilidad no tiene: aquí la estimación es **nuestra** y se estaba
atribuyendo a la tarifa de un tercero. Un conductor que llega al poste esperando 0,34 €/kWh porque
la aplicación se lo dijo no distingue si el número salió del operador o de una mediana estadística;
simplemente paga otra cosa.

Hoy el precio que se muestra sale **siempre de lo que el operador publica**, resuelto por franjas
sobre el conector, y **un conector sin tarifa no tiene precio ni coste**: la simulación devuelve
duración y energía, y deja el coste vacío. Los miles de conectores de los que REVE no publica
tarifa se quedan sin cifra, que es la respuesta honesta.

**La estimación sobrevive, cambiada de sitio.** Los márgenes medidos siguen siendo un resultado
válido, y en la fase 7 son lo que se **ofrece** al propietario de un punto privado cuando fija su
propio precio: ahí sugerir un número es justamente el objetivo, no una afirmación sobre el poste de
nadie. El código vive en `backend/app/services/price_suggestion.py`, sin ningún llamador hasta
entonces y con el motivo escrito en el propio módulo para que nadie lo borre por parecer muerto.

## La curva del PVPC

La curva de precios se ingiere de la API pública de datos de REE, que no exige credencial: el PVPC
aparece como serie con identificador **1001** dentro del *endpoint* de precios de mercado, en
€/MWh, y se almacena una fila por hora en €/kWh, con histórico desde el **1 de enero de 2026** [10].
Consultada con agregación horaria, esa serie devuelve 24 valores por día, y sobre 24 valores está
construido el sistema; el encaje de esa granularidad con la norma corresponde al capítulo 10,
«Marco regulador».

Dos detalles de la ingesta merecen mención porque son decisiones y no descuidos. El primero es que
**REE responde con un error de servidor para un día que aún no ha publicado**: el cliente lo trata
como «todavía no» y no como fallo, registra una línea de auditoría, devuelve una lista vacía y deja
que el siguiente intento lo recoja. Confundir «aún no existe» con «se ha roto» habría llenado el
registro de falsos positivos todas las tardes. El segundo es que la ingesta rellena el hueco desde
la última hora almacenada en lugar de pedir solo el día en curso, de modo que una parada de días la
cura una sola ejecución: es la propiedad que permitió recuperar la curva entera tras la parada de
julio sin ninguna intervención manual.

## El catálogo de vehículos

Treinta y un modelos habituales del mercado español, cada uno con capacidad útil de batería,
potencia máxima en alterna, potencia máxima en continua y estándar de conector en continua. La
recarga en alterna es siempre Type 2 en el mercado europeo, así que lo único que varía por modelo
es el estándar de continua, CCS o CHAdeMO.

Está curado a mano desde fichas técnicas públicas de fabricante, y no importado de una API, porque
no se localizó ninguna que fuera a la vez gratuita, completa para el mercado español y con una
licencia de reutilización limpia. Una treintena de modelos basta para que la mayoría de los
conductores encuentre el suyo o uno equivalente, y mantenerlos cuesta una lista en una semilla
idempotente. Son valores de ficha, aproximados a efectos de simulación, y así se declaran.

## Caminos no tomados

**ACN-Data.** El conjunto abierto de sesiones de recarga de Caltech [46] se consideró para calibrar
la ocupación y dar realismo a las sesiones simuladas. Llegó a haber una migración que creaba su
tabla y otra posterior que la borra. Se descartó por dos razones que se refuerzan: es aparcamiento
de un campus universitario californiano, una distribución sin traducción defendible a la red
pública española; y, sobre todo, el resultado quedaba como dato interno sin valor de cara al
usuario, que no ve una calibración, ve un color en un marcador.

**La ocupación simulada.** El segundo paso del mismo camino fue sustituir la calibración por un
modelo sintético ligero que generase ocupación verosímil por franja horaria. Barato y bueno para
una demostración. También abandonado, y por la razón que importa: producía un dato que quien usara
la aplicación leería como real sin serlo, indistinguible de un dato verdadero en la interfaz, y
sostener esa distinción ante una sola pregunta en la defensa costaba más de lo que aportaban unos
marcadores de colores.

La consecuencia es que **la disponibilidad no se modela**. Los puntos aparecen disponibles por
defecto, y eso es un valor ilustrativo que la memoria declara en lugar de disimular. La estructura
queda intacta: la columna de estado con el valor OCPI del EVSE, la agregación por punto —disponible
si alguno figura libre, ocupado si todos los conocidos están en uso, desconocido si no hay dato— y
los colores del marcador siguen ahí, alimentables por una fuente real, ya sea un acuerdo con un
operador o el propio REVE si algún día publica el flujo de estado, sin más migración que empezar a
escribir en esa columna. Ocultar la dimensión entera habría eliminado la señal engañosa, pero
también el punto de extensión. Cuando lleguen las reservas y las sesiones (fases 9 y 10), esa misma
agregación pasará a alimentarse de la ocupación que generen los propios usuarios, que es una fuente
interna y coherente aunque no sea el estado del poste.

Conviene separar dos cosas que se confunden. La *disponibilidad* (libre o en uso) es la que no se
modela. El *estado operativo* (funciona o está averiado) es otra dimensión, se asume siempre
operativo y su *endpoint* se eliminó del ETL junto con su cursor: sondear unos 42.000 EVSEs a cinco
peticiones por hora no es aritméticamente posible, y una cobertura parcial sería peor que ninguna,
porque el usuario no podría saber qué puntos llevan estado real y cuáles no.

> **PENDIENTE:** dos observaciones que necesitan un día de operación ordinaria. La primera, que
> `/cpos` y `/locations` empiecen a consumir presupuesto —sus cursores siguen en la siembra porque
> la puesta al día de tarifas se lo lleva entero— y que el número de conectores pendientes de
> espejar baje desde los 1.837 medidos. La segunda, repetir el censo de conectores sin precio
> ahora que el drenaje ha terminado, para separar lo que el ETL ha reparado de lo que no puede
> reparar: de los 1.155 registros sin rellenar, 740 habían cambiado en origen, mientras que las
> 2.138 tarifas caducadas no son recuperables por ninguna ventana, y ese límite pertenece a la
> fuente y así hay que contarlo.
