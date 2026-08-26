# 3. Análisis, requisitos y planificación

El capítulo recorre el camino que va de los dos papeles que intervienen en la recarga hasta la
planificación del desarrollo de la aplicación. Empieza por quién usa el sistema y por las seis
condiciones de las que depende el sistema; sigue con los casos de uso y con los requisitos,
funcionales y no funcionales, cada uno acompañado del criterio que permite comprobarlo; y termina
con la trazabilidad hacia los objetivos del capítulo 1, la metodología de trabajo, la planificación
y los riesgos del proyecto.

## Actores

Ante la recarga de vehículos eléctricos hay dos papeles. Por un lado, el conductor necesita
recargar el vehículo fuera de casa: localiza un punto, comprueba qué conector tiene y a qué precio,
calcula lo que va a costarle y lo que va a tardar antes de enchufar y, en el diseño previsto, lo
reserva, registra la sesión y la paga. El propietario dispone de un punto y decide qué hacer con
él: darlo de alta, mantenerlo privado o publicarlo en el mapa, ponerle precio y seguir el uso y los
ingresos que genera.

Intervienen además cinco sistemas externos de los cuales, dos, aportan los datos que la aplicación
no genera: REVE, de donde procede el catálogo de puntos, y la API pública de Red Eléctrica, de
donde procede la curva de precios. Google cumple dos papeles distintos, ya que actúa como proveedor
de identidad para el acceso con cuenta propia y como destino del enlace de navegación hacia el
punto elegido. Por otro lado, OpenFreeMap sirve las teselas sobre las que se dibuja el mapa.
Finalmente, Resend entrega los correos de verificación y restablecimiento de contraseña.

Los dos papeles humanos no son dos usuarios distintos, sino la misma persona en momentos distintos:
quien tiene un punto en su garaje estará interesado en gestionarlo, aunque sea para uso privado; y
por lo general, también carga fuera de casa. Por eso al registrarse nadie elige bando: la identidad
es única —una cuenta, una sesión, un mismo perfil—; la autorización no mira un campo de rol sino la
pertenencia del recurso, de modo que ser propietario es una situación y no un atributo; y la
navegación ofrece las mismas secciones a todo el mundo, por si en algún momento las necesitaran.

La siguiente figura resume esas relaciones a través del diagrama de contexto del sistema del modelo
C4 [33]:

> **[FIGURA 3.1]** — *Diagrama de contexto del sistema* (modelo C4 [33], nivel 1).

## Restricciones

En la fase inicial de la planificación y el desarrollo de la aplicación, se encontraron seis
restricciones, por lo que el diseño del sistema se planteó desde el inicio alrededor de ellas. Cada
una se enuncia aquí junto con la decisión de diseño que impuso; el desarrollo completo de esa
decisión queda para el capítulo que corresponde.

- **El catálogo procede de una única fuente externa.** Todos los puntos que muestra la aplicación
  salen del registro oficial, sobre cuyo formato, disponibilidad y continuidad no se tiene control
  alguno. Esa dependencia obliga a que el sistema no dependa de la fuente para funcionar: sirve el
  catálogo desde su propia copia y la fuente solo interviene para refrescar las tarifas y señalar
  los puntos nuevos que aún no constan en ella.
- **La API de REVE admite 5 peticiones/hora.** Es la restricción que más lejos llega, porque
  descarta consultar la fuente en tiempo real y obliga a construir el sistema sobre una copia local
  que se siembra despacio —la carga inicial completa tardó unos 12 días de ejecuciones
  desatendidas— y se refresca de forma incremental. Decide el modelo de datos, la forma del proceso
  de ingesta y hasta el número de procesos que pueden ejecutarlo a la vez. La descripción completa
  se detalla en el capítulo 5.
- **No existe un flujo de disponibilidad en tiempo real.** Es consecuencia directa de la
  restricción anterior, y la estructura para admitir esa señal está construida y vacía: el estado
  del EVSE, su agregación al punto y el color del marcador existen, pero no hay ninguna fuente
  conectada a ellos. La decisión que se tomó en su lugar fue tratar los puntos del catálogo como si
  formaran parte de una red propia: la ocupación que ve un usuario nace de las reservas y las
  sesiones que otros inician dentro de la aplicación, con el estado compartido entre todos ellos.
  Eso determina que ocupación, reservas y sesiones sean tablas locales y no un reflejo del poste;
  el modelo se detalla en el capítulo 5 y su recorrido por pantalla, en el capítulo 7.
