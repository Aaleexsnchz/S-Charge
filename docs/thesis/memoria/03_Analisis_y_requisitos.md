# 3. Análisis y requisitos

## Dos roles, una sola aplicación

Ante la recarga hay dos papeles. El **conductor** necesita energía fuera de casa: localiza un
punto, comprueba qué conector tiene y a qué precio, calcula lo que va a costarle y lo que va a
tardar antes de enchufar y, en el diseño previsto, lo reserva, registra la sesión y la paga. El
**propietario** dispone de un punto y decide qué hacer con él: darlo de alta, mantenerlo
privado o publicarlo en el mapa, ponerle precio y seguir el uso y los ingresos que genera.

Separarlos en dos aplicaciones sería un error de análisis, porque casi siempre son la misma
persona en momentos distintos. Quien tiene un punto en su plaza de garaje conduce también fuera
de casa y usa la red pública como cualquiera; quien hoy carga en la calle puede instalar un
wallbox el mes que viene y pasar a ofrecerlo. Al registrarse nadie elige bando: no hay pantalla
de «soy conductor» o «soy propietario».

Eso tiene tres consecuencias de diseño que se arrastran al resto de la memoria. La identidad es
única: una cuenta, una sesión, un mismo espacio de perfil. La autorización no se resuelve con
un campo de rol en el usuario, sino por pertenencia del recurso —el punto guarda a qué cuenta
pertenece, y las operaciones de propietario se autorizan contra esa relación—, de modo que el
rol es una situación y no un atributo. Y la navegación ofrece las mismas secciones a todo el
mundo: la pantalla de puntos propios existe para cualquier usuario y aparece vacía mientras no
haya dado de alta ninguno, en lugar de esconderse tras un permiso.

Junto a los dos actores humanos intervienen tres sistemas externos que el usuario no ve: REVE,
del que procede el catálogo; la API pública de Red Eléctrica, de la que procede la curva de
precios; y Google, que actúa a la vez como proveedor de identidad y como destino del enlace de
navegación.

## Casos de uso

La tabla recoge lo que el sistema hace hoy y lo que está formulado para las fases pendientes,
sin mezclar ambas cosas: la columna de estado es la que distingue una funcionalidad usable de
un diseño escrito.

| Id | Actor | Descripción | Estado |
| --- | --- | --- | --- |
| **CU-01** | Usuario | Crear una cuenta con correo y contraseña y verificarla desde el enlace recibido | Implementado |
| **CU-02** | Usuario | Iniciar sesión con credenciales propias o con una cuenta de Google, y recuperar el acceso perdido | Implementado |
| **CU-03** | Conductor | Localizar puntos de recarga en el mapa y filtrarlos por disponibilidad, tipo de conector y banda de precio | Implementado |
| **CU-04** | Conductor | Consultar la ficha de un punto: operador, dirección, conectores, potencia, tarifa y estado | Implementado |
| **CU-05** | Conductor | Simular una recarga en un punto para su modelo de vehículo y un rango de carga | Implementado |
| **CU-06** | Conductor | Abrir la navegación hasta el punto en la aplicación de mapas del móvil | Implementado |
| **CU-07** | Conductor | Ver desde el panel de inicio los puntos más próximos a su posición | Implementado |
| **CU-08** | Propietario | Dar de alta un punto propio, decidir si aparece en el mapa y fijarle precio | Diseñado |
| **CU-09** | Propietario | Obtener la franja más barata para cargar en un punto propio dada la energía necesaria y la hora de salida | Diseñado |
| **CU-10** | Conductor | Reservar un punto para un intervalo, consultarlo y cancelarlo | Diseñado |
| **CU-11** | Conductor · Propietario | Consultar el historial de sesiones y el uso de los puntos propios | Diseñado |
| **CU-12** | Conductor · Propietario | Pagar una sesión desde el monedero y recibir el abono correspondiente | Diseñado |

**Tabla 3.1.** Casos de uso del sistema. «Implementado» significa desplegado y usable en
producción a 5 de agosto de 2026; «diseñado» significa formulado y planificado, no construido.

