# 4. Arquitectura del sistema

## Visión de conjunto

El sistema en ejecución son tres piezas y un proceso que trabaja aparte. En el navegador del
móvil corre la PWA: una aplicación de página única servida como ficheros estáticos, con su
manifiesto y su *service worker*. Bajo un único dominio, un proxy inverso reparte por ruta —lo
que empieza por `/api/` va al backend FastAPI, el resto se sirve como fichero de la aplicación—.
El backend habla con una sola base de datos PostgreSQL mediante un controlador asíncrono. Y
fuera del camino de la petición, un conjunto de procesos ETL escribe en esa misma base de datos
por su cuenta: el espejo del catálogo de REVE y la ingesta diaria de la curva de precios.

Que los ETL queden fuera de ese camino no es una preferencia estética. La API de REVE admite
5 peticiones/hora, y ese techo descarta cualquier arquitectura en la que abrir el mapa provoque
una llamada a REVE: el catálogo se copia una vez y se mantiene desde entonces. La restricción
es, con diferencia, la que más forma da al sistema, y el capítulo 5 la argumenta en detalle. Hoy
el contenedor que dispara esos procesos está desplegado pero deliberadamente detenido, por
motivos que corresponden al capítulo 8.

**La propiedad que ordena el resto del diseño es el mismo origen.** La aplicación y su API se
publican bajo un solo dominio: el navegador descarga la SPA de `https://s-charge.app` y todas
sus llamadas salen contra `https://s-charge.app/api/*`. Para el navegador, la API no es un
tercero, sino la misma aplicación. De ahí se siguen dos consecuencias que atraviesan el trabajo
entero. La primera es que la sesión puede vivir en una cookie `HttpOnly` de origen propio, que
el código JavaScript no puede leer y que el navegador adjunta sin que el cliente la manipule
—el capítulo 6 desarrolla la sesión, sus atributos y su modelo de amenazas—. La segunda es que
no hay superficie CORS: ni *preflight*, ni lista de orígenes autorizados, ni una configuración
que mantener sincronizada entre dos despliegues distintos. Lo que no existe no se puede
configurar mal.

El entorno de desarrollo conserva la propiedad en lugar de simularla: el servidor de desarrollo
de Vite hace de proxy de `/api/*` hacia el backend nativo, de modo que la cookie también es de
origen propio mientras se programa. Un fallo de cookies entre orígenes no puede aparecer solo en
producción, porque en desarrollo tampoco hay dos orígenes.

> **[FIGURA 4.1]** — *Arquitectura de ejecución.* Diagrama de cajas y flechas, la figura
> principal del capítulo. Arriba, caja **Navegador (móvil)** con la PWA —React + Vite—, el
> *service worker* y el manifiesto. De ella sale una flecha rotulada **HTTPS · cookie
> `HttpOnly` de origen propio** hacia la caja **Caddy — proxy inverso, un solo dominio**. De
> Caddy salen dos flechas etiquetadas por ruta: `/api/*` → caja **FastAPI**, y `/*` → caja
> **nginx (ficheros estáticos de `dist/`)**. Dentro de la caja de FastAPI, escrito en tres
> niveles, `routers → services → models`. De FastAPI sale una flecha rotulada **asyncpg
> (asíncrono)** hacia la caja **PostgreSQL 18**, con las diez tablas listadas dentro. A un lado,
> desconectada del camino anterior, la caja **Procesos ETL (cron en el contenedor
> `scheduler`)**, con dos flechas salientes hacia dos cajas externas —**API de REVE** (rotulada
> «5 peticiones/hora») y **API de REE `apidatos`**— y una flecha entrante a PostgreSQL rotulada
> **escrituras periódicas (`upsert`)**. Un marco discontinuo debe englobar Caddy, nginx,
> FastAPI, PostgreSQL y el `scheduler`, con la etiqueta «un único servidor, Docker Compose
> (capítulo 8)». Lo que la figura tiene que dejar ver de un vistazo: que el navegador solo
> conoce un origen, y que la ruta de datos externa no atraviesa la API.
> **Cómo obtenerla:** diagrama a dibujar en draw.io o Mermaid.

## El backend por capas

El backend se organiza en tres capas —`routers → services → models`— sostenidas por una regla
que se puede comprobar leyendo un fichero: **los routers son finos y la lógica de negocio no
importa FastAPI**. Un router valida la entrada, llama a un servicio y devuelve lo que recibe;
todo lo que decide algo vive en `app/services/`, donde no aparece ninguna importación del
*framework*.