- **No hay hardware de recarga.** Sin acceso a una estación, ninguna sesión física puede observarse
  ni medirse, de modo que la simulación tiene que ser un modelo construido a partir de
  especificaciones —potencia mínima entre vehículo y conector, con reducción por encima del 80 % de
  carga en corriente continua— y no un ajuste sobre sesiones reales. Por la misma razón el
  movimiento económico entre conductor y propietario se resuelve sin pasarela de pago, ya que no
  hay sesión física que cobrar. La consecuencia para la validación se recoge en el capítulo 9.
- **El presupuesto de infraestructura es mínimo.** Un único servidor virtual pequeño y un dominio,
  con los contenedores gobernados por Docker Compose detrás de un proxy inverso. Eso elimina de
  partida las arquitecturas con varios nodos, base de datos gestionada u orquestador, y convierte
  el escalado en un capítulo argumentado en vez de construido (capítulo 8).
- **Un solo desarrollador y una fecha de entrega fija.** No hay reparto posible del trabajo ni
  paralelismo entre personas, de modo que el orden de las fases es la principal herramienta de
  planificación: cada una tiene que dejar la aplicación en un estado presentable por sí mismo.

## Casos de uso

La tabla recoge lo que el sistema hace hoy, lo que está formulado para las fases pendientes y lo
que se ha previsto sin entrar en el alcance de este trabajo. El estado maneja los mismos dos
valores que la tabla de requisitos: «implementado» y «pendiente».

| Id | Actor | Descripción | Estado |
| --- | --- | --- | --- |
| **CU-01** | Usuario | Crear una cuenta con correo y contraseña y verificarla desde el enlace recibido | Implementado |
| **CU-02** | Usuario | Iniciar sesión con credenciales propias o con una cuenta de Google, y recuperar el acceso perdido | Implementado |
| **CU-03** | Conductor | Localizar puntos de recarga en el mapa y aplicar filtros | Implementado |
| **CU-04** | Conductor | Consultar la ficha de un punto | Implementado |
| **CU-05** | Conductor | Estimar tiempo y coste de una recarga en un punto | Implementado |
| **CU-06** | Conductor | Abrir la navegación hasta el punto en la aplicación de mapas del móvil | Implementado |
| **CU-07** | Conductor | Ver desde el panel de inicio los puntos más próximos a su posición | Implementado |
| **CU-08** | Propietario | Dar de alta un punto propio, fijarle precio y horario, y abrirlo o cerrarlo a nuevas reservas | Pendiente |
| **CU-09** | Propietario | Optimizar la carga en función del precio de la electricidad | Pendiente |
| **CU-10** | Conductor | Reservar un punto para un intervalo, consultarlo y cancelarlo | Pendiente |
| **CU-11** | Conductor · Propietario | Consultar el historial de sesiones y el uso de los puntos propios | Pendiente |
| **CU-12** | Conductor · Propietario | Iniciar una sesión de carga y liquidar su coste desde el monedero | Pendiente |
| **CU-13** | Conductor | Planificar un viaje largo con las paradas de recarga necesarias según la autonomía del vehículo y el estado de la batería | Pendiente |
| **CU-14** | Conductor · Propietario | Resolver en lenguaje natural preguntas sobre puntos, precios y sesiones propias | Pendiente |

**Tabla 3.1.** Casos de uso del sistema.

