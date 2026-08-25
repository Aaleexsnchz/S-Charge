# 2. Estado del arte

Este capítulo traza el panorama actual de la recarga de vehículo eléctrico en España: qué productos
y estándares hay hoy y qué resuelve cada uno. Si el capítulo anterior expuso el problema, este
inventaría las soluciones ya disponibles, para fijar el punto de partida sobre el que se construye
S-Charge.

## El registro oficial español

Para contar cuántos puntos de recarga públicos hay en España, el barómetro de ANFAC del segundo
trimestre de 2026 usa Electromaps, y explica por qué: no hay «una plataforma de información oficial
de puntos a nivel nacional» [1]. El documento es del 2 de julio de 2026, siete meses después de que
el Estado publicase su propio mapa. Esa frase describe el sector mejor que cualquier inventario:
hay un registro oficial y, aun así, la asociación de fabricantes cuenta con los avisos de los
usuarios de una aplicación privada.

REVE es el mapa público de puntos de recarga de España. Lo dirige el Ministerio para la Transición
Ecológica y el Reto Demográfico y lo opera Red Eléctrica de España, que se presenta como agente
neutral y no comercial [6]. Su base legal es la Resolución de 2 de abril de 2025, que crea el
Sistema de Gestión y Visualización (SGV) como destino de la información dinámica de la
infraestructura de acceso público, se lo encomienda de forma provisional a Red Eléctrica y obliga a
remitir esa información a los operadores con instalaciones de 43 kW o más [11]; por debajo de ese
umbral es voluntario. Detrás hay una cadena más larga —el artículo 10 del Real Decreto 184/2022,
que obliga a remitir localización, características, disponibilidad y precio al ministerio [12] y la
Orden TED/445/2023, que lo desarrolla mediante el registro RIPREE [13]—, cuyo detalle corresponde
al capítulo 10.

Como producto ofrece consulta de la infraestructura con información dinámica de los operadores
integrados: ubicación, potencia, tipos de conector y, cuando el operador lo remite, disponibilidad
y precio. En diciembre de 2025 Red Eléctrica declaraba unos 40.000 emplazamientos con unos 43.000
conectores, y que el 99 % del territorio peninsular accesible por carretera tiene un punto a menos
de 50 km [6]. La aplicación móvil de ese mismo mes añade el planificador de ruta.

Lo que su documentación describe es consulta y planificación. No hay funcionalidad alguna de
reserva de plaza ni de sesión de pago, y el alta de puntos por particulares queda fuera de su
ámbito por definición: el SGV recoge infraestructura de acceso público remitida por operadores
inscritos en RIPREE [11], y un enchufe de garaje de un particular no encaja ahí.

El propio REVE explica la ausencia. A la pregunta de si permite reservar o pagar responde que no
contempla transacciones comerciales de ningún tipo «dado que la normativa vigente no contempla
dicha opción», y se define como agente neutral sin interés comercial en la recarga [6]. Es una
limitación de estatuto, no de producto: su papel es informativo y su operador es el operador del
sistema eléctrico, una actividad regulada y separada de las liberalizadas. Importa señalarlo porque
descarta al candidato más obvio: quién tiene los mejores datos de infraestructura del país no puede
convertirlos en un servicio de recarga, y no por falta de medios, sino por el papel que le asigna
la norma. Eso no deja el terreno libre —los apartados siguientes muestran productos privados que ya
activan y pagan sesiones—, pero sí significa que el registro oficial no va a ocuparlo. El capítulo
10 desarrolla el argumento y comprueba que la actividad que aquí se propone sí está prevista por
esa misma normativa.

> **[FIGURA 2.1]** — *El mapa oficial REVE* [6].

## Los operadores y la itinerancia

Cada operador —CPO, *Charge Point Operator*— cuenta con su aplicación, con su alta de usuario y sus
propias tarifas. Si cada una de esas redes exigiera darse de alta por separado, el conductor
acabaría con una aplicación por operador. Para evitarlo se montó hace años la itinerancia, que
permite cargar en una red ajena con la cuenta que uno ya tiene: es el mismo mecanismo que el
*roaming* en telefonía, donde la tarjeta de un operador da servicio también en la red de otro.

