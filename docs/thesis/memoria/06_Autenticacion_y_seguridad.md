# 6. Autenticación y seguridad

La autenticación no se ensambló a partir de primitivas de FastAPI, sino que se delegó en `fastapi-users`, una librería mantenida cuyos valores por defecto coinciden con la guía vigente de OWASP. Elegir la librería equivale a adoptar esas decisiones, y este trabajo no las vuelve a litigar una por una: lo que sí se registra son los dos puntos en los que se desvía deliberadamente de ella —el transporte de la sesión y el modelo de amenazas de la vinculación de cuentas— y las decisiones que la librería no toma.

## Identidad

Las claves primarias de usuario son UUID v4, con 122 bits de entropía. Un identificador no enumerable evita que el conocimiento de un usuario permita recorrer los demás, y descarta de raíz la clase de fuga en la que un identificador secuencial revela el volumen de la base o el orden de alta.

El correo electrónico se almacena en `citext`, el tipo de texto sin distinción de mayúsculas de PostgreSQL, y el esquema de entrada lo normaliza a minúsculas y sin espacios. Lo relevante no es la normalización, que cualquier capa puede hacer, sino **dónde vive la invariante**: la unicidad sin distinción de mayúsculas es una restricción de la base de datos, no una comprobación del código. La parte local de una dirección es sensible a mayúsculas según el RFC 5321, de modo que `Alice@x.com` y `alice@x.com` son, formalmente, dos direcciones distintas que en la práctica totalidad de los proveedores entregan al mismo buzón. Sin la restricción, dos cuentas separadas comparten bandeja de entrada, y con ella comparten también los enlaces de verificación y de restablecimiento de contraseña: el camino corto hacia la apropiación de la cuenta ajena. Poner la invariante en el motor significa que un endpoint nuevo, escrito por alguien que no conozca este razonamiento, no puede saltársela.

## Almacenamiento de contraseñas

Argon2id con `memory_cost=19456`, `time_cost=2` y `parallelism=1`, es decir, 19 MiB de memoria y dos iteraciones. Son los parámetros mínimos que recomienda OWASP [39], y no los del RFC 9106, que propone como primera opción 2 GiB de memoria por hash [40]. La divergencia entre ambas fuentes es grande y conviene decir cuál se sigue y por qué: 2 GiB por verificación son inviables en un servidor de 4 GB que además aloja la base de datos, y bastarían diez inicios de sesión simultáneos para agotar la máquina. Se sigue el criterio de OWASP, que está formulado precisamente como un suelo alcanzable en hardware ordinario.

El verificador re-calcula el hash de forma automática cuando detecta que el almacenado se generó con parámetros distintos de los actuales. Endurecer el coste más adelante es, por tanto, cambiar tres constantes: los hashes antiguos se van reemplazando por los nuevos a medida que cada usuario inicia sesión, sin migración ni invalidación masiva de contraseñas.

La política de contraseñas es únicamente de longitud, con un mínimo de 15 caracteres, y sigue la revisión 4 de NIST SP 800-63B en sus tres exigencias [41]. Su sección §3.1.1 prohíbe las reglas de composición y la caducidad periódica, porque ambas empujan a los usuarios hacia patrones predecibles; y fija en **15 caracteres** el mínimo cuando la contraseña actúa como **factor único**, que es exactamente este caso. Los ocho caracteres que la norma admite como suelo solo valen dentro de una autenticación multifactor, que esta aplicación no tiene.

Un fallo de autenticación devuelve siempre el mismo `401` genérico, con independencia de si el correo existe. Y no basta con igualar el cuerpo de la respuesta: si el servidor solo calcula el hash cuando encuentra al usuario, la diferencia de tiempo entre una respuesta rápida y una lenta es un oráculo que permite enumerar direcciones registradas. Por eso, cuando el usuario no existe, se verifica igualmente la contraseña contra un hash ficticio. El coste se paga a propósito para que el reloj no diga lo que la respuesta calla.

