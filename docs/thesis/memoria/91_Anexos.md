# Anexos

Los anexos recogen el material que respalda el cuerpo de la memoria pero que, incorporado a él,
lo haría ilegible. Cada uno indica de dónde se genera, para que ninguno se escriba a mano dos
veces.

> **PENDIENTE:** salvo el anexo A, que ya está escrito, este fichero es el guion de los anexos y no
> su contenido. Cada apartado lleva la instrucción de cómo producirlo. El anexo B es obligatorio y
> debe cumplimentarlo el autor.

---

## Anexo A — Fichas de especificación de casos de uso

Se recogen aquí las fichas de los casos de uso que no se reproducen en el capítulo 3, con la misma
plantilla que la del CU-10: identificador, actores, precondiciones y postcondiciones, flujo
principal numerado, flujos alternativos, excepciones y requisitos relacionados.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-01 — Crear una cuenta y verificarla |
| **Actor principal** | Usuario |
| **Actores secundarios** | Servicio de correo |
| **Precondiciones** | El visitante no tiene sesión activa y la dirección de correo no pertenece a ninguna cuenta verificada |
| **Postcondiciones** | Existe una cuenta en estado no verificado y se ha enviado a esa dirección un enlace de verificación; la cuenta no puede iniciar sesión hasta usarlo |
| **Flujo principal** | 1. El visitante abre el formulario de registro.<br>2. Introduce una dirección de correo y una contraseña de al menos 15 caracteres.<br>3. El sistema valida el formato del correo y la longitud de la contraseña, y comprueba que la dirección no está en uso.<br>4. El sistema crea la cuenta como no verificada, guarda la contraseña derivada y envía el enlace de verificación.<br>5. El usuario abre el enlace; el sistema marca la cuenta como verificada y habilita el acceso. |
| **Flujo alternativo A — el correo ya está registrado** | En el paso 3 la dirección pertenece a una cuenta existente. El sistema no crea nada y responde con un mensaje que no revela si la cuenta existe, invitando a recuperar el acceso. |
| **Flujo alternativo B — contraseña insuficiente** | En el paso 3 la contraseña no alcanza los 15 caracteres. El formulario señala el campo y la petición no llega al servidor. |
| **Excepción — enlace caducado o ya usado** | En el paso 5 el enlace no es válido. El sistema lo rechaza y ofrece reenviar la verificación a la misma dirección. |
| **Requisitos relacionados** | RF-01 |

**Tabla A.1.** Especificación detallada del CU-01.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-02 — Iniciar sesión y recuperar el acceso |
| **Actor principal** | Usuario |
| **Actores secundarios** | Google como proveedor de identidad, servicio de correo |
| **Precondiciones** | Existe una cuenta verificada asociada a la dirección de correo |
| **Postcondiciones** | El usuario tiene sesión activa y las rutas bajo `/api` responden con su identidad |
| **Flujo principal** | 1. El usuario abre la pantalla de acceso.<br>2. Introduce correo y contraseña, o elige entrar con su cuenta de Google.<br>3. El sistema comprueba las credenciales o valida la identidad devuelta por el proveedor.<br>4. Si la dirección de Google coincide con una cuenta existente, el sistema enlaza ambas identidades sin duplicar el usuario.<br>5. El sistema abre la sesión y lleva al usuario al mapa. |
| **Flujo alternativo A — acceso perdido** | El usuario solicita restablecer la contraseña. El sistema envía un enlace de un solo uso y, al usarlo, permite fijar una nueva y continúa por el paso 5. |
| **Flujo alternativo B — cuenta sin verificar** | En el paso 3 la cuenta existe, pero no ha verificado el correo. El sistema deniega el acceso y ofrece reenviar la verificación. |
| **Excepción — credenciales inválidas** | El sistema responde con un error genérico, sin distinguir si falla la dirección o la contraseña, y no revela la existencia de la cuenta. |
| **Requisitos relacionados** | RF-02, RF-03 |

