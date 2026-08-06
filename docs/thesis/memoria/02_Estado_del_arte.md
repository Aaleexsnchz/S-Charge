# 2. Estado del arte

Para contar cuántos puntos de recarga públicos hay en España, el barómetro de ANFAC del segundo
trimestre de 2026 usa Electromaps, y lo justifica diciendo que lo hace «ante la falta de una
plataforma de información oficial de puntos a nivel nacional» [1]. El documento está
fechado el 2 de julio de 2026, siete meses después de que el Estado publicase su propio mapa. Esa
frase describe el estado del arte mejor que cualquier inventario: existe un registro oficial, y aun
así la asociación del sector cuenta con datos aportados por usuarios de una aplicación privada.

## El registro oficial español

REVE es el mapa público de puntos de recarga de España. Lo dirige el Ministerio para la Transición
Ecológica y el Reto Demográfico y lo opera Red Eléctrica de España, que se describe como agente
neutral y no comercial actuando bajo la dirección del ministerio [3]. Su base legal directa
es la Resolución de 2 de abril de 2025 de la Dirección General de Política Energética y Minas, que
crea el Sistema de Gestión y Visualización (SGV) como destino de la información dinámica de la
infraestructura de acceso público, lo encomienda con carácter provisional a Red Eléctrica y obliga a
remitir esa información a los operadores con instalaciones de 43 kW o más [6]. Por
debajo de ese umbral la remisión es voluntaria. Detrás hay una cadena más larga —el artículo 10 del
Real Decreto 184/2022, que obliga a remitir localización, características, disponibilidad y precio
al ministerio [7], y la Orden TED/445/2023, que lo desarrolla a través del registro RIPREE
[8]—, cuyo detalle corresponde al capítulo 12.

Como producto, REVE ofrece consulta de la infraestructura pública con información dinámica para los
operadores integrados: ubicación, potencia, tipos de conector y, cuando el operador lo remite,
disponibilidad y precio en tiempo real. En diciembre de 2025 Red Eléctrica declaraba unos 40.000
emplazamientos con unos 43.000 conectores, y que el 99 % del territorio peninsular accesible por
carretera tiene un punto de recarga a menos de 50 km [3]. La aplicación móvil lanzada ese
mismo mes añade un planificador de ruta que calcula el trayecto según la capacidad de batería, el
consumo y la potencia de carga del vehículo, y devuelve tiempo estimado, coste energético y paradas
necesarias.

Lo que la documentación pública de REVE describe es consulta y planificación. No se localizó
descripción alguna de reserva de plaza, de sesión de pago ni de alta de puntos por particulares, y
esto último queda fuera de su ámbito por construcción: el SGV recoge infraestructura de **acceso
público** remitida por operadores dados de alta en RIPREE [6], categoría en la que un
enchufe de garaje particular no encaja.

Queda una cuestión abierta que conviene declarar aquí. El *endpoint*
`https://www.mapareve.es/api/external/v1` existe y responde, pero devuelve `HTTP 403 Missing
Authentication Token` sin credenciales, y en la comprobación del 5 de agosto de 2026 no se localizó
documentación pública de esa interfaz ni un aviso legal legible: la web es una aplicación de página
única y no sirve texto a un cliente automatizado. En qué condiciones puede reutilizarse ese catálogo
es materia del capítulo 12, que lo trata como pregunta sin respuesta y no la resuelve por
conveniencia.

> **[FIGURA 2.1]** — *El mapa oficial REVE.* Captura de `https://mapareve.es` con el mapa de España
> a escala nacional y la ficha de un punto de recarga abierta, de modo que se vean los campos que el
> registro oficial publica (operador, potencia, tipo de conector y, si el operador lo remite, estado
> y precio). Está aquí para que el lector vea el punto de partida contra el que se compara el resto
> del capítulo.
> **Cómo obtenerla:** navegador de escritorio, ventana a 1.280 px, capturar el mapa y ampliar la
> ficha lateral. Indicar en el pie la fecha de la captura.

## Las aplicaciones de los operadores

El patrón dominante del mercado español es que cada operador de puntos de recarga —CPO, *Charge
Point Operator*— publica su propia aplicación, con su propia alta de usuario y su propia tarifa. El
conductor que recorre el país acaba con varias cuentas y varios métodos de pago, uno por red.

Sobre marcas concretas, este trabajo se limita a lo que pudo leerse en su fuente. Zunder se presenta
como operador de referencia de recarga ultrarrápida en el sur de Europa y declara que su aplicación
da acceso tanto a su red propia como a las de sus socios de itinerancia «sin requerir registros
adicionales», además de una tarjeta física, eZCard [9]. De las demás aplicaciones que operan en
España no se describe aquí ninguna función: sus sitios no se pudieron recuperar con garantías —el de
Chargemap devuelve `HTTP 402` a un cliente automatizado— y afirmar que a una aplicación le falta algo
porque no aparece en su portada es ausencia de evidencia, no evidencia de ausencia.

