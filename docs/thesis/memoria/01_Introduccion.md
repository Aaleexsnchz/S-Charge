# 1. Introducción

## La recarga pública en España

Recargar un vehículo eléctrico fuera de casa obliga a resolver dos cosas a la vez: encontrar un
punto que funcione y averiguar con qué aplicación se activa. La primera pregunta tiene desde
hace poco una respuesta pública y razonablemente buena. La segunda no la tiene ninguna.

La infraestructura ha dejado de ser escasa en términos absolutos. Según el barómetro de
electromovilidad de ANFAC, a 30 de junio de 2026 había en España 56.682 puntos de recarga
de acceso público operativos, 3.610 más que al cerrar 2025 [1]. El crecimiento es
sostenido, pero la comparación europea sigue siendo desfavorable: el indicador global de
electromovilidad que publica la asociación sitúa a España en 26,9 sobre 100 frente a 40,1 de la
UE-27, y la brecha es mayor en el componente de infraestructura (15,4 frente a 31,1) que en el
de penetración del vehículo electrificado. Solo el 32 % de la red pública supera los 22 kW.

Hay además un dato incómodo. El mismo barómetro estima que 17.821 puntos instalados están
fuera de servicio, un 23,9 % de todo lo desplegado; de estar operativos, la cifra pública
rondaría los 74.503. ANFAC advierte en el propio documento que ese estado procede de los
reportes de los usuarios de Electromaps, porque no dispone de una plataforma oficial de
información de puntos a escala nacional: es una estimación sectorial, no una medición oficial.
Aun con esa cautela, apunta a lo que los conductores declaran cuando se les pregunta, que es
encontrar la estación plenamente operativa al llegar, no esperar, y disponer de información de
precio clara y transparente [2].

> **[FIGURA 1.1]** — *Infraestructura pública española: operativa, fuera de servicio y posición
> frente a la UE.* Dos paneles: (a) barras apiladas con los 56.682 puntos operativos y los
> 17.821 fuera de servicio a 30-06-2026; (b) barras comparadas del indicador global de
> electromovilidad y de sus componentes (penetración, infraestructura, infraestructura ≥50 kW)
> para España y la UE-27. Justifica de un vistazo por qué el problema de este trabajo no es la
> falta de puntos sino el acceso a ellos.
> **Cómo obtenerla:** gráfico a construir con los datos del barómetro de ANFAC del segundo
> trimestre de 2026; indicar en el pie que el estado «fuera de servicio» es estimación de ANFAC
> a partir de Electromaps.

## El problema

La red está repartida entre decenas de operadores de punto de recarga —CPO, *Charge Point
Operator*—, y cada uno llega al conductor a través de su propia aplicación, con su propio
registro de usuario, su propio método de pago y su propia tarifa. El resultado, para quien solo
quiere enchufar el coche, es una cartera de aplicaciones que hay que instalar por adelantado
sin saber cuál hará falta. La fragmentación no es un fallo de ningún operador en concreto: es
la forma que tiene el mercado.

Sobre ese panorama, el Estado publicó una respuesta parcial. REVE, dirigido por el Ministerio
para la Transición Ecológica y el Reto Demográfico y operado por Red Eléctrica de España como
agente neutral y no comercial, reúne la información de la infraestructura pública y la sirve en
un mapa y en una aplicación móvil; incorpora, además, un planificador de rutas que calcula
paradas, tiempos y coste energético a partir de la capacidad de la batería y de la potencia de
carga [3]. Resuelve, y bien, el descubrimiento: dónde hay puntos y cómo llegar.

Lo que REVE describe termina ahí. No es una plataforma de gestión: no reserva una plaza, no
simula lo que costará y durará una recarga concreta para un modelo de coche concreto, no
propone cuándo conviene cargar en función del precio de la electricidad y no da cabida al punto
de un particular, que por definición no está en el registro de operadores. Ese es el hueco.
Entre la consulta pública de infraestructura y la aplicación cerrada de cada operador no hay
una capa que gestione la recarga completa del conductor, y esa capa es lo que este trabajo
construye.

## Motivación