> **[FIGURA 6.1]** — *Flujo de autenticación y vinculación de cuentas.* Diagrama con las dos ramas de alta y su punto de encuentro: (a) registro por contraseña → usuario `is_verified=false` → correo de verificación → `POST /verify` → sesión permitida; (b) `GET /auth/google/authorize` → callback → alta automática con `is_verified=true`; y la rama central de `associate_by_email`, marcando con un rombo la comprobación `if not user.is_verified` y sus dos salidas (vinculación normal frente a vinculación con borrado del hash de contraseña). Está aquí porque el ataque de cáscara descrito más abajo solo se entiende viendo las tres ramas juntas.
> **Cómo obtenerla:** diagrama a dibujar en Mermaid (`flowchart TD`) a partir de la tabla de ramas de `oauth_callback`.

## La sesión

El estado de autenticación es un único JWT firmado con HS256, con audiencia explícita y 14 días de vida, transportado en una cookie `HttpOnly; Secure; SameSite=Lax` en la ruta `/`. No hay pareja de token de acceso y token de refresco, ni endpoint de renovación.

Cada atributo de la cookie responde a una amenaza concreta. `HttpOnly` la hace ilegible desde JavaScript, lo que neutraliza el vector dominante de pérdida de credenciales en una SPA: la exfiltración por XSS desde `localStorage`. `SameSite=Lax` impide que la cookie viaje en sub-peticiones de otro sitio, que es la defensa frente a CSRF apropiada para una aplicación servida en un único origen; `Strict` habría roto la redirección de vuelta del proveedor OAuth, de modo que aquí `Lax` es un requisito y no una preferencia. `Secure` exige TLS.

El patrón SPA de doble token se rechazó tras examinarlo, y no por desconocimiento: un borrador anterior lo especificaba. Ese patrón procede de las aplicaciones móviles y del OAuth entre orígenes distintos, donde se presentan *bearer tokens* a APIs de terceros y el token de acceso no puede residir en una cookie. Una PWA del mismo origen no tiene ninguno de esos problemas. Su argumento habitual —«un token de acceso de vida corta limita el daño si lo roban»— se desmonta solo en una SPA, porque un XSS controla la página con independencia de dónde viva el token, mientras que una única cookie `HttpOnly` impide la exfiltración igual de bien que partir la credencial en dos. A cambio, el doble token cobra dos peajes específicos: un token en memoria se pierde al cerrar la ventana de la PWA, y cada arranque en frío paga una llamada de renovación antes de la primera petición útil; y el *service worker* no puede leer un token en memoria sin guardarlo en `IndexedDB`, que es exactamente lo que la protección frente a XSS pretendía evitar. La cookie la envía el navegador sola, también desde el *service worker*.

Lo que esto cuesta hay que decirlo sin rodeos: **la sesión es apátrida y no se puede revocar**. Una cookie robada sigue siendo válida hasta que expira, hasta catorce días después, y nada dentro de la aplicación puede cerrar la sesión de otro dispositivo. Es una limitación aceptada para un trabajo de máster; la vía de mejora es una tabla de sesiones en la base de datos, que es el mismo trabajo que la rotación de tokens de refresco respaldada por base de datos y no lo hace más barato.

## OAuth con Google

Las identidades del proveedor no se guardan como columnas del usuario, sino en una tabla de unión `oauth_account` con restricción de unicidad sobre el par `(oauth_name, account_id)`. Un segundo proveedor es una fila más, no una migración con dos columnas nuevas que quedan nulas para el 90 % de las cuentas. La unicidad sobre el par, y no sobre el identificador solo, es lo que permite que dos proveedores emitan identificadores que colisionen sin que eso vincule cuentas ajenas.

La vinculación por correo está activada, de modo que quien ya tenía una cuenta con contraseña y más tarde entra con Google acaba en su cuenta de siempre y no en una duplicada. Es la decisión cómoda para el usuario y la que abre el problema del apartado siguiente.

## Verificación y el ataque de «cáscara» de pre-registro

