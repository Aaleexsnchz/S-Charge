# 7. Funcionalidades de la aplicación

## Lo que funciona hoy

Todo lo que se describe hasta el apartado «Diseñado, no construido» está desplegado en
`s-charge.app` y se usa desde un teléfono. A partir de ahí cambia el tiempo verbal porque cambia
el estatus.

### La aplicación como PWA

El cliente se entrega como *Progressive Web App*: manifiesto de aplicación web y *service
worker*, sin envoltorio nativo y sin tienda. La definición de MDN describe exactamente lo que se
buscaba —una aplicación construida con tecnologías web que se instala en el dispositivo y ofrece
una experiencia equiparable a la de una aplicación específica de plataforma [33]—, y los dos
componentes que lo hacen posible son estándares del W3C [37][34]. En
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
explícito por especificación [46]. Tocar un punto abre una hoja inferior con lo
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

**Coste.** Se valora con lo que el operador publica y con nada más (capítulo 5). **La sesión se
tarifica por la ventana que ocupa, no por el instante en que se consulta**: una recarga dura horas
y las franjas cambian a hora en punto, así que cada paso de carga paga la franja que cubre el
minuto en que llega su energía. El reparto es minuto a minuto y no por intersección de intervalos,
porque en corriente continua la potencia decae por encima del codo y la energía no se distribuye
uniformemente entre las franjas que la sesión cruza. La respuesta devuelve el **precio efectivo**
—el coste dividido entre la energía—, no una franja concreta: citar una sola para una carga que
cruzó dos sería un número que ningún contador marca. Sobre un conector real, la misma recarga de
42 kWh cuesta 13,21 € empezando a las 10:00 y 14,86 € empezando a las 21:00, un 12,5 % de
diferencia que depende solo de cuándo se enchufa. Si el conector no tiene precio publicado, la
casilla de coste **se queda vacía** y se dicen igualmente duración y energía. Que la información de
precio sea clara y comparable es, además, lo que los conductores europeos señalan como una de las
tres cosas que más valoran de una sesión de recarga pública [2]. Elegir *cuándo* cargar sigue
siendo competencia del optimizador (más adelante en este mismo capítulo); aquí solo se valora bien
una ventana que el conductor ya ha decidido.

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
> tres métricas (duración, energía, coste) y la línea inferior con la potencia media y el precio
> efectivo de la carga.
> **Cómo obtenerla:** captura sobre un conector con tarifa y otra sobre uno sin ella, para que se
> vea que en el segundo el coste queda vacío en lugar de estimado; si solo cabe una, la del
> conector sin tarifa, que es la decisión que se defiende.

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
[23], y dejar el resto del catálogo en consulta. Quedan por fijar la granularidad y los
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
si la plataforma se queda una comisión, que es el argumento del modelo de negocio (capítulo 11) y
obliga a introducir una tercera cuenta en el libro.

## Optimización de la carga

Un conductor llega a casa a las siete de la tarde, enchufa y vuelve a salir a las siete de la
mañana. Necesita 30 kWh y su punto entrega 7,4 kW: unas cuatro horas de carga dentro de una ventana
de doce. Las ocho restantes son holgura, y la holgura vale dinero, porque la electricidad no cuesta
lo mismo a las diez de la noche que a las cuatro de la madrugada. Cuándo debe correr la carga, y
cuánto se ahorra frente a enchufar y empezar, es lo que la fase 9 contempla responder en
`POST /api/recommend`. **Queda formulado, no implementado**; aquí no hay ninguna cifra medida.

La funcionalidad se dirige a un punto que el usuario posee, y esa restricción es de sentido, no de
alcance. En un poste ajeno el precio lo fija el operador, es plano a lo largo del día y no hay curva
contra la que programar, y quien ha parado a repostar quiere marcharse, no esperar seis horas a que
ceda el mercado. La curva del PVPC es el precio que paga un consumidor doméstico en su acometida.
Las dos entradas ya existen: la energía objetivo sale de la simulación descrita arriba y la curva, del
servicio de precios (capítulo 5).

### Formulación