La respuesta del sector a esa fragmentación es la itinerancia entre operadores. Hubject se describe
como la mayor red internacional de *eRoaming* y declara más de 1,1 millones de puntos de recarga,
más de 3.500 socios B2B y más de 75 países [10]; Gireve declaraba 695.000 puntos en febrero de
2026 y un millón de transacciones mensuales [11]. Ahora bien, la itinerancia resuelve el
problema del operador —que su cliente pueda recargar fuera de su red con el contrato que ya tiene—,
no el del ciudadano que quiere comparar antes de decidir sin ser cliente de nadie.

## Agregadores y plataformas

Electromaps, del grupo Wallbox, ordena su propuesta en tres verbos: encontrar puntos, activar
sesiones y planificar viajes. El sitio declara más de 522.864 puntos de recarga públicos, ofrece un
llavero RFID (Electropass) y funciones de comunidad —fotos y comentarios de otros conductores—
[12]. Es además la fuente de datos del barómetro con el que se abre el capítulo.

PlugShare es una comunidad de conductores con reseñas y fotografías que, según fuentes secundarias
coincidentes, incluye cargadores domésticos compartidos [13]. A Better Routeplanner, de
Iternio Planning AB, resuelve el problema del viaje largo: según las mismas fuentes secundarias,
planifica la ruta con un modelo energético por variante de vehículo que tiene en cuenta temperatura,
elevación, pasajeros y carga, y decide dónde parar, cuánto tiempo y a qué potencia [14]. No está
verificado que optimice contra el precio de la electricidad, y por tanto no se afirma.

La comunidad suple la información que el operador no publica —si el poste funcionaba ayer, si el aparcamiento estaba lleno—, y la planificación de ruta
resuelve la parte energética del viaje. Ninguno de los tres se pudo verificar operando sobre el
precio horario minorista de la electricidad, que es la señal económica que el conductor español tiene
delante cuando decide a qué hora carga.

## Place to Plug y la recarga entre particulares

Place to Plug es una plataforma española que se define como conexión entre conductores de vehículo
eléctrico y anfitriones —«particulares, empresas o instituciones»— que ofrecen un enchufe para
recargar, y cuya propuesta al conductor es «descubrir, reservar y recargar» en miles de puntos
[5]. Ofrece aplicación móvil y un producto B2B para operadores. Es el único producto
verificado en esta investigación que combina las dos piezas que definen el modelo de este trabajo:
punto aportado por un particular y reserva previa.

Conviene decirlo sin rodeos, porque de ello depende la credibilidad del resto de la memoria: **la
recarga entre particulares no es una idea nueva y este trabajo no puede reclamar haberla inventado**.
Lo que no se pudo confirmar de Place to Plug es su modelo económico —cómo se retribuye al anfitrión y
si es él quien fija la tarifa—, de modo que tampoco se afirma nada sobre ello.

El precedente internacional es EVmatch, en Estados Unidos. Según varias fuentes secundarias
coincidentes, el propietario de un cargador doméstico lo publica, otro conductor reserva una franja
horaria, recibe la dirección exacta **después** de la reserva y activa la sesión desde la aplicación,
con el precio fijado por el anfitrión [15]. Ese detalle de revelar la dirección solo tras la
reserva no es cosmético: es la primera decisión de privacidad que impone el modelo, porque publicar
puntos de particulares significa publicar domicilios.

Un tercer producto ocupa una posición distinta y conviene situarlo por contraste. EVDC Network
vende sus propios cargadores y los acompaña de una aplicación con acceso a redes de itinerancia y
de un token propio en cadena de bloques; su reclamo comercial —*"the parking space that earns for
you"*— es exactamente el de rentabilizar una plaza infrautilizada [16]. La diferencia con este
trabajo no está en la idea sino en la puerta de entrada: allí monetizar el punto **pasa por
comprar el equipo del fabricante**, mientras que aquí la plataforma es software sobre un catálogo
que ya existe y sobre el punto que el propietario ya tenga, sea de la marca que sea. De su sitio
solo se pudo comprobar la venta de equipos, la aplicación de itinerancia y el token; **el
mecanismo concreto de compartición entre particulares, la reserva y la cobertura en España no se
confirmaron**, así que no se le atribuyen aquí.