Lo que compra esa regla no es orden visual, sino una propiedad de las pruebas. Un servicio que
no conoce FastAPI se ejerce como una función corriente: la simulación de recarga y la cascada de
precios se prueban con entradas y salidas, sin cliente HTTP que levantar, sin inyección de
dependencias que resolver y, en su mayor parte, sin base de datos. La consecuencia práctica es
que la parte del sistema donde vive el criterio —la que puede estar mal de una forma que no se
ve— es también la más barata de comprobar.

El resto de la estructura completa el reparto. En `app/schemas/` están los modelos Pydantic de
petición y respuesta, que son a la vez la validación de entrada y la fuente del esquema OpenAPI
del siguiente apartado. En `app/models/`, un fichero por agregado con las tablas SQLAlchemy. En
`app/integrations/`, los clientes HTTP de las dos APIs externas, aislados para que el resto del
código no sepa cómo pagina REVE ni cómo responde REE. Y en `app/etl/`, la lógica de los procesos
periódicos, que reutiliza esos clientes y esos modelos pero no pasa por la API.

```text
backend/app/
  routers/       auth · points · prices · simulate · users · vehicles
  services/      points · pricing · prices · simulation · email · user_manager
  models/        user · cpo · charging_point · tariff · vehicle · price · etl
  schemas/       auth · point · price · simulation · vehicle · health
  integrations/  reve · ree
  etl/           reve · pvpc · cursor
  utils/         audit · auth_backend · rate_limit · security
```

Son ~3.157 líneas de Python sobre 10 tablas y 9 migraciones de Alembic. La autenticación se
aplica en el punto de montaje de los routers y no ruta a ruta, de forma que un *endpoint* nuevo
dentro de uno de ellos nace protegido; el capítulo 6 lo desarrolla.

## El frontend

El frontend se organiza **por funcionalidad**: un fichero vive con la funcionalidad que lo
posee. La página del mapa, sus filtros, su hoja inferior de detalle y el *hook* que trae los
puntos están juntos en `features/map/`, y no repartidos entre una carpeta de páginas, otra de
componentes y otra de *hooks*. `components/` y `lib/` guardan únicamente lo que de verdad
comparten varias funcionalidades —el cliente de la API generado, el guardián de rutas
protegidas—; un componente que solo usa una funcionalidad no llega ahí. Cada funcionalidad se
mantiene plana hasta que crece: la subcarpeta aparece cuando el primer fichero la necesita, no
antes.

Dos reglas más pequeñas sostienen el conjunto, y ambas existen por el mismo motivo. No hay
ficheros barril —ningún `index.ts` por funcionalidad— y los iconos se importan por ruta
completa, nunca desde el paquete raíz. Un solo `import { Foo } from '@mui/icons-material'`
arrastra el manifiesto entero de iconos al *chunk* y anula el *tree-shaking* en silencio, que es
la peor clase de regresión de rendimiento: no falla nada, simplemente se descargan cientos de
kilobytes de más. Por eso la regla no se confía a la disciplina, sino que la vigila el *linter*
con una restricción de importaciones que rompe la construcción. Son ~4.732 líneas de TS, TSX y
CSS.

## El contrato entre las dos mitades

Los tipos con los que el frontend habla con la API no se escriben: **se generan**. FastAPI
deriva el esquema OpenAPI de los modelos Pydantic, una tarea del repositorio lo exporta a un
`openapi.json` versionado y de ese fichero se regenera el tipado del cliente. Ambos ficheros
—el esquema y los tipos— se guardan en el repositorio, de modo que un cambio de contrato aparece
en el *diff* de la revisión y no en la consola del navegador.

La consecuencia es la que importa. Como el esquema está en el repositorio, la integración
continua puede regenerarlo desde el código y comparar: si difiere, falla. **Un cambio de
contrato rompe la integración continua en lugar de romper el frontend en ejecución.** Antes de
versionar el esquema esto no era posible, porque generar los tipos exigía tener el backend
levantado, algo que ninguna comprobación automática hacía. El principio es el mismo que ordena
el último apartado de este capítulo: mover una verificación de una persona a una herramienta.

