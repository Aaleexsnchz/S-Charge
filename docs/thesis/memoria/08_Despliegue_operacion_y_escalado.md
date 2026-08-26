# 10. Despliegue, operación y escalado

## Un servidor, una pila, un origen

La aplicación se sirve desde el 4 de agosto de 2026 en `https://s-charge.app`. Debajo hay un
único servidor virtual alquilado en Hetzner —2 vCPU, 4 GB de memoria, x86-64, Ubuntu 26.04 LTS,
región de la Unión Europea— que ejecuta la pila de Docker Compose definida en el repositorio:
PostgreSQL 18, el backend FastAPI, el *build* estático del frontend servido por nginx, Caddy como
proxy inverso y un contenedor `scheduler` para los procesos ETL. Ni balanceador, ni segundo nodo,
ni servicio gestionado. Solo Caddy publica puertos —80, 443 y 443/UDP—; los demás contenedores se
hablan por la red interna, y que Postgres no publique ninguno es lo único que lo mantiene fuera
de internet.

Caddy termina TLS con certificados de Let's Encrypt que obtiene y renueva por sí solo, y reparte
por ruta: `/api/*` al backend, el resto a nginx. El mismo origen que el capítulo 4 identifica
como propiedad ordenadora del diseño es aquí infraestructura, no código: dos bloques de
configuración mantienen la sesión en una cookie de origen propio y suprimen la superficie CORS.

El dominio `.app` está en la lista de precarga HSTS, de modo que el navegador rechaza HTTP contra
ese origen al nivel del dominio de primer nivel: la exigencia de HTTPS queda cableada en el
cliente en vez de depender de una cabecera del servidor. La contrapartida merece decirse: el
origen **nunca** puede servirse por HTTP, ni siquiera para depurar, y un fallo de certificado no
degrada el sitio, lo deja inaccesible. HTTPS era obligatorio de todas formas: las interfaces del
*service worker* exigen contexto seguro, igual que la geolocalización [34].

El contenedor `scheduler` está construido y desplegado, pero **no arranca**: vive tras un perfil
de Compose que un `up -d` omite. El perfil es un seguro, no una comodidad —un tick desatendido
mueve la marca de agua del ETL (capítulo 5), y hoy interesa inspeccionarla antes de que eso
ocurra—. Con una bandera de despliegue, olvidarla arrancaría los procesos; con un perfil, los
deja parados.

> **[FIGURA 10.1]** — *La pila de producción.* Diagrama de cajas dentro de un marco rotulado
> **VPS · 2 vCPU / 4 GB · Ubuntu 26.04 · UE**. Fuera del marco, arriba, la caja **Navegador
> (móvil)** con una flecha rotulada `HTTPS 443` que entra al marco y llega a la caja **Caddy**;
> junto a esa flecha, la etiqueta **únicos puertos publicados: 80 / 443 / 443·UDP**. De Caddy
> salen dos flechas rotuladas por ruta: `/api/*` → **backend (FastAPI, usuario no root)** y `/*`
> → **frontend (nginx sirviendo `dist/`)**. Del backend, una flecha a **PostgreSQL 18**, y bajo
> esa caja el rótulo **sin entrada `ports:` — solo alcanzable por la red interna**. A un lado,
> con borde discontinuo y la etiqueta **detenido tras un perfil de Compose**, la caja
> **scheduler (supercronic)**, con una flecha discontinua hacia PostgreSQL y dos flechas
> salientes fuera del marco hacia **API de REVE** y **API de REE**. Abajo, tres cilindros de
> volumen: `postgres_data`, `caddy_data`, `caddy_config`. A la izquierda del marco, una caja
> pequeña **ufw: 22 / 80 / 443** con una nota al pie: *no filtra los puertos publicados por
> Docker*. Lo que la figura debe dejar ver de un vistazo: que solo un proceso está expuesto y que
> la base de datos no tiene camino desde fuera.
> **Cómo obtenerla:** diagrama a dibujar en draw.io o Mermaid a partir de
> `docker-compose.prod.yml` y el `Caddyfile`.

## Por qué un servidor propio y no otra cosa

Las restricciones son cuatro: uno o dos usuarios, gasto mínimo, una URL HTTPS real que se pueda
abrir en un móvil, y un proceso periódico que siga corriendo con el portátil cerrado. Las
candidatas caen en cuatro grupos, y el motivo del descarte dice más que la lista.

**Las que duermen o caducan.** El servicio web gratuito de Render se suspende por inactividad y
su base de datos expira a los noventa días; la capa gratuita de Supabase **pausa el proyecto**
tras una semana sin uso. Un demostrador permanente y un cron son justo lo que una instancia
dormida rompe: la primera visita pagaría el arranque en frío y el ETL no dispararía.

