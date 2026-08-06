# 7. Funcionalidades de la aplicación

## Lo que funciona hoy

Todo lo que se describe hasta el apartado «Diseñado, no construido» está desplegado en
`s-charge.app` y se usa desde un teléfono. A partir de ahí cambia el tiempo verbal porque cambia
el estatus.

### La aplicación como PWA

El cliente se entrega como *Progressive Web App*: manifiesto de aplicación web y *service
worker*, sin envoltorio nativo y sin tienda. La definición de MDN describe exactamente lo que se
buscaba —una aplicación construida con tecnologías web que se instala en el dispositivo y ofrece
una experiencia equiparable a la de una aplicación específica de plataforma [36]—, y los dos
componentes que lo hacen posible son estándares del W3C [40][37]. En
la práctica el usuario obtiene un icono en la pantalla de inicio, ventana propia sin cromo del
navegador y una pantalla de arranque. Se ha probado en un iPhone y en un Android reales: en iOS
mediante «Añadir a pantalla de inicio» de Safari y en Android con el aviso de instalación nativo
de Chrome.

La alternativa nativa se descartó por aritmética, no por preferencia. Una PWA es un código, un
despliegue y una matriz de pruebas; iOS y Android nativos son dos canales de publicación, dos
cadenas de construcción, dos colas de revisión y dos ecosistemas que hay que mantener al día. Para
un trabajo de una sola persona ese coste no compra nada que la memoria pueda defender, porque la
contribución es la aplicación, no su empaquetado. Envolver la web en un contenedor nativo con
Capacitor habría heredado el peaje de las tiendas sin ganar interfaz nativa.

El diseño es **mobile-first** con 360 px como anchura de referencia, y no por moda: el usuario al
que se dirige está de pie junto a un poste, con el móvil en una mano y el cable en la otra. El
escritorio funciona, pero es el caso derivado.

> **[FIGURA 7.1]** — *La aplicación instalada.* Dos paneles: (a) pantalla de inicio de un iPhone
> real con el icono de S-Charge entre otras aplicaciones; (b) la aplicación abierta en ventana
> autónoma, donde debe verse que no hay barra de direcciones ni controles del navegador.
> **Cómo obtenerla:** captura de pantalla del teléfono tras instalar desde `s-charge.app` con
> Safari; recortar ambas al mismo alto.

### El mapa

`GET /api/points/map` devuelve el catálogo nacional completo como una `FeatureCollection` GeoJSON
reducida: una entidad por punto con su posición, los estándares de conector presentes, la potencia
máxima y el precio mínimo. Son ~13.700 elementos y ~3,5 MB de JSON que viajan en ~503 KB
comprimidos, tras un recorte del 35 % sobre los 772 KB iniciales que consistió en dejar fuera del
documento todo lo que el mapa no pinta.

La vista carga esa colección una sola vez en una fuente de MapLibre GL JS sobre teselas
vectoriales de OpenFreeMap, y el *clustering* lo resuelve la propia biblioteca en GPU. Esa decisión
—desarrollada en el capítulo 4— es la que hace que los filtros sean instantáneos: como el catálogo
entero ya está en el navegador, las etiquetas de filtro (disponibilidad, conector Tipo 2, CCS o
CHAdeMO, y bandas de precio de 0,40 y 0,60 €/kWh) se compilan a expresiones de filtrado de
MapLibre y refiltran la fuente sin una sola petición al servidor. Al abrir, el mapa se centra en la
posición del usuario mediante el control de geolocalización del navegador, que exige permiso
explícito por especificación [48]. Tocar un punto abre una hoja inferior con lo
esencial, y desde la ficha completa el botón «Navegar» abre Google Maps con el destino: la
aplicación no compite con un navegador GPS, delega en el que el usuario ya tiene.

El modelo de cargar una vez tiene su factura y está medida. Lighthouse puntúa 31 en rendimiento
sobre `/map` frente a 94 en `/login`, con FCP de 3,0 s y LCP de 4,5 s ya con la carga útil
recortada. Renderizar 13.700 marcadores no es el problema; descargarlos y analizarlos sí. La
corrección está diseñada y pendiente: añadir un `bbox` opcional al mismo *endpoint*, pedir los
límites visibles en cada `moveend` con rebote, cachear un rectángulo un 50 % mayor que la vista
para no repetir la petición al desplazarse dentro de él, y por debajo de un zoom de ciudad no
pedir nada —eso sería otra vez el país entero— sino invitar a acercarse.

