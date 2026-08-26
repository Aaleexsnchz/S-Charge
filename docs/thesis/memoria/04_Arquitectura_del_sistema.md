# 4. Arquitectura del sistema

Este capítulo describe cómo está construido el sistema y por qué está construido así. Recorre
primero las piezas en ejecución y la decisión de publicarlas todas bajo un mismo origen; después el
servidor y el cliente por dentro, cada uno con su *stack* y las decisiones que lo justifican,
además del contrato que los une. Termina con las comprobaciones automáticas y el entorno en que se
construye.

## Visión general

El sistema sigue una arquitectura cliente-servidor [38] y está compuesto de tres piezas en el
camino de la petición y varios procesos que trabajan aparte. En el navegador del móvil corre la
PWA: una aplicación de página única (SPA) servida como ficheros estáticos, con su manifiesto y su
*service worker*. Bajo un único dominio, un proxy inverso reparte por ruta: lo que empieza por
`/api/` va al *backend* y el resto se sirve como fichero de la aplicación. El *backend* habla con
una sola base de datos PostgreSQL mediante un controlador asíncrono.

El *stack* utilizado para el desarrollo del sistema es FastAPI y PostgreSQL en el servidor y React
sobre Vite en el cliente. Esta es una combinación habitual hoy en día en el desarrollo web, con
documentación abundante y un ecosistema maduro. En mi caso, es además la combinación usada
habitualmente en el ámbito profesional. En un proyecto de fin de máster, en el que participa un
solo desarrollador y hay un plazo fijo, eso pesa más que una comparativa entre alternativas, ya que
el tiempo que no se gasta aprendiendo herramientas nuevas se emplea en el problema.

Las dos mitades viven en un único repositorio, lo que facilita el trabajo de desarrollo. Separarlas
sería conveniente solo si hubiera personas o equipos independientes para cada pieza. Fuera del
camino de la petición, tres procesos ETL escriben en esa misma base de datos por su cuenta: la
siembra del catálogo de REVE, el refresco incremental de los puntos —que relevó a la siembra al
terminar la primera copia— y la ingesta diaria de la curva de precios.

Que los ETL queden fuera de ese camino es consecuencia directa del límite de 5 peticiones/hora de la API de REVE. Ninguna arquitectura en la que abrir el mapa provoque una llamada a la fuente es viable con esa restricción, así que el catálogo se copia una vez y desde entonces el refresco reparte su presupuesto por orden de prioridad: primero las tarifas, que son lo único que se mueve con frecuencia, y solo con lo que sobre el catálogo físico. Ese mismo script de refresco es además el que descubre los puntos que REVE ha publicado después de la siembra inicial, ya que al llegar la tarifa de un conector que la base de datos no conoce sus identificadores quedan anotados en una tabla hasta que una llamada al catálogo trae la estación entera. El capítulo 5 lo desarrolla.

La siguiente figura recoge la estructura del repositorio en su primer nivel y, dentro de cada
mitad, la organización de sus carpetas, que los dos apartados siguientes explican:

> **[FIGURA 4.1]** — *Estructura del repositorio: primer nivel, backend y frontend.*

La propiedad que ordena el resto del diseño es el mismo origen. La aplicación y su API se publican
bajo un solo dominio: el navegador descarga la SPA de `https://s-charge.app` y todas sus llamadas
salen contra `https://s-charge.app/api/*`. Para el navegador, la API no es un tercero, sino la
misma aplicación, porque coinciden esquema, *host* y puerto, que son los tres componentes con los
que la política del mismo origen decide qué puede acceder a qué [39]. De ahí se siguen dos
consecuencias que atraviesan el trabajo entero. La primera es que la sesión puede vivir en una
cookie `HttpOnly` de origen propio, que el código JavaScript no puede leer y que el navegador
adjunta sin que el cliente la manipule; el capítulo 6 la desarrolla. La segunda es que no hay
superficie CORS que configurar, y eso importa por seguridad y no por comodidad. CORS no protege:
relaja la política del mismo origen, y una relajación excesiva no rompe nada, así que puede pasar
inadvertida. Bajo un mismo origen esa clase de fallo no se mitiga, no existe.