> **[FIGURA 4.2]** — *Cómo se genera el contrato.* Cadena de cajas de izquierda a derecha:
> **modelos Pydantic + routers** → **esquema OpenAPI** (`app.openapi()`) → **`openapi.json`
> versionado en el repositorio** → **`openapi-typescript`** → **`schema.d.ts`** → **cliente
> tipado (`openapi-fetch`) usado por los *hooks* de TanStack Query**. Debajo, una caja
> **Integración continua** con una flecha que entra en la cadena, regenera el esquema desde el
> código y lo compara con el fichero versionado; salida etiquetada «difiere → falla la
> construcción». Marcar con un icono los dos ficheros que se guardan en el repositorio.
> **Cómo obtenerla:** diagrama a dibujar en draw.io o Mermaid.

## El stack y sus razones

El inventario completo de bibliotecas y versiones es un anexo; aquí interesa el razonamiento de
las piezas que sostienen la arquitectura descrita.

En el cliente, **React sobre Vite y TypeScript**. Sobre esa base, el estado de servidor se
gestiona con **TanStack Query**, y conviene decir qué problema resuelve porque no es evidente:
una aplicación que crece en *endpoints* de lectura acaba reimplementando en cada página, con
`useEffect`, la misma caché, la misma deduplicación de peticiones simultáneas, la misma política
de reintento y los mismos estados de carga y error. TanStack Query los define una vez. El caso
que lo justifica aquí es el mapa: su carga de puntos se pide una vez y se comparte entre visitas
dentro de la misma sesión, en lugar de volver a descargarse cada vez que el usuario vuelve a la
pestaña.

El mapa se dibuja con **MapLibre GL JS sobre teselas de OpenFreeMap**. Tres restricciones
deciden: unos 13.700 puntos sobre un móvil de gama media, presupuesto cero y un repositorio
público donde no puede vivir una clave de API. MapLibre renderiza por WebGL y agrupa los puntos
de forma nativa, que es exactamente la forma en que el backend sirve el conjunto; OpenFreeMap
entrega teselas vectoriales sin registro, sin clave y sin cuota de uso. Las alternativas con
mejor documentación —Mapbox GL JS, Google Maps— exigen todas un identificador facturable que
acabaría empaquetado en el *bundle* de un repositorio abierto.

La aplicación se distribuye como **PWA instalable**: manifiesto de aplicación web, que declara
nombre, iconos, ámbito y modo de presentación [37], y *service worker* para el
arranque de la carcasa. Es la vía por la que una aplicación construida con tecnologías web se
instala en el dispositivo y se comporta como una nativa [33], sin dos cadenas de
construcción ni dos revisiones de tienda para un solo desarrollador. Tiene además una atadura
con el apartado anterior: las interfaces del *service worker* solo están disponibles en contexto
seguro [34], de modo que HTTPS no es una buena práctica añadida sino un
requisito de instalabilidad.

Tener un *service worker* obliga a decidir algo que la literatura de PWA suele dar por resuelto:
qué se puede servir desde una caché. La carcasa se precachea entera, porque un *build* es
inmutable por construcción y su versión la fija el propio artefacto. Los datos no, y el criterio
que los separa no es cuánto ocupan sino **cuánta caducidad toleran**. El catálogo de puntos solo
se mueve cuando se ejecuta la siembra, así que servirlo con *stale-while-revalidate* cambia un
dato de horas por un mapa que aparece de inmediato y se refresca por detrás. Los precios siguen
al PVPC hora a hora, y ahí una caché sería una mentira silenciosa: un fallo de red se ve —la
pantalla no pinta— y el usuario sabe que no debe fiarse, mientras que un precio caducado
presentado como actual es indistinguible de uno correcto. La aplicación prefiere fallar de forma
visible a acertar de forma dudosa, que es la misma premisa por la que una sesión vale el
presupuesto que aceptó y no el precio del instante en que se consulta. El monedero y el
histórico quedan fuera por esa razón y por una segunda: son datos de un usuario concreto, y una
caché del dispositivo los sobreviviría al cierre de sesión.

Conviene entonces no exagerar qué significa aquí «funciona sin conexión». Sin red la aplicación
arranca y pinta su interfaz, pero no tiene datos que mostrar, y el mapa —que es la pantalla
principal— tampoco se dibuja, porque su cartografía base se descarga de un tercero. La casilla
que la instalabilidad parece prometer está deliberadamente medio marcada, y decirlo es más útil
que dar por hecho que un *service worker* equivale a una aplicación sin conexión.