**Tabla A.2.** Especificación detallada del CU-02.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-03 — Localizar puntos de recarga en el mapa y filtrarlos |
| **Actor principal** | Conductor |
| **Actores secundarios** | Copia local del catálogo, servicio de mapas |
| **Precondiciones** | El usuario tiene sesión activa y la copia local contiene puntos en el área consultada |
| **Postcondiciones** | Ninguna: la consulta no modifica el estado del sistema |
| **Flujo principal** | 1. El conductor abre el mapa.<br>2. El sistema solicita al servidor los puntos del área visible y los presenta agrupados por proximidad.<br>3. El conductor desplaza o amplía el mapa y el sistema repite la consulta para la nueva área.<br>4. El conductor aplica filtros de disponibilidad, tipo de conector o banda de precio.<br>5. El sistema resuelve el filtrado sobre los puntos ya cargados, sin volver a pedir datos al servidor. |
| **Flujo alternativo A — ningún punto cumple los filtros** | En el paso 5 el resultado está vacío. El mapa lo indica y ofrece deshacer los filtros aplicados. |
| **Flujo alternativo B — geolocalización denegada** | En el paso 1 el navegador no concede la posición. El mapa se centra en una vista por omisión y el resto del flujo continúa igual. |
| **Excepción — el servidor no responde** | El mapa conserva los puntos ya cargados y advierte de que los datos pueden no estar actualizados. |
| **Requisitos relacionados** | RF-04, RF-05 |

**Tabla A.3.** Especificación detallada del CU-03.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-04 — Consultar la ficha de un punto |
| **Actor principal** | Conductor |
| **Actores secundarios** | Copia local del catálogo |
| **Precondiciones** | El usuario tiene sesión activa y el punto existe en la copia local del catálogo |
| **Postcondiciones** | Ninguna: la consulta no modifica el estado del sistema |
| **Flujo principal** | 1. El conductor selecciona un punto en el mapa o en el panel de inicio.<br>2. El sistema recupera operador, dirección, conectores con su potencia, tarifa y estado.<br>3. La ficha presenta esos datos y ofrece las acciones disponibles sobre el punto: simular la recarga, abrir la navegación y reservarlo. |
| **Flujo alternativo A — el punto no publica tarifa** | La ficha lo indica expresamente y ninguna pantalla posterior muestra coste para ese conector: la simulación devuelve energía y duración con el coste vacío, sin sustituirlo por una estimación (capítulo 5). |
| **Flujo alternativo B — datos incompletos en el registro oficial** | Los campos ausentes se presentan vacíos y etiquetados como tales, sin sustituirlos por valores supuestos. |
| **Excepción — el punto ya no está en el catálogo** | Si el identificador no aparece en la copia local, el sistema informa de que el punto no está disponible y devuelve al mapa. |
| **Requisitos relacionados** | RF-04, RF-06 |

**Tabla A.4.** Especificación detallada del CU-04.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-05 — Simular una recarga en un punto |
| **Actor principal** | Conductor |
| **Actores secundarios** | Catálogo de vehículos, tarifa del punto, curva PVPC |
| **Precondiciones** | El usuario tiene sesión activa; el punto existe en el catálogo y tiene al menos un conector con potencia declarada |
| **Postcondiciones** | Ninguna: la simulación no escribe en la base de datos ni deja rastro en el estado del usuario |
| **Flujo principal** | 1. El conductor abre la ficha del punto (CU-04) y solicita simular la recarga.<br>2. El sistema presenta el diálogo con los conectores del punto y la lista de modelos de vehículo.<br>3. El conductor elige modelo, conector y el rango de carga de partida y llegada (por defecto, del 20 % al 80 %).<br>4. El sistema determina la potencia efectiva como el mínimo entre la que admite el vehículo y la que entrega el conector, e integra la carga aplicando la reducción de potencia propia de la corriente continua por encima del 80 %.<br>5. El sistema valora la energía resultante con la tarifa del punto, franja a franja sobre la ventana que ocupa la recarga.<br>6. El sistema devuelve energía entregada, duración y coste, y los muestra en el diálogo. |
| **Flujo alternativo A — el punto no publica tarifa** | En el paso 5 no hay tarifa asociada al conector. El sistema devuelve energía y duración y deja el coste vacío, sin sustituirlo por ninguna estimación (capítulo 5). El flujo continúa en el paso 6. |
| **Flujo alternativo B — rango de carga inválido** | En el paso 3 la carga de llegada es menor o igual que la de partida. El sistema rechaza la petición con un error de validación y el diálogo señala el campo; no se llega al paso 4. |
| **Excepción — sesión caducada** | Cualquier paso posterior al 1 puede encontrar la sesión expirada; la API responde 401 y el cliente lleva al usuario a la pantalla de acceso. |
| **Requisitos relacionados** | RF-07, RF-08, RF-09 |

