# Anexos

Los anexos recogen el material que respalda el cuerpo de la memoria pero que, incorporado a él,
lo haría ilegible. Cada uno indica de dónde se genera, para que ninguno se escriba a mano dos
veces.

> **PENDIENTE:** este fichero es el guion de los anexos, no su contenido. Cada apartado lleva la
> instrucción de cómo producirlo. El anexo A es obligatorio y debe cumplimentarlo el autor.

---

## Anexo A — Declaración de uso de IA generativa

**Obligatorio.** Formulario oficial de la Universidad Carlos III de Madrid, cumplimentado y
firmado por el autor, declarando los usos descritos en el capítulo 12.

> **PENDIENTE:** descargar el formulario vigente de la guía de la biblioteca de la UC3M sobre IA
> generativa en el TFM, cumplimentarlo marcando los usos que el capítulo 12 describe —asistencia
> a la redacción sobre documentación técnica propia previa, y asistencia al desarrollo del
> software— y adjuntarlo aquí.

## Anexo B — Manual de instalación y despliegue

Cómo levantar el sistema desde un clon del repositorio y cómo se despliega en producción:
requisitos previos, configuración, arranque de la base de datos, migraciones, ejecución de
backend y frontend, y el procedimiento de despliegue y de vuelta atrás.

**Cómo generarlo:** condensar `README.md` (arranque rápido y comandos), `docs/setup/deployment.md`
(aprovisionamiento del servidor) y `docs/operations.md` (operación, copias de seguridad, acceso
a la base de datos de producción y actualizaciones mayores de PostgreSQL). No reescribir: extraer
y ordenar.

## Anexo C — Esquema completo de la base de datos

Diagrama entidad-relación y descripción de las diez tablas —`users`, `oauth_account`, `cpos`,
`charging_points`, `evses`, `connectors`, `tariffs`, `vehicles`, `electricity_prices` y
`reve_etl_cursor`— con sus columnas, tipos, claves y restricciones.

**Cómo generarlo:** a partir de `backend/app/models/` y del histórico de migraciones de
`backend/alembic/versions/`. El diagrama puede obtenerse con una herramienta de ingeniería
inversa sobre la base de datos real, o dibujarse a partir de las relaciones declaradas en los
modelos.

## Anexo D — Catálogo de la API REST

Los endpoints publicados, con método, ruta, parámetros, esquema de respuesta y códigos de error.

**Cómo generarlo:** directamente desde `openapi.json`, que está versionado en la raíz del
repositorio y que CI mantiene sincronizado con el código. Es el anexo más barato de producir y
el que documenta la superficie contractual del sistema.

## Anexo E — Registro de decisiones de arquitectura

Los quince registros de decisión, cada uno con su decisión, sus razones, sus consecuencias y
**las alternativas rechazadas**, que son la parte que demuestra criterio.

**Cómo generarlo:** desde `docs/decisions/`. Conviene una tabla índice al principio —
identificador, título, fase, estado — y a continuación el contenido de cada registro. Si el
espacio aprieta, la tabla índice más los cuatro o cinco registros más significativos
(`be-0001` espejo frente a proxy, `auth-0002` sesión por cookie, `be-0002` disponibilidad no modelada,
`infra-0001` despliegue) cubren lo esencial.

## Anexo F — Galería de pantallas

Las capturas de la aplicación que no caben en el cuerpo, comentadas. El capítulo 7 marca las que
van en el cuerpo; el resto vive aquí.

**Cómo generarlo:** capturas a 360 px de ancho sobre el despliegue de producción, con una cuenta
de demostración. Incluir al menos: las seis pantallas de autenticación, el mapa con distintos
filtros activos, la ficha de punto completa, el diálogo de simulación con su resultado, el
dashboard y las pantallas con maqueta etiquetada «datos de ejemplo» — estas últimas importan,
porque documentan la disciplina de no presentar como real lo que no lo es.

## Anexo G — Skills de agente y reproducibilidad

Qué *skills* de agente se usaron durante el desarrollo, para qué sirvió cada una en este
proyecto concreto, y cómo se reproducen desde el fichero de anclaje de versiones. Complementa el
capítulo 12.

**Cómo generarlo:** desde `docs/thesis/skills.md` y `skills-lock.json`.

## Anexo H — Glosario de siglas y términos

**Cómo generarlo:** recorrer la memoria recogiendo las siglas desarrolladas en su primera
aparición. Como mínimo: AFIR, BEV, CCS, CPO, CSP, DC/AC, eMSP, ETL, EVSE, HSTS, IEC, JWT, OCPI,
OCPP, ODS, PVPC, PWA, RGPD, SoC, SPA, TLS, VPS.

---

## Anexo opcional — Catálogo de vehículos

Los 31 modelos sembrados, con capacidad útil de batería y potencia máxima en AC y en DC.
Incluir solo si la memoria necesita cuerpo; su valor es documentar el criterio de curación de
datos descrito en el capítulo 5.

**Cómo generarlo:** desde `backend/scripts/seed_vehicles.py` o consultando la tabla `vehicles`.