El formato de especificación detallada se ilustra con CU-10. Las fichas de los demás casos siguen
esta misma plantilla y se recogen en el anexo A.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-10 — Reservar un punto de recarga |
| **Actor principal** | Conductor |
| **Actores secundarios** | Propietario del punto, reloj del sistema |
| **Precondiciones** | El usuario tiene sesión activa; el punto existe en el catálogo, está visible y abierto, el intervalo solicitado empieza en el futuro y cae dentro del horario de disponibilidad del punto, y el monedero del conductor cubre la señal |
| **Postcondiciones** | Queda una reserva activa asociada al punto y al conductor, con la señal retenida en su monedero hasta que la reserva se resuelva, y el resto de usuarios ve el punto ocupado durante ese intervalo |
| **Flujo principal** | 1. El conductor abre la ficha del punto (CU-04) y solicita reservarlo.<br>2. El sistema propone un intervalo a partir de la hora actual y de la duración estimada de la recarga (CU-05).<br>3. El conductor ajusta el intervalo y confirma.<br>4. El sistema comprueba que el intervalo no se solapa con ninguna reserva ni sesión activa del mismo punto.<br>5. El sistema retiene la señal, crea la reserva, marca el punto como ocupado en ese intervalo e informa al conductor del margen del que dispone para iniciar la sesión y de las condiciones en que recupera la señal.<br>6. El resto de usuarios ve el punto ocupado en el mapa desde su siguiente consulta. |
| **Flujo alternativo A — el intervalo se solapa** | En el paso 4 existe otra reserva o una sesión en curso que pisa el intervalo, o el intervalo cae fuera del horario del punto. El sistema rechaza la petición, indica el primer hueco libre disponible y devuelve el control al paso 3. |
| **Flujo alternativo B — cancelación por el conductor** | Con la reserva activa, el conductor la cancela. Si lo hace al menos 15 minutos antes de la hora de inicio, el sistema libera el intervalo y devuelve la señal; por debajo de ese margen, la señal se abona al propietario. En ambos casos el punto vuelve a estar disponible. |
| **Excepción — la reserva caduca** | Transcurrido el margen de inicio sin que el conductor abra la sesión (CU-12), el sistema marca la reserva como caducada, libera el punto, abona la señal al propietario y deja constancia en el historial del conductor. |
| **Requisitos relacionados** | RF-05, RF-06, RF-10, RF-12, RF-13, RF-19 |

**Tabla 3.2.** Especificación detallada del CU-10.

## Requisitos funcionales

Los requisitos se derivan de los casos de uso y se enuncian de forma que se pueda comprobar su
cumplimiento. La prioridad es alta cuando el requisito sostiene un objetivo específico del capítulo
1, media cuando completa o mejora una funcionalidad ya cubierta y baja cuando añade valor sobre
funcionalidades que ya responden sin él.