Se discretiza el intervalo entre el instante actual y la hora de salida en $T$ franjas de duración
$\Delta t$, con la hora como granularidad natural: es la que sirve la API de REE y la que almacena
la tabla de precios. Cada franja $t \in \{1, \dots, T\}$ tiene un precio conocido $c_t$ en €/kWh,
el vehículo necesita $E$ kWh y la potencia máxima por franja es
$P_{max} = \min(P_{punto}, P_{coche})$, el mismo eslabón más débil que aplica la
simulación. La variable de decisión $e_t$ es la energía entregada en la franja $t$.

$$\min_{e_1,\dots,e_T} \sum_{t=1}^{T} c_t\, e_t
\qquad \text{sujeto a} \qquad
\sum_{t=1}^{T} e_t = E,
\qquad 0 \le e_t \le P_{max}\,\Delta t$$

El problema es factible si $E \le T\,P_{max}\,\Delta t$; cuando no lo es, la respuesta correcta no
es un horario sino cuánta energía cabe antes de la salida.

#### El caso sin contigüidad

Así escrito es un programa lineal con una restricción de igualdad y cotas por variable, y su óptimo
es **voraz**: se ordenan las franjas por precio ascendente y se llenan a tope hasta agotar $E$, con
a lo sumo una parcialmente llena. Es la mochila fraccionaria, y el argumento de intercambio es
inmediato: mover energía de una franja cara a otra más barata que no esté llena baja el coste sin
violar ninguna restricción.

La consecuencia práctica pesa más que el resultado: **no hace falta un solucionador de programación
lineal** para un problema cuya solución cerrada cabe en diez líneas.

#### Una única ventana contigua

Si se exige que la carga ocurra de un tirón, el problema cambia de naturaleza. La ventana dura
$n = \lceil E / (P_{max}\Delta t) \rceil$ franjas y solo hay $T - n + 1$ posiciones. Dentro de una
ventana fija el reparto óptimo sigue siendo voraz: como todas las franjas comparten la misma cota,
se llenan al máximo $n-1$ de ellas y el resto $r = E - (n-1)\,P_{max}\Delta t$ va a la más cara de
las $n$. El coste de la ventana que empieza en $i$ es

$$C_i \;=\; P_{max}\Delta t \sum_{t=i}^{i+n-1} c_t \;-\; \left(P_{max}\Delta t - r\right)
\max_{i \le t \le i+n-1} c_t$$

y sus dos piezas se obtienen en tiempo constante por ventana: la suma con sumas prefijas, el máximo
con una cola monótona. El recorrido es lineal en $T$. Toda solución contigua es factible en el
problema sin contigüidad, luego el voraz nunca es peor; la diferencia entre ambos es medible y la
evaluación debe publicarla en vez de darla por despreciable.

#### Las decisiones que la fase debe cerrar

**Ventana contigua o franjas partidas.** Partir es óptimo por construcción y la curva del PVPC
tiene muchos días dos valles que no son adyacentes. En contra: un horario partido es difícil de
verificar para el usuario, no se expresa en el temporizador de una toma doméstica ni en la
programación horaria del vehículo —que es como se ejecutaría mientras no haya control sobre el
hardware— y una sesión interrumpida no siempre se reanuda sola. La propuesta es contigua por
defecto, con el plan partido aparte y su ahorro adicional explícito.

**La potencia del vehículo restringe o la energía se toma como dada.** Tomar el mínimo entre punto
y vehículo reutiliza una regla ya implementada y datos que el catálogo de 31 vehículos contiene; en
una toma doméstica el límite suele ser el cargador de a bordo del coche, no la instalación, e
ignorarlo produciría ventanas más cortas que las reales. A cambio obliga a tener un vehículo
seleccionado. La propuesta es tomar $E$ y $P_{max}$ de la simulación cuando hay vehículo y
conector, y admitir que se introduzcan a mano cuando no.

El modelo supone además que la energía se coloca libremente hasta la cota: cierto con una curva de
potencia plana, falso bajo el *taper* de la corriente continua, como se vio en la simulación. Un punto doméstico es
de corriente alterna, justo el caso donde la suposición se sostiene.

### Pseudocódigo