**Las que parten el origen.** Vercel para el frontend con el backend en otro sitio, o una CDN
estática delante de una API propia, reintroducen cookies entre sitios y configuración CORS a
cambio de una ventaja —caché en el borde— que a esta escala no se nota.

**Las que sobran.** Las grandes nubes y Kubernetes gestionado añaden facturación real y
sobrecarga de orquestación para uno o dos usuarios. La capa siempre gratuita de Google Cloud es
una instancia de 1 GB limitada a regiones de Estados Unidos: demasiado pequeña para construir
imágenes en el host, y sin localización de datos en la UE.

**Las que fallan por un detalle.** Los hosts ARM gratuitos son la opción de coste cero y quedan
bloqueados por un binario: el planificador usa supercronic, compilado solo para x86-64. Y un
subdominio gratuito de DuckDNS habría ahorrado el dominio, pero `duckdns.org` está en la Public
Suffix List, así que Google lo trata como dominio privado de primer nivel y exige verificación de
propiedad antes de aceptarlo en OAuth.

**Podman pierde por encaje, no por mérito.** Sin demonio y sin root por defecto, su postura de
seguridad es mejor en abstracto, pero `podman compose` delega en una implementación externa de
Compose y esta pila se apoya donde esa capa es más delgada: comprobaciones de salud, dependencias
condicionadas a que un servicio esté sano y construcción multietapa. El hueco que cerraría ya
está cerrado por otros medios: el backend corre sin privilegios y Postgres no publica puerto.

**El proxy de Cloudflare se rechaza por la credencial que exige**, no por el esfuerzo, que es
cosa de una hora. Al terminar TLS en el borde rompe el desafío ACME de Caddy y obliga a validar
por DNS, lo que significa **un token con permiso de edición de DNS guardado en el propio
servidor**. El radio de daño de ese secreto supera al del host que protegería: quien lo tenga
puede repuntar el dominio, emitir certificados válidos e interceptar tráfico, incluida la
respuesta de OAuth de Google. Añadir un secreto más peligroso para proteger un servidor que
publica un catálogo público es el intercambio equivocado.

## La cadena de entrega

Backend y frontend usan gestores de paquetes con fichero de bloqueo —uv y pnpm— fijados a la
**misma versión en CI y en la imagen de producción**. Esa deriva ocurrió de verdad durante la
fase de despliegue, y produce la avería más cara: la que solo aparece al construir la imagen.

El análisis estático se concentra en tres herramientas: Ruff para Python —linter y formateador en
el mismo binario—, Biome para TypeScript y CSS, y basedpyright para los tipos. Qué se comprueba
al hacer *commit* y qué al hacer *push* lo decide el tiempo: en el commit corren linter y
formateador **solo sobre los ficheros preparados**; el comprobador de tipos y las dos baterías de
tests son demasiado lentos para vivir entre teclear un mensaje y recuperar el prompt.

Un hook lento se acaba esquivando, y esquivarlo es justo lo que el proyecto prohíbe. La batería
completa del hook de *pre-push* —linter, formateador, comprobador de tipos, 134 tests de backend
contra una base de datos real, tests y *build* de frontend— tarda **8 segundos de reloj frente a
unos 29 de CPU**, porque los trabajos corren en paralelo y el coste es el del más lento, no la
suma. Con ese margen no hizo falta sacrificar ninguna comprobación. Y la orden manual equivalente
no reimplementa la lista: **ejecuta ese mismo hook**, así que no hay dos definiciones que puedan
divergir.

CI repite eso y añade lo que localmente no cabe: construye las **tres imágenes de producción** en
cada *pull request*, de modo que un `Dockerfile` roto falla en la revisión y no en el despliegue.
Se le suma el esquema OpenAPI versionado, que CI regenera y compara: un cambio de contrato rompe
la integración continua en vez de romper la aplicación en ejecución.

Ningún manifiesto guarda un número de versión: `git describe --tags` alimenta un argumento de
construcción que queda grabado en las imágenes y aflora en `/api/health`. Las etiquetas se ponen
**a mano** porque el número es una afirmación deliberada sobre el alcance —una menor marca una
fase entregada— y no un recuento. Por eso se descartó `release-please`, que deriva el salto de
los tipos de commit y responde a otra pregunta; su beneficio principal, sincronizar cadenas de
versión entre manifiestos, desaparece además cuando la versión viene de la etiqueta. **Todavía no
se ha etiquetado ninguna versión**, así que `/api/health` responde hoy con el hash del commit
desplegado.

Se despliega **al empujar una etiqueta, no al fusionar en `main`**: la fusión construye y prueba,
y nada más. Eso compra que publicar sea un acto deliberado, que varias fusiones se acumulen
detrás de una sola entrega y que producción no se mueva sola, cuando bajo despliegue por fusión
cualquier fusión altera el sitio en vivo, incluida la de la noche anterior a la defensa. A
cambio, «fusionado» ya no implica «en vivo» y olvidar la etiqueta pasa a ser un modo de fallo;
una ejecución manual del flujo despliega la rama principal para ver trabajo sin publicar en un
móvil real.