Los registros por contraseña nacen sin verificar y no pueden iniciar sesión hasta que se verifican; los de Google se verifican solos, porque Google ya ha demostrado el control de la dirección. Ninguna de las dos reglas es original. Interesa lo que producen juntas cuando se añade la vinculación por correo.

Sin más medidas, la vinculación por correo habilita un ataque de cáscara: el atacante registra una cuenta con contraseña usando la dirección de la víctima —una cáscara vacía, que no puede usar porque no verifica el correo— y espera. Cuando la víctima entra con Google, la vinculación funde ambas identidades en silencio y el atacante conserva una contraseña operativa sobre la cuenta de la víctima. La víctima no ve nada anómalo: entró con Google y todo funcionó.

Cerrarlo requiere las dos mitades a la vez, y ninguna sirve sola. La barrera de verificación por sí misma rompe el caso legítimo, porque la vinculación no marca la fila como verificada y el usuario que llega desde Google se encuentra bloqueado en su propia cuenta. Marcarla como verificada sin más reabre el ataque, ya que la contraseña que el atacante fijó pasaría entonces las dos comprobaciones. La solución consiste en **borrar el hash en el mismo instante en que la fila se verifica**: cuando la vinculación aterriza sobre una cuenta con contraseña aún sin verificar, se marca como verificada y se sustituye la contraseña por el hash de un secreto aleatorio que se descarta sin guardarse en ninguna parte. La víctima entra por Google con normalidad; la contraseña del atacante deja de existir; si el usuario legítimo la había puesto él, recupera el acceso por el flujo ordinario de restablecimiento. Es el patrón que aplican los proveedores de identidad comerciales, y la clave está en que ambos efectos ocurren en la misma transacción.

La condición que dispara todo esto es una sola comprobación —si el usuario devuelto sigue sin verificar— y distingue las tres ramas posibles sin casos especiales: usuario recurrente reconocido por su fila de `oauth_account`, alta nueva por Google, y vinculación por correo sobre una fila sin verificar. Solo la tercera borra el hash.

## Límites de tasa y la identidad del cliente

Verificar el correo frena el registro indiscriminado, pero no dice nada sobre los intentos contra cuentas que ya existen, y `/forgot-password` es un *endpoint* que envía correo a quien lo encuentre. Los límites son por IP y por ruta, y el criterio es explícito: **el coste de un endpoint decide su ventana**.

| Router | Límite | Qué se defiende |
| --- | --- | --- |
| Login / logout | 10/minuto | CPU del verificador Argon2id y fuerza bruta contra cuentas existentes |
| Registro | 10/hora | Alta masiva de cuentas |
| Verificación y restablecimiento | 5/hora | La bandeja de entrada de un tercero y la cuota del proveedor de correo |

**Tabla 6.1.** Límites de tasa por ruta y el criterio que fija cada ventana.

La diferencia entre el minuto y la hora no es un ajuste fino: es la distinción entre un coste que paga este servidor y un coste que paga otra persona. Un intento de login fallido consume CPU propia y se puede permitir con generosidad; un correo de restablecimiento enviado a la dirección de un tercero consume su atención y una cuota que no es de quien lo dispara.

Detrás hay una dependencia que no es evidente: **un límite por IP no vale más que la IP en la que se apoya**. Tras un proxy inverso, la dirección que ve la aplicación es la del proxy, con lo que todo internet comparte un contador y el primer atacante que alcanza el límite deja fuera a todos los usuarios a la vez. La protección se convierte en una denegación de servicio contra uno mismo. Arreglar el límite antes que la cabecera reenviada no es un arreglo parcial, es peor que no hacer nada; el orden importa.

El *camino no tomado* fue confiar en las cabeceras reenviadas con un comodín, que es la receta que circula. Se justifica diciendo que el contenedor del backend no publica puertos, de modo que solo el proxy puede alcanzarlo. El razonamiento confunde dos cosas distintas: impedir que alguien **rodee** el proxy no impide que envíe una cabecera **a través** de él. Y el comodín no es simplemente más permisivo, es que **devuelve otro valor**. Con comodín, el servidor ASGI deja de recorrer la cadena `X-Forwarded-For` y toma su primer elemento, que es precisamente el que un cliente puede fijar; restringiendo la confianza a la subred del proxy, recorre la cadena desde el final y se queda con el primer salto no confiable.

