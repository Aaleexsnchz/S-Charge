# 1. Introducción

## La recarga pública en España

Un conductor de vehículo eléctrico en España encuentra hoy dónde cargar con relativa facilidad y
puede activar la sesión de carga en casi cualquier red con una sola cuenta. Además, la
infraestructura ha dejado de ser escasa en términos absolutos. Según el barómetro de
electromovilidad de ANFAC, a 30 de junio de 2026 había en España 56.682 puntos de recarga de
acceso público operativos, 3.610 más que al cerrar 2025 [1]. El crecimiento es sostenido, pero la
comparación europea sigue siendo desfavorable: el indicador global de electromovilidad que publica
la asociación sitúa a España en 26,9 sobre 100 frente a 40,1 de la UE, por detrás de países como
Portugal y Francia.

> **[FIGURA 1.1]** — *Índice global de electromovilidad* [1].

En el componente de infraestructura, la brecha también es amplia, 15,4 en España frente a 31,1 en
la UE. Además, solo el 32 % de la red pública supera los 22 kW.

> **[FIGURA 1.2]** — *Indicador de infraestructura de recarga* [1].

El mismo barómetro estima que 17.821 puntos instalados están fuera de servicio, un 23,9 % de todo
lo desplegado; de estar operativos, la cifra pública rondaría los 74.503. ANFAC advierte en el
propio documento que ese estado procede de los reportes de los usuarios de Electromaps, porque no
dispone de una plataforma oficial de información de puntos a escala nacional: es una estimación
sectorial, no una medición oficial.

## El problema

Preguntados por lo que valoran de una recarga pública, los conductores europeos de vehículo
eléctrico de batería citan encontrar la estación plenamente operativa al llegar (88 % la considera
importante o muy importante), no esperar para acceder al punto (88 %) y disponer de información de
precio clara y transparente (84 %) [2]. Ninguna de las tres depende ya de cuántos postes haya
instalados, sino de la aplicación con la que se usa. Actualmente, el mercado de aplicaciones de
recarga no está vacío: está fragmentado.

- **Descubrir puntos y activar la sesión.** Los agregadores publican mapas de cientos de miles de
  puntos y activan la recarga en redes ajenas con una sola cuenta: Electromaps ordena su propuesta
  en encontrar puntos, activar sesiones y planificar viajes, y declara más de 522.864 puntos [3].
  Las aplicaciones de los operadores hacen lo propio sobre su red y la de sus socios de
  itinerancia: IONITY informa de disponibilidad en tiempo real e inicia la sesión, con suscripción
  o pago por uso [4], y Zunder declara acceso a su red y a las de sus socios sin registros
  adicionales [5]. Además, lo habitual es encontrar la tarifa de un punto antes de enchufar un
  vehículo.
- **Planificar un viaje largo.** El mapa oficial del Estado, REVE, calcula el trayecto según la
  capacidad de la batería, el consumo y la potencia de carga del vehículo, y devuelve tiempo
  estimado, coste energético y paradas necesarias [6]; Electromaps también planifica viajes [3].
  El cálculo de cuánta energía, tiempo y dinero para un coche concreto existe también en productos.
- **Elegir la hora más barata para cargar en casa.** LuzPorHora calcula la ventana continua más
  económica contra el precio horario regulado [7]; Gridio, además de calcularla, programa y ejecuta
  la recarga contra precios de mercado y excedente solar, sin hardware adicional [8].
- **Ofrecer el punto propio y cobrar por su uso.** Place to Plug conecta a conductores con
  anfitriones —particulares, empresas o instituciones— que ofrecen su enchufe, con descubrimiento y
  reserva previa [9]. A cambio, los anfitriones pueden gestionar sus puntos de carga de forma
  sencilla y obtener ingresos adicionales cuando otros usuarios los usan.

Comparar precios entre puntos ya lo hacen varios agregadores; lo que no está resuelto es comparar
el coste de la recarga concreta para un coche determinado entre los puntos que uno tiene cerca, y
decidir con esa vista delante.

