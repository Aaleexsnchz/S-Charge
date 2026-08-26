# 12. Marco regulador

## De dónde sale el dato que la aplicación sirve

El Reglamento (UE) 2023/1804 (AFIR) obliga a cada operador de punto de recarga (CPO) a poner a
disposición sin coste los datos estáticos de sus instalaciones y los dinámicos —estado
operativo, disponibilidad y precio por operación— mediante una API de «acceso libre y no
restringido» comunicada a los puntos de acceso nacionales [15]. Que exista un catálogo
nacional consultable por un tercero no es una cortesía de quien lo publica, sino el resultado de
una norma; en qué condiciones ese tercero puede copiarlo y volver a servirlo es otra cuestión, y
queda abierta al final del capítulo. El artículo 5 fija además cómo se presenta el precio: en
puntos de 50 kW o más el importe de la operación se basa en el precio por kWh y debe mostrarse
antes de iniciar la sesión [15]. De ahí que el sistema modele la tarifa en €/kWh como
magnitud primaria: no es una simplificación de diseño, es la unidad que la norma impone al
operador.

La cadena española es más precisa, y de ella sale la decisión de diseño más determinante del
trabajo. El Real Decreto 184/2022 obliga en su artículo 10 a remitir al MITECO la localización,
características, disponibilidad y precio de venta al público de cada instalación [12];
la Orden TED/445/2023 lo desarrolla y sitúa la información estática en el registro RIPREE
[13]; y la **Resolución de 2 de abril de 2025** crea el Sistema de Gestión y
Visualización para la información dinámica, encarga su operación a Red Eléctrica de España y
fija **OCPI —2.2.1, 2.2 y 2.1.1— como protocolo estándar de comunicación** [11].

La consecuencia suele contarse al revés: el esquema de datos de esta aplicación reproduce la
topología OCPI —emplazamiento, EVSE, conector [28]— **porque una norma española la
impone en origen**, no por afinidad técnica con un estándar. El manual de integración del
operador del sistema lo formula igual: el punto de recarga «tiene equivalencia con el objeto
EVSE del protocolo OCPI y es coherente con la definición que se hace en el Reglamento AFIR»
[29]. Un modelo distinto no habría sido una alternativa de ingeniería, sino una
capa de traducción sobre una jerarquía fijada desde el BOE.

> **[FIGURA 12.1]** — *La cadena normativa hasta el modelo de datos.* Diagrama de flujo vertical
> en cinco cajas encadenadas: Reglamento (UE) 2023/1804 (art. 20: datos estáticos y dinámicos,
> acceso libre) → RD 184/2022 (art. 10: remisión al MITECO) → Orden TED/445/2023 (contenido y
> forma; RIPREE para lo estático) → Resolución de 2 de abril de 2025 (SGV operado por REE;
> **OCPI 2.2.1** como protocolo) → esquema de este trabajo (`cpos` → `charging_points` →
> `evses` → `connectors`). Etiquetar la última flecha con «la jerarquía llega impuesta, no
> elegida», que es el argumento del apartado. **Cómo obtenerla:** diagrama a dibujar en Mermaid
> (`flowchart TD`).

## El PVPC es un precio regulado, no una estimación

El Real Decreto 216/2014 sigue siendo la norma base del Precio Voluntario para el Pequeño
Consumidor (PVPC) y el Real Decreto 446/2023 lo **modifica**, no lo sustituye: reescribe el
término de ajuste como $TaE = (A - 1)\cdot P_{mah} + B\cdot F_t$, indexando parte del precio a
una cesta de futuros para reducir su volatilidad [56][61]. Los coeficientes
$A = 0,45$ y $B = 0,55$ rigen desde 2026, tras un transitorio en 2024 y 2025 con más peso del
mercado diario, y la norma obliga al operador del sistema a publicar los términos del coste de
producción antes de las 20:15 del día anterior al del suministro. De esa hora sale la ventana de
ingesta diaria, y de la norma sale lo que hace defendible calcular costes con este precio: no se
estima nada ni se promedian tarifas comerciales, se consume un precio que un organismo oficial
está obligado a calcular con una fórmula publicada y a difundir a una hora fijada.

Sobre la granularidad conviene ser exacto. La API pública de REData devuelve el PVPC en 24
valores horarios mientras el precio spot ya viene en 96 períodos cuarto-horarios
[10]; el sistema está construido sobre esos 24 valores y los consume así. Cómo se ha
adaptado formalmente el PVPC a esa granularidad no se ha verificado, y este capítulo no afirma
que la norma vigente lo defina como horario.

> **PENDIENTE:** comprobar en el BOE si el RD 216/2014 ha sido modificado tras el paso del
> mercado mayorista a 96 períodos, y qué granularidad establece hoy para el PVPC.

## Protección de datos

