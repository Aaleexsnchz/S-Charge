---
status: borrador (redacción de la memoria, nivel conceptual)
---

# Migración del stack

Este capítulo documenta un conjunto de **decisiones técnicas revisadas** a mitad del proyecto:
el frontend pasa de MUI a Tailwind + shadcn/ui, la base de datos a PostgreSQL 18, el backend a
Python 3.13, el entorno de desarrollo abandona los contenedores para la aplicación, y la cadena
de herramientas cambia de gestor de hooks y añade actualización automática de dependencias.

Interesa a la memoria no por el resultado técnico de cada cambio, sino por el criterio común
que los ordena. Una decisión de arquitectura no es correcta o incorrecta en abstracto: lo es
respecto a la información disponible y al peso relativo de los criterios en ese momento. Varias
de las decisiones originales fueron acertadas cuando se tomaron **y aun así se sustituyen**,
porque el criterio dominante cambió. Documentarlo es más honesto —y más útil— que presentar el
stack final como si hubiera sido evidente desde el principio.

## El criterio que ordena todos los cambios

Al plantear estas migraciones apareció una distinción más útil que la habitual "cuánto código
hay que tocar": **si la migración la verifica una herramienta o la verifica una persona**.

- Subir de versión el intérprete, cambiar de versión mayor la base de datos, sustituir el
  gestor de hooks o generar tipos desde el esquema de la API son cambios que el *type checker*,
  la batería de tests y el build confirman o rechazan. El número de ficheros afectados es casi
  irrelevante: si CI pasa, la migración es correcta.
- Reescribir diez pantallas de interfaz no lo verifica ninguna herramienta. El compilador
  confirma que el código compila; que la aplicación se siga viendo bien en un móvil de 360 px
  solo lo confirma una persona mirándola.

Ese es el coste real de una migración, y es el que decide cuáles se hacen sin apenas
deliberación y cuál exige una fase propia con criterio de aceptación explícito.

---

## 1. Frontend: de MUI a Tailwind + shadcn/ui

### El punto de partida y por qué fue correcto