> **[FIGURA 10.2]** — *De un commit a producción.* Diagrama de flujo horizontal en cuatro
> bandas. Banda 1, **local**: `commit` → caja *ruff + biome sobre ficheros preparados + escaneo
> de secretos*; `push` → caja *pre-push: ruff, formato, basedpyright, pytest, biome, vitest,
> build*, rotulada **8 s de reloj / ~29 s de CPU, en paralelo**. Banda 2, **pull request**: caja
> *CI — las mismas comprobaciones + construcción de las tres imágenes de producción +
> `openapi.json` sin deriva + escaneo de secretos sobre todo el historial*, con la salida
> **fusión a `main`** y, junto a ella, destacada, la etiqueta **no despliega**. Banda 3,
> **entrega**: `git tag vX.Y.Z` → `push` → caja **CD (GitHub Actions)**, conectada por una flecha
> rotulada **SSH con clave dedicada** al servidor. Banda 4, dentro del servidor y en secuencia:
> `git checkout --detach` → *volcado previo a la migración* → `up -d --build` →
> `alembic upgrade head`. Añadir una flecha discontinua desde una caja **ejecución manual** hacia
> CD, rotulada **despliega `main`**.
> **Cómo obtenerla:** diagrama a dibujar en Mermaid (`flowchart LR`) a partir de `lefthook.yml`,
> `.github/workflows/ci.yml` y `cd.yml`.

## Operación

Un despliegue es una secuencia corta ejecutada por SSH: traer las etiquetas, situar el servidor
en el *ref* desplegado con un `HEAD` desacoplado —nunca sobre una rama que se mueve—, volcar la
base de datos, reconstruir los contenedores y migrar. Volver atrás es la misma operación apuntando
a la etiqueta anterior, y el volcado previo existe porque **el código retrocede y el esquema no**:
restaurarlo es la única forma de deshacer una migración.

La copia de seguridad periódica es otra cosa: un volcado lógico comprimido que sube a un bucket
externo, y del que solo viaja la mitad sin datos personales, porque se excluyen las filas de
cuentas. **Una cuenta la recrea su dueño en un minuto; el espejo de REVE cuesta unos 12 días de
ticks bajo el límite de 5 peticiones/hora.** Se protege lo que no se puede regenerar barato, y la
consecuencia se declara: perder el host pierde todas las cuentas, equilibrio que deja de ser
correcto en cuanto una cuenta lleve saldo detrás.

Para mirar la base de datos de producción no se abre un puerto, se abre un túnel SSH que publica
el `5432` remoto solo en la máquina del operador y mientras dura la conexión. Detrás hay una
trampa que mucha gente tiene sin saberlo: **`ufw` no protege los puertos que publica Docker.**
Docker inserta sus reglas DNAT antes de la cadena INPUT del cortafuegos, así que añadir una
entrada `ports:` expone el servicio a internet mientras `ufw status` sigue mostrando una política
impecable. Lo que mantiene privada esta base de datos no es el cortafuegos: es que su servicio no
tiene entrada `ports:`.

## Escalado, argumentado y no construido

Un solo servidor se rompe primero por sitios identificables. Las imágenes se construyen **en el
propio host**, que es la razón del suelo de 4 GB de memoria: un *build* de producción del
frontend compite por RAM con Postgres. De ahí sale una garantía más débil de lo que parece,
porque el artefacto que corre en producción no es el que CI probó, sino uno reconstruido desde el
mismo código. Cada despliegue es una interrupción, y no hay conmutación por error.

| Pieza | Dónde se rompe | Qué la sustituye |
| --- | --- | --- |
| Construcción en el host | Compite por memoria con Postgres; el artefacto desplegado no es el probado | Construir una vez en CI, publicar en un registro y que el servidor solo descargue un *digest* inmutable |
| Postgres autogestionado | Sin conmutación por error, parcheado manual, sin agrupación de conexiones | Instancia gestionada, PgBouncer delante y una réplica de lectura para el catálogo |
| Un solo nodo de aplicación | Cada despliegue y cada reinicio es una caída | Dos nodos tras un balanceador; la aplicación ya es sin estado |
| Copia lógica periódica | Ventana de pérdida de horas o días | Archivado continuo de WAL y recuperación a un punto en el tiempo |
| `docker compose logs` | No responde si el sistema va lento ni si un error llegó a un usuario | Trazas de error, métricas, registros agregados, sondas externas y alertas |

**Tabla 10.1.** Dónde falla primero el despliegue actual y qué pieza lo sustituye en cada escalón.