El sistema trata cuatro datos personales y ninguno más: **correo electrónico** y **nombre** en la
tabla de usuarios, **identidad del proveedor OAuth** en la de vinculación, y **dirección IP** en
los registros de auditoría y como clave de los límites de tasa. No se almacena posición —la del
navegador centra el mapa y no se persiste—, ni historial, ni datos de pago.

Correo, nombre e identidad de proveedor son los datos sin los cuales no hay cuenta: se tratan
para prestar el servicio que el usuario solicita al registrarse. La IP exige más argumentación.
*Breyer* no declara que toda IP dinámica sea dato personal en abstracto: condiciona la
calificación a que el responsable disponga de medios legales para identificar al interesado con
datos adicionales del proveedor de acceso [53]. En un servicio abierto al público
en España esa condición se cumple con normalidad, así que se trata como dato personal. La base
jurídica es el interés legítimo del artículo 6.1.f, y el considerando 49 declara legítimo el
tratamiento «estrictamente necesario y proporcionado para garantizar la seguridad de la red y de
la información» [35]: un registro de auditoría de autenticación y una clave de límite de
tasa son ese caso. Lo que obliga no es el consentimiento, sino informar, no reutilizar el dato y
acotar su conservación —hoy acotada por volumen y no por tiempo (capítulo 6).

Los derechos de acceso, rectificación, supresión y portabilidad de los artículos 15 a 20, y la
notificación de brechas en un máximo de 72 horas del artículo 33.1, son exigibles desde el primer
usuario real [35]. **Ninguno está implementado**, ni hay política de privacidad
publicada, ni contratos de encargado con los tres proveedores que procesan datos por cuenta del
servicio —alojamiento, correo transaccional e identidad—, ni política de conservación.

La supresión, además, no es un endpoint que falte. Borrar un usuario obliga a decidir qué ocurre
con lo que cuelga de él, y la respuesta no es la misma para todo: una reserva cancelada puede
desaparecer con la cuenta, pero una sesión facturada y su apunte en el monedero sostienen
obligaciones contables que sobreviven a la petición, así que lo razonable es disociar el hecho
económico de su titular antes que borrar la fila. Y el dato sigue en las copias de seguridad
—volcados nocturnos— hasta que la retención las rota, lo que obliga a declarar ese plazo al
interesado en lugar de prometer una desaparición inmediata. Argumentar la postura es trabajo
legítimo; no haberlo pensado no lo sería.

> **PENDIENTE:** declarar por escrito la base jurídica de cada categoría de dato, su plazo de
> conservación y el de rotación de las copias, y redactar la política de privacidad y los
> contratos de encargado antes de admitir a un usuario que no sea el propio autor.

## La cookie de sesión y el artículo 22.2

El artículo 22.2 de la LSSI exceptúa el almacenamiento «en la medida que resulte estrictamente
necesario, para la prestación de un servicio de la sociedad de la información expresamente
solicitado por el destinatario» [62]. La guía de la AEPD desarrolla la excepción
con una lista cerrada de finalidades y, en lo que aquí importa, la enuncia así: cookies «de
autenticación o identificación de usuario (**únicamente de sesión**)» [63].

El sistema instala una sola cookie, y su contenido es un JWT firmado con 14 días de vida. La
tentación es darla por exenta. El análisis honesto es menos cómodo: por finalidad encaja de
lleno —sin ella la API devuelve 401 en todo salvo la comprobación de salud y la propia
autenticación—, pero por duración no es «únicamente de sesión», porque sobrevive al cierre del
navegador, que es justo lo que la formulación de la AEPD acota. Reducirla a cookie de sesión
estricta la sitúa dentro de la letra de la excepción, al precio de exigir un inicio de sesión en
cada apertura: coste real para alguien de pie junto a un poste con el móvil en la mano.
Mantener los 14 días obliga a defender que la persistencia sigue siendo estrictamente necesaria
para el servicio solicitado, lo que es sostenible pero ya no automático, y a informarlo en una
política que no existe. Lo que no es defendible es la tercera vía, que es la actual: 14 días,
ninguna información y la excepción dada por supuesta.

## Derechos sobre el catálogo espejado

La aplicación mantiene una copia del catálogo público y se la sirve a sus usuarios. Son dos actos
distintos y conviene no fundirlos: **copiar** para uso propio y **volver a poner a disposición
del público**. El segundo es el que hay que justificar, y para ello habría que establecer tres
cosas. Los términos de uso de la fuente, que fijan lo que el titular permite al margen de
cualquier otro título. Si el catálogo atrae el derecho *sui generis* sobre bases de datos: la
Directiva 96/9/CE lo concede a quien acredite una inversión sustancial en la obtención,
verificación o presentación del contenido y le permite impedir la extracción o reutilización de
una parte sustancial, con un plazo que una base actualizada de forma continua puede renovar
[64]; un registro nacional mantenido de forma permanente encaja en ese perfil, y el
derecho opera **al margen** del derecho de autor. Y la atribución: si se debe, con qué texto y
dónde. Que el dato se sirva solo a usuarios autenticados ayuda menos de lo que parece: reduce
exposición y volumen, no convierte la reutilización en otra cosa.