En el servidor, **FastAPI** con **SQLAlchemy 2.0 en modo asíncrono**, **Alembic** para las
migraciones y **Pydantic** para el contrato; un solo motor asíncrono sirve tanto a la API como a
los procesos ETL. Los datos viven en **PostgreSQL 18**, elegido por tener restricciones de
verdad —una integridad que un código defectuoso no puede saltarse— y por dos novedades concretas
de esa versión mayor, que se argumentan a continuación.

## Decisiones revisadas a mitad de proyecto

Varias decisiones tomadas al principio se han sustituido, y una de ellas está argumentada pero
aún no ejecutada. Interesan menos por su resultado técnico que por el criterio común que las
ordena, que apareció al plantearlas y resultó más útil que la pregunta habitual de cuánto código
hay que tocar: **si la migración la verifica una herramienta o la verifica una persona.**

Subir de versión el intérprete de Python, cambiar de versión mayor la base de datos o generar
los tipos del cliente desde el esquema son cambios que el comprobador de tipos, la batería de
pruebas y la construcción confirman o rechazan; el número de ficheros afectados es casi
irrelevante, porque si la integración continua pasa, la migración es correcta. Reescribir una
decena de pantallas no lo verifica ninguna herramienta: el compilador confirma que el código
compila, pero que la aplicación se siga viendo bien en un móvil de 360 px solo lo confirma
alguien mirándola. Ese es el coste real, y es el que decide cuáles se hacen sin apenas
deliberación y cuál exige una fase propia.

### De MUI a Tailwind + shadcn/ui

El frontend se construyó sobre MUI con Emotion, y ahí sigue: se llegó a diseñar una migración a
Tailwind con shadcn/ui, y **se descartó**. La decisión original fue correcta y conviene decirlo sin
ambigüedad, porque un solo desarrollador con calendario fijo necesitaba controles de formulario,
diálogos, navegación y, sobre todo, anillos de foco accesibles y atributos ARIA correctos sin
escribirlos. Esa decisión permitió tener las pantallas de autenticación, el mapa y la ficha de
punto funcionando en semanas. MUI no falló; lo que cambió es el peso relativo de los criterios.

Cuatro cosas la hacen caducar. Emotion serializa e inyecta estilos en tiempo de ejecución, en
cada renderizado, mientras que Tailwind resuelve lo mismo al compilar y no deja motor de estilos
en el paquete —la auditoría Lighthouse de la fase 2 dio 31 en rendimiento en `/map` bajo
*throttling* móvil; el motor de mapas domina esa cifra, pero el coste del CSS en tiempo de
ejecución es aditivo y evitable—. shadcn/ui no es una dependencia sino código copiado al
repositorio, de forma que adaptar el sistema de diseño pasa de sobrescribir estilos ajenos desde
fuera a editar ficheros propios; los más de cien usos de la prop `sx` acumulados son la señal
habitual de que el sistema de diseño y la librería tiran en direcciones distintas. TanStack
Router valida en tiempo de compilación los parámetros de ruta y de búsqueda, convirtiendo en
error de construcción una familia de fallos que hoy solo aparece en ejecución. Y falta una capa
de formularios que la aplicación nunca ha tenido: el alta de puntos privados será el primer
formulario real, y un único esquema Zod validaría en cliente lo mismo que Pydantic valida en
servidor.

**El argumento decisivo no es ninguno de los anteriores: es el momento.** El coste de migrar
crece con cada fase. Hoy son una decena de pantallas; después de puntos privados, optimizador,
reservas y monedero serían del orden de dieciocho, y construir ocho pantallas nuevas sobre una
base que se pretende abandonar es el desperdicio real, no la migración. La decisión es binaria:
o ahora, o nunca.

Las alternativas se pesaron y perdieron. *No migrar* tiene coste cero, y equivale a decidir no
migrar nunca. *Seguir en MUI con un motor de estilos sin tiempo de ejecución* —Pigment CSS—
resolvería el primer punto conservando la API de componentes, pero la propia documentación de
MUI lo describe como alfa temprana, y no toca la propiedad de los componentes, el tipado de
rutas ni los formularios: apostar la interfaz de un trabajo con entrega fija a una API en alfa
es un mal cambio. *Migrar solo los estilos* ahorra menos de lo que parece, porque los ficheros de
enrutado se tocan igualmente al reescribir cada pantalla. Y la *migración incremental, pantalla
a pantalla*, es la aparentemente prudente y la peor: obliga a mantener dos sistemas de estilos
durante semanas, con dos maneras de hacer cada cosa y el doble de superficie de revisión.