```text
VORAZ  (franjas partidas)
  orden   <- indices 1..T ordenados por c_t ascendente
  e       <- vector de ceros
  restante<- E
  para t en orden mientras restante > 0:
      e_t      <- min(P_max * dt, restante)
      restante <- restante - e_t
  devolver e, coste = suma(c_t * e_t)

VENTANA DESLIZANTE  (una sola ventana contigua)
  n <- techo(E / (P_max * dt))
  r <- E - (n-1) * P_max * dt
  S <- sumas prefijas de c
  para i en 1..T-n+1:
      pico    <- max(c_i .. c_{i+n-1})            # cola monotona, O(1) amortizado
      coste_i <- P_max*dt * (S_{i+n-1} - S_{i-1}) - (P_max*dt - r) * pico
  devolver el i de coste minimo
```

### Complejidad y tamaño real del problema

El voraz es $O(T \log T)$ por la ordenación y la ventana deslizante es $O(T)$. Con la hora como
franja, una noche son doce y un día entero veinticuatro: a esa escala la diferencia es teórica,
ambos terminan en microsegundos y el coste de la petición lo domina la lectura de la curva en la
base de datos.

De ahí la conclusión honesta del capítulo: **la dificultad no está en la optimización, está en los
datos**. Los precios se guardan por instante de inicio de hora y se consultan en hora local de
Madrid, de modo que los dos días del año en que cambia la hora tienen 23 o 25 franjas y no 24. Y un
horizonte que cruza la medianoche necesita un día que puede no estar publicado: el precio del día
siguiente no aparece antes de las 20:15 [47] y la API de REE devuelve un error del servidor
para un día que aún no lo está. Las dos respuestas defendibles son truncar el horizonte en la
última hora publicada y decirlo, o rechazar la petición.

### La respuesta prevista

El diseño previsto para `POST /api/recommend` es devolver la ventana recomendada —inicio, fin y
energía por franja—, su coste estimado, una o dos alternativas (el plan partido y la ventana más
barata si el usuario pudiera salir más tarde) y, sobre todo, **el ahorro frente a cargar ahora**:
el mismo cálculo empezando en el instante de la petición. Esa cifra es la que da sentido a la
funcionalidad, y si resulta ser de céntimos, decirlo también es parte del trabajo. Como en la
simulación, el cálculo se apoya en el PVPC realmente almacenado para cada franja, no en una
proyección: si falta la curva del día, no hay recomendación que dar.

> **[FIGURA 8.1]** — *La ventana óptima sobre la curva real de un día.* Gráfica de barras con las
> 24 franjas horarias del PVPC de un día concreto ya almacenado (€/kWh en el eje vertical, hora
> local de Madrid en el horizontal), con la ventana recomendada sombreada, la ventana equivalente
> que empezaría al enchufar marcada en otro tono, y ambos costes anotados junto al ahorro entre
> ellas. **Cómo obtenerla:** debe generarse con datos reales de la tabla `electricity_prices`
> —histórico disponible desde el 1 de enero de 2026—, no con una curva inventada; basta un guion de
> Matplotlib sobre el volcado de un día representativo. Elegir un día con diferencial claro entre
> valle y pico e indicar la fecha en el pie.

### Dónde queda esto frente a la literatura

La programación de recarga frente a una señal de precio es un problema estudiado y resuelto: hay
revisiones canónicas de las estrategias de recarga inteligente en redes de distribución
[48], formulaciones del *valley filling* como protocolo descentralizado sobre
flotas que negocian su perfil con una señal común [49], marcos de coordinación de muchos
vehículos bajo la restricción física de una infraestructura compartida [38][50] y
variantes para los cargos por demanda en emplazamientos no residenciales [51].

Ninguna de esas dificultades aparece aquí. Este problema tiene **un vehículo, un punto, ninguna
restricción de red y un precio exógeno**, lo que lo reduce a un programa lineal de libro cuya
solución voraz se conoce desde mucho antes que los vehículos eléctricos. La aportación no es
algorítmica: es aplicar un resultado conocido a datos españoles reales. Un límite: si muchos
usuarios optimizaran a la vez contra la misma curva el valle se desplazaría, y esa realimentación
es lo que los protocolos descentralizados modelan [49] y este diseño no.