**Los términos de uso de la fuente no se han podido verificar.** El *endpoint* que consume el
proyecto responde `HTTP 403` sin credenciales y no se localizó aviso legal legible, al servirse
el sitio como aplicación de una sola página [6]. Este capítulo no concluye que el
espejado esté permitido ni que no lo esté: «se espeja un dato público» no es por sí solo un
argumento jurídico. La misma laguna afecta a la licencia de reutilización de los precios, con
menor riesgo por tratarse de una API abierta sin autenticación [10].

> **PENDIENTE:** abrir `mapareve.es` en un navegador real, leer aviso legal y condiciones y, si
> no hay licencia explícita, solicitarla por escrito al MITECO y a Red Eléctrica; repetir la
> comprobación para `ree.es` y para `datos.gob.es`; y comprobar si el artículo 43 del Data Act
> excluye del derecho *sui generis* datos como estos. Sin eso, la explotación fuera del ámbito
> académico no debería iniciarse.

## Accesibilidad

La Directiva (UE) 2016/2102 impone requisitos de accesibilidad a los sitios y aplicaciones de
**los organismos del sector público**, de modo que una aplicación privada queda fuera de su
ámbito [65]. La que sí podría alcanzarla es la Directiva (UE) 2019/882, aplicable
desde el 28 de junio de 2025, que cubre servicios de consumo entre los que figura el comercio
electrónico y exime del lado de los servicios a las microempresas [66]. Ambas se
conocen aquí por fuentes secundarias, así que el encaje se plantea como hipótesis: un servicio
que hoy solo consulta información probablemente no presta un servicio de comercio electrónico,
pero las reservas, el monedero y las sesiones de pago de las fases 9 y 10 cambiarían esa
conversación.

La referencia técnica es WCAG 2.2 [36], y lo hecho es modesto: el analizador estático del
frontend aplica el conjunto de reglas de accesibilidad y rompe la compilación cuando se
incumplen, y la auditoría Lighthouse de junio de 2026 dio 100 en accesibilidad en `/map` y 98 en
`/login`. No conviene venderlo como conformidad: una puntuación automática cubre una fracción de
los criterios y no dice nada sobre navegación por teclado ni lectores de pantalla.

> **PENDIENTE:** determinar, leyendo el artículo 2 de la Directiva (UE) 2019/882, si el servicio
> con monedero entra en su ámbito y si aplicaría la exención de microempresa; en caso
> afirmativo, revisión manual de conformidad con WCAG 2.2 nivel AA.

## Situación de cumplimiento

| Obligación | Situación | Qué haría falta |
| --- | --- | --- |
| Modelo de datos conforme a OCPI (Resolución de 2 abr. 2025) | Cumplido | — |
| Precio unitario en €/kWh como magnitud primaria (AFIR art. 5.4) | Cumplido | Desglose completo de componentes cuando existan tarifas propias (fase 8) |
| Disponibilidad en tiempo real (AFIR art. 20) | No abordado | Dato ausente en la fuente; exigiría integración OCPI con cada CPO |
| Base jurídica del tratamiento de la IP (art. 6.1.f y cons. 49) | Parcial | Base decidida y registrada; falta declararla al interesado |
| Limitación del plazo de conservación (art. 5.1.e) | Parcial | Rotación por volumen; falta política en tiempo, también para las copias |
| Política de privacidad publicada | No abordado | Redactarla y publicarla antes del primer usuario externo |
| Contratos de encargado del tratamiento (art. 28) | No abordado | Firmarlos con alojamiento, correo transaccional e identidad |
| Derechos de acceso, rectificación y portabilidad (arts. 15-20) | No abordado | Exportación de los datos de la cuenta y vía de contacto declarada |
| Derecho de supresión (art. 17) | No abordado | Decidir disociación frente a borrado por entidad y declarar el plazo de las copias |
| Notificación de brechas en 72 horas (art. 33.1) | No abordado | Procedimiento escrito; hoy no hay observabilidad que detecte la brecha |
| Cookie de sesión y art. 22.2 LSSI | Parcial | Reducir a cookie de sesión o justificar e informar los 14 días |
| Condiciones de reutilización del catálogo espejado | No abordado | Verificar términos y licencia; atribución en la ficha de punto y aviso legal |
| Accesibilidad WCAG 2.2 AA | Parcial | Ámbito por confirmar; revisión manual más allá de la auditoría automática |

**Tabla 12.1.** Obligaciones que alcanzan al sistema, situación real a fecha de esta memoria y
trabajo necesario en cada una. «Parcial» significa que la decisión está tomada y documentada,
pero no completamente ejecutada.
