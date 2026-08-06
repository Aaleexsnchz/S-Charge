# 13. Entorno socioeconómico, presupuesto y planificación

## A quién sirve y qué resuelve para cada lado

España tenía **56.682 puntos de recarga de acceso público operativos** a 30 de junio de 2026, y
su indicador global de electromovilidad —26,9 sobre 100— seguía **13,2 puntos por debajo de la
media de la UE-27**, con la distancia ampliándose [1]. El mismo barómetro estima que
17.821 puntos instalados están fuera de servicio, un 23,9 % del total, aunque conviene decir de
dónde sale: ANFAC lo calcula a partir de reportes de usuarios en Electromaps y lo advierte en el
propio documento, ante la falta de una plataforma oficial de información de puntos.

Para el **conductor**, el problema no es solo cuántos puntos hay. El patrón del mercado es que
cada operador publica su propia aplicación, con su propia alta y su propio método de pago, de
modo que usar la red del país exige gestionar varias. Cuando se pregunta a los conductores
europeos qué importa en una sesión de recarga pública, las respuestas son que la estación esté
operativa al llegar, que no haya que esperar y que exista **información de precio clara y
transparente** [2]. Esa tercera es exactamente la que una aplicación puede resolver
sin instalar un solo cargador.

Para el **propietario de un punto**, el problema es el inverso: un cargador doméstico o de
empresa es un activo instalado que se usa unas horas al día y está parado el resto. Ponerlo a
disposición de otros conductores convierte capacidad ociosa en ingreso sin obra nueva.

Ese doble encaje define un **mercado de dos lados**, con su problema clásico de arranque: sin
puntos publicados no hay conductores, y sin conductores ningún propietario publica el suyo. Aquí
es donde el diseño del sistema hace un trabajo económico y no solo técnico. **El catálogo espejado
de REVE llena un lado antes de tener un solo usuario**: quien abre la aplicación el primer día ve
~13.700 puntos de carga reales con su tarifa, no una pantalla vacía esperando a que alguien
publique el primero. El lado que queda por construir es únicamente el de los propietarios, que es
además el lado con incentivo económico directo. La captación deja de ser un problema doble y pasa
a ser uno simple.

Conviene acotar la novedad. La recarga entre particulares existe: **Place to Plug** opera ya en
España conectando conductores con anfitriones particulares y permitiendo reservar
[5], y la literatura académica estudia el modelo tanto desde la percepción de los
usuarios como desde la de los anfitriones reales [17][18][19]. Lo
que aquí se defiende es la combinación —catálogo nacional espejado del registro oficial, puntos de
particulares, simulación por modelo de vehículo y optimización contra la curva PVPC real en una
sola PWA—, no la invención del modelo.

> **[FIGURA 13.1]** — *El mercado de dos lados y el arranque asimétrico.* Diagrama con la
> plataforma en el centro y dos columnas a los lados. Izquierda, **conductores**: flechas de
> entrada rotuladas *un solo alta y un solo pago*, *precio visible antes de enchufar*,
> *simulación por modelo*. Derecha, **propietarios**: *ingreso de un activo parado*, *fijan precio
> o margen*. En el centro, bajo la plataforma, una caja destacada rotulada **catálogo REVE
> espejado — ~13.700 puntos disponibles antes del primer usuario**, con una flecha hacia el lado
> de los conductores marcada como *lado ya lleno*, y el lado de los propietarios marcado como
> *lado por construir*. La asimetría entre los dos lados es lo que la figura debe hacer evidente.
> **Cómo obtenerla:** diagrama a dibujar en draw.io o Mermaid.

## Modelo de ingresos y economía unitaria

El ingreso previsto es una **comisión porcentual sobre las sesiones celebradas en puntos de
particulares**. Los puntos de operadores comerciales no se monetizan: están en la aplicación
porque la hacen útil desde el primer día, no porque exista contrato con el operador. Esa
distinción importa, porque significa que la parte del catálogo que da tracción no genera ingreso
y la que genera ingreso todavía no existe.

| Magnitud | Valor | Origen |
| --- | --- | --- |
| Batería del vehículo | 60 kWh | **Dato**: mediana del catálogo real de 31 modelos (61,7 kWh), redondeada |
| Ventana de carga | 20 % → 80 % | **Dato**: valor por defecto de la simulación |
| Energía de la sesión | 36 kWh | Derivado |
| PVPC de referencia | 0,12 €/kWh | **Dato**: referencia del análisis de márgenes |
| Margen del propietario en corriente alterna | +0,22 €/kWh | **Dato**: mediana sobre ~27.000 tarifas reales |
| Precio al conductor | 0,34 €/kWh | Derivado |
| Importe de la sesión | 12,24 € | Derivado |
| Comisión de la plataforma | 10 % | **Hipótesis** |
| Ingreso por sesión | 1,22 € | Derivado de la hipótesis |