| `--forwarded-allow-ips` | Cliente resuelto |
| --- | --- |
| `*` | `1.2.3.4` (el valor que envió el cliente) |
| `172.16.0.0/12` | `203.0.113.9` (el par real del proxy) |

**Tabla 6.2.** Cliente que resuelve uvicorn ante una cabecera `X-Forwarded-For: 1.2.3.4, 203.0.113.9`, según a quién se confíe.

Hoy el comodín resultaría inofensivo, pero solo porque Caddy descarta lo que envíe el cliente mientras no se le declaren proxies de confianza. Eso es un valor por defecto de otro componente, y deja de ser cierto en cuanto se antepone una CDN. Escribir la subred costaba exactamente lo mismo.

## Dónde está realmente la frontera

Durante buena parte del desarrollo la aplicación dio dos respuestas distintas a la misma pregunta. El cliente envolvía todas sus páginas en un guardia de ruta que redirige a `/login` si no hay sesión; la API, mientras tanto, servía el catálogo, los precios, el simulador y el listado de vehículos a cualquiera que conociera la URL. Nadie decidió eso: la interfaz llevaba la decisión tomada desde el principio y el backend nunca llegó a aplicarla.

El error de razonamiento merece nombrarse porque es frecuente. **Un guardia de ruta en el cliente no es control de acceso: es navegación.** Decide qué se pinta, no qué se sirve. El código que lo evalúa corre en el navegador del usuario, que puede ignorarlo, y las URLs que la propia aplicación consulta están a la vista en cualquier inspector. Todo lo que el navegador puede pedir puede pedirlo también `curl`, y el servidor no tiene ningún medio para distinguir «esta petición viene de mi frontend» de «esta petición viene de otro sitio»: cualquier cabecera o valor que el cliente lleve consigo es igualmente visible y reproducible. La única frontera que existe es la que comprueba el servidor. Es la categoría que OWASP sitúa en primer lugar de su clasificación de riesgos, control de acceso roto [42].

Un segundo argumento, más ligado al despliegue, empujaba en la misma dirección equivocada: el contenedor del backend no publica puertos, luego «no está expuesto». Es cierto y es insuficiente, por la misma razón que en el apartado anterior. No publicar puertos impide rodear el proxy inverso; no impide llegar a través de él, que es justo lo que hace el navegador de cualquier usuario legítimo. Si esa ruta estuviera cerrada, la aplicación no funcionaría.

La corrección monta la dependencia de sesión sobre los routers completos y no endpoint a endpoint, de manera que un endpoint nuevo dentro de uno de ellos no pueda nacer sin protección. La prueba de regresión no enumera rutas a mano: las **deriva del esquema OpenAPI de la propia aplicación** y exige un `401` en todas salvo las deliberadamente públicas, que son la comprobación de salud y la superficie de autenticación. Una lista escrita a mano envejece en silencio, y su modo de fallo —dejar de cubrir lo que se añadió después— es exactamente el que no se quiere. La prueba lleva además dos guardas propias: una que comprueba que el inventario de rutas no está vacío, porque un error tipográfico en el filtro convertiría el conjunto en cero casos que pasan, y otra que recorre el camino completo de registro, verificación e inicio de sesión y comprueba que la cookie real sí abre la puerta, para que la batería no siguiera pasando si la frontera rechazara a todo el mundo.

