---
status: borrador (estructura de la memoria)
---

# Estructura de la memoria

Índice de capítulos de la memoria del TFM y la idea central de cada uno. Es un guion
vivo: se ajusta conforme avanza el desarrollo. Los capítulos se redactan en español;
se conservan los términos técnicos consolidados en inglés (bearer token, upsert, rate
limit, ledger, etc.).

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

4. **Arquitectura del sistema** — PWA React + Vite + MUI, backend FastAPI, Postgres,
   Docker Compose; el modelo OCPI 2.2.1; decisiones de diseño (enlaza a los ADRs en
   [decisions/](../decisions/)).

5. **Datos y modelo** — REVE como _mirror_ sembrado una sola vez y servido desde Postgres
   ([data-model.md](modelo-de-datos.md)); precios PVPC de REE y estrategia de estimación
   ([precios-y-actualizacion.md](precios-y-actualizacion.md)); planificación de la siembra
   bajo el límite de la API ([seed-scheduling.md](planificacion-de-siembra.md)); catálogo de
   vehículos. Incluye **"camino no tomado: ACN-Data"**: el dataset histórico de Caltech
   se consideró para calibrar la simulación de ocupación y el realismo de las sesiones;
   se descartó porque no aportaba nada de cara al usuario, quedaba como dato interno y no
   llegó a integrarse. Se documenta como decisión razonada (qué prometía, por qué se
   abandonó, qué lo sustituye: un modelo sintético ligero, solo ilustrativo).

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
    arquitectura para escalar y operar a muchos usuarios; costes.

11. **Modelo de negocio y viabilidad** — propuesta de valor, modelo de ingresos
    (comisión sobre sesiones de puntos públicos), economía unitaria y rentabilidad.

12. **Hoja de ruta futura** — mejoras pendientes y transición a una app móvil nativa.

13. **Conclusiones** — resultados, aprendizajes y líneas de trabajo futuras.

## Capítulos ya redactados (nivel conceptual)

Estos documentos existen y alimentan los capítulos anteriores:
[auth.md](autenticacion.md) · [data-model.md](modelo-de-datos.md) ·
[precios-y-actualizacion.md](precios-y-actualizacion.md) ·
[seed-scheduling.md](planificacion-de-siembra.md) · [session-theft.md](robo-de-sesion.md).

Los capítulos de negocio, despliegue/escalado y hoja de ruta se redactan en la Fase 7
(`modelo-de-negocio.md`, `despliegue-y-escalado.md`, `hoja-de-ruta.md`); aún no existen.