Queda una advertencia sobre el color de los marcadores. Depende de `aggregate_status`, una
agregación del estado de los EVSE de cada punto, pero ninguna fuente alimenta hoy ese estado, de
modo que la agregación devuelve el mismo valor para todo el catálogo y el color no informa de
nada. La disponibilidad no se modela; el capítulo 5 explica por qué.

> **[FIGURA 7.2]** — *El catálogo nacional en una vista.* `/map` a 360 px de ancho, zoom inicial
> de península completa, con los *clusters* visibles y sus recuentos. Es la captura que demuestra
> el volumen del espejo de REVE de un vistazo.
> **Cómo obtenerla:** captura en móvil (o DevTools con viewport de 360 px) nada más abrir `/map`,
> antes de que el control de geolocalización recentre la cámara.

> **[FIGURA 7.3]** — *Filtrado en cliente y selección de un punto.* `/map` a 360 px con la etiqueta
> de conector CCS activa, el *cluster* de Madrid expandido y la hoja inferior de un punto abierta
> sobre el mapa. Deben verse a la vez la barra de etiquetas con una seleccionada y la reducción de
> marcadores respecto a la figura anterior.
> **Cómo obtenerla:** misma sesión que la 7.2; activar la etiqueta CCS, acercarse a Madrid hasta
> que el *cluster* se despliegue y tocar un marcador.

### La ficha de un punto

`/points/:id` presenta el punto tal y como lo entrega el espejo del catálogo: nombre y operador,
estado, precio «desde» —el mínimo de las tarifas de sus conectores—, dirección con código postal y
provincia, horario cuando no es 24 h, y la lista de sus puntos de conexión. Cada EVSE se despliega
en sus conectores con estándar, potencia y tipo de corriente, y a la derecha el precio por kWh de
su tarifa o un guion si no la hay. Todo eso procede de REVE y conserva la jerarquía OCPI con la que
se almacena (capítulo 5). Debajo, dos acciones: «Simular carga» y «Navegar».

> **[FIGURA 7.4]** — *Ficha de un punto real.* `/points/:id` a 360 px sobre un punto con varios
> EVSE, al menos un conector CCS en corriente continua y tarifa conocida, de forma que se vea el
> bloque de precio «desde», el desglose por conector con su €/kWh y los dos botones de acción.
> **Cómo obtenerla:** elegir en producción un punto de un CPO con tarifa sembrada y capturar la
> página completa; si no cabe, dos capturas encadenadas.

### La simulación de recarga

Antes de enchufar, el conductor quiere saber cuánto tardará, cuánta energía añadirá y cuánto le
costará. `POST /api/simulate` responde a las tres preguntas sin depender de ninguna fuente externa
en el momento de la petición.

**Entradas.** Un vehículo del catálogo curado —capacidad útil de batería y potencia máxima en AC y
en DC de 31 modelos habituales del mercado español—, un conector concreto de un punto real, con su
tipo de corriente y su potencia máxima, y una ventana de estado de carga que por defecto va del
20 % al 80 %, el tramo realista de una sesión rápida.

**Potencia de pico.** La carga la limita el eslabón más débil entre coche y poste:

$$P_{\text{pico}} = \min\left(P_{\text{veh}},\; P_{\text{con}}\right)$$

donde $P_{\text{veh}}$ es el máximo del vehículo en AC o en DC según el tipo del conector. Si el
conector es de continua y el coche no la admite, la simulación se rechaza en vez de devolver un
número: la interfaz bloquea el botón de cálculo y avisa antes de pedir nada al servidor.

**Curva de potencia.** La AC se modela plana, porque el cargador de a bordo sostiene su potencia
prácticamente hasta el final. La DC decae por encima de un codo de estado de carga: se mantiene en
el pico hasta el $s_c = 80\ \%$ y desde ahí baja linealmente hasta una cola $\tau = 0,2$ del pico
al 100 %, que es la forma gruesa de la protección de la batería a estado de carga alto:

$$P(s) = \begin{cases}
P_{\text{pico}}, & s \le s_c \\[4pt]
P_{\text{pico}}\left[1 - (1-\tau)\,\dfrac{s - s_c}{100 - s_c}\right], & s > s_c
\end{cases}$$

**Energía y duración.** La energía entregada sale de la batería y de la ventana,
$E = C\,(s_f - s_i)/100$, y no depende de la curva. La duración sí, y se obtiene integrando la
ventana en pasos del 1 % de estado de carga: en cada paso se divide la energía del tramo por la
potencia instantánea, evaluada en el punto medio del paso.

