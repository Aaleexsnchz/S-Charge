# 11. Validación y resultados

## Estrategia de pruebas

La batería del backend son **134 pruebas** en veintitrés módulos que reproducen la estructura de
`app/`, en tres niveles que se distinguen por lo que necesitan para correr.

Las **pruebas de servicio no tocan la base de datos**, y pueden no tocarla porque la lógica de
negocio no importa el framework: la simulación de recarga y la cascada de precio son funciones
sobre objetos de dominio, de modo que esa separación —descrita en el capítulo 4— convierte su
verificación en aritmética comprobable sin arrancar nada: una prueba que fija el codo del *taper*
al 80 % de estado de carga y comprueba la energía resultante falla por una sola razón.

Las **pruebas de ruta sí usan una base de datos real**, dentro de una transacción que se deshace
al terminar. Una base de datos falsa en memoria habría verificado un motor que producción no
ejecuta, y son justamente las restricciones de integridad y los `upsert` lo que interesa
comprobar.

Las **APIs externas se simulan en el transporte**, no en el cliente que las envuelve: se sustituye
la capa HTTP y se devuelven respuestas grabadas, con lo que el código bajo prueba es el cliente
entero, con su gestión de errores, su paginación y su tratamiento de los `504`. Ninguna prueba
llama de verdad a REVE ni a REE en integración continua, y no por higiene: el presupuesto de REVE
es de 5 peticiones/hora, y una batería que lo consumiera dejaría sin cuota al ETL.

La prueba que mejor resume el criterio es la que **deriva la lista de rutas del propio esquema de
la aplicación**. Lee `app.openapi()`, se queda con todo lo que empieza por `/api` y no cae bajo
los dos prefijos deliberadamente públicos —`/api/health` y `/api/auth/`—, y exige **401** en cada
método de cada ruta. Un router montado sin la dependencia de autenticación no pasa desapercibido:
hace fallar este módulo en lugar de llegar a producción. Enumerar las rutas a mano habría sido
peor por la forma de su fallo, no por su coste: una lista escrita envejece en silencio, porque una
ruta nueva simplemente no está en ella y nadie recibe aviso, mientras que la derivada crece sola.
El módulo lleva dos guardas propias: una comprueba que el inventario no está vacío, porque una
errata en el filtro de prefijos dejaría la batería probando nada mientras sigue en verde; la otra
recorre el camino de credenciales completo —alta, verificación, sesión— y exige un **200**, porque
sin ella la batería pasaría igual si la puerta rechazara a todo el mundo.

La contrapartida hay que decirla entera. **La cobertura del frontend es mínima**: 27 pruebas de
Vitest concentradas en un solo módulo —el que traduce los códigos de error de la API a la copia en
español—, y el resto de la interfaz se verifica mirándola. Ninguna pantalla tiene prueba propia. Y
**la cobertura del backend ni se mide ni la exige la integración continua**: el objetivo de ≥70 %
sobre `services/` está formulado para la fase de endurecimiento y hoy no es más que eso.

## La cadena de comprobaciones como validación continua

Qué se comprueba al hacer *commit* y qué al hacer *push* lo decide el tiempo: en el commit corren
el linter y el formateador sobre los ficheros preparados; al empujar corre todo lo demás —tipos,
las dos baterías y el *build* del frontend—. La medida que hizo viable esa segunda mitad es que
tarda **8 segundos de reloj frente a unos 29 de CPU**, porque los trabajos corren en paralelo y el
coste es el del más lento y no la suma. Con ese margen no hizo falta sacrificar ninguna
comprobación. A eso se suma el contrato de API versionado: la integración continua lo regenera y
falla si difiere, con lo que una divergencia
entre backend y frontend se manifiesta como un fallo de CI y no como un error en ejecución. El
detalle de la cadena de entrega está en el capítulo 8.

## Rendimiento medido

| Página | Rendimiento | Accesibilidad | Buenas prácticas | SEO |
| --- | --- | --- | --- | --- |
| `/login` | 94 | 98 | 96 | 82 |
| `/map` | **31** | 100 | 100 | 82 |

**Tabla 11.1.** Auditoría Lighthouse del 13 de junio de 2026 sobre el *build* de producción con
el preset móvil.

El 31 de `/map` no se esconde porque explicarlo vale más que maquillarlo. La causa dominante no es
el código de la aplicación sino la pantalla: el motor de mapas ha de descargarse, compilar su
estilo y completar el primer pintado WebGL antes de que haya nada visible, y sobre él se cargan
~13.700 puntos en una sola fuente. Reducir el payload del mapa —de 772 a 503 KB comprimidos, un
35 % menos— dejó FCP en 3,0 s, LCP en 4,5 s y Speed Index en 3,4 s. Las palancas que quedan están
identificadas y ninguna aplicada: caché del *service worker* sobre la respuesta del catálogo,
carga por *viewport* con un `bbox` en lugar de España entera, y la migración del frontend, que
elimina el CSS que hoy se inyecta en cada render.

Esta medición es **deliberadamente la línea base** contra la que se comparará esa migración, y por
eso se registró antes de tocar nada. El compromiso adquirido es que el resultado se publique sea
cual sea: si la mejora resulta marginal, ese también es un hallazgo.