> **[FIGURA 3.1]** — *Diagrama de casos de uso.* Un recuadro de sistema rotulado «S-Charge» que
> contiene las doce elipses CU-01 a CU-12 de la tabla 3.1, con el identificador y el nombre
> corto en cada una. A la izquierda, dos actores, **Conductor** y **Propietario**, y por encima
> de ellos un actor **Usuario registrado** del que ambos heredan mediante una flecha de
> generalización (triángulo hueco); de *Usuario registrado* salen las asociaciones a CU-01 y
> CU-02, de *Conductor* las de CU-03 a CU-07, CU-10 y CU-12, y de *Propietario* las de CU-08,
> CU-09, CU-11 y CU-12 — CU-11 y CU-12 reciben línea de los dos. Dentro del recuadro, dos
> relaciones `«include»` en línea discontinua: CU-05 incluye CU-04, y CU-10 incluye CU-04. A la
> derecha, tres actores secundarios en forma de sistema externo —**REVE**, **REE (PVPC)** y
> **Google**— asociados respectivamente a CU-03/CU-04, a CU-05/CU-09 y a CU-02/CU-06. Las
> elipses de los casos diseñados se dibujan con trazo discontinuo y las de los implementados con
> trazo continuo, y el pie lo declara: la figura distingue de un vistazo lo construido de lo
> formulado.
> **Cómo obtenerla:** diagrama UML a dibujar en draw.io o PlantUML. Sin colores; la distinción
> se hace con el trazo para que sobreviva a la impresión en blanco y negro.

El formato de especificación detallada se ilustra con CU-05, que es el caso más representativo
del trabajo: cruza las tres fuentes de datos del sistema —catálogo, tarifa y vehículo—, es la
funcionalidad que REVE no ofrece y es la que produce el algoritmo evaluable del capítulo 7. Los
demás casos siguen la misma plantilla y no se reproducen aquí.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-05 — Simular una recarga en un punto |
| **Actor principal** | Conductor |
| **Actores secundarios** | Catálogo de vehículos, tarifa del punto, curva PVPC |
| **Precondiciones** | El usuario tiene sesión activa; el punto existe en el catálogo y tiene al menos un conector con potencia declarada |
| **Postcondiciones** | Ninguna: la simulación no escribe en la base de datos ni deja rastro en el estado del usuario |
| **Flujo principal** | 1. El conductor abre la ficha del punto (CU-04) y solicita simular la recarga.<br>2. El sistema presenta el diálogo con los conectores del punto y la lista de modelos de vehículo.<br>3. El conductor elige modelo, conector y el rango de carga de partida y llegada (por defecto, del 20 % al 80 %).<br>4. El sistema determina la potencia efectiva como el mínimo entre la que admite el vehículo y la que entrega el conector, e integra la carga aplicando la reducción de potencia propia de la corriente continua por encima del 80 %.<br>5. El sistema valora la energía resultante repartiéndola entre las franjas horarias que la sesión atraviesa, al precio que el operador publica para cada una.<br>6. El sistema devuelve energía entregada, duración y coste, y los muestra en el diálogo. |
| **Flujo alternativo A — el punto no publica tarifa** | En el paso 5 no hay tarifa asociada al conector. El sistema no estima ningún precio (capítulo 5): devuelve duración y energía y deja el coste vacío, indicando que el operador no publica precio. El flujo continúa en el paso 6. |
| **Flujo alternativo B — rango de carga inválido** | En el paso 3 la carga de llegada es menor o igual que la de partida. El sistema rechaza la petición con un error de validación y el diálogo señala el campo; no se llega al paso 4. |
| **Excepción — sesión caducada** | Cualquier paso posterior al 1 puede encontrar la sesión expirada; la API responde `401` y el cliente lleva al usuario a la pantalla de acceso |
| **Requisitos relacionados** | RF-09, RF-10, RF-11 |

**Tabla 3.2.** Especificación detallada del caso de uso CU-05.

## Requisitos funcionales