```text
horas ← 0
s     ← soc_inicial
mientras s < soc_final:
    s'    ← min(s + 1, soc_final)
    P     ← potencia_en_soc(pico, tipo, (s + s') / 2)
    horas ← horas + (bateria / 100) · (s' − s) / P
    s     ← s'
```

Para la AC la integración es formalmente innecesaria: con la curva plana todos los términos tienen
el mismo denominador y el resultado es exactamente $E/P_{\text{pico}}$. Para la DC solo aporta algo
cuando la ventana cruza el codo, y entonces los últimos pasos pesan más que los primeros y el
tiempo total queda por encima de $E/P_{\text{pico}}$. Conviene decirlo sin adornos: con la ventana
por defecto de 20 % a 80 % el *taper* no llega a intervenir, y solo aparece si el usuario estira la
carga por encima del 80 %, que es justamente donde la intuición del conductor falla más. La
respuesta incluye además la **potencia media**, $\bar{P} = E/t$, como resumen interpretable de lo
anterior: si es menor que el pico, el usuario está viendo cuánto le cuesta el último tramo.

**Coste.** Se reutiliza la cascada de precios del capítulo 5, sin redefinirla aquí: tarifa real del
conector si el espejo la tiene y, si no, PVPC de la hora más el margen que corresponda al tipo de
corriente. El coste es energía por precio. Lo que sí es propio de esta pantalla es que la respuesta
declara la **procedencia** del precio, y la interfaz la muestra junto a la cifra, de modo que el
usuario sabe si está leyendo un dato o una estimación. Que la información de precio sea clara y
comparable es, además, lo que los conductores europeos señalan como una de las tres cosas que más
valoran de una sesión de recarga pública [2]. La sesión se valora a un único precio
horario, el del instante de la simulación; repartirla entre franjas es competencia del optimizador
(capítulo 8).

**Qué no modela.** Es una predicción basada en especificaciones, no una medida. Fuera quedan la
temperatura de la batería y del ambiente, la degradación por edad, las pérdidas de conversión y el
perfil de *taper* real de cada modelo, que el fabricante rara vez publica y que aquí se sustituye
por una recta con dos constantes documentadas. Sirve para orientar la decisión previa a la carga y
se presenta como estimación, nunca como garantía.

> **PENDIENTE:** contraste del modelo frente a al menos una recarga real medida (energía y
> duración observadas en un punto conocido con un vehículo del catálogo), para poder dar aquí el
> error de la predicción en lugar de declararla sin cuantificar.

> **[FIGURA 7.5]** — *Diálogo de simulación con resultado.* El diálogo «Simular carga» sobre
> `/points/:id` a 360 px, ya calculado: selector de conector y de vehículo, ventana 20–80 %, las
> tres métricas (duración, energía, coste) y la línea inferior con la potencia media y la
> procedencia del precio.
> **Cómo obtenerla:** captura sobre un conector DC con tarifa real y otra sobre uno sin tarifa, para
> que se vea la diferencia de procedencia; si solo cabe una, la de precio estimado.

> **[FIGURA 7.6]** — *Curva de potencia del modelo.* Diagrama con el estado de carga en el eje X
> (0–100 %) y la potencia en el eje Y: una recta horizontal para AC y, para DC, el tramo plano
> hasta el codo del 80 % y la caída lineal hasta el 20 % del pico al 100 %; sombrear la ventana por
> defecto 20–80 % para que se vea que no toca el codo.
> **Cómo obtenerla:** gráfico a generar con los parámetros del propio servicio de simulación
> (`DC_TAPER_KNEE_SOC`, `DC_TAPER_TAIL_FRACTION`); no es una captura de la aplicación.

### El dashboard

La pantalla de entrada saluda al usuario por su nombre y le muestra los puntos que tiene cerca,
obtenidos de su geolocalización y de una consulta acotada por rectángulo al catálogo. Eso es real.

Las cuatro tarjetas de estadísticas —sesiones, kWh, euros y CO₂— y la tarjeta de próxima reserva
son maqueta: se alimentan de un fichero de datos fijos y llevan encima una insignia que dice
«Datos de ejemplo». La insignia es un componente compartido, no un texto suelto, y se aplica a las
tres superficies simuladas de la aplicación. Es una decisión de producto y merece defenderse: una
aplicación no puede presentar como real una funcionalidad que no lo es, ni siquiera en una demo
académica donde nadie iba a comprobarlo. Cada maqueta es además una promesa de borrar algo, porque
el fichero que la alimenta desaparece en la fase que la hace real.