**Tabla A.5.** Especificación detallada del CU-05.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-06 — Abrir la navegación hasta el punto |
| **Actor principal** | Conductor |
| **Actores secundarios** | Aplicación de mapas del dispositivo |
| **Precondiciones** | El usuario tiene sesión activa, la ficha del punto está abierta y el punto tiene coordenadas válidas |
| **Postcondiciones** | Ninguna en el sistema: el control pasa a la aplicación de mapas del dispositivo |
| **Flujo principal** | 1. El conductor solicita la navegación desde la ficha del punto.<br>2. El sistema compone el enlace de destino con las coordenadas del punto.<br>3. El dispositivo abre su aplicación de mapas con el destino ya fijado. |
| **Flujo alternativo A — el dispositivo no tiene aplicación de mapas asociada** | El enlace se abre en el navegador, que resuelve el destino con el servicio de mapas por omisión. |
| **Flujo alternativo B — el punto carece de coordenadas** | La acción aparece deshabilitada en la ficha y el sistema muestra únicamente la dirección postal. |
| **Excepción — el sistema operativo bloquea la apertura** | El sistema presenta la dirección del punto para copiarla manualmente. |
| **Requisitos relacionados** | RF-06 |

**Tabla A.6.** Especificación detallada del CU-06.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-07 — Ver los puntos más próximos desde el panel de inicio |
| **Actor principal** | Conductor |
| **Actores secundarios** | Geolocalización del dispositivo, copia local del catálogo |
| **Precondiciones** | El usuario tiene sesión activa |
| **Postcondiciones** | Ninguna: la consulta no modifica el estado del sistema |
| **Flujo principal** | 1. El conductor abre el panel de inicio.<br>2. El sistema solicita la posición al dispositivo.<br>3. El sistema ordena los puntos de la copia local por distancia y presenta los más cercanos con su distancia y su estado.<br>4. Al elegir uno, el conductor pasa a su ficha (CU-04). |
| **Flujo alternativo A — geolocalización denegada** | El panel omite la lista por proximidad, lo advierte y ofrece abrir el mapa completo. |
| **Flujo alternativo B — ningún punto en el radio inicial** | El sistema amplía el radio de búsqueda y lo indica junto a la lista. |
| **Excepción — posición imprecisa** | El sistema presenta la lista advirtiendo del margen de error de la posición recibida. |
| **Requisitos relacionados** | RF-05 |

**Tabla A.7.** Especificación detallada del CU-07.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-08 — Dar de alta un punto propio, fijarle precio y gestionar su disponibilidad |
| **Actor principal** | Propietario |
| **Actores secundarios** | Catálogo propio, curva PVPC |
| **Precondiciones** | El usuario tiene sesión activa y declara disponer de un punto de recarga propio |
| **Postcondiciones** | El punto queda registrado a nombre del propietario con su visibilidad, su precio y su horario; si es público y está abierto, aparece en el mapa del resto de usuarios y admite reservas dentro de ese horario |
| **Flujo principal** | 1. El propietario abre la gestión de sus puntos y solicita añadir uno.<br>2. Indica ubicación, tipo de conector y potencia.<br>3. Decide si el punto es visible para el resto de usuarios o solo para él.<br>4. Fija el precio como PVPC más un margen o como precio fijo por kWh.<br>5. Define el horario en el que el punto admite reservas.<br>6. El sistema valida los datos, registra el punto y lo incorpora al catálogo. |
| **Flujo alternativo A — punto privado** | En el paso 3 el propietario lo mantiene oculto. El punto no aparece en el mapa ni admite reservas de terceros, y sigue sirviendo para simular y programar sus propias cargas. |
| **Flujo alternativo B — precio indexado al PVPC** | En el paso 4 el precio se expresa como margen sobre la curva horaria, de modo que varía cada hora sin intervención del propietario. |
| **Flujo alternativo C — cierre puntual del punto** | El propietario cierra el punto desde su gestión con efecto inmediato: deja de admitir nuevas reservas y desaparece de las búsquedas de terceros. Las reservas ya confirmadas se mantienen salvo que el propietario las cancele expresamente. |
| **Excepción — ubicación duplicada** | El sistema rechaza el alta si las coordenadas coinciden con las de otro punto ya registrado por el mismo usuario. |
| **Requisitos relacionados** | RF-10 |