Zunder declara que la suya da acceso a su red y a las de sus socios de itinerancia «sin requerir
registros adicionales», además de una tarjeta física [5]. IONITY declara 772 emplazamientos de
recarga rápida en 24 países, con aplicación propia que localiza puntos, informa de disponibilidad
en tiempo real e inicia la sesión [4]. Iberdrola y bp pulse, en empresa conjunta, se presentan como
la mayor red ultrarrápida de España y Portugal con más de 2.500 puntos de hasta 400 kW [14].

Para que esa itinerancia funcione, las redes tienen que entenderse entre sí, y de eso se ocupa el
*eRoaming*. El *eRoaming* es la interoperabilidad entre los dos papeles que intervienen en cada
recarga: el CPO, que posee el punto y fija su tarifa, y el prestador de servicios de movilidad
—eMSP, *e-Mobility Service Provider*—, que tiene la cuenta del conductor y le factura la sesión;
son los dos papeles que el Reglamento AFIR define y regula por separado [15]. Lo que ambos se
intercambian es la información de puntos, tarifas y sesiones [16].

Esa conexión admite dos formas: a través de un *hub* que enlaza a la vez a muchos operadores, o de
forma directa entre dos empresas que acuerdan conectarse entre sí, sin pasar por ningún
intermediario central —es la conexión punto a punto o *peer-to-peer*—, hablando un protocolo común
como OCPI. La diferencia práctica está en el número de acuerdos: con un *hub* basta conectarse una
vez para alcanzar a todos sus miembros, mientras que punto a punto cada operador crea sus enlaces
uno a uno.

El modelo de *hub* concentra hoy a los mayores actores: Hubject se describe como la mayor red
internacional de *eRoaming*, con más de 1,1 millones de puntos y más de 3.500 socios en más de 75
países [17]; Gireve declaraba 695.000 puntos en febrero de 2026 y un millón de transacciones
mensuales [18]. Con una sola cuenta se recarga en cientos de redes ajenas: el acceso a la red ya
está resuelto, y a escala continental.

El precio, en cambio, no queda resuelto. Una misma recarga en un mismo poste tiene importes
distintos según el medio con el que se inicie. Y no por falta de norma, porque AFIR ya obliga al
prestador de servicios de movilidad a desglosar todos los componentes del precio antes de iniciar
la sesión [15]. La práctica va por detrás: un estudio elaborado para el Parlamento Europeo en 2026
constata que la información de precios rara vez está disponible antes de iniciar la carga, que las
estructuras tarifarias resultan difíciles de entender y que el importe final depende de si se paga
*ad hoc* al operador o a través de un prestador de servicios de movilidad, en ocasiones con cargos
ocultos [19].

El diferencial está además cuantificado: el precio de un prestador de servicios de movilidad puede
superar el de la recarga *ad hoc* hasta en 12 céntimos por kWh [20]. Las suscripciones van en la
dirección contraria: el Passport de IONITY, la suscripción del propio operador a 12,99 €/mes, deja
el kWh de su red en 0,35 € [4]. Es decir, el precio de una recarga depende de con qué aplicación o
suscripción se pague, no solo del poste. S-Charge muestra el que publica el operador, espejado del
registro oficial.

## Agregadores y planificadores

Los productos de este apartado no poseen infraestructura: son terceros que reúnen en un mapa las
redes de otros. Conviene separar aquí dos cosas que suelen confundirse, porque no todos llegan
igual de lejos: algunos actúan además como eMSP —tienen la cuenta del conductor y le activan y
facturan la sesión—, mientras que otros se limitan a informar o a planificar el viaje, sin venderle
recarga. S-Charge arranca en el segundo grupo, porque activar y cobrar sesiones exige acuerdos
comerciales con cada operador y asumir las obligaciones que AFIR impone a los prestadores de
servicios de movilidad; pasar al primero es, no obstante, la evolución prevista del producto, y el
capítulo 10 examina qué haría falta para ello.

Electromaps, del grupo Wallbox, ordena su propuesta de la siguiente manera: encontrar puntos,
activar sesiones y planificar viajes. Es el único de los tres productos revisados aquí que actúa
también como eMSP. Declara más de 522.864 puntos públicos, ofrece un llavero RFID (Electropass) y
añade comunidad —fotos y comentarios de otros conductores— [3]. Es, además, la fuente del barómetro
citado en 2.1.

PlugShare es una comunidad de conductores con reseñas y fotografías que incluye cargadores
domésticos compartidos [21]. A Better Routeplanner, de Iternio Planning AB, planifica la ruta con
un modelo energético por variante de vehículo que tiene en cuenta temperatura, elevación, pasajeros
y carga, y decide dónde parar, cuánto tiempo y a qué potencia cargar [22].