> **[FIGURA 7.7]** — *Datos reales y maqueta etiquetada conviviendo.* `/` a 360 px con el saludo,
> la lista de puntos cercanos con distancias reales y, en el mismo encuadre, la insignia «Datos de
> ejemplo» sobre las tarjetas de estadísticas y sobre la de próxima reserva.
> **Cómo obtenerla:** captura desde el teléfono con el permiso de ubicación ya concedido, en una
> zona con puntos cerca; la insignia debe quedar legible sin ampliar.

## Diseñado, no construido

Lo que sigue tiene modelo de datos pensado, superficie de interfaz esbozada y preguntas abiertas
identificadas, pero no está implementado. Se recoge aquí porque el diseño es trabajo defendible hoy
y porque las preguntas que cada fase deberá cerrar son la mejor prueba de que no se improvisará.

### Puntos de carga privados y precio del propietario

Es la aportación de plataforma y el primer dato del sistema que REVE no proporciona: un usuario da
de alta su propio punto, decide si aparece o no en el mapa público, le pone precio y ve su uso. El
modelo ya reserva la columna de propietario en la tabla de puntos, y nada más. La fase 8 contempla
el alta de extremo a extremo, un interruptor de visibilidad que gobierne la aparición en el mapa,
y un precio del propietario expresado como PVPC más margen o como una cantidad fija por kWh —la
primera forma indexa automáticamente el precio al mercado, la segunda es la que un particular
entiende sin explicaciones.

Tres preguntas quedan por decidir: si el punto de un particular reutiliza la jerarquía OCPI
completa o una forma simplificada, ya que un enchufe de garaje no tiene tres EVSE; cómo fija el
propietario la ubicación, con chincheta en el mapa o geocodificando una dirección; y si la
propiedad se verifica de alguna manera o se acepta bajo declaración.

### Reservas

Reservar una franja horaria en un punto, con detección de solapes para que la reserva signifique
algo. El diseño previsto es un *endpoint* de creación que rechace el solape en la propia base de
datos, el listado y la cancelación de las reservas propias, y la tarjeta de próxima reserva del
dashboard alimentada por fin con datos reales.

La pregunta de fondo es incómoda y conviene formularla tal cual: no tiene sentido reservar un punto
sembrado de REVE, porque ningún operador real va a respetar una reserva hecha en una aplicación con
la que no tiene relación alguna. La opción defendible es restringir las reservas a los puntos dados
de alta por particulares, que es el modelo que siguen las plataformas entre pares existentes
[15], y dejar el resto del catálogo en consulta. Quedan por fijar la granularidad y los
límites —duración de la franja, máximo por reserva, antelación admitida, plazo de cancelación— y
qué significa una reserva para la disponibilidad de un punto cuya disponibilidad real no se modela.

### Registro de sesiones

Un historial de recargas efectivamente ocurridas, con energía, duración y coste, por conductor y
por punto, del que se derivarían las estadísticas del dashboard y el uso que ve el propietario. Hoy
no existe ni la tabla.

El obstáculo no es de programación. Sin hardware y sin flujo de estado, **nada observa una recarga
real**: el sistema no puede saber que ocurrió. Solo hay dos salidas honestas. O el conductor pulsa
iniciar y parar, y la aplicación mide tiempo de reloj y estima la energía; o una reserva completada
se convierte automáticamente en sesión usando la simulación como cifra de energía. La primera
depende de que el usuario coopere; la segunda registra una recarga que quizá no sucedió. Se elija
la que se elija, hay que declararla en la interfaz y en la memoria, porque de ella depende el valor
de todas las cifras agregadas que la aplicación muestre después.

### Monedero simulado

Para que cargar en el punto de otro mueva dinero hace falta un monedero: al conductor se le
descuenta, al propietario se le abona y ambos ven el movimiento. El diseño fija una restricción
desde el principio: **el saldo es un valor derivado de un libro de anotaciones *append-only***,
nunca una columna mutable que se suma y se resta. Un apunte inmutable por movimiento permite
reconstruir cualquier saldo, auditar una discrepancia y hacer idempotente un reintento; una columna
mutable no permite ninguna de las tres cosas y convierte cualquier error de concurrencia en dinero
perdido sin rastro.

No hay pasarela de pago real, ni la habrá dentro del alcance de este trabajo: la recarga de saldo
es simulada y el dinero no existe fuera de la base de datos. Las preguntas abiertas son si los
apuntes se registran como filas con signo o como movimientos por partida doble, qué ocurre cuando
el saldo es insuficiente —bloquear al reservar, bloquear al completar o admitir saldo negativo— y
si la plataforma se queda una comisión, que es el argumento del modelo de negocio (capítulo 13) y
obliga a introducir una tercera cuenta en el libro.