### Cómo se evaluará

La evaluación no necesita usuarios ni sesiones reales: se ejecuta enteramente sobre el histórico
del PVPC almacenado desde el 1 de enero de 2026.

1. Una rejilla de perfiles cruza tres energías objetivo —de la simulación de tres vehículos del
   catálogo sobre la ventana por defecto de 20 % a 80 %— con tres potencias domésticas (3,7, 7,4
   y 11 kW) y dos pares de llegada y salida.
2. Para cada día del histórico y cada perfil se calculan tres costes: cargar al llegar, cargar en
   la mejor ventana contigua y cargar con el reparto voraz.
3. Se reportan la media y la distribución del ahorro en € por sesión y en porcentaje, la fracción
   de días en que no alcanza un umbral que lo haga relevante, y la brecha entre ventana contigua y
   reparto partido.
4. Aparte, como comprobación del algoritmo y no del ahorro, el voraz se contrasta con un
   solucionador lineal de referencia sobre instancias aleatorias: una prueba de propiedad barata y
   la forma honesta de sostener que la implementación calcula el óptimo.

> **PENDIENTE:** ejecutar la evaluación descrita una vez implementada la fase 9 y rellenar aquí el
> ahorro medio y su distribución por perfil, la brecha entre ventana contigua y reparto partido, y
> la fracción de días en que el ahorro es despreciable. Hasta entonces este capítulo no contiene
> ninguna cifra de ahorro, ni debe contenerla.

## Asistente de IA

La fase 12 no ha empezado y **el conjunto concreto de funcionalidades no está decidido**. Lo que sí
lo está, y es lo que se defiende aquí, es la forma que tendría: una capa de lenguaje natural
**sobre las APIs que la aplicación ya tiene** —puntos, simulación, recomendación, precios,
reservas— usadas como herramientas. Ninguna fuente de datos nueva, ningún modelo entrenado, ningún
dato que no pase antes por un *endpoint* existente. El contrato de esa API está versionado en el
repositorio como `openapi.json` (capítulo 4), así que las descripciones de las herramientas se
derivan de él en lugar de escribirse a mano y quedar desfasadas en la primera migración.

### La frontera determinista

Dinero, precios, energía y horarios se calculan con los servicios deterministas que ya existen; el
modelo orquesta y explica. Es la decisión que hace defendible la funcionalidad, y conviene
argumentarla como producto y no como tecnología: un número inventado por un modelo de lenguaje en
una aplicación que mueve dinero y promete un ahorro no es una imprecisión, es un fallo. Si el
asistente dice que cargar de tres a siete de la mañana ahorra 1,80 €, esa cifra tiene que ser la
que devolvió el optimizador, no una plausible.

Hay un segundo argumento, menos evidente: lo que calcula un servicio se prueba, y lo que redacta un
modelo, no. El coste de una sesión sale hoy de una función con pruebas unitarias, la misma que
alimenta la pantalla; si el asistente lo recalculase por su cuenta, la aplicación tendría dos
respuestas para la misma pregunta y solo una estaría verificada. El apartado anterior evalúa el ahorro que
produce el optimizador, y esa evaluación no dice absolutamente nada sobre un ahorro que un modelo
se invente.

De la frontera se sigue el reparto. Las herramientas devuelven estructuras —franjas horarias, kWh,
euros, identificadores de punto—; el modelo decide qué herramienta llamar, con qué parámetros y en
qué orden, y convierte el resultado en una frase. También hereda el control de acceso: las llamadas
se ejecutan con la sesión del usuario que pregunta y contra los mismos *endpoints* protegidos
(capítulo 6), de modo que el asistente no abre una vía privilegiada a datos que la interfaz no
mostraría.

