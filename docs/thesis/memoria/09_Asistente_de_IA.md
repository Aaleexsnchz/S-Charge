# 9. Asistente de IA

La fase 12 no ha empezado y **el conjunto concreto de funcionalidades no está decidido**. Lo que sí
lo está, y es lo que se defiende aquí, es la forma que tendría: una capa de lenguaje natural
**sobre las APIs que la aplicación ya tiene** —puntos, simulación, recomendación, precios,
reservas— usadas como herramientas. Ninguna fuente de datos nueva, ningún modelo entrenado, ningún
dato que no pase antes por un *endpoint* existente. El contrato de esa API está versionado en el
repositorio como `openapi.json` (capítulo 4), así que las descripciones de las herramientas se
derivan de él en lugar de escribirse a mano y quedar desfasadas en la primera migración.

## La frontera determinista

Dinero, precios, energía y horarios se calculan con los servicios deterministas que ya existen; el
modelo orquesta y explica. Es la decisión que hace defendible la funcionalidad, y conviene
argumentarla como producto y no como tecnología: un número inventado por un modelo de lenguaje en
una aplicación que mueve dinero y promete un ahorro no es una imprecisión, es un fallo. Si el
asistente dice que cargar de tres a siete de la mañana ahorra 1,80 €, esa cifra tiene que ser la
que devolvió el optimizador, no una plausible.

Hay un segundo argumento, menos evidente: lo que calcula un servicio se prueba, y lo que redacta un
modelo, no. El coste de una sesión sale hoy de una función con pruebas unitarias, la misma que
alimenta la pantalla; si el asistente lo recalculase por su cuenta, la aplicación tendría dos
respuestas para la misma pregunta y solo una estaría verificada. El capítulo 8 evalúa el ahorro que
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

## Las funcionalidades candidatas

| Candidata | Qué aporta | Coste y dependencias |
| --- | --- | --- |
| Asistente de viaje con llamadas encadenadas (buscar punto → simular → optimizar → reservar) | Una sola frase del usuario atraviesa cuatro servicios; es la demostración más completa | La más cara y la de mayor riesgo: exige las fases 9 y 10 terminadas |
| Explicación en lenguaje natural de la salida del optimizador | Convierte un horario en un porqué: qué horas, y cuánto se ahorra frente a cargar ahora | La más barata: consume una salida ya calculada y no hace aritmética |
| Búsqueda conversacional sobre el catálogo | Traduce una frase a los filtros que el mapa ya aplica en el navegador | Barata; su peor fallo es un resultado vacío, no una cifra equivocada |
| Sugerencias a partir del histórico | Propone la próxima recarga a partir de la rutina del conductor | Depende del registro de sesiones, que no existe y arrastra el problema de honestidad del capítulo 7 |

**Tabla 9.1.** Candidatas del banco de ideas para la fase 12, con su aportación y su coste.

Las dos más defendibles como capítulo son la explicación del horario y la búsqueda conversacional,
por la misma razón: su peor fallo es una frase pobre. La primera además cierra el capítulo 8, donde
un ahorro que el usuario no entiende no cambia su comportamiento. El asistente de viaje es la idea
con más fuerza en una defensa, pero su riesgo no está en el modelo sino en sus dependencias: sin
reservas no hay último paso. Las sugerencias a partir del histórico quedan al final, porque se
apoyarían en un registro que hoy nadie observa.

## Lo que la fase tendrá que decidir

**La profundidad** se fija contra las horas que queden, no al revés. **El modelo** se anotará por
su identificador exacto y no por su nombre comercial, porque una familia de modelos cambia de
comportamiento sin cambiar de nombre y un resultado que no dice cuál se usó no es reproducible.
**La clave de API** necesita sitio en la pila de producción: hoy los secretos llegan a los
contenedores como variables de entorno desde un fichero en el disco del servidor (capítulo 10), y
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

## Por qué es la primera candidata a recortarse

El orden de recorte está declarado por adelantado y esta fase es la primera en salir. El núcleo del
trabajo es la aplicación, y el asistente es una capa sobre funciones que ya responden sin él. Si el
calendario obliga a elegir entre terminar el optimizador y empezar el asistente, la elección está
tomada desde antes de que se plantee: renunciar a esta fase cuesta un capítulo, renunciar a las
anteriores costaría el argumento.

> **PENDIENTE:** si la fase 12 llega a ejecutarse, rellenar aquí el conjunto de funcionalidades
> finalmente elegido y por qué; el identificador exacto del modelo; el coste medio y máximo medido
> por consulta; el comportamiento implementado ante la indisponibilidad del proveedor; y una
> transcripción real de una conversación completa como figura.