Lo que **no** aparece en esa escalera es orquestación de contenedores, y justificar su ausencia
es tanto resultado como describir cuándo entraría. Kubernetes resuelve planificar contenedores
sobre una flota: dónde cabe cada cosa, cómo reprogramarla cuando un nodo cae, cómo sostener un
número de réplicas. Con un nodo esas decisiones tienen respuesta trivial y la herramienta es todo
coste. El umbral no es un número de usuarios sino un cambio cualitativo: **cuando hay más
máquinas de las que una persona quiere gobernar a mano**.

Pasar de un nodo a varios impone dos disciplinas. La primera afecta a cada migración futura: con
despliegues progresivos conviven dos versiones del código contra la misma base de datos, así que
toda migración debe seguir el patrón **expandir y contraer** —añadir la columna anulable,
escribir en la vieja y en la nueva, rellenar hacia atrás y eliminar la vieja en una versión
posterior—. Hoy esa incompatibilidad dura los segundos que van de levantar los contenedores a
migrar; con varios nodos pasa a ser permanente. La segunda es la observabilidad, de la que hoy no
hay nada, aunque la base es mejor de lo que sugiere esa ausencia: el backend ya emite registros
estructurados en JSON y ya anota los eventos de seguridad, que es la parte difícil de añadir
después.

Y tres trampas propias de este sistema, que valen más que cualquier consejo general:

- **El planificador no se puede replicar.** Dos instancias disparan el refresco a la misma hora
  contra una API limitada a 5 peticiones/hora: el presupuesto se agota al instante y el ETL entra
  en un bucle permanente de rechazo. Varios hosts exigirían un planificador explícitamente no
  replicado, elección de líder o una cola con cerrojo distribuido.
- **El cursor del ETL tiene una carrera, alcanzable hoy sin escalar nada.** Cada tick lee,
  modifica y reescribe una fila por *endpoint*; dos ejecuciones simultáneas corrompen la marca de
  agua, y basta lanzar un refresco a mano mientras el cron dispara. Un cerrojo consultivo de
  PostgreSQL lo cierra: queda formulado, no implementado.
- **El límite de tasa en memoria se debilita al escalar.** El limitador guarda su estado en el
  proceso, así que N réplicas conceden N veces el límite pretendido: la protección se afloja justo
  cuando más tráfico hay.

## Costes de infraestructura

| Concepto | Coste | Nota |
| --- | --- | --- |
| Servidor (Hetzner, 2 vCPU / 4 GB, UE) | ~7-18 €/mes | Facturación por horas, sin permanencia |
| Dominio `s-charge.app` | ~10 €/año | Registrador a precio de coste, privacidad WHOIS incluida |
| Certificados TLS (Let's Encrypt) | 0 € | Emisión y renovación automáticas por Caddy |
| DNS | 0 € | Registro A en modo solo DNS, sin proxy |
| Integración y despliegue continuos | 0 € | Minutos gratuitos de GitHub Actions |
| Copia de seguridad externa (Backblaze B2) | 0 € | Volcados comprimidos, retención de los ocho más recientes |
| Correo transaccional y teselas del mapa | 0 € | Capa gratuita en ambos casos |

**Tabla 10.2.** Coste recurrente de la infraestructura. El presupuesto del proyecto y el modelo
económico se tratan en el capítulo 11.

## Carencias declaradas

**No hay entorno de preproducción**, así que las migraciones ven datos con forma de producción
por primera vez en producción. La opción completa —preproducción al fusionar, producción al
etiquetar— necesita un segundo entorno que aquí no existe.

**Los secretos son ficheros `.env` en disco, y no se rotan.** El paso proporcionado no es un
gestor de secretos —en un único servidor, la llave que lo abriría vive en el mismo disco que
aquello que protege— sino cifrar el fichero y versionarlo, descifrándolo al desplegar: compra
historial revisable, no confidencialidad frente a un host comprometido, y decirlo importa.

**Las copias se verifican a mano, cuando se verifican.** El guion de volcado ya se niega a dejar
un artefacto que no se cree —conserva el estado de salida y comprueba el tamaño— porque un
volcado de 0 bytes llegó al bucket externo el 13 de julio de 2026 sin que nadie lo advirtiera;
pero comprobar el tamaño no es restaurar, y una copia que nadie ha restaurado es una hipótesis.

**No hay observabilidad ni análisis automático de dependencias.** Un bot de actualización con
agrupación semanal y sin fusión automática —porque etiquetar despliega— está diseñado y aún no
configurado; y estar al día no es saber si alguna dependencia es vulnerable hoy, siendo la cadena
de suministro de software una de las categorías de riesgo de la edición vigente del OWASP Top 10
[50].

Ninguna de estas ausencias es un descuido: son decisiones proporcionadas a un servidor, una
persona y un puñado de usuarios. Lo que las convierte en decisiones y no en olvidos es que están
escritas.