> **PENDIENTE:** medida posterior a la migración —Lighthouse en `/map` y en una pantalla de
> formulario, y tamaño del *bundle*, con el mismo método de la auditoría de la fase 2— para
> contrastarla con la medida previa. El resultado se publica sea cual sea; una mejora marginal
> también es un hallazgo.

### PostgreSQL 17 → 18

Aquí no se sustituye una herramienta, se sube de versión mayor la misma, y lo que lo justifica
son novedades concretas. La primera son las **claves primarias temporales `WITHOUT OVERLAPS`**.
La fase de reservas debe garantizar que dos reservas no solapen sobre el mismo conector, y
comprobarlo en la aplicación —consultar si hay solape y después insertar— arrastra una condición
de carrera clásica: entre la consulta y la inserción, otra transacción puede insertar una reserva
que solape. Declarar el rango temporal como parte de la clave primaria convierte la detección de
conflictos en una invariante del esquema, imposible de saltarse por concurrencia o por un camino
de código que olvide comprobarla. Para una funcionalidad cuyo valor depende de que la reserva
signifique algo, la diferencia no es de comodidad sino de corrección. El diseño de esa tabla
corresponde a la fase 10 y no está construido.

La segunda es `uuidv7()`, **evaluada y descartada**. Las claves primarias del proyecto son UUID
versión 4, aleatorios, de modo que cada inserción cae en una hoja arbitraria del índice; UUIDv7
antepone una marca de tiempo y las claves nuevas se insertan de forma aproximadamente ordenada.
Sobre el papel es atractiva. No se adopta porque **su beneficio es de localidad en la inserción y
este sistema apenas inserta**: la tabla mayor ronda las 47.000 filas y se sembró una vez, y el
flujo permanente son veinticuatro precios al día y *upserts* dispersos del refresco de tarifas. A
esa escala la diferencia no es pequeña, es inmedible. El argumento que decide es el mismo
criterio de este apartado: **un cambio cuyo beneficio no puede medirse no se defiende, se cree**.
Adoptarlo obligaría a escribir que «mejora la localidad del índice» sin un número detrás, que es
exactamente la clase de afirmación que este trabajo intenta no hacer. Queda como camino no
tomado, con la puerta abierta donde tendría sentido: las tablas de sesiones y reservas serán las
primeras con un ritmo de inserción real.

El coste operativo, en cambio, es real y no se disimula. Un salto de versión mayor no es cambiar
la etiqueta de la imagen: el formato del directorio de datos cambia, un volumen de la 17 bajo una
imagen 18 se niega a arrancar, y desde la 18 cambia además el punto de montaje. El procedimiento
es volcar con la imagen antigua, destruir el volumen, arrancar la nueva y restaurar. Como la base
de datos contiene una siembra que costó ~12 días de ticks bajo el límite de 5 peticiones/hora,
ese es el punto exacto donde el cambio podría costar datos irrecuperables, y por eso se
documenta como procedimiento y no como nota al pie.

### El entorno de desarrollo

El proyecto ejecutaba en contenedores las tres piezas, con recarga en caliente por *bind mounts*.
Hoy solo PostgreSQL corre en contenedor durante el desarrollo; backend y frontend se ejecutan de
forma nativa. El argumento decisivo no es la velocidad, aunque mejore: es que **ya existía una
cadena de herramientas nativa y era la autoritativa**. Los *hooks* de git, el comprobador de
tipos, el *linter* y las pruebas corren en el host, y son los que deciden si un *commit* entra y
si la integración continua pasa. El contenedor de desarrollo era un segundo entorno paralelo al
que realmente gobierna el proyecto, con su clase de fallo asociada: funciona en el contenedor,
falla en el *hook*. Colapsar los dos en uno elimina esa categoría entera.

La paridad con producción, que era el argumento a favor de los contenedores en desarrollo, se
conserva donde importa: producción sigue ejecutando el stack completo en contenedores, ese mismo
stack se levanta en local para una prueba de humo y la integración continua construye las
imágenes de producción en cada *pull request*. La paridad, además, nunca fue total: las imágenes
de desarrollo usaban etapas de construcción distintas de las de producción.