El problema tiene tres propiedades que lo hacen buen material para un trabajo de fin de máster.
Es real, en el sentido de que lo padece cualquiera que conduzca un eléctrico en España hoy. Se
apoya en datos públicos reales: el catálogo nacional de puntos y la curva horaria del PVPC
—Precio Voluntario para el Pequeño Consumidor— que publica Red Eléctrica en una API abierta y
sin autenticación [4]. Y viene con restricciones que no se pueden negociar, que es
justamente lo que convierte un ejercicio de programación en un problema de ingeniería: la API
de REVE admite 5 peticiones/hora, un techo que descarta consultarla en tiempo real y obliga
a construir el sistema alrededor de una copia local sembrada poco a poco. Esa restricción
condiciona el modelo de datos, la planificación de la siembra y el diseño del proceso de
actualización, y se argumenta en el capítulo 5.

A eso se suma el atractivo de recorrer el ciclo entero. Concebir el producto, decidir su
arquitectura, escribir el backend y el cliente, desplegarlo en un servidor propio con HTTPS y
dejarlo accesible a cualquiera es un trabajo que rara vez cabe completo en un trabajo
académico, y es exactamente la parte que se defiende aquí.

## Objetivos

**Objetivo general.** Concebir, diseñar, desarrollar de extremo a extremo, desplegar y
argumentar la viabilidad de *S-Charge*, una PWA (*Progressive Web App*) que unifique en una
sola aplicación la gestión de la recarga de vehículo eléctrico en España, cubriendo lo que la
consulta pública de infraestructura no cubre.

| Id | Objetivo específico | Criterio de verificación |
| --- | --- | --- |
| **OE1** | Construir la aplicación de extremo a extremo: cliente instalable en el móvil, API propia, base de datos y sistema de identidad, con la cadena de comprobaciones automatizada. | La aplicación se instala y se usa en un móvil real; la API sirve las funcionalidades descritas en el capítulo 7; las comprobaciones de estilo, tipos y pruebas pasan en cada cambio. |
| **OE2** | Espejar en base de datos propia el catálogo nacional de puntos de recarga publicado por REVE, respetando su límite de 5 peticiones/hora, con un esquema alineado con el estándar sectorial OCPI (véase el capítulo 2). | Volumen de operadores, puntos, EVSE (*Electric Vehicle Supply Equipment*), conectores y tarifas almacenados y consultables desde la API, y siembra completada de forma desatendida. |
| **OE3** | Simular una recarga antes de enchufar, para el modelo de vehículo del usuario y el conector concreto de un punto, devolviendo energía, duración y coste. | Existe un servicio de simulación accesible desde la ficha del punto, con un algoritmo formulado y contrastable (capítulo 7). |
| **OE4** | Optimizar el momento de la recarga contra precios reales, ingiriendo a diario la curva horaria del PVPC y proponiendo la franja más barata para una necesidad energética y una hora de salida dadas. | La ingesta diaria de precios funciona y acumula histórico; el algoritmo queda formulado y evaluado en el capítulo 8. |
| **OE5** | Desplegar el sistema en producción y dejarlo accesible públicamente en un dominio propio bajo HTTPS, con entrega automatizada desde el repositorio. | La aplicación responde en `https://s-charge.app`, se instala desde producción y un cambio llega al servidor sin intervención manual (capítulo 10). |
| **OE6** | Argumentar la viabilidad del producto: coste de operación, modelo de ingresos, camino de escalado y límites conocidos del sistema. | Los capítulos 10 y 13 presentan costes reales, economía unitaria y los puntos de ruptura de un único servidor, y el capítulo 11 recoge lo medido frente a lo declarado. |

**Tabla 1.1.** Objetivos específicos y criterio con el que se evalúa cada uno. El capítulo 15
los revisa uno por uno.

## Alcance y límites

Cuatro límites se fijan aquí porque afectan a la lectura de todo lo demás.

**La disponibilidad en tiempo real no se modela.** El sistema no recibe un flujo constante de
estado de los puntos, de modo que la ocupación que muestra el mapa es ilustrativa. La
infraestructura de datos para admitir una fuente real existe, pero no hay tal fuente conectada,
y el trabajo lo declara en lugar de fabricar una ocupación verosímil.