> **[FIGURA 6.2]** — *La frontera, comprobada contra producción.* Captura del terminal con la salida de `curl -i https://s-charge.app/api/points`, mostrando en una sola pantalla el `HTTP/2 401` y las cabeceras de seguridad de la respuesta (`strict-transport-security`, `content-security-policy`, `permissions-policy`, `x-content-type-options`, ausencia de `server`). Sustituye a dos capturas: demuestra a la vez que la API no sirve el catálogo sin sesión y qué endurecimiento llega realmente al cliente.
> **Cómo obtenerla:** ejecutar el comando contra el dominio de producción y capturar la salida completa; no recortar las cabeceras.

## Robo de sesión y *bearer tokens*

Todo lo anterior defiende el modelo de amenazas estándar de una SPA: exfiltración por XSS, CSRF, reutilización de credenciales y abuso de cuentas sin verificar. No defiende la vía de apropiación que domina los informes de incidentes de cuentas de consumo desde 2024.

El ataque no empieza en el servidor. Un equipo comprometido —típicamente por ingeniería social, como el falso CAPTCHA que pide al usuario pegar un comando en un terminal— ejecuta un *infostealer* bajo la propia cuenta de sistema operativo del usuario. El programa lee el almacén de cookies del navegador, las contraseñas guardadas y la huella del equipo, y lo sube todo como un lote que se vende como mercancía. El comprador lo carga en un navegador anti-detección configurado con un proxy residencial cercano a la víctima, presenta la cookie robada y queda autenticado desde la primera petición.

Dos propiedades hacen que ninguna señal de anomalía lo detecte. La cookie robada es una prueba de identidad **completa**: es la salida de un inicio de sesión previo y correcto, con cualquier segundo factor ya satisfecho, de modo que no se invoca ningún paso de re-autenticación. Y el atacante presenta la huella y la geografía aproximada de la víctima —agente de usuario, zona horaria, idioma, hashes de canvas y WebGL—, con lo que el motor de riesgo no ve nada que le llame la atención. Los paneles de «actividad reciente» siguen atribuyendo las peticiones al dispositivo que **acuñó** la sesión, no al que realiza cada petición.

La causa es arquitectónica y no de implementación: las cookies de sesión son *bearer tokens*. Poseer la cadena equivale, por protocolo, a poseer la credencial, y nada en la petición liga el token al dispositivo que lo recibió. `HttpOnly` neutraliza la exfiltración por JavaScript, que es su objetivo de diseño, y no puede neutralizar la exfiltración por código nativo que corre como el mismo usuario del sistema, porque ninguna aplicación puede: en un escritorio monousuario la frontera de seguridad es el proceso que el usuario decide ejecutar, no la aplicación que custodia la credencial.

| Categoría | Mecanismo | Efecto | En este trabajo |
| --- | --- | --- | --- |
| Hacer el token no-*bearer* | DBSC [43], DPoP [44] | Cada petición lleva la firma de una clave residente en el TPM o el Secure Enclave; la cookie sola no basta. Ataca la causa raíz. | No. DBSC lo lideran los fabricantes de navegadores y aún no es una primitiva estable para el servidor; DPoP exigiría un transporte sin cookies, rechazado para una PWA del mismo origen |
| Re-autenticar antes de acciones sensibles | Verificación con WebAuthn o *passkey* al cambiar correo o contraseña y al consentir un OAuth nuevo | La sesión robada puede navegar, pero no escalar | No. Viable en la capa de aplicación y añadible más adelante |
| Limitar el radio de daño | Vidas cortas, rotación con detección de reutilización, revocación en servidor | Reduce la ventana de explotación; no la previene | Sí, y solo esta |

**Tabla 6.3.** Categorías de defensa frente al replay de un token robado, y cuál implementa este trabajo.

La respuesta honesta en la defensa a «¿por qué esto no resiste el robo de sesión?» es que **ninguna aplicación actual lo resiste** bajo el modelo de *bearer token*. Las dos defensas que cambiarían esa respuesta o bien no son todavía una primitiva expuesta al servidor, o bien son un endurecimiento incremental y no una omisión de diseño. La amenaza posterior al compromiso del equipo del usuario se reconoce fuera de alcance, no se pasa por alto.

## La IP como dato personal