| Id | Requisito | Criterio de verificación | Prioridad | Estado |
| --- | --- | --- | --- | --- |
| **RF-01** | Registro con correo y contraseña de 15 caracteres como mínimo; la cuenta no puede iniciar sesión hasta verificar la dirección | Prueba automatizada de registro: una contraseña de 14 caracteres se rechaza y una de 15 se acepta; la cuenta creada responde 401 al intentar acceder antes de verificar | Alta | Implementado |
| **RF-02** | Alta e inicio de sesión con Google —si el correo ya existe, la cuenta se enlaza sin duplicar el usuario— y restablecimiento de contraseña mediante enlace de un solo uso enviado al correo | Alta con Google sobre un correo ya registrado: la base conserva un único usuario con las dos identidades enlazadas. El enlace de restablecimiento funciona una vez y es rechazado en el segundo uso | Alta | Implementado |
| **RF-03** | Toda ruta bajo `/api` exige sesión y responde 401 sin ella, salvo la de salud y las de autenticación | Recorrido automatizado de las rutas bajo `/api` sin sesión: todas responden 401 salvo la de salud y las de autenticación | Alta | Implementado |
| **RF-04** | El sistema mantiene copia propia del catálogo nacional —operador, punto, EVSE, conector y tarifa— y la sirve desde su API | La API sirve operador, punto, EVSE, conector y tarifa con la fuente externa desconectada | Alta | Implementado |
| **RF-05** | El mapa presenta el catálogo completo agrupado por proximidad y permite filtrar por disponibilidad, tipo de conector y banda de precio sin nueva petición al servidor; el panel de inicio muestra los puntos más cercanos a la posición del dispositivo | Con el catálogo ya cargado y sin red, los filtros siguen respondiendo sobre los puntos en memoria. Con una posición fijada, el panel devuelve los puntos ordenados por distancia creciente | Alta | Implementado |
| **RF-06** | La ficha de un punto muestra operador, dirección, conectores con su potencia, tarifa y estado, y desde ella se abre la navegación al punto en la aplicación de mapas del dispositivo | La respuesta de la ficha incluye los cinco campos —operador, dirección, conectores con potencia, tarifa y estado— o su marca de ausencia, y el enlace generado abre la aplicación de mapas con las coordenadas del punto en iPhone y en Android | Alta | Implementado |
| **RF-07** | El catálogo de vehículos contiene al menos 30 modelos del mercado español con capacidad de batería y potencia máxima en corriente alterna y continua | Recuento del catálogo de vehículos igual o superior a 30 modelos, con capacidad y potencias no nulas | Alta | Implementado |
| **RF-08** | La curva horaria del PVPC se ingiere a diario, se conserva como histórico y el día en curso es consultable desde la API | Registro de la ejecución diaria de la ingesta y consulta a la API de la curva del día en curso; el histórico conserva los días anteriores | Alta | Implementado |
| **RF-09** | Dada una combinación de modelo, conector y rango de carga, el sistema devuelve energía, duración y coste estimados de la sesión; el coste sale de la tarifa que el operador publica y de ninguna otra fuente, de modo que un conector sin tarifa devuelve energía y duración sin coste | Caso de referencia calculado a mano: energía, duración y coste coinciden con el resultado esperado. Sobre un conector sin tarifa publicada, la respuesta trae energía y duración y el coste vacío, nunca un valor estimado | Alta | Implementado |
| **RF-10** | Un punto propio se registra con ubicación, conector, potencia, visibilidad, precio —PVPC más margen o fijo por kWh— y horario de disponibilidad, y su propietario puede cerrarlo a nuevas reservas | El punto registrado conserva todos esos atributos; al cambiar el PVPC de referencia el precio indexado varía y el fijo no; con el punto cerrado, toda reserva nueva se rechaza | Alta | Pendiente (fase 7) |
| **RF-11** | Dada la energía necesaria y la hora de salida, el sistema propone la franja más barata en un punto propio, cuantifica el ahorro frente a cargar de inmediato y programa la sesión en esa franja | Caso con curva conocida: la franja propuesta coincide con la más barata calculada a mano, el ahorro se corresponde y la sesión queda programada en ese intervalo | Media | Pendiente (fase 8) |
| **RF-12** | Un punto puede reservarse para un intervalo futuro dentro de su horario; la reserva se rechaza si se solapa con otra existente y, si la sesión no se inicia en el margen concedido, caduca y el punto vuelve a estar disponible sin intervención de nadie | Dos reservas solapadas sobre el mismo punto: la segunda se rechaza. Transcurrido el margen sin sesión, la reserva figura como caducada y el punto admite una reserva nueva | Alta | Pendiente (fase 9) |
| **RF-13** | La reserva exige una señal de 1 € retenida en el monedero: se descuenta del importe de la sesión si el conductor acude, y se abona al propietario si cancela con menos de 15 minutos de antelación o no acude | La reserva atendida descuenta la señal del importe liquidado; la cancelada fuera de plazo y la caducada dejan la señal como apunte a favor del propietario | Media | Pendiente (fases 9 y 10) |
| **RF-14** | Una sesión puede iniciarse sobre un punto libre o al amparo de una reserva; al iniciarse queda registrada y con la retención aplicada | Una sesión iniciada sobre un punto libre se abre igual que una amparada en reserva; al iniciarse existen su registro y la retención | Alta | Pendiente (fase 9) |
| **RF-15** | Al cerrarse la sesión se liquida con su energía, duración y coste, más el recargo por ocupación si el vehículo sigue conectado tras el final de la carga, y descontando la señal si venía de una reserva | El registro de la sesión cerrada recoge energía, duración y coste consultables en el historial, y los apuntes del conductor y del propietario cuadran sin que ninguno se modifique a posteriori | Alta | Pendiente (fase 10) |
| **RF-16** | El usuario formula preguntas en lenguaje natural sobre puntos, precios y sus propias sesiones, y el sistema responde a partir de consultas a su propia API acotadas a la identidad de quien pregunta | Un conjunto de preguntas de referencia obtiene respuestas cuyos datos coinciden con los que devuelve la API para ese usuario; una pregunta sobre datos de otro usuario no obtiene respuesta | Baja | Pendiente (fase 12) |
| **RF-17** | El conductor consulta el historial de sus sesiones con fecha, punto, energía, duración y coste, y el propietario el uso de sus puntos con la energía entregada y el importe abonado | Tras cerrarse una sesión aparece en el historial del conductor y en el del propietario, con los mismos importes que registran los apuntes del monedero | Media | Pendiente (fase 9) |
| **RF-18** | Dados un origen, un destino y una carga de partida, el sistema devuelve un plan de viaje con las paradas de recarga necesarias, la energía a recuperar en cada una y el tiempo de carga asociado | Un trayecto que excede la autonomía declarada del vehículo devuelve al menos una parada alcanzable con la carga disponible; un trayecto que cabe en la autonomía no propone ninguna | Baja | Pendiente (fase 11) |
| **RF-19** | El sistema avisa al usuario de los hechos que afectan a su reserva o a su dinero: confirmación de la reserva, proximidad del vencimiento, caducidad con pérdida de la señal y liquidación de la sesión | Cada uno de esos cuatro hechos deja un aviso visible para el usuario afectado, comprobado recorriendo el ciclo completo de una reserva | Media | Pendiente (fase 9) |