La primera decisión fue construir sobre [MUI](https://mui.com) con Emotion como motor de
estilos. El razonamiento era de asignación de esfuerzo: un TFM de un solo desarrollador con
calendario fijo necesita controles de formulario, diálogos, hojas inferiores, navegación,
snackbars y, sobre todo, *focus rings* accesibles y atributos ARIA correctos **sin
escribirlos**. La aplicación existe para demostrar el producto, no para ser un ejercicio de
CSS. Esa decisión permitió tener seis pantallas de autenticación, un mapa y una vista de
detalle funcionando en semanas.

Conviene afirmarlo sin ambigüedad: **MUI no falló**. Lo que cambió no es la calidad de la
herramienta, sino el peso relativo de los criterios.

### Qué cambia el criterio

**El coste en tiempo de ejecución del CSS-in-JS.** Emotion serializa e inyecta estilos *en
tiempo de ejecución*, en cada render: el navegador descarga el motor de estilos, lo analiza y
lo ejecuta antes de pintar. Tailwind resuelve lo mismo **en tiempo de compilación**, dejando
una hoja de estilos estática y ningún motor en el bundle. La aplicación tiene un problema de
rendimiento medido: la auditoría Lighthouse de la fase 2 dio **31 en Performance** en `/map`
bajo *throttling* móvil. La causa dominante es el motor de mapas con ~13.700 puntos, pero el
coste del CSS-in-JS es aditivo y evitable.

**Propiedad de los componentes.** shadcn/ui no es una dependencia: **copia el código fuente de
cada componente al repositorio**. Adaptar el sistema de diseño *s-charge* pasa de sobrescribir
estilos desde fuera —con la prop `sx` y las claves de tema de la librería— a editar
directamente el componente. El proyecto acumula 116 usos de `sx`, la señal habitual de que el
sistema de diseño y la librería tiran en direcciones distintas.

**Tipado del enrutado.** TanStack Router valida en tiempo de compilación los parámetros de ruta
y los *search params*: convierte en error de build una familia de fallos que hoy solo aparecen
en ejecución, y hace viable mover estado de interfaz —los filtros del mapa— a la URL sin
escribir validación a mano.

**Una capa de formularios que aún no existe.** El asistente de alta de puntos privados será el
primer formulario real de la aplicación. Adoptar TanStack Form con esquemas **Zod** significa
que una sola definición valida en cliente y refleja el contrato que el backend valida con
Pydantic. Es una adición, no una sustitución.

**Coherencia de familia.** Router, Query y Form comparten convenciones de tipado. La aplicación
ya usa TanStack Query, de modo que la migración reduce el número de modelos mentales.

### El argumento decisivo: el momento

Ninguna razón anterior justifica por sí sola reescribir una interfaz que funciona. Lo que
decide es **cuándo**. El coste de migrar crece con cada fase: hoy son unas diez pantallas;
después de puntos privados, optimizador, reservas y monedero serían del orden de dieciocho. Y
construir ocho pantallas nuevas sobre una base que se pretende abandonar es el desperdicio
real, no la migración. La decisión es binaria: **o ahora, o nunca**. Se hace ahora.

**El sistema de diseño no se rediseña.** Los tokens de la fase 4 —paleta, superficies, radios,
tipografía con cifras monoespaciadas— se re-expresan como tokens de Tailwind. Cambia la
implementación, no la apariencia; el criterio de aceptación es que no haya regresiones
visuales.

### Qué se pierde

La migración devuelve trabajo que MUI daba hecho: la **navegación inferior** pasa a ser un
componente propio (del orden de treinta líneas); los **snackbars** cambian de notistack a
sonner; los **gráficos** dejan MUI X Charts por la capa de shadcn —sin coste real todavía,
ninguna gráfica se alimenta aún de datos reales—; y la **accesibilidad** deja de venir por
defecto de una librería madura: shadcn se apoya en primitivas *headless* que la cubren, pero la
responsabilidad se acerca al código propio.

Y el riesgo que ninguna herramienta verifica: **la regresión visual**. Es la razón de hacerlo
en una fase propia y no de forma incremental mientras se construyen funcionalidades.

### Alternativas consideradas

- **No migrar.** Coste cero e interfaz que funciona. Se descarta por el argumento del momento:
  no migrar hoy equivale a decidir no migrar nunca.
- **Seguir en MUI con un motor de estilos sin tiempo de ejecución (Pigment CSS).** Resolvería
  el coste de runtime conservando la API de componentes. Se descarta porque la propia
  documentación de MUI describe Pigment CSS como **alfa temprana**, y porque no resuelve la
  propiedad de los componentes, el tipado de rutas ni los formularios. Apostar la interfaz de
  un TFM con entrega fija a una API en alfa es un riesgo mal pagado.
- **Migrar solo los estilos y conservar React Router.** Los ficheros de enrutado se tocan
  igualmente al reescribir las pantallas, así que el ahorro es menor de lo que parece y se
  pierde el tipado de rutas.
- **Migración incremental, pantalla a pantalla.** La opción aparentemente prudente y la peor:
  obliga a mantener dos sistemas de estilos en una base de ~3.200 líneas durante semanas, con
  dos maneras de hacer cada cosa y el doble de superficie de revisión.

---

## 2. Base de datos: PostgreSQL 17 → 18

Aquí no se sustituye una herramienta: se sube de versión mayor la misma. Lo que lo justifica es
que **tres novedades de la 18 se usan directamente en este proyecto**, no una mejora genérica
de rendimiento.

**Claves primarias temporales (`WITHOUT OVERLAPS`).** La fase de reservas debe garantizar que
dos reservas no solapen sobre el mismo conector. Comprobarlo en la aplicación —consultar si hay
solape y después insertar— arrastra una condición de carrera clásica: entre la consulta y la
inserción, otra transacción puede insertar una reserva que solape. La solución correcta es que
la restricción viva en la base de datos, y PostgreSQL 18 permite declararla como parte de la
clave primaria:

```sql
CREATE EXTENSION btree_gist;
CREATE TABLE bookings (
  connector_id uuid,
  during       tstzrange,
  PRIMARY KEY (connector_id, during WITHOUT OVERLAPS)
);
```

Comprobado sobre 18.4: la segunda reserva solapada se rechaza con *conflicting key value
violates exclusion constraint*. La detección de conflictos deja de ser código de aplicación y
pasa a ser una invariante del esquema, imposible de saltarse por concurrencia o por un camino
de código que olvide comprobarla. Para una funcionalidad cuyo valor depende de que la reserva
signifique algo, la diferencia no es de comodidad sino de corrección.

**`uuidv7()`.** Las claves primarias del proyecto son UUID. La versión 4 es aleatoria, de modo
que cada inserción cae en una hoja arbitraria del índice B-tree, fragmentándolo y perjudicando
la localidad de caché —efecto que se nota justamente en tablas grandes como el catálogo
sembrado—. UUIDv7 antepone una marca de tiempo, con lo que las claves nuevas se insertan de
forma aproximadamente ordenada, conservando el resto de propiedades del UUID: unicidad sin
coordinación y opacidad frente a un entero autoincremental, que revela volumen. PostgreSQL 18
lo genera de forma nativa, sin extensión ni generación en el cliente.

**Entrada/salida asíncrona.** La 18 introduce un subsistema de E/S asíncrona (`io_method`, con
soporte de `io_uring` en Linux) que beneficia recorridos secuenciales, *bitmap heap scans* y
`VACUUM` — el perfil exacto de las consultas del mapa y de los procesos ETL sobre decenas de
miles de filas. Es la menos específica de las tres razones y no se defiende con números
propios: se declara como razonable, no como medida.

**El coste operativo, que es real.** Un salto de versión mayor **no es cambiar la etiqueta de
la imagen**: el formato del directorio de datos cambia, y un volumen de la 17 bajo una imagen
18 se niega a arrancar. Como la base de datos contiene la siembra de REVE —doce días de trabajo
bajo el límite de cinco peticiones por hora— el procedimiento es volcar con la imagen antigua,
destruir el volumen, arrancar la nueva y restaurar. Queda documentado como parte del
procedimiento y no como nota al pie, porque es el punto exacto donde este cambio podría costar
datos irrecuperables.

---

## 3. Backend: Python 3.12 → 3.13

Cambio menor y verificable por CI. La razón no es de rendimiento sino de **ecosistema**: la
fase de asistente de IA depende de SDKs cuyo soporte se ancla a las versiones que la comunidad
ya ha adoptado, y 3.13 lo está de forma general mientras 3.14 aún arrastra desfase en parte de
ese ecosistema. Se comprobó que el conjunto completo de dependencias resuelve, instala e
importa tanto en 3.13 como en 3.14 —incluida la extensión en C de `asyncpg`—, de modo que la
elección es deliberada y no una limitación técnica: se prefiere la versión con más soporte de
terceros sobre la más reciente, porque aquí el beneficio de la más reciente es marginal y el
riesgo para la fase de IA no lo es.

---

## 4. Entorno de desarrollo: contenedores solo para la base de datos

El proyecto ejecutaba en Docker las tres piezas —base de datos, backend y frontend— con recarga
en caliente mediante *bind mounts*. Pasa a ejecutar **solo PostgreSQL en contenedor**; backend
y frontend corren de forma nativa.

El argumento decisivo no es la velocidad, aunque mejore: es que **ya existía una cadena de
herramientas nativa y era la autoritativa**. Los hooks de git, el *type checker*, el linter y
los tests se ejecutan en el host, y son los que deciden si un commit entra y si CI pasa. El
contenedor de desarrollo era un segundo entorno paralelo al que realmente gobierna el proyecto,
con la clase de fallo asociada: *funciona en el contenedor, falla en el hook*. Colapsar los dos
en uno elimina esa categoría entera.

La paridad con producción, que era el argumento a favor de los contenedores en desarrollo, se
conserva donde importa: producción sigue ejecutando el stack completo en contenedores, ese
mismo stack se levanta en local para una prueba de humo, y CI construye las tres imágenes de
producción en cada *pull request*, de modo que un `Dockerfile` roto falla antes del despliegue.
La paridad además nunca fue total: las imágenes de desarrollo usaban etapas de construcción
distintas de las de producción.

---

## 5. Cadena de herramientas

**De pre-commit a lefthook.** Todos los hooks del proyecto estaban declarados como órdenes del
sistema sin paso de ficheros: se pagaba el arranque del entorno Python de pre-commit sin usar
aquello que lo justifica —su gestión de entornos multi-lenguaje— y se analizaba el árbol
completo en cada commit en lugar de los ficheros preparados. lefthook se instala como
dependencia de desarrollo del propio proyecto, procesa en paralelo solo los ficheros
preparados, puede corregirlos y volver a añadirlos al índice, y añade un hook de *pre-push* que
replica exactamente lo que ejecuta CI. Esto último sustituye una instrucción escrita en la
documentación —"acuérdate de ejecutar la batería completa antes de subir"— por algo que no se
puede olvidar. Con una condición: el escaneo de secretos deja de ser obligatorio en local, así
que pasa a ser un trabajo de CI sobre el historial completo; de lo contrario el cambio
eliminaría una defensa sin sustituirla.

**Renovate.** Las incidencias de mantenimiento acumuladas durante la fase de despliegue —un
*runtime* de Actions obsoleto, dos versiones distintas del gestor de paquetes entre CI y la
imagen, el gestor de Python fijado a versiones distintas en dos sitios— son exactamente la
clase de deriva que un bot de dependencias plantea como *pull requests* revisables. Se
configura con agrupación y periodicidad semanal para que el ruido sea asumible en un proyecto
de una persona, y **sin fusión automática**, porque fusionar contra la rama principal despliega
a producción.

**Esquema OpenAPI versionado.** La generación de tipos del frontend exigía tener el backend en
ejecución, lo que impide que CI la verifique. Exportando el esquema a un fichero versionado, CI
puede regenerarlo y fallar si difiere: un cambio de contrato en el backend rompe la integración
continua en lugar de romper el frontend en ejecución. Es el mismo principio que gobierna el
resto del capítulo —mover la verificación de una persona a una herramienta— aplicado al
contrato entre las dos mitades del sistema.

---

## Evaluación

Los cambios verificables por herramientas se dan por buenos cuando CI pasa; no hay nada que
medir. El único que exige medición es el frontend, y se mide: antes del primer cambio y al
terminar se registran **Lighthouse en `/map` y en una pantalla de formulario, y el tamaño del
bundle**, con el mismo método que la auditoría de la fase 2 (build de producción, preset
móvil).

El resultado se publica **sea cual sea**. Si la mejora resulta marginal, ese también es un
hallazgo publicable, y encaja con el criterio de honestidad que sigue el resto de la memoria:
es el mismo razonamiento por el que la disponibilidad de los puntos no se simula (véase
[modelo-de-datos.md](modelo-de-datos.md)).

## Lectura para la defensa

La pregunta previsible es *"¿por qué cambiaste de herramientas a mitad del proyecto?"*. La
respuesta es que las decisiones iniciales optimizaban arranque —tener producto funcionando
cuanto antes—, que era el criterio correcto con cero pantallas construidas, y que una vez
construida la base el criterio dominante pasó a ser el coste marginal de cada pantalla nueva,
el rendimiento en móvil y la solidez de las invariantes de datos. Ninguna fue un error
corregido: fueron decisiones con fecha de caducidad, sustituidas cuando caducaron y en el punto
del calendario donde migrar cuesta menos.