Los requisitos se derivan de los casos de uso y se enuncian de forma que su cumplimiento pueda
comprobarse ejecutando algo: una petición que devuelve un código concreto, una pantalla que
muestra un dato concreto, un recuento. La prioridad es alta cuando el requisito sostiene un
objetivo específico del capítulo 1, media cuando mejora una funcionalidad ya cubierta y baja
cuando pertenece a una fase declarada opcional.

| Id | Requisito | Prioridad | Estado |
| --- | --- | --- | --- |
| **RF-01** | Registro con correo y contraseña de 15 caracteres como mínimo; la cuenta no puede iniciar sesión hasta verificar la dirección | Alta | Implementado |
| **RF-02** | Alta e inicio de sesión con Google; si el correo ya existe, la cuenta se enlaza sin duplicar el usuario | Alta | Implementado |
| **RF-03** | Restablecimiento de contraseña mediante enlace de un solo uso enviado al correo | Alta | Implementado |
| **RF-04** | Toda ruta bajo `/api` exige sesión y responde `401` sin ella, salvo la de salud y las de autenticación | Alta | Implementado |
| **RF-05** | El sistema mantiene copia propia del catálogo nacional —operador, punto, EVSE, conector y tarifa— y la sirve desde su API | Alta | Implementado |
| **RF-06** | El mapa presenta el catálogo completo agrupado por proximidad y permite filtrar por disponibilidad, tipo de conector y banda de precio sin nueva petición al servidor | Alta | Implementado |
| **RF-07** | La ficha de un punto muestra operador, dirección, conectores con su potencia, tarifa y estado | Alta | Implementado |
| **RF-08** | Desde la ficha se abre la navegación al punto en la aplicación de mapas del dispositivo | Media | Implementado |
| **RF-09** | El catálogo de vehículos contiene al menos 30 modelos del mercado español con capacidad de batería y potencia máxima en corriente alterna y continua | Media | Implementado |
| **RF-10** | La curva horaria del PVPC se ingiere a diario, se conserva como histórico y el día en curso es consultable desde la API | Alta | Implementado |
| **RF-11** | Dada una combinación de modelo, conector y rango de carga, el sistema devuelve energía, duración y coste de la sesión | Alta | Implementado |
| **RF-12** | El panel de inicio muestra los puntos más cercanos a la posición del dispositivo | Media | Implementado |
| **RF-13** | Toda superficie que no se alimenta de datos reales aparece etiquetada como datos de ejemplo | Alta | Implementado |
| **RF-14** | Un usuario da de alta un punto propio indicando ubicación, tipo de conector, potencia y visibilidad | Alta | Diseñado (fase 8) |
| **RF-15** | El propietario fija el precio de un punto público como PVPC más margen o como precio fijo por kWh | Alta | Diseñado (fase 8) |
| **RF-16** | Dada la energía necesaria y la hora de salida, el sistema propone la franja más barata en un punto propio y cuantifica el ahorro frente a cargar de inmediato | Alta | Diseñado (fase 9) |
| **RF-17** | La reserva de un punto detecta solapes y rechaza la que se pisa con otra ya existente | Media | Diseñado (fase 10) |
| **RF-18** | Al cerrarse una reserva queda registrada la sesión con energía, duración y coste | Media | Diseñado (fase 10) |
| **RF-19** | El saldo del monedero se deriva de un libro de apuntes de solo anexado; una sesión de pago adeuda al conductor y abona al propietario, y ambos ven el movimiento | Baja | Diseñado (fase 11) |
| **RF-20** | El asistente conversacional opera sobre las APIs propias del sistema, sin incorporar fuentes de datos nuevas | Baja | Diseñado (fase 12) |

**Tabla 3.3.** Requisitos funcionales. El estado distingue lo construido de lo formulado, e
indica la fase que lo construiría.

## Requisitos no funcionales

