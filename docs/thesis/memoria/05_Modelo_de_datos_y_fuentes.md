# 5. Modelo de datos y fuentes

La aplicación genera muy poco dato propio. Casi todo lo que muestra viene de fuera, y buena parte del trabajo consiste en traerlo, conciliarlo y servirlo sin que la latencia dependa del proveedor. Cuatro fuentes, con papeles distintos.

**REVE** aporta el catálogo real de la red pública española: quién opera, dónde está cada estación, qué enchufes tiene y a qué precio. Es el directorio oficial, dirigido por el MITECO y operado por Red Eléctrica de España [6], y su sistema intercambia información con los operadores mediante OCPI (*Open Charge Point Interface*) 2.2.1 [11][29].

**REE** aporta la economía: la curva del PVPC (Precio Voluntario para el Pequeño Consumidor), única referencia horaria del coste de la energía que el sistema maneja.

**El catálogo de vehículos** aporta la entrada de la simulación. Sin capacidad útil de batería ni potencias máximas no hay forma de convertir una tarifa en un tiempo y un coste de recarga.

**El usuario** aporta lo que ninguna de las tres puede: su cuenta, su vehículo y —en el diseño previsto para la fase 8— sus propios puntos de carga con el precio al que los ofrece. Esa cuarta fuente es la aportación de la plataforma frente a un simple visor del catálogo oficial.

| Fuente | Qué aporta | Acceso | Estado |
| --- | --- | --- | --- |
| REVE (MITECO / REE) | Catálogo OCPI: operadores, ubicaciones, EVSEs, conectores, tarifas | API con credencial, 5 peticiones/hora | Espejado en Postgres |
| REE — REData | Curva horaria del PVPC, indicador 1001 | API pública, sin token | Ingesta diaria |
| Catálogo de vehículos | 31 modelos con batería útil y potencias máximas | Curado a mano | Semilla en el repositorio |
| Usuarios | Cuenta y perfil; puntos privados y su precio | Alta en la aplicación | Cuenta construida; puntos privados en fase 8 |

**Tabla 5.1.** Las cuatro fuentes de datos y su papel.

## La jerarquía OCPI, espejada

OCPI encadena tres entidades: el *connector* es el enchufe o cable concreto que el vehículo usa, el *EVSE* (*Electric Vehicle Supply Equipment*) es la parte que controla el suministro a un único vehículo en una única sesión, y la *location* agrupa los EVSEs que están juntos en el espacio [28]. El manual de integración del sistema español lo confirma y añade el detalle que más confunde a quien llega de fuera: el «punto de recarga» de la regulación equivale al objeto EVSE de OCPI, y no existe objeto para «estación de recarga» [29]. Por encima de la ubicación, REVE añade el CPO (*Charge Point Operator*), la empresa que gestiona el hardware; por debajo del conector cuelga la tarifa.

El esquema replica esa cadena. Un CPO agrupa muchas ubicaciones; una ubicación tiene latitud, longitud, dirección y horario; dentro de ella hay una fila por plaza de aparcamiento; y cada plaza expone uno o dos enchufes con su estándar (Type 2, CCS, CHAdeMO), su tipo de corriente y su terna de potencia, tensión e intensidad máximas. La instantánea española tomada durante la siembra contiene algo más de un centenar de operadores, decenas de miles de puntos de carga y del orden de decenas de miles de conectores, con una media de tres plazas por ubicación y, en la mayoría de ellas, un único enchufe.

> **[FIGURA 5.1]** — *Diagrama entidad-relación del esquema.* Debe mostrar las diez tablas y sus relaciones: `cpos` (1—N) `charging_points` por la clave ajena `party_id`, que apunta al identificador OCPI del operador y no a la clave primaria; `charging_points` (1—N) `evses` y `evses` (1—N) `connectors`, ambas con borrado en cascada; `connectors` (N—1) `tariffs` por una clave ajena anulable; `charging_points` (N—1) `users` por `owner_user_id`, anulable y con `ON DELETE SET NULL`, que es el enganche de los puntos privados; `users` (1—N) `oauth_account`; y, sin relación con las anteriores, `vehicles`, `electricity_prices` y `reve_etl_cursor`. Marcar en cada tabla espejada la restricción de unicidad sobre el identificador de origen —`(source, source_id)` en `charging_points`, `source_id` en `cpos` y `tariffs`— porque es la clave de la idempotencia del ETL. **Cómo obtenerla:** diagrama a dibujar en Mermaid (`erDiagram`) a partir de los modelos de `backend/app/models/`.

