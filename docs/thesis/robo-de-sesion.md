---
title: Robo de sesión y replay de bearer tokens
status: borrador (redacción de la memoria, nivel conceptual)
---

# Robo de sesión y replay de bearer tokens

La mecánica de sesión descrita en [auth.md](autenticacion.md) defiende contra el modelo de amenazas estándar de una SPA: exfiltración por XSS, CSRF, credential stuffing y abuso de cuentas no verificadas. **No** defiende contra la vía de apropiación de cuentas que domina los informes de incidentes de cuentas de consumo desde 2024 — **el robo de la cookie de sesión por malware de tipo information stealer ejecutándose en la propia máquina del usuario, seguido de su replay desde un navegador controlado por el atacante**. Este capítulo registra por qué existe esa brecha, por qué no puede cerrarse dentro de una aplicación, y dónde se sitúa la frontera defensiva.

## La amenaza

Un equipo comprometido — típicamente el resultado de un vector de ingeniería social como un CAPTCHA falso que pide al usuario pegar un script en un terminal ("ClickFix") — ejecuta un information stealer (Lumma, Vidar, StealC, históricamente RedLine) bajo la propia cuenta de SO del usuario. El stealer lee el almacén de cookies del navegador, las contraseñas guardadas, `localStorage` y la huella del navegador, y lo sube todo como un "log" que se vende en mercados de comodities. El comprador carga el log en un **navegador anti-detección** (Octo, Genesium, Dolphin{anty}) configurado con un **proxy residencial** geolocalizado cerca de la víctima, presenta la cookie de sesión robada, y queda autenticado como la víctima desde la primera petición.

Dos propiedades hacen que el ataque sea difícil de detectar en la capa del relying party:

- *La cookie robada es una prueba de identidad completa.* Es la *salida* de un inicio de sesión previamente exitoso, con cualquier factor MFA ya satisfecho. No se invoca ningún paso de re-autenticación; el MFA no se vuelve a solicitar.
- *El atacante presenta la huella de la víctima y su geografía IP aproximada.* `User-Agent`, hash de canvas, hash de WebGL, zona horaria e idioma coinciden. El motor de riesgo del proveedor de identidad, que depende de señales de anomalía, no ve ninguna anomalía. Los paneles de "actividad reciente" siguen atribuyendo las peticiones al dispositivo que *acuñó* la sesión, no al host que realiza cada petición individual.

Un usuario con MFA hardware, sin reutilización de contraseñas y sin inicios de sesión desde dispositivos nuevos puede aun así perder todas las cuentas cuyas cookies de sesión estuvieran en el perfil del navegador en el momento en que se ejecutó el stealer.

## El problema del bearer token

La causa raíz es arquitectónica, no de implementación: las cookies de sesión HTTP son **bearer tokens**. La posesión de la cadena del token equivale, por protocolo, a la posesión de la credencial. Nada en la cadena de peticiones liga el token al dispositivo que lo emitió. Toda sesión web moderna — cookies `HttpOnly` incluidas — tiene esta propiedad una vez que la cookie llega a un atacante.

El diseño de sesión de [auth-0002](../decisions/auth-0002-cookie-session.md) es explícito en su alcance: `HttpOnly` neutraliza la exfiltración por **JavaScript** (XSS), y ese es su objetivo de diseño. No puede neutralizar la exfiltración por **código nativo ejecutándose como el mismo usuario de SO que el navegador**, porque ninguna aplicación puede. En un SO de escritorio monousuario, la frontera de seguridad es el proceso que el usuario decide ejecutar, no la aplicación que custodia la credencial — el almacén de cookies del navegador es, por necesidad, legible por el proceso del navegador, que se ejecuta como el usuario, junto a cualquier otro código que el usuario ejecute.

## Qué puede hacer una aplicación

Las defensas contra el replay de bearer tokens caen en tres categorías:

| Categoría | Mecanismo | Efecto |
|---|---|---|
| Hacer el token no-bearer | [DBSC][dbsc] (Device-Bound Session Credentials), [DPoP][dpop] (RFC 9449) | Cada petición lleva una firma de una clave residente en el TPM / Secure Enclave del dispositivo. La cookie por sí sola es insuficiente; la clave de firma no puede ser exfiltrada por código en espacio de usuario. Ataca la causa raíz. |
| Re-autenticar antes de acciones sensibles | Step-up con WebAuthn / passkey en cambio de email, cambio de contraseña, consentimiento OAuth a nuevos relying parties | La sesión robada puede navegar pero no escalar. Cierra el pivote de apropiación característico de los incidentes reales (sesión robada → "Iniciar sesión con Google" en un tercero → enlace de restablecimiento de contraseña a una bandeja leída con la misma sesión → apropiación permanente). |
| Limitar el radio de daño si roban un token | TTL cortos, rotación de refresh con detección de reutilización, revocación en servidor respaldada por BD | Reduce la ventana de explotación; no la previene. |

Las dos primeras categorías son las decisivas. DBSC en particular, desplegándose en Chrome y Google durante 2025–26, es el primer mecanismo de adopción amplia que rompe la asunción de bearer token en las sesiones web cotidianas — y al aplicarse en la capa del proveedor de identidad, toda sesión derivada de OAuth aguas abajo de una cuenta de Google protegida por DBSC hereda parte del beneficio.

## Qué hace este proyecto, y qué no

La sesión del TFM implementa solo la categoría tres: una cookie JWT `HttpOnly; Secure; SameSite=Lax` con TTL de 14 días ([auth-0002](../decisions/auth-0002-cookie-session.md)), con la revocación respaldada por BD como endurecimiento futuro plausible. La categoría uno no está implementada: DBSC está liderado por los fabricantes de navegadores y aún no es una primitiva estable de cara al relying party, y DPoP exigiría un transporte sin cookies que auth-0002 rechaza específicamente para una PWA same-origin. La categoría dos — step-up WebAuthn en acciones sensibles — es viable en la capa de aplicación y una adición creíble más adelante, pero queda fuera del alcance actual: la superficie de modificación de cuenta es pequeña (cambio de contraseña y de email, ambos custodiados por verificación con enlace de email en el IdP) y no justifica por sí sola el coste de la ceremonia WebAuthn.

La respuesta honesta en la defensa a *"¿por qué esto no es resistente al robo de sesión?"* es que ninguna aplicación actual lo es bajo el modelo de bearer token. Las dos defensas que cambian esa respuesta o bien no son todavía una primitiva expuesta al relying party (DBSC) o bien son un endurecimiento añadible de forma incremental y no una omisión de diseño (step-up WebAuthn). La sesión con cookie de [auth-0002](../decisions/auth-0002-cookie-session.md) está dimensionada para las amenazas SPA dominantes; la amenaza posterior al compromiso del equipo se reconoce como fuera de alcance, no como un descuido.

## Incidentes de referencia

El patrón alcanzó visibilidad pública a través de apropiaciones de cuentas de alto perfil impulsadas por infostealers en plataformas sin requisito de step-up para acciones sensibles — de forma más prominente, servicios de chat y videojuegos de consumo durante 2024–25. La mecánica es consistente: stealer → log de cookies → navegador anti-detección → "Iniciar sesión con Google" o equivalente → enlace de restablecimiento por email → apropiación permanente. El mismo patrón es el ejemplo motivador del borrador del grupo de trabajo de DBSC y de la ampliación de los re-prompts FIDO2 de Google Advanced Protection a los flujos de consentimiento OAuth durante 2025.

[dbsc]: https://w3c.github.io/webappsec-dbsc/
[dpop]: https://datatracker.ietf.org/doc/html/rfc9449