> **[FIGURA 4.2]** — *Diagrama de contenedores de S-Charge* (modelo C4 [33], nivel 2).

## El backend

Sobre FastAPI y PostgreSQL 18 se apoyan tres piezas más: SQLAlchemy 2.0 en modo asíncrono para el
acceso a los datos, Alembic para versionar los cambios del esquema y Pydantic para validar lo que
entra y sale de la API. Un solo motor asíncrono atiende tanto las peticiones como los procesos ETL.
Al margen de la aplicación, el trabajo diario se sostiene en uv para las dependencias y el entorno
virtual, Ruff para el formato y las reglas de estilo, basedpyright para los tipos y pytest para las
pruebas. El inventario completo de bibliotecas y versiones se encuentra en el anexo.

El *backend* se organiza en tres capas —*routers* → *services* → *models*— según el patrón de
arquitectura en capas, cuya frontera principal está aquí entre las dos primeras: los *routers* se
ocupan del protocolo y los servicios, del dominio. Un *router* valida la entrada, llama a un
servicio y devuelve lo que recibe; las decisiones viven en `app/services/`; y la tercera capa,
`app/models/`, declara las tablas como clases de SQLAlchemy —un fichero por agregado— y es la única
que conoce el esquema de la base de datos. La separación permite probar el dominio sin levantar la
aplicación, ya que una prueba puede llamar directamente al servicio, pasarle unos datos y comprobar
lo que devuelve, sin necesidad de un servidor que atienda la petición. No hay entre los servicios y
los modelos una cuarta capa de repositorios porque no es necesaria: SQLAlchemy ya abstrae el acceso
a los datos [40], de modo que envolverlo añadiría una indirección sin aislar nada que no esté
aislado.

El resto de la estructura, que la figura 4.1 recoge, completa el reparto. En `app/schemas/` están
los modelos Pydantic de petición y respuesta, que son a la vez la validación de entrada y la fuente
del esquema OpenAPI del siguiente apartado. En `app/integrations/`, los clientes HTTP de las dos
APIs externas de datos, se encuentran aislados para que el resto del código no dependa de cómo
pagina o responde cada una; el envío de correo, que se apoya en Resend, se resuelve en su propio
servicio. En `app/etl/`, se encuentra la lógica de los procesos periódicos, que reutiliza esos
clientes, esos modelos y los servicios pero no pasa por la API; sus puntos de entrada viven en
`backend/scripts/`, fuera de `app/`, y son los que el capítulo 5 detalla. Que los procesos ETL
escriban directamente en la base de datos y no contra sus propios *endpoints* es deliberado, ya que
hacerlo por HTTP obligaría a publicar una superficie de escritura masiva que ninguna funcionalidad
del producto necesita y que habría que autenticar y proteger. Esto encarecería cada registro y
ataría la ingesta a que el *backend* esté levantado. El riesgo de esa vía directa sería que la API
y los procesos acabaran con definiciones distintas de las mismas tablas, y lo evita que ambos
importen los modelos de `app/models/`.

## El frontend

Sobre React y Vite, el cliente se escribe en TypeScript, gestiona sus dependencias con pnpm y
confía a Biome el formato y las reglas de estilo; el tipado lo comprueba el propio compilador de
TypeScript.

El *frontend* se organiza por funcionalidad: un fichero vive con la funcionalidad que lo posee. La
página del mapa, sus filtros, su hoja inferior de detalle y el *hook* que trae los puntos están
juntos en `features/map/`, y no repartidos entre una carpeta de páginas, otra de componentes y otra
de *hooks*. Las carpetas `components/` y `lib/` guardan únicamente lo que de verdad comparten
varias funcionalidades —el cliente de la API generado, el guardián de rutas protegidas—; un
componente que solo usa una funcionalidad no llega ahí. Cada funcionalidad se mantiene plana hasta
que crece, y la subcarpeta aparece cuando el primer fichero la necesita, no antes. El contraste con
la organización por capas del servidor se aprecia en la figura 4.1.