**Tabla A.8.** Especificación detallada del CU-08.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-09 — Optimizar la carga en función del precio de la electricidad |
| **Actor principal** | Propietario |
| **Actores secundarios** | Curva PVPC, catálogo de vehículos |
| **Precondiciones** | El usuario tiene sesión activa, dispone de al menos un punto propio registrado y la curva horaria del día está disponible |
| **Postcondiciones** | Queda una carga programada en la ventana elegida y el sistema conserva el ahorro estimado frente a cargar de inmediato. La programación actúa sobre la red simulada y no envía ninguna orden a un cargador físico |
| **Flujo principal** | 1. El propietario elige uno de sus puntos y solicita programar una carga.<br>2. Indica la energía que necesita y la hora a la que el vehículo debe estar disponible.<br>3. El sistema recorre la curva horaria del PVPC hasta esa hora y localiza la ventana continua más barata capaz de entregar esa energía a la potencia del punto.<br>4. El sistema muestra la ventana propuesta, su coste y el ahorro frente a empezar de inmediato.<br>5. El propietario confirma y el sistema programa la carga en esa ventana. |
| **Flujo alternativo A — la energía no cabe antes de la hora de salida** | En el paso 3 no existe ninguna ventana suficiente. El sistema propone la más barata posible, advierte de que la carga quedará incompleta e indica qué energía se alcanzaría. |
| **Flujo alternativo B — sin curva del día disponible** | El sistema recurre al histórico del día anterior y marca el coste y el ahorro como estimados. |
| **Excepción — la ventana propuesta ya ha pasado** | Si al confirmar la ventana ha quedado atrás, el sistema recalcula con la hora actual antes de programar la carga. |
| **Requisitos relacionados** | RF-08, RF-11 |

**Tabla A.9.** Especificación detallada del CU-09.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-11 — Consultar el historial de sesiones y el uso de los puntos propios |
| **Actor principal** | Conductor · Propietario |
| **Actores secundarios** | Registro de sesiones, libro de apuntes del monedero |
| **Precondiciones** | El usuario tiene sesión activa |
| **Postcondiciones** | Ninguna: la consulta no modifica el estado del sistema |
| **Flujo principal** | 1. El usuario abre el historial.<br>2. Como conductor, el sistema lista sus sesiones con fecha, punto, energía, duración y coste.<br>3. Como propietario, el sistema añade el uso de sus puntos con la energía entregada y el importe abonado.<br>4. El usuario selecciona una sesión y consulta su detalle junto con los apuntes del monedero asociados. |
| **Flujo alternativo A — sin sesiones registradas** | El historial lo indica y ofrece volver al mapa para localizar un punto. |
| **Flujo alternativo B — reserva caducada sin carga** | La reserva no utilizada figura en el historial marcada como caducada, sin energía y con la señal perdida como único importe. |
| **Excepción — sesión en curso** | La sesión abierta se presenta al principio de la lista con su estado y sin importe definitivo hasta su liquidación. |
| **Requisitos relacionados** | RF-14, RF-15, RF-17 |

**Tabla A.10.** Especificación detallada del CU-11.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-12 — Iniciar una sesión de carga y liquidarla |
| **Actor principal** | Conductor |
| **Actores secundarios** | Propietario del punto, libro de apuntes del monedero, reloj del sistema |
| **Precondiciones** | El usuario inicia una sesión y su monedero cubre la retención estimada; el punto está libre en ese momento o el conductor tiene sobre él una reserva vigente (CU-10) |
| **Postcondiciones** | La sesión queda registrada con energía, duración y coste; el libro de apuntes recoge la retención, la liquidación y la liberación del sobrante, y el punto vuelve a estar libre |
| **Flujo principal** | 1. El conductor inicia la sesión desde la ficha del punto: directamente si el punto está libre, o dentro del margen de su reserva si la tiene.<br>2. El sistema estima el coste de la carga prevista y retiene ese importe en el monedero como garantía.<br>3. La carga transcurre en la aplicación, con la duración calculada a partir de la potencia efectiva del punto y del vehículo.<br>4. El conductor da por terminada la sesión, o el sistema la cierra al alcanzarse la energía prevista.<br>5. El sistema liquida la energía consumida al precio del punto, añade el recargo por ocupación si el vehículo ha seguido conectado tras el final de la carga, descuenta la señal si la sesión venía de una reserva, y libera el resto de la retención.<br>6. El libro de apuntes adeuda al conductor el importe liquidado y abona al propietario el suyo; ambos lo ven en su historial. |
| **Flujo alternativo A — interrupción anticipada** | En el paso 4 el conductor detiene la carga antes de lo previsto. El sistema liquida únicamente la energía entregada hasta ese momento y libera el resto de la retención. |
| **Flujo alternativo B — retención insuficiente** | Si durante el paso 3 el consumo previsto supera la garantía retenida, el sistema amplía la retención con el saldo disponible o cierra la sesión al alcanzar el límite, avisando al conductor. |
| **Excepción — saldo insuficiente al iniciar** | En el paso 2 el monedero no cubre la retención. El sistema no abre la sesión, conserva la reserva y solicita recargar el monedero. |
| **Requisitos relacionados** | RF-13, RF-14, RF-15, RF-19 |

