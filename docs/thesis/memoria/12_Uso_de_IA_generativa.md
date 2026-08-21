# 14. Uso de inteligencia artificial generativa

Este trabajo se ha desarrollado con asistencia de un agente de código basado en un modelo de
lenguaje. Ocultarlo sería incompatible con el criterio de honestidad que sigue el resto de la
memoria, y describirlo con vaguedad —«se emplearon herramientas de IA»— no informaría de nada.
Este capítulo detalla en qué consistió esa asistencia, qué controles se aplicaron sobre ella y
dónde están sus límites.

## El marco de la universidad

La Universidad Carlos III de Madrid admite el uso de IA generativa en los trabajos de fin de
máster siempre que se declare, y exige cumplimentar el formulario de declaración correspondiente
e incluirlo como anexo [60]. Su guía distingue entre usos aceptables —procesamiento de
datos con las debidas cautelas, refinamiento de texto previamente propio, apoyo al pensamiento
crítico— y usos que comprometen las competencias que el título debe acreditar, entre los que
sitúa expresamente la generación de texto y la estructuración de contenidos. También advierte
de que emplear IA para **fabricar datos** que deberían obtenerse mediante investigación real es
éticamente inaceptable.

Dos de esas líneas se han respetado sin matices, y conviene decirlo antes que nada: **no se ha
fabricado ningún dato** y **no se ha inventado ninguna referencia**. Todas las cifras de esta
memoria proceden del sistema construido, de mediciones hechas sobre él o de fuentes públicas
verificadas; toda referencia bibliográfica se comprobó contra su documento original antes de
citarse. Cuando una fuente no pudo verificarse, la memoria lo declara en lugar de rellenarlo,
como ocurre con los términos de uso de la fuente de datos que se analizan en el capítulo 10.

El uso que sí requiere declaración expresa —y que el formulario del anexo recoge— es el de
apoyo a la redacción, realizado sobre documentación técnica previa de elaboración propia y
sometido a revisión del autor.

## La asistencia durante el desarrollo

La parte más sustancial no está en la memoria sino en el software. El desarrollo se realizó con
un agente de código operando sobre el repositorio, con un patrón de trabajo estable: el autor
fija el objetivo y las restricciones, el agente propone e implementa, y la revisión y la
decisión final son del autor.

Lo que hace este uso defendible no es la herramienta sino **el andamiaje que se construyó
alrededor**, que es en sí mismo una decisión de ingeniería. Todo cambio atraviesa la misma
cadena de comprobaciones descrita en el capítulo 8 —linter, formateador, comprobación de tipos,
pruebas de backend contra base de datos real, pruebas y construcción de frontend— antes de poder
llegar a la rama principal, y esa cadena no distingue quién escribió el código. Las decisiones
arquitectónicas quedan registradas en documentos de decisión con sus alternativas rechazadas
(quince en total), de modo que existe un rastro revisable del porqué de cada una. El resultado
es que la asistencia se ejerce dentro de un sistema que la verifica, en lugar de sobre un
repositorio donde la única garantía sería la confianza.

El proyecto usa además **skills de agente**: conjuntos de instrucciones que fijan cómo se aborda
un tipo de tarea concreto —qué comprobar, en qué orden, qué evitar—. No añaden capacidades al
modelo; convierten en revisable y repetible un criterio que de otro modo quedaría implícito. El
anexo correspondiente registra cuáles se usaron, para qué y con qué versión exacta, anclada por
un hash de contenido, porque sin la versión la afirmación «se usó tal skill» no sería
verificable. Un procedimiento escrito que dice «reproduce antes de arreglar» o «un registro de
decisión solo si condiciona la arquitectura» sigue siendo una decisión de ingeniería del autor,
esté ejecutada por una persona o asistida por un agente. Lo que no está escrito es lo que no se
puede revisar.

## La asistencia en la redacción de la memoria

Los capítulos de esta memoria se redactaron con asistencia del agente a partir de **material
propio anterior**: los documentos de decisión, los planes de fase, los documentos conceptuales
en español escritos durante el desarrollo y el código del propio sistema. El agente no partió de
una página en blanco ni de conocimiento general sobre vehículos eléctricos; partió de
documentación técnica que ya existía en el repositorio y cuyo contenido es resultado del trabajo
realizado.

Los controles aplicados fueron tres. Primero, **la bibliografía se verificó por separado y antes
de escribir**: cada fuente se descargó y se leyó, y las que no pudieron comprobarse quedaron
marcadas como no verificadas y excluidas de cualquier afirmación propia. Ese proceso corrigió
varias premisas que el autor daba por buenas, entre ellas la revisión vigente de una norma
técnica de referencia y la identidad del organismo que opera el registro público español de
puntos de recarga. Segundo, **el estado real del sistema se fijó por adelantado** y por escrito,
distinguiendo lo construido de lo diseñado, para que ningún capítulo pudiera describir como
funcionando algo que no lo está: esa distinción recorre toda la memoria y es visible en cada
capítulo. Tercero, **la revisión del autor**, que es la que convierte un borrador en texto
propio y de la que depende la validez de todo lo anterior.

## Límites y riesgos

Tres son reales y merecen nombrarse.

El primero es la **verosimilitud sin verdad**: un modelo de lenguaje produce con igual soltura
una cita correcta y una inventada, y la segunda no se distingue de la primera por su aspecto.
Es la razón de que la verificación bibliográfica se hiciera como tarea separada y previa, con
descarga del documento original, y no como comprobación posterior sobre un texto ya escrito.

El segundo es la **erosión del criterio propio**. Aceptar una propuesta razonable es más rápido
que evaluarla, y repetido muchas veces produce un trabajo que el autor no podría defender. La
mitigación no fue metodológica sino estructural: los documentos de decisión obligan a escribir
la alternativa rechazada y el motivo, y una alternativa rechazada que no se sabe argumentar es
la señal de que la decisión no se tomó realmente.

El tercero afecta a esta memoria en concreto. La guía de la universidad señala que la capacidad
de redactar y de estructurar es una competencia que el máster debe acreditar, y la asistencia en
la redacción está en tensión con ese criterio. El autor asume esa tensión, la declara aquí y en
el formulario del anexo, y responde de la totalidad del contenido: de su exactitud, de su
estructura y de su defensa.

> **PENDIENTE:** cumplimentar el formulario oficial «Declaración de uso de IA generativa» de la
> UC3M e incorporarlo como anexo, marcando los usos concretos que este capítulo describe.
> Revisar además que la redacción final de cada capítulo refleje la voz del autor tras su
> revisión manual.