**Tabla 3.3.** Requisitos funcionales.

## Requisitos no funcionales

Los requisitos no funcionales se enuncian junto al criterio con el que se comprueba cada uno,
porque un atributo de calidad que no dice cómo se mide es difícil de comprobar después.

| Id | Requisito | Criterio de verificación | Estado |
| --- | --- | --- | --- |
| **RNF-01** | Diseño *mobile-first* con 360 px como anchura de referencia | Cada pantalla construida se recorre completa a 360 px sin desbordamiento horizontal, comprobado en emulador y en un iPhone y un Android reales | Implementado |
| **RNF-02** | Interfaz en español; código, comentarios, *commits* y documentación técnica en inglés | Ninguna cadena visible en inglés en las vistas; los códigos de error del *backend* se traducen en el cliente | Implementado |
| **RNF-03** | Rendimiento en móvil medido, no declarado | Auditoría Lighthouse sobre la construcción de producción con perfil móvil | Implementado |
| **RNF-04** | Instalable como PWA en el móvil desde la instancia de producción | Manifiesto y *service worker* servidos; instalación efectiva probada en iPhone y Android | Implementado |
| **RNF-05** | La sesión viaja en una cookie `HttpOnly` de primera parte, con vida de 14 días, sin credenciales accesibles desde JavaScript | Inspección de la cookie emitida y ausencia de credenciales en el almacenamiento del navegador (capítulo 6) | Implementado |
| **RNF-06** | Cifrado en tránsito obligatorio | HTTPS con certificado automático y HSTS activo; sin contexto seguro no funcionarían ni el *service worker* ni la geolocalización [34] | Implementado |
| **RNF-07** | Límites de tasa por IP de cliente y por ruta en las operaciones sensibles | 10 por minuto en acceso, 10 por hora en registro y 5 por hora en los envíos de correo, respondiendo 429 con `Retry-After` | Implementado |
| **RNF-08** | Minimización de datos personales | El sistema almacena correo electrónico y, en su caso, el identificador de la cuenta de Google; la dirección IP se trata con finalidad de seguridad, y ningún otro dato personal aparece en el esquema. Queda pendiente el marco de tratamiento que exigiría una operación con usuarios reales [35] | Parcial |
| **RNF-09** | Copia de seguridad cifrada de la base de datos completa y capacidad de restauración demostrada | Copia semanal cifrada fuera de la máquina que incluye las cuentas, las sesiones y los apuntes del monedero, por ser los datos que no existen en ninguna otra fuente, y volcado completo automático antes de cada migración; restauración ensayada a mano con recuento de filas idéntico. La verificación automática de la restauración queda como criterio de la fase 13 | Parcial |
| **RNF-10** | Mantenibilidad sostenida por comprobaciones automatizadas, no por disciplina | Estilo, formato, tipos y pruebas se ejecutan antes de cada envío al repositorio y en cada *pull request*. La integración continua falla si el cliente y el servidor divergen | Implementado |
| **RNF-11** | Accesibilidad de la interfaz construida | Puntuación de accesibilidad de Lighthouse de 100 en `/map` y 98 en `/login` en la medición de junio de 2026, sobre los criterios de contraste y etiquetado de WCAG 2.2 [36] | Implementado |
| **RNF-12** | Trazabilidad de los eventos de identidad | Cada registro, acceso, verificación y restablecimiento emite una línea JSON de auditoría a la salida estándar del proceso | Implementado |
| **RNF-13** | Toda superficie que no se alimenta de datos reales aparece etiquetada como datos de ejemplo | Revisión pantalla por pantalla de la construcción de producción: ninguna de las vistas construidas presenta datos ficticios sin su etiqueta | Implementado |
| **RNF-14** | Entrega continua: un cambio integrado en la rama principal llega al servidor de producción sin intervención manual | Registro de la última publicación: se dispara desde la rama principal y no existe ningún paso manual entre la aceptación del cambio y su disponibilidad en producción | Implementado |