**Tabla 13.1.** Economía unitaria de una sesión tipo. Solo la comisión es una cifra inventada;
todo lo demás sale de parámetros reales del sistema o de medidas sobre el mercado español.

Con esa comisión, el coste recurrente de la infraestructura —de ~7 a ~18 €/mes de servidor más
~10 €/año de dominio, es decir, entre 7,8 y 18,8 €/mes— queda cubierto con **entre 7 y 16
sesiones mensuales en toda la plataforma**. La cifra es tan pequeña que su lectura correcta no es
optimista sino la contraria: **el servidor no es el coste que decide nada**. Lo que decide es todo
lo que ese cálculo deja fuera y no está construido —comisión de la pasarela de pago, soporte,
cobertura de responsabilidad frente a un incidente en un punto ajeno, y el tiempo de la persona
que mantiene el sistema—. Cubrir el hosting con dieciséis sesiones es una comprobación de orden
de magnitud, no un umbral de rentabilidad, y proyectarlo a varios años sería dar precisión a una
hipótesis del 10 %.

> **[FIGURA 13.2]** — *Cobertura del coste de infraestructura.* Gráfico de líneas: eje
> horizontal, sesiones mensuales en la plataforma (0 a 40); eje vertical, euros al mes. Una recta
> creciente rotulada **ingreso por comisión (hipótesis del 10 %: 1,22 €/sesión)** y una banda
> horizontal sombreada entre 7,8 y 18,8 €/mes rotulada **coste de infraestructura (servidor +
> dominio)**. Marcar los dos cortes, en 7 y en 16 sesiones. Añadir al pie, dentro de la figura, la
> advertencia **no incluye pasarela de pago, soporte, responsabilidad ni personal**.
> **Cómo obtenerla:** diagrama a dibujar a partir de la tabla 13.1.

## Presupuesto del trabajo

El primer *commit* del repositorio es del **28 de marzo de 2026** y la aplicación llegó a
producción el **4 de agosto de 2026**: algo más de diecinueve semanas de trabajo a tiempo parcial
de una sola persona, durante las cuales se completaron cinco de las fases planificadas. Las horas
de la tabla 13.2 son una **estimación razonada sobre esa duración real**, no un registro
cronometrado, y se presentan por bloques de trabajo precisamente para no fingir una precisión que
no existe.

| Bloque de trabajo | Fases | Horas estimadas |
| --- | --- | --- |
| Fundación: autenticación, esquema, andamiaje | 1 | 60 |
| Espejo del catálogo REVE y mapa | 2 | 55 |
| Simulación, catálogo de vehículos e ingesta de precios | 3 | 40 |
| Rediseño y arquitectura de información | 4 | 45 |
| Despliegue, integración continua y verificación de seguridad | 5 | 60 |
| Documentación, decisiones registradas y material de memoria | Transversal | 40 |
| **Total** | | **300** |

**Tabla 13.2.** Estimación de esfuerzo por bloque, equivalente a unas 16 horas semanales
sostenidas durante el periodo.

| Partida | Base de cálculo | Importe |
| --- | --- | --- |
| Personal — ingeniería de software | 300 h × 30 €/h (**tarifa hipotética de mercado**) | 9.000,00 € |
| Servidor de producción | ~2 meses a ~12 €/mes | 24,00 € |
| Dominio `s-charge.app` | 1 año, registrador a precio de coste | 10,00 € |
| Utillaje y servicios | Software libre o capa gratuita | 0,00 € |
| Amortización del equipo | 1.500 € a 48 meses, 5 meses de uso (**hipótesis**) | 156,25 € |
| **Total sin impuestos** | | **9.190,25 €** |
| IVA (21 %) | | 1.929,95 € |
| **Total con impuestos** | | **11.120,20 €** |

**Tabla 13.3.** Presupuesto del trabajo. La tarifa horaria y el valor del equipo son hipótesis
declaradas; el resto son costes efectivamente incurridos.