Dos decisiones se apartan del vocabulario de OCPI. La primera es de nomenclatura: OCPI llama *locations* a las ubicaciones —de ahí que el *endpoint* de REVE se llame `/locations`—, pero la tabla se llama `charging_points`. El término OCPI es más abstracto de lo que la aplicación necesita y se lee peor en el código, donde «ubicación» compite además con la posición del usuario en el mapa; `GET /api/points` y `usePoint(id)` no admiten esa ambigüedad. La semántica OCPI queda intacta: solo cambia la etiqueta.

La segunda es la columna `source`, que distingue las filas sembradas desde REVE de las que registrará un usuario. Compartir tabla en lugar de separar catálogo oficial y catálogo privado mantiene una sola consulta para el mapa: los dos tipos de punto salen con la misma forma de respuesta, los mismos filtros los alcanzan y ninguna funcionalidad posterior tiene que decidir dónde buscar. El precio es un par de columnas anulables y una restricción de unicidad compuesta, `(source, source_id)`, que impide que un identificador de REVE colisione con uno de usuario.

## Espejo, no proxy

**La API de REVE admite cinco peticiones por hora.** Ese único número decide la arquitectura de datos del proyecto. Una carga en frío del mapa consumiría la cuota de una hora entera, de modo que un *proxy* en tiempo de petición no puede servir ni a un usuario. La alternativa es poseer el catálogo: copiarlo a Postgres con un ETL por cursor y servirlo siempre desde ahí, sin llamar nunca a REVE mientras se atiende a alguien.

El espejo compra tres cosas que un *proxy* no daría. Los puntos aportados por usuarios viven en las mismas tablas y salen en la misma consulta. El esquema evoluciona sin coordinarse con el proveedor: añadir una columna o un índice es una migración propia. Y la aplicación sigue funcionando cuando REVE no responde, que no es una hipótesis sino algo observado: la regresión de rendimiento descrita más abajo mantuvo el refresco detenido durante semanas sin que el mapa ni el detalle de un punto dejaran de servirse.

El coste es el de un activo que no se puede regenerar barato. La siembra completa consumió **unos 12 días** de ticks desatendidos, así que repetirla para poblar un entorno nuevo no es una opción: producción y cualquier entorno reconstruido arrancan desde un archivo `pg_dump`. Con ello, la custodia del dato —copias de seguridad, copias fuera del servidor, verificación de la restauración— pasa a ser responsabilidad propia.

Se descartaron cuatro alternativas. El *proxy* directo, por la cuota y porque ataría la disponibilidad de la aplicación a la de REVE. El *proxy* con caché agresiva, que no es más que un espejo con peores garantías: sin control del esquema, sin sitio para los puntos de usuario y con la caché fría excediendo igualmente la cuota. Reducir el ámbito a una comunidad autónoma, que habría abaratado la siembra a costa de la afirmación central del producto, la vista nacional unificada. Y raspar el mapa público en lugar de usar la API: más volumen y sin límite declarado, pero sin contrato estable y, sobre todo, indefendible en un trabajo académico, donde la procedencia del dato tiene que poder citarse. Las condiciones de uso de la API de REVE son además una cuestión abierta que se trata en el capítulo 10, «Marco regulador».

## La siembra: el contrato por tick

Con cinco llamadas por hora y un catálogo que necesita cientos de páginas, ni el *proxy* ni el script único sirven. Un programa de arranque de larga duración solo tiene dos comportamientos posibles: ignorar el límite y estrangularse a base de respuestas `429`, o dormir doce minutos entre llamadas durante doce días siendo un punto único de fallo. Un planificador en proceso dentro de FastAPI pierde su estado en cada reinicio del contenedor, y darle un almacén de trabajos en base de datos duplicaría la tabla de cursores que el ETL ya necesita. Cron es la primitiva más pequeña que cumple la restricción: planificación declarativa, persistente entre reinicios, un proceso independiente por tick y sin estado compartido.

Que «un proceso corto cada hora» sea la abstracción correcta, y no un apaño, depende de dos propiedades del tick.

**Acotado.** Cada ejecución gasta como mucho cinco llamadas, elige el siguiente *endpoint* no completado respetando el orden de dependencia `/cpos → /locations → /connectors/tariffs` —una tarifa no se puede enganchar a un conector que todavía no existe— y termina limpiamente ante un `429`, dejando el cursor donde estaba. Las páginas son de 100 registros, luego el techo teórico de ingesta son 12.000 filas al día.