**Tabla 3.4.** Requisitos no funcionales.

## Trazabilidad

La tabla cruza los objetivos específicos del capítulo 1 con los casos de uso y los requisitos que
los sirven, además de con el capítulo donde se comprueba cada uno. Se lee en dos direcciones: hacia
adelante comprueba que ningún objetivo se quedó sin requisitos que lo sostengan, y hacia atrás, que
ningún requisito se ha colado sin responder a un objetivo declarado.

| Objetivo | Casos de uso | Requisitos | Dónde se comprueba |
| --- | --- | --- | --- |
| **OE1** | CU-01, CU-02 | RF-01 a RF-03; RNF-01, RNF-05, RNF-10, RNF-12, RNF-13 | Capítulos 6 y 9 |
| **OE2** | CU-03, CU-04 | RF-04 a RF-06 | Capítulo 5 |
| **OE3** | CU-05 a CU-14 | RF-05, RF-07 a RF-19 | Capítulo 7 |
| **OE4** | — | RNF-04, RNF-06, RNF-09, RNF-14 | Capítulo 8 |
| **OE5** | — | RNF-03, RNF-08 | Capítulos 8, 9 y 11 |

**Tabla 3.5.** Trazabilidad entre los objetivos específicos del capítulo 1, los casos de uso y los
requisitos que los sirven.

## Metodología y planificación

El desarrollo no ha seguido ningún marco de trabajo conocido. El punto de partida fue la idea y las
funcionalidades que se querían construir; a partir de ahí se construyó un plan general que se
dividió en fases, y cada fase se planificó en detalle justo antes de abordarla. En la práctica es
un desarrollo iterativo e incremental [37] donde se va entregando funcionalidad utilizable y el
alcance de la siguiente se decide con lo aprendido en la anterior. No se ha adoptado Scrum ni
ningún otro método de equipo porque sus mecanismos principales resuelven problemas de coordinación
que no existen cuando el equipo es una sola persona. Sí se conserva de esa metodología lo que sigue
teniendo sentido en solitario, entregar en incrementos utilizables, fijar el criterio de terminado
antes de empezar y revisar el plan al cerrar cada fase.

El trabajo se organiza en fases numeradas, y cada una es una funcionalidad con sentido propio. Cada
fase lleva sus criterios de aceptación escritos por adelantado, en forma de lista de comprobación,
antes de escribir la primera línea de código y están redactados como hechos observables.

La unidad de entrega es la *slice* —un corte vertical de funcionalidad que atraviesa cliente, API y
base de datos—, que equivale exactamente a un *pull request*, la propuesta de cambio que se revisa
y se incorpora en bloque. La unidad de trabajo es la tarea, que equivale a un *commit*, cada
anotación con la que el repositorio registra un cambio. El histórico del repositorio se convierte
así en el registro real del trabajo, y el título de cada *pull request* sirve directamente como
nota de la versión correspondiente.

