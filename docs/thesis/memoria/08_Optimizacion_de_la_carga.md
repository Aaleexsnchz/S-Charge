# 8. Optimización de la carga

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
Las dos entradas ya existen: la energía objetivo sale de la simulación (capítulo 7) y la curva, del
servicio de precios (capítulo 5).

## Formulación

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

### El caso sin contigüidad

Así escrito es un programa lineal con una restricción de igualdad y cotas por variable, y su óptimo
es **voraz**: se ordenan las franjas por precio ascendente y se llenan a tope hasta agotar $E$, con
a lo sumo una parcialmente llena. Es la mochila fraccionaria, y el argumento de intercambio es
inmediato: mover energía de una franja cara a otra más barata que no esté llena baja el coste sin
violar ninguna restricción.

La consecuencia práctica pesa más que el resultado: **no hace falta un solucionador de programación
lineal** para un problema cuya solución cerrada cabe en diez líneas.

### Una única ventana contigua

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

### Las decisiones que la fase debe cerrar

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
potencia plana, falso bajo el *taper* de la corriente continua (capítulo 7). Un punto doméstico es
de corriente alterna, justo el caso donde la suposición se sostiene.

## Pseudocódigo

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

## Complejidad y tamaño real del problema

El voraz es $O(T \log T)$ por la ordenación y la ventana deslizante es $O(T)$. Con la hora como
franja, una noche son doce y un día entero veinticuatro: a esa escala la diferencia es teórica,
ambos terminan en microsegundos y el coste de la petición lo domina la lectura de la curva en la
base de datos.

De ahí la conclusión honesta del capítulo: **la dificultad no está en la optimización, está en los
datos**. Los precios se guardan por instante de inicio de hora y se consultan en hora local de
Madrid, de modo que los dos días del año en que cambia la hora tienen 23 o 25 franjas y no 24. Y un
horizonte que cruza la medianoche necesita un día que puede no estar publicado: el precio del día
siguiente no aparece antes de las 20:15 [49] y la API de REE devuelve un error del servidor
para un día que aún no lo está. Las dos respuestas defendibles son truncar el horizonte en la
última hora publicada y decirlo, o rechazar la petición.

## La respuesta prevista

El diseño previsto para `POST /api/recommend` es devolver la ventana recomendada —inicio, fin y
energía por franja—, su coste estimado, una o dos alternativas (el plan partido y la ventana más
barata si el usuario pudiera salir más tarde) y, sobre todo, **el ahorro frente a cargar ahora**:
el mismo cálculo empezando en el instante de la petición. Esa cifra es la que da sentido a la
funcionalidad, y si resulta ser de céntimos, decirlo también es parte del trabajo. Como en la
simulación, la respuesta indica la procedencia del precio de cada franja, para que la interfaz no
presente como dato lo que es estimación.

> **[FIGURA 8.1]** — *La ventana óptima sobre la curva real de un día.* Gráfica de barras con las
> 24 franjas horarias del PVPC de un día concreto ya almacenado (€/kWh en el eje vertical, hora
> local de Madrid en el horizontal), con la ventana recomendada sombreada, la ventana equivalente
> que empezaría al enchufar marcada en otro tono, y ambos costes anotados junto al ahorro entre
> ellas. **Cómo obtenerla:** debe generarse con datos reales de la tabla `electricity_prices`
> —histórico disponible desde el 1 de enero de 2026—, no con una curva inventada; basta un guion de
> Matplotlib sobre el volcado de un día representativo. Elegir un día con diferencial claro entre
> valle y pico e indicar la fecha en el pie.

## Dónde queda esto frente a la literatura

La programación de recarga frente a una señal de precio es un problema estudiado y resuelto: hay
revisiones canónicas de las estrategias de recarga inteligente en redes de distribución
[26], formulaciones del *valley filling* como protocolo descentralizado sobre
flotas que negocian su perfil con una señal común [25], marcos de coordinación de muchos
vehículos bajo la restricción física de una infraestructura compartida [31][28] y
variantes para los cargos por demanda en emplazamientos no residenciales [27].

Ninguna de esas dificultades aparece aquí. Este problema tiene **un vehículo, un punto, ninguna
restricción de red y un precio exógeno**, lo que lo reduce a un programa lineal de libro cuya
solución voraz se conoce desde mucho antes que los vehículos eléctricos. La aportación no es
algorítmica: es aplicar un resultado conocido a datos españoles reales. Un límite: si muchos
usuarios optimizaran a la vez contra la misma curva el valle se desplazaría, y esa realimentación
es lo que los protocolos descentralizados modelan [25] y este diseño no.

## Cómo se evaluará

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