**Idempotente.** Las cuatro importaciones escriben con `INSERT … ON CONFLICT DO UPDATE`, y el objetivo del conflicto es siempre el identificador de origen, nunca la clave primaria interna:

```sql
INSERT INTO tariffs (id, source_id, price_per_kwh, ...) VALUES (...)
ON CONFLICT (source_id) DO UPDATE SET
  price_per_kwh = excluded.price_per_kwh,
  last_refreshed_at = excluded.last_refreshed_at;
```

Reejecutar una página ya descargada actualiza las filas en su sitio en vez de duplicarlas. La combinación de ambas propiedades convierte la fragilidad del entorno en un no-problema: un tick perdido lo recupera el siguiente, un tick fallido no cuesta nada, y un portátil cerrado ocho horas cuesta ocho ticks de progreso y ninguna corrupción.

> **[FIGURA 5.2]** — *Flujo de un tick del ETL.* Diagrama de flujo de una sola ejecución: leer los tres cursores → ¿siembra completa? → si no, elegir el primer *endpoint* sin `completed_at` y paginar desde `next_page` con presupuesto de 5 llamadas; si sí, pasar al refresco incremental con `date_from` = marca de agua. Debe mostrar las tres salidas del tick —página corta (marca `completed_at` o avanza la marca de agua), presupuesto agotado (guarda `next_page`) y `429` (corte limpio sin tocar el cursor)— y la rama de `504`, que decide entre saltar la marca de agua y reintentar. **Cómo obtenerla:** diagrama a dibujar en Mermaid (`flowchart`) a partir de `backend/scripts/seed_reve.py` y `refresh_reve.py`.

## El refresco incremental y la marca de agua

Terminada la siembra, el cron deja de sembrar y pasa a refrescar **solo `/connectors/tariffs`**. El catálogo físico se congela en la instantánea: no contiene precios, cambia rara vez, y dedicarle presupuesto se lo robaría a lo único que sí se mueve. El coste asumido y declarado es que las estaciones que REVE incorpore después de la siembra no aparecen.

El *endpoint* de tarifas acepta `date_from`, `page` y `limit`, y devuelve todos los conectores cuya tarifa cambió desde ese instante. **No existe `date_to`.** Esa ausencia gobierna todo lo demás. Cada tick fija `date_from` en la marca de agua (*watermark*), pagina el resultado —a lo largo de varios ticks si hace falta— y, al drenarlo, adelanta la marca al instante en que arrancó el ciclo. Como solo trae lo cambiado, un día normal son decenas de tarifas frente a una capacidad de 12.000 filas diarias.

Lo que pesa no es la antigüedad absoluta de `date_from`, sino cuánto ha cambiado entre `date_from` y ahora. Y el modo de fallo no es el que uno esperaría: una marca de agua atrasada no devuelve un resultado grande, devuelve un `504`. El servidor tiene que recorrer todo lo posterior a esa fecha antes de componer la primera página, la pasarela agota el tiempo de espera y no llega ninguna fila. Paginar no ayuda, porque ya la página 1 exige el recorrido completo. Se comprobó con pruebas controladas, en las mismas condiciones y variando un solo parámetro: `date_from` de hace unas 100 horas, de hace unas 20 y valores intermedios devolvían `504`, mientras que `date_from = ahora − 3 h` devolvía `200`; añadir `date_to`, al no ser un parámetro reconocido, no cambiaba nada.

Sin `date_to` no se puede trocear un rango antiguo, así que la recuperación no puede consistir en reintentar más fino. Un `504` con la marca de agua vieja se resuelve **saltándola a `ahora − lookback`** —dos horas por defecto, una ventana que se sabe que responde `200`— y siguiendo. El tramo saltado es irrecuperable por este *endpoint* y se pierde a sabiendas: es justo un periodo en el que apenas cambió nada, y recuperarlo costaría días de cuota. Un `504` con la marca de agua ya reciente se interpreta al revés, como fallo transitorio del proveedor, y se deja igual para reintentar en el siguiente tick sin saltar nada. Cada salto deja una línea de auditoría, `reve_refresh_jumped_to_recent`, con el tramo exacto al que se ha renunciado. El reintento inmediato del cliente se desactiva en este camino: bajo cinco llamadas por hora, gastar una segunda en un `504` no compensa.