Ninguna de esas capacidades es, por separado, un problema abierto, y varias aplicaciones reúnen
unas cuantas. Lo que no se ha encontrado es una que las tenga todas. El conductor que las quiere
termina con tres o cuatro instaladas, cada una con su alta de usuario, su mapa y su catálogo de
puntos, teniendo que combinarlas para contar con todas las funcionalidades. La unión que ninguna
hace es además la más útil: la recarga pública y la doméstica viven en herramientas distintas, de
modo que quien optimiza el precio horario no conoce el catálogo de puntos y quien conoce el
catálogo no razona sobre el precio de la electricidad ni permite gestionar el punto propio.

Del lado público, REVE es la pieza más completa. Está dirigida por el Ministerio para la Transición
Ecológica y el Reto Demográfico y operado por Red Eléctrica de España como agente neutral y no
comercial [6], su función es informativa y su operador tiene prohibido por estatuto competir en el
mercado. No reserva, no propone cuándo cargar y no da cabida al punto de un particular, que por
definición no está en el registro de operadores: es un espacio que el actor público no puede
ocupar.

El problema del que parte esta memoria es, por tanto, de completitud y no de invención: no se ha
encontrado ninguna aplicación lo bastante completa como para que un conductor la elija y desinstale
las demás. El capítulo 2 sitúa el panorama actual y, producto a producto, se compara quién cubre
qué.

## Qué hace este trabajo

Este trabajo propone esa aplicación —S-Charge— y la lleva construida tan lejos como alcanza un
trabajo de fin de máster desarrollado por un solo alumno con tiempo y recursos limitados. No todo
llega a producto: una parte está diseñada y desarrollada, otra queda diseñada y sin implementar, y
algunas piezas se quedan en idea y se recogen al final, entre las mejoras futuras. La frontera
entre unas y otras está marcada en todo momento: el capítulo 7 la traza funcionalidad por
funcionalidad y el 13 evalúa lo conseguido.

Que el catálogo quede incompleto no convierte el resultado en una maqueta, porque la prioridad ha
sido levantar una base funcional estable y desplegada antes que acumular funcionalidades. Algunas
quedan a medio camino, y se señala dónde; la decisión responde a que sobre una base sólida se puede
seguir construyendo, mientras que un catálogo amplio sin cimientos no se sostiene. Lo implementado
trabaja sobre datos reales —el catálogo nacional de puntos de recarga del registro oficial y la
ingesta diaria del precio regulado horario de la electricidad—, y la simulación de una parada se
calcula con las especificaciones del vehículo y del conector, no con valores de ejemplo.

La misma exigencia se aplica a cómo se entrega el sistema. La aplicación está desplegada y
accesible públicamente bajo HTTPS, es instalable en el móvil como aplicación web progresiva y se
publica mediante una cadena de integración y despliegue continuos, con la autenticación, los
límites de tasa y el endurecimiento del servidor que describe el capítulo 6. Ahí está la ambición
de fondo: dejar el modelo de datos, la arquitectura y el despliegue ya resueltos y en
funcionamiento, de manera que completar el producto sea seguir desarrollando y no empezar de nuevo.
Este capítulo y el siguiente dibujan hacia dónde va S-Charge y dónde se sitúa en el panorama
actual, mientras que el resto de la memoria se centra en qué se ha desarrollado y cómo.

## Motivación

Lo que mueve este trabajo es cubrir una necesidad concreta de quien conduce un eléctrico en España,
ya que hoy reparte entre varias aplicaciones lo que debería poder resolver en una. Es una necesidad
real, no una carencia teórica, y está al alcance de una aplicación bien planteada.

A eso se suma el atractivo de construir algo desde cero y hacerlo bien: tener una idea, plantearla
y llevarla de principio a fin. Concebir el producto, decidir su arquitectura, escribir el backend y
el cliente, desplegarlo en un servidor propio bajo HTTPS y dejarlo accesible a cualquiera. El reto
no está en que funcione una demostración, sino en que cada pieza esté resuelta con criterio y el
conjunto se sostenga.

El terreno, eso sí, impone sus condiciones. La materia prima es pública —el catálogo nacional de
puntos de recarga de REVE [6] y la curva horaria del PVPC (Precio Voluntario para el Pequeño
Consumidor) que publica Red Eléctrica [10]—, pero no toda llega en las mismas condiciones. La del
PVPC es abierta, no pide autenticación y puede consultarse sin restricciones; la del registro
nacional de puntos de recarga (REVE) exige clave de API y admite cinco peticiones por hora, un
techo que descarta consultarla en vivo y obliga a dar un rodeo: construir el sistema alrededor de
una copia local que se siembra poco a poco y se refresca por partes. Esto ha supuesto un reto:
diseñar contra lo que hay y no contra lo que convendría tener obliga a replantear el modelo de
datos y el proceso de actualización desde el primer día, además de encontrar una solución que
funcione dentro de ese margen. El capítulo 5 la desarrolla.