El enrutado lo resuelve React Router, del que depende la carga de datos por ruta y, con ella, el
arranque de la sesión que describe el capítulo 6. El estado de servidor se delega en una biblioteca
que resuelva de una sola vez la caché, la deduplicación de peticiones simultáneas y los estados de
carga y error, que de otra manera habría que reimplementar en cada página; el caso principal en el
que se usa es el mapa, cuya carga de puntos se solicita una vez y se comparte entre visitas de la
misma sesión. La biblioteca utilizada en este caso es TanStack Query, entre otras bibliotecas
equivalentes, porque no impone cliente de *fetch* propio y se acopla sin fricción al cliente tipado
que se genera desde el esquema OpenAPI; RTK Query habría obligado a introducir Redux, que el
proyecto no necesita para nada más. Por último, la interfaz se apoya también en una biblioteca de
componentes ya resueltos en accesibilidad —controles de formulario, diálogos, hojas inferiores y
avisos, con anillos de foco visibles y atributos ARIA correctos—. Aquí se ha recurrido a MUI por la
cobertura de ese catálogo y por experiencia previa con él, pero se podría haber optado por alguna
otra opción similar, como shadcn/ui.

El mapa se dibuja con MapLibre GL JS sobre teselas de OpenFreeMap. Los cerca de 13.700 puntos del
catálogo descartan de entrada las bibliotecas que dibujan un marcador por elemento y obligan a
escoger una que renderice por WebGL y agrupe de forma nativa, que es además la manera en que el
*backend* sirve el conjunto. Eso deja tres candidatas equivalentes en lo técnico —MapLibre GL JS,
Mapbox GL JS y Google Maps— y la decisión se traslada al coste, porque las dos últimas facturan por
carga de mapa a partir de cierto umbral y exigen dar de alta un medio de pago, mientras que
MapLibre es de código abierto y OpenFreeMap entrega teselas vectoriales sin registro, sin clave y
sin cuota de uso.

La aplicación se distribuye como PWA instalable, lo que exige un manifiesto de aplicación web que
declare nombre, iconos, ámbito y modo de presentación [41], y un *service worker* que se encargue
del arranque de la carcasa —el armazón de la aplicación, o *app shell*, que consiste en el
documento HTML, los estilos, el paquete de JavaScript y los iconos, es decir, todo lo que no son
datos—. Es la vía por la que una aplicación construida con tecnologías web se instala en el
dispositivo y se comporta como una nativa [42], sin el coste de mantener una aplicación nativa para
Android y otra para iOS, cada una con su cadena de construcción y su revisión de tienda. Esta
decisión enlaza además con el mismo origen que describe el apartado 4.1, porque las interfaces del
*service worker* solo están disponibles en contexto seguro [34], de modo que HTTPS no es una buena
práctica añadida sino un requisito de instalabilidad.

Tener un *service worker* obliga además a decidir qué se sirve desde una caché, y el criterio a
seguir no es la frecuencia con que cambia cada tipo de recurso, sino el daño que hace servirlo
caducado. Por ejemplo, la carcasa se precachea entera porque un *build* es inmutable, mientras que
los datos no. El catálogo de puntos se actualiza por lotes, con una cadencia de días, no de horas,
así que servirlo con *stale-while-revalidate* [43] cambia unas horas de desfase por un mapa
inmediato que se refresca por detrás; los precios siguen al PVPC hora a hora, y ahí una caché
serviría un dato caducado como si fuera el actual, de modo que se piden siempre a la red.

## El contrato entre las dos mitades y la cadena de comprobaciones

Los tipos con los que el *frontend* habla con la API no se escriben a mano, sino que se generan.
FastAPI deriva el esquema OpenAPI [44] de los modelos Pydantic, un *script* de `backend/scripts/`
lo exporta a un `openapi.json` versionado y de ese fichero se regenera el tipado del cliente. Ambos
ficheros —el esquema y los tipos— se guardan en el repositorio.

Eso permite comprobar automáticamente los dos eslabones de la cadena. Por un lado, se regenera el
esquema desde el código para contrastarlo con el fichero guardado; por otro, se regenera el tipado
del cliente a partir de ese esquema, para comprobar que tampoco se ha quedado atrás. En cualquiera
de los dos casos, la construcción se detiene. Un contrato desincronizado falla así en el equipo de
quien lo ha cambiado, y no en el navegador de quien usa la aplicación. La alternativa habitual,
generar el tipado contra un servidor levantado, dejaría ese paso en manos de quien se acuerde de
ejecutarlo, sin rastro en el repositorio con el que contrastarlo.