La comunidad suple lo que el operador no publica mediante las reseñas y el planificador resuelve la
parte energética del viaje.

## La optimización de la recarga doméstica

En España ya hay producto que ayuda a decidir a qué hora conviene cargar en casa según el precio
horario comercial.

LuzPorHora publica el precio horario del PVPC y tiene una herramienta para vehículos eléctricos: el
usuario indica cuánto tiempo necesita cargar y hasta qué hora como máximo, y ella calcula la
ventana continua más barata en intervalos de 30 minutos, comparando «cargar ahora» con «ventana
óptima» [7]. Se queda, eso sí, en la recomendación, ya que indica la ventana óptima, pero no se
conecta al cargador para llevarla a cabo.

Gridio no solo aconseja, ejecuta: programa la recarga según precios de mercado y excedente solar,
emparejándose con el coche a través de los servicios en la nube del fabricante, sin hardware
adicional, en 28 países europeos según declara en la página web [8]. Cerrar el lazo hasta el
control del vehículo, como hace Gridio, queda fuera del alcance de este trabajo —que se limita a
recomendar—, pero es la dirección natural de su evolución futura.

En este caso, ambas herramientas buscan optimizar la carga del vehículo eléctrico, pero ninguna de
ellas va más allá ni aporta otro tipo de funcionalidad.

## La recarga entre particulares

Place to Plug es una plataforma española que conecta conductores con anfitriones —«particulares,
empresas o instituciones»— que ofrecen un enchufe, y le propone al conductor «descubrir, reservar y
recargar» en miles de puntos [9]. Tiene aplicación móvil y un producto B2B para operadores. Cabe
mencionar que también ofrece la recarga en puntos públicos.

El precedente internacional es EVmatch, en Estados Unidos. El dueño de un cargador doméstico lo
publica, otro conductor reserva una franja, recibe la dirección exacta después de reservar y activa
la sesión desde la aplicación, con el precio que fija el anfitrión [23]. Ese detalle de dar la
dirección solo tras la reserva no es cosmético: es la primera decisión de privacidad que impone el
modelo, porque publicar puntos de particulares conlleva, por lo general, publicar domicilios.

EVDC Network sirve de contraste: vende sus propios cargadores y ofrece una aplicación que, además
de esos equipos, localiza y cobra en redes de terceros —declara socios a Ionity, ChargePoint y
Flo— con un token propio de *blockchain*, una moneda digital con la que se paga la recarga [24]. En
este caso, monetizar el punto pasa por comprar su equipo y convertirlo en un nodo de su red.

Hay además literatura reciente sobre percepción pública de la compartición de cargadores
residenciales en California [25], sobre la experiencia de anfitriones reales [26] y sobre la
compartición de puntos privados combinada con servicios *vehicle-to-grid* [27].

## Estándares

OCPI (*Open Charge Point Interface*), de la EVRoaming Foundation, es el protocolo de intercambio
entre plataformas: modela la topología de la infraestructura y los módulos que un CPO y un
prestador de servicios de movilidad necesitan intercambiar —ubicaciones, tarifas, sesiones,
facturación— sobre HTTP y JSON [28]. Es normativo, ya que la Resolución de 2 de abril de 2025 fija
OCPI 2.2.1, 2.2 y 2.1.1 como protocolo de comunicación con el SGV español [11], y el manual técnico
de integración de Red Eléctrica confirma que el sistema está construido sobre OCPI 2.2.1 [29]. Ese
manual deja además una precisión que este trabajo hereda: el «punto de recarga» del vocabulario
regulador español equivale al objeto EVSE de OCPI, y en 2.2.1 no existe un objeto para «estación de
recarga». Cómo se traduce esa topología a tablas es asunto del capítulo 5.