## Objetivos

**Objetivo general.** Diseñar, construir de extremo a extremo, desplegar y argumentar S-Charge, una
PWA (*Progressive Web App*) que unifique en una sola aplicación la gestión de la recarga de vehículo
eléctrico en España.

A continuación, se enumeran los objetivos específicos del trabajo:

| Id | Objetivo específico | Criterio de verificación |
| --- | --- | --- |
| **OE1** | Construir la aplicación de extremo a extremo: cliente instalable en el móvil, API propia, base de datos y sistema de identidad, con la cadena de comprobaciones automatizada. | La aplicación se instala y se usa en un móvil real; la API sirve las funcionalidades descritas en el capítulo 7; las comprobaciones de estilo, tipos y pruebas pasan en cada cambio. |
| **OE2** | Localizar una fuente de datos válida para el catálogo nacional de puntos de recarga y resolver cómo explotarla dentro de sus condiciones de acceso. | Volumen de operadores, puntos, EVSE (*Electric Vehicle Supply Equipment*), conectores y tarifas almacenados y consultables desde la API, y siembra completada de forma desatendida. |
| **OE3** | Reunir en un único flujo capacidades que hoy están repartidas entre productos distintos. | Funcionalidades desarrolladas e integradas en la aplicación. |
| **OE4** | Desplegar el sistema en un entorno real y dejarlo accesible a cualquiera en un dominio propio bajo HTTPS, con entrega automatizada desde el repositorio. | La aplicación responde en `https://s-charge.app`, se instala desde el entorno desplegado y un cambio llega al servidor sin intervención manual (capítulo 8). |
| **OE5** | Valorar cómo encajaría el producto en el mercado y estudiar su viabilidad: hueco que ocupa frente a la oferta existente, coste de operación, modelo de ingresos, camino de escalado y límites conocidos del sistema. | Los capítulos 8 y 11 presentan costes reales, economía unitaria y los puntos de ruptura de un único servidor, y el capítulo 9 recoge lo logrado frente a lo declarado. |

**Tabla 1.1.** Objetivos específicos y criterio con el que se evalúa cada uno.

## Alcance y límites

Cuatro límites afectan a la lectura de todo lo demás, y son distintos de la frontera entre lo
construido y lo diseñado: estos quedan fuera incluso del diseño.

- **La disponibilidad en tiempo real no se modela.** El sistema no recibe estado de los puntos
  desde sus operadores, de modo que la ocupación que muestra el mapa no procede de la
  infraestructura, sino de las sesiones que los usuarios inician en la propia
  aplicación. Es una simulación coherente entre usuarios, no un reflejo del estado real, y así se
  declara; el apartado 3.2 explica la decisión de diseño y el capítulo 5, el modelo que la
  sostiene.
- **El monedero es simulado.** El movimiento económico entre conductor y propietario de un punto se
  registra en un libro de apuntes interno; no hay pasarela de pago ni dinero real en ninguna parte
  del sistema.
- **No hay acuerdo con operadores ni integración con el hardware.** Este trabajo no tiene acuerdo
  con ningún operador de puntos de recarga ni actúa como prestador de servicios de movilidad, de
  modo que no hay interlocutor a quien pedir una reserva o el arranque de una sesión. El capítulo
  10 sitúa esta aplicación frente a las capas que quedan por debajo, OCPP entre ellas, y examina
  qué haría falta para cruzar esa frontera.
- **El despliegue es un único servidor.** El escalado horizontal se argumenta —dónde se rompe
  primero y qué lo sustituye en cada escalón— pero no se construye: la configuración concreta y ese
  argumento están en el capítulo 8.

Y un límite más, este sobre lo que se puede afirmar: cada capacidad que reúne esta propuesta tiene
ya al menos un producto que la sirve en el mercado español, de modo que la contribución está en la
combinación y en haber planteado la idea y llevarla a cabo a través de un sistema desplegado.