La línea de utillaje merece leerse como resultado y no como ausencia. **Todo lo que construye,
prueba, despliega y opera este sistema cuesta cero euros**: el lenguaje, el framework, la base de
datos, el servidor web con sus certificados, la integración continua, el mapa base, el envío de
correo transaccional y la copia de seguridad externa caben en software libre o en capas gratuitas.
El coste del proyecto es, con más de un 99 % del presupuesto, tiempo de una persona.

> **PENDIENTE:** registrar el coste real de las suscripciones de asistencia de IA generativa
> empleadas durante el desarrollo (véase el capítulo 14) e incorporarlo como línea propia de la
> tabla 13.3, recalculando los totales.

## Impacto socioeconómico y ambiental

De adoptarse, el efecto más directo es de **utilización, no de despliegue**: la literatura de
planificación de infraestructura de recarga se ocupa de cuántos puntos hacen falta y dónde
situarlos [29][30]; poner en circulación los que ya están instalados actúa sobre
el mismo problema por el lado del aprovechamiento, y es la palanca más barata de las dos. En un
país donde casi una cuarta parte del parque instalado se reporta como no operativo, mejorar el
rendimiento de lo existente no es una idea menor [1].

El segundo efecto es el **desplazamiento de la demanda a las horas más baratas**, que en el
sistema eléctrico español suelen coincidir con las de mayor peso renovable. Se dice así, con
«suelen», y no se traduce a toneladas de CO₂ evitadas: hacerlo exigiría un factor de emisión
horario defendible y una fuente que lo sostenga, y ninguna de las dos cosas se ha establecido en
este trabajo. La consecuencia práctica es explícita en el producto: la tarjeta de **CO₂ evitado**
que aparece hoy en el panel es maqueta etiquetada como dato de ejemplo, y la postura adoptada es
que **o se apoya en un factor de emisión con fuente, o desaparece de la interfaz**. Mostrar una
cifra ambiental sin poder defenderla sería el tipo exacto de afirmación que el resto de la memoria
evita.

El tercero es la **reducción de fricción** en la adopción del vehículo eléctrico: menos altas,
menos aplicaciones y el precio visible antes de enchufar, en la dirección que la propia regulación
europea ya impone a los operadores al exigir precios comparables y transparentes y su
presentación antes de iniciar la sesión [24] (el marco completo, en el capítulo 12).

De los Objetivos de Desarrollo Sostenible, dos son defendibles sin forzar el argumento: el
**ODS 7**, por el desplazamiento de consumo hacia horas de mayor peso renovable y por el mejor
aprovechamiento de infraestructura energética instalada, y el **ODS 11**, por su contribución a
una movilidad urbana menos contaminante. No se reclaman más.

> **PENDIENTE:** falta fuente citable para los Objetivos de Desarrollo Sostenible 7 y 11 (Agenda
> 2030 de Naciones Unidas); añadirla a la bibliografía y citarla aquí.

## Explotación del resultado

Entre este prototipo desplegado y un producto hay cuatro asuntos bloqueantes, todos ya
identificados en el registro de carencias del proyecto.

**Protección de datos.** El sistema almacena datos personales de sujetos de la UE y hoy no tiene
política de privacidad publicada, base jurídica documentada, acuerdos de encargo con sus
proveedores, política de retención, vía funcional de supresión ni procedimiento de notificación de
brechas en las 72 horas que exige el reglamento [38]. La supresión, además, no es un
*endpoint* que falte: borrar una cuenta obliga a decidir qué ocurre con sus sesiones, sus reservas
y sus apuntes de monedero.

**Pago real.** El monedero está diseñado como registro simulado. Cobrar de verdad exige una
pasarela, con lo que trae detrás: identificación del beneficiario, retenciones fiscales y una
comisión que come parte de la de la plataforma.

**Verificación de la titularidad de los puntos.** Nada impide hoy publicar un punto que no es de
uno. En una plataforma que dirige a un conductor a una dirección concreta, eso es un problema de
responsabilidad antes que de producto.

**Observabilidad.** Hoy la respuesta a *si está caído, si va lento o si un error llegó a un
usuario* es leer los registros del contenedor. Con usuarios reales, los incidentes se conocen por
los usuarios.

La vía de crecimiento pasa por **acuerdos con operadores**, y ahí el diseño ya dejó la puerta
abierta: el esquema sigue la jerarquía de OCPI [20], que es además el protocolo que la
propia normativa española impone para el intercambio de información dinámica con el sistema
público [6]. Integrar a un operador comercial es extender el origen de los datos, no
rehacer el modelo.