Registrar la IP del cliente introduce datos personales en los registros de la aplicación. Una dirección dinámica es dato personal para el prestador que dispone de medios legales para identificar al interesado con los datos adicionales que tiene su proveedor de acceso; así lo condicionó el Tribunal de Justicia en el asunto *Breyer* [45], y este trabajo asume cumplida esa condición y trata la IP como tal. La base jurídica es el interés legítimo del artículo 6.1.f, y el considerando 49 menciona expresamente la seguridad de las redes y de la información [35]: un registro de auditoría de autenticación y una clave de límite de tasa son ese caso y no una zona gris. Lo que obliga entonces no es el consentimiento, sino informar, no reutilizar el dato para otros fines y acotar la conservación. El desarrollo del marco jurídico corresponde al capítulo 10; aquí importa la consecuencia de ingeniería.

Esa última obligación es la que reveló algo, porque el valor por defecto fallaba hacia el lado inseguro: Docker conserva los registros de los contenedores indefinidamente. El mismo descuido era a la vez un almacén de datos personales sin plazo y el riesgo de llenado de disco que nadie había acotado —una coincidencia frecuente entre protección de datos y operación—. La rotación acota el **volumen**; la limitación del plazo pide acotar el **tiempo**, y eso queda pendiente junto al resto de obligaciones que este trabajo reconoce sin resolver. Registrarlo no lo resuelve: lo convierte en una decisión tomada en lugar de una omisión.

Se descartó llevar los eventos a una tabla de PostgreSQL, pese a que haría trivial el borrado por plazo con una sentencia `DELETE`. Meter una escritura en la ruta de autenticación tiene coste, y sobre todo empuja datos personales hacia las copias de seguridad, cuya conservación es más larga y más gruesa que la de los registros: la tabla resolvería el borrado en un sitio y lo complicaría en otro. Una tabla se justificaría si el historial de accesos llegara a mostrarse al usuario, pero eso sería una funcionalidad del producto y no un registro de seguridad, dos cosas que conviene no confundir por compartir los mismos campos.

Los eventos auditados hoy son el alta, el inicio de sesión correcto, la verificación, el restablecimiento, el fallo de envío de correo y la vinculación OAuth que borra el hash, en líneas JSON sobre la salida estándar. El fallo de inicio de sesión y el cierre de sesión no tienen punto de enganche en la librería y no están cubiertos, lo que deja precisamente sin registrar la señal más útil para detectar fuerza bruta.

## Endurecimiento verificado, y lo que falta

Sobre el servidor real están comprobados HSTS con un año de vigencia, el juego de cabeceras de seguridad de OWASP —`X-Content-Type-Options`, `Referrer-Policy`, las dos políticas de aislamiento de origen cruzado, `X-Frame-Options`— y una `Permissions-Policy` que apaga todas las capacidades del navegador salvo la geolocalización, que la aplicación necesita para el botón de «dónde estoy». La ruta del esquema OpenAPI se anula en producción, lo que retira con ella la documentación interactiva de Swagger y ReDoc sin tocar el contrato versionado, que se genera llamando a la aplicación y no por HTTP. PostgreSQL no publica puerto alguno.

Dos cabeceras se omiten a propósito y no por olvido: el aislamiento estricto de recursos incrustados bloquearía las teselas de OpenFreeMap, que son de otro origen y no declaran permiso, y la geolocalización se permite para este origen por la razón ya dicha.

Lo que no está es la Content-Security-Policy completa. Hoy se envía únicamente `frame-ancestors 'none'`, que se puede desplegar ya porque no depende de `default-src` y por tanto restringe el enmarcado sin tocar guiones ni estilos. La política completa espera a la migración del frontend descrita en el capítulo 4: MUI y Emotion inyectan etiquetas `<style>` en línea, lo que obligaría a declarar `style-src 'unsafe-inline'` y a negar buena parte del beneficio que se pretendía obtener. Escribir una CSP que hay que debilitar en su directiva más expuesta es peor que posponerla, porque produce la apariencia de una defensa donde no la hay.
