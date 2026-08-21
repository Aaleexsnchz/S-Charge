# 15. Conclusiones y trabajo futuro

## Evaluación de los objetivos

El capítulo 1 fijó seis objetivos específicos con un criterio de verificación cada uno. Cinco se
cumplen y uno se cumple a medias.

| Id | Objetivo | Resultado |
| --- | --- | --- |
| **OE1** | Aplicación de extremo a extremo | **Cumplido.** Cliente instalable, API propia, base de datos, sistema de identidad y cadena de comprobaciones automatizada, con ~3.157 líneas de Python y ~4.732 de TypeScript sobre 10 tablas y 134 pruebas de backend. |
| **OE2** | Espejar el catálogo nacional bajo el límite de 5 peticiones/hora | **Cumplido.** 142 operadores, ~13.700 puntos, ~42.000 EVSEs, ~47.000 conectores y ~27.000 tarifas, sembrados en unos 12 días de ticks desatendidos. |
| **OE3** | Simular una recarga por modelo de vehículo y conector | **Cumplido.** Servicio de simulación accesible desde la ficha del punto, con modelo físico formulado y declarado como estimación basada en especificaciones. |
| **OE4** | Optimizar el momento de la recarga contra precios reales | **Parcialmente cumplido.** La ingesta diaria del PVPC funciona y acumula histórico desde el 1 de enero de 2026, y el algoritmo queda formulado, acotado en complejidad y con su experimento de evaluación diseñado; **no está implementado**. |
| **OE5** | Desplegar en producción, accesible públicamente | **Cumplido.** La aplicación responde en `https://s-charge.app` sobre HTTPS, se instala como PWA desde producción y la entrega está automatizada desde el repositorio. |
| **OE6** | Argumentar la viabilidad | **Cumplido.** Costes reales, economía unitaria declarada como hipótesis, camino de escalado razonado y registro explícito de carencias. |

**Tabla 15.1.** Resultado de cada objetivo específico.

Que OE4 quede a medias es la consecuencia directa de una decisión de calendario tomada por
adelantado y no un imprevisto: el despliegue se antepuso al resto del trabajo de
funcionalidades para disponer pronto de una instancia real accesible desde el móvil y con los
procesos de actualización fuera del portátil. El coste de esa decisión es exactamente este, y
estaba previsto.

## Lo que este trabajo demuestra

**Una restricción externa puede ordenar una arquitectura entera.** El límite de cinco peticiones
por hora de la fuente de datos no fue un inconveniente que sortear, sino el dato del que se
derivan el espejo en base de datos propia, la siembra por *ticks* acotados e idempotentes, la
tabla de cursores, la política de refresco limitada a las tarifas y hasta la estrategia de
copias de seguridad, porque el catálogo es el único artefacto del sistema que no se puede
regenerar barato. Diseñar alrededor de una restricción da resultados más específicos —y más
defendibles— que diseñar en abstracto.

**Una decisión correcta puede caducar sin haber sido un error.** Las decisiones iniciales
optimizaban el arranque, que era el criterio adecuado con cero pantallas construidas; una vez
construida la base, el criterio dominante pasó a ser el coste marginal de cada pantalla nueva y
el rendimiento en el móvil. Separar «me equivoqué» de «esto tenía fecha de caducidad» es lo que
permite revisar decisiones sin convertir el proyecto en una sucesión de arrepentimientos. El
criterio que ordenó esas revisiones —**si una migración la verifica una herramienta o la
verifica una persona**— resultó más útil que la medida habitual de cuánto código hay que tocar.

**La frontera de seguridad es la que comprueba el servidor.** Durante buena parte del desarrollo
la aplicación tuvo dos respuestas distintas a la misma pregunta: el cliente exigía sesión para
todo y la API servía el catálogo a cualquiera que conociera la URL. El error de razonamiento
—confundir un guardia de navegación con un control de acceso— es común, y la corrección
interesante no fue añadir la comprobación sino **derivar la prueba de regresión del propio
esquema de la aplicación**, de modo que un endpoint nuevo no pueda nacer sin protección.

**Declarar lo que no se modela vale más que simularlo.** La disponibilidad en tiempo real de los
puntos no se modela, y hubo dos intentos sucesivos de resolverlo —calibrar la ocupación con un
conjunto de datos real y, después, generarla sintéticamente— que se abandonaron por la misma
razón: producían un dato que el usuario leería como real sin serlo. La aplicación etiqueta como
«datos de ejemplo» todo lo que aún no lo es. Esa disciplina cuesta algo en apariencia y ahorra
mucho en credibilidad.

## Aprendizajes

El más útil no es técnico. Escribir la alternativa rechazada junto a cada decisión obliga a
comprobar que la decisión se tomó de verdad; una alternativa que no se sabe argumentar es la
señal de que se eligió por inercia. Los quince registros de decisión de este proyecto fueron
más caros de escribir que de leer, y son lo que ha hecho posible redactar esta memoria sin
reconstruir a posteriori razonamientos que nadie tuvo.

En lo técnico, lo que más tiempo consumió no fue construir funcionalidades sino **entender el
comportamiento real de un sistema ajeno**: por qué una consulta con marca de agua antigua agota
el tiempo del *gateway* mientras una reciente responde, y por qué la respuesta correcta no era
reintentar sino saltar la marca de agua y aceptar la pérdida. Ese tipo de problema no aparece en
un entorno de laboratorio y es el que distingue un sistema en funcionamiento de un prototipo.

## Trabajo futuro

**Lo comprometido y no ejecutado**, en el orden en que está planificado: la migración del
frontend a una base coherente, la reactivación de los procesos de actualización de datos —hoy
detenidos deliberadamente, con la marca de agua congelada para poder inspeccionarla—, los puntos
de carga de particulares con precio del propietario, el optimizador que completa OE4, y después
las funcionalidades opcionales de reservas, monedero y asistente de IA, con su orden de recorte
ya declarado.

**Lo que exigiría un producto real**, y que el capítulo 8 registra sin disimular: observabilidad
—hoy inexistente y la mayor carencia individual del sistema—, cumplimiento efectivo en
protección de datos con vía de supresión que alcance a las copias de seguridad, verificación
automática de la restauración, política de seguridad de contenido completa, y el cerrojo que
elimina la condición de carrera del cursor del proceso de actualización, alcanzable hoy sin
escalar nada.

**Lo que depende de terceros.** La disponibilidad en tiempo real no es un problema de ingeniería
sino de acceso al dato: exige un acuerdo con cada operador o una fuente que hoy no se publica.
El esquema alineado con OCPI deja esa puerta abierta sin tocar la base de datos, que era
precisamente el motivo de alinearlo.

Queda una lectura de conjunto. El trabajo no ha inventado la recarga entre particulares, y el
capítulo 2 nombra a quien ya la ofrece. Lo que aquí se sostiene es más modesto y, creo, más
verificable: que una sola persona puede concebir, construir, desplegar y argumentar un sistema
que integra un catálogo nacional real, precios regulados reales y funcionalidad propia, y hacerlo
declarando con precisión qué parte es dato, qué parte es estimación y qué parte todavía no
existe.