La literatura reciente acompaña a estos productos. Hay trabajo publicado sobre percepción pública de
la compartición de cargadores residenciales en California [17], sobre la experiencia de
anfitriones reales [18] y sobre la compartición de puntos privados combinada con servicios
*vehicle-to-grid* [19]. Se citan por su objeto y no por sus resultados: su texto completo
no se consultó para este trabajo.

## Estándares

OCPI (*Open Charge Point Interface*), mantenido por la EVRoaming Foundation, es el protocolo de
intercambio entre plataformas: modela la topología de la infraestructura de recarga y los módulos que
un CPO y un prestador de servicios de movilidad necesitan intercambiar —ubicaciones, tarifas,
sesiones, detalles de facturación— sobre HTTP y JSON [20]. Su relevancia aquí es directa y
normativa: la Resolución de 2 de abril de 2025 fija OCPI, en sus versiones 2.2.1, 2.2 y 2.1.1, como
protocolo estándar de comunicación con el SGV español [6], y el manual técnico de
integración de Red Eléctrica confirma que el sistema está construido sobre OCPI 2.2.1, con la versión
declarada en la ruta del *endpoint* y autenticación por cabecera `Authorization: Token` [21].
Ese mismo manual deja una precisión que este trabajo hereda: el «punto de recarga» del vocabulario
regulador español tiene equivalencia con el objeto EVSE de OCPI, y en OCPI 2.2.1 no existe un objeto
para «estación de recarga». Cómo se traduce esa topología a tablas es asunto del capítulo 5.

OCPP (*Open Charge Point Protocol*), de la Open Charge Alliance, es el estándar adyacente que este
trabajo **no** usa, y explicar por qué aclara dónde se sitúa. OCPP es el protocolo de comunicación
entre las estaciones de recarga y el sistema de gestión que las controla [22]: habla entre el
poste y su *backend*, y ha llegado a norma internacional: la edición 3 de OCPP 2.0.1 fue aprobada
como IEC 63584 en 2024, y la versión 2.1 de 2025 añade control de recursos energéticos distribuidos
y V2G. OCPI, en cambio, habla entre plataformas. Una aplicación que no opera hardware no tiene con
quién hablar OCPP.

Por debajo de ambos están los estándares físicos que aparecen en los datos. IEC 62196-1:2022, en su
edición 4.0, fija los requisitos generales de clavijas, bases, conectores y tomas para la recarga
conductiva de vehículos eléctricos [23]. Las fuentes consultadas sitúan el conector Tipo 2 en
la parte 2 de esa misma norma y las configuraciones Combo (CCS) y CHAdeMO en la parte 3, pero solo la
parte 1 se verificó en la web oficial del IEC; los demás números se recogen con esa reserva y sin
atribuirles especificaciones eléctricas. Lo que sí está fijado
normativamente es que el tipo de conector es un dato obligatorio: el artículo 20 del Reglamento AFIR
obliga a los CPO, desde el 14 de abril de 2025, a poner a disposición sin coste alguno los datos
estáticos —tipo de conector y de corriente, potencia máxima, ubicación— y los dinámicos —estado
operativo, disponibilidad, precio por operación— a través de una API de acceso libre y no restringido
[24].

> **[FIGURA 2.2]** — *Dónde habla cada estándar.* Diagrama de tres capas en horizontal: (1) poste de
> recarga; (2) sistema de gestión del CPO; (3) plataformas —SGV/REVE, plataformas de itinerancia y
> prestadores de servicios de movilidad—. La flecha entre (1) y (2) rotulada **OCPP**; las flechas
> entre (2) y (3), **OCPI 2.2.1**. Marcar con un recuadro discontinuo la capa 3 como el único nivel
> en el que opera una aplicación que no posee hardware. Justifica en una imagen la distinción
> OCPP/OCPI que el texto acaba de establecer.
> **Cómo obtenerla:** diagrama a dibujar en draw.io o Mermaid, en blanco y negro, sin iconografía de
> marca.

## Lo que dice la literatura

Cuatro líneas de trabajo tocan este problema, y cada una aporta algo distinto.

La **optimización de la recarga frente a señales de precio o de red** es la más madura. El protocolo
descentralizado de *valley filling* de Gan, Topcu y Low [25] es la referencia clásica; la
revisión de García-Villalobos y colaboradores, de un grupo español, sistematiza las estrategias de
recarga inteligente en redes de distribución [26]; hay trabajo específico sobre
reducción de cargos por demanda en emplazamientos no residenciales [27] y sobre marcos de
redes de recarga adaptativas [28]. Casi toda esta literatura supone **control sobre la potencia
entregada**: el algoritmo decide a qué ritmo carga cada vehículo. Una aplicación que no opera los
postes no tiene esa palanca, y su margen de actuación se reduce a recomendar cuándo y dónde. Es una
diferencia de planteamiento, no de grado, y condiciona lo que puede formularse en el capítulo 8.

