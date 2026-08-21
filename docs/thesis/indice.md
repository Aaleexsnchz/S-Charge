---
status: superado por memoria/ — se conserva como guion de origen
---

# Estructura de la memoria

> **La memoria ya está redactada en [memoria/](memoria/)**, con quince capítulos. Este documento
> fue el guion del que salió y se conserva porque recoge la intención de cada capítulo, pero
> **la estructura vigente es la de [memoria/README.md](memoria/README.md)**, no la de aquí.
>
> Tres diferencias que importan: la memoria añade **Marco regulador** (cap. 12) y **Entorno
> socioeconómico, presupuesto y planificación** (cap. 13), que la Escuela Politécnica exige y
> este guion no contemplaba; añade **Uso de IA generativa** (cap. 14) como capítulo propio en
> lugar de anexo; y separa **Validación y resultados** (cap. 11) de los capítulos de
> funcionalidad.

Índice de capítulos de la memoria del TFM y la idea central de cada uno. Los capítulos se
redactan en español; se conservan los términos técnicos consolidados en inglés (bearer token,
upsert, rate limit, ledger, etc.).

**Tesis central.** El núcleo del trabajo es **la propia aplicación**: una PWA unificada
de gestión de recarga de vehículo eléctrico que agrupa, bajo una sola app, lo que hoy
está fragmentado en la aplicación de cada operador, y mejora la app pública de REVE (que
solo permite consultar puntos y planificar una ruta). El optimizador de carga y las
funciones de IA/agentes son **funcionalidades de valor añadido** de la aplicación, no
núcleos separados. La contribución es concebir, diseñar, desarrollar de extremo a extremo,
desplegar y argumentar la viabilidad del producto.

## Capítulos

1. **Introducción** — contexto de la movilidad eléctrica en España; el problema (apps
   fragmentadas por operador; la app de REVE solo consulta puntos y planifica rutas);
   motivación, objetivos y alcance del trabajo.

2. **Estado del arte** — REVE y las aplicaciones de los CPOs: qué ofrecen y sus límites;
   estándares relevantes (OCPI 2.2.1); el hueco que cubre una plataforma unificada.

3. **Análisis y requisitos** — roles **conductor** y **propietario**; casos de uso;
   requisitos funcionales y no funcionales (PWA mobile-first, 360px de referencia).

4. **Arquitectura del sistema** — visión de conjunto: PWA, backend FastAPI, Postgres y el
   modelo OCPI 2.2.1; decisiones de diseño (enlaza a los ADRs en [decisions/](../decisions/)).

   4.1. **Stack tecnológico** — qué se usa en ejecución y por qué: React + Vite + Tailwind y
   shadcn/ui en el cliente; FastAPI, SQLAlchemy y PostgreSQL 18 en el servidor; Caddy y Docker
   Compose en producción. Se redacta como narrativa, no como inventario: el listado completo y
   vivo, con una línea de justificación por herramienta, vive en
   [tech-stack.md](../tech-stack.md) y no se duplica aquí.

   4.2. **Decisiones revisadas** — PostgreSQL 18, Python 3.13, entorno de desarrollo nativo y
   cadena de herramientas, recogidas en [tech-stack.md](../tech-stack.md). Por qué las
   decisiones iniciales fueron correctas, por qué caducan y cómo se verifica cada cambio.

5. **Datos y modelo** — REVE como _mirror_ sembrado una sola vez y servido desde Postgres
   ([data-model.md](modelo-de-datos.md)); precios PVPC de REE y estrategia de estimación
   ([precios-y-actualizacion.md](precios-y-actualizacion.md)); planificación de la siembra
   bajo el límite de la API ([seed-scheduling.md](planificacion-de-siembra.md)); catálogo de
   vehículos. Incluye **"camino no tomado: ACN-Data"**: el dataset histórico de Caltech
   se consideró para calibrar la simulación de ocupación y el realismo de las sesiones;
   se descartó porque no aportaba nada de cara al usuario, quedaba como dato interno y no
   llegó a integrarse. Se documenta como decisión razonada, junto con el segundo paso del
   mismo camino: el modelo sintético ligero que iba a sustituirlo y que también se abandonó.
   La disponibilidad **no se modela** y la memoria lo declara explícitamente.

6. **Autenticación y seguridad** — identidad, almacenamiento de contraseñas, sesión por
   cookie, OAuth, verificación, auditoría y _rate limiting_ ([auth.md](autenticacion.md)); modelo
   de amenazas de robo de sesión ([session-theft.md](robo-de-sesion.md)).

7. **Funcionalidades de la aplicación** — mapa con filtros y navegación; detalle de punto;
   reservas; puntos de carga privados con uso de pago; **monedero/ledger** simulado;
   simulación de recarga previa ([simulacion-de-recarga.md](simulacion-de-recarga.md)).

8. **Optimización de carga** — algoritmo de coste/tiempo sobre la curva PVPC: formulación,
   pseudocódigo y evaluación. Funcionalidad de valor añadido y capítulo algorítmico de la
   memoria.

9. **Asistente / agentes de IA** — _candidato, según el tiempo disponible_; qué valor
   aporta como diferenciador (ideas en [ideas-backlog.md](../ideas-backlog.md)). La defensa
   no depende de este capítulo.

10. **Despliegue, escalado y operación** — despliegue real (HTTPS, PWA instalable);
    **cadena de herramientas de desarrollo y entrega**: gestores de paquetes y bloqueo de
    versiones, linters y comprobación de tipos, hooks de git, integración y despliegue
    continuos, versionado y releases, actualización de dependencias. Va aquí, y no en el
    capítulo de arquitectura, porque es proceso de ingeniería y no estructura del sistema.
    Después: **arquitectura para escalar**, argumentada y no implementada — dónde se rompe
    primero un único servidor, qué lo sustituye en cada escalón (Postgres gestionado, registro
    de imágenes, segundo nodo tras un balanceador) y por qué la orquestación de contenedores
    (Kubernetes) solo se justifica cuando hay una flota que planificar. Justificar que **no**
    se usa a esta escala es tan resultado como describir cuándo se usaría. Y costes.

11. **Modelo de negocio y viabilidad** — propuesta de valor, modelo de ingresos
    (comisión sobre sesiones de puntos públicos), economía unitaria y rentabilidad.

12. **Hoja de ruta futura** — mejoras pendientes y transición a una app móvil nativa.

13. **Conclusiones** — resultados, aprendizajes y líneas de trabajo futuras.

**Anexo — Metodología de desarrollo asistido** ([skills.md](skills.md)): qué skills de agente se
han usado, para qué, y cómo se reproducen desde el *lockfile*. Transparencia metodológica y
reproducibilidad.

## Capítulos ya redactados (nivel conceptual)

Estos documentos existen y alimentan los capítulos anteriores:
[auth.md](autenticacion.md) · [data-model.md](modelo-de-datos.md) ·
[precios-y-actualizacion.md](precios-y-actualizacion.md) ·
[seed-scheduling.md](planificacion-de-siembra.md) · [session-theft.md](robo-de-sesion.md) ·
[simulacion-de-recarga.md](simulacion-de-recarga.md) · [skills.md](skills.md).

Los capítulos de negocio, despliegue/escalado y hoja de ruta se redactan en la fase de
redacción (`modelo-de-negocio.md`, `despliegue-y-escalado.md`, `hoja-de-ruta.md`); aún no
existen.