**Tabla A.11.** Especificación detallada del CU-12.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-13 — Planificar un viaje con sus paradas de recarga |
| **Actor principal** | Conductor |
| **Actores secundarios** | Servicio de mapas, copia local del catálogo, catálogo de vehículos |
| **Precondiciones** | El usuario tiene sesión activa, ha elegido un modelo de vehículo y declara su carga de partida; existe trayecto por carretera entre origen y destino |
| **Postcondiciones** | Ninguna sobre el estado del sistema: el plan es un resultado de cálculo que el conductor puede guardar como lista de paradas |
| **Flujo principal** | 1. El conductor introduce origen, destino y carga de partida.<br>2. El sistema obtiene el trayecto del servicio de mapas y lo divide en tramos.<br>3. El sistema estima el consumo de cada tramo a partir de la capacidad y el consumo del modelo elegido.<br>4. Cuando la carga restante estimada baja del margen de reserva, el sistema busca en la copia local los puntos próximos a ese tramo y elige el que añade menos desvío y menos coste.<br>5. El sistema calcula en cada parada la energía a recuperar y el tiempo de carga con el mismo modelo del CU-05, y continúa hasta el destino.<br>6. El sistema presenta el plan completo: paradas, energía, tiempo de carga y coste total. |
| **Flujo alternativo A — el destino se alcanza sin paradas** | El sistema lo indica y muestra la carga estimada a la llegada, sin proponer ningún punto intermedio. |
| **Flujo alternativo B — tramo sin puntos alcanzables** | El sistema señala el tramo como no cubierto, propone la última parada posible y advierte de que el viaje no puede completarse con ese vehículo. |
| **Excepción — el servicio de mapas no responde** | El sistema comunica que no puede calcular el trayecto y no ofrece un plan parcial que pudiera inducir a error. |
| **Requisitos relacionados** | RF-04, RF-07, RF-09, RF-18 |

**Tabla A.12.** Especificación detallada del CU-13.

| Campo | Contenido |
| --- | --- |
| **Identificador** | CU-14 — Resolver consultas en lenguaje natural |
| **Actor principal** | Conductor · Propietario |
| **Actores secundarios** | Modelo de lenguaje, API propia del sistema |
| **Precondiciones** | El usuario tiene sesión activa y la consulta puede resolverse con datos del catálogo y del propio usuario |
| **Postcondiciones** | Ninguna: el asistente consulta y no escribe en el estado del sistema |
| **Flujo principal** | 1. El usuario escribe una pregunta en lenguaje natural sobre puntos, precios o sus propias sesiones.<br>2. El sistema traduce la pregunta a una o varias consultas de la API propia, acotadas a la identidad del usuario.<br>3. El sistema redacta la respuesta con los datos devueltos e indica la pantalla donde el usuario puede comprobarlos. |
| **Flujo alternativo A — la pregunta excede los datos disponibles** | El asistente lo declara y no completa la respuesta con estimaciones ajenas a las fuentes del sistema. |
| **Flujo alternativo B — pregunta ambigua** | El asistente pide la precisión que falta antes de consultar, en lugar de elegir una interpretación por su cuenta. |
| **Excepción — la API rechaza la consulta** | El asistente responde que no puede acceder al dato y remite a la pantalla correspondiente, sin reintentar la consulta con menos restricciones. |
| **Requisitos relacionados** | RF-03, RF-16 |

**Tabla A.13.** Especificación detallada del CU-14.

## Anexo B — Declaración de uso de IA generativa

**Obligatorio.** Formulario oficial de la Universidad Carlos III de Madrid, cumplimentado y
firmado por el autor, declarando los usos descritos en el capítulo 12.