**El monedero es simulado.** El movimiento económico entre conductor y propietario de un punto
se registra en un libro de apuntes interno; no hay pasarela de pago ni dinero real en ninguna
parte del sistema.

**No hay integración con el hardware de recarga.** El protocolo que comunica una estación con
el sistema de gestión de su operador, OCPP (*Open Charge Point Protocol*), queda fuera: vive
por debajo del operador, y esta aplicación se sitúa en el nivel de agregación, no en el de
control del equipo. La consecuencia práctica es que el sistema no arranca ni detiene una sesión
física.

**El despliegue es un único servidor.** Una máquina virtual con Docker Compose detrás de un
proxy inverso. El escalado horizontal se argumenta —dónde se rompe primero y qué lo sustituye
en cada escalón— pero no se construye (capítulo 10).

Queda un límite más, este sobre lo que se puede afirmar. La combinación que propone este
trabajo no es un territorio virgen: existe al menos una plataforma española, Place to Plug, que
ya conecta a conductores con anfitriones particulares que ofrecen su enchufe y permite
reservarlo [5]. La contribución defendible no es haber inventado la recarga entre
particulares, sino la **combinación** concreta —catálogo nacional espejado del registro
oficial, más puntos de particulares, más simulación por modelo de vehículo, más optimización
contra la curva de precios real, en una sola aplicación instalable— y el hecho de haberla
concebido, construido, desplegado y argumentado de principio a fin. El capítulo 2 sitúa a los
competidores con el detalle que merecen.

> **[FIGURA 1.2]** — *El hueco que ocupa S-Charge.* Diagrama de tres columnas: a la izquierda,
> las aplicaciones de operador (registro propio, tarifa propia, cobertura de su red); en el
> centro, la consulta pública de REVE (descubrimiento y planificación de ruta sobre toda la
> red); a la derecha, S-Charge, marcando qué toma de cada lado y qué añade (simulación,
> optimización de precio, puntos de particulares, reserva). Debe verse que las tres columnas no
> compiten en lo mismo.
> **Cómo obtenerla:** diagrama a dibujar en draw.io o Mermaid. No atribuir a un operador
> concreto ninguna función que no esté verificada en el capítulo 2.

## Estructura de la memoria

- **Capítulo 2 — Estado del arte.** REVE, las aplicaciones de operador, los agregadores y las
  plataformas entre particulares; los estándares del sector y dónde queda el hueco.
- **Capítulo 3 — Análisis y requisitos.** Roles, casos de uso, requisitos y metodología de
  trabajo por fases.
- **Capítulo 4 — Arquitectura del sistema.** Estructura de la solución, pila tecnológica y
  decisiones de diseño con sus alternativas descartadas.
- **Capítulo 5 — Modelo de datos y fuentes.** El estándar OCPI, el espejo del catálogo de REVE
  bajo el límite de peticiones, los precios y el catálogo de vehículos.
- **Capítulo 6 — Autenticación y seguridad.** Identidad, credenciales, sesión, límites de tasa,
  auditoría y el modelo de amenazas de robo de sesión.
- **Capítulo 7 — Funcionalidades de la aplicación.** Mapa, ficha de punto, simulación de
  recarga y las funcionalidades de plataforma.
- **Capítulo 8 — Optimización de la carga.** Formulación, pseudocódigo y evaluación del
  optimizador sobre la curva de precios.
- **Capítulo 9 — Asistente de IA.** La capa conversacional prevista sobre las APIs propias.
- **Capítulo 10 — Despliegue, operación y escalado.** La producción real, la cadena de entrega,
  el escalado argumentado y los costes.
- **Capítulo 11 — Validación y resultados.** Qué se ha probado y qué se ha medido.
- **Capítulo 12 — Marco regulador.** AFIR, la normativa española de información de recarga, el
  PVPC, la protección de datos y los derechos sobre los datos espejados.
- **Capítulo 13 — Entorno socioeconómico.** Negocio, viabilidad, presupuesto y planificación.
- **Capítulo 14 — Uso de IA generativa.** Cómo se ha empleado y con qué controles.
- **Capítulo 15 — Conclusiones.** Evaluación de los objetivos, aprendizajes y trabajo futuro.