Queda un detalle del traspaso entre siembra y refresco del que depende la corrección del precio mostrado. **La siembra no es atómica**: pagina durante doce días, así que una tarifa capturada en la página 1 refleja el estado de REVE del primer día y no del último. Si el primer refresco arrancara en `completed_at`, se saltaría en silencio cualquier precio que hubiera cambiado durante la propia siembra. Por eso la primera marca de agua es `min(last_refreshed_at)` sobre las tarifas, la captura más antigua. Drenado ese primer barrido, todas las filas comparten un mismo instante de captura y el modelo de marca única ya es correcto en adelante.

La auditoría distingue además dos recuentos que es fácil confundir. Como el *upsert* reescribe toda fila descargada cambie o no su precio, el número de filas tocadas sobrestima el movimiento real; la línea `reve_etl_tariffs` registra por eso `rows` —lo descargado— junto a `changed`, las tarifas cuyo `last_tariff_updated` cae dentro de la ventana consultada, es decir, las que de verdad cambiaron en origen.

**El estado del espejo se declara, no se disimula.** Un fallo de rendimiento del lado de REVE —ventanas de consulta amplias que expiraban por tiempo— mantuvo la marca de agua congelada durante semanas, y es el que motivó la lógica de salto descrita arriba. El propio planificador se desplegó primero detenido, para poder inspeccionar el cursor antes de que un tick lo moviera. La aplicación siguió sirviendo durante todo ese tiempo las tarifas de la última captura buena, que es exactamente lo que el diseño de espejo promete: quedarse desactualizado en lugar de caerse.

> **PENDIENTE:** medición del primer ciclo de refresco tras reactivar el planificador — cuántos ticks tarda la marca de agua en volver a un instante reciente, cuántas filas se saltan en el primer `reve_refresh_jumped_to_recent` y cuántas tarifas cambian realmente (`changed`) en el primer día de operación normal.

## Precios: por qué la estimación dejó de mostrarse

Antes de decidir cómo mostrar un precio hubo que mirar qué son realmente las tarifas del catálogo. Y no son lo que el nombre sugiere: **la tarifa de REVE es un precio comercial plano, no un precio horario**. Cientos de tarifas coinciden en los mismos valores redondos, y los operadores reprecian en lotes esporádicos, con meses entre cambios, de forma desacoplada del mercado mayorista. No hay un «precio de REVE en tiempo real» que perseguir, lo que justifica que baste con refrescar tarifas una vez por hora.

Lo segundo que dicen los datos es que el margen del operador sobre el coste de la energía es estable por tipo de recarga. Frente a un PVPC de referencia de unos **0,12 €/kWh**, la mediana sobre unas **27.000 tarifas reales** da **+0,22 €/kWh en corriente alterna** y **+0,32 €/kWh en corriente continua**. Varía entre operadores, pero el valor por tipo basta como estimación.

De ahí salió una **cascada de tres escalones**, que se construyó y luego se retiró de la pantalla. Si el conector tenía tarifa real almacenada se servía esa; si no, se estimaba como `PVPC(hora) + margen[tipo]`; y la respuesta viajaba etiquetada con su procedencia (`reve_tariff` o `pvpc_plus_margin`) para que la interfaz distinguiera un dato de una estimación. La apuesta era que **etiquetar la procedencia permite estimar sin engañar**.

**No se sostiene, y es un camino no tomado que merece contarse.** Un número verosímil colocado donde el usuario espera un precio se lee como un precio, lea o no la etiqueta que lo acompaña: la cifra ocupa el lugar destacado y la procedencia es letra pequeña. El fallo es el mismo que se le reprocha a simular la disponibilidad —*un dato inventado que se lee como real es peor que un campo vacío*—, con un agravante que la disponibilidad no tiene: aquí la estimación es **nuestra** y se estaba atribuyendo a la tarifa de un tercero. Un conductor que llega al poste esperando 0,34 €/kWh porque la aplicación se lo dijo no distingue si el número salió del operador o de una mediana estadística; simplemente paga otra cosa.

Hoy el precio que se muestra sale **siempre de lo que el operador publica**, resuelto por franjas sobre el conector, y **un conector sin tarifa no tiene precio ni coste**: la simulación devuelve duración y energía, y deja el coste vacío. Los miles de conectores de los que REVE no publica tarifa se quedan sin cifra, que es la respuesta honesta.

**La estimación sobrevive, cambiada de sitio.** Los márgenes medidos siguen siendo un resultado válido, y en la fase 8 son lo que se **ofrece** al propietario de un punto privado cuando fija su propio precio: ahí sugerir un número es justamente el objetivo, no una afirmación sobre el poste de nadie. El código vive en `backend/app/services/price_suggestion.py`, sin ningún llamador hasta entonces y con el motivo escrito en el propio módulo para que nadie lo borre por parecer muerto.