El contrato escrito en el repositorio sirve además a quien no ha escrito el servidor, ya se trate
de otra persona o de un asistente de programación, como Codex o Claude Code. La forma de cada
respuesta no hay que deducirla leyendo los *routers*, porque está declarada, y el compilador
rechaza cualquier llamada que no se ajuste a ella.

> **[FIGURA 4.3]** — *Generación y verificación del contrato de la API.*

Generar el contrato y comprobarlo automáticamente responde a un principio que ordena también otras
decisiones del capítulo, y es que la regla que no se puede comprobar de forma automática acaba
incumpliéndose. De ahí que las propiedades que el sistema debe mantener no se confíen a una guía de
estilo, sino a comprobaciones que rompen la construcción cuando se violan. Trasladar así la
verificación de una persona a una herramienta es una decisión de arquitectura y no de proceso,
porque determina qué propiedades del sistema pueden darse por ciertas sin revisarlas a mano.

Esas comprobaciones actúan en tres momentos. Antes de cada *commit* se ejecuta lo que depende solo
de los ficheros preparados —formato, reglas de estilo y búsqueda de secretos—; antes de cada envío,
lo que exige mirar el proyecto entero, desde el tipado y las pruebas hasta la coincidencia del
contrato con el código; y la integración continua lo repite todo sobre la rama protegida, donde
ningún cambio entra sin tenerlo en verde. La duplicidad es deliberada, porque el *hook* local se
puede omitir y la comprobación remota no. Solo dos trabajos quedan exclusivamente en el lado
remoto, porque tardan demasiado para ejecutarlos en cada envío: la construcción de las imágenes de
contenedor y el rastreo de secretos sobre todo el historial, que en local se limita a lo que está a
punto de entrar.

Ese reparto responde a un principio conocido como desplazamiento a la izquierda [45], según el cual
cuanto más tarde se detecta un defecto más cuesta corregirlo. De ahí que cada comprobación se sitúe
en el momento más temprano en que puede ejecutarse con sentido, y que la detección de secretos
ocupe el extremo de esa escala, porque una clave que llega al repositorio queda en el historial,
aunque después se borre del código.

## Entorno de desarrollo

Las herramientas específicas de cada mitad se han nombrado en los dos apartados anteriores,
mientras que las que se aprecian en la siguiente tabla son transversales.

| Herramienta | Uso en el proyecto | Descripción |
| --- | --- | --- |
| Zed | Escritura de código en las dos mitades | Editor de código |
| Claude | Asistencia en la escritura y revisión de código | Agente de código |
| Git | Control de versiones e historial del trabajo | Sistema de control de versiones distribuido |
| GitHub | Alojamiento del repositorio, revisión por *pull request* e integración continua con Actions | Plataforma de alojamiento y automatización |
| just | Ejecución de las tareas repetidas del proyecto | Ejecutor de comandos declarados en un fichero |
| lefthook | Ejecución de las comprobaciones antes de cada *commit* | Gestor de *hooks* de Git |
| DBeaver | Consulta e inspección de la base de datos | Cliente gráfico de bases de datos |
| Docker Compose | Levantado de PostgreSQL en desarrollo y del *stack* completo en producción | Orquestador de contenedores declarado en un fichero |

**Tabla 4.1.** Herramientas transversales del entorno de desarrollo.

En desarrollo solo PostgreSQL corre en contenedor y el resto se ejecuta de forma nativa, por dos
razones. La primera es práctica: con el código dentro del contenedor, cada dependencia que se añade
obliga a reconstruir la imagen para que el intérprete la vea, y en un proyecto que empieza eso
ocurre a diario. La segunda es que se crearía un segundo entorno paralelo al de referencia, que es
donde actúa la cadena de comprobaciones del apartado anterior, y ambos podrían divergir justamente
en las dependencias instaladas. El servidor de Vite hace de proxy de `/api/*` hacia el *backend*,
de modo que el mismo origen se conserva mientras se programa en lugar de simularse y un fallo de
cookies entre orígenes no puede aparecer solo en producción.