| Id | Requisito | Criterio de verificación | Estado |
| --- | --- | --- | --- |
| **RNF-01** | Diseño *mobile-first* con 360 px como anchura de referencia | Cada pantalla se recorre completa a 360 px sin desbordamiento horizontal, comprobado en emulador y en un iPhone y un Android reales | Cumplido en lo construido |
| **RNF-02** | Interfaz en español; código, comentarios, *commits* y documentación técnica en inglés | Ninguna cadena visible en inglés en las vistas; los códigos de error del backend se traducen en el cliente | Cumplido |
| **RNF-03** | Rendimiento en móvil medido, no declarado | Auditoría Lighthouse sobre la construcción de producción con perfil móvil. Medición de 13-06-2026: 94 en `/login` y 31 en `/map`, con FCP 3,0 s y LCP 4,5 s en el mapa tras reducir su carga útil un 35 % | Medido; pendiente de mejora |
| **RNF-04** | Instalable como PWA en el móvil desde la instancia de producción | Manifiesto y *service worker* servidos; instalación efectiva probada en iPhone y Android [33] | Cumplido |
| **RNF-05** | La sesión viaja en una cookie `HttpOnly` de primera parte, con vida de 14 días, sin credenciales accesibles desde JavaScript | Inspección de la cookie emitida y ausencia de credenciales en el almacenamiento del navegador (capítulo 6) | Cumplido |
| **RNF-06** | Cifrado en tránsito obligatorio | HTTPS con certificado automático y HSTS activo; sin contexto seguro no funcionarían ni el *service worker* ni la geolocalización [34] | Cumplido |
| **RNF-07** | Límites de tasa por IP de cliente y por ruta en las operaciones sensibles | 10 por minuto en acceso, 10 por hora en registro y 5 por hora en los envíos de correo, respondiendo `429` con `Retry-After` | Cumplido |
| **RNF-08** | Minimización de datos personales | El sistema almacena correo electrónico y, en su caso, el identificador de la cuenta de Google; la dirección IP se trata con finalidad de seguridad. El desarrollo del marco y lo que falta para una operación con usuarios reales está en el capítulo 10 [35] | Parcial |
| **RNF-09** | Copia de seguridad de la base de datos y capacidad de restauración demostrada | Copia semanal fuera de la máquina —restringida al volcado sin datos personales, que es la parte irrecuperable— y volcado completo automático antes de cada migración; restauración ensayada a mano con recuento de filas idéntico. La verificación automática de la restauración es criterio de la fase 13 | Parcial |
| **RNF-10** | Mantenibilidad sostenida por comprobaciones automatizadas, no por disciplina | Estilo, formato, tipos y pruebas se ejecutan antes de cada envío al repositorio y en cada *pull request*; la batería completa tarda 8 s de reloj. 134 pruebas de backend y 27 de frontend. El contrato de la API está versionado y la integración continua falla si el cliente y el servidor divergen | Cumplido |
| **RNF-11** | Accesibilidad de la interfaz construida | Puntuación de accesibilidad de Lighthouse de 100 en `/map` y 98 en `/login` en la medición de junio de 2026, sobre los criterios de contraste y etiquetado de WCAG 2.2 [36] | Cumplido en lo construido |
| **RNF-12** | Trazabilidad de los eventos de identidad | Cada registro, acceso, verificación y restablecimiento emite una línea JSON de auditoría a la salida estándar del proceso | Cumplido |

**Tabla 3.4.** Requisitos no funcionales y criterio con el que se comprueba cada uno.

> **PENDIENTE:** repetir la auditoría Lighthouse de `/map` y `/login` tras optimizar la carga
> útil del mapa y sustituir aquí el estado de RNF-03 por la comparación antes/después.

## Restricciones

Cinco condiciones no se negociaron con el diseño: el diseño se hizo alrededor de ellas.

**La API de REVE admite 5 peticiones/hora.** Es la restricción que más lejos llega, porque
descarta consultar la fuente en tiempo real y obliga a construir el sistema sobre una copia
local que se siembra despacio —la carga inicial completa tardó unos 12 días de ejecuciones
desatendidas— y se refresca de forma incremental. Decide el modelo de datos, la forma del
proceso de ingesta y hasta el número de procesos que pueden ejecutarlo a la vez. El argumento
completo es del capítulo 5.

**No existe un flujo de disponibilidad en tiempo real.** La fuente no publica un estado
continuo de ocupación, de modo que el sistema no puede saber si un punto está libre ahora. La
estructura para admitir esa señal existe —el estado del EVSE, su agregación al punto y el color
del marcador— pero no hay nada conectado a ella. La decisión fue declararlo en lugar de
inventar una ocupación verosímil, y condiciona lo que puede prometer una reserva.