> **[FIGURA 9.1]** — *La frontera determinista.* Diagrama con tres bandas: arriba la conversación
> del usuario; en medio el modelo, con una única responsabilidad rotulada («elige herramienta,
> parámetros y orden; redacta la respuesta»); abajo las herramientas expuestas, una caja por
> *endpoint* real (`/api/points`, `/api/simulate`, `/api/recommend`, `/api/prices/today`), con una
> etiqueta que indique que todo cálculo de euros, kWh y horas ocurre en esa banda inferior. Marcar
> con trazo distinto las herramientas que hoy existen y las que dependen de fases pendientes.
> **Cómo obtenerla:** diagrama a dibujar en Mermaid (`flowchart`).

### Las funcionalidades candidatas

| Candidata | Qué aporta | Coste y dependencias |
| --- | --- | --- |
| Asistente de viaje con llamadas encadenadas (buscar punto → simular → optimizar → reservar) | Una sola frase del usuario atraviesa cuatro servicios; es la demostración más completa | La más cara y la de mayor riesgo: exige las fases 9 y 10 terminadas |
| Explicación en lenguaje natural de la salida del optimizador | Convierte un horario en un porqué: qué horas, y cuánto se ahorra frente a cargar ahora | La más barata: consume una salida ya calculada y no hace aritmética |
| Búsqueda conversacional sobre el catálogo | Traduce una frase a los filtros que el mapa ya aplica en el navegador | Barata; su peor fallo es un resultado vacío, no una cifra equivocada |
| Sugerencias a partir del histórico | Propone la próxima recarga a partir de la rutina del conductor | Depende del registro de sesiones, que no existe y arrastra el problema de honestidad del capítulo 7 |

**Tabla 9.1.** Candidatas del banco de ideas para la fase 12, con su aportación y su coste.

Las dos más defendibles como capítulo son la explicación del horario y la búsqueda conversacional,
por la misma razón: su peor fallo es una frase pobre. La primera además cierra el apartado de optimización, donde
un ahorro que el usuario no entiende no cambia su comportamiento. El asistente de viaje es la idea
con más fuerza en una defensa, pero su riesgo no está en el modelo sino en sus dependencias: sin
reservas no hay último paso. Las sugerencias a partir del histórico quedan al final, porque se
apoyarían en un registro que hoy nadie observa.

### Lo que la fase tendrá que decidir

**La profundidad** se fija contra las horas que queden, no al revés. **El modelo** se anotará por
su identificador exacto y no por su nombre comercial, porque una familia de modelos cambia de
comportamiento sin cambiar de nombre y un resultado que no dice cuál se usó no es reproducible.
**La clave de API** necesita sitio en la pila de producción: hoy los secretos llegan a los
contenedores como variables de entorno desde un fichero en el disco del servidor (capítulo 8), y
la de un proveedor de modelos sería el primer secreto del sistema con coste monetario por llamada,
de manera que una fuga es una factura además de un acceso. **El coste por consulta** hay que
medirlo y acotarlo antes de exponer nada, con un límite por usuario del mismo tipo que los que ya
protegen la autenticación.

Y **qué hace la interfaz cuando el modelo no está disponible**, que es la decisión que manda sobre
las demás. El criterio es explícito: la demostración de la defensa no puede depender de un servicio
externo. De ahí que el asistente sea una superficie añadida y nunca el único camino hacia una
función —todo lo que se pueda pedir hablando tiene que seguir estando a un par de toques— y que un
fallo de la llamada degrade a la pantalla determinista que responde a esa misma pregunta, con un
aviso y sin dejar la conversación colgada.

### Por qué es la primera candidata a recortarse

El orden de recorte está declarado por adelantado y esta fase es la primera en salir. El núcleo del
trabajo es la aplicación, y el asistente es una capa sobre funciones que ya responden sin él. Si el
calendario obliga a elegir entre terminar el optimizador y empezar el asistente, la elección está
tomada desde antes de que se plantee: renunciar a esta fase cuesta un capítulo, renunciar a las
anteriores costaría el argumento.

> **PENDIENTE:** si la fase 12 llega a ejecutarse, rellenar aquí el conjunto de funcionalidades
> finalmente elegido y por qué; el identificador exacto del modelo; el coste medio y máximo medido
> por consulta; el comportamiento implementado ante la indisponibilidad del proveedor; y una
> transcripción real de una conversación completa como figura.