La **planificación de infraestructura** —dónde conviene instalar puntos, con qué modelos se decide—
tiene revisiones amplias [29][30]. Explica por qué la red está donde está, que es
contexto útil, pero no ayuda al conductor que ya está delante de un poste.

Los **conjuntos de datos de sesiones reales** son la tercera línea. ACN-Data, de Caltech, publicó más
de 30.000 sesiones de recarga en el puesto de trabajo y modeló la distribución de sus parámetros con
mezclas de gaussianas [31]; después han aparecido alternativas urbanas y armonizadas a escala
de ciudad [32][33]. ACN-Data es además un *camino no tomado* de este proyecto, y las
razones se explican en el capítulo 5.

La cuarta es la **demanda y las barreras percibidas**, donde conviene leer con cuidado. La ansiedad
de autonomía se cita a menudo como barrera objetiva, cuando el trabajo académico que la estudia con
ese nombre es explícitamente crítico con el concepto y lo trata como retórica reaccionaria
[34]. Las encuestas europeas apuntan a otra cosa: el precio del vehículo sigue siendo la
barrera principal, la preocupación por la disponibilidad de recarga pública ha disminuido desde 2023,
y lo que sigue siendo crítico es el acceso a recarga fiable cerca del domicilio, en particular para
los hogares **sin plaza privada** [35]. Preguntados por lo que importa en una sesión de
recarga pública, los conductores europeos señalan encontrar la estación plenamente operativa, esperar
poco o nada, y disponer de «información de precio clara y transparente» [2]. Ese último punto
y el del hogar sin plaza privada son, respectivamente, el argumento de la comparación de precios y el
del modelo entre particulares.

## El hueco

| Producto | Descubrimiento de puntos | Cobertura nacional (España) | Reserva | Puntos de particulares | Simulación por modelo de vehículo | Optimización por precio horario |
| --- | --- | --- | --- | --- | --- | --- |
| REVE [3] | Sí | Sí, registro oficial | No verificado | Fuera de ámbito (solo acceso público) | Parcial: planificador de ruta por batería, consumo y potencia | No verificado |
| Apps de CPO (verificado: Zunder [9]) | Sí, red propia y socios de itinerancia | No: red propia y acuerdos | No verificado | No verificado | No verificado | No verificado |
| Electromaps [12] | Sí, con comunidad | Internacional; declara >522.864 puntos | No verificado | No verificado | No verificado | No verificado |
| PlugShare [13] | Sí, con comunidad | Internacional | No verificado | Sí, según fuentes secundarias | No verificado | No verificado |
| ABRP [14] | Sí, según fuentes secundarias | Internacional | No verificado | No verificado | Sí, según fuentes secundarias | No verificado |
| Place to Plug [5] | Sí | No verificado | Sí | Sí | No verificado | No verificado |
| EVmatch [15] | Sí, según fuentes secundarias | EE. UU. | Sí, según fuentes secundarias | Sí, según fuentes secundarias | No verificado | No verificado |
| EVDC Network [16] | Sí | No verificado | No verificado | Sí, pero condicionado a comprar su equipo | No verificado | No verificado |
| Este trabajo | Sí | Sí, espejo del registro oficial | Diseñada, no construida | Diseñados, no construidos | Sí | Diseñada, no construida |

**Tabla 2.1.** Capacidades verificadas de las alternativas analizadas. «No verificado» significa que
la investigación bibliográfica no pudo comprobar esa capacidad en una fuente abierta, no que el
producto carezca de ella.

La tabla tiene más celdas sin verificar que llenas: buena parte de estos productos son aplicaciones
cerradas que no se pueden auditar desde fuera. Aun así, el mapa que dibuja basta. El registro
oficial cubre el catálogo nacional y la
planificación de ruta; Place to Plug cubre el eje de particulares con reserva; los agregadores cubren
descubrimiento y comunidad; ABRP cubre el modelo energético del viaje. Ninguna alternativa verificada
reúne las cuatro cosas, y en particular ninguna se pudo verificar operando sobre la curva de precio
horario de la electricidad, que es la única señal que convierte «cargar más barato» en una decisión
concreta.

Ahí encaja este trabajo, y en esos términos acotados: no en inventar la recarga entre particulares
—ya existe, en España y con producto en el mercado— sino en reunir en una sola aplicación el catálogo
nacional espejado del registro oficial, los puntos aportados por particulares, la simulación por
modelo de vehículo y la optimización contra el precio real de la electricidad. La última columna de
la tabla dice también qué parte de esa combinación está construida hoy y qué parte está diseñada y
argumentada pero no implementada; el capítulo 7 detalla la frontera.