Conviene distinguir dos niveles de planificación. El orden de las fases y lo que entra en cada una
se fijaron al principio, y son los que recoge la tabla 3.6; lo que no se escribe por adelantado es
el plan detallado de cada fase, que se redacta justo antes de abordarla. Se ha hecho así para poder
tomar decisiones cuando hay información y más contexto para tomarlas, ya que esa información la
produce la fase anterior, evitando así el tener que estar reescribiendo los planes específicos de
cada fase constantemente. Al cerrar una fase, lo que sobrevive se migra a la documentación estable.

La rama principal está protegida: todo entra mediante una *pull request* con las comprobaciones en
verde, sin envíos directos ni reescrituras de historia, y es lo que ejecuta producción, de modo que
debe quedar desplegable en cada *commit*. La cadena de comprobaciones que hace cumplir esa regla se
describe en el capítulo 8.

El desarrollo se ha realizado de forma discontinua, compaginado con la actividad profesional, de
modo que el calendario se expresa en hitos de cierre verificables contra el repositorio y no en
dedicación sostenida. La tabla recoge las fases en el orden previsto y el estado de cada una a la
fecha de esta memoria.

| Id | Fase | Estado |
| --- | --- | --- |
| 1 | Fundación: contenedores, API, base de datos y autenticación | Terminada |
| 2 | Espejo del catálogo de REVE y mapa | Terminada |
| 3 | Simulación de recarga, vehículos y precios | Terminada |
| 4 | Rediseño del cliente y arquitectura de información | Terminada |
| 5 | Despliegue, integración y entrega continuas, versiones | Terminada |
| 6 | Reactivación de los procesos de ingesta | Terminada |
| 7 | Puntos privados y precio del propietario | Pendiente |
| 8 | Optimizador de recarga | Pendiente |
| 9 | Reservas y registro de sesiones | Pendiente |
| 10 | Monedero y sesiones de pago | Pendiente |
| 11 | Planificador de viajes con paradas de recarga | Pendiente |
| 12 | Asistente de IA (opcional) | Pendiente |
| 13 | Pulido, seguridad y endurecimiento | Pendiente |
| 14 | Redacción de la memoria | Pendiente |

**Tabla 3.6.** Las fases del proyecto y su estado a la fecha de esta memoria; las pendientes
aparecen resaltadas.

Los hitos verificables del proyecto son estos: el primer *commit* del repositorio, el 28 de marzo
de 2026; el cierre de las fases 1 a 4 —autenticación, catálogo y mapa, simulación y rediseño del
cliente— a lo largo del segundo trimestre; y el paso a producción con la fase 5 cerrada, el 4 de
agosto de 2026. Cada una de esas fechas se corresponde con un *commit* o una etiqueta del
repositorio, de modo que el calendario del proyecto puede comprobarse sin depender de lo que afirme
esta memoria. Las fases pendientes no llevan fecha comprometida.

## Riesgos

Una restricción es una condición conocida desde el principio, y todas están en el apartado 3.2. Por
otro lado, un riesgo es un suceso incierto que puede ocurrir o no. Aquí se recogen únicamente los
riesgos cuya respuesta no está ya comprometida en un requisito con criterio de verificación.

| Id | Riesgo | Efecto | Respuesta y estado | Origen |
| --- | --- | --- | --- | --- |
| **R-01** | La siembra del catálogo no termina en plazo o hay que reiniciarla | El mapa se queda sin catálogo completo | Siembra por partes con marca de agua, reanudable sin repetir lo ya traído. Materializado: llevó unos 12 días | 3.2, API de REVE |
| **R-02** | Cambio de formato o caída de la fuente oficial | El catálogo deja de actualizarse | El espejo aísla la aplicación de la fuente: el catálogo se sigue sirviendo, aunque REVE no responda. Se siguen mostrando datos reales, pero las tarifas dejarían de refrescarse y los puntos nuevos no llegarían a detectarse | 3.2, fuente externa única |
| **R-03** | Alcance mayor que el tiempo disponible | Fases sin cerrar y funcionalidades a medio construir | Criterios de aceptación escritos por adelantado y fases ordenadas para que cada una deje la aplicación presentable | 3.2, un solo desarrollador |

**Tabla 3.7.** Riesgos del proyecto.