> **[FIGURA 5.3]** — *De la tarifa publicada al precio que se enseña.* Árbol de decisión sobre `pricing_kind`: franja de energía resuelta para la potencia del conector, *gratis*, tarificado por tiempo o por sesión, tarifa caducada con su fecha, y sin precio publicado. Debe verse qué mensaje sale en cada rama y que **ninguna produce una cifra estimada**, con la rama de sugerencia al propietario (fase 8) dibujada aparte para dejar claro que no alimenta esta pantalla. **Cómo obtenerla:** diagrama a dibujar en Mermaid (`flowchart`) sobre `backend/app/services/tariff_pricing.py`.

La curva de precios se ingiere de la API pública de datos de REE, que no exige token: el PVPC aparece como serie con identificador **1001** dentro del *endpoint* de precios de mercado, en €/MWh, y se almacena una fila por hora en €/kWh, con histórico desde el **1 de enero de 2026** [10]. Consultada con agregación horaria, esa serie devuelve 24 valores por día, y sobre 24 valores está construido el sistema; el encaje de esa granularidad con la norma corresponde al capítulo 10, «Marco regulador».

Un detalle de la ingesta merece mención porque es una decisión y no un descuido: **REE responde con un error de servidor para un día que aún no ha publicado**. El cliente lo trata como «todavía no» y no como fallo — registra una línea de auditoría, devuelve una lista vacía y deja que el siguiente intento lo recoja. Confundir «aún no existe» con «se ha roto» habría llenado el registro de falsos positivos todas las tardes.

## El catálogo de vehículos

Treinta y un modelos habituales del mercado español, cada uno con capacidad útil de batería, potencia máxima en alterna, potencia máxima en continua y estándar de conector en continua. La recarga en alterna es siempre Type 2 en el mercado europeo, así que lo único que varía por modelo es el estándar de continua, CCS o CHAdeMO.

Está curado a mano desde fichas técnicas públicas de fabricante, y no importado de una API, porque no se localizó ninguna que fuera a la vez gratuita, completa para el mercado español y con una licencia de reutilización limpia. Una treintena de modelos basta para que la mayoría de los conductores encuentre el suyo o uno equivalente, y mantenerlos cuesta una lista en una semilla idempotente. Son valores de ficha, aproximados a efectos de simulación, y así se declaran.

## Caminos no tomados

**ACN-Data.** El conjunto abierto de sesiones de recarga de Caltech [38] se consideró para calibrar la ocupación y dar realismo a las sesiones simuladas. Llegó a haber una migración que creaba su tabla y otra posterior que la borra. Se descartó por dos razones que se refuerzan: es aparcamiento de un campus universitario californiano, una distribución sin traducción defendible a la red pública española; y, sobre todo, el resultado quedaba como dato interno sin valor de cara al usuario, que no ve una calibración, ve un color en un marcador.

**La ocupación simulada.** El segundo paso del mismo camino fue sustituir la calibración por un modelo sintético ligero que generase ocupación verosímil por franja horaria. Barato y bueno para una demostración. También abandonado, y por la razón que importa: producía un dato que quien usara la aplicación leería como real sin serlo, indistinguible de un dato verdadero en la interfaz, y sostener esa distinción ante una sola pregunta en la defensa costaba más de lo que aportaban unos marcadores de colores.

La consecuencia es que **la disponibilidad no se modela**. Los puntos aparecen disponibles por defecto, y eso es un valor ilustrativo que la memoria declara en lugar de disimular. La estructura queda intacta: la columna `status` con el valor OCPI del EVSE, la agregación por punto —disponible si alguno figura libre, ocupado si todos los conocidos están en uso, desconocido si no hay dato— y los colores del marcador siguen ahí, alimentables por una fuente real, ya sea un acuerdo con un operador o el propio REVE si algún día publica el flujo de estado, sin más migración que empezar a escribir en esa columna. Ocultar la dimensión entera habría eliminado la señal engañosa, pero también el punto de extensión.

Conviene separar dos cosas que se confunden. La *disponibilidad* (libre o en uso) es la que no se modela. El *estado operativo* (funciona o está averiado) es otra dimensión, se asume siempre operativo y su *endpoint* se eliminó del ETL junto con su cursor: sondear unos 42.000 EVSEs a cinco peticiones por hora no es aritméticamente posible, y una cobertura parcial sería peor que ninguna, porque el usuario no podría saber qué puntos llevan estado real y cuáles no.