El estándar va por delante de la norma que lo adopta: OCPI 2.3.0 se publicó el 21 de febrero de
2025 y la 3.0 está terminada a la espera de publicación [30], mientras que la resolución española,
de abril de 2025, adopta una versión que llevaba mes y medio superada. El desfase importa poco
aquí: 2.3.0 se construye sobre 2.2.1, la topología emplazamiento → EVSE → conector no cambia y el
sistema español con el que se dialoga habla 2.2.1. De lo que añade —pago directo en el propio
poste, campos fiscales, extensibilidad y un módulo opcional de reservas— solo el último tiene algo
que ver con este trabajo, ya que estandariza calendarios, reservas y penalizaciones por no
comparecer. Tampoco se emplea porque usarlo exigiría un acuerdo con el operador del punto que este
trabajo no tiene, y esa misma ausencia de contraparte es la que descarta reservar aquí: sin
operador que la respete, lo que se registra sobre la réplica propia del catálogo es la sesión que
el conductor dice haber hecho, no una plaza reservada (capítulo 7).

Conviene no confundir OCPI con OCPP (*Open Charge Point Protocol*), de la Open Charge Alliance,
porque actúan en niveles distintos. OCPP conecta cada estación de recarga con el sistema de gestión
de su operador [31]: habla entre el poste y su *backend*. OCPI conecta ese *backend* con las demás
plataformas. Este trabajo no usa OCPP, ya que quien no opera postes no tiene con quién hablarlo.
Por debajo están los estándares físicos que aparecen en los datos. La norma IEC 62196-1:2025 fija
los requisitos generales de clavijas, bases, conectores y tomas para la recarga conductiva [32].

> **[FIGURA 2.2]** — *Dónde habla cada estándar.*

Lo que sí está fijado normativamente es que el tipo de conector es un dato obligatorio: el artículo
20 del Reglamento AFIR obliga a los operadores, desde el 14 de abril de 2025, a poner a disposición
sin coste los datos estáticos —tipo de conector y de corriente, potencia máxima, ubicación— y los
dinámicos —estado operativo, disponibilidad, precio por operación— por una API de acceso libre y no
restringido [15]. Que este sistema no consuma esos datos dinámicos tiene una explicación de
alcance: la obligación recae sobre cada operador por separado, de modo que aprovecharla exigiría
integrarse operador a operador. Conviene añadir que no se ha podido verificar que los principales
operadores españoles publiquen esa interfaz, puesto que no se ha localizado documentación pública
de API conformes al artículo 20. La única vía agregada y documentada que se ha encontrado es el
punto de acceso nacional, y es su API la que limita a cinco peticiones por hora.

## El hueco detectado

Casi todo lo que hace falta para cargar un coche eléctrico en España ya existe. Cargar en cientos
de redes con una sola cuenta funciona desde hace años. Saber a qué hora sale más barato cargar en
casa lo resuelven LuzPorHora y Gridio, y el segundo hasta lo ejecuta. Alquilar el enchufe de un
particular tiene plataforma propia y con reserva. Y calcular qué energía, cuánto tiempo y cuánto
dinero necesita un coche concreto es justo lo que hacen los planificadores de ruta. Ninguna de las
funciones de esta aplicación es una novedad por separado.

Lo que ninguna tiene es la combinación de todas las funcionalidades útiles para un conductor de
vehículos eléctricos. Ahí hay una oportunidad, y es la que ocupa este trabajo: reunir en una sola
aplicación las que hoy obligan a tener varias instaladas. A continuación, vemos una comparación de
algunas aplicaciones de vehículos eléctricos, para ver qué funcionalidades tiene cada una de forma
sencilla.

| Aplicación | Mapa de puntos | Planificación ruta | Estimación coste | Optimización carga | Puntos de particulares | Reserva / inicio de sesión |
| --- | --- | --- | --- | --- | --- | --- |
| REVE | Sí | Sí | No | No | No | No |
| Electromaps | Sí | Solo guía al punto elegido | Solo la tarifa del punto | No | Gestión de cargadores privados para organizaciones | Inicio de sesión |
| Chargemap | Sí | Sí | Sí | No | No | Inicio de sesión |
| Zunder | Sí | Solo indica estaciones de camino como parada | No | No | No, opera su propia red | Inicio de sesión en su red y socios |
| Gridio | No | No | No | Sí | No | Programa carga |
| Place to Plug | Sí | No | Solo la tarifa del punto | No | Sí | Sí |

**Tabla 2.1.** Comparación de capacidades entre aplicaciones.

S-Charge apunta precisamente a esa completitud, y desde los dos lados del problema: quien conduce
resuelve en una sola aplicación dónde cargar, a qué hora sale más barato y cuánto le costará,
mientras que quien gestiona uno o varios puntos los ofrece y los rentabiliza desde la misma. Nada
impide que sea la misma persona, ya que estaría todo unificado.