> **PENDIENTE:** descargar el formulario vigente de la guía de la biblioteca de la UC3M sobre IA
> generativa en el TFM, cumplimentarlo marcando los usos que el capítulo 12 describe —asistencia
> a la redacción sobre documentación técnica propia previa, y asistencia al desarrollo del
> software— y adjuntarlo aquí.

## Anexo C — Manual de instalación y despliegue

Cómo levantar el sistema desde un clon del repositorio y cómo se despliega en producción:
requisitos previos, configuración, arranque de la base de datos, migraciones, ejecución de
backend y frontend, y el procedimiento de despliegue y de vuelta atrás.

**Cómo generarlo:** condensar `README.md` (arranque rápido y comandos), `docs/setup/deployment.md`
(aprovisionamiento del servidor) y `docs/operations.md` (operación, copias de seguridad, acceso
a la base de datos de producción y actualizaciones mayores de PostgreSQL). No reescribir: extraer
y ordenar.

## Anexo D — Esquema completo de la base de datos

Diagrama entidad-relación y descripción de las doce tablas —`users`, `oauth_account`, `cpos`,
`charging_points`, `evses`, `connectors`, `tariffs`, `tariff_elements`, `vehicles`,
`electricity_prices`, `reve_etl_cursor` y `reve_unmirrored_connectors`— con sus columnas, tipos,
claves y restricciones.

**Cómo generarlo:** a partir de `backend/app/models/` y del histórico de migraciones de
`backend/alembic/versions/`. El diagrama puede obtenerse con una herramienta de ingeniería
inversa sobre la base de datos real, o dibujarse a partir de las relaciones declaradas en los
modelos.

## Anexo E — Catálogo de la API REST

Los endpoints publicados, con método, ruta, parámetros, esquema de respuesta y códigos de error.

**Cómo generarlo:** directamente desde `openapi.json`, que está versionado en la raíz del
repositorio y que CI mantiene sincronizado con el código. Es el anexo más barato de producir y
el que documenta la superficie contractual del sistema.

## Anexo F — Registro de decisiones de arquitectura

Los dieciséis registros de decisión, cada uno con su decisión, sus razones, sus consecuencias y
**las alternativas rechazadas**, que son la parte que demuestra criterio.

**Cómo generarlo:** desde `docs/decisions/`. Conviene una tabla índice al principio —
identificador, título, fase, estado — y a continuación el contenido de cada registro. Si el
espacio aprieta, la tabla índice más los cinco registros más significativos (`be-0001` espejo
frente a proxy, `be-0002` disponibilidad no modelada, `be-0003` el precio en el conector,
`auth-0002` sesión por cookie, `infra-0001` despliegue) cubren lo esencial.

## Anexo G — Galería de pantallas

Las capturas de la aplicación que no caben en el cuerpo, comentadas. El capítulo 7 marca las que
van en el cuerpo; el resto vive aquí.

**Cómo generarlo:** capturas a 360 px de ancho sobre el despliegue de producción, con una cuenta
de demostración. Incluir al menos: las seis pantallas de autenticación, el mapa con distintos
filtros activos, la ficha de punto completa, el diálogo de simulación con su resultado, el
dashboard y las pantallas con maqueta etiquetada «datos de ejemplo» — estas últimas importan,
porque documentan la disciplina de no presentar como real lo que no lo es.

## Anexo H — Skills de agente y reproducibilidad

Qué *skills* de agente se usaron durante el desarrollo, para qué sirvió cada una en este
proyecto concreto, y cómo se reproducen desde el fichero de anclaje de versiones. Complementa el
capítulo 12.

**Cómo generarlo:** desde `docs/thesis/skills.md` y `skills-lock.json`.

## Anexo I — Glosario de siglas y términos

**Cómo generarlo:** recorrer la memoria recogiendo las siglas desarrolladas en su primera
aparición. Como mínimo: AFIR, BEV, CCS, CPO, CSP, DC/AC, eMSP, ETL, EVSE, HSTS, IEC, JWT, OCPI,
OCPP, ODS, PVPC, PWA, RGPD, SoC, SPA, TLS, VPS.

---

## Anexo opcional — Catálogo de vehículos

Los 31 modelos sembrados, con capacidad útil de batería y potencia máxima en AC y en DC.
Incluir solo si la memoria necesita cuerpo; su valor es documentar el criterio de curación de
datos descrito en el capítulo 5.

**Cómo generarlo:** desde `backend/scripts/seed_vehicles.py` o consultando la tabla `vehicles`.