**No hay hardware de recarga.** Sin acceso a una estación, ninguna sesión física puede
observarse, medirse ni contrastarse. Eso obliga a que la simulación sea un modelo a partir de
especificaciones —potencia mínima entre vehículo y conector, con reducción por encima del 80 %
de carga en corriente continua— y no un ajuste sobre sesiones reales; y explica que el monedero
sea un libro de apuntes interno y no un cobro. La consecuencia para la validación se recoge en
el capítulo 9.

**El presupuesto de infraestructura es mínimo.** Un único servidor virtual pequeño y un
dominio. Eso elimina de partida las arquitecturas con varios nodos, base de datos gestionada u
orquestador, y convierte el escalado en un capítulo argumentado en vez de construido
(capítulo 8).

**Un solo desarrollador y una fecha de entrega fija.** No hay reparto posible del trabajo ni
paralelismo entre personas, así que el alcance es la única variable que se puede mover. De ahí
que la metodología dedique tanto esfuerzo a decidir por adelantado qué se recorta.

## Metodología de desarrollo

El trabajo se organiza en **14 fases**, y cada una es una funcionalidad con sentido propio: al
terminarla la aplicación hace algo que antes no hacía, no queda a medio camino de nada. Ninguna
es una capa técnica —no hay una fase «base de datos» ni una fase «frontend»—, porque una fase
que no se puede enseñar tampoco se puede dar por terminada.

Cada fase lleva sus **criterios de aceptación escritos por adelantado**, en forma de lista de
comprobación, antes de escribir la primera línea de código. Están redactados como hechos
observables: «la siembra completa se ejecuta de forma desatendida», «un cambio llega al
servidor sin intervención manual», «el mapa se ha probado en un iPhone y un Android reales». La
utilidad de escribirlos antes no es documental sino de honestidad: cuando el criterio se fija
después, uno acaba redactándolo a la medida de lo que ha conseguido hacer.

La unidad de entrega es la ***slice*, que equivale exactamente a un *pull request***, y la
unidad de trabajo es la **tarea, que equivale a un *commit***. La equivalencia es literal y
tiene efectos prácticos: si una *slice* no cabe en una rama que se pueda revisar y fusionar
entera, está mal cortada; si una tarea toca dos asuntos que no comparten motivo, son dos
*commits*. El histórico del repositorio se convierte así en el registro real del trabajo —231
*commits* repartidos en algo más de veinte *pull requests* a 5 de agosto de 2026— y el título
de cada una sirve directamente como nota de la versión correspondiente.

Los **planes de fase se escriben justo antes de empezar la fase, nunca por adelantado**. Un
plan que merezca la pena seguir necesita que sus decisiones se tomen en el momento en que hay
información para tomarlas, y esa información la produce la fase anterior: el orden de las
fases 6 y 7 se fijó cuando el despliegue ya había demostrado qué construía la integración
continua y qué no. Y son **desechables**. Al cerrar una fase, el conocimiento que sobrevive se
migra a la documentación estable —una decisión al registro de decisiones, un procedimiento al
manual de operación, una medida al documento de la funcionalidad que se comparará con ella— y
el plan deja de tener lectores. La regla que lo sostiene es que ningún documento permanente
puede citar un plan de fase como fuente.

Las **fases opcionales y el orden de recorte están declarados por adelantado**. Si el calendario
se estrecha, salen de abajo arriba: primero el asistente de IA, después el monedero y por
último las reservas con el registro de sesiones. Son las prescindibles porque ninguna sostiene
por sí sola un pilar del trabajo —el modelo de plataforma lo sostiene la fase 8, el algoritmo
evaluable la fase 9 y el pilar de despliegue la fase 5—, y todo lo marcado como núcleo no se
negocia. Recortar una fase no significa dejar una pantalla a medias: la funcionalidad conserva
su estado de no construida y su interfaz de muestra sigue etiquetada, porque la aplicación no
puede presentar como operativo algo que se ha decidido no hacer. Tener decidido el recorte
antes de necesitarlo es gestión; decidirlo cuando falta una semana es otra cosa.