> **[FIGURA 11.1]** — *Línea base de rendimiento y su comparación pendiente.* Gráfico de barras
> agrupadas con las cuatro categorías de Lighthouse en el eje horizontal y la puntuación 0-100 en
> el vertical. Dos series por categoría: `/login` y `/map`, con los valores de la tabla 11.1. A la
> derecha, un bloque de barras vacías con contorno discontinuo rotulado **«tras la migración del
> frontend — pendiente de medir»**, para que la figura muestre que la comparación está
> comprometida y aún no cerrada.
> **Cómo obtenerla:** diagrama a dibujar a partir de la tabla 11.1; la mitad derecha se rellena
> con la segunda auditoría cuando exista.

> **PENDIENTE:** repetir la auditoría Lighthouse (mismo método: *build* de producción, preset
> móvil, `/map` y una pantalla de formulario) al terminar la migración del frontend, y sustituir
> la mitad derecha de la figura 11.1 y el texto de este apartado por la comparación real, incluido
> el tamaño del *bundle* antes y después.

## Validación funcional en dispositivo real

La instalación como aplicación, la ventana propia sin barra de navegador, el mapa y la
geolocalización se probaron en un iPhone y un Android físicos, no en un emulador. La distinción
pesa aquí porque el usuario está de pie junto a un poste de recarga, con una mano y con la
cobertura que haya. Un emulador no reproduce el diálogo de permisos que el navegador del sistema
presenta para la geolocalización —un permiso que la especificación exige de forma expresa y
recomienda limitar a una sola sesión [46]—, ni el criterio con que cada plataforma
decide ofrecer la instalación [33], ni el coste del primer pintado WebGL sobre una GPU
móvil. Lo que un emulador valida es el diseño responsivo.

> **[FIGURA 11.2]** — *La aplicación instalada en un teléfono real.* Dos capturas juntas tomadas
> en un móvil físico: a la izquierda, la pantalla de inicio del sistema con el icono de s-charge
> entre las demás aplicaciones; a la derecha, `/map` abierto **desde ese icono**, en ventana
> propia y sin barra de direcciones, con el punto azul de la geolocalización visible y un
> *cluster* urbano en pantalla. La ausencia de barra de navegador es el detalle que la figura
> tiene que demostrar.
> **Cómo obtenerla:** capturas de pantalla en un iPhone o Android real, con la aplicación
> instalada desde `https://s-charge.app`, a la anchura nativa del dispositivo.

## Verificación del despliegue

| Comprobación | Resultado observado | Estado |
| --- | --- | --- |
| HTTPS con redirección desde HTTP y HSTS | `max-age=31536000; includeSubDomains` | Correcto |
| Juego de cabeceras de seguridad | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Permitted-Cross-Domain-Policies: none`, `Cross-Origin-Opener-Policy` y `Cross-Origin-Resource-Policy` a `same-origin` | Correcto |
| `Permissions-Policy` | `geolocation=(self)`; el resto de capacidades del navegador denegadas | Correcto |
| `Content-Security-Policy` | Solo `frame-ancestors 'none'` | Parcial, declarado |
| Cabecera `Server` | Suprimida | Correcto |
| `GET /api/points` sin sesión | `401` | Correcto |
| Documentación interactiva de la API | Desactivada en producción | Correcto |
| Puerto de Postgres en el host | No publicado; accesible solo en la red interna | Correcto |

**Tabla 11.2.** Comprobaciones ejecutadas contra el servidor de producción real. La política de
contenido incompleta es una carencia conocida, no un descuido: el motor de estilos actual inyecta
etiquetas `<style>` en línea, y una política estricta obligaría a permitirlas hasta anularse a sí
misma [42].

## Resultados del sistema como producto

El catálogo español está espejado por completo: **142 operadores, ~13.700 puntos de carga,
~42.000 EVSEs y ~47.000 conectores** en Postgres, sembrados en **~12 días de ticks desatendidos**
bajo un límite de 5 peticiones/hora. Sobre él hay un histórico de precios PVPC desde el 1 de enero
de 2026 y **31 modelos de vehículo** con capacidad de batería y potencia máxima en corriente
alterna y continua, que es lo que permite a la simulación devolver un número y no una estimación
genérica. La aplicación está desplegada, instalable y accesible en
**`https://s-charge.app`**.

## Lo que no se ha validado

**No hay pruebas de carga.** No existe medición de dónde satura esta pila: ni conexiones
concurrentes, ni coste de la consulta del mapa, ni la contención de memoria entre la construcción
de las imágenes y Postgres durante un despliegue. El capítulo 8 argumenta por dónde se rompe
primero un solo servidor; nada lo ha medido.

**No hay cobertura exigida en integración continua**, de modo que «hay 134 pruebas» no garantiza
nada sobre qué proporción del código ejercitan.

**No hay pruebas automatizadas de extremo a extremo del cliente.** Toda la validación de interfaz
es manual, y por tanto irrepetible y dependiente de que alguien se acuerde de mirar la misma
pantalla dos veces.

**No hay usuarios reales** más allá del autor y de pruebas puntuales en dispositivos ajenos: nada
de lo que se afirma sobre la utilidad del producto procede de observar a alguien usándolo.

**La disponibilidad de los puntos no se valida porque no se modela.** No falta una prueba: falta
un dato que no existe en el origen. REVE no expone un flujo de estado permanente, los puntos se
muestran disponibles por defecto y así se declara en la interfaz.

> **PENDIENTE:** medir el punto de saturación de la pila (peticiones concurrentes sobre
> `/api/points/map` y sobre `/api/simulate` hasta degradación) y registrar aquí el número de
> usuarios concurrentes que soporta un servidor de 2 vCPU y 4 GB, que es la cifra que el capítulo
> 10 argumenta sin medir.