La rama principal está protegida: todo entra por *pull request* con las comprobaciones en
verde, sin envíos directos ni reescrituras de historia, y es lo que ejecuta producción, de modo
que debe quedar desplegable en cada *commit*. La cadena de comprobaciones que hace cumplir esa
regla —ganchos locales e integración continua— se describe en el capítulo 8.

| # | Fase | Carácter | Estado a 5 de agosto de 2026 |
| --- | --- | --- | --- |
| 1 | Fundación: contenedores, API, base de datos y autenticación | Núcleo | Terminada |
| 2 | Espejo del catálogo de REVE y mapa | Núcleo | Terminada |
| 3 | Simulación de recarga, vehículos y precios | Núcleo | Terminada |
| 4 | Rediseño del cliente y arquitectura de información | Núcleo | Terminada |
| 5 | Despliegue, integración y entrega continuas, versiones | Núcleo | En curso — desplegado en producción el 4 de agosto de 2026; queda etiquetar la primera versión |
| 6 | Migración del stack del cliente | Núcleo | No iniciada |
| 7 | Reactivación de los procesos de ingesta | Núcleo | No iniciada — el planificador está desplegado y deliberadamente parado |
| 8 | Puntos privados y precio del propietario | Núcleo | No iniciada |
| 9 | Optimizador de recarga | Núcleo | No iniciada |
| 10 | Reservas y registro de sesiones | Opcional | No iniciada |
| 11 | Monedero y sesiones de pago | Opcional | No iniciada |
| 12 | Asistente de IA | Opcional | No iniciada |
| 13 | Pulido, seguridad y endurecimiento | Núcleo | No iniciada |
| 14 | Redacción de la memoria | Núcleo | En curso |

**Tabla 3.5.** Las 14 fases y su estado real. El orden de recorte de las opcionales es 12, 11 y
10, en ese orden.

## Planificación temporal

El primer *commit* del repositorio es del **28 de marzo de 2026**. Las fases 1 a 4 —
autenticación, catálogo y mapa, simulación y rediseño del cliente— se cerraron entre esa fecha
y finales de junio; la fase 5 se abrió con la infraestructura de despliegue a principios de
julio y llevó la aplicación a producción el **4 de agosto de 2026**. Ese es el punto en que se
escribe esta memoria: de las once fases marcadas como núcleo, cuatro están cerradas y una a
punto de cerrarse, y las tres opcionales siguen sin empezar.

Queda, en el orden en que está previsto abordarlo, la migración del stack del cliente, la
reactivación de los procesos de ingesta —parados desde el 8 de julio de 2026, con la marca de
agua congelada a propósito para poder medir el hueco antes de que un ciclo la mueva—, los
puntos de propietario y el optimizador. Las tres fases opcionales entran solo si el calendario
lo permite, y la redacción avanza en paralelo desde ahora.

> **[FIGURA 3.2]** — *Cronograma del proyecto.* Diagrama de Gantt con una barra por fase sobre
> un eje mensual de marzo a septiembre de 2026. Las barras de las fases 1 a 5 son reales y se
> dibujan con las fechas verificables del repositorio; las de las fases 6 a 14 son previsión y
> se dibujan con trama distinta y sin fechas de fin comprometidas, con las tres opcionales
> además en un tono más claro. Hitos marcados como rombo: primer *commit* (28-03-2026), primera
> *pull request* de autenticación fusionada (20-04-2026), siembra del catálogo de REVE
> (21-06-2026), infraestructura de despliegue (09-07-2026) y puesta en producción (04-08-2026).
> **Cómo obtenerla:** diagrama a construir con las fechas de fusión que devuelve
> `git log --merges --date=short` sobre el repositorio del proyecto, para que las barras reales
> no se estimen. No inventar fechas de fin para las fases no iniciadas.

> **PENDIENTE:** completar la figura 3.2 con las fechas de cierre efectivas de las fases 6 a 14
> a medida que se cierren, y revisar la tabla 3.5 antes de la entrega.
